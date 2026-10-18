# Contributing

Read [AGENTS.md](AGENTS.md) first — it holds the conventions every action here follows and
why `setup-nextjs-bun` doesn't compose `setup-bun`.

## Commits

Conventional commits: `type(scope): subject`, e.g. `feat(setup-go): add Go toolchain setup`.

- Subject is imperative and under ~72 characters.
- Body explains **why**, not which files changed.
- One logical unit per commit — one action per commit where practical.
- No AI attribution trailers.

## Before opening a PR

1. Run `gate` from the repository root. It detects this repo's local checks (actionlint,
   fixture gates, `bun test audit-bun`, `scripts/check-setup-bun-drift.py`, action.yml schema,
   undeclared-input, tracked-fixture). CI self-tests of the composite actions need a GitHub
   runner and are not what `gate` covers.
2. Schema-validate any changed `action.yml`:

   ```bash
   uvx check-jsonschema --builtin-schema vendor.github-actions <action>/action.yml
   ```

3. Shellcheck every `run:` block in the file.
4. Actually run the action with [`act`](https://github.com/nektos/act) against a real
   fixture — see [AGENTS.md § Testing an action before committing it](AGENTS.md#testing-an-action-before-committing-it)
   for the cold/warm-cache testing pattern and its gotchas. A schema-valid, shellcheck-clean
   action can still be functionally broken; only actually running it catches that.
5. `.github/workflows/ci.yml` schema-validates every `action.yml`, checks undeclared inputs,
   shared-step drift, tracked fixtures, and actionlint on workflows — the same root checks
   `.gate.toml` adds on top of detection. Fixture language gates (biome, `go test`, ruff,
   clippy) run in local `gate` only; the composite self-test jobs exercise the actions, not
   those fixture checks. A red CI run on a PR still means something above wasn't done first.

## Adding a new action

- New directory at the repo root, `action.yml` inside it — not nested deeper.
- Follow the conventions in [AGENTS.md](AGENTS.md): no `checkout`, no project-specific
  build/test steps (the standardized opt-in test and lint/security gates on `setup-go`,
  `setup-python`, `setup-rust`, and `setup-bun` are the documented exceptions — see AGENTS.md),
  every wrapped action SHA-pinned with a version comment, no bare `${{ inputs.* }}`
  interpolation inside `run:`.
- Add a committed fixture under `.github/test-fixtures/` if the action needs one for CI
  self-testing, and wire a cold/warm job pair into `.github/workflows/ci.yml` following the
  existing `test-setup-bun-*` jobs as the template. If it shares a lockfile-based cache key
  with another action's fixture, give it distinct fixture content (a different dependency) so
  the cache keys do not collide across self-test jobs.
- Add a usage section to [HUMANS.md](HUMANS.md) — inputs worth knowing, an example snippet,
  outputs.
- Tag a new version once it ships. This repo has no long-lived release branches — a fix or
  addition ships in the next tag.

## Reporting a bug

Open an issue. For a security concern, see [SECURITY.md](SECURITY.md) instead of a public
issue.
