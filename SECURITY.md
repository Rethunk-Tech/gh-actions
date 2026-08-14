# Security

## Supported versions

The latest tagged release. This repo has no long-lived release branches, so a fix ships in
the next tag rather than being backported.

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting** on this repository (Security → Report a
vulnerability). It stays private until a fix ships.

Please do not open a public issue for a suspected vulnerability first.

## What is in scope

These actions run inside a caller's workflow with whatever permissions that workflow has, so
the interesting failures are ones where an action does something the caller's inputs didn't
ask for:

- Any `run:` step that would let a value from a workflow input, an untrusted PR title/branch
  name, or similar reach a shell as anything other than an inert argument — script injection
  via unquoted or inline `${{ }}` interpolation. Every input this repo's actions consume goes
  in via `env:` first; a step that regresses to inline interpolation is a bug even if no
  concrete exploit is demonstrated.
- A wrapped third-party action's SHA pin resolving to different content than the version
  comment claims (i.e. the pin itself was tampered with in a PR, not that the upstream project
  was compromised — that's out of scope, see below).
- A cache key collision that would let one consumer's cached content be served to an unrelated
  consumer's job under a different repo/branch (GitHub's own cache scoping is the primary
  defense here; this repo's actions' contribution is only whether the *key* is constructed
  correctly).

## What is not

- **The wrapped third-party actions' own supply chain** (`oven-sh/setup-bun`,
  `actions/setup-node`, `actions/cache`). This repo SHA-pins each one specifically so a
  compromise upstream requires a new, reviewed pin bump here before it reaches any consumer —
  but a vulnerability in the upstream project itself is that project's to fix and disclose,
  not this repo's.
- **A caller passing genuinely untrusted, attacker-controlled input directly into `install-args`
  or `extra-cache-key`** without their own sanitization. These inputs are designed for a
  repo's own CI configuration (flags, hash expressions), not for values sourced from PR
  content — a caller wiring one to something an outside contributor controls is a
  caller-side design choice, not a vulnerability in the action itself.
- **A cache serving stale content within its own correctly-scoped key.** That's a correctness/
  performance bug (a degenerate `hashFiles()` result, a missing `restore-keys` prefix) —
  please file it as an ordinary issue, not a security report.
