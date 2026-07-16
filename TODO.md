# TODO

## backup posture

- No Time Machine / external drive by design - the machine is treated as
  near-stateless, restorable from cloud services and git remotes.
- If a gap ever matters: an hourly `tmutil localsnapshot` launchd agent is a free,
  no-hardware 24h undo for local file damage.

## remote command

- **Is `dfs remote on`/`off` toggling necessary, or just added security?**
  It's attack-surface reduction (defense-in-depth), not functionally required.
  - The only real gate is macOS **Remote Login** (`sshd`). All other setup persists
    across the toggle: mosh/zellij installed, phone key in `authorized_keys`,
    key-only hardening in `/etc/ssh/sshd_config.d/`, Tailscale.
  - Run `on` once and never run `off` and it keeps working. `off` just points you to
    flip Remote Login off + `pkill`s live mosh/sshd sessions.
  - Given SSH is already **key-only** (password auth off) and reachability is gated by
    **Tailscale**, leaving Remote Login on permanently is a defensible posture. The
    toggle's value scales with how untrusted the networks you're on are.
  - **Caveat to verify:** `tailscale down` does NOT stop LAN access (see
    `service.py:128` comment). So on a shared/coffee-shop Wi-Fi, anyone on the local
    network can reach `sshd` if Remote Login is on. That's the one case where toggling
    Remote Login off does real work vs. a trusted home LAN where it's just hygiene.
