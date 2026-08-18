# Infrastructure-as-Code / Kubernetes Landscape — Watch

**Status:** OPEN / reference survey. Not an active build — a tracked view of
the IaC, Kubernetes, and GitOps tooling landscape for when infrastructure work
gets serious. No adoption decision has been made.

**Last surveyed:** 2026-08-18 · **Next review cue:** before any real
provisioning work starts, or roughly every 6 months given how fast this
category moves (license status, CNCF levels, and version numbers below are
all time-sensitive).

## The bet

**We are not building this yet.** The interest is specifically in **ArgoCD +
Kubernetes + Crossplane** as the eventual GitOps control-plane approach *if
and when* infrastructure complexity justifies it — declarative Git as the
single source of truth, Kubernetes as the reconciliation engine for
everything (apps and cloud resources alike), not just containers. This doc
exists so that decision is informed when it's actually made, without
overbuilding now. See "When would this actually make sense" at the bottom.

---

## 1. Terraform — the incumbent, now BSL and IBM-owned

- **License:** HashiCorp moved Terraform from MPL 2.0 to the Business Source
  License (BSL) 1.1 in August 2023 — it restricts building a *competing*
  product/service on top of the source, but normal use (including commercial
  internal use) is unaffected. **IBM completed its $6.4B acquisition of
  HashiCorp in early 2025**, and — despite IBM's history of open-sourcing Red
  Hat acquisitions — the BSL has **not** reverted; there's no sign it will.
- **Direction under IBM:** Project Infragraph (previewed HashiConf Sept 2025)
  ties Terraform into IBM watsonx, Red Hat Ansible, OpenShift, and IBM's
  mainframe stack — a bet on enterprise platform lock-in, not a return to
  open source.
- **Current state (2026):** Terraform CLI is at v1.14.x. Still the largest
  provider/module ecosystem and the default in most job postings and
  tutorials. The practical risk isn't "it stopped working" — it's ecosystem
  gravity shifting toward OpenTofu for anyone license-sensitive.
- **CDKTF (CDK for Terraform) is dead.** HashiCorp deprecated it
  2025-12-10 — archived, read-only, no further fixes. If "real programming
  language over infra" is the goal, that road now points to Pulumi, not
  Terraform-flavored TypeScript.

## 2. OpenTofu — the community fork, now ahead on some features

- **What it is:** MPL 2.0-licensed fork of Terraform ~1.5, governed by the
  Linux Foundation. Joined the **CNCF as a sandbox project in April 2025**.
- **Adoption:** 10M+ GitHub downloads, 3,900+ providers, 23,600+ modules
  (mid-2026 figures). Fidelity migrated 50,000+ state files to it; GitLab
  dropped its Terraform CI/CD templates in May 2025 over BSL licensing risk.
- **Where it's pulled ahead of Terraform's open binary** (as of ~v1.12,
  mid-2026): native **state encryption** (v1.7), **early variable
  evaluation** (v1.8), provider `for_each` (v1.9), `-exclude` flag (v1.9),
  OCI registry support (v1.10). These shipped in OpenTofu before Terraform.
- **Migration:** CLI-compatible near-drop-in for most Terraform configs;
  the practical blocker cited most often is perceived migration effort on an
  org-wide cutover, not technical risk — teams that migrate workspace-by-
  workspace report the smoothest path.
- **Read:** for anything new and license-sensitive, OpenTofu is the more
  defensible default over Terraform today — same HCL, same mental model,
  no BSL exposure, an active roadmap set by committee rather than one vendor.

## 3. Pulumi — infra in a real language

