## Summary

- _What changed and why._

## Verification

- [ ] `check-jsonschema --builtin-schema vendor.github-actions <action>/action.yml` for every changed `action.yml`
- [ ] `shellcheck` on every changed `run:` block
- [ ] Ran the action end-to-end with [`act`](https://github.com/nektos/act) against a real fixture — not just schema-checked (see [AGENTS.md § Testing an action before committing it](../AGENTS.md#testing-an-action-before-committing-it))
- [ ] `.github/workflows/ci.yml` passes

## Risk

- [ ] Changes a wrapped action's SHA pin (major version bump — reviewed the upstream changelog)
- [ ] Changes an existing action's default input value (breaking for current consumers)
- [ ] New action, no existing consumer affected
