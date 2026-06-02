# Dotfiles

Box up an opinionated developer experience as idempotent, repeatable setup.

Clone on a fresh Mac, run one install script, and the machine is bootstrapped: Homebrew packages, macOS preferences and Dock, and the curated agentic-coding tooling (rules, skills, MCP) we've blessed — deployed globally across Claude Code, Cursor, Codex, Gemini, and Pi. A tight `dotfiles` CLI keeps it healthy (doctor, snapshot, brew sync) and handles small conveniences (remote SSH, model benchmarks). A small phone-drivable TUI manages long-running agent sessions on the go.

**This is** the single source for our developer experience — when we bless a tool, it goes in here and becomes core. **It is not** a project generator or a terminal dashboard. It sets up the computer and gets out of the way. Technology taste (which language, which framework) lives as reviewable reference in [`docs/stacks/`](docs/stacks/README.md) — consulted per-project, never pushed.

---

## Quick Start

### Fresh Mac Setup

```bash
# 1. Install Xcode CLI tools
xcode-select --install

# 2. Clone and run
git clone https://github.com/<your-username>/dotfiles ~/dotfiles
~/dotfiles/install.sh

# 3. Re-run anytime (idempotent)
dotfiles install
```

**What you get:**
- Shell: Zsh + Oh My Zsh + custom theme
- Runtimes: Go, Rust, Bun, Node.js (fnm), Python (uv)
- Editors: Zed (default `$EDITOR` / quick edits) + Cursor (AI-native, shared MCP servers)
- Terminal: Ghostty (GPU-accelerated, desktop notifications)
- CLI: Git, gh, just, jq, delta, hyperfine, and more
- AI: Claude Code (with plugins, hooks, MCP servers), Claude Desktop

The installer is idempotent — safe to re-run anytime.

### CLI development

The `dotfiles` CLI is migrating to a hexagonal Python/Typer app in `cli/`
(uv-managed). Run dev checks with `just check`. `bin/dotfiles` delegates migrated
commands to the Python CLI and falls back to the legacy Bash router for the rest.

---

## What's Installed

### Shell & Terminal

- **Zsh + Oh My Zsh**: Custom two-line prompt with git status, venv indicator, error-aware prompt character
- **Ghostty**: GPU-accelerated terminal with desktop notifications
- **Termius**: SSH/SFTP client and host manager
- **Rectangle**: Window management
- **Shell aliases**: `cc` (Claude Code with profiles), `ccr` (AI code review), `cca` (address PR feedback)

### Runtimes

| Runtime | Manager | Notes |
|---------|---------|-------|
| **Node.js** | fnm | LTS version, auto-switches per project |
| **Bun** | direct | Preferred JS runtime (faster than Node) |
| **Python** | uv | Python 3.14, fast package management |
| **Go** | brew | With gopls, delve, air, sqlc, goose, templ, staticcheck |
| **Rust** | rustup | Via official installer (not Homebrew) |

### Editors

- **Zed**: Default editor — set as `$EDITOR` / git editor and the macOS open handler for text, markdown, and source/config files (`.md`, `.txt`, `.yaml`, `.json`, `.toml`, `.py`, `.ts`, etc. — see `macos/file-associations.sh`; GPU-native, boots faster than Cursor for quick edits). Config managed in `editors/zed/` (settings + keymap symlinked). Drives external agents via **ACP** — `claude-acp`, `codex-acp`, `gemini` pre-wired to use **subscription logins, not API keys** (start a thread with `cmd-?`, authenticate in-thread; keybinds `cmd-alt-a`/`-o`/`-g`).
- **Cursor**: Primary AI-native IDE (VS Code compatible, shared MCP servers, hooks, skills, agents)
- **LM Studio**: Local LLM runner (MLX/GGUF, OpenAI-compatible server). Model + context window pinned via `macos/lmstudio.sh` (default: `google/gemma-4-e4b` @ 32K) — point Zed/Obsidian/CLIs at `http://localhost:1234/v1`.
- **TypeWhisper**: On-device voice-to-text (Parakeet ASR + local Gemma cleanup via the LM Studio endpoint above, or Apple Intelligence). Replaced Wispr Flow 2026-05-29 — fully local, no subscription. No Homebrew cask; installed via `dotfiles brew install` post-install from GitHub releases.
- **Obsidian**: Knowledge base — vault configs + community plugins managed via symlinks

  | Plugin | Purpose |
  |--------|---------|
  | **Spaced Repetition** | Flashcards in notes (`question::answer`), SM-2 scheduling |
  | **Dataview** | Query notes like a database (inline JS/DQL) |
  | **Templater** | Advanced templates with JS expressions |
  | **Calendar** | Visual calendar sidebar linked to daily notes |
  | **Natural Language Dates** | Type `@tomorrow` → date link |
  | **Linter** | Auto-format markdown on save |