- **License:** Apache 2.0 core/CLI — permissive, no BSL-style restriction.
- **Positioning:** declarative *state* like Terraform, but infrastructure is
  authored in TypeScript, Python, Go, C#, or Java instead of HCL — real
  loops, functions, types, and unit tests instead of a bespoke DSL. Provider
  coverage (~4,800 claimed vs Terraform's ~1,800-2,000 in vendor benchmarks)
  is wide because Pulumi auto-generates SDKs from Terraform providers under
  the hood.
- **Why it's interesting here:** if the eventual stack leans on "real code,"
  Pulumi is the actual real-language IaC tool now that CDKTF is dead. Best
  fit for developer-led teams comfortable treating infra as software
  (tests, CI, normal package management) rather than ops-led teams that want
  a stable declarative DSL.
- **Tradeoff vs OpenTofu/Terraform:** smaller community/ecosystem, Pulumi
  Cloud (their SaaS state backend) is the easy path though self-hosted state
  backends exist, and "infra in a general-purpose language" is also a
  footgun risk (imperative logic creeping into what should stay declarative).

## 4. Crossplane — Kubernetes as the control plane

- **What it is, philosophically:** instead of a CLI that runs `plan`/`apply`
  against cloud APIs, Crossplane turns a Kubernetes cluster itself into the
  control plane. Cloud resources (an RDS instance, an S3 bucket, a VPC)
  become Kubernetes **custom resources** that a controller continuously
  reconciles — the same reconciliation loop Kubernetes uses for pods, now
  applied to your cloud account. You compose primitive resources into
  higher-level platform APIs via **Compositions** and **XRDs (Composite
  Resource Definitions)** — e.g. expose a `Database` CRD to app teams that
  internally provisions the right cloud primitives per environment.
- **Maturity:** reached **CNCF Graduated status on 2025-10-28** — the
  highest tier (same tier as Kubernetes, ArgoCD, Prometheus). 3,000+
  contributors, 500+ companies. This is a strong signal of production
  staying power, not a young experiment.
- **Crossplane v2 (2026):** namespaced XRs/MRs (was cluster-scoped only),
  can now compose *any* Kubernetes resource, not just Crossplane-managed
  cloud resources; **claims removed** for a simpler model; Activation
  Policies let you install only the CRDs you actually use instead of the
  whole provider surface.
- **This is the piece that makes ArgoCD + Crossplane coherent:** ArgoCD
  syncs Git → Kubernetes manifests as its whole job; if your cloud resources
  *are* Kubernetes manifests (via Crossplane CRDs), ArgoCD becomes the GitOps
  layer for infrastructure and applications through one mechanism, not two.

### Alternatives in the "Kubernetes as control plane for cloud" space

| Tool | Scope | Positioning |
|---|---|---|
| **AWS Controllers for Kubernetes (ACK)** | AWS only | Single-vendor operator, tracks AWS's own API surface closely, less abstraction than Crossplane's Compositions. |
| **GCP Config Connector** | GCP only | Same pattern for Google Cloud. |
| **Azure Service Operator (ASO)** | Azure only | Same pattern for Azure. |
| **kro (Kube Resource Orchestrator)** | Cloud-agnostic, object-agnostic | Newest entrant (AWS-led). Define a `ResourceGraphDefinition`, get a simple CRD that composes *existing* resources — including ACK/ASO/Config-Connector-managed cloud resources — without Crossplane's provider/Composition machinery. Lighter-weight if you just want to bundle a handful of resources behind one CR, rather than build a full internal platform API. |

**Rule of thumb:** single-cloud shop that wants minimal abstraction → the
vendor's own operator (ACK/Config Connector/ASO), optionally glued with kro.
Multi-cloud, or want a real internal platform API surface for other teams to
consume → Crossplane.

## 5. ArgoCD — the GitOps controller

- **Status:** CNCF **Graduated**, ~60% market share among GitOps tools —
  the default choice for most Kubernetes shops. Ships as an integrated
  platform: built-in web UI, centralized RBAC, single control-plane view
  across clusters. **Akuity** (founded by ex-Argo maintainers) is the
  primary commercial steward and offers a hosted/managed control plane.
- **vs Flux (the other CNCF-Graduated GitOps controller):** Flux is a
  modular toolkit of independent controllers assembled like building
  blocks — no bundled UI, lighter resource footprint (~half ArgoCD's
  CPU/memory during initial sync), closer to "the Kubernetes way." ArgoCD
  wins on developer experience, multi-cluster fleet management
  (ApplicationSets), and the polished UI; Flux wins on composability,
  native Helm handling, and running lean.
- **For the ArgoCD+Crossplane pairing specifically:** ArgoCD's
  ApplicationSets pattern (templating many `Application` objects from one
  generator) maps naturally onto "one Crossplane XRD instance per
  environment/tenant," which is likely why this combo shows up together in
  practice — it's a well-worn platform-engineering pattern, not a novel one.

## 6. Kubernetes runtimes — right-sized for where we actually are

Not every K8s conversation needs the big managed control planes. For local
dev, CI, and eventually lightweight self-hosted production:

| Tool | Best for | Notes |
|---|---|---|
| **kind** (Kubernetes-in-Docker) | Local dev / CI | Fastest spin-up/teardown; built for testing Kubernetes itself. Not for anything long-lived. |
| **k3s** (Rancher/SUSE) | Edge, small production, "just works" | Single binary, <100MB, runs on 512MB RAM, CNCF-certified. Most documentation, most battle-tested of the lightweight distros. The pragmatic default if self-hosting. |
| **k0s** (Mirantis) | Zero-dependency ops | Single binary, no external deps (no Docker required), simplicity-first design. |
| **Talos Linux** | Immutable, API-managed OS + K8s | Worth a mention for a fully declarative, SSH-less node OS — steeper learning curve, strongest security posture. |
| **Managed (EKS/GKE/AKS)** | Not operating the control plane at all | Offloads etcd/control-plane ops entirely; the default once cost/complexity of self-hosting stops paying for itself. |

## 7. Adjacent tools worth knowing, briefly

- **Ansible** — configuration management (Day 1/2: install packages, push
  config, restart services), not provisioning. Complements Terraform/
  OpenTofu rather than competing: provision with Tofu, configure with
  Ansible. Backed by Red Hat/IBM; agentless, procedural, still the default
  for config management in 2026.
- **Terragrunt** — thin DRY wrapper around Terraform/OpenTofu for managing
  many environments/modules without copy-pasted HCL. Orthogonal add-on, not
  a competitor.
- **Helm** — the Kubernetes package manager (templated YAML + values).
  Still the ecosystem default for shipping/installing apps into a cluster.
- **Kustomize** — patch-based (not templated) YAML overlays, built into
  `kubectl`. Complements or substitutes for Helm depending on taste;
  many shops use both (Helm to install, Kustomize to overlay).
- **cdk8s** — write Kubernetes manifests in TypeScript/Python/Go with
  compile-time validation, synthesizes to plain YAML. The Pulumi-style bet
  applied to K8s manifests specifically rather than cloud resources.
- **CUE / Timoni** — CUE is a constraint-based config language; Timoni is a
  CUE-powered Kubernetes package manager (a Helm alternative). Still
  pre-1.0 / early ecosystem maturity as of 2026 — interesting, not yet a
  safe default.
- **KCL (KusionStack)** — a constraint-based configuration language from
  the same lineage as CUE, backed by Kusion/ByteDance-adjacent tooling.
  Same category as CUE/Timoni: worth watching, not yet mainstream.

## 8. When would this actually make sense

The 2026 industry consensus is blunt: **Kubernetes is a complexity tax that
only pays off past a real team/scale threshold** — commonly cited around
15-20+ engineers or hundreds of workloads, and specifically *not* when the
same few people shipping features are also the ones debugging ingress. Below
that line, a managed container platform or serverless deployment target
gets equivalent reliability with a fraction of the operational surface.

That reframes the actual trigger for ArgoCD+Kubernetes+Crossplane here: not
"we have cloud resources to manage" (Terraform/OpenTofu alone handles that
fine solo), but **"we have enough distinct environments/tenants/services
that a self-service internal platform API pays for itself, and enough
people to justify owning a GitOps control plane."** Until that's true, plain
OpenTofu (or Pulumi if the team leans code-first) for cloud provisioning,
optionally a single lightweight k3s cluster for anything that's already
containerized, is the right-sized answer — and matches the standing "no
armies, own only what you need" posture from
[agent-harness-landscape.md](agent-harness-landscape.md) applied to
infrastructure instead of coding agents.

---

## Sources (primary, 2026-08)

- Terraform/BSL/IBM — [SoftwareSeni: HashiCorp, Terraform, OpenTofu and the IBM Acquisition](https://www.softwareseni.com/hashicorp-terraform-opentofu-and-the-ibm-acquisition-wild-card-for-infrastructure-as-code/), [Jorijn Schrijvershof: OpenTofu vs Terraform 2026](https://jorijn.com/en/blog/opentofu-vs-terraform-2026-the-fork-finally-diverged/)
- OpenTofu adoption/features — [env.dev: OpenTofu in 2026](https://env.dev/guides/opentofu), [Quali: Terraform and OpenTofu, where are we now](https://www.quali.com/blog/terraform-and-opentofu-where-are-we-now/)
- Pulumi — [Pulumi vs OpenTofu docs](https://www.pulumi.com/docs/iac/comparisons/opentofu/), [env zero: Terraform Alternatives in 2026](https://www.envzero.com/insights/terraform-alternatives-in-2026-opentofu-pulumi-crossplane-and-what-actually-fits-your-team)
- CDKTF deprecation — [HashiCorp Developer: terraform-cdk](https://github.com/hashicorp/terraform-cdk), [Peter Woods: CDKTF is Dead](https://peterwoods.online/blog/cdktf-is-dead)
- Crossplane graduation/v2 — [CNCF: Crossplane Graduation Announcement](https://www.cncf.io/announcements/2025/11/06/cloud-native-computing-foundation-announces-graduation-of-crossplane/), [CNCF: Crossplane project page](https://www.cncf.io/projects/crossplane/)
- Crossplane alternatives / kro — [platformengineering.org: Introducing kro](https://platformengineering.org/blog/introducing-kubernetes-resource-orchestrator-kro), [Encore: Crossplane Alternatives 2026](https://encore.dev/articles/crossplane-alternatives)
- ArgoCD vs Flux — [Akuity: Argo CD vs Flux, a 2026 Practitioner's Guide](https://akuity.io/argo-cd-vs-flux-a-detailed-comparison), [Portainer: ArgoCD vs Flux 2026](https://www.portainer.io/blog/argocd-vs-flux)
- Lightweight Kubernetes — [dasroot.net: K3s and K0s for Edge and Development](https://dasroot.net/posts/2026/04/k3s-k0s-lightweight-kubernetes-edge-development/), [sanj.dev: KiND vs K3d vs K0s](https://sanj.dev/post/kind-vs-k3d-vs-k0s/)
- Ansible/Terraform split — [Red Hat: Ansible vs Terraform](https://www.redhat.com/en/topics/automation/ansible-vs-terraform)
- Right-sizing K8s for small teams — [DigitalOcean community: Is Kubernetes overkill for small projects in 2026](https://www.digitalocean.com/community/questions/is-kubernetes-overkill-for-small-projects-in-2026), [Encore: Kubernetes Alternatives for Small Teams](https://encore.cloud/resources/kubernetes-alternatives)

*Fast-moving category — re-verify license status, CNCF levels, and version
numbers before committing to anything.*
