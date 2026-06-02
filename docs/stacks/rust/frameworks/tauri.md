# Tauri 2

> Cross-platform desktop apps with a Rust backend and a web frontend. Read with [../README.md](../README.md) for the underlying language taste. Picked over Electron (heavy, not Rust).

## Stack

```yaml
Framework:   Tauri 2 (Rust backend + web frontend)
Frontend:    SvelteKit or plain Svelte
IPC:         Tauri commands (invoke) + events
State:       Managed state via tauri::State
Plugins:     Tauri plugin ecosystem (fs, dialog, shell, etc.)
```

## Commands (Rust ↔ frontend IPC)

- Define with the `#[tauri::command]` attribute.
- Register in `Builder::new().invoke_handler(tauri::generate_handler![...])`.
- Call from the frontend: `import { invoke } from '@tauri-apps/api/core'`.
- Commands can be `async` and return `Result<T, E>`.
- Access managed state via `state: tauri::State<'_, AppState>`.

## State management

- Register state with `.manage(AppState::new())` in the builder.
- Use `Arc<Mutex<T>>` or `Arc<RwLock<T>>` for mutable shared state.
- Access in commands via the `State<'_, T>` extractor.

## Events

- Emit from Rust: `app.emit("event-name", payload)`.
- Listen in the frontend: `listen("event-name", callback)`.
- Use for push updates, progress reporting, and background task results.

## Security

- Configure the `allowlist` in `tauri.conf.json` — **deny by default**.
- Validate all IPC inputs on the Rust side.
- Use CSP headers for the webview.

## Structure

```
src-tauri/
  src/main.rs              — Tauri app setup, command registration
  src/commands/            — #[tauri::command] handlers
  src/state.rs             — managed state types
  Cargo.toml               — Rust dependencies
  tauri.conf.json          — Tauri configuration
src/                       — Frontend (SvelteKit/Svelte)
```

## Commands

```bash
just dev                   # Start Tauri dev mode (frontend + backend)
just build                 # Build distributable
cargo tauri icon           # Generate app icons from a source image
```
