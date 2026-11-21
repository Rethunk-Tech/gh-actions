"""setup-go cache keys must hash listed module files, not a newline-joined hashFiles glob."""

from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ACTION = Path("setup-go/action.yml").read_text()
HELPER = Path("scripts/github-workflow-io.sh").resolve()


def _hash_listed_source() -> str:
    start = ACTION.index("hash_listed() {")
    end = ACTION.index("\n        }\n", start)
    return textwrap.dedent(ACTION[start : end + len("\n        }")])


def _run_hash_listed(tree: Path, listed: str) -> str:
    script = (
        f'. "{HELPER}"\n'
        f"{_hash_listed_source()}\n"
        'printf "%s\\n" "$LISTED" | hash_listed\n'
    )
    env = os.environ.copy()
    env["LISTED"] = listed
    result = subprocess.run(
        ["bash", "-c", script],
        cwd=tree,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _module_tree(root: Path) -> None:
    for name in ("backend", "tools"):
        (root / name).mkdir()
        (root / name / "go.mod").write_text(f"module {name}\n")
        (root / name / "go.sum").write_text(f"{name} 1\n")


class SetupGoCacheKey(unittest.TestCase):
    def test_does_not_pass_newline_joined_deps_to_hashfiles(self) -> None:
        self.assertNotIn("hashFiles(steps.moddir.outputs.deps)", ACTION)

    def test_keys_use_hash_computed_in_the_resolve_step(self) -> None:
        self.assertIn("env.SETUP_GO_DEPS_HASH", ACTION)
        self.assertGreaterEqual(ACTION.count("env.SETUP_GO_DEPS_HASH"), 5)

    def test_single_caller_glob_still_uses_hashfiles(self) -> None:
        self.assertIn("hashFiles(inputs.cache-dependency-path)", ACTION)

    def test_hashes_through_the_portable_helper(self) -> None:
        # windows-latest has no shasum and macOS has no sha256sum.
        self.assertNotIn("shasum", ACTION)
        self.assertNotIn("sha256sum", ACTION)
        self.assertEqual(ACTION.count('github_sha256 "$f"'), 1)
        self.assertIn("| github_sha256 |", ACTION)

    def test_suffix_is_empty_by_default_and_on_the_primary_key_only(self) -> None:
        self.assertEqual(
            ACTION.count("inputs.cache-key-suffix &&"), 2
        )  # build and lint keys
        key = next(
            l
            for l in ACTION.splitlines()
            if l.strip().startswith("key: setup-go-${{ runner.os")
        )
        self.assertIn("inputs.cache-key-suffix", key)

    def test_multiline_globs_hash_nested_modules(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tree = Path(raw)
            _module_tree(tree)
            globs = "**/go.sum\n**/go.mod"
            first = _run_hash_listed(tree, globs)
            self.assertNotEqual(first, "no-modules")
            self.assertRegex(first, r"^[0-9a-f]{64}$")

            (tree / "backend" / "go.sum").write_text("backend 2\n")
            second = _run_hash_listed(tree, globs)
            self.assertNotEqual(second, first)

            literals = "\n".join(
                f"{name}/{fname}"
                for name in ("backend", "tools")
                for fname in ("go.mod", "go.sum")
            )
            self.assertEqual(second, _run_hash_listed(tree, literals))
            self.assertRegex(
                _run_hash_listed(tree, "backend/go.sum"), r"^[0-9a-f]{64}$"
            )


class SetupGoBuildCachePrune(unittest.TestCase):
    def test_prune_is_not_linux_only(self) -> None:
        start = ACTION.index("Prune build cache to the saving job's working set")
        step = ACTION[start : ACTION.index("Restore golangci-lint cache", start)]
        self.assertNotIn("runner.os == 'Linux'", step)
        self.assertNotIn("-printf", step)


class SetupGoRestoreKeys(unittest.TestCase):
    def test_restore_keys_prefer_the_same_job_before_any_job(self) -> None:
        lines = [l.strip() for l in ACTION.splitlines()]
        i = lines.index("key: setup-go-${{ runner.os }}-${{ runner.arch }}-go${{ steps.setup-go.outputs.go-version }}-${{ github.job }}.${{ env.SETUP_GO_DEPS_HASH }}${{ inputs.cache-key-suffix && format('-{0}', inputs.cache-key-suffix) || '' }}")
        self.assertEqual(lines[i + 1], "restore-keys: |")
        self.assertTrue(lines[i + 2].endswith("-${{ github.job }}.${{ env.SETUP_GO_DEPS_HASH }}"))
        self.assertTrue(lines[i + 3].endswith("-${{ github.job }}."))
        self.assertTrue(lines[i + 4].endswith("-go${{ steps.setup-go.outputs.go-version }}-"))
