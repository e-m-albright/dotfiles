# Remote access: phone ⇄ laptop

How to drive the laptop's coding agents (and a terminal) from a phone over a
private network. The stack is **Tailscale** (private network) + two surfaces:

- **Paseo** — the **daily driver**: a self-hosted daemon that runs your coding
  agents (Pi, Claude Code, Codex) on the laptop, driven from a polished native
  phone app. The app connects **directly** to the daemon over the tailnet — no
  relay, no vendor cloud.
- **Zellij web client** — the **terminal fallback**: a browser terminal to the
  laptop's Zellij sessions, for when you want a raw shell instead of the agent UI.

Both are kept alive by launchd agents and fronted by the `dotfiles` CLI + the
Mission Control TUI.

## The mental model (read this first)

Everything runs **on the laptop**; the phone is a thin client over the tailnet.

- **Paseo** runs a daemon on the laptop that spawns/keeps agent sessions alive.
  The phone app is a window onto them — start an agent, walk away, pick it up
  from the phone in the same session. Multiple agents run in parallel.
- **Zellij** runs one server on the laptop. The Zellij web client is a browser
  onto its sessions; phone and laptop can attach to the **same** session at once
  (Zellij is multiplayer). A session that lives *on the phone itself* never
  exists — the phone is always a client of the laptop.
- Nothing to install on the phone but the **Tailscale** app and the **Paseo**
  app. The Zellij fallback is just a web page (installable as a PWA).

## One-time setup

### Paseo (daily driver)

1. **Install** (npm global, pinned): `npm install -g @getpaseo/cli@<version>`.
2. **Set a daemon password** (stored hashed in `~/.paseo`, never in a plist):
   `paseo daemon set-password`.
3. **Bring it up** via the CLI — `dfs remote on` installs a launchd agent
   (`com.dotfiles.paseo`, `RunAtLoad` + `KeepAlive`) that runs
   `paseo start --no-relay --listen 0.0.0.0:6767`. `--no-relay` keeps the
   Cloudflare relay **out of the path** — traffic stays pure-tailnet.
4. **On the phone:** install the **Paseo** app, then *add a daemon connection*
   directly: address = your `100.x` tailnet IP (`tailscale ip -4`) `:6767`,
   plus your daemon password. `dfs remote status` prints the address.

Because the relay is disabled there is **no QR pairing** — you add the connection
by address + password once, and it's saved. (The QR only works via the relay; we
don't use it.)

### Zellij web client (terminal fallback)

1. Ensure Tailscale is running and **HTTPS certificates** are enabled for the
   tailnet (Tailscale admin → DNS → HTTPS Certificates) — `tailscale serve` needs
   them.
2. `dfs remote on` also ensures the Zellij web launchd agent
   (`com.dotfiles.zellij-web`) is running and exposes it with
   `tailscale serve --bg 8082` (tailnet-only HTTPS — **never** `funnel`).
3. Mint a login token when you need one: `dfs remote web --new-token`.
4. On the phone, open `https://<machine>.<tailnet>.ts.net/` (or deep-link to a
   session, e.g. `…/mobile`) and enter the token. Add to Home Screen for a PWA
   icon. `dfs remote qr` prints a scannable QR of that URL.

`dfs remote on` does all of the above in one shot (and brings Tailscale up unless
`--no-tailscale`); `dfs remote off` tears down the Zellij `tailscale serve` route.
`dfs remote status` shows Tailscale / Paseo / Zellij-web state + the addresses.

## Daily use

**Paseo:** open the app, pick or start an agent (Pi, Claude Code, Codex). Sessions
persist on the laptop; reconnect any time.

**Zellij web fallback — deep-link into a session:** point your PWA icon at
`https://<machine>.<tailnet>.ts.net/<session>` to skip the landing picker. The
`mobile` deck is the natural target (Mission Control + a shell). Create it once:

```bash
zellij --session mobile --layout mobile   # detach with Ctrl-o then d; it persists
```

**Keys** (Zellij defaults — the status bar shows them live):

| Do this | Keys |
|---|---|
| Switch tabs | `Ctrl t` then `1` / `2` (or `h` / `l`) |
| New tab | `Ctrl t` then `n` |
| **Detach** (leave it running) | `Ctrl o` then `d` — or just close the tab |
| Open the session manager | `Ctrl o` then `w` |
| Quit Zellij (**ends** the session) | `Ctrl q` — avoid unless you mean it |

**Drive the Sessions pane by keyboard** (tapping is unreliable in a browser
terminal):

| Do this | Keys |
|---|---|
| Jump straight to the n-th live session | `1`–`9` |
| Move the highlight | `j` / `k` (vim) or arrows |
| Open the highlighted session's actions | `Enter` |
| New / kill / reload | `n` / `x` / `r` |

**Pick up on the laptop:** `dfs session attach mobile` (or `dfs session` to
fuzzy-pick). Same session, same panes; you can stay attached on both.

## Session lifecycle

Detaching or losing the connection **never** ends a session — it keeps running on
the laptop. The **Mission Control TUI** Sessions pane manages live sessions; every
destructive action takes a deliberate confirm.

One Zellij nuance: `kill` destroys a session (gone, not recoverable). Zellij
serializes sessions to disk and resurrects them after a **reboot**
(`dfs session attach <name>`), but there's no "stop but keep it" — treat `kill` as
permanent.

```bash
dfs session kill <name>        # kill a running session (gone — not resurrectable)
zellij delete-session <name>   # purge an exited/serialized one from history
```

## Troubleshooting

| Symptom | Check |
|---|---|
| Paseo app won't connect | Tailscale up on both? Daemon running (`dfs remote status`)? Address = `100.x:6767`? Right password? |
| Paseo relay showing | It's off (`--no-relay`) — the status line just prints the configured endpoint; traffic is direct. |
| Zellij: can't connect | Tailscale up + logged in on **both**? `dfs remote status`. Web server up? `dfs remote web`. |
| Zellij: cert warning | Open the **MagicDNS name**, not the raw tailnet IP — the `tailscale serve` cert is issued for the name. HTTPS certs enabled in the tailnet admin? |
| `tailscale serve` hangs on first run | HTTPS certificates aren't enabled for the tailnet — enable them in Tailscale admin → DNS, then retry. |
| Zellij: page won't accept the token | Mint a fresh one: `dfs remote web --new-token`. |
| Landed in a bare shell, not the deck | The `mobile` session was created without the layout. Kill it and recreate with `--layout mobile`. |
| Stop all phone access | `tailscale serve --https=443 off` (Zellij), and/or bring Tailscale down (cuts off Paseo too). |

## Zellij web client details

```bash
dfs remote web --start      # daemonized zellij web server (127.0.0.1:8082)
dfs remote web --new-token  # one-time login token (shown once)
dfs remote web --stop       # stop the server
```

It listens on `127.0.0.1:8082` only; `tailscale serve --bg 8082` publishes it to
the tailnet over HTTPS (TLS terminated by Tailscale). Read-only tokens are
available for view-only sharing.

> **Security housekeeping:** rotate login secrets periodically and revoke any that
> have been shared or pasted outside the machine. Zellij: `zellij web
> --revoke-token <name>` / `dfs remote web --new-token`. Paseo: `paseo daemon
> set-password` sets a fresh hashed password.
