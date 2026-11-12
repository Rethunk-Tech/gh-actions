"""setup-rust must add components and targets to the toolchain the repo pins, not the default."""

from __future__ import annotations

import importlib.util
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

PINNED = "1.90.0-x86_64-unknown-linux-gnu"

RUSTUP = f"""#!/bin/sh
echo "rustup $*" >> "$RUSTUP_LOG"
case " $* " in
  *" set profile "*|*" install "*|*" update "*|*" default "*) ;;
  *" show active-toolchain "*) echo "{PINNED} (default)" ;;
esac
"""

RUSTC = """#!/bin/sh
case "$1" in
  -vV) echo 'host: x86_64-unknown-linux-gnu' ;;
esac
"""


class InstallRustToolchain(unittest.TestCase):
    def test_components_and_targets_follow_the_toolchain_file(self) -> None:
        path = ROOT / "setup-rust" / "action.yml"
        step = drift.parse_steps(path.read_text(), path)["Install Rust toolchain"]
        script = drift.fields(step)["run"]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "rust-toolchain.toml").write_text(
                '[toolchain]\nchannel = "1.90"\n'
            )
            (tmp_path / "bin").mkdir()
            for name, body in (("rustup", RUSTUP), ("rustc", RUSTC)):
                stub = tmp_path / "bin" / name
                stub.write_text(body)
                stub.chmod(0o755)
            log = tmp_path / "rustup.log"
            env = {
                **os.environ,
                "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
                "RUSTUP_LOG": str(log),
                "GITHUB_OUTPUT": str(tmp_path / "output"),
                "GITHUB_ENV": str(tmp_path / "env"),
                "COMPONENTS": "clippy",
                "TARGETS": "aarch64-unknown-linux-gnu",
                "RUN_CLIPPY": "true",
                "RUN_FMT": "false",
                "TOOLCHAIN": "",
                "CARGO_HOME": str(tmp_path / "cargo"),
                "CARGO_TARGET_DIR": "",
            }
            subprocess.run(
                ["bash", "-e", "-c", script],
                cwd=tmp_path,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            calls = log.read_text().splitlines()

        selected = f"--toolchain {PINNED}"
        self.assertTrue(
            any(c.startswith(f"rustup component add {selected} clippy") for c in calls),
            calls,
        )
        self.assertTrue(
            any(
                c.startswith(f"rustup target add {selected} aarch64-unknown-linux-gnu")
                for c in calls
            ),
            calls,
        )


if __name__ == "__main__":
    unittest.main()
