"""Cache steps must not run on events that execute fork code against the base repo's cache."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = "github.event_name != 'pull_request_target' && github.event_name != 'workflow_run'"
ACTIONS = ("setup-bun", "setup-nextjs-bun", "setup-go", "setup-rust")


class CacheTrust(unittest.TestCase):
    def test_every_cache_step_is_guarded_and_keyed_by_arch(self) -> None:
        for action in ACTIONS:
            text = (ROOT / action / "action.yml").read_text()
            steps = re.split(r"^    - name: ", text, flags=re.M)[1:]
            cache = [s for s in steps if "uses: actions/cache" in s and "cache/save" not in s]
            self.assertTrue(cache, action)
            for s in cache:
                with self.subTest(action=action, step=s.splitlines()[0]):
                    self.assertIn(GUARD, s)
                    self.assertIn("runner.arch", s)

    def test_floating_major_requires_a_commit_on_main(self) -> None:
        text = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn('git merge-base --is-ancestor "$TAG^{commit}" origin/main', text)


if __name__ == "__main__":
    unittest.main()
