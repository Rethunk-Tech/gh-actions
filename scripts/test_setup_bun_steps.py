"""Step behaviour shared by setup-bun and setup-nextjs-bun."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
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


class PlaywrightVersionPin(unittest.TestCase):
    def resolve(self, action: str, spec: str) -> list[str]:
        script = step(action, "Resolve Playwright version")["run"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "package.json").write_text(
                json.dumps({"devDependencies": {"@playwright/test": spec}})
            )
            output = tmp_path / "output"
            output.write_text("")
            subprocess.run(
                ["bash", "-e", "-c", script],
                cwd=tmp_path,
                env={**os.environ, "GITHUB_OUTPUT": str(output)},
                check=True,
                capture_output=True,
                text=True,
            )
            return output.read_text().splitlines()

    def test_non_semver_spec_is_unpinned(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                self.assertIn("version=unpinned", self.resolve(action, "catalog:"))

    def test_exact_version_stays_pinned(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                self.assertIn("version=1.64.1", self.resolve(action, "1.64.1"))


if __name__ == "__main__":
    unittest.main()
