# Terminal tooling

[`macos/packages.toml`](../macos/packages.toml) is the source of truth for installed software. Workbench owns watch lists and comparative agent-tool research.

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

## Resources

- [Yazi](https://yazi-rs.github.io/)
- [Helix](https://helix-editor.com/)
- [Ghostty](https://ghostty.org/)
- [`../macos/packages.toml`](../macos/packages.toml)
