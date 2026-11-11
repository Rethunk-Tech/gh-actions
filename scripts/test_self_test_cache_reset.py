"""Cold self-tests must wipe caches GitHub would restore from the base branch, not only this ref."""

from __future__ import annotations

import pathlib
import unittest

CI = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _reset_job(text: str) -> str:
    start = text.index("  reset-self-test-caches:")
    end = text.index("  test-setup-bun-cold:")
    return text[start:end]


class TestSelfTestCacheReset(unittest.TestCase):
    def test_reset_wipes_base_and_default_branch_caches(self) -> None:
        body = _reset_job(CI.read_text())
        self.assertIn("GITHUB_BASE_REF", body)
        self.assertIn("DEFAULT_BRANCH", body)
        self.assertIn("github.event.repository.default_branch", body)
        # A single --ref "$GITHUB_REF" leaves main's caches visible to a PR restore.
        self.assertNotIn('--ref "$GITHUB_REF"', body)
        self.assertIn('--ref "$ref"', body)


if __name__ == "__main__":
    unittest.main()
