#!/usr/bin/env bash
# A cache a cold self-test leg saves can take seconds to be listed, and a warm leg that restores before then misses it
# (setup-rust, run 39563575077). Wait until a key with this prefix and suffix is listed for the ref, for up to two
# minutes; past that the warm leg's own assertion reports what it restored.
set -euo pipefail
prefix=$1
suffix=${2:-}
for _ in $(seq 24); do
  if gh cache list --repo "$GITHUB_REPOSITORY" --ref "$GITHUB_REF" --key "$prefix" --limit 100 --json key -q '.[].key' |
    grep -qF -- "$suffix"; then
    echo "cache $prefix…$suffix is listed"
    exit 0
  fi
  sleep 5
done
echo "::warning::no cache $prefix…$suffix listed after two minutes" >&2
