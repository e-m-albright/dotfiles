# Remote Shell: phone ⇄ laptop

How to drive the laptop from a phone (or any second device) over a private
network, with sessions that survive disconnects and reboots. The stack is
**Tailscale** (private network) + **Mosh** (roaming-resilient transport) +
**Zellij** (persistent terminal sessions), fronted by the `dotfiles` CLI and the
Mission Control TUI.

## The mental model (read this first)

There is **one Zellij server, and it runs on the laptop.** The phone is a thin
client: Termius connects to the laptop over Mosh and runs everything *there*.

- Every session lives on the laptop. "Starting a session from the phone" creates
  a real session on the laptop — walk over to it later and you're in the same one.
- The phone and the laptop can attach to the **same** session at once (Zellij is
  multiplayer — each gets its own cursor). The TUI shows `👤 N attached` when more
  than one client is live.
- A session that lives *on the phone itself* does not exist. The phone is always a
  client of the laptop.

(Cross-*machine* sessions — attaching from laptop B to laptop A — are the
`dotfiles remote web` experiment, not this daily flow. See the bottom.)

## One-time setup

### On the laptop

1. **Tailscale** is installed by `install.sh`. Make sure it's running and logged in.
2. **Turn on Remote Login by hand:** System Settings → General → Sharing → **Remote
   Login**. (`dotfiles remote status` prints an `open …` shortcut that jumps straight
   to that pane.) The CLI deliberately doesn't flip this — doing it via `systemsetup`
   would require granting your terminal Full Disk Access on macOS 26+, which isn't
   worth a standing privilege grant for a one-tap toggle.
3. Authorize the phone and harden SSH — paste the phone's **public** key (generate it
   in Termius first, see below):

   ```bash
   dotfiles remote on --add-key "ssh-ed25519 AAAA... termius-phone" --harden-ssh
   ```

   This appends the key to `~/.ssh/authorized_keys` and (with `--harden-ssh`) disables
   SSH password auth so only your key works. It prints the **Tailscale IP** and the
   exact Mosh command to paste into Termius. (If Remote Login is still off, it nudges
   you back to step 2 rather than failing.)
4. Sanity-check anytime with `dotfiles remote status` — Remote Login state, Tailscale,
   and whether SSH is `key-only` or still `password allowed`.

### On the phone

1. **Tailscale** app — install, log into the **same** tailnet, confirm the laptop
   appears in the device list.
2. **Termius** app — install.
3. **SSH key** — in Termius, **Vault → Keychain** (new iOS nav puts it under the
   bottom **Vault** tab, not Settings) → **+** → generate a key. Prefer a **Face ID
   key** (Secure Enclave: the private key can't leave the phone, Face ID gates every
   connect). Copy its **public** key; that's what you pass to `dotfiles remote
   on --add-key`. (Easiest order: make the key on the phone first, then run `remote on`.)
4. **New Host** in Termius — these are GUI fields, not a pasted command. `dotfiles
   remote on` prints the exact values:
   - **Address**: the laptop's Tailscale IP (the `100.x.y.z` that `remote on` printed)
     or its MagicDNS name.
   - **Username**: your macOS username.
   - **Key**: the Termius key from step 3.
   - **Mosh**: enable it. Set the mosh-server path to `/opt/homebrew/bin/mosh-server`
     (full path — a non-login SSH session may not have `/opt/homebrew/bin` on PATH).
   - **Startup command**: `dotfiles session attach mobile`.
5. Connect. You land in the **mobile deck**.

(The `mosh --server=… -- dotfiles session attach mobile` line `remote on` prints is
the **desktop-to-desktop** form — for the `mosh` CLI on another *computer*. You don't
paste it into Termius mobile; it just shows the same values the GUI fields take.)

## Daily use

**Connecting from the phone** drops you straight into the `mobile` session:

- **Tab 1 "deck"** — already running Mission Control (`dotfiles tui`).
- **Tab 2 "shell"** — a normal shell.
- First connect ever builds the deck from the layout; after that you re-attach to
  the same running session, right where you left it.

**Keys** (Zellij defaults — the status bar shows them live):

| Do this | Keys |
|---|---|
| Switch tabs | `Ctrl t` then `1` / `2` (or `h` / `l`) |
| New tab | `Ctrl t` then `n` |
| **Detach** (leave it running) | `Ctrl o` then `d` — or just close Termius |
| Open the session manager | `Ctrl o` then `w` |
| Quit Zellij (**ends** the session) | `Ctrl q` — avoid unless you mean it |

**Pick up on the laptop:** `dfs session attach mobile` (or `dfs session` to fuzzy-pick).
Same session, same panes, same running programs. You can stay attached on both.

## Session lifecycle

Detaching or losing the connection **never** ends a session — it keeps running on
the laptop. That's the everyday safety net: close Termius, lose signal, walk away,
and `dfs session attach mobile` later picks up exactly where you left off.

The **Mission Control TUI** Sessions pane manages your live sessions: a pinned
**+ New session** row (or press `n`), and tapping any session opens an action sheet
to **Attach/switch** or **Kill** it. Every action is a deliberate tap, so a phone
misfire is harmless.

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
| Can't connect at all | Tailscale up + logged in on **both**? `dotfiles remote status`. Remote Login on? |
| SSH works, Mosh doesn't | Mosh enabled on the Termius host? mosh-server path = `/opt/homebrew/bin/mosh-server`? Mosh needs UDP — Tailscale handles the NAT traversal. |
| Key rejected | Re-run `dotfiles remote on --add-key "<public key>"`. With `--harden-ssh`, password auth is off — the key must be right. |
| Landed in a bare shell, not the deck | The `mobile` session was created without the layout (e.g. after `delete-session`). `dfs session kill mobile` then reconnect to rebuild it. |
| Want to stop all phone access | Turn **Remote Login** off in System Settings → General → Sharing (run `dotfiles remote off --kill-sessions` to also drop open Mosh/SSH sessions). |

## Web client (experiment)

Zellij can also serve sessions to a browser — no Termius, just a bookmark:

```bash
dfs remote web --start      # daemonized zellij web server
dfs remote web --new-token  # one-time login token (shown once)
```

It listens on `127.0.0.1:8082` only until you set `web_server_ip` + TLS certs in
`terminal/zellij/config.kdl` (over Tailscale, use `tailscale cert`). It's a
convenient second door (zero-install, shareable, read-only tokens), but Mosh
degrades better on flaky cell connections — **Termius/Mosh stays the primary path.**
