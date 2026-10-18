# Security

## Supported versions

The latest tagged release. No long-lived branches; a fix ships in the next tag.

## Reporting

GitHub **private vulnerability reporting** (Security → Report a vulnerability). Do not open a public issue first.

## In scope

- A `run:` step that interpolates a workflow input, PR title/branch, or similar into a shell as anything but an inert argument (inline `${{ }}`). Inputs must enter via `env:`.
- A wrapped-action SHA pin whose content does not match the version comment (tamper in a PR here). Upstream compromise of a wrapped action is out of scope.
- A cache key that would serve one consumer's cache to an unrelated repo/branch. GitHub scopes the cache; this repo is responsible for key construction.

## Out of scope

- Vulnerabilities in wrapped actions (`oven-sh/setup-bun`, `astral-sh/setup-uv`, `actions/setup-node`, `actions/cache`). Pins here stop an upstream compromise until a reviewed bump; disclose upstream.
- A caller feeding attacker-controlled PR content into `install-args` or `extra-cache-key`. Those are for the caller's own CI flags and hashes.
- Stale cache under a correctly-scoped key. File as an ordinary issue.
