# Work Profile Data-Flow Registry

Last reviewed: 2026-09-22. This registry describes the intended `work` profile in
`macos/packages.toml`; it is not company approval. Account settings, enterprise
contracts, device-management controls, repository hooks, and live network
traffic were not inspected.

A tool is not private merely because its executable runs locally. The relevant
boundary is what it can read, what it transmits in the selected mode, who
receives that transmission, and which contract governs retention and use.
Likewise, a networked tool does not necessarily upload source code.

## Required decisions before use

1. Approve Homebrew and its explicit package allowlist.
2. Select the company-approved Claude Code authentication route and terms.
3. Select and enforce Pi's model provider; the work profile intentionally
   declares no provider.
4. Decide whether Zed telemetry, collaboration, extensions, edit prediction,
   built-in AI, and ACP agents are allowed.
5. Confirm the approved Git host, AWS accounts, Terraform state and execution
   backends, container runtime, registries, and personal-account applications.
6. Approve local clipboard history, accessibility permissions, microphone access,
   and downloaded dictation models before enabling Flycut, Rectangle, or TypeWhisper.

Until those decisions are recorded, installation approval must not be treated
as approval to send company data through every installed feature.

## Registry

| Surface and permitted mode | Data available to the tool | External recipients in that mode | Intended control and current state |
| --- | --- | --- | --- |
| **Claude Code** through an approved commercial account, API, Amazon Bedrock, or Vertex AI route | Prompts, selected source and diffs, repository metadata, tool output, local transcripts, and credentials exposed to its process | Anthropic or the configured cloud model provider; optional feedback recipients | **Pending provider approval.** Commercial terms can prohibit model training, but processing and retention still depend on the actual route and contract. Do not use a personal consumer account for company source. Workbench blocks named sensitive paths but is not an information-flow boundary. |
| **Pi** with an explicitly approved provider | Prompts, selected source, repository metadata, tool results, transcripts, and provider credentials | The configured model provider | **Blocked pending provider selection.** `agents/profiles/work/pi/models.json` contains no provider, and the work profile excludes personal connectors and local-model routing. Record provider, account class, retention, and training terms before use. |
| **Zed local editing** without collaboration or AI features | Open files, project paths, diagnostics, extensions, and editor state | Zed may receive enabled metrics or crash diagnostics; extensions and language servers may contact their own services | **Pending editor approval and live-settings review.** The installer deliberately does not deploy personal Zed settings. Review telemetry and every extension before opening company repositories. |
| **Zed AI, edit prediction, collaboration, or ACP** | Prompts, selected code context, repository context, collaboration content, and agent tool output | Zed and its hosted providers, a directly configured provider, gateway providers, collaborators, or the ACP agent's provider, depending on the feature | **Off until separately approved.** Each request path has different recipients and terms. Installing Zed does not approve these features. |
| **Git and Git LFS, local operations** | Working tree, commits, history, configured hooks, and large-file pointers or objects | None from Git itself; hooks may invoke networked commands | **Local use allowed after tool approval.** The work profile does not install personal Git, SSH, identity, credential, or remote configuration. Inspect repository hooks before running them. |
| **Git, Git LFS, and `gh`, remote operations** | Commits, source, branches, repository metadata, large files, pull requests, issues, workflow inputs, and credentials | The configured Git host, GitHub, and any workflow integrations | **Use only company-approved remotes and accounts.** A push intentionally transfers the selected history and content. |
| **AWS CLI** against approved company accounts | AWS credentials, request parameters, resource identifiers and values, command output, and explicitly uploaded artifacts | AWS service endpoints and configured proxies or identity providers | **Pending account and credential-flow approval.** It does not upload local source unless a command or child tool requests that upload. Avoid secrets on command lines and in shell history. |
| **Terraform through tenv, local execution** with an approved local or remote state backend | Terraform configuration, provider arguments, variables, outputs, state, credentials, and local files read by providers | Provider APIs, the selected state backend, module and provider registries; HashiCorp release endpoints when tenv installs Terraform | **Pending backend and provider approval.** Pin project versions with `.terraform-version` or `required_version`. Treat state and plans as sensitive even when source execution is local. |
| **Terraform remote execution** | Configuration archive, variables, plans, logs, state, and workspace metadata | Terraform Cloud or the configured remote-execution service and its subprocessors | **Off until explicitly approved.** Remote execution has a materially different data boundary from a local run. |
| **OrbStack and `docker compose`** with approved images and registries | Mounted source, environment variables, image layers, registry credentials, volumes, and workload traffic | Image registries, OrbStack licensing/update services, and every endpoint contacted by running workloads | **Pending runtime and license approval.** OrbStack supplies Compose; the work profile does not install a duplicate `docker-compose` formula. Review Compose files, mounts, environment files, and images per repository. |
| **Homebrew** with the work allowlist | Requested formulae and casks, host and network metadata, and installer output | Homebrew and package download hosts, including GitHub and vendor CDNs | **Pending package-manager approval.** `HOMEBREW_NO_ANALYTICS=1` is set before installation and in interactive shells. The work allowlist is fail-closed, but downloaded packages still execute vendor code. |
| **uv and Python** for managed runtimes and project environments | Python version requests, dependency names and versions, project lockfiles, registry credentials, and package build inputs | Python runtime download hosts and configured package indexes | **Allowed only through approved indexes.** Python 3.14 is uv-managed; project dependencies belong in locked uv environments, not a shared global environment. Package build scripts can execute code. |
| **fnm, Node, and npm** for Node LTS and pinned Pi installation | Runtime and package version requests, npm configuration and credentials, package lifecycle-script inputs | Node and npm download infrastructure or configured private registries | **Allowed only through approved registries.** Global packages use `~/.npm-global` so fnm upgrades do not change ownership. npm lifecycle scripts can execute code during installation. |
| **Deno** running trusted project commands | Files and environment exposed by granted permissions, imported code, dependency metadata, and runtime arguments | Imported module hosts, package registries, and endpoints allowed by the command's network permissions | **Per-project review required.** Deno permission prompts help constrain access but do not make a granted network operation private. |
| **Workbench bootstrap, sync, and drift** | Public checkout metadata and local agent configuration | GitHub during a fresh clone; sync and drift otherwise operate locally | **Repository approval required.** A fresh work checkout is pinned to a reviewed commit. Workbench excludes personal MCP servers, browser and productivity connectors, Codex, external skills, and local-model routing from the work profile. |
| **Oh My Zsh bootstrap** | Shell environment and the enabled plugin configuration | GitHub during the pinned install; automatic updates are disabled on work hosts | **Included as part of shell approval.** Only the minimal Git plugin is enabled. Repository or local shell code can still execute arbitrary commands. |
| **Spotify** | Account identity, listening history, device information, network metadata, and application telemetry | Spotify and its subprocessors | **Pending personal-account application approval.** It has no intended access to source code, but installation and personal sign-in are separate policy decisions. |
| **Rectangle, Flycut, Caffeine, and f.lux** | Rectangle can observe window and accessibility state; Flycut stores copied clipboard content locally; Caffeine controls idle sleep; f.lux observes time and display state | None in their intended local modes, excluding installation and update traffic | **Pending host-utility approval.** Do not grant Accessibility to Rectangle or enable Flycut clipboard history until local storage of company window and clipboard data is approved. The work profile installs these apps but does not add login items. Caffeine is Intel-only and may require Rosetta. |
| **TypeWhisper local dictation** | Microphone audio, local transcripts, selected model files, and text inserted into the focused application | Model and update download hosts during installation or updates; no intended speech recipient during local transcription | **Pending microphone and local-model approval.** Confirm the selected model and live network behavior before dictating company information. Keep transcripts out of clipboard history when that combination is not approved. |
| **Ghostty** as a terminal | Visible terminal content, clipboard actions, and child-process input and output | None from normal terminal rendering; child processes retain their own network access | **Local by default.** Treat terminal integrations and executed commands separately. |
| **`jq`, `yq`, `ripgrep`, `fd`, `fzf`, `bat`, `zoxide`, `shellcheck`, `git-delta`, and `gitleaks`** | Files, paths, source, history, and potentially secrets selected for inspection | None in their intended local modes, excluding installation and update traffic | **Local by default.** This classification does not cover compromised binaries or wrappers that send their output elsewhere. |
| **`just` and Lefthook** | Whatever files, credentials, and environment their repository-owned recipes and hooks can access | Any recipient invoked by those recipes or hooks | **Treat repository configuration as executable code.** Review recipes and hooks before running them in an unfamiliar checkout. |

