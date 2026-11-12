#!/usr/bin/env python3
"""Fail if overlapping Release jobs can leave the floating major on an older tag.

The move-major step force-pushes vN when this tag looks newest in that job's
checkout. A per-ref concurrency group lets two tag jobs run at once; the older
job's fetch-depth-0 checkout can omit the newer tag and overwrite vN last.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def concurrency_group(text: str) -> str:
    match = re.search(r"^concurrency:\n  group: (.+)$", text, re.M)
    if not match:
        raise AssertionError("release.yml: missing concurrency.group")
    return match.group(1).strip()


def newest(tags: list[str], major: str) -> str:
    pattern = re.compile(rf"^{re.escape(major)}\.[0-9]+(\.[0-9]+)?$")

    def version_key(tag: str) -> tuple[int, ...]:
        return tuple(int(part) for part in tag.lstrip("v").split("."))

    matching = [tag for tag in tags if pattern.match(tag)]
    return sorted(matching, key=version_key, reverse=True)[0]


def move_major(visible: list[str], this_tag: str, floating: dict[str, str]) -> None:
    match = re.fullmatch(r"(v[0-9]+)\.[0-9]+(\.[0-9]+)?", this_tag)
    if not match:
        return
    major = match.group(1)
    if newest(visible, major) != this_tag:
        return
    floating[major] = this_tag


class ReleaseMajorTagRace(unittest.TestCase):
    def test_overlapping_jobs_leave_vN_on_newest(self) -> None:
        group = concurrency_group(WORKFLOW.read_text())
        floating: dict[str, str] = {}

        if "github.ref" in group:
            # Overlap: v1.10 checked out before v1.11 existed; its force-push lands last.
            move_major(["v1.10"], "v1.10", floating)
            move_major(["v1.10", "v1.11"], "v1.11", floating)
            move_major(["v1.10"], "v1.10", floating)
        else:
            # Shared group serializes: the later job's checkout sees every v1.* tag.
            move_major(["v1.10"], "v1.10", floating)
            move_major(["v1.10", "v1.11"], "v1.11", floating)
            move_major(["v1.10", "v1.11"], "v1.10", floating)

        self.assertEqual(floating.get("v1"), "v1.11")


if __name__ == "__main__":
    unittest.main()
