# AGENTS.md

Internals for anyone — human or model — changing this repository. To *use* an action from
here, read [HUMANS.md](HUMANS.md).

## File map

| Path | Holds |
| --- | --- |
| [README.md](README.md) | Orientation and the documentation index |
| [HUMANS.md](HUMANS.md) | Consuming an action from another repo — inputs, outputs, pinning |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Process — commit style, testing, how to add a new action |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting and trust boundary |

No `CHANGELOG.md`, `docs/`, or `specs/` yet — two actions, small enough that git tags carry the
version history. Add a changelog once tracking that by tag alone stops scaling.

## What this repo is

Composite GitHub Actions shared across the fleet (multiple orgs: Rethunk-Tech, Rethunk-AI,
Albino-Geek-Services, Citadel-Inc, and others), built to remove copy-pasted CI boilerplate —
Bun/Go/.NET toolchain setup, dependency caching — that was drifting independently per repo.
Public, not Marketplace-listed: Marketplace adds a global-uniqueness naming requirement, a
root-only/no-workflows repo constraint, and public-discoverability overhead for zero
functional gain over a plain public repo, which is all `uses: owner/repo/path@ref`
cross-org referencing actually needs.

**The goal is maintainable unity across the fleet, not preserving every repo's existing
quirk.** An input earns a place here only when a real caller genuinely needs it (evidenced by
grepping actual usage, never "this seems useful") — but the reverse also holds: standardizing
a whole workflow file, or dropping a repo-specific step, is in scope even when it costs that
one repo some bespoke behavior, if the fleet-wide result is easier to maintain. Don't treat
"repo X currently does it differently" as a constraint to design around by default — treat it
as a candidate for the fleet to converge on, and make that call explicitly rather than
defaulting to preserving variance.

## Status

**Shipped (`v1`):** `setup-bun`, `setup-nextjs-bun`, `setup-go`.

