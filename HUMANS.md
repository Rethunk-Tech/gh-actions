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
- uses: Rethunk-Tech/gh-actions/setup-bun@v1.11
  with:
    working-directory: frontend        # default: .
    # bun-version: "1.4.0"            # default: resolved from package.json's packageManager
    # install-args: --no-frozen-lockfile
    # node-version: "22"               # opt-in Node runtime alongside Bun
    # install-playwright: "true"
    # playwright-browsers: chromium    # scope the Playwright install; empty = install everything
    # playwright-directory: apps/web  # where the Playwright version is pinned and browsers
    #                                 # install; defaults to working-directory
```

Outputs: `cache-hit` — whether the Bun install-store cache was hit. `playwright-cache-hit`
and `playwright-version` are set when `install-playwright` is on (`playwright-version` is
`unpinned` if no package.json at `playwright-directory` names a pin).

`install-playwright` skips `playwright install-deps` when the only missing system packages are
fonts, which on `ubuntu-latest` is always the case for Chromium. A repo that asserts pixel
snapshots of CJK or Thai text in CI should install those fonts itself. Combined with
`skip-install`, browsers still install: the CLI is `bunx playwright@<pin>` from
`playwright-directory`'s package.json, not an unpinned `bunx playwright`.

**Caching a build directory too** — a path the repo owns that should not be keyed on the
lockfile, such as a Turborepo `.turbo`. Both inputs are required for the cache to run at all;
leaving the restore fragment empty restores from any previous extra cache for this OS, which
is what a SHA-keyed cache wants because its key never repeats:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-bun@v1.11
  with:
    extra-cache-paths: .turbo
    extra-cache-key: ${{ github.sha }}
    # extra-cache-restore-key-fragment: ""   # default: match any earlier extra cache
```

**Toolchain only, no install** — a caller with no `package.json` of its own (bun used purely
to put a `bun` binary on PATH), or one that must run `bun install` itself later after other
setup steps that have to happen first (e.g. cloning sibling repos for Bun `link:` resolution):

```yaml
- uses: Rethunk-Tech/gh-actions/setup-bun@v1.11
  with:
    skip-install: "true"     # only installs the bun binary; no lockfile check, no bun install.
                             # The install-store cache still runs whenever a bun.lock is
                             # present, so a caller that installs later keeps the cache.
```

### `setup-nextjs-bun`

Everything `setup-bun` does, plus a `.next/cache` build cache and `NEXT_TELEMETRY_DISABLED=1`.
One Next.js app per call — for a repo with multiple Next apps, call this once per app instead.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-nextjs-bun@v1.11
  with:
    working-directory: frontend
    # same optional inputs as setup-bun: bun-version, node-version, install-playwright,
    # playwright-browsers, playwright-directory, extra-cache-paths, extra-cache-key,
    # extra-cache-restore-key-fragment
```

**Bun workspace / monorepo**, where `bun install` must run at the workspace root but the
Next app itself lives in a subdirectory (`.next/`, source files to hash for the build-cache
key) — set `next-app-directory` separately from `working-directory`:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-nextjs-bun@v1.11
  with:
    working-directory: .                     # workspace root — bun install runs here
    next-app-directory: apps/dashboard        # the actual Next app — .next/cache lives here
```

Leave `next-app-directory` unset for a single-app repo — it defaults to `working-directory`.

Outputs: `cache-hit` — whether the Bun install-store cache was hit. Same Playwright
outputs as `setup-bun` when `install-playwright` is on.

### `setup-go`

Go toolchain via `actions/setup-go`, plus a module/build cache keyed per job. Optionally also
runs golangci-lint and/or govulncheck as a gate on the same job — opt-in, off by default.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-go@v1.11
  with:
    go-version-file: go.mod          # default; may point into a subdir, e.g. backend/go.mod
    # go-version: "1.26.5"           # exact version instead — overrides go-version-file
    # cache-dependency-path: "**/go.sum"  # default: the go.sum next to go-version-file, plus go-version-file
```

Outputs: `go-version`, `cache-hit` (an exact key match for this job).

The cache key is Go version + dependency hash + job id, so a `lint` job and a `go test -race` job
each restore the build cache they filled themselves. A job's first run, or a dependency bump,
falls back to the newest cache any job saved for the same Go version. Matrix legs share one job
id and therefore one cache entry.

**Lint + vuln gate** — both run from the same directory `go-version-file`/`cache-dependency-path`
already names (no separate `working-directory` input needed), each `continue-on-error` behind
a final gate step, so enabling both still surfaces both findings even if one fails:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-go@v1.11
  with:
    run-lint: "true"                 # Linux and macOS runners; binary checksum-verified per run
    # lint-version: v2.13.2          # default: built with go1.27, matching the fleet's modules
    # lint-args: --timeout 5m
    run-govulncheck: "true"
    # govulncheck-version: v1.7.0    # default: fleet-latest as of this writing
    # govulncheck-args: -tags=foo
```