### CLI Tools

| Category | Tools |
|----------|-------|
| **Core** | git, git-lfs, delta (diffs), gh (GitHub CLI), jq, yq, wget, fd, ripgrep, fzf, zoxide, helix (editor), yazi (file manager) + preview helpers (poppler, resvg, imagemagick, sevenzip), tmux, mosh, zellij |
| **System** | htop, iftop, nmap, dockutil, terminal-notifier |
| **Dev** | just (task runner), lefthook (git hooks), shellcheck (shell linting), hyperfine (benchmarks), atlas (migrations), duckdb, infisical (secrets), wrangler (Cloudflare deploys, via npm — brew formula is the unrelated Erlang tool) |

### Daily Drivers — Power User Tips

Most of the CLI tools above have a steep-ish learning curve that pays for itself in days. This is the minimum set of shortcuts worth memorising.

#### fzf keybindings (shell-wide)

Loaded by `.zshrc` via `source <(fzf --zsh)` — active everywhere.

| Key | Action |
|-----|--------|
| `Ctrl-T` | Fuzzy-pick file(s), paste path(s) at cursor. E.g. `git add <Ctrl-T>`, `cursor <Ctrl-T>` |
| `Ctrl-R` | Fuzzy-search shell history. Replaces the default reverse-i-search. |
| `Alt-C`  | Fuzzy-cd into any subdirectory of cwd |
| `**<Tab>` | Trigger fzf anywhere. `ssh **<Tab>` (hosts), `kill -9 **<Tab>` (PIDs), `git co **<Tab>` (branches) |
| `Tab` on a path | Path completion via fzf |

Inside any fzf prompt: `'foo` = exact match, `!bar` = exclude, `^prefix` / `suffix$` = anchor.

#### zoxide — smart `cd`

Defines `z` and `zi` (replaces the oh-my-zsh `z` plugin). Learns from your `cd` history; a path has to be visited once before `z` will jump to it.

| Command | Action |
|---------|--------|
| `z <word>` | Jump to best-ranked dir matching `word` |
| `z foo bar` | Multi-keyword — dir must match both. `z dot shell` → `~/dotfiles/shell` |
| `zi` | Interactive picker over all tracked dirs (uses fzf) |
| `z -` | Previous directory |

#### fd — fast file finder (replaces `find`)

Respects `.gitignore` by default.

| Command | Purpose |
|---------|---------|
| `fd pattern` | Find files matching regex on name |
| `fd -e md` | Filter by extension |
| `fd -H pattern` | Include hidden files |
| `fd -t d pattern` | Directories only (`-t f` = files) |
| `fd pattern -x cmd {}` | Run `cmd` on each match (replaces `find -exec`) |

#### ripgrep (`rg`) — fast content search

Respects `.gitignore` by default. **`grep` will feel broken after you learn this.**

| Command | Purpose |
|---------|---------|
| `rg pattern` | Search file contents recursively from cwd |
| `rg -l pattern` | Just filenames that match |
| `rg -C 3 pattern` | 3 lines of context before + after |
| `rg -t py pattern` | Type-filtered (common: `py`, `go`, `rust`, `md`, `ts`) |
| `rg -g '*.toml' pattern` | Glob-filtered |
| `rg --files` | List all non-ignored files (faster than `fd` for "everything") |

#### yazi — terminal file manager

Launch with `yz` (wrapper function — see below). Navigation is vim-keyed.

| Key | Action |
|-----|--------|
| `h` `j` `k` `l` | Navigate (←↓↑→) |
| `space` | Toggle-select (multi-select by holding + repeating) |
| `enter` / `o` | Open with default app |
| `y` / `x` / `p` | Copy / cut / paste |
| `d` / `D` | Trash / permanent-delete |
| `a` / `r` | Create file or dir / rename |
| `/` | Search in current dir |
| `f` / `F` | Find-by-name (fd) / find-in-files (rg) |
| `z` | Jump to directory via zoxide |
| `i` / `I` | Scroll preview pane up/down |
| `t` / `1`–`9` | New tab / switch tab |
| `g` / `G` | Top / bottom of list |
| `q` | Quit (shell follows via the `yz` wrapper) |

