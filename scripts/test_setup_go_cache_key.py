"""setup-go cache keys must hash listed module files, not a newline-joined hashFiles glob."""

from __future__ import annotations

import unittest
from pathlib import Path

ACTION = Path("setup-go/action.yml").read_text()


class SetupGoCacheKey(unittest.TestCase):
    def test_does_not_pass_newline_joined_deps_to_hashfiles(self) -> None:
        self.assertNotIn("hashFiles(steps.moddir.outputs.deps)", ACTION)

    def test_keys_use_hash_computed_in_the_resolve_step(self) -> None:
        self.assertIn("env.SETUP_GO_DEPS_HASH", ACTION)
        self.assertGreaterEqual(ACTION.count("env.SETUP_GO_DEPS_HASH"), 5)

    def test_single_caller_glob_still_uses_hashfiles(self) -> None:
        self.assertIn("hashFiles(inputs.cache-dependency-path)", ACTION)

    def test_hashes_with_shasum_so_macos_gets_a_key(self) -> None:
        self.assertNotIn("sha256sum", ACTION)
        self.assertEqual(ACTION.count('shasum -a 256 "$f"'), 1)
        self.assertIn("| shasum -a 256 |", ACTION)

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


class SetupGoBuildCachePrune(unittest.TestCase):
    def test_prune_is_not_linux_only(self) -> None:
        start = ACTION.index("Prune build cache to the saving job's working set")
        step = ACTION[start : ACTION.index("Restore golangci-lint cache", start)]
        self.assertNotIn("runner.os == 'Linux'", step)
        self.assertNotIn("-printf", step)