Doesn't fit every caller — a custom JSON-output/non-fatal gating script, or a job-level
CGO_ENABLED/PKG_CONFIG_PATH build-tag requirement (job-level `env:` reaches these steps
fine; it's the invocation shape itself, e.g. raw `-json` output, that doesn't map to an input)
— those callers just leave `run-lint`/`run-govulncheck` off and keep their own step.

### `setup-python`

uv + a Python interpreter via `astral-sh/setup-uv`, with its dependency cache enabled, then
`uv sync`. Optionally also runs ruff and/or `uv audit` as a gate on the same job — opt-in, off
by default.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-python@v1.11
  with:
    # python-version: "3.14"          # default: resolved from .python-version / requires-python
    # uv-version: "0.11.28"           # default: from pyproject.toml/uv.toml, else latest
    # working-directory: host         # default: .
    # install-args: --locked --group dev   # default: --locked (REPLACES, does not append)
```

Outputs: `uv-version`, `python-version`, `cache-hit`.

`python-version` selects the interpreter by exporting `UV_PYTHON`; it does not install one
itself. uv downloads a managed interpreter when `uv sync`/`uv run` needs it, so this is
invisible to most callers — but a step that runs with networking disabled must still do its
own `uv python install <ver>` first.

`install-args` replaces the default rather than appending to it, so keep `--locked` in the
value — it fails on a stale `uv.lock` instead of silently re-resolving it. The lint gate below
needs ruff present in the synced environment, which for most repos means adding `--group dev`.

**Lint + audit gate** — each `continue-on-error` behind a final gate step, so enabling more
than one still surfaces every finding even if an earlier one fails:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-python@v1.11
  with:
    install-args: --locked --group dev
    run-ruff: "true"
    # ruff-paths: "bench/ tests/"     # default: .   (shared by both ruff steps)
    # ruff-args: --select=E,F          # extra flags for `ruff check` only
    run-ruff-format: "true"            # separate input: most callers lint without enforcing
                                       # ruff's formatter, and one input for both would fail
                                       # every repo that has only ever run `ruff check`
    run-audit: "true"
    # audit-args: --locked             # default; audits uv.lock, so a pinned-but-uninstalled
    #                                  # extra carrying an advisory still fails
```

`uv audit` is still marked experimental upstream and may change without warning — that is why
`run-audit` is opt-in rather than on by default.

**Toolchain only, no sync** — a caller with no project of its own, using uv purely to put `uv`
and `uvx` on PATH for a standalone tool:

```yaml
- uses: Rethunk-Tech/gh-actions/setup-python@v1.11
  with:
    skip-install: "true"     # only installs uv and the interpreter; no uv sync. The cache is
                             # still restored and saved.
```

### `setup-rust`

A Rust toolchain from the runner's preinstalled rustup, plus a cargo registry and `target/`
cache keyed per job.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-rust@v1.11
  with:
    # toolchain: "1.98"                  # default: rust-toolchain.toml, else stable
    # components: rustfmt, clippy        # comma- or space-separated
    # targets: aarch64-unknown-linux-gnu
    # working-directory: .               # where Cargo.lock and rust-toolchain.toml live
```

Output: `cache-hit` (an exact key match for this job).

The key is the compiler build (`rustc -vV`) + `targets` + `Cargo.lock` hash + job id, so matrix
legs that differ by target, and jobs on different toolchains, never share a `target/`. Sets
`CARGO_INCREMENTAL=0` unless the job already set it.

A `toolchain` input becomes the rustup default, but a `rust-toolchain.toml` still wins inside
its own directory. To check an older toolchain in such a repo, name it on the command:
`cargo +1.98 check`.

### Coming later

`upload-pages` is designed but not yet built — see [AGENTS.md](AGENTS.md)
for status.

## Pinning

Point-release tags (`v1.11`, `v1.12`, …) are immutable. The floating major `v1` is moved by
`.github/workflows/release.yml` to the newest `v1.N` when that tag is the latest in the major.

Convenience examples here use the current point-release (`@v1.11`). Fleet call sites pin by
commit SHA with a version comment, matching how these actions pin their own dependencies:

```yaml
uses: Rethunk-Tech/gh-actions/setup-bun@<sha> # v1.11
```

Check [the releases page](https://github.com/Rethunk-Tech/gh-actions/releases) for the current
tag. `@v1` tracks the newest `v1.N`. A point-release that predates an action is a hard failure,
not a stale pin: `setup-rust` is not on `v1.10`, so `setup-rust@v1.10` fails with
`Can't find 'action.yml'`.

The repo-ops actions-refresh-sha sweep ([Rethunk-Tech/repo-ops](https://github.com/Rethunk-Tech/repo-ops))
keeps an existing **SHA** pin current within a major automatically; it has nothing to act on for a
bare version-tag reference like `@v1.11` (there is no stale SHA in that reference for the sweep to
find). Crossing a major (`v1` → `v2`) needs actions-refresh-sha with the latest option, and
only ever applies to SHA pins either way.

## Reporting a problem

Open an issue on this repo. For a security concern, see [SECURITY.md](SECURITY.md) instead of
a public issue.
