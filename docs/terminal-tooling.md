# Terminal tooling

[`config/packages.toml`](../config/packages.toml) is the source of truth for installed software. Workbench owns watch lists and comparative agent-tool research.

## Current interactive stack

| Tool | Job |
|---|---|
| [Ghostty](https://ghostty.org/) | GPU-accelerated terminal |
| [Helix](https://helix-editor.com/) (`hx`) | Modal editor with built-in tree-sitter and Language Server Protocol support |
| [Yazi](https://yazi-rs.github.io/) | Async file manager and previews |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | Repository-aware content search |
| [fd](https://github.com/sharkdp/fd) | File search |
| [fzf](https://github.com/junegunn/fzf) | Interactive fuzzy selection |
| [zoxide](https://github.com/ajeetdsouza/zoxide) | Frecency-based directory navigation |
| [bat](https://github.com/sharkdp/bat) | Syntax-highlighted file and diff paging |

## Deliberate absence of a multiplexer

Zellij, tmux, and Mosh are retired. Their process-continuity and phone-shell jobs are not needed:

- Paseo owns Pi, Claude Code, and Codex process continuity and mobile rendering.
- The owner does not need arbitrary terminal connectivity from the phone.
- Ghostty tabs and ordinary shells cover local interactive work.

Do not reintroduce a multiplexer because it is conventional. Require a concrete local process that must survive terminal closure and cannot be owned by launchd, a project service, or Paseo.

## Agent workflow boundary

Agent behavior, review workflows, and tool evaluations live in the Workbench repository. This host layer supplies the terminal and command-line tools only. Cross-model review uses the harnesses directly rather than a terminal-level session manager.

Workbench's restricted terminal launchers use a native macOS sandbox; Lima is retired. Zed editing, built-in agents, and manually configured external agents remain host-authority workflows. Editor command approvals are not a repository isolation boundary because the editor itself can read files and execute requested tools outside an agent's sandbox.

Local Pi is an explicitly unrestricted workflow. The local inference service remains unchanged for its other consumers; no restricted-agent tunnel exposes that service.

Ghostty denies programmatic clipboard reads and allows programmatic writes without prompts. This keeps Pi copy actions convenient, but any terminal program can replace clipboard contents. The owner accepts that write risk; existing clipboard contents remain unreadable through this interface. These terminal escape-sequence requests (OSC 52) are performed by the host terminal, outside a child process's sandbox. After changing these settings, use **Command+Shift+Comma** or **Reload Config** in Ghostty's command palette to reload existing windows. A successful configuration check does not establish that an already-open window has loaded the new policy.

## Resources

- [Yazi](https://yazi-rs.github.io/)
- [Helix](https://helix-editor.com/)
- [Ghostty](https://ghostty.org/)
- [`../config/packages.toml`](../config/packages.toml)
