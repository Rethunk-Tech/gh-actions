#!/usr/bin/env bash
# Runs real downstream callers' CI jobs under act against this tree (or REF), so a changed
# default or input contract fails here instead of across the fleet after a pin bump.
# Usage: scripts/act-callers.sh [REF]   (default: the working tree's HEAD)
# ACT_CALLERS_ONLY=substr limits the run to matching callers; logs stay in ~/.cache/act-callers.
# Callers: scripts/act-callers.txt, one "Org/repo workflow job [act args...]" per line.
# A full pass (every caller ran and passed, none skipped, no ACT_CALLERS_ONLY) stamps REF's sha into
# ~/.cache/nomad-hud/act-stamp, which nomad-hud's guard requires before a push, tag or pin bump.
set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
ref=${1:-HEAD}
src=${ACT_CALLERS_SRC:-$(bosun roots 2>/dev/null | grep com.github | head -1)}
src=${src:-/usr/local/src/com.github}
logs=${XDG_CACHE_HOME:-$HOME/.cache}/act-callers
only=${ACT_CALLERS_ONLY:-}
mkdir -p "$logs"
for t in act docker; do
  command -v "$t" >/dev/null || {
    echo "act-callers: $t not installed" >&2
    exit 1
  }
done

tmp=$(mktemp -d "${TMPDIR:-/var/tmp}/act-callers.XXXXXX")
trap 'rm -rf --one-file-system -- "$tmp"' EXIT
mkdir "$tmp/tree"
git -C "$here" archive "$ref" | tar -x -C "$tmp/tree"

# act-latest lacks tools GitHub's ubuntu runner ships; add each one only when missing, so callers'
# own steps run as they do in CI. Docker's layer cache makes this a no-op after the first build.
image=act-callers-runner:latest
docker build -q -t "$image" - >/dev/null <<'DOCKERFILE'
FROM catthehacker/ubuntu:act-latest
RUN missing=""; for t in shellcheck; do command -v "$t" >/dev/null || missing="$missing $t"; done; \
    if [ -n "$missing" ]; then apt-get update && apt-get install -y --no-install-recommends $missing && rm -rf /var/lib/apt/lists/*; fi
RUN command -v google-chrome >/dev/null || { \
      curl -fsSLo /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
      apt-get update && apt-get install -y --no-install-recommends /tmp/chrome.deb && \
      rm -rf /tmp/chrome.deb /var/lib/apt/lists/*; }
DOCKERFILE

fail=0 ran=0 skipped=0
while read -r repo wf job extra; do
  case "$repo" in '' | '#'*) continue ;; esac
  [ -z "$only" ] || [[ $repo == *"$only"* ]] || continue
  dir="$src/$repo"
  if [ ! -d "$dir/.git" ]; then
    echo "act-callers: skip $repo (no clone at $dir)"
    skipped=$((skipped + 1))
    continue
  fi
  # Every gh-actions pin the caller uses maps to this tree. act cannot parse `uses: $/...`
  # (same-repo reference), so the copy points those at the caller's own pin instead.
  mapfile -t pins < <(grep -ho 'Rethunk-Tech/gh-actions/[^@]*@[0-9a-f]\{40\}' "$dir/.github/workflows/$wf" | sed 's/.*@//' | sort -u)
  [ ${#pins[@]} -gt 0 ] || {
    echo "act-callers: skip $repo (no gh-actions pin in $wf)"
    skipped=$((skipped + 1))
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
  if (cd "$dir" && act push -W ".github/workflows/$wf" -j "$job" "${args[@]}" \
    -P "ubuntu-latest=$image" --pull=false $extra) >"$log" 2>&1; then
    echo "act-callers: ok   $repo $wf/$job"
  else
    echo "act-callers: FAIL $repo $wf/$job"
    grep -E '❌|::error|Error:' "$log" | tail -8 >&2
    echo "act-callers: full log $log" >&2
    fail=1
  fi
done <"$here/scripts/act-callers.txt"

echo "act-callers: $ran caller job(s) run, $skipped skipped, ref $ref"
if [ "$fail" -eq 0 ] && [ "$ran" -gt 0 ] && [ "$skipped" -eq 0 ] && [ -z "$only" ]; then
  stamp_dir=$HOME/.cache/nomad-hud
  mkdir -p "$stamp_dir"
  git -C "$here" rev-parse "$ref" >"$stamp_dir/act-stamp.tmp"
  mv "$stamp_dir/act-stamp.tmp" "$stamp_dir/act-stamp"
fi
exit "$fail"
