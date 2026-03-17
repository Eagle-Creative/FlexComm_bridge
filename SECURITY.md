# Security Policy

## Supported Versions

The latest `main` branch is actively maintained.

## Reporting a Vulnerability

Please do not disclose vulnerabilities in public issues.

Report security concerns privately to:

- `maintainers@example.com`

Include:

- Description of the issue
- Impact assessment
- Reproduction steps
- Suggested mitigation (if known)

We will acknowledge reports as quickly as possible and work on a fix before coordinated disclosure.

## Security Best Practices for This Project

- Never commit broker credentials or tokens.
- Keep production overrides out of git.
- Use TLS and authentication for non-local MQTT deployments.
