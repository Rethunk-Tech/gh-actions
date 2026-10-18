"""Parser and compare tables for check-setup-bun-drift.py."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_setup_bun_drift",
    Path(__file__).resolve().parent / "check-setup-bun-drift.py",
)
assert _SPEC is not None and _SPEC.loader is not None
drift = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(drift)

PATH = Path("setup-bun/action.yml")
CORE = "version=$(node -e 'process.stdout.write(\"1\")')"
BUN_PW = "\n".join(
    (
        "if [ -f package.json ]; then",
        CORE,
        "else",
        "version=unpinned",
        "fi",
    )
)


def steps(playwright: str, cache_if: str | None) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for name in drift.WATCHED:
        if name == "Cache Bun install store":
            step: dict[str, object] = {"uses": "actions/cache@sha"}
            if cache_if is not None:
                step["if"] = cache_if
            out[name] = step
        elif name == "Resolve Playwright version":
            out[name] = {"run": playwright}
        else:
            out[name] = {"run": "shared"}
    return out


def pair(
    bun_pw: str = BUN_PW,
    next_pw: str = CORE,
    bun_if: str | None = drift.LOCKFILE_IF,
    next_if: str | None = None,
) -> dict[str, dict[str, dict[str, object]]]:
    return {
        "setup-bun": steps(bun_pw, bun_if),
        "setup-nextjs-bun": steps(next_pw, next_if),
    }


class ParseSteps(unittest.TestCase):
    def test_parse_steps(self) -> None:
        cases: list[tuple[str, str, object]] = [
            (
                "maps and blocks",
                """\
  steps:
    - name: Setup Bun
      uses: oven-sh/setup-bun@abc
      with:
        bun-version: 1.2.0
    - name: Cache extra paths
      run: |
        echo one
        echo two
""",
                {
                    "Setup Bun": {
                        "uses": "oven-sh/setup-bun@abc",
                        "with": {"bun-version": "1.2.0"},
                    },
                    "Cache extra paths": {"run": "echo one\necho two"},
                },
            ),
        ]
        for label, text, want in cases:
            with self.subTest(label):
                self.assertEqual(drift.parse_steps(text, PATH), want)

        deaths: list[tuple[str, str]] = [
            ("no steps", "runs:\n  using: composite\n"),
            (
                "duplicate",
                "  steps:\n    - name: A\n      run: x\n    - name: A\n      run: y\n",
            ),
            ("tab indent", "  steps:\n    - name: A\n\t\trun: x\n"),
            (
                "nested map",
                "  steps:\n    - name: A\n      with:\n        extra:\n          k: v\n",
            ),
        ]
        for label, text in deaths:
            with self.subTest(label):
                with self.assertRaises(SystemExit):
                    drift.parse_steps(text, PATH)


class CheckCacheIf(unittest.TestCase):
    def test_check_cache_if(self) -> None:
        cases: list[tuple[str, dict[str, str], dict[str, str], list[str]]] = [
            ("reviewed exception", {"if": drift.LOCKFILE_IF}, {}, []),
            (
                "next grew an if",
                {"if": drift.LOCKFILE_IF},
                {"if": "true"},
                [
                    "Cache Bun install store grew an if on setup-nextjs-bun (true); review it explicitly"
                ],
            ),
            (
                "both unset",
                {},
                {},
                [
                    "Cache Bun install store if matches (both unset); remove the lockfile exception"
                ],
            ),
            (
                "wrong bun if",
                {"if": "true"},
                {},
                [
                    "Cache Bun install store if on setup-bun must stay "
                    f"{drift.LOCKFILE_IF!r}, got 'true'"
                ],
            ),
        ]
        for label, left, right, want in cases:
            with self.subTest(label):
                errors: list[str] = []
                drift.check_cache_if(left, right, errors)
                self.assertEqual(errors, want)


class CheckPlaywrightRun(unittest.TestCase):
    def test_check_playwright_run(self) -> None:
        cases: list[tuple[str, str, str, bool]] = [
            ("reviewed exception", BUN_PW, CORE, True),
            ("cores differ", BUN_PW, "other", False),
            ("guards now match", BUN_PW, BUN_PW, False),
            (
                "bun guard is not the reviewed check",
                "if [ -f package.json ]; then\n" + CORE,
                CORE,
                False,
            ),
        ]
        for label, bun_run, next_run, ok in cases:
            with self.subTest(label):
                errors: list[str] = []
                drift.check_playwright_run({"run": bun_run}, {"run": next_run}, errors)
                self.assertEqual(errors == [], ok)


class Compare(unittest.TestCase):
    def test_compare(self) -> None:
        missing = pair()
        del missing["setup-bun"]["Setup Bun"]
        reordered = pair()
        reordered["setup-nextjs-bun"] = {
            name: reordered["setup-nextjs-bun"][name]
            for name in reversed(list(reordered["setup-nextjs-bun"]))
        }
        field_drift = pair()
        field_drift["setup-nextjs-bun"]["Setup Bun"] = {"run": "other"}

        cases: list[tuple[str, dict[str, dict[str, dict[str, object]]], bool]] = [
            ("matching reviewed exceptions", pair(), True),
            ("missing shared step", missing, False),
            ("watched order differs", reordered, False),
            ("non-special field differs", field_drift, False),
        ]
        for label, parsed, ok in cases:
            with self.subTest(label):
                self.assertEqual(drift.compare(parsed) == [], ok)


if __name__ == "__main__":
    unittest.main()
