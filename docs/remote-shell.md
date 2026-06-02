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
2. Authorize the phone and turn on remote access — paste the phone's **public** key
   (generate it in Termius first, see below):

   ```bash
   dotfiles remote on --add-key "ssh-ed25519 AAAA... termius-phone" --harden-ssh
   ```

   This enables macOS Remote Login, appends the key to `~/.ssh/authorized_keys`,
   and (with `--harden-ssh`) disables SSH password auth so only your key works.
   It prints the **Tailscale IP** and the exact Mosh command to paste into Termius.
3. Sanity-check anytime with `dotfiles remote status` (Remote Login + Tailscale state).

### On the phone

1. **Tailscale** app — install, log into the **same** tailnet, confirm the laptop
   appears in the device list.
2. **Termius** app — install.
3. **SSH key** — in Termius, Keychain → generate a new key (ed25519). Copy its
   **public** key; that's what you pass to `dotfiles remote on --add-key` above.
   (Easiest order: make the key on the phone first, then run `remote on`.)
4. **New Host** in Termius:
   - **Address**: the laptop's Tailscale IP (the `100.x.y.z` that `remote on` printed)
     or its MagicDNS name.
   - **Username**: your macOS username.
   - **Key**: the Termius key from step 3.
   - **Mosh**: enable it. Set the mosh-server path to `/opt/homebrew/bin/mosh-server`.
   - **Startup command**: `dotfiles session attach mobile`
     (or paste the full command `dotfiles remote on` printed).
5. Connect. You land in the **mobile deck**.

## Daily use

**Connecting from the phone** drops you straight into the `mobile` session:

- **Tab 1 "deck"** — already running Mission Control (`dotfiles tui`).
- **Tab 2 "shell"** — a normal shell.
- First connect ever builds the deck from the layout; every connect after
  resurrects your exact last state.

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

## Session lifecycle (and how resurrection actually works)

Detaching or losing the connection **never** ends a session — it keeps running on
the laptop. That's the everyday safety net: close Termius, lose signal, walk away,
and `dfs session attach mobile` later picks up exactly where you left off.

Resurrection is a separate, narrower thing, and it's worth being precise because
it's easy to assume it's more on-demand than it is:

- Zellij **serializes** every session to disk (`session_serialization true`). When
  the Zellij **server stops while sessions are serialized — i.e. a reboot** — those
  sessions reappear as **EXITED / resurrectable**. `dfs session attach <name>` (or
  Restore in the TUI) brings one back: its panes and the commands that were running,
  behind a `press ENTER to run` guard so nothing destructive auto-fires.
- This is mainly a **reboot survivor**, not an on-demand stop/start. There is **no
  command to gracefully park a single running session into the resurrectable state** —
  `kill`/`delete` (below) destroy a session, they don't hibernate it.

So the realistic loop is: reboot the Mac → your sessions are waiting in the
**RESURRECTABLE** group → tap Restore. Day to day you just detach and re-attach.

In the **Mission Control TUI** the Sessions pane is a manager: a pinned
**+ New session** row (or press `n`), and tapping any row opens an action sheet —
Attach/switch a live one, **Kill** it (permanent), or **Restore/Delete** one from
the **RESURRECTABLE** group. Every action is a deliberate tap, so a phone misfire
is harmless.

To remove a session for good:

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
| Want to stop all phone access | `dotfiles remote off --kill-sessions` (disables Remote Login and drops open Mosh/SSH sessions). |

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
