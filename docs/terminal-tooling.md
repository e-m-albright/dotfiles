# Terminal Tooling Stack

> The "terminal ergonomics renaissance" is real. Fast Rust-based replacements
> for classic Unix tools, plus agent-aware workbenches. This page maps the
> current landscape; [`macos/packages.toml`](../macos/packages.toml) is the
> source of truth for what's actually installed.

## Currently Installed (Daily Driver)

| Tool | Replaces | Notes |
|---|---|---|
| **[Ghostty](https://ghostty.org/)** | iTerm2 / Terminal.app | GPU-accelerated terminal. Improved previous-command search in 1.3.0. |
| **[Helix](https://helix-editor.com/)** (binary `hx`) | Vim/Neovim | Postmodern modal editor in Rust. Multiple selections, tree-sitter + LSP built-in, no plugin system needed. |
| **[Yazi](https://yazi-rs.github.io/)** | ranger / nnn | Async file manager in Rust. Image/PDF/video previews via Kitty graphics protocol. Native pairing with fzf/zoxide/ripgrep. |
| **[ripgrep](https://github.com/BurntSushi/ripgrep)** | `grep -r` | Recursive search that respects `.gitignore`. Fast. |
| **[fd](https://github.com/sharkdp/fd)** | `find` | Sane defaults, 5-10x speed. |
| **[fzf](https://github.com/junegunn/fzf)** | - | Fuzzy finder. The thing everything else plugs into (history, files, branches, processes). |
| **[zoxide](https://github.com/ajeetdsouza/zoxide)** | `cd` | "Smart cd" - resolves directories in <1ms by learning where you actually go. |
| **[bat](https://github.com/sharkdp/bat)** | `cat` | Syntax highlighting, Git markers, and pager support. |

## Evaluation Candidates (Not Yet Installed)

The short list (watch-only tools live in the workbench repo's
`playbook/tools-to-evaluate.md`):

- **Atuin** - searchable command-history sync via SQLite. Full-screen fuzzy search on up-arrow.
- **Zellij** - modern tmux alternative. Discoverable keybindings, YAML/KDL layouts.
- **Lazygit** - TUI for git. Faster than the CLI for hunk staging, rebasing, diffs. **Especially useful alongside AI agents** - file-level diff view gives precise control over every line before committing.
- **Lazydocker** - same idea for containers.
- **Btop** - prettier, faster htop.
- **eza** - `ls` with git status, icons, tree mode.
- **delta** - git's diff viewer rewritten: side-by-side, syntax highlighting, word-level highlights.
- **difftastic** - **structural (AST-based) diffs** that ignore reformatting noise. Devastating once you try it on a refactor PR.
- **Starship** or **oh-my-posh** - fast cross-shell prompts surfacing git, k8s context, exec time, language versions.
- **fish** - sane defaults + autosuggestions without a plugin manager.
- **sesh** - session picker fusing tmux + zoxide + fzf for one-keystroke project jumps.

## The "Yazelix" Combo

[Yazelix](https://github.com/luccahuguet/yazelix) is a reproducible terminal
IDE bundling **Yazi + Zellij + Helix** with a layout tuned for AI-assisted
work. Yazi panel for files, Helix panel for editing, Zellij for tab/split
management, with Lazygit + Claude Code as additional panes. Aspirational
target if/when committing to a fully-terminal IDE.

## Agent-Aware Workbenches

Two different bets on "what does an editor look like when you have an agent in it?"

- **[Warp](https://www.warp.dev/)** - terminal explicitly designed for multi-agent dev. Supports Codex, OpenCode, Gemini CLI as first-class threads. Vertical tabs to group agents, configurable metadata (git branch, worktrees, PR), unified notification center across agents. Send inline comments / snippets / files from Warp's code review or input directly to a running third-party agent session. **Best for juggling multiple Claude Code instances across worktrees.**
- **[Zed](https://zed.dev/)** - GPU-accelerated native editor, Vim/Helix modes, rapidly building out an agent panel with ACP (Agent Client Protocol) support, streaming thinking blocks, per-project agent threads. Less "terminal" than Warp; shares the speed-first philosophy.

If you stay fully in the terminal, the Yazelix combo + Claude Code in one pane
is the genuine "terminal IDE" today. If you want an agent-aware GUI workbench,
Warp is the most explicit bet.

## Picking a Stack

The default recommendation today:

> **Ghostty + Zellij + Helix + Lazygit + Yazi**, with Claude Code in one pane.
>
> Warp as the alternative when you want agent-aware UI affordances and
> multi-agent juggling.

This delivers: GPU-fast terminal, modern modal editing with LSP, tab/split
management, fast git operations, file management with previews, and an agent
in the loop.

## Why Rust-Based Tools Keep Winning

The pattern is consistent: every "classic Unix tool, but in Rust" has won
developer mindshare. Why:

1. **Single-binary distribution** - no Python/Ruby dependency hells.
2. **Speed measurable in the human-perception range** - 5-10x faster means "instant" instead of "perceptible pause."
3. **Sane defaults from the start** - no decades of backwards-compatibility cruft.
4. **`.gitignore` and `.git/` awareness baked in** - the common case (developer in a repo) is the default case.
5. **Cross-platform** - Linux, macOS, Windows all work without per-OS notes.

The original tools (`grep`, `find`, `ls`, `cd`, `cat`) aren't going away -
they're the lingua franca of every shell script. But the modern replacements
have become the **interactive** default for almost every dev who tries them.

## AI Code Review at the Terminal Level

Separate from the dedicated PR reviewers (see the workbench repo's
`playbook/knowledge/ai-code-review.md`):

- **Bugbot** and **Codex's review mode** are the names showing up most for ad-hoc terminal review.
- Pattern: write code with Claude Code, then pipe the diff through a different model (Codex via OpenAI CLI, or `claude code review`) for a cross-model second opinion. **The cross-model second opinion catches a surprising amount.**
- Cheapest: `git diff main | claude -p "review this for bugs"` or `gemini -p "review this diff"`.

## Resources

- [Yazi](https://yazi-rs.github.io/) | [Helix](https://helix-editor.com/) | [Ghostty](https://ghostty.org/)
- [Warp](https://www.warp.dev/) | [Zed](https://zed.dev/)
- [Yazelix](https://github.com/luccahuguet/yazelix)
- See also: [`../macos/packages.toml`](../macos/packages.toml) for what's currently installed.
