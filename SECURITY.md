# Security Policy

## Supported Versions

WasmDock is pre-1.0; security fixes are applied to the latest released version
and `main`.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |
| < 0.1   | ❌        |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via GitHub's
[private vulnerability reporting](https://github.com/hariharanragothaman/wasmdock/security/advisories/new)
(Security → Report a vulnerability).

Include where possible:

- A description of the vulnerability and its impact
- Steps to reproduce or a proof of concept
- Affected version(s) and environment (OS, Python, Docker version)

You can expect an acknowledgement within a few days. Once a fix is available,
we will coordinate disclosure and credit reporters who wish to be named.

## Scope

WasmDock orchestrates Docker and produces container images from templates.
Be mindful that:

- Building and running images executes code via the Docker daemon.
- `wasmdock pull` downloads images from registries you specify.

Only build and run projects/images you trust.