**Designed, not yet built (`v2`):** `setup-dotnet`, `upload-pages`. Deferred, not
wrong — each has a genuinely small value proposition on its own (near-pure passthroughs of the
underlying action's inputs, or a few lines saved across non-identical call sites). Pick one up
by giving it its own directory following the conventions below; re-verify the design against
the fleet's current state before building rather than trusting old design notes as binding.

## Conventions every action here follows

- **No `actions/checkout`.** The caller does that first, before the `uses:` line — standard
  composite-action convention.
- **No build/test steps** — those are project-defined commands that vary too much per repo to
  centralize; stays the caller's own job step. **Lint/security-gate steps are the one
  deliberate exception** (`setup-go`'s opt-in `run-lint`/`run-govulncheck`, off by default):
  unlike build/test, every real fleet caller invokes the exact same two tools
  (`golangci-lint-action`, `govulncheck`) with only their version/args/mode varying — real
  passthrough inputs, not a project-defined verb — and centralizing them converges the fleet
  onto one reviewed SHA pin instead of ~15 independently-drifting ones. Each such gate runs
  with `continue-on-error: true` behind a final gate step (never plain fail-fast) so enabling
  more than one still surfaces every finding in one run. A caller whose exact invocation
  doesn't fit (custom JSON-gating, non-cancelling separate jobs by design) just doesn't set the
  input and keeps its own step — this exception doesn't extend to a project's actual
  build/test commands, which stay out per the rule above.
- **Every wrapped action is SHA-pinned** with a `# vX.Y.Z` comment. `repo-ops`'s
  `--actions-refresh-sha` sweep keeps these current within a major; a wrapped action's major
  bump is a manual, reviewed change here.
- **No inline `${{ inputs.* }}` interpolation inside a `run:` body.** Script-injection
  surface — GitHub's own hardening guidance warns against it. Every value goes in via `env:`
  and is referenced as a shell variable. `actions/upload-pages-artifact` (a first-party
  composite) is the reference pattern: `env: INPUT_PATH: ${{ inputs.path }}` then
  `run: tar --directory "$INPUT_PATH" ...`.
- **A value that may legitimately contain multiple space-separated tokens** (e.g.
  `install-args`, `playwright-browsers`) is *branched* on empty vs non-empty, not
  interpolated bare — an empty value word-splits or throws depending on the downstream CLI's
  own argument parsing, breaking every default-path consumer that leaves the input unset.
  Where the non-empty branch does intentionally rely on word-splitting a multi-token value,
  mark it explicitly:

  ```bash
  # VALUE may hold multiple space-separated tokens; word-splitting is intentional.
  # shellcheck disable=SC2086
  some-command $VALUE
  ```

  A `shellcheck disable=` directive cannot carry trailing prose on the same line — the
  explanation goes on the line above, or shellcheck fails to parse the directive itself.

## Testing an action before committing it

`actionlint` cannot validate a composite `action.yml` — it parses whatever file it's pointed
at *as a workflow*, so it throws bogus structural errors on an action's own inputs/outputs
schema and never catches anything real inside the action. `.github/workflows/ci.yml`'s `lint`
job scopes it to `.github/workflows/*.yml` only, and schema-validates `action.yml` files
separately with `check-jsonschema --builtin-schema vendor.github-actions` — this catches
structural mistakes (a missing `shell:`, a malformed input) but **nothing inside `${{ }}`**: a
schema-valid `action.yml` with a broken expression or a degenerate `hashFiles()` call still
passes clean.

The only thing that catches a broken expression, a bad cache key, or a caching mechanism that
silently never saves is actually running the action — locally with [`act`](https://github.com/nektos/act)
before committing, and in CI via `.github/workflows/ci.yml`'s self-test jobs (`test-setup-bun-cold`
→ `test-setup-bun-warm`, same pattern for `setup-nextjs-bun`) after. A few things that are easy
to get wrong when writing that kind of test:

- **`actions/cache` saves in the job's *post* phase, after every main step completes.**
  Calling an action that uses it twice within the *same job* will never see a hit on the
  second call — the first call's save hasn't happened yet. Test cold-vs-warm across two
  *separate* job runs (a `needs:`-chained pair, or two separate `act` invocations sharing a
  `--cache-server-path`), not two calls in one job.
- Locally, use a real fixture with a real `bun.lock` — `bun install` in a scratch directory
  generates one; don't hand-write a plausible-looking lockfile.
- `act` needs Docker and a `--cache-server-path` to actually exercise `actions/cache` restore/
  save; without it, cache steps are effectively no-ops in local testing.
- Any test fixture created for local iteration stays untracked/cleaned up before committing —
  `.github/test-fixtures/` is the one committed exception, used by `ci.yml`'s own self-test.
- **`actions/cache`'s `cache-hit` output is tri-state, not boolean:** `''` (total miss —
  neither the exact key nor any `restore-keys` prefix matched), `'false'` (a `restore-keys`
  *partial* match restored something, but not the exact key), `'true'` (exact key match).
  `setup-bun` and `setup-nextjs-bun` intentionally share the same `restore-keys` prefix
  (`${{ runner.os }}-bun-`) so unrelated projects on the same runner OS warm-start each
  other's Bun install-store cache — a deliberate design choice, not an oversight. This means
  a "cold" self-test job can legitimately see `cache-hit: 'false'` if a *different* fixture's
  job saved its cache first in a parallel run. Assert `!= 'true'` on a cold run (rules out a
  stale exact-match surviving the cache reset), never emptiness (rules out the intentional,
  racy, harmless partial-match case too).

## The one design decision worth understanding before touching `setup-nextjs-bun`

It does not compose `setup-bun`, even though GitHub's `$/` self-repository reference syntax
(an action referencing a sibling action in the same repo) would let it. The reason not to use
it here: nesting composite actions triggers a still-open runner bug ([actions/runner#2009](https://github.com/actions/runner/issues/2009),
[#2030](https://github.com/actions/runner/issues/2030)) affecting an *expression-valued*
`path:` on `actions/cache` at nesting depth ≥2 — the cache key itself is unaffected (cached in
job state, not re-evaluated at post time), but the path can fail to resolve when the post step
runs, so the cache silently never saves. A runner maintainer's comment on #2009 states the bug
is triggered specifically by a *local* (`uses: ./path`) composite reference and avoided by a
*remote* one (`uses: owner/repo/path@ref`); whether `$/` counts as "local" for this purpose has
no public answer yet. Given that ambiguity, `setup-nextjs-bun` duplicates `setup-bun`'s core
steps instead of composing them.

Two consequences that matter if you touch either action:

1. **They will drift** if one changes without the other — an accepted, documented cost, not
   an oversight. Check both when changing shared behavior (Bun setup, the install-store cache,
   the Playwright branch).
2. `setup-nextjs-bun`'s own `.next/cache` step resolves its path via `$GITHUB_ENV` in the
   guard step rather than an inline `inputs.working-directory` expression — this keeps it safe
   at nesting depth 1, but **a consumer that wraps this action inside their own local
   composite reintroduces the exact bug at depth 2.** Don't nest either action inside a
   further local composite; say so if you're writing a README section a consumer might copy.

Re-evaluate composing via `$/` once #2009/#2030 close, or once the local-vs-`$/` question has
a public answer.

## Why `oven-sh/setup-bun` and not a hand-rolled install

The one non-`actions/*` dependency in this repo. `oven-sh` is the same org that publishes Bun
itself (not an unrelated third party), `setup-bun` is actively maintained and SHA-pins its own
dependencies internally, and it does real work that would have to be reimplemented to drop it — Windows needs a genuinely different install mechanism
than Linux/macOS, and this repo's own `bun-version-file` fallback (reading a version from
`package.json`'s `packageManager` field) is exactly the resolution logic `setup-bun` already
implements. A bare `curl | bash` alternative would also be a supply-chain *regression*: a
SHA-pinned action reference is an immutable, auditable artifact; a curl-piped install script
from a live URL has no equivalent pin.
