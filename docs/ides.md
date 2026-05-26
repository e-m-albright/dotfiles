# IDE Tracker

Living tracker for editors and IDE-shaped workbenches. Decisions and tradeoffs, not a build plan. Companion to [tools-to-evaluate.md](./tools-to-evaluate.md) — that doc is a wider bookmark list; this one is specifically about what we edit code in day to day.

**Last updated:** 2026-05-07

---

## At a glance

| Editor | Status | Role | Next action |
|---|---|---|---|
| **Cursor** | In use | Primary IDE — extension ecosystem, AI inline edits | Stay until something earns the switch |
| **Zed** | Installed, not adopted | GPU-native, Vim/Helix modes, ACP agent panel | **Try side-by-side with Cursor for a week** |
| **Neovim** | Not installed | Modal terminal editor, mature LSP/Treesitter, huge plugin ecosystem | **Spike a LazyVim or kickstart.nvim setup** |
| **Helix** | Installed (`hx`) | Postmodern modal editor in Rust, batteries-included (LSP/Treesitter, no plugin system). Replaces `micro` as terminal editor. | **Use as terminal editor for a week; learn modal keybindings** |
| **Yazelix** (Helix + Yazi + Lazygit + Zellij) | Partial — Helix + Yazi installed | Reproducible terminal IDE bundle, AI-tool-friendly layout | Add Zellij + Lazygit to complete bundle |
| **Warp** | Not installed | Agentic workbench — multi-agent tabs, worktree metadata, unified notifications | **High-priority revisit — capabilities expanding fast** |
| **VS Code** | Not in use | Extension parity with Cursor, no AI built-in | Skip — Cursor supersedes |

---

## Current setup

**Primary:** Cursor (`editors/cursor/{settings.json, keybindings.json, extensions.sh, mcp.json}`). Extensions tuned for SvelteKit + Python — see [`editors/EXTENSIONS.md`](../editors/EXTENSIONS.md).

**Terminal:** Ghostty (Fira Code Nerd Font) + Fish.

**Already installed but not yet load-bearing:** Zed (now managed via `macos/brew.sh` ide cask list, added 2026-05-07). `editors/zed/`-style config still pending.

---

## Highlighted: candidates to try

### Zed

GPU-accelerated, native, written in Rust. Has Vim *and* Helix modes. Rapidly building out an agent panel with ACP (Agent Client Protocol) support, streaming thinking blocks, and per-project agent threads. Open-sourced Jan 2024.

