# Security Policy

## Supported Versions

| Version | Supported          |
|---------|-------------------|
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

The AgentForge team takes security seriously. If you discover a security
vulnerability, please **do not open a public GitHub issue**.

Instead, report it privately using one of the following channels:

- **GitHub Security Advisories**: Use the "Report a vulnerability" tab under
  the repository's *Security* section.
- **Email**: security@agentforge.dev

We will acknowledge receipt within **2 business days** and aim to provide a
triage assessment within **5 business days**.

## Disclosure Process

1. Reporter submits a private advisory.
2. Maintainers confirm the issue and assess severity (CVSS v3.1).
3. A fix is developed on a private fork and a CVE is requested if warranted.
4. The advisory is published and a patched release is cut.
5. Credit is given to the reporter (unless they wish to remain anonymous).

## Security Design Principles

AgentForge is built with defense-in-depth:

- **Policy gating** at the API gateway, service, and data layers (OPA-style).
- **Multi-tenant isolation** via row-level security, namespace isolation, and
  key-prefixing.
- **PII detection & redaction** on all LLM inputs and outputs.
- **Immutable audit logs** for every state-changing action.
- **Secrets management** abstraction with rotation support.
- **Input validation** on every external boundary (Pydantic models).

## Dependency Security

- Automated dependency scanning via GitHub Dependabot.
- `pip-audit` runs in CI on every pull request.
- Container images are scanned with Trivy before release.
