---
name: session-recovery
description: Reconstruct in-flight work after a crash, power outage, reboot, or accidental terminal close. Identifies which Claude Code sessions were active, classifies each as merged / open / orphaned, maps them to feature branches and worktrees, and produces concrete `claude --resume` commands plus a cleanup punch list. Use when the user asks to "recover sessions", "what was I working on", "resume after a crash", or after they mention losing tabs/terminals.
---

# Session Recovery

Reconstruct what was in flight from on-disk artifacts. Trust evidence over memory.

## Inputs you need from the user

Optional but helpful — work without them if missing:

- A list of work-stream names they remember (e.g. "auth refactor", "Chat A").
- The repo they were working in (default: cwd).
- Approximate crash time (default: derive from `uptime`).

## The data sources, in priority order

Sessions and worktrees decay independently. Always cross-check at least two sources before reporting status.

1. **Claude Code session logs** — `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`
   - `<encoded-cwd>` is the cwd with `/` → `-` and a trailing `--` for hidden dirs (so `/Users/alice/repo/.worktrees/foo` → `-Users-alice-repo--worktrees-foo`).
   - The JSONL contains the full conversation. Each line is one event with a `cwd`, `sessionId`, `gitBranch`, `slug`, `timestamp`, and either a user message or assistant content.
   - **A session is resumable from any cwd** via `claude --resume <session-id>` — the worktree being gone does not delete the conversation history.
2. **Git reflog** — `git reflog --date=iso` on the main repo. Authoritative record of merges, rebases, resets, and `pull --ff-only` operations near the crash.
3. **Git branches + `git branch --contains <sha>`** — proves whether a chat's commits actually landed on `main` vs sit on a feature branch.
4. **`git worktree list`** — shows which worktrees still physically exist. Cross-reference with session cwds.
5. **`gh pr list --state all`** — distinguishes "merged via PR" from "merged locally" from "open".
6. **`uptime` and `date`** — bound the crash window. Activity in JSONL after `now - uptime` is post-reboot work the user has already started.
7. **`ps -ef | grep "[c]laude"`** — currently-running Claude processes. If two `claude --resume` are already running, the user has started recovery; don't re-suggest those.
8. **The repo's own truth files** — many projects have a tasklist or chat-letter map (`docs/roadmap/`, `docs/superpowers/`, etc.). Always check these before declaring something "open".

## Workflow

### 1. Bound the crash window

```bash
date
uptime          # system rebooted ~uptime ago
ps -ef | grep "[c]laude"   # who's already running?
```

If `ps` shows live `claude --resume` processes, mark those sessions as "user is already resuming" and do not list them as needing action.

### 2. Inventory active sessions

```bash
# All sessions touched in the last day, newest first:
find ~/.claude/projects -name "*.jsonl" -newermt "yesterday" 2>/dev/null \
  | xargs ls -lt | head -40
```

Note timestamps near the crash window — those are the in-flight tabs.

### 3. Identify each session's topic + state

For every candidate session, extract first user message + last assistant message. Use Python (jq is unreliable on these JSONLs because some `text` fields contain unescaped newlines and shell quoting):

```python
import json, sys
p = sys.argv[1]
first_user, last_asst, last_cwd, last_branch = None, None, None, None
with open(p) as f:
    for l in f:
        try:
            d = json.loads(l)
            t = d.get('type')
            last_cwd = d.get('cwd', last_cwd)
            last_branch = d.get('gitBranch', last_branch)
            content = d.get('message', {}).get('content', [])
            if isinstance(content, str): content = [{'type':'text','text':content}]
            for b in content:
                if isinstance(b, dict) and b.get('type') == 'text':
                    txt = b['text']
                    if t == 'user' and not txt.startswith('<') and first_user is None:
                        first_user = txt[:300]
                    elif t == 'assistant':
                        last_asst = txt[:400]
        except: pass
print('cwd:', last_cwd); print('branch:', last_branch)
print('FIRST:', first_user); print('LAST:', last_asst)
```

