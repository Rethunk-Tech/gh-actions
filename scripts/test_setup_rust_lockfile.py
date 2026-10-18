"""setup-rust must refuse a missing Cargo.lock rather than key the cache on an empty hash."""

from __future__ import annotations

import unittest
from pathlib import Path

ACTION = Path("setup-rust/action.yml").read_text()


class SetupRustLockfile(unittest.TestCase):
    def test_fails_closed_when_cargo_lock_is_absent(self) -> None:
        self.assertIn(
            "Cargo.lock not found — refusing to build a cache key from a missing lockfile",
            ACTION,
        )
