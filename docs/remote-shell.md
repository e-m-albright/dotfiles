# Remote Shell: phone ⇄ laptop

How to drive the laptop from a phone (or any second device) over a private
network, with sessions that survive disconnects and reboots. The stack is
**Tailscale** (private network) + **Zellij** (persistent terminal sessions) +
the **Zellij web client** (a browser, no app to install), fronted by the
`dotfiles` CLI and the Mission Control TUI.

## The mental model (read this first)

There is **one Zellij server, and it runs on the laptop.** The phone is a thin
client: a **browser** reaches the laptop's Zellij web server over the tailnet and
runs everything *there*.

- Every session lives on the laptop. "Starting a session from the phone" creates
  a real session on the laptop — walk over to it later and you're in the same one.
- The phone and the laptop can attach to the **same** session at once (Zellij is
  multiplayer — each gets its own cursor). The TUI shows `👤 N attached` when more
  than one client is live.
- A session that lives *on the phone itself* does not exist. The phone is always a
  client of the laptop.
- Nothing to install on the phone but the **Tailscale** app — the terminal is a
  web page (installable as a PWA for an app-like icon).

## One-time setup

### On the laptop

1. **Tailscale** is installed by `install.sh`. Make sure it's running and logged
   in, and that **HTTPS certificates** are enabled for your tailnet (Tailscale
   admin → DNS → HTTPS Certificates). `tailscale serve` needs them.
2. **Start the Zellij web server** (localhost only):

   ```bash
   dfs remote web --start      # daemonized zellij web server on 127.0.0.1:8082
   ```

   A launchd agent (`com.dotfiles.zellij-web`, `RunAtLoad` + `KeepAlive`) keeps it
   running across crashes and reboots, so it's there whenever you reach for it.
3. **Expose it to the tailnet** (tailnet-only HTTPS; Tailscale terminates TLS):

   ```bash
   tailscale serve --bg 8082
   ```

   This publishes `https://<your-machine>.<tailnet>.ts.net/` to your tailnet —
   **never the public internet** (that would be `tailscale funnel`, which we do
   not use). Confirm with `tailscale serve status`.
4. **Mint a login token** for the web client (shown once):

   ```bash
   dfs remote web --new-token
   ```

5. Sanity-check anytime with `dfs remote status` (Tailscale + host) and
   `dfs remote web` (server status).

### On the phone

1. **Tailscale** app — install, log into the **same** tailnet, confirm the laptop
   appears in the device list.
2. **Open the web client** in the browser:
   `https://<your-machine>.<tailnet>.ts.net/` (or deep-link straight to a session,
   e.g. `…/mobile`, to skip the picker). Enter the login token from
   `dfs remote web --new-token`.
3. **Add to Home Screen** (Share → Add to Home Screen) for an app-like PWA icon.
4. You land in the Zellij web client; open the **mobile deck** session (below).

## Daily use

**Deep-link straight into a session** — bookmark / point your PWA icon at
`https://<your-machine>.<tailnet>.ts.net/<session>` and you skip the landing
picker. The `mobile` deck is the natural target:

- **Tab 1 "deck"** — already running Mission Control (`dotfiles tui`), your
  session picker/launcher.
- **Tab 2 "shell"** — a normal shell.
- First open ever builds the deck from the layout; after that you re-attach to the
  same running session, right where you left it.

**Keys** (Zellij defaults — the status bar shows them live):

| Do this | Keys |
|---|---|
| Switch tabs | `Ctrl t` then `1` / `2` (or `h` / `l`) |
| New tab | `Ctrl t` then `n` |
| **Detach** (leave it running) | `Ctrl o` then `d` — or just close the tab |
| Open the session manager | `Ctrl o` then `w` |
| Quit Zellij (**ends** the session) | `Ctrl q` — avoid unless you mean it |

**Drive the Sessions pane by keyboard** (tapping is unreliable in a browser
terminal, so the deck is built to need neither):

