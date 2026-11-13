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
