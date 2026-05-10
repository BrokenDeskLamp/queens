"""Executable specification runner.

Discovers markdown spec files in ``docs/spec/`` and executes
annotated bash code blocks as CLI integration tests.

Each `` ```bash `` block is one test case. The first line starting
with ``$ `` is the command. Lines starting with ``# directive: value``
are assertions. Other ``# `` comments are documentation (ignored by
the runner).

Supported directives:

    # exit: N           — expect exit code N (default: 0)
    # stdout: text      — stdout must contain ``text``
    # stdout!: text     — stdout must NOT contain ``text``
    # stderr: text      — stderr must contain ``text``
    # stderr!: text     — stderr must NOT contain ``text``

All tests run from the project root so ``uv run queens`` resolves.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

SPEC_DIR = Path(__file__).parent.parent / "docs" / "spec"
PROJECT_ROOT = Path(__file__).parent.parent


def _parse_spec(md_file: Path) -> list[tuple[str, str, dict[str, object]]]:
    """Parse a spec markdown file, returning (test_id, command, assertions) tuples."""
    text = md_file.read_text()

    # Find all ```bash blocks
    blocks = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)

    test_cases: list[tuple[str, str, dict[str, object]]] = []
    for idx, block in enumerate(blocks):
        lines = block.strip().split("\n")

        command: str | None = None
        assertions: dict[str, object] = {
            "exit": 0,
            "stdout_contains": [],
            "stdout_not": [],
            "stderr_contains": [],
            "stderr_not": [],
        }

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("$ "):
                if command is None:
                    command = stripped[2:].strip()
                continue

            if stripped.startswith("# "):
                directive = stripped[2:].strip()
                if ":" not in directive:
                    continue  # doc comment, skip
                key, _, value = directive.partition(":")
                key = key.strip()
                value = value.strip()
                if key == "exit":
                    assertions["exit"] = int(value)
                elif key == "stdout":
                    assertions["stdout_contains"].append(value)
                elif key == "stdout!":
                    assertions["stdout_not"].append(value)
                elif key == "stderr":
                    assertions["stderr_contains"].append(value)
                elif key == "stderr!":
                    assertions["stderr_not"].append(value)
                # Unknown directives are silently ignored (future-proof)

        if command is not None:
            test_id = f"{md_file.stem}[{idx}]"
            test_cases.append((test_id, command, assertions))

    return test_cases


def _discover_specs() -> list[tuple[str, str, dict[str, object]]]:
    """Collect all test cases from docs/spec/*.md files."""
    if not SPEC_DIR.exists():
        return []

    cases: list[tuple[str, str, dict[str, object]]] = []
    for md_file in sorted(SPEC_DIR.glob("*.md")):
        cases.extend(_parse_spec(md_file))
    return cases


SPEC_CASES = _discover_specs()


@pytest.mark.parametrize(
    ("test_id", "command", "assertions"),
    SPEC_CASES,
    ids=[c[0] for c in SPEC_CASES],
)
def test_spec(test_id: str, command: str, assertions: dict[str, object]) -> None:  # noqa: ARG001
    """Execute a CLI command and verify its output matches the spec."""
    result = subprocess.run(  # noqa: S602 — intentional for CLI integration tests
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=PROJECT_ROOT,
        check=False,
    )

    stdout = result.stdout
    stderr = result.stderr

    # ── Exit code ──────────────────────────────────────────────────
    expected_exit: int = assertions["exit"]  # type: ignore[assignment]
    assert result.returncode == expected_exit, (
        f"Exit code {result.returncode} != {expected_exit}\n"
        f"stdout:\n{stdout}\nstderr:\n{stderr}"
    )

    # ── Stdout assertions ──────────────────────────────────────────
    for pattern in assertions["stdout_contains"]:  # type: ignore[union-attr]
        assert pattern in stdout, (
            f"Expected stdout to contain: {pattern!r}\nstdout:\n{stdout}"
        )

    for pattern in assertions["stdout_not"]:  # type: ignore[union-attr]
        assert pattern not in stdout, (
            f"Expected stdout to NOT contain: {pattern!r}\nstdout:\n{stdout}"
        )

    # ── Stderr assertions ──────────────────────────────────────────
    for pattern in assertions["stderr_contains"]:  # type: ignore[union-attr]
        assert pattern in stderr, (
            f"Expected stderr to contain: {pattern!r}\nstderr:\n{stderr}"
        )

    for pattern in assertions["stderr_not"]:  # type: ignore[union-attr]
        assert pattern not in stderr, (
            f"Expected stderr to NOT contain: {pattern!r}\nstderr:\n{stderr}"
        )
