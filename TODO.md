# TODO

Work that is decided but not built. `AGENTS.md` and `HUMANS.md` describe what
exists; this file is the only place that describes what does not.

Sections are unordered.

## upload-pages is designed and still has one caller

`AGENTS.md` Status (`Designed, not yet built`) already names this. The
action would be a near-pure passthrough around `actions/upload-pages-artifact`,
saving a couple of lines at each call site. It currently has exactly one
caller (`Rethunk-AI/bakeoff-results`), which otherwise depends on nothing in
this repo.

The bar this repo uses for a new composite is the one `setup-python` cleared:
many sites across repos, incompatible variants. One caller does not.

Decided shape: a `upload-pages/` directory with its own `action.yml`, following
the conventions in `AGENTS.md` (no `actions/checkout`, SHA-pinned
`actions/upload-pages-artifact`, values in via `env:` not inline
`${{ inputs.* }}` inside `run:`). Re-verify the fleet's current call sites
before building; do not treat older design notes as binding.

Rejected: building it as a v2 tag while the rest of the repo is v1.
Rejected: wrapping it because a second caller "might" appear.

### Read

1. `AGENTS.md:48` — status, the one-caller count, and the instruction to
   re-verify against the fleet before building.
2. `HUMANS.md` — consumers see shipped actions only; do not re-add a "coming later" section.
3. `AGENTS.md:82` — conventions every action here follows. A new directory
   copies those, it does not invent a Pages-specific exception.
4. The caller's workflow in `Rethunk-AI/bakeoff-results` — confirm it still
   uses `actions/upload-pages-artifact` the same way, and whether a second
   caller now exists.

### Traps

- **A second caller that is also a one-line passthrough still is not the
  bar.** `setup-dotnet` was dropped for that reason (`AGENTS.md:63`). Count
  incompatible variants, not `uses:` lines.
- **Marketplace listing is out of scope.** This repo stays a plain public
  repo (`AGENTS.md` "What this repo is").
- **Do not nest a local composite inside another local composite.** The
  `actions/cache` path-resolution bug at nesting depth ≥2
  (`AGENTS.md` setup-nextjs-bun section) is why `setup-nextjs-bun` duplicates
  steps. A Pages action that only wraps `actions/*` is fine; wrapping
  `setup-nextjs-bun` is not.

### Acceptance

- A second fleet caller exists, or a recount documents incompatible variants
  that a composite would collapse.
- `upload-pages/action.yml` is schema-valid, SHA-pins its wrapped action, and
  has a self-test job in `.github/workflows/ci.yml`.
- `HUMANS.md` gains a usage section for the new action in the same commit it
  ships. `gate` stays clean.

## setup-nextjs-bun has no audit or test gate

`setup-bun` has opt-in `run-audit` and `run-test` (`setup-bun/action.yml:93`
and `:101`). `setup-nextjs-bun` duplicates the install-store and Playwright
steps and deliberately does **not** declare those inputs.
`HUMANS.md:97` says undeclared `with:` keys are ignored.

