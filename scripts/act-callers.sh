#!/usr/bin/env bash
# Runs real downstream callers' CI jobs under act against this tree (or REF), so a changed
# default or input contract fails here instead of across the fleet after a pin bump.
# Usage: scripts/act-callers.sh [REF]   (default: the working tree's HEAD)
# ACT_CALLERS_ONLY=substr limits the run to matching callers (and skips the self-tests); logs stay
# in ~/.cache/act-callers. ACT_CALLERS_SELFTEST=only runs just the self-tests, =0 skips them.
# Callers: scripts/act-callers.txt, one "Org/repo workflow job [act args...]" per line. A caller
# pinning a tag instead of a 40-hex sha is skipped, which blocks the stamp.
# A ref whose sha is already stamped exits at once (the pre-push hook reruns this after the full pass).
# Self-tests: ci.yml's Linux jobs, run on a rewritten committed copy of REF with a fresh cache dir.
# A full pass (self-tests and every caller ran and passed, none skipped, no ACT_CALLERS_ONLY) stamps REF's sha into
# ~/.cache/nomad-hud/act-stamp, which nomad-hud's guard requires before a push, tag or pin bump.
set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
ref=${1:-HEAD}
src=${ACT_CALLERS_SRC:-$(bosun roots 2>/dev/null | grep com.github | head -1)}
src=${src:-/usr/local/src/com.github}
logs=${XDG_CACHE_HOME:-$HOME/.cache}/act-callers
only=${ACT_CALLERS_ONLY:-}
selftest=${ACT_CALLERS_SELFTEST:-}
mkdir -p "$logs"
for t in act docker; do
  command -v "$t" >/dev/null || {
    echo "act-callers: $t not installed" >&2
    exit 1
  }
done

# The pre-push hook reruns this after a stamped full pass; a push that waits that long outlives its ssh session.
stamp=$HOME/.cache/nomad-hud/act-stamp
if [ -z "$only" ] && [ -z "$selftest" ] && [ "$(cat "$stamp" 2>/dev/null)" = "$(git -C "$here" rev-parse "$ref")" ]; then
  echo "act-callers: $ref already passed in full, stamp is current"
  exit 0
fi

tmp=$(mktemp -d "${TMPDIR:-/var/tmp}/act-callers.XXXXXX")
trap 'rm -rf --one-file-system -- "$tmp"' EXIT
mkdir "$tmp/tree"
git -C "$here" archive "$ref" | tar -x -C "$tmp/tree"
sha=$(git -C "$here" rev-parse "$ref")

