# Security Policy

This project takes a conservative stance on build and container security, and welcomes responsible disclosure.

## Container Hardening

- Non-root runtime:
  - The image creates and runs as a dedicated `namer` user instead of `root`.
  - Runtime directories (`/database`, `/cache`, `/tmp/namer`) are owned by `namer:namer` with 775 permissions.
- Stable base OS:
  - Uses standard Ubuntu 24.04 repositories; avoids "devel" channels.
- Tooling installation:
  - Python tooling is installed via `pipx` (e.g., Poetry).
  - Node is installed via the system package manager; `pnpm` is pinned (`pnpm@10.0.0`).
  - Avoids insecure patterns like `curl | bash` for tooling bootstrap.
- Build steps:
  - CI/PR builds do not push images.
  - Shell features are invoked explicitly with `bash -lc` where needed, without sourcing `~/.bashrc`.
- Health check:
  - The container includes a basic HTTP health check endpoint.

## Secrets and Logging

- API tokens (TPDB/StashDB) are expected to be supplied via environment variables or external secret stores.
- Tokens are masked in configuration serialization (`namer/configuration.py::to_dict`).
- Avoid enabling highly verbose diagnostic logging in shared environments as it may include contextual values.

## Supply Chain & Updates

- Dependabot is enabled for pip, GitHub Actions, Docker, and npm.
- We prefer minimal, pinned versions for core build tools and avoid network access in final runtime layers.

## Reporting a Vulnerability

If you discover a security issue, please do not open a public GitHub issue first.

- Email: security@rzp.one (preferred)
- Alternatively, open a GitHub Security Advisory (private) and add the maintainers.

Please include:
- A clear description of the issue and potential impact
- Steps to reproduce
- A suggested remediation if available

We will acknowledge receipt within 72 hours and provide an estimated timeline for remediation. Thank you for helping keep the ecosystem safe.
