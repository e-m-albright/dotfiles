# dotfiles-cli

CLI for the dotfiles dev environment.

Run `dotfiles <command>` through the `bin/dotfiles` shim. Python commands use
the synced virtual environment when present, with `uv run` as the fallback.

Run `just` for grouped help and `just verify` for the complete project gate.
`just check` runs Python checks and tests; `just check --fast` skips tests for
pre-commit. Use `just fmt --check` to check formatting and
`just scrub --caches` to remove generated caches. `just scrub --artifacts`
deletes local working notes under the ignored documentation directories.

## Layout

Each feature owns its commands and decisions: `cli.py` renders, `service.py`
decides. Tests stay beside the modules they cover.

- `app/` assembles the command tree. `context.py` defines the runtime context
  and its accessor; `wiring.py` constructs concrete dependencies.
- `features/` groups capabilities: packages, credentials, Doctor, passwords,
  and remote access. Each feature keeps its rendering, services, and models
  together.
- `ports.py` defines effect interfaces, command results, and the credential
  storage error. `adapters/` implements process execution and Keychain access.
- `console.py` and `banner.py` handle shared presentation; `result.py` defines
  shared step results. `testing/` supplies fakes.

The `packages` feature keeps declarations and validation in `manifest.py`.
`service.py` coordinates the Homebrew, npm, Go, and special-installer modules.
Its public command names remain `brew` and `clean`; `brew upgrade` still
upgrades only Homebrew packages.

`test_architecture.py` enforces the dependency rules:

- Features cannot import application registration or dependency construction.
  Renderers can use `app.context`.
- Feature decisions and models cannot import rendering or concrete adapters.
  Adapters cannot import features; context and ports cannot construct adapters.
- Only Doctor can coordinate other features. Package backends cannot import
  their orchestrator.
- Package exports cannot shadow sibling modules. Each concept has one canonical
  source path.
