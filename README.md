# gh-actions

Shared composite GitHub Actions for the fleet. Public, not Marketplace-listed — reference
directly via `uses: Rethunk-Tech/gh-actions/<action>@<ref>` from any repo in any org.

## Actions

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
    # playwright-browsers: chromium    # scope Playwright install; empty = install everything
    # extra-cache-paths: |             # additional cache, independently keyed
    #   frontend/.some-build-cache
    # extra-cache-key: ${{ hashFiles('frontend/**/*.ts') }}
```

Outputs: `cache-hit` (bun install-store cache hit).

### `setup-nextjs-bun`

Next.js-specific — everything `setup-bun` does, plus a `.next/cache` build cache (dual-hash
keyed per Next.js's own CI-build-caching guide) and `NEXT_TELEMETRY_DISABLED=1`. Does not
compose `setup-bun` — duplicates its core steps directly (see "Design notes" below for why).
One Next app per `working-directory`; for a multi-app repo, call `setup-bun` once per app
instead.

```yaml
- uses: actions/checkout@v7
- uses: Rethunk-Tech/gh-actions/setup-nextjs-bun@v1
  with:
    working-directory: frontend
    # same optional inputs as setup-bun: bun-version, install-args, node-version,
    # install-playwright, playwright-browsers
```

Outputs: `cache-hit` (bun install-store cache hit).

## Design notes

- Neither action runs `actions/checkout` — the caller does that first.
- Neither action runs lint/build/test — those are project-defined commands that vary too
  much per repo to centralize; stays the caller's own job step.
- Every wrapped action is SHA-pinned with a version comment.
- `install-playwright` does not cache browser binaries — Playwright's own CI guidance
  recommends against it (restore time is comparable to download time), and `--with-deps`
  installs OS dependencies via `apt` on every run regardless of any binary cache.
- **`setup-nextjs-bun` does not compose `setup-bun`.** It could, via GitHub's `$/`
  self-repository reference syntax (an action referencing a sibling action in the same repo)
  — that mechanism itself works correctly. The reason not to: nesting composite actions
  triggers a still-open runner bug ([actions/runner#2009](https://github.com/actions/runner/issues/2009),
  [#2030](https://github.com/actions/runner/issues/2030)) affecting an *expression-valued*
  `path:` on `actions/cache` at nesting depth ≥2 — the cache key is unaffected (cached in
  state, not re-evaluated), but the path can silently fail to resolve at save time. A
  maintainer comment on #2009 states the bug is triggered by *local* (`uses: ./path`)
  composite references specifically and avoided by a remote reference
  (`uses: owner/repo/path@ref`) — whether `$/` counts as "local" for this purpose is not
  publicly verified. Given that ambiguity, `setup-nextjs-bun` flattens instead of composing.
  Consequence: the two actions duplicate their core steps and will drift if one changes
  without the other — an accepted, documented cost.
- Because of the same bug class, **do not nest either of these actions inside your own local
  composite action** — `setup-nextjs-bun`'s `.next/cache` step resolves its path via
  `$GITHUB_ENV` rather than an inline expression specifically to stay safe at depth 1, but
  wrapping it in a further local composite reintroduces the risk.
- `oven-sh/setup-bun` (the one non-`actions/*` dependency here) is the Bun runtime's own
  vendor-published action, actively maintained, and provides real hard-to-replicate value —
  correct cross-platform installation (Windows needs a different mechanism than Linux/macOS)
  and version resolution from `package.json`'s `packageManager` field, which both actions'
  own `bun-version-file` fallback directly relies on.

## Testing

`.github/workflows/ci.yml` schema-validates both `action.yml` files (`actionlint` cannot —
it parses any file as a workflow) and self-tests each action against a committed fixture
(`.github/test-fixtures/`) across a cold-cache job followed by a warm-cache job that only
starts once the cold job's cache save has actually landed — proving `cache-hit` is genuinely
empty on a first run and `true` on a second, not just that the action exits zero.
