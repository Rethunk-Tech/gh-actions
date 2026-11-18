#!/usr/bin/env bash
# Runs real downstream callers' CI jobs under act against this tree (or REF), so a changed
# default or input contract fails here instead of across the fleet after a pin bump.
# Usage: scripts/act-callers.sh [REF]   (default: the working tree's HEAD)
# ACT_CALLERS_ONLY=substr limits the run to matching callers; logs stay in ~/.cache/act-callers.
# Callers: scripts/act-callers.txt, one "Org/repo workflow job [act args...]" per line.
set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
ref=${1:-HEAD}
src=${ACT_CALLERS_SRC:-/usr/local/src/com.github}
logs=${XDG_CACHE_HOME:-$HOME/.cache}/act-callers
only=${ACT_CALLERS_ONLY:-}
mkdir -p "$logs"
for t in act yq; do
  command -v "$t" >/dev/null || {
    echo "act-callers: $t not installed" >&2
    exit 1
  }
done

tmp=$(mktemp -d "${TMPDIR:-/var/tmp}/act-callers.XXXXXX")
trap 'rm -rf --one-file-system -- "$tmp"' EXIT
mkdir "$tmp/tree"
git -C "$here" archive "$ref" | tar -x -C "$tmp/tree"

fail=0 ran=0
while read -r repo wf job extra; do
  case "$repo" in '' | '#'*) continue ;; esac
  [ -z "$only" ] || [[ $repo == *"$only"* ]] || continue
  dir="$src/$repo"
  if [ ! -d "$dir/.git" ]; then
    echo "act-callers: skip $repo (no clone at $dir)"
    continue
  fi
  # Every gh-actions pin the caller uses maps to this tree. act cannot parse `uses: $/...`
  # (same-repo reference), so the copy points those at the caller's own pin instead.
  mapfile -t pins < <(grep -ho 'Rethunk-Tech/gh-actions/[^@]*@[0-9a-f]\{40\}' "$dir/.github/workflows/$wf" | sed 's/.*@//' | sort -u)
  [ ${#pins[@]} -gt 0 ] || {
    echo "act-callers: skip $repo (no gh-actions pin in $wf)"
    continue
  }
  args=()
  for p in "${pins[@]}"; do
    copy="$tmp/pin-$p"
    [ -d "$copy" ] || {
      cp -a "$tmp/tree" "$copy"
      sed -i -E "s#uses: \\\$/([^ ]+)#uses: Rethunk-Tech/gh-actions/\\1@$p#" "$copy"/*/action.yml
    }
    args+=(--local-repository "Rethunk-Tech/gh-actions@$p=$copy")
  done
  log="$logs/$(basename "$repo")-$job.log"
  ran=$((ran + 1))
  # shellcheck disable=SC2086 # extra holds the caller line's own act flags
  (cd "$dir" && act push -W ".github/workflows/$wf" -j "$job" "${args[@]}" \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest $extra) >"$log" 2>&1 && rc=0 || rc=$?
  # Judge only the steps that call this repo: the act image lacks tools GitHub's runner has
  # (shellcheck, browsers), so a caller's own later step can fail here for reasons CI never sees.
  # The last result line for a step name is the outer step; composite inner steps print first.
  bad=""
  while IFS= read -r step; do
    last=$(grep -E "(Success|Failure) - Main $(printf '%s' "$step" | sed 's/[][\.*^$/]/\\&/g') \[" "$log" | tail -1)
    case "$last" in *Success*) ;; *) bad+="${bad:+, }$step${last:+ failed}${last:- never ran}" ;; esac
  done < <(yq ".jobs.\"$job\".steps[] | select(.uses // \"\" | test(\"Rethunk-Tech/gh-actions/\")) | (.name // .uses)" "$dir/.github/workflows/$wf")
  if [ -z "$bad" ]; then
    [ "$rc" -eq 0 ] && note="" || note=" (a caller-only step failed under act; see $log)"
    echo "act-callers: ok   $repo $wf/$job$note"
  else
    echo "act-callers: FAIL $repo $wf/$job: $bad"
    grep -E '❌|::error|Error:' "$log" | tail -8 >&2
    echo "act-callers: full log $log" >&2
    fail=1
  fi
done <"$here/scripts/act-callers.txt"

echo "act-callers: $ran caller job(s) run, ref $ref"
exit "$fail"
