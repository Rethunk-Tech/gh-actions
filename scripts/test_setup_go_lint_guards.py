"""setup-go: lint cache honours cache=false, lint download is attested, post action runs on node24."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ACTION = Path("setup-go/action.yml").read_text()
POST = Path("setup-go/prune-post/action.yml").read_text()


class SetupGoLintGuards(unittest.TestCase):
    def test_lint_cache_steps_skip_when_cache_is_off(self) -> None:
        conds = re.findall(r"- name: (?:Restore|Save) golangci-lint cache\n\s+(?:id: .*\n\s+)?if: (.+)", ACTION)
        self.assertEqual(len(conds), 2)
        for cond in conds:
            self.assertIn("inputs.cache == 'true'", cond)

    def test_download_verifies_attestation(self) -> None:
        self.assertIn("gh attestation verify", ACTION)

    def test_prune_post_uses_node24(self) -> None:
        self.assertIn("using: node24", POST)


class CacheInputDefaultsOffOnTags(unittest.TestCase):
    def test_every_setup_action_gates_its_caches_on_tag_and_release(self) -> None:
        for name in ("setup-go", "setup-rust", "setup-bun", "setup-nextjs-bun", "setup-python"):
            text = Path(name, "action.yml").read_text()
            self.assertRegex(text, r"(?m)^  cache:\n(?:    .*\n)*?    default: \"\"\n", name)
            self.assertIn("github.ref_type != 'tag' && github.event_name != 'release'", text, name)
            self.assertNotRegex(text, r"if: [^\n]*uses: actions/cache", name)

    def test_race_tests_do_not_sleep_at_exit(self) -> None:
        self.assertIn("GORACE: atexit_sleep_ms=0", ACTION)


if __name__ == "__main__":
    unittest.main()
