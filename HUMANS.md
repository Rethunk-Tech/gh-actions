# Using gh-actions

Shared composite GitHub Actions for the fleet — public, not Marketplace-listed. Reference an
action directly from any repo in any org:

```yaml
uses: Rethunk-Tech/gh-actions/<action>@<ref>
```

No install step, no setup on the consuming repo beyond a normal `actions/checkout` before the
`uses:` line — these are composite actions, not a CLI you run locally.

## Available actions

### `setup-bun`

Generic Bun toolchain + install + cache. No framework assumptions.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-bun@v1.5
  with:
    working-directory: frontend        # default: .
    # bun-version: "1.3.14"            # default: resolved from package.json's packageManager
    # install-args: --no-frozen-lockfile
    # node-version: "22"               # opt-in Node runtime alongside Bun
    # install-playwright: "true"
    # playwright-browsers: chromium    # scope the Playwright install; empty = install everything
```

Output: `cache-hit` — whether the Bun install-store cache was hit.

**Toolchain only, no install** — a caller with no `package.json` of its own (bun used purely
to put a `bun` binary on PATH), or one that must run `bun install` itself later after other
setup steps that have to happen first (e.g. cloning sibling repos for Bun `link:` resolution):

```yaml
- uses: Rethunk-Tech/gh-actions/setup-bun@v1.5
  with:
    skip-install: "true"     # only installs the bun binary; no lockfile check, cache, or install
```

### `setup-nextjs-bun`

Everything `setup-bun` does, plus a `.next/cache` build cache and `NEXT_TELEMETRY_DISABLED=1`.
One Next.js app per call — for a repo with multiple Next apps, call this once per app instead.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-nextjs-bun@v1.5
  with:
    working-directory: frontend
    # same optional inputs as setup-bun: bun-version, node-version, install-playwright,
    # playwright-browsers
```

**Bun workspace / monorepo**, where `bun install` must run at the workspace root but the
Next app itself lives in a subdirectory (`.next/`, source files to hash for the build-cache
key) — set `next-app-directory` separately from `working-directory`:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-nextjs-bun@v1.5
  with:
    working-directory: .                     # workspace root — bun install runs here
    next-app-directory: apps/dashboard        # the actual Next app — .next/cache lives here
```

Leave `next-app-directory` unset for a single-app repo — it defaults to `working-directory`.

Output: `cache-hit` — whether the Bun install-store cache was hit.

### `setup-go`

Go toolchain via `actions/setup-go`, with its built-in module/build cache enabled. Optionally
also runs golangci-lint and/or govulncheck as a gate on the same job — opt-in, off by default.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-go@v1.5
  with:
    go-version-file: go.mod          # default; may point into a subdir, e.g. backend/go.mod
    # go-version: "1.26.5"           # exact version instead — overrides go-version-file
    # cache-dependency-path: go.sum  # default: resolved next to go-version-file
```

Outputs: `go-version`, `cache-hit`.

**Lint + vuln gate** — both run from the same directory `go-version-file`/`cache-dependency-path`
already names (no separate `working-directory` input needed), each `continue-on-error` behind
a final gate step, so enabling both still surfaces both findings even if one fails:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-go@v1.5
  with:
    run-lint: "true"
    # lint-version: v2.12.2          # default: fleet-latest as of this writing
    # lint-args: --timeout 5m
    # lint-install-only: "true"      # only install the binary; a caller's own Makefile lints
    run-govulncheck: "true"
    # govulncheck-version: v1.7.0    # default: fleet-latest as of this writing
    # govulncheck-args: -tags=foo
```

Doesn't fit every caller — a custom JSON-output/non-fatal gating script, or a job-level
`CGO_ENABLED`/`PKG_CONFIG_PATH` build-tag requirement (job-level `env:` reaches these steps
fine; it's the invocation shape itself, e.g. raw `-json` output, that doesn't map to an input)
— those callers just leave `run-lint`/`run-govulncheck` off and keep their own step.

### Coming later

`setup-dotnet` and `upload-pages` are designed but not yet built — see [AGENTS.md](AGENTS.md)
for status.

## Pinning

Tags here are **frozen point-releases** (`v1`, `v1.1`, ... `v1.5`, each a fixed commit,
never retargeted) — not a rolling major alias the way `actions/checkout@v4` is upstream. Pin
by the latest version tag for convenience (`@v1.5`), or by commit SHA with a version comment
for maximum supply-chain hardening, matching how these actions pin their own dependencies:

```yaml
uses: Rethunk-Tech/gh-actions/setup-bun@<sha> # v1.5
```

Either way, check [the releases page](https://github.com/Rethunk-Tech/gh-actions/releases) for
the current tag — a bare `@v1` resolves to the very first `v1` commit, not the latest `v1.x`.

`repo-ops`'s `--actions-refresh-sha` sweep (Rethunk-Tech/repo-ops) keeps an existing **SHA**
pin current within a major automatically; it has nothing to act on for a bare version-tag
reference like `@v1.5` (there's no stale SHA in that reference for the sweep to find). Crossing
a major (`v1` → `v2`) needs `--actions-refresh-sha --latest`, and only ever applies to SHA
pins either way.

## Reporting a problem

Open an issue on this repo. For a security concern, see [SECURITY.md](SECURITY.md) instead of
a public issue.
