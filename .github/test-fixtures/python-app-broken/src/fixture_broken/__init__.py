# `os` is never used: ruff's default rule set flags unused imports. Imports cleanly at runtime,
# so only the lint gate can catch it.
import os


def add(a: int, b: int) -> int:
    return a + b