**Why try it:**
- Native-performance alternative to Cursor/VS Code; the speed difference is felt, not measured.
- Recent LSP investment for Python. See [Making Python in Zed Fun](https://zed.dev/blog/making-python-in-zed-fun).
- Built-in real-time collaborative editing (channels).
- Already installed locally — friction to test is zero.

**Cost of switching:**
- Smaller extension ecosystem (no VS Code Marketplace). If our Cursor extension stack is load-bearing, this is the binding constraint.
- Cursor's inline AI edit ergonomics are still ahead for some workflows.

**Decision rule:** spend a week editing primary projects in Zed. If extension gaps don't bite and the speed delta feels real, promote to primary.

### Neovim

Modal editor descended from Vim, with a mature Lua plugin ecosystem and first-class LSP/Treesitter/DAP. The terminal-first option that has the deepest community and the most agentic-coding integrations (Avante, CodeCompanion, claude.nvim).

**Why try it:**
- Plays naturally inside Ghostty + tmux/Zellij workflows — no app-switching tax.
- Agentic plugins are catching up fast; Neovim is a viable home for Claude Code as a side panel.
- Forces the keyboard-driven discipline that pays back across other tools (Yazi, Helix, Lazygit).

**Cost of switching:**
- Initial config investment is real even with starter distros (LazyVim, kickstart.nvim, AstroNvim).
- Inline AI edit UX is still behind Cursor and Zed; primarily competitive when paired with a side-channel agent.

**Decision rule:** scaffold a LazyVim setup, use it for a week of solo work on a low-stakes project. Promote only if it feels lighter than Cursor for routine edits.

---

## Terminal-first IDEs (from a private tech-stack evaluation)

The "terminal IDE" stack worth tracking, surfaced in a 2026-05-07 tech-stack evaluation:

- **Helix** — postmodern modal editor in Rust. Multiple selections, Treesitter and LSP built in, no plugin system needed. The "batteries included" answer to Neovim's plugin sprawl.
- **Yazi** — async file manager in Rust with image/PDF/video previews via Kitty graphics protocol. *Already installed.*
- **Lazygit** — TUI for git. Best ergonomics for staging hunks from agent batches. (Listed in that evaluation's adoption punch list as **High** priority.)
- **Zellij** — modern tmux alternative. Discoverable keybindings, layouts as YAML/KDL, plugin system.
- **[Yazelix](https://github.com/luccahuguet/yazelix)** — reproducible bundle of Helix + Yazi + Lazygit + Zellij. Layout designed for AI tools. Works locally or over SSH with zero manual setup.

**Position:** these are exploration items, not adoption recommendations. Don't install them just because they're trendy. Treat Yazelix as a one-evening experiment.

---

## Agentic workbenches

### Warp — high-priority revisit

The terminal most explicitly designed for agentic dev, and the surface area is expanding faster than anything else in this tracker. Multi-threaded development with Codex, OpenCode, Gemini CLI; vertical tabs to group agents; configurable metadata (git branch, worktrees, PRs); unified notification center across coding agents. Can send inline comments, snippets, or files from Warp to a running third-party agent session.

**Why upgraded from trigger-based to active candidate:** Warp's roadmap is moving from "AI terminal" to full agentic workbench (multi-agent orchestration, worktree-aware tabs, agent-to-agent messaging). Capabilities now exist that didn't when this was first parked — re-evaluating preemptively is cheaper than waiting for the bottleneck to bite.

**Next action:** install (uncomment in `macos/brew.sh:210`), use as primary terminal for a week alongside Ghostty, judge on (a) does the multi-agent UI actually reduce friction vs. tmux/Zellij panes, (b) does the workbench replace any Cursor/Zed surface area, (c) is the proprietary-terminal lock-in acceptable given the UX delta.

### Zed (agent panel)

Same Zed as above, doubling as a workbench. ACP support, per-project agent threads. Less "terminal" than Warp, more "editor that runs as fast as a terminal."

---

## Decision criteria

When evaluating a candidate against the current setup, weigh in this order:

1. **Speed of routine edits.** Open file → jump to symbol → edit → save. The inner loop. If it's slower or the same, the rest doesn't matter.
2. **Agent ergonomics.** How does it host Claude Code / Codex / inline AI? Cursor's bar is high here; native agent panels (Zed, Warp) and side-channel agents (Neovim plugins) have to clear it.
3. **Extension/LSP coverage** for SvelteKit, Python, Rust, Go. Anything that breaks LSP for our load-bearing languages is disqualified.
4. **Configuration portability.** Lives in this dotfiles repo, idempotent install, survives a fresh laptop. Same bar as `editors/cursor/`.
5. **Failure mode.** What happens when it crashes mid-edit? Cursor's recovery is good; new entrants need to demonstrate this.

---

## Re-evaluation triggers

- **Cursor pricing change** that materially affects the "stay" calculus → revisit Zed and Neovim seriously.
- **Cursor extension breakage** for Svelte or Python that lasts more than a week → Zed promotion candidate.
- **Multi-worktree agent juggling** becomes the daily bottleneck → already upgraded Warp to active eval; this trigger now means *adopt*, not *evaluate*.
- **A genuine terminal-only week** (e.g., remote dev, restricted laptop) → install Yazelix and use it in anger.
- **An updated tech-stack evaluation** changes the agentic-workbench section → propagate changes here.

---

## Out of scope

- VS Code (Cursor supersedes — same extensions, more AI).
- JetBrains IDEs (not currently in the stack; revisit only for languages where a JetBrains tool is materially ahead, e.g. Rust + RustRover).
- Sublime Text, TextMate, BBEdit (legacy; no agentic story).
- Emacs (acknowledged greatness; not in the candidate set for this user).

---

## Source links

- Private tech-stack & DevX evaluation (local notes) — section 4 (Agentic Dev Workbenches), section 3 (Terminal Toolkit)
- [Zed](https://zed.dev) · [Neovim](https://neovim.io) · [Helix](https://helix-editor.com) · [Yazelix](https://github.com/luccahuguet/yazelix) · [Warp](https://www.warp.dev/agents/claude-code)
- [`docs/tools-to-evaluate.md`](./tools-to-evaluate.md) — broader bookmark list, includes Zed at a higher level.
