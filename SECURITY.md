# Security

## Supported versions

The latest tagged release. No long-lived branches; a fix ships in the next tag.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository: <https://github.com/Rethunk-Tech/gh-actions/security/advisories/new>, or the **Security** tab, then **Report a vulnerability**. The report stays private between you and us until a fix ships.

If private reporting is unavailable, email [oss@rethunk.tech](mailto:oss@rethunk.tech) with **[SECURITY]** in the subject.

Please do not open a public issue, pull request or discussion for a suspected vulnerability.

A useful report has the affected repository and version (or commit), steps to reproduce, what an attacker gets and under which conditions, and whether anyone else knows.

## What counts as a vulnerability

A vulnerability is a flaw that lets someone cross a boundary they should not: run code, read or change data they have no right to, escape a sandbox or path restriction, or leak a credential. A bug is anything else that misbehaves, such as a crash on your own input, wrong output or a slow path; open an ordinary issue for those. If you are unsure which one you have, report it privately and we will say.

## Coordinated disclosure

We handle the report inside the private advisory, so you see each status change and can comment on the fix. The advisory goes public when the fix ships, or 90 days after your report, whichever comes first. If a fix is close, either of us can ask for more time in the thread. You are credited in the advisory unless you would rather not be.

## Response timelines

- We acknowledge your report within 3 business days.
- We give you an assessment (accepted, needs more information or declined, with reasons) within 10 business days.
- We aim to ship a fix within 90 days of the report.

## In scope

- A `run:` step that interpolates a workflow input, PR title/branch, or similar into a shell as anything but an inert argument (inline `${{ }}`). Inputs must enter via `env:`.
- A wrapped-action SHA pin whose content does not match the version comment (tamper in a PR here). Upstream compromise of a wrapped action is out of scope.
- A cache key that would serve one consumer's cache to an unrelated repo/branch. GitHub scopes the cache; this repo is responsible for key construction.

## Out of scope

- Vulnerabilities in wrapped actions (`oven-sh/setup-bun`, `astral-sh/setup-uv`, `actions/setup-node`, `actions/cache`). Pins here stop an upstream compromise until a reviewed bump; disclose upstream.
- A caller feeding attacker-controlled PR content into `install-args` or `extra-cache-key`. Those are for the caller's own CI flags and hashes.
- Stale cache under a correctly-scoped key. File as an ordinary issue.

## Safe harbour

We will not pursue legal action against good-faith research that avoids privacy violations, data destruction and disruption of services, stops at a proof of concept, and keeps the details private until the advisory is published. Rethunk.Tech, LLC. maintains this repository.
