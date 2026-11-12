"""Step behaviour shared by setup-bun and setup-nextjs-bun."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "check_setup_bun_drift", ROOT / "scripts" / "check-setup-bun-drift.py"
)
assert _SPEC is not None and _SPEC.loader is not None
drift = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(drift)


def step(action: str, name: str) -> dict[str, str]:
    path = ROOT / action / "action.yml"
    return drift.fields(drift.parse_steps(path.read_text(), path)[name])


class PlaywrightCacheKey(unittest.TestCase):
    def test_key_covers_browser_set_and_arch(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                key = step(action, "Cache Playwright browsers")["with.key"]
                self.assertIn("runner.arch", key)
                self.assertIn("steps.playwright-version.outputs.browsers", key)


if __name__ == "__main__":
    unittest.main()
