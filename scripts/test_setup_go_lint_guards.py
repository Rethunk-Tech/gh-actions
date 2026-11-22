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
            self.assertIn("inputs.cache != 'false'", cond)

    def test_download_verifies_attestation(self) -> None:
        self.assertIn("gh attestation verify", ACTION)

    def test_prune_post_uses_node24(self) -> None:
        self.assertIn("using: node24", POST)


if __name__ == "__main__":
    unittest.main()
