#!/usr/bin/env bash
# Shared by composite action run: steps. Source from
# "${GITHUB_ACTION_PATH}/../scripts/github-workflow-io.sh".
# Matches audit-bun/annotation(): workflow commands still interpret %0A/%0D/%25.

github_encode() {
  local s=$1
  s=${s//'%'/'%25'}
  s=${s//$'\r'/'%0D'}
  s=${s//$'\n'/'%0A'}
  printf '%s' "$s"
}

# Reject CR/LF in a caller-controlled path before echo key=$value to
# GITHUB_ENV / GITHUB_OUTPUT. The name is a literal input id, not interpolated
# into a workflow command from untrusted text.
github_require_single_line() {
  case "$2" in
    *$'\n'* | *$'\r'*)
      echo "::error::$1 contains a carriage return or newline" >&2
      exit 1
      ;;
  esac
}

# sha256sum (GNU coreutils: Linux and Git Bash on Windows) or shasum (macOS, which has no
# sha256sum). Both print "<hex>  <file>" and accept -c, so callers pass the same arguments.
github_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$@"
  else
    shasum -a 256 "$@"
  fi
}
