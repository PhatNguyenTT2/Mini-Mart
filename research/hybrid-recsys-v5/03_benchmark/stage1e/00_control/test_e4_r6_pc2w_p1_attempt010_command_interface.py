#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import e4_r6_pc2w_p1_attempt010_command_interface as interface


PYTHON = str(Path(sys.executable).resolve())
RUNNER = str((Path.cwd() / "runner.py").resolve())
EXPECTED = [PYTHON, RUNNER, "--repo-root", str(Path.cwd().resolve()), "--token", "abc"]


class CommandInterfaceTests(unittest.TestCase):
    def assert_code(self, code: str, original: list[str], expected: list[str] = EXPECTED) -> None:
        with self.assertRaises(interface.CommandInterfaceError) as caught:
            interface.bind_exact_python_script_argv(original, expected)
        self.assertEqual(caught.exception.code, code)

    def test_exact_dash_b_script_command_passes(self) -> None:
        binding = interface.bind_exact_python_script_argv(
            [PYTHON, "-B", RUNNER, *EXPECTED[2:]], EXPECTED
        )
        self.assertEqual(binding.interpreter_flags, ("-B",))
        self.assertEqual(list(binding.normalized_argv), EXPECTED)
        self.assertTrue(binding.as_record()["original_argv_exactly_bound"])

    def test_missing_dash_b_fails(self) -> None:
        self.assert_code("INTERPRETER_FLAGS_EXACT_MISMATCH", [PYTHON, RUNNER, *EXPECTED[2:]])

    def test_unknown_flag_fails(self) -> None:
        self.assert_code("INTERPRETER_FLAG_UNSUPPORTED", [PYTHON, "-I", RUNNER, *EXPECTED[2:]])

    def test_duplicate_dash_b_fails(self) -> None:
        self.assert_code("INTERPRETER_FLAG_DUPLICATE", [PYTHON, "-B", "-B", RUNNER, *EXPECTED[2:]])

    def test_module_invocation_fails(self) -> None:
        self.assert_code("NON_SCRIPT_INVOCATION_FORBIDDEN", [PYTHON, "-m", "module", *EXPECTED[2:]])

    def test_inline_command_invocation_fails(self) -> None:
        self.assert_code("NON_SCRIPT_INVOCATION_FORBIDDEN", [PYTHON, "-c", "pass", *EXPECTED[2:]])

    def test_runner_path_drift_fails(self) -> None:
        other = str((Path.cwd() / "other.py").resolve())
        self.assert_code("NORMALIZED_PROCESS_ARGV_MISMATCH", [PYTHON, "-B", other, *EXPECTED[2:]])

    def test_argument_order_drift_fails(self) -> None:
        self.assert_code(
            "NORMALIZED_PROCESS_ARGV_MISMATCH",
            [PYTHON, "-B", RUNNER, "--token", "abc", "--repo-root", str(Path.cwd().resolve())],
        )

    def test_python_executable_drift_fails(self) -> None:
        other_python = str((Path.cwd() / "python.exe").resolve())
        self.assert_code("PYTHON_EXECUTABLE_MISMATCH", [other_python, "-B", RUNNER, *EXPECTED[2:]])

    def test_short_original_vector_fails(self) -> None:
        self.assert_code("ORIGINAL_ARGV_TOO_SHORT", [PYTHON, "-B"])


if __name__ == "__main__":
    unittest.main()
