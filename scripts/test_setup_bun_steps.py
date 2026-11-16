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

    def test_range_resolves_to_installed_version(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                script = step(action, "Resolve Playwright version")["run"]
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_path = Path(tmp)
                    (tmp_path / "package.json").write_text(
                        json.dumps({"devDependencies": {"@playwright/test": "^1.60.0"}})
                    )
                    pkg = tmp_path / "node_modules" / "@playwright" / "test"
                    pkg.mkdir(parents=True)
                    (pkg / "package.json").write_text(
                        json.dumps({"name": "@playwright/test", "version": "1.65.1"})
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
                    self.assertIn("version=1.65.1", output.read_text().splitlines())

    def test_exact_version_stays_pinned(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                self.assertIn("version=1.64.1", self.resolve(action, "1.64.1"))


class PlaywrightCacheHitEmptyDir(unittest.TestCase):
    def probe(self, action: str, browsers: str) -> str:
        script = step(action, "Install Playwright")["run"]
        wrapper = (
            'bunx() { echo "WOULD_INSTALL missing=${missing-?} argc=$#"; exit 0; }\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / ".cache" / "ms-playwright").mkdir(parents=True)
            result = subprocess.run(
                ["bash", "-e", "-c", wrapper + script],
                env={
                    **os.environ,
                    "HOME": str(home),
                    "PLAYWRIGHT_BROWSERS": browsers,
                    "PLAYWRIGHT_CACHE_HIT": "true",
                    "PLAYWRIGHT_VERSION": "1.64.1",
                },
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout

    def test_empty_cache_installs_default_set(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                out = self.probe(action, "")
                self.assertIn("WOULD_INSTALL", out)
                self.assertNotIn("restored from cache", out)

    def test_named_chromium_missing_installs(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                out = self.probe(action, "chromium")
                self.assertIn("WOULD_INSTALL", out)
                self.assertNotIn("restored from cache", out)


class ExtraCacheKey(unittest.TestCase):
    def test_key_separates_different_path_sets(self) -> None:
        for action in drift.ACTIONS:
            with self.subTest(action):
                spec = step(action, "Cache extra paths")
                self.assertIn("steps.extra-paths-hash.outputs.hash", spec["with.key"])
                self.assertIn(
                    "steps.extra-paths-hash.outputs.hash", spec["with.restore-keys"]
                )


if __name__ == "__main__":
    unittest.main()
