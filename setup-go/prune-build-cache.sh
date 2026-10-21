#!/usr/bin/env bash
# Prune a Go build cache to the entries within two hours of its newest one (see the step in action.yml).
# One batched stat pass: a fork per file took 96s on Linux and 280s on Windows.
set -euo pipefail
cache=$1
[ -d "$cache" ] || exit 0
list=$(mktemp)
trap 'rm -f "$list"' EXIT
find "$cache" -type f -exec stat -c '%Y %n' {} + >"$list" 2>/dev/null \
  || find "$cache" -type f -exec stat -f '%m %N' {} + >"$list"
newest=$(awk '$1 > m { m = $1 } END { print m + 0 }' "$list")
[ "$newest" -gt 0 ] || exit 0
before=$(du -sm "$cache" | cut -f1)
awk -v cutoff=$((newest - 7200)) '$1 < cutoff { sub(/^[0-9]+ /, ""); print }' "$list" | tr '\n' '\0' | xargs -0 rm -f
echo "Go build cache pruned from ${before} MB to $(du -sm "$cache" | cut -f1) MB"
