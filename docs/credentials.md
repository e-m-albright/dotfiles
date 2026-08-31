# Local credentials

Dotfiles owns the host-wide inventory and secure enrollment mechanics for local programmatic credentials. The inventory is machine-local metadata, not a secret store:

```text
~/.config/dotfiles/credentials.toml
```

It records one row per revocable grant: provider, consumer boundary, storage backend, declared scopes, expiration or rotation policy, and restoration instructions. Secret values never belong in this file or this repository.

## Storage preference

Choose the highest tier the provider and workload support:

1. **Short-lived workload identity.** Prefer federated, automatically expiring credentials for unattended software when the provider supports them.
2. **Delegated OAuth in the owning client.** Keep rotating OAuth tokens in the application or CLI that owns the authorization flow. Do not copy them into Keychain merely to centralize storage.
3. **Application-scoped static secret in macOS Keychain.** Use a separate API key for each consumer and environment. Restrict scopes, provider-side budgets, referrers, addresses, or APIs when supported.
4. **Application-private file.** Use an owner-only file only when a protocol requires a JSON artifact or rotating token cache. Set mode `0600`; keep it outside repositories.
5. **Platform secret store.** CI credentials belong in the CI platform's encrypted secret store, independently scoped per repository and environment.

Environment variables are transport, not storage. A launcher may resolve one grant and inject it into one child process, but shell profiles and launchd property lists must not contain secret literals. Durable plaintext `.env` files are prohibited.

For interactive agents, provider-supported subscription OAuth is normally preferable to a metered API key. For unattended jobs, use a dedicated workload identity or application-scoped API key unless the provider explicitly supports that OAuth grant for automation.

## Commands

```text
dotfiles credential init
dotfiles credential list
dotfiles credential list --json
dotfiles credential set google-pi
dotfiles credential link-pi google-pi
dotfiles credential run google-pi -- python local_job.py
dotfiles doctor
```

`credential set` invokes the macOS `security` prompt directly. It does not accept a secret argument, read the secret into Python, or capture terminal output. `credential link-pi` writes a command reference into Pi's private auth store, so Pi resolves the key from Keychain at use time. `credential run` removes ambient API and OAuth variables, resolves only the named grant, injects its declared environment variable into one child process, and replaces itself with that process. Launchd jobs can use this wrapper without putting a secret literal in a property list.

Edit the private TOML file to add application grants or annotate consumers, scopes, expiry, rotation, and restoration. Unknown fields and duplicate identifiers are rejected. `credential list --json` is the stable local inventory interface for other repositories.

## Isolation boundary

A key per application gives independent attribution, budget limits, rotation, and revocation. It does not create a hard process boundary: ordinary scripts running as the same macOS user can generally request the same unlocked Keychain item.

Use a separate macOS user, a signed sandboxed application with a Keychain access-control list, or a policy-enforcing credential broker when hostile-process isolation is required. Do not pretend that environment-variable naming or separate launchd property lists provide that guarantee.

## Operational rules

- Never rename a Keychain service during migration; change declarations before moving secret bytes.
- Report `stored`, not `authenticated`, unless a provider is actually queried.
- Presence checks inspect Keychain metadata and file metadata only. They do not print values or refresh OAuth grants.
- Distinguish missing credentials from an inaccessible or locked Keychain.
- Store one grant per consumer boundary rather than one shared provider key.
- Set provider-side budgets and alerts for metered API grants. Alerts are not hard spending caps unless the provider says otherwise.
