#!/usr/bin/env python3
"""Pure Attempt-010 Python command-interface binding.

This module performs no host, Docker, WSL, network, or filesystem I/O at import
time.  It validates the real ``sys.orig_argv`` shape before the inherited
Attempt-008 runner receives a canonical argv view.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REQUIRED_INTERPRETER_FLAGS = ("-B",)


class CommandInterfaceError(RuntimeError):
    """Fail-closed command-interface mismatch with a stable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CommandBinding:
    interpreter_flags: tuple[str, ...]
    normalized_argv: tuple[str, ...]

    def as_record(self) -> dict[str, object]:
        return {
            "schema_version": "stage1e-attempt010-python-command-binding-1.0",
            "interpreter_flags": list(self.interpreter_flags),
            "normalized_argv": list(self.normalized_argv),
            "original_argv_exactly_bound": True,
        }


def _require_string_vector(name: str, values: Sequence[str]) -> list[str]:
    materialized = list(values)
    if not materialized or any(not isinstance(value, str) or value == "" for value in materialized):
        raise CommandInterfaceError(f"{name.upper()}_INVALID")
    return materialized


def bind_exact_python_script_argv(
    original_argv: Sequence[str],
    expected_normalized_argv: Sequence[str],
    *,
    required_interpreter_flags: Sequence[str] = REQUIRED_INTERPRETER_FLAGS,
) -> CommandBinding:
    """Validate an exact Python-script process command and remove only ``-B``.

    ``expected_normalized_argv`` is the exact command expected by the inherited
    runner after interpreter-only flags are removed.  No unknown, duplicate,
    reordered, missing, ``-c``, or ``-m`` invocation form is accepted.
    """

    original = _require_string_vector("original_argv", original_argv)
    expected = _require_string_vector(
        "expected_normalized_argv", expected_normalized_argv
    )
    required_flags = tuple(
        _require_string_vector("required_interpreter_flags", required_interpreter_flags)
    )
    if len(expected) < 2:
        raise CommandInterfaceError("EXPECTED_NORMALIZED_ARGV_TOO_SHORT")
    if len(original) < 3:
        raise CommandInterfaceError("ORIGINAL_ARGV_TOO_SHORT")
    if len(set(required_flags)) != len(required_flags):
        raise CommandInterfaceError("REQUIRED_INTERPRETER_FLAGS_DUPLICATE")
    if any(flag != "-B" for flag in required_flags):
        raise CommandInterfaceError("REQUIRED_INTERPRETER_FLAG_UNSUPPORTED")

    actual_python = str(Path(original[0]).resolve())
    expected_python = str(Path(expected[0]).resolve())
    if actual_python != expected_python:
        raise CommandInterfaceError("PYTHON_EXECUTABLE_MISMATCH")

    cursor = 1
    observed_flags: list[str] = []
    while cursor < len(original) and original[cursor].startswith("-"):
        flag = original[cursor]
        if flag in {"-c", "-m"}:
            raise CommandInterfaceError("NON_SCRIPT_INVOCATION_FORBIDDEN")
        if flag not in required_flags:
            raise CommandInterfaceError("INTERPRETER_FLAG_UNSUPPORTED")
        if flag in observed_flags:
            raise CommandInterfaceError("INTERPRETER_FLAG_DUPLICATE")
        observed_flags.append(flag)
        cursor += 1

    if tuple(observed_flags) != required_flags:
        raise CommandInterfaceError("INTERPRETER_FLAGS_EXACT_MISMATCH")
    if cursor >= len(original):
        raise CommandInterfaceError("RUNNER_PATH_MISSING")

    actual_runner = str(Path(original[cursor]).resolve())
    expected_runner = str(Path(expected[1]).resolve())
    normalized = [actual_python, actual_runner, *original[cursor + 1 :]]
    canonical_expected = [expected_python, expected_runner, *expected[2:]]
    if normalized != canonical_expected:
        raise CommandInterfaceError("NORMALIZED_PROCESS_ARGV_MISMATCH")

    return CommandBinding(
        interpreter_flags=tuple(observed_flags),
        normalized_argv=tuple(normalized),
    )
