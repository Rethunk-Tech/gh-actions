<h1 align="center">gh-actions</h1>

<div align="center">

[![CI](https://github.com/Rethunk-Tech/gh-actions/actions/workflows/ci.yml/badge.svg)](https://github.com/Rethunk-Tech/gh-actions/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/tag/Rethunk-Tech/gh-actions?label=release)](https://github.com/Rethunk-Tech/gh-actions/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

Shared composite GitHub Actions for the fleet — public, not Marketplace-listed, referenced
directly from any repo in any org via `uses: Rethunk-Tech/gh-actions/<action>@<ref>`. Built to
replace copy-pasted Bun/Next.js/Go toolchain-setup and dependency-caching boilerplate that was
drifting independently per repo across the fleet.

## Quick start

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-bun@v1.4
  with:
    working-directory: frontend
```

Full inputs/outputs, pinning practice, and the `setup-nextjs-bun` variant: [HUMANS.md](HUMANS.md).

## Highlights

- Cross-org by design — one `uses:` line works from any repo in any GitHub org, no shared
  workflow-permission config required.
- `setup-bun` resolves the Bun version from the consuming repo's own `package.json`
  `packageManager` field by default — no version to keep in sync by hand.
- `setup-nextjs-bun` adds a `.next/cache` build cache keyed exactly per Next.js's own
  documented CI caching guide (lockfile hash + source-file hash, independently invalidated).
- `setup-go` wraps `actions/setup-go`'s own module/build cache — no hand-rolled cache key to
  keep in sync with upstream's.
- `setup-go` also bundles opt-in golangci-lint/govulncheck gates, each `continue-on-error`
  behind a final gate step — enabling both still surfaces both findings even if one fails.
- Every wrapped dependency is SHA-pinned with a version comment; `repo-ops`'s
  `--actions-refresh-sha` sweep keeps pins current fleet-wide.
- Actually tested, not just schema-checked: each action runs end-to-end via `act` before a
  commit, and CI self-tests a real cold-cache-miss → warm-cache-hit round trip on every push.

## Documentation

| Doc | For |
| --- | --- |
| [HUMANS.md](HUMANS.md) | Using an action from another repo — inputs, outputs, pinning |
| [AGENTS.md](AGENTS.md) | Internals — conventions, testing, why `setup-nextjs-bun` doesn't compose `setup-bun` |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Commit style, testing before a PR, adding a new action |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting and trust boundary |

## License

[MIT](LICENSE)
