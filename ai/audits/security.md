---
name: audit-security
description: OWASP-style security audit — injection, broken authz/IDOR, secrets in code, unsafe deserialization, SSRF, missing authn, timing-unsafe comparisons, ReDoS
---

# Security Audit: Injection, AuthZ, Secrets, and Unsafe Inputs

You are auditing this codebase for security defects in the OWASP tradition. Serves **P4 (Boundaries are contracts)** — every external input is untrusted until validated at the edge, and trust inside is earned by that validation.

## What to look for

### Injection
- String-concatenated SQL, shell, or template strings built from user input instead of parameterized queries / argument arrays
- `eval`, `exec`, `os.system`, `child_process.exec`, dynamic `import()` driven by request data
- Unescaped user data flowing into HTML, log formats, or LDAP/XML/NoSQL queries

### Broken Authorization / IDOR
- Endpoints that read an object by ID without checking the caller owns or may access it
- Authorization decided on the client, or trusting a role/tenant field from the request body
- Missing tenant/scope filters in queries (a `WHERE id = ?` with no `AND owner = ?`)

### Secrets in Code
- API keys, tokens, private keys, passwords, connection strings hardcoded or committed
- Secrets in default config, test fixtures, or example files that look real
- Logging that prints credentials, tokens, or full request bodies

### Unsafe Deserialization
- `pickle`, `yaml.load` (non-safe), `Marshal`, native-object deserializers on untrusted bytes
- Type confusion from JSON parsed straight into privileged structures without validation

### SSRF & Outbound Requests
- Server-side fetches to a URL/host taken from user input without an allowlist
- Webhook, image-proxy, or URL-preview features that can reach internal addresses/metadata endpoints

### Missing Authentication
- Routes, handlers, or admin/debug endpoints with no authn check
- Auth middleware applied per-route in a way that's easy to forget on a new endpoint

### Timing-Unsafe Comparisons & ReDoS
- Token/HMAC/password comparison with `==` instead of a constant-time compare
- User-controlled input matched against catastrophically-backtracking regexes

## How to report

For each finding: `file:line`, the vulnerability class, **severity** (critical / high / medium), the concrete exploit path, and the fix (parameterize, add the authz check, move the secret to env/secret store, use a safe loader/allowlist/constant-time compare). NEVER auto-apply a fix or commit a change.

Findings open an issue or a draft PR for human review. Never auto-merge, and never auto-apply a generative refactor.
