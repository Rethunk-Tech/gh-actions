"""Fail when setup-bun and setup-nextjs-bun diverge on shared steps.

setup-nextjs-bun duplicates those steps instead of composing setup-bun (see
AGENTS.md). A difference is allowed only where this file names it. Delete an
exception once the two sides match again.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIONS = ("setup-bun", "setup-nextjs-bun")
WATCHED = (
    "Setup Bun",
    "Cache Bun install store",
    "Resolve Playwright version",
    "Cache Playwright browsers",
    "Install Playwright",
    "Install Playwright system deps",
)
SKIP_INSTALL_CLAUSE = "inputs.skip-install != 'true' && "
LOCKFILE_IF = "steps.lockfile.outputs.present == 'true'"
PACKAGE_JSON_GUARD = (
    "if [ -f package.json ]; then",
    "else",
    "version=unpinned",
    "fi",
)
BLOCK_MARKS = ("|", "|-", ">", ">-")

# Fields handled below, so the generic compare does not also flag them.
SPECIAL = {
    ("Setup Bun", "with.bun-version-file"),
    ("Cache Bun install store", "if"),
    ("Resolve Playwright version", "run"),
}


def die(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def indent_of(line: str) -> int:
    stripped = line.lstrip(" ")
    if stripped[:1] == "\t" or (line[: len(line) - len(stripped)] and "\t" in line):
        die(f"tab indent in action.yml: {line!r}")
    return len(line) - len(stripped)


def is_comment(line: str) -> bool:
    return line.lstrip(" ").startswith("#")


def steps_body(text: str, path: Path) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index("  steps:") + 1
    except ValueError:
        die(f"{path}: no runs.steps block")
    body: list[str] = []
    for line in lines[start:]:
        if line.strip() and not is_comment(line) and indent_of(line) < 4:
            break
        body.append(line)
    return body


def parse_steps(text: str, path: Path) -> dict[str, dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    name: str | None = None
    chunk: list[str] = []

    def finish() -> None:
        if name is None:
            return
        if name in found:
            die(f"{path}: duplicate step {name!r}")
        found[name] = parse_step(chunk, path, name)

    for line in steps_body(text, path):
        match = re.match(r"^    - name: (.*)$", line)
        if match:
            finish()
            name = match.group(1).strip()
            chunk = []
        elif name is not None:
            chunk.append(line)
    finish()
    return found


def parse_step(lines: list[str], path: Path, name: str) -> dict[str, object]:
    step: dict[str, object] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or is_comment(line):
            i += 1
            continue
        if indent_of(line) != 6:
            die(f"{path}: {name}: unexpected line: {line}")
        key, _, rest = line.lstrip().partition(":")
        rest = rest.strip()
        if rest in BLOCK_MARKS:
            step[key], i = read_block(lines, i + 1, 6)
        elif rest == "":
            step[key], i = read_map(lines, i + 1, 6, path, name)
        else:
            step[key] = rest
            i += 1
    return step


def read_block(lines: list[str], i: int, parent: int) -> tuple[str, int]:
    raw: list[str] = []
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            raw.append("")
            i += 1
            continue
        if indent_of(line) <= parent:
            break
        raw.append(line)
        i += 1
    while raw and raw[-1] == "":
        raw.pop()
    if not raw:
        return "", i
    width = min(indent_of(line) for line in raw if line)
    return "\n".join(line[width:] if line else "" for line in raw).strip(), i


def read_map(
    lines: list[str], i: int, parent: int, path: Path, name: str
) -> tuple[dict[str, str], int]:
    mapping: dict[str, str] = {}
    while i < len(lines):
        line = lines[i]
        if not line.strip() or is_comment(line):
            i += 1
            continue
        if indent_of(line) <= parent:
            break
        key, _, rest = line.lstrip().partition(":")
        rest = rest.strip()
        if rest in BLOCK_MARKS:
            mapping[key], i = read_block(lines, i + 1, indent_of(line))
        elif rest == "":
            die(f"{path}: {name}: nested map under {key} is not a shared-step shape")
        else:
            mapping[key] = rest
            i += 1
    return mapping, i


def fields(step: dict[str, object]) -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in step.items():
        if isinstance(value, dict):
            for child, child_value in value.items():
                flat[f"{key}.{child}"] = child_value
        elif isinstance(value, str):
            flat[key] = value.strip() if key == "run" else value
    return flat


def norm_run(script: str) -> list[str]:
    return [line.strip() for line in script.splitlines() if line.strip()]


def check_version_file(
    left: dict[str, str], right: dict[str, str], errors: list[str]
) -> None:
    bun = left.get("with.bun-version-file")
    nxt = right.get("with.bun-version-file")
    if bun is None or nxt is None:
        errors.append("Setup Bun is missing with.bun-version-file")
        return
    if SKIP_INSTALL_CLAUSE in nxt:
        errors.append(
            "setup-nextjs-bun bun-version-file references skip-install, which it does not have"
        )
        return
    if SKIP_INSTALL_CLAUSE not in bun:
        if bun == nxt:
            errors.append(
                "Setup Bun with.bun-version-file matches; remove the skip-install exception"
            )
        else:
            errors.append(
                "Setup Bun with.bun-version-file diverged and the skip-install clause is gone"
            )
        return
    if bun.replace(SKIP_INSTALL_CLAUSE, "", 1) != nxt:
        errors.append(
            "Setup Bun with.bun-version-file differs by more than the skip-install clause\n"
            f"  setup-bun: {bun}\n  setup-nextjs-bun: {nxt}"
        )


def check_cache_if(
    left: dict[str, str], right: dict[str, str], errors: list[str]
) -> None:
    bun = left.get("if")
    nxt = right.get("if")
    if nxt is not None:
        errors.append(
            f"Cache Bun install store grew an if on setup-nextjs-bun ({nxt}); review it explicitly"
        )
        return
    if bun == LOCKFILE_IF:
        return
    if bun is None:
        errors.append(
            "Cache Bun install store if matches (both unset); remove the lockfile exception"
        )
    else:
        errors.append(
            f"Cache Bun install store if on setup-bun must stay {LOCKFILE_IF!r}, got {bun!r}"
        )


def check_playwright_run(
    left: dict[str, str], right: dict[str, str], errors: list[str]
) -> None:
    bun_lines = norm_run(left.get("run", ""))
    next_lines = norm_run(right.get("run", ""))

    def split(lines: list[str]) -> tuple[list[str], list[str]]:
        guard = [line for line in lines if line in PACKAGE_JSON_GUARD]
        core = [line for line in lines if line not in PACKAGE_JSON_GUARD]
        return core, guard

    bun_core, bun_guard = split(bun_lines)
    next_core, next_guard = split(next_lines)
    if bun_core != next_core:
        errors.append(
            "Resolve Playwright version differs beyond the missing-package.json guard\n"
            f"  setup-bun: {bun_core}\n  setup-nextjs-bun: {next_core}"
        )
        return
    if bun_guard == next_guard:
        errors.append(
            "Resolve Playwright version package.json guard now matches; remove that exception"
        )
        return
    if tuple(bun_guard) != PACKAGE_JSON_GUARD or next_guard:
        errors.append(
            "Resolve Playwright version guard is not the reviewed setup-bun-only package.json check\n"
            f"  setup-bun guard: {bun_guard}\n  setup-nextjs-bun guard: {next_guard}"
        )


def compare(parsed: dict[str, dict[str, dict[str, object]]]) -> list[str]:
    errors: list[str] = []
    orders: dict[str, list[str]] = {}
    flat: dict[str, dict[str, dict[str, str]]] = {}
    for action in ACTIONS:
        steps = parsed[action]
        orders[action] = [name for name in steps if name in WATCHED]
        missing = [name for name in WATCHED if name not in steps]
        if missing:
            errors.append(f"{action} is missing shared steps: {', '.join(missing)}")
        flat[action] = {name: fields(steps[name]) for name in WATCHED if name in steps}
    if orders["setup-bun"] != orders["setup-nextjs-bun"]:
        errors.append(
            "shared steps are in a different order\n"
            f"  setup-bun: {orders['setup-bun']}\n"
            f"  setup-nextjs-bun: {orders['setup-nextjs-bun']}"
        )
    if errors:
        return errors

    pairs = (
        ("Setup Bun", check_version_file),
        ("Cache Bun install store", check_cache_if),
        ("Resolve Playwright version", check_playwright_run),
    )
    for step_name, checker in pairs:
        checker(
            flat["setup-bun"][step_name], flat["setup-nextjs-bun"][step_name], errors
        )

    for step_name in WATCHED:
        left = flat["setup-bun"][step_name]
        right = flat["setup-nextjs-bun"][step_name]
        for key in sorted(set(left) | set(right)):
            if (step_name, key) in SPECIAL:
                continue
            if left.get(key) != right.get(key):
                errors.append(
                    f"{step_name} {key} differs\n"
                    f"  setup-bun: {left.get(key)!r}\n"
                    f"  setup-nextjs-bun: {right.get(key)!r}"
                )
    return errors


def main() -> None:
    parsed = {
        action: parse_steps(
            (ROOT / action / "action.yml").read_text(), ROOT / action / "action.yml"
        )
        for action in ACTIONS
    }
    errors = compare(parsed)
    if errors:
        for message in errors:
            print(f"::error::{message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
