"""setup-go/prune-build-cache.sh keeps entries within two hours of the newest and removes the rest."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path("setup-go/prune-build-cache.sh").resolve()


class PruneBuildCache(unittest.TestCase):
    def test_keeps_the_newest_two_hours(self) -> None:
        with tempfile.TemporaryDirectory(prefix="go build ") as root:
            now = int(time.time())
            ages = {"ab/new-d": 0, "ab/hour-d": 3600, "cd/edge-d": 7100, "cd/old-d": 7300, "ef/week-d": 604800}
            for name, age in ages.items():
                path = Path(root, name)
                path.parent.mkdir(exist_ok=True)
                path.write_text("x")
                os.utime(path, (now - age, now - age))
            subprocess.run(["bash", str(SCRIPT), root], check=True, capture_output=True)
            left = sorted(str(p.relative_to(root)) for p in Path(root).rglob("*") if p.is_file())
            self.assertEqual(left, ["ab/hour-d", "ab/new-d", "cd/edge-d"])

    def test_a_missing_cache_is_not_an_error(self) -> None:
        subprocess.run(["bash", str(SCRIPT), "/nonexistent/go-build"], check=True)


if __name__ == "__main__":
    unittest.main()