The first user message often names the chat letter or feature ("pursue Chat F", "@docs/...pursue Chat A"). The last assistant message reveals state ("Ready to merge", "Worktree safe to remove", "Clean. Ready to close.").

### 4. Cross-check each session against git

Before reporting a session as "open" or "needs work":

```bash
# Did the work actually land on main?
git log --all --oneline --since="2 days ago" | grep -iE "<topic-keyword>|chat <letter>"
git branch -a --contains <suspect-commit>

# Is the worktree real?
git worktree list

# Is the branch ahead of main?
git log main..<branch> --oneline
git log <branch>..main --oneline   # empty = fully merged
```

A session that ends with "Ready to close" but whose commits are NOT on main means the merge was pending when the crash hit. A session that ends mid-task is genuinely interrupted.

### 5. Classify and report

For each session, produce a row:

| Workstream | Session ID | cwd / branch | State | Action |
|---|---|---|---|---|
| (user's name for it) | (uuid) | (path / branch) | merged ✓ / ahead-of-main / orphaned-but-resumable / live-worktree | concrete command |

States to distinguish:
- **Merged + worktree gone** — work landed, nothing to do but cleanup. Conversation is still resumable for context if needed.
- **Merged + worktree still on disk** — landed; worktree is stale and safe to `git worktree remove`.
- **Branch ahead of main** — work didn't land yet. Either resume the session, open a PR, or merge.
- **Worktree gone, branch gone, no commits found** — the session may have been research-only or work was rebased away. Resume the conversation to recover context.
- **Live-worktree, session interrupted mid-task** — highest priority to resume.

### 6. Propose actions, not just status

For each row, give a copy-paste command:

```bash
# Resume a specific conversation (works even if the original cwd is gone):
claude --resume <session-id>

# Continue most-recent in a worktree:
cd <worktree-path> && claude --continue

# Open a PR for a feature branch ahead of main:
cd <worktree-path> && gh pr create

# Cleanup a stale worktree whose branch is fully merged:
git worktree remove <path>
git branch -d <branch>
```

## Common pitfalls

- **Don't trust session-file mtimes at first glance.** Mtimes after the crash mean the user is already resuming that session in another tab — those need to be excluded from the "needs action" list, not added.
- **Directory mtimes lie.** `~/.claude/projects/<dir>/` mtime may be from a tool touching it during shutdown; the actual session activity is in the `.jsonl` mtime inside.
- **Don't conflate "worktree is gone" with "work is lost".** Cross-check with `git branch --contains` and `git log --all`. Most "lost" chats turn out to have their commits on main even though the worktree was cleaned up.
- **Don't conflate "branch exists" with "work is unmerged".** A branch can exist and be fully reachable from main. Always run `git log main..<branch>` to confirm there's a delta.
- **A session whose last message says "Ready to close" or "Safe to remove" usually landed.** But verify with `git branch --contains` — sometimes the merge was queued and the crash hit before it ran.
- **`grep -oE` with brace counts breaks** on macOS BSD grep. Use Python for JSONL parsing.
- **Project-specific chat-letter maps.** Some repos use `Chat A` / `Chat N` conventions to map to tasklist sections, not to session IDs. Check the repo's roadmap docs before guessing the mapping.

## Output shape

End with a punch list grouped by category:

```
## Already in flight (don't re-suggest)
- <session> — user is resuming in ttysNNN

## Resume to continue
- <feature> — `cd <path> && claude --continue`

## Already merged — cleanup only
- <feature> — `git worktree remove <path> && git branch -d <branch>`

## Needs PR / merge
- <feature> — N commits ahead of main; `gh pr create`

## Unidentified workstreams from the user's list
- <name> — couldn't map to a session/branch; ask the user for cwd or topic
```

The unidentified bucket is critical: don't fabricate a match. Ask.
