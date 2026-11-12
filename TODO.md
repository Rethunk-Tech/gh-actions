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
3. `AGENTS.md:62` — conventions every action here follows. A new directory
   copies those, it does not invent a Pages-specific exception.
4. The caller's workflow in `Rethunk-AI/bakeoff-results` — confirm it still
   uses `actions/upload-pages-artifact` the same way, and whether a second
   caller now exists.

### Traps

- **A second caller that is also a one-line passthrough still is not the
  bar.** `setup-dotnet` was dropped for that reason. Count
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

`setup-bun` has opt-in `run-audit` and `run-test` (`setup-bun/action.yml:91`
and `:99`). `setup-nextjs-bun` duplicates the install-store and Playwright
steps and deliberately does **not** declare those inputs.
`HUMANS.md:100` says undeclared `with:` keys are ignored.

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
real Next.js caller needs those gates on the same step rather than a follow-on
`setup-bun` or `audit-bun` step. Copy the `setup-bun` gate steps
and add a drift-check exception only for the Next.js-only `.next/cache` step.

Rejected: nesting `uses: ./setup-bun` today. That reintroduces the cache-save
bug.
Rejected: documenting a fake `run-audit` input that the action ignores.

### Read

1. `HUMANS.md:100` — the consumer contract: those keys are ignored.
2. `setup-bun/action.yml:230` `bun test` and `:240` `bun audit` — the steps
   to copy, including `continue-on-error` and the final gate table at `:248`.
3. `scripts/check-setup-bun-drift.py:16` `WATCHED` — a new shared step must
   be listed or it will not be compared.
4. `AGENTS.md` setup-nextjs-bun section — local vs `$/` and the depth-2
   warning for consumers.

### Traps

- **A consumer that wraps `setup-nextjs-bun` in their own local composite
  is already at depth 2.** Adding gates does not fix that; do not tell
  callers to nest.
- **`run-audit` on `setup-bun` calls `audit-bun/audit.ts` by path**
  (`setup-bun/action.yml:246`). The duplicated step must use the same path,
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
  behaviour. `HUMANS.md:100` is rewritten to match. `gate` stays clean.
