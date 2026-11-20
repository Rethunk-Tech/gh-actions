"""act-callers.sh takes its clone root from `bosun roots` unless ACT_CALLERS_SRC is set."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "act-callers.sh"


def _stub(directory: Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class ActCallersSrc(unittest.TestCase):
    def run_script(self, bosun: str, env_src: str | None = None) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            _stub(bin_dir, "act", "exit 0")
            _stub(bin_dir, "docker", "exit 0")
            _stub(bin_dir, "bosun", bosun)
            env = {
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "ACT_CALLERS_ONLY": "dom-input-nav",
                "XDG_CACHE_HOME": str(Path(tmp) / "cache"),
                "TMPDIR": tmp,
            }
            env.pop("ACT_CALLERS_SRC", None)
            if env_src:
                env["ACT_CALLERS_SRC"] = env_src
            done = subprocess.run(
                ["bash", str(SCRIPT), "HEAD"], env=env, capture_output=True, text=True
            )
            return done.stdout + done.stderr

    def test_bosun_roots_first_com_github_line(self) -> None:
        out = self.run_script('printf "/nope\\n/x/com.github\\n"')
        self.assertIn("no clone at /x/com.github/Rethunk-Tech/dom-input-nav", out)

    def test_env_wins_over_bosun(self) -> None:
        out = self.run_script("echo /x/com.github", env_src="/env/src")
        self.assertIn("no clone at /env/src/Rethunk-Tech/dom-input-nav", out)


if __name__ == "__main__":
    unittest.main()
