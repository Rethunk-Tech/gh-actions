# `os` is never used: ruff's default rule set flags it as F401. Imports cleanly at runtime,
# so only the lint gate can catch it.
import os


def add(a: int, b: int) -> int:
    return a + b