Preview pane auto-uses the installed companions: `poppler` (PDFs), `resvg` (SVGs), `imagemagick` (HEIC/PSD/TIFF), `sevenzip` (peek inside archives).

**Key yazi tip:** `yz` is defined as a shell function (in `.zshrc`), not a plain alias — so when you quit yazi, your shell `cd`s to wherever you ended up. This turns yazi from a viewer into a navigator.

#### High-value combos

| Combo | Effect |
|-------|--------|
| `cursor $(fd -t f \| fzf)` | Fuzzy-pick a file and open in Cursor |
| `cd $(zoxide query -l \| fzf)` | Equivalent to `zi`, useful when scripting |
| `rg -l pattern \| xargs cursor` | Open every matching file in Cursor |
| `fd -e py -x wc -l {}` | Run a command on every matched file |
| `gh pr list \| fzf` | Fuzzy-pick a PR (any gh-listed thing, really) |

### AI Tools

| Tool | Provider | Status | Purpose |
|------|----------|--------|---------|
| **Claude Code** | Anthropic | active | Agentic coding assistant (CLI) with plugins, hooks, MCP servers |
| **Claude Desktop** | Anthropic | active | Claude macOS app |
| **Cursor** | Cursor | active | AI-native editor with shared MCP servers, hooks, skills, agents |
| **Codex CLI** | OpenAI | active | Terminal coding agent (open-source, o4-mini default) |
| **Pi** | earendil-works | active | Local-first lightweight terminal agent (shares `~/.agents/skills`); packages `pi-superpowers-plus` + `mitsupi`, vendored `safe-git` guardrail. See ADR-0005/0006 + [docs/pi-power-setup.md](docs/pi-power-setup.md) |
| **Copilot CLI** | GitHub | disabled | Terminal coding agent (fleet mode, cloud delegation) |
| **Codex Desktop** | OpenAI | disabled | macOS app for parallel coding agents |
| **GWS CLI** | Google | active | Google Workspace CLI (Drive, Gmail, Calendar, Sheets, Admin) |
| **Gemini CLI** | Google | disabled | Terminal coding agent (Gemini 2.5 Pro, free tier) |
| **Antigravity** | Google | disabled | AI-native IDE (dual Editor/Manager view) |

**Cursor extensions** (managed in `editors/extensions.sh`):

| Extension | Status | Notes |
|-----------|--------|-------|
| `anthropic.claude-code` | active | Claude Code companion inside Cursor |
| `github.copilot` | disabled | Conflicts with Cursor built-in AI |
| `google.gemini-code-assist` | disabled | Gemini Code Assist for IDE |
| `openai.codex` | disabled | Codex IDE extension |

See `docs/knowledge/ai-tools.md` for the full landscape and investigation notes.

### Codex CLI

Setup is automated via `dotfiles agent setup` (also runs during install):

