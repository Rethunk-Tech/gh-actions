"""Path writes and ::error:: payloads must not carry raw CR/LF/% into workflow commands."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "github-workflow-io.sh"

ENCODE_CASES = (
    ("plain", "plain"),
    ("a%b", "a%25b"),
    ("a\nb%", "a%0Ab%25"),
    ("a\rb", "a%0Db"),
    ("%0A::add-path::/tmp/evil", "%250A::add-path::/tmp/evil"),
)

INTERPOLATED_ERROR = (
    Path("setup-bun/action.yml"),
    Path("setup-nextjs-bun/action.yml"),
    Path("setup-go/action.yml"),
    Path("setup-rust/action.yml"),
)

PATH_WRITES = (
    (
        Path("setup-bun/action.yml"),
        "working-directory",
        "path=$WORKING_DIRECTORY/package.json",
    ),
    (
        Path("setup-nextjs-bun/action.yml"),
        "working-directory",
        "path=$WORKING_DIRECTORY/package.json",
    ),
    (
        Path("setup-nextjs-bun/action.yml"),
        "next-app-directory",
        "NEXT_APP_DIR=${NEXT_APP_DIR}",
    ),
    (Path("setup-go/action.yml"), "go-version-file", 'dir=$(dirname "$path")'),
)


def run_helper(*args: str, extra: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            "-c",
            f'. "{HELPER}"\n{extra}',
            "github-workflow-io",
            *args,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


class GithubWorkflowIo(unittest.TestCase):
    def test_encode_matches_annotation_order(self) -> None:
        for raw, want in ENCODE_CASES:
            with self.subTest(raw=raw):
                proc = run_helper(raw, extra='github_encode "$1"; echo')
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout.rstrip("\n"), want)

    def test_require_single_line_rejects_cr_lf(self) -> None:
        for raw in ("a\nb", "a\rb"):
            with self.subTest(raw=raw):
                proc = run_helper(
                    "working-directory",
                    raw,
                    extra='github_require_single_line "$1" "$2"',
                )
                self.assertEqual(proc.returncode, 1)
                self.assertIn(
                    "::error::working-directory contains a carriage return or newline",
                    proc.stderr,
                )
                self.assertNotIn("::add-path::", proc.stderr)
                self.assertNotIn(raw, proc.stderr)

    def test_require_single_line_accepts_a_path(self) -> None:
        proc = run_helper(
            "working-directory",
            "apps/web",
            extra='github_require_single_line "$1" "$2"',
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_interpolated_error_lines_run_through_github_encode(self) -> None:
        for path in INTERPOLATED_ERROR:
            text = path.read_text()
            with self.subTest(path=str(path)):
                self.assertIn("github_encode", text)
                self.assertNotRegex(
                    text,
                    r'echo "::error::\$[A-Za-z_]',
                )

    def test_path_env_writes_reject_cr_lf_first(self) -> None:
        for path, name, write in PATH_WRITES:
            text = path.read_text()
            with self.subTest(path=str(path), name=name):
                self.assertIn(f"github_require_single_line {name} ", text)
                require_at = text.index(f"github_require_single_line {name} ")
                write_at = text.index(write)
                self.assertLess(require_at, write_at)
