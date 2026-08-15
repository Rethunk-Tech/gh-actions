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
- uses: Rethunk-Tech/gh-actions/setup-bun@v1
  with:
    working-directory: frontend        # default: .
    # bun-version: "1.3.14"            # default: resolved from package.json's packageManager
    # install-args: --no-frozen-lockfile
    # node-version: "22"               # opt-in Node runtime alongside Bun
    # install-playwright: "true"
    # playwright-browsers: chromium    # scope the Playwright install; empty = install everything
    # extra-cache-paths: |             # an additional cache, independently keyed
    #   frontend/.some-build-cache
    # extra-cache-key: ${{ hashFiles('frontend/**/*.ts') }}
    # extra-cache-restore-key-fragment: ${{ hashFiles('frontend/bun.lock') }}
```

Output: `cache-hit` — whether the Bun install-store cache was hit.

**Toolchain only, no install** — a caller with no `package.json` of its own (bun used purely
to put a `bun` binary on PATH), or one that must run `bun install` itself later after other
setup steps that have to happen first (e.g. cloning sibling repos for Bun `link:` resolution):

```yaml
- uses: Rethunk-Tech/gh-actions/setup-bun@v1
  with:
    skip-install: "true"     # only installs the bun binary; no lockfile check, cache, or install
```

### `setup-nextjs-bun`

Everything `setup-bun` does, plus a `.next/cache` build cache and `NEXT_TELEMETRY_DISABLED=1`.
One Next.js app per call — for a repo with multiple Next apps, call this once per app instead.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-nextjs-bun@v1
  with:
    working-directory: frontend
    # same optional inputs as setup-bun: bun-version, install-args, node-version,
    # install-playwright, playwright-browsers
```

**Bun workspace / monorepo**, where `bun install` must run at the workspace root but the
Next app itself lives in a subdirectory (`.next/`, source files to hash for the build-cache
key) — set `next-app-directory` separately from `working-directory`:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-nextjs-bun@v1
  with:
    working-directory: .                     # workspace root — bun install runs here
    next-app-directory: apps/dashboard        # the actual Next app — .next/cache lives here
```

Leave `next-app-directory` unset for a single-app repo — it defaults to `working-directory`.

Output: `cache-hit` — whether the Bun install-store cache was hit.

### `setup-go`

Go toolchain via `actions/setup-go`, with its built-in module/build cache enabled.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-go@v1
  with:
    go-version-file: go.mod          # default; may point into a subdir, e.g. backend/go.mod
    # go-version: "1.26.5"           # exact version instead — overrides go-version-file
    # cache-dependency-path: go.sum  # default: resolved next to go-version-file
```

Outputs: `go-version`, `cache-hit`.

### Coming later

`setup-dotnet` and `upload-pages` are designed but not yet built — see [AGENTS.md](AGENTS.md)
for status.

## Pinning

Pin by tag (`@v1`) for convenience, or by commit SHA with a version comment for maximum
supply-chain hardening, matching how these actions pin their own dependencies:

```yaml
uses: Rethunk-Tech/gh-actions/setup-bun@<sha> # v1.0.0
```

`repo-ops`'s `--actions-refresh-sha` sweep (Rethunk-Tech/repo-ops) keeps a SHA pin current
within a major automatically; crossing a major (`v1` → `v2`) needs
`--actions-refresh-sha --latest`.

## Reporting a problem

Open an issue on this repo. For a security concern, see [SECURITY.md](SECURITY.md) instead of
a public issue.