- **Global instructions**: `~/.codex/AGENTS.md` deployed from shared rules
- **Config**: `~/.codex/config.toml` with MCP servers and `project_doc_fallback_filenames = ["CODEX.md"]`
- **Statusline**: `[tui]` theme + status-line text segments installed from `ai/agents/codex/statusline.toml`
- **Hooks**: Format-on-save (reuses Claude's hook), sensitive file guard, terminal notifications
- **Skills**: deployed from `ai/skills/` via `npx skills`
- **MCP servers**: From shared source (`ai/agents/shared/mcp-servers.json`) — targets "codex" or "claude"
- **Command auto-approve**: `~/.codex/rules/default.rules` deployed from `ai/agents/codex/default.rules` (universal allowlist; Codex appends interactive approvals — fold back periodically)

See `ai/agents/codex/` for all configuration files.

### Gemini CLI

Setup is automated via `dotfiles agent setup`:

- **Settings**: `~/.gemini/settings.json` seeded from `ai/agents/gemini/settings.json` (preserves existing auth)
- **Global instructions**: `~/.gemini/GEMINI.md` written verbatim from `ai/agents/shared/rules.md` (the same kernel every vendor gets)
- **MCP servers**: From shared source (`ai/agents/shared/mcp-servers.json`) — servers with `gemini` in `targets`

Gemini does not yet have skills or subagents surfaces; rules cover the equivalent ground.

See `ai/agents/gemini/` for all configuration files.

### External Connections

Services we integrate with, and how. Prefer CLIs (simplest) > MCPs (cross-tool) > plugins (tool-specific).

| Service | Method | Claude Code | Cursor | Codex | Notes |
|---------|--------|:-----------:|:------:|:-----:|-------|
| **GitHub** | CLI (`gh`) + MCP | yes | yes | yes | CLI + MCP server (`gh mcp-server`) |
| **Linear** | MCP (`mcp-remote`) | yes | yes | yes | Issue tracking |
| **Context7** | MCP (`@upstash/context7-mcp`) | plugin | yes | — | Up-to-date library docs |
| **Neon** | ~~MCP~~ (disabled) | — | — | — | Neon Postgres; revisit when actively using Neon projects |
| **Granola** | MCP (`granola-mcp` via `uvx`) | yes | — | — | Meeting notes (reads local cache, no API key) |
| **Notion** | MCP | yes | yes | yes | Via shared MCP servers |
| **Playwright** | MCP (`@playwright/mcp`) | yes | yes | yes | Tier 3a — drive a real page, screenshot, click, network. WebRTC-capable. |
| **Chrome DevTools** | MCP (`chrome-devtools-mcp`) | yes | yes | yes | Tier 4 — Chrome-only forensics: network, console, perf traces |
| **agent-browser** | CLI (`agent-browser`) | yes | yes | yes | Tier 2 — token-cheap (~200-400/page) "look at this page" CLI. No MCP overhead. |
| **pinchtab** | CLI (`pinchtab`) | yes | yes | yes | Tier 2 — accessibility-tree extraction (~800 tokens/page). HTTP API. |
| **Stagehand** | per-project SDK (`@browserbasehq/stagehand`) | yes | yes | yes | Tier 5 — natural-language test framework for long agentic flows. Install per-project. |
| **Gmail** | claude.ai cloud MCP | yes | — | — | Claude Code only (not reproducible in config) |
| **Google Calendar** | claude.ai cloud MCP | yes | — | — | Claude Code only (not reproducible in config) |

**Considered** (not yet enabled — add to `ai/agents/shared/mcp-servers.json` when needed):

| Service | Method | Why consider | Status |
|---------|--------|-------------|--------|
| **Slack** | MCP (`mcp-remote`) | Team comms — search channels, post messages, triage threads | Evaluate |
| **Datadog** | MCP / CLI (`datadog-ci`) | APM, logs, dashboards, incident context | Evaluate |
| **Sentry** | MCP / CLI (`sentry-cli`) | Error tracking, issue triage, release management | Evaluate |
| **Dagster** | Plugin / MCP | Data pipeline orchestration & observability | Evaluate |

MCP config: `ai/agents/shared/mcp-servers.json` (shared source), deployed to Claude Code and Cursor by `dotfiles agent setup`.

### Claude Code

Setup is automated via `dotfiles agent setup` (also runs during install):

- **Global instructions**: `~/.claude/CLAUDE.md` written from `ai/agents/shared/rules.md` (the universal kernel — process, safety, voice, command style)
- - **Permissions**: `permissions.{allow,deny,defaultMode}` from `ai/agents/claude/permissions.json` (canonical baseline — fold interactive approvals back periodically)
- **Plugins**: 19 plugins (LSP, workflows, tooling, quality, integrations)
- **Hooks**: Format-on-save (biome/ruff/rustfmt/gofmt/shellcheck), sensitive file guard, terminal notifications on completion
- **Skills**: deployed from `ai/skills/` via `npx skills`
- **Agents**: deployed from `ai/subagents/`
- **MCP servers**: From shared source (`ai/agents/shared/mcp-servers.json`) — GitHub, Linear, Granola, Notion, Playwright, Chrome DevTools (standalone); Context7 (via plugin)
- **Browser-tool tiers**: See `docs/knowledge/browser-tooling.md` — when to reach for Playwright tests (Tier 1), agent-browser/pinchtab CLIs (Tier 2), Playwright/Chrome DevTools MCPs (Tier 3-4), or Stagehand (Tier 5)
- **Cloud MCPs**: Gmail, Google Calendar (configured via claude.ai, not in dotfiles)
- **Preferences**: Voice mode, terminal bell, acceptEdits mode
- **Desktop**: MCP servers + preferences (cowork, sidebar, web search)

**Shell workflow aliases** (in `.zshrc`):

| Alias | Usage | Description |
|-------|-------|-------------|
| `cc` | `cc [-w] [-a\|-p\|-e] [--chrome]` | Launch Claude Code with worktree + permission profile |
| `ccc` | `ccc -wa`, `ccc --yolo` | Claude Code in Chrome — shorthand for `cc --chrome` |
| `ccr` | `ccr`, `ccr 2277`, `ccr <url>` | AI code review — local uses `/review-pr` (6 agents), PR uses `/code-review` (5 agents + GitHub comments) |
| `cca` | `cca [-c] [-p] [PR]` | Address PR feedback — `-c` replies to comments, `-p` pushes |
| `gcmw` | `gcmw` | Generate a commit message for staged changes via Claude Sonnet and commit |
| `gacp` | `gacp`, `gacp "msg"` | Stage everything, commit (generated message or given), and push in one shot |

See `ai/agents/claude/` for all configuration files.

### Cursor

Setup is automated via `dotfiles agent setup cursor` (also runs during install):

- **MCP servers**: From shared source (`ai/agents/shared/mcp-servers.json`)
- **Editor config**: `editors/cursor/settings.json` + `editors/cursor/keybindings.json` symlinked into Cursor User config
- **Universal rules**: `~/.cursor/rules/shared-rules.mdc` generated from `ai/agents/shared/rules.md` (the one kernel)
- **Hooks**: Shared hook definitions deployed from `ai/agents/cursor/hooks/`
- **Skills**: Cursor doesn't have a skills concept; rules cover the equivalent surface
- **Subagents**: Cursor doesn't dispatch subagents; the `ai/subagents/` collection deploys to Claude Code and Codex only
- **Rules**: Shared rules from `ai/agents/shared/rules.md`
- **Marketplace stack**: See `ai/agents/cursor/PLUGINS.md` for core/work plugin recommendations and install commands (`/add-plugin ...`)

Note: Cursor Marketplace plugin installs and OAuth flows are manual by design (run in Cursor chat/UI). The setup scripts print an explicit checklist so these steps are hard to miss.

See `ai/agents/cursor/` for all configuration files.

---

## Configuration

### Homebrew

Edit `macos/packages.toml` to customize packages. Organized by category with opt-in feature flags. Essentials include Chrome and Tailscale.

```bash
# Sync packages from packages.toml (idempotent)
dotfiles brew install

# Skip optional groups
dotfiles brew install --no-ai --no-social

# Report stale (installed but not in manifest) and missing packages
dotfiles brew stale
```

### The `dotfiles` Command

```bash
dotfiles help                # Show available commands
dotfiles install             # Re-run full setup (install.sh)
dotfiles doctor              # Check all tools are installed; exits non-zero when tools are missing
dotfiles doctor --fix        # Repair symlinks and redeploy agent configs
dotfiles update              # Update OS, Homebrew, runtimes, and dev tools
dotfiles clean               # Clear Homebrew caches
dotfiles brew install        # Sync Homebrew packages from packages.toml
dotfiles brew stale          # Find packages not declared in packages.toml
dotfiles dock                # Reset Dock layout
dotfiles profile-shell       # Profile shell startup time
dotfiles cursor-plugins      # Print Cursor Marketplace plugin install checklist
dotfiles agent overview      # Show active agentic setup (Claude Code + Cursor)
dotfiles agent setup        # Configure Claude + Cursor + Codex + Gemini + Pi (optional --reset-mcp, --clean)
dotfiles agent verify        # Check skills/agents deployed + probe MCP servers (--offline skips probes)
dotfiles completions         # Output shell completions
dotfiles remote on --dry-run
                             # Preview Termius SSH/Mosh/Zellij setup
dotfiles remote on --add-key "ssh-ed25519 AAAA... termius-phone" --harden-ssh
                             # Enable phone access with key-only SSH
dotfiles remote off --dry-run
                             # Preview turning off macOS Remote Login
dotfiles remote off --kill-sessions
                             # Turn off Remote Login and kill active SSH/Mosh sessions
dotfiles sesh                # fzf-pick a live zellij session and attach
dotfiles sesh ls             # list sessions
dotfiles sesh new <name>     # create + attach
dotfiles sesh attach <name>  # attach (create if needed)
dotfiles sesh kill <name>    # kill a session
dotfiles snapshot            # Capture machine state (brew, runtimes, symlinks, agent config)
dotfiles snapshot ls         # List saved snapshots, newest first
dotfiles snapshot diff [A] [B]
                             # Diff two snapshots; A/B are slug prefixes or 'now'
dotfiles tui                 # Launch Mission Control TUI (phone command deck)
dotfiles                     # Bare invocation prints help (use 'dotfiles tui' for the dashboard)
```

`dotfiles remote on` prints the Mosh command to paste into Termius. It connects over Tailscale/SSH and attaches to a persistent `zellij` session named `mobile` by default. `dotfiles remote off` turns off macOS Remote Login, which prevents new SSH/Mosh logins. Add `--kill-sessions` to disconnect already-open Termius sessions too.

`dotfiles sesh` (alias: `dotfiles session`) manages zellij sessions on the current machine. The same sessions are reachable from the phone over Termius/mosh — `dotfiles remote on` also prints a picker-based Termius startup command that drops straight into the fzf session picker.

`dotfiles snapshot` captures a point-in-time machine state and saves it as JSON under `~/.local/state/dotfiles/snapshots/`. Use `diff now` to compare the latest saved snapshot against the current live state, or pass two slug prefixes to diff any two captures.

`dotfiles tui` opens the Mission Control TUI — a phone-drivable Textual dashboard over the same core services. Press `q` to quit. (Bare `dotfiles` with no args prints help.) The **Remote** pane shows your Remote Login / Tailscale state; press `[t]` to toggle Remote Login (sudo-aware), `[c]` to copy the Mosh connect command to the clipboard, or `[k]` to kill open Mosh sessions (with a self-disconnect confirmation). The **Sessions** pane lists live zellij sessions; press Enter to attach (or switch session if already inside zellij).

Enable tab completion:
```bash
# Add to ~/.zshrc
eval "$(dotfiles completions)"
```

### Git

- `.gitconfig`: Modern defaults (delta, push.autoSetupRemote, rebase on pull)
- `.gitconfig.local`: Your name/email (created on first install, not committed)
- `.gitignore_global`: Common ignores

---

## Directory Structure

```
dotfiles/
├── install.sh              # Main installer (run this)
├── bin/                    # CLI tools (dotfiles command — shim delegates migrated subcommands to cli/)
├── cli/                    # Python/Typer CLI (uv-managed, hexagonal). Dev gate: `just check`
├── shell/                  # Zsh config + theme
├── git/                    # Git config + global ignores
├── editors/                # Cursor settings + Obsidian vault configs
├── terminal/               # Ghostty config
├── macos/                  # Homebrew, Dock, SSH, print utilities
├── ai/                     # All cross-vendor AI assets
│   ├── agents/             #   Per-vendor deploy config: claude, cursor, codex, gemini, pi, shared
│   │   └── shared/rules.md #     the universal agent kernel (deployed verbatim to every vendor)
│   ├── skills/             #   Canonical skill source (deployed via `npx skills`)
│   ├── subagents/          #   Subagent definitions (deployed via cp loop)
│   ├── prompts/            #   System-prompt artifacts (advisor/detailed, gemini-chunks) for web chats
│   ├── audits/             #   Audit prompts run by scheduled bot-audits on a cadence
│   ├── rules-sync/         #   Cross-harness rule-sync fragment (dotfiles agent migrate-rules-sync)
│   └── artifacts/          #   Ephemeral agent scratch (gitignored, on demand)
└── docs/                   # Curated knowledge base (see docs/README.md)
    ├── engineering-philosophy.md  # 12 universal principles
    ├── stacks/             #   Technology taste by language/framework (consulted per-project)
    ├── knowledge/          #   Cross-cutting practice (AI tools, prompting/, discovery, memory)
    ├── adr/                #   Numbered architecture decisions
    ├── developer-workflow.md  # How all the tools work together
    └── specs/              #   In-flight design specs and plans
```

---

## TODO

- [ ] **Evaluate Raycast** — Could replace both Rectangle (window management) and Flycut (clipboard manager) with a single tool. Already disabled in `macos/packages.toml`. Prioritize trying this.

---

## Philosophy

**Machine setup:**
- Idempotent — run anytime, get the same result
- Opinionated but removable — edit `macos/packages.toml` to customize
- Fast — parallel installs, skip what's already there

**Agentic config:**
- One curated kernel of rules + skills, deployed globally to every vendor — maintained in one place, no per-project linking
- Taste documented, not pushed — `docs/stacks/` is reference an agent consults per-project; nothing is force-injected
- Bless a tool and it becomes core; otherwise it stays out of the garden
