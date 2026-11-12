#!/usr/bin/env python3
"""Fail if a tag's GitHub Release is dropped or the floating major lands on an older tag.

GitHub keeps one pending run per concurrency group, so putting every tag in
`${{ github.workflow }}` drops a middle tag's Release. The move-major job
serializes on that shared group; a per-ref group there lets two moves run at
once, and the older job's fetch-depth-0 checkout can omit the newer tag and
overwrite vN last.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
SHARED_GROUP = "${{ github.workflow }}"


def top_level_concurrency_group(text: str) -> str | None:
    match = re.search(r"^concurrency:\n  group: (.+)$", text, re.M)
    return match.group(1).strip() if match else None


def job_concurrency_group(text: str, job: str) -> str | None:
    match = re.search(
        rf"^  {re.escape(job)}:\n(?:    .+\n)*    concurrency:\n(?:      #.*\n)*      group: (.+)$",
        text,
        re.M,
    )
    return match.group(1).strip() if match else None


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
        text = WORKFLOW.read_text()
        self.assertNotEqual(top_level_concurrency_group(text), SHARED_GROUP)
        self.assertNotEqual(job_concurrency_group(text, "release"), SHARED_GROUP)
        group = job_concurrency_group(text, "move-major")
        self.assertEqual(group, SHARED_GROUP)
        floating: dict[str, str] = {}

        if group is not None and "github.ref" in group:
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