## Explicitly excluded from the work profile

Codex, Claude Desktop configuration, MCP servers, browser and personal
connectors, externally downloaded skills, Paseo, Tailscale, local model runners,
Go, Rust, personal Git and SSH configuration, and personal Zed settings are not
part of the work installation. Semgrep is also excluded pending alignment with
the company's approved static-analysis platform.

For Semgrep specifically, Community Edition scans can remain local. Semgrep
states that local-rule scans do not enable metrics, while Registry rules,
authenticated `semgrep ci`, Pro features, AppSec Platform reporting, and
AI-powered detection introduce different network and data-processing paths.
Approval must name the permitted mode rather than merely the product.

## Verification procedure

For every approval or material configuration change:

1. Record the product, feature mode, account class, destination, retention,
   training terms, subprocessors, and approving owner.
2. Confirm the deployed configuration and authentication route on the machine.
3. Run a synthetic repository with marker data through the intended workflow.
4. Observe destinations through the company-approved firewall or proxy. Network
   observation confirms endpoints, not encrypted request contents.
5. Compare observed behavior with vendor documentation and the enterprise
   agreement. Resolve discrepancies before using real company data.
6. Recheck after major upgrades, provider changes, enabling extensions, or
   moving from local to CI or remote execution.

Keep secrets out of test markers, prompts, logs, and this registry. See
[`privacy-data-hygiene.md`](privacy-data-hygiene.md) for provider retention and
host-hygiene guidance.

## Sources

- [Anthropic: Claude Code data usage](https://docs.anthropic.com/en/docs/claude-code/data-usage)
- [Anthropic: Claude Code installation methods](https://code.claude.com/docs/en/installation)
- [Zed: AI privacy and request paths](https://zed.dev/docs/ai/privacy-and-security)
- [Zed: telemetry](https://zed.dev/docs/telemetry)
- [Semgrep: metrics](https://semgrep.dev/docs/metrics)
- [Semgrep: Code overview](https://semgrep.dev/docs/semgrep-code/overview)
- [tenv documentation](https://tofuutils.github.io/tenv/)
- [HashiCorp: verifying Terraform binary archives](https://developer.hashicorp.com/terraform/tutorials/cli/verify-archive)
- [OrbStack privacy policy](https://docs.orbstack.dev/legal/privacy)
- [OrbStack subprocessors](https://docs.orbstack.dev/legal/subprocessors)