| Do this | Keys |
|---|---|
| Jump straight to the n-th live session | `1`–`9` |
| Move the highlight | `j` / `k` (vim) or arrows |
| Open the highlighted session's actions | `Enter` |
| New session | `n` |
| Kill the highlighted session | `x` |
| Reload the list | `r` |

**Open pi for a project:** `dfs remote pi PROJECT` resolves an unambiguous repo
basename beneath `~/code/public` or `~/code/private`, then creates or attaches to a
project-specific Zellij session and runs `pi --continue`. Pass an absolute path when
the basename exists in both roots.

**Pick up on the laptop:** `dfs session attach mobile` (or `dfs session` to fuzzy-pick).
Same session, same panes, same running programs. You can stay attached on both.

## Session lifecycle

Detaching or losing the connection **never** ends a session — it keeps running on
the laptop. That's the everyday safety net: close the browser, lose signal, walk
away, and `dfs session attach mobile` later picks up exactly where you left off.

The **Mission Control TUI** Sessions pane manages your live sessions: a pinned
**+ New session** row (`n`), and selecting any session opens an action sheet to
**Attach/switch** or **Kill** it. On the laptop you can tap; on the phone, drive it
by keyboard (see the Sessions-pane key table above) — `1`–`9` jump straight to a
session, `j`/`k` move the highlight, `Enter` opens the actions. Every destructive
action still takes a deliberate confirm, so a misfire is harmless.

One Zellij nuance worth knowing: `kill` destroys a session (it's gone, not
recoverable). Zellij does serialize sessions to disk and can resurrect them after a
**reboot** (`dfs session attach <name>` reopens a serialized one), but there's no
on-demand "stop but keep it" — so treat `kill` as permanent.

To remove a session:

```bash
dfs session kill <name>        # kill a running session (gone — not resurrectable)
zellij delete-session <name>   # purge an exited/serialized one from history
```

## Troubleshooting

| Symptom | Check |
|---|---|
| Can't connect at all | Tailscale up + logged in on **both**? `dfs remote status`. Web server up? `dfs remote web`. |
| Browser shows a cert warning | Open the **MagicDNS name** (`<machine>.<tailnet>.ts.net`), not the raw tailnet IP — the `tailscale serve` cert is issued for the name. HTTPS certs enabled in the tailnet admin? |
| `tailscale serve` hangs on first run | HTTPS certificates aren't enabled for the tailnet — enable them in Tailscale admin → DNS, then retry. |
| Page loads but won't accept the token | Mint a fresh one: `dfs remote web --new-token` (tokens are shown once and can't be retrieved later). |
| Landed in a bare shell, not the deck | The `mobile` session was created without the layout (e.g. after `delete-session`). `dfs session kill mobile` then reopen to rebuild it. |
| Want to stop all phone access | `tailscale serve --https=443 off` (stop exposing), and/or `dfs remote web --stop`. |

## Web client details

Zellij serves sessions to a browser — no app to install, just a bookmark:

```bash
dfs remote web --start      # daemonized zellij web server (127.0.0.1:8082)
dfs remote web --new-token  # one-time login token (shown once)
dfs remote web --stop       # stop the server
```

It listens on `127.0.0.1:8082` only; `tailscale serve --bg 8082` publishes it to
the tailnet over HTTPS (TLS terminated by Tailscale — no `web_server_cert`/`key`
needed in `terminal/zellij/config.kdl`). Read-only tokens are available for
view-only sharing.

> **TODO (security housekeeping):** rotate the Zellij web login token periodically,
> and revoke any token that has been shared or pasted outside the machine (e.g. into
> a chat transcript). Tokens are tailnet-gated but long-lived until revoked:
> `zellij web --revoke-token <name>` to kill one, `dfs remote web --new-token` to mint
> a fresh one. (Pending item: rotate the token created during the initial web-client
> bring-up.)