# act cannot parse `uses: $/...` (same-repo reference), so a copy points those at the pinned sha.
rewrite_self_refs() { sed -i -E "s#uses: \\\$/([^ ]+)#uses: Rethunk-Tech/gh-actions/\1@$2#" "$1"/*/action.yml; }

# act-latest lacks tools GitHub's ubuntu runner ships; add each one only when missing, so callers'
# own steps run as they do in CI. Docker's layer cache makes this a no-op after the first build.
image=act-callers-runner:latest
docker build -q -t "$image" - >/dev/null <<'DOCKERFILE'
FROM catthehacker/ubuntu:act-latest
RUN missing=""; for t in shellcheck; do command -v "$t" >/dev/null || missing="$missing $t"; done; \
    if [ -n "$missing" ]; then apt-get update && apt-get install -y --no-install-recommends $missing && rm -rf /var/lib/apt/lists/*; fi
RUN command -v rustup >/dev/null || { \
      curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain none; }
ENV PATH=/root/.cargo/bin:$PATH
RUN command -v google-chrome >/dev/null || { \
      curl -fsSLo /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
      apt-get update && apt-get install -y --no-install-recommends /tmp/chrome.deb && \
      rm -rf /tmp/chrome.deb /var/lib/apt/lists/*; }
DOCKERFILE

fail=0 ran=0 skipped=0 selftested=0
# ci.yml's self-tests are the only run of an action's own contract. Workarounds for act: the
# rewritten tree is committed (gorelease refuses a dirty repo), and every run gets a fresh cache
# dir because reset-self-test-caches needs `gh`, which the image lacks. Windows legs cannot run.
if [ -z "$only" ] && [ "$selftest" != 0 ]; then
  self="$tmp/self"
  cp -a "$tmp/tree" "$self"
  rewrite_self_refs "$self" "$sha"
  git -C "$self" init -q
  git -C "$self" add -A
  git -C "$self" -c user.name=act -c user.email=act@local commit -qm act
  log="$logs/self-tests.log"
  # all-checks needs the Windows jobs act skips, so it always fails; any other failed job counts.
  act_selftests() { (cd "$self" && act push -W .github/workflows/ci.yml --concurrent-jobs 1 --matrix os:ubuntu-latest \
    -P "ubuntu-latest=$image" --pull=false --rm --cache-server-path "$(mktemp -d "$tmp/cache.XXXXXX")" \
    --local-repository "Rethunk-Tech/gh-actions@$sha=$self"); }
  act_selftests >"$log" 2>&1 || true
  if ! grep -E "^Error: Job '.*' failed" "$log" | grep -qv "Job 'all-checks' failed" && grep -q "Job succeeded" "$log"; then
    echo "act-callers: ok   self-tests ci.yml"
    selftested=1
  else
    echo "act-callers: FAIL self-tests ci.yml"
    grep -E '❌|::error|Error:' "$log" | tail -8 >&2
    echo "act-callers: full log $log" >&2
    fail=1
  fi
fi

while read -r repo wf job extra; do
  case "$repo" in '' | '#'*) continue ;; esac
  [ -z "$only" ] || [[ $repo == *"$only"* ]] || continue
  dir="$src/$repo"
  if [ ! -d "$dir/.git" ]; then
    echo "act-callers: skip $repo (no clone at $dir)"
    skipped=$((skipped + 1))
    continue
  fi
  # Every gh-actions pin the caller uses maps to this tree, with `$/` pointed at the caller's pin.
  mapfile -t pins < <(grep -ho 'Rethunk-Tech/gh-actions/[^@]*@[0-9a-f]\{40\}' "$dir/.github/workflows/$wf" | sed 's/.*@//' | sort -u)
  [ ${#pins[@]} -gt 0 ] || {
    echo "act-callers: skip $repo (no gh-actions sha pin in $wf; a tag pin is not resolved)"
    skipped=$((skipped + 1))
    continue
  }
  args=()
  for p in "${pins[@]}"; do
    copy="$tmp/pin-$p"
    [ -d "$copy" ] || {
      cp -a "$tmp/tree" "$copy"
      rewrite_self_refs "$copy" "$p"
    }
    args+=(--local-repository "Rethunk-Tech/gh-actions@$p=$copy")
  done
  log="$logs/$(basename "$repo")-$job.log"
  ran=$((ran + 1))
  # shellcheck disable=SC2086 # extra holds the caller line's own act flags
  if (cd "$dir" && act push -W ".github/workflows/$wf" -j "$job" "${args[@]}" \
    -P "ubuntu-latest=$image" --pull=false --rm $extra) >"$log" 2>&1; then
    echo "act-callers: ok   $repo $wf/$job"
  else
    echo "act-callers: FAIL $repo $wf/$job"
    grep -E '❌|::error|Error:' "$log" | tail -8 >&2
    echo "act-callers: full log $log" >&2
    fail=1
  fi
done < <([ "$selftest" = only ] || cat "$here/scripts/act-callers.txt")

echo "act-callers: $ran caller job(s) run, $skipped skipped, ref $ref"
if [ "$fail" -eq 0 ] && [ "$selftested" -eq 1 ] && [ "$ran" -gt 0 ] && [ "$skipped" -eq 0 ] && [ -z "$only" ]; then
  mkdir -p "$(dirname "$stamp")"
  git -C "$here" rev-parse "$ref" >"$stamp.tmp"
  mv "$stamp.tmp" "$stamp"
fi
exit "$fail"