The reason the actions are not composed is
[actions/runner#2009](https://github.com/actions/runner/issues/2009) /
[#2030](https://github.com/actions/runner/issues/2030): an expression-valued
`path:` on `actions/cache` at nesting depth ≥2 can fail to resolve in the
post step, so the cache never saves (`AGENTS.md` "The one design decision
worth understanding before touching `setup-nextjs-bun`").

Decided shape: once #2009/#2030 close, or once a runner maintainer answers
whether `$/` counts as local, compose via `$/` and delete the duplicated
steps (and `scripts/check-setup-bun-drift.py`). Until then, duplicating the
audit/test/skip-install steps into `setup-nextjs-bun` is allowed only if a
real Next.js caller needs those gates on the same step rather than a
follow-on `setup-bun` or `audit-bun` step. Copy the `setup-bun` gate steps
and add a drift-check exception only for the Next.js-only `.next/cache` step.

Rejected: nesting `uses: ./setup-bun` today. That reintroduces the cache-save
bug.
Rejected: documenting a fake `run-audit` input that the action ignores.

### Read

1. `HUMANS.md:97` — the consumer contract: those keys are ignored.
2. `setup-bun/action.yml:222` `bun test` and `:232` `bun audit` — the steps
   to copy, including `continue-on-error` and the final gate table at `:240`.
3. `scripts/check-setup-bun-drift.py:16` `WATCHED` — a new shared step must
   be listed or it will not be compared.
4. `AGENTS.md` setup-nextjs-bun section — local vs `$/` and the depth-2
   warning for consumers.

### Traps

- **A consumer that wraps `setup-nextjs-bun` in their own local composite
  is already at depth 2.** Adding gates does not fix that; do not tell
  callers to nest.
- **`run-audit` on `setup-bun` calls `audit-bun/audit.ts` by path**
  (`setup-bun/action.yml:238`). The duplicated step must use the same path,
  not a second copy of the auditor.
- **skip-install is not a Next.js caller shape today.** Adding it without a
  fleet site that skip-installs a Next app is an input that exists only for
  symmetry.

### Acceptance

- Either the actions are composed via `$/` after the runner bug is closed,
  or the duplicated gate steps exist, are drift-checked, and a Next.js
  self-test fixture fails `run-audit`/`run-test` the way `bun-app-vulnerable`
  and `bun-app-failing` do.
- Existing Next.js callers that do not set the new inputs keep today's
  behaviour. `HUMANS.md:97` is rewritten to match. `gate` stays clean.

## setup-rust has no cargo-audit gate

`setup-go` has `run-govulncheck` (`setup-go/action.yml:79`). `setup-python`
has `run-audit` (`setup-python/action.yml:64`). `setup-bun` has `run-audit`
(`setup-bun/action.yml:93`). `setup-rust` has `run-clippy`, `run-fmt`, and
`run-test` (`setup-rust/action.yml:30`, `:37`, `:45`) and no vuln gate.
`AGENTS.md` names rust's lint/security exception as clippy and fmt only.

`cargo-audit` is not a GitHub-owned action. A nested third-party action
fails org allowlists (`AGENTS.md` nested-action rule), so the implemention
has to download a checksum-verified binary the way `setup-go` downloads
golangci-lint (`setup-go/action.yml:228`).

Decided shape: opt-in `run-audit` (default `"false"`),
`continue-on-error: true`, a row in the existing gate table, output
`audit-outcome`. Install `cargo-audit` onto the toolchain in the same
style as golangci-lint (SHA or release checksum, not `cargo install` from
crates.io unpinned). Command is `cargo audit` from `working-directory`.
A `rust-app-vulnerable` fixture with a crate whose advisory has a shipped
fix, plus a CI job that asserts `audit-outcome=failure`.

Rejected: wrapping `actions-rs/audit-check` or any non-`actions/*` /
non-verified-Marketplace action.
Rejected: treating clippy as the vuln gate. Clippy is lint; cargo-audit is
vuln (`rethunk-gate-cli` TODO already draws that line).
Rejected: turning it on by default. Every other security gate here is opt-in.

### Read

1. `AGENTS.md` conventions — the lint/security-gate exception, SHA pins,
   `env:` not inline interpolation, `continue-on-error` behind a final gate.
2. `setup-go/action.yml:228` — the checksum-verified binary download to copy.
3. `setup-rust/action.yml:156` — where the new step sits (after fmt, before
   or after test) and `:183` the gate table that must grow a row.
4. Fleet recount of `cargo audit` / `cargo-audit` in heft and any other rust
   caller. An input earns a place only when a real caller needs it
   (`AGENTS.md`).

### Traps

- **`cargo install cargo-audit` on every job is not a pin.** The Go lint
  step verifies the tarball against the release checksums file
  (`setup-go/action.yml:267`). Match that, or the supply chain is weaker
  than golangci-lint.
- **A rust-app-vulnerable fixture that `cargo test` also fails is a bad
  fixture.** The audit-only job must leave clippy, fmt, and test off, the
  way `test-setup-python-audit-fail` leaves ruff off.
- **`cargo audit` needs a lockfile.** The fixture tracks `Cargo.lock`.
- **Detection will try to run the fixture.** Add it to `.gate.toml`
  `[detect] exclude` in the same commit, like `python-app-vulnerable`.

### Acceptance

- `run-audit` default `"false"` leaves every current caller unchanged.
- A clean `Cargo.lock` with `run-audit: true` yields `audit-outcome=success`.
- `rust-app-vulnerable` yields composite failure and `audit-outcome=failure`.
- `HUMANS.md` documents the input next to clippy/fmt/test. `gate` stays
  clean.

## extra-cache with only one of paths or key set is a silent no-op

`setup-bun/action.yml:199` (and the duplicate at
`setup-nextjs-bun/action.yml:171`) runs the extra cache only when
`extra-cache-paths != '' && extra-cache-key != ''`. Setting exactly one
skips the step with no `::error::`. `HUMANS.md:46` says both inputs are
required for the cache to run at all. A caller that forgets the key thinks
they cached `.turbo` and did not.

Decided shape: a guard step before the cache step that errors when exactly
one of the two is non-empty, naming both inputs. Empty/empty stays the
default no-op. The same guard in `setup-nextjs-bun`, or a drift-check if
the step is shared. A CI job that sets only `extra-cache-paths` and asserts
the composite fails.

This **fails jobs that currently succeed** with a one-sided `with:`. That
is why it is deferred: it is a contract change, even though the docs
already called one-sided configuration useless.

Rejected: restoring from a missing key. There is no key to restore.
Rejected: a warning annotation that still skips. Callers do not read
warnings as "your cache is off".

### Read

1. `setup-bun/action.yml:51` and `:59` — the two inputs.
2. `setup-bun/action.yml:199` — the `if:` that silently skips.
3. `HUMANS.md:46` — "Both inputs are required for the cache to run at all".
4. `scripts/check-setup-bun-drift.py` — the Next.js duplicate must stay in
   sync or be excepted.

### Traps

- **A workflow that sets `extra-cache-key` from an expression that expands
  empty** (failed `hashFiles`, empty secret) will start failing. That is
  the point, and it is why this waits for a counted caller, not a drive-by.
- **Do not word-split `extra-cache-paths`.** It is `actions/cache` `path`
  form, newline-separated (`setup-bun/action.yml:53`).
- **`extra-cache-restore-key-fragment` empty is valid** when both required
  inputs are set (`HUMANS.md:47`). The guard does not mention it.

### Acceptance

- Paths and key both empty: extra cache skipped, action succeeds (today).
- Paths set, key empty: composite fails with an error that names both
  inputs. Symmetric for key-without-paths.
- Both set: existing extra-cache cold/warm jobs still restore the marker.
- `HUMANS.md` can keep "both required"; the action now matches. `gate`
  stays clean.
