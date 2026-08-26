# Remote access: phone ⇄ laptop

The mobile stack is intentionally limited to **Tailscale** plus **Paseo**:

- **Tailscale** supplies the private encrypted network and device identity.
- **Paseo** runs Pi, Claude Code, and Codex on the Mac and provides the native mobile interface for transcripts, tools, approvals, interrupts, and reconnection.

There is no phone shell, browser terminal, terminal multiplexer, Mosh layer, or Mission Control session manager. The owner does not need terminal connectivity from the phone, and Paseo already owns agent process continuity.

## Mental model

Everything runs on the Mac. Paseo desktop and mobile are clients of one local daemon reached directly over the tailnet. The relay remains disabled.

The private Notes web surface may also use Tailscale, but it is a separate productivity application and trust boundary. It does not transport or render coding-agent sessions.

## One-time setup

1. `dotfiles brew install` reconciles Paseo.app and Tailscale. The managed daemon uses the CLI bundled inside Paseo.app so the desktop and daemon protocol versions stay aligned.
2. Set a Paseo daemon password with `paseo daemon set-password`. Paseo stores only its hash under `~/.paseo`; never put the plaintext in shell history or tracked configuration.
3. Run `dfs remote on`. It brings Tailscale up and installs `com.dotfiles.paseo`, a RunAtLoad launchd agent bound to the Mac's current Tailscale IPv4 on port 6767.
4. Keep `--no-relay` enabled. The daemon fails closed when no tailnet address is available.
5. In Paseo desktop and mobile, save the daemon address printed by `dfs remote status`, plus the daemon password.

Because the relay is disabled there is no relay QR pairing. Tailscale encrypts and authenticates the network hop; the Paseo password protects the daemon protocol.

## Daily use

```bash
dfs remote status       # Tailscale, Paseo, and the direct daemon address
dfs remote on           # bring Tailscale up and ensure Paseo is running
dfs remote off          # disconnect Tailscale; local agents keep running
dfs remote paseo        # report Paseo state and address
dfs remote tailscale    # report tailnet state
```

Open Paseo on the phone, then pick or start Pi, Claude Code, or Codex. Paseo maintains the agent run on the Mac and reconnects its clients; no terminal session wrapper is involved.

## Password rotation and recovery

Rotate the daemon password when no Paseo agents are actively running:

```bash
dotfiles remote paseo --rotate-password
```

The command delegates the hidden prompt to Paseo, then reloads the launchd-managed daemon. The plaintext password never passes through dotfiles or appears in its output. Update the saved password in desktop and mobile clients afterward.

Preview without prompting or restarting:

```bash
dotfiles remote paseo --rotate-password --dry-run
```

## Troubleshooting

| Symptom | Check |
|---|---|
| Paseo app will not connect | Is Tailscale up on both devices? Is `dfs remote status` healthy? Does the saved address match the current `100.x:6767` value? Is the password current? |
| Paseo reports a relay | The managed launch command must contain `--no-relay`; run `dfs remote on` to reconcile it. |
| Daemon stopped after the Tailscale address changed | `dfs remote on` detects a stale listen address and reinstalls the launchd agent. |
| Desktop works but mobile does not | Verify the phone is on the same tailnet and points to the direct tailnet address, not localhost or a retired endpoint. |
| Stop phone access without ending agents | `dfs remote off` disconnects Tailscale while Paseo and its active agents continue locally. |

For deeper daemon, client-registry, and authentication repair, use the Workbench `paseo-management` skill. Preserve projects, workspaces, agent records, and `~/.paseo/agents`; repair only the failing layer.
