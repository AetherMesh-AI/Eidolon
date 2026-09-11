# Eidolon Security Policy

Eidolon is an independent, experimental project. Work toward a `v0.1.0` prerelease does not establish production readiness, a security audit, or a supported release series. No supported-version matrix, bounty, or response-time commitment is established here.

## Reporting a vulnerability

No private Eidolon vulnerability-reporting channel has been verified for this documentation update. Check the [repository security page](https://github.com/AetherMesh-AI/Eidolon/security) for a maintainer-published private reporting option before sharing sensitive details. The presence of this policy alone does not mean private reporting is enabled.

If no private channel is available, open a non-sensitive issue in the [Eidolon repository](https://github.com/AetherMesh-AI/Eidolon/issues) asking how to contact a maintainer privately. Do not include exploit instructions, vulnerable deployment details, private conversations, credentials, or affected user data in that request. Do not send project reports to contacts copied from the original codebase.

Once a private channel is confirmed, a useful report includes:

- A concise description, impact, and the access or prerequisites an attacker needs.
- The affected source revision or build, dirty-state information if applicable, OS, and relevant runtime versions.
- A minimal reproduction using disposable data and test accounts you control.
- The component and trust boundary involved, with file and line references where useful.
- Sanitized logs or evidence, plus any proposed mitigation.

Do not test against another person's installation or account without permission. If credentials were exposed, revoke or rotate them through the provider; removing a log or commit does not invalidate a leaked secret.

## Trust model and limits

### Host access is consequential

The runtime can execute commands and use file, browser, network, and integration tools. A locally running process can have access to resources available to its operating-system account. Do not treat the application as a sandbox or assume that choosing another agent creates an operating-system security boundary.

Use a separate OS account, container, VM, or appropriately configured remote environment when isolation is needed. Review exposed paths, network access, credentials, and execution backends. Isolating a terminal backend does not automatically contain the main application, its plugins, other tools, or inherited environment. No deployment isolation configuration is certified by this policy.

### Approvals and model instructions are not containment

External pages, files, messages, tool results, and model output can be attacker-controlled. Prompt instructions, approval dialogs, command scanners, redaction, and allowlists can reduce risk but are not an OS-level containment boundary. Do not grant broad privileges merely because a model or UI describes an action as safe.

Report concrete unintended command execution, authentication bypass, secret disclosure, unsafe rendering, or filesystem access with its actual preconditions. Do not assume a report is out of scope solely because untrusted content or a model was involved; distinguish a heuristic limitation from a breach of an enforced boundary.

### External access requires authorization

For every enabled network-facing adapter, require an explicit caller allowlist or equivalent authentication and authorization before dispatching work, resolving approvals, or returning output. Session identifiers are routing handles, not credentials. Local IPC must remain protected by OS access controls; exposing it beyond the local user requires an explicit authentication layer. These are requirements to enforce and test, not a claim that every adapter has passed review.

Do not expose experimental gateways or APIs directly to the public internet. Use appropriately configured network controls, restrict egress where needed, and run with least privilege rather than as an administrator. Separate instances and credentials are appropriate when callers require different trust levels; an agent role label does not enforce that separation.

### Prototype records are not permissions

Organization objectives, example teams, activity, local decisions, and outcomes are prototype records. Local approval does not grant runtime permissions, and a recorded outcome is not proof that work executed. Memory and cross-agent knowledge remain prototypes, not a mature access-control system. Do not rely on agent roles or apparent memory separation to protect sensitive information.

### Local storage is not a privacy guarantee

The default application data home is `~/.eidolon`; compatibility configuration can override it. A separate directory does not imply encryption, enforced profile isolation, or protection from other processes running as the same user. Configured providers and integrations may receive data when used. Review their permissions and data handling before supplying private material.

Use disposable data for experimental builds. Keep independent backups of important information, protect credentials with appropriate filesystem permissions or OS facilities, and inspect diagnostics before sharing them. Native startup and synthetic persistence evidence do not establish secure data handling across every path.

### Extensions and updates are executable trust decisions

Treat plugins, skills that invoke code, MCP servers, dependencies, installers, and update sources as code or services requiring review. Limit their credentials and privileges. A dependency pin helps identify reviewed code; it is not proof that code is safe.

Use only sources you have verified. A source repository, version label, or successful build is not proof of a signed artifact or a tested installation/update path. Installed-update recovery, data survival, complete AI conversation flows, first-attempt agent switching, and process cleanup must not be represented as accepted merely because other tests passed.

## Contributor responsibilities

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md). Security-sensitive changes should describe the boundary being enforced and include isolated tests of the real path. Never include live credentials, private profile state, or exploit-bearing user data in fixtures. Avoid logging secrets and verify exact process ownership before cleanup.

## License

The [MIT license](LICENSE), including its existing copyright, permission notice, and warranty disclaimer, remains applicable. This policy does not replace those terms.
