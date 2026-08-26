#!/usr/bin/env python3
"""Synthetic/static pre-runtime tests for the dormant next-attempt packet."""

from __future__ import annotations

import copy
import hashlib
import json
import ast
import dataclasses
import sys
import unittest
from pathlib import Path

import e4_r6_pc2w_p1_gate_receipt_binding as binding
import e4_r6_pc2w_p1_attempt010_command_interface as command_interface


CONTROL = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
HEAD = "b" * 40
PACKET = "c" * 40
PACKET_PATHS = (
    f"{CONTROL}/e4_r6_pc2w_p1_attempt011_admission_observation_contract.json",
    f"{CONTROL}/e4_r6_pc2w_p1_attempt011_execution_authorization.json",
    f"{CONTROL}/execute_e4_r6_pc2w_p1_attempt011_admission_observation.py",
    f"{CONTROL}/validate_e4_r6_pc2w_p1_attempt011_static_packet.py",
)
CENTRAL_PATH = (
    f"{CONTROL}/rebaseline_v2_e4_r6_pc2w_p1_attempt011_"
    "central_static_validation_receipt.json"
)
AUDIT_PATH = (
    f"{CONTROL}/rebaseline_v2_e4_r6_pc2w_p1_attempt011_"
    "fresh_independent_audit_receipt.json"
)


def encoded(value: object) -> bytes:
    return (json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n").encode()


class BlobStore:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], bytes] = {}
        self.calls: list[tuple[Path, str, str]] = []

    def add(self, revision: str, path: str, raw: bytes) -> None:
        self.values[(revision, path)] = raw

    def __call__(self, repo: Path, revision: str, path: str) -> bytes:
        self.calls.append((repo, revision, path))
        return self.values[(revision, path)]


class ReceiptFixture:
    def __init__(self) -> None:
        self.repo = Path("synthetic-repository")
        self.store = BlobStore()
        for index, path in enumerate(PACKET_PATHS):
            self.store.add(PACKET, path, f"packet-{index}\n".encode())
        facts = [
            {
                "path": path,
                "git_blob_bytes": len(self.store.values[(PACKET, path)]),
                "git_blob_sha256": hashlib.sha256(
                    self.store.values[(PACKET, path)]
                ).hexdigest(),
            }
            for path in PACKET_PATHS
        ]
        self.spec = binding.GateReceiptSpec(
            stage_id="E4-R6-PC2W-P1-ATTEMPT011",
            packet_files=PACKET_PATHS,
            central_schema=(
                "stage1e-e4-r6-pc2w-p1-attempt011-"
                "central-static-validation-receipt-1.0"
            ),
            central_verdict="PASS_PC2W_P1_ATTEMPT011_CENTRAL_STATIC_VALIDATION",
            central_validator_verdict="READY_FOR_CENTRAL_STATIC_VALIDATION",
            fresh_audit_schema=(
                "stage1e-e4-r6-pc2w-p1-attempt011-"
                "fresh-independent-audit-receipt-1.0"
            ),
            fresh_audit_verdict=(
                "PASS_PC2W_P1_ATTEMPT011_FRESH_INDEPENDENT_AUDIT_"
                "READY_FOR_EXACT_COMMAND_CONFIRMATION"
            ),
        )
        self.central = {
            "schema_version": self.spec.central_schema,
            "stage_id": self.spec.stage_id,
            "verdict": self.spec.central_verdict,
            "packet_commit": PACKET,
            "packet_artifacts": facts,
            "validator_verdict": self.spec.central_validator_verdict,
            "runtime_commands_executed": False,
            "write_set": [CENTRAL_PATH],
        }
        central_raw = encoded(self.central)
        central_hash = hashlib.sha256(central_raw).hexdigest()
        self.audit = {
            "schema_version": self.spec.fresh_audit_schema,
            "stage_id": self.spec.stage_id,
            "verdict": self.spec.fresh_audit_verdict,
            "packet_commit": PACKET,
            "packet_artifacts": facts,
            "central_validation_receipt_git_blob_sha256": central_hash,
            "runtime_commands_executed": False,
            "write_set": [AUDIT_PATH],
        }
        audit_raw = encoded(self.audit)
        self.store.add(HEAD, CENTRAL_PATH, central_raw)
        self.store.add(HEAD, AUDIT_PATH, audit_raw)
        self.central_locator = binding.ReceiptLocator(CENTRAL_PATH, central_hash)
        self.audit_locator = binding.ReceiptLocator(
            AUDIT_PATH, hashlib.sha256(audit_raw).hexdigest()
        )

    def validate(self) -> dict[str, dict[str, str]]:
        return binding.validate_bound_gate_receipts(
            repository_root=self.repo,
            execution_head=HEAD,
            packet_commit=PACKET,
            spec=self.spec,
            central_locator=self.central_locator,
            fresh_audit_locator=self.audit_locator,
            read_git_blob=self.store,
        )

    def replace_central_raw(self, raw: bytes) -> None:
        self.store.add(HEAD, CENTRAL_PATH, raw)
        self.central_locator = binding.ReceiptLocator(
            CENTRAL_PATH, hashlib.sha256(raw).hexdigest()
        )

    def replace_audit_raw(self, raw: bytes) -> None:
        self.store.add(HEAD, AUDIT_PATH, raw)
        self.audit_locator = binding.ReceiptLocator(
            AUDIT_PATH, hashlib.sha256(raw).hexdigest()
        )

    def replace_central(self, **changes: object) -> None:
        self.central = copy.deepcopy(self.central)
        self.central.update(changes)
        self.replace_central_raw(encoded(self.central))

    def replace_audit(self, **changes: object) -> None:
        self.audit = copy.deepcopy(self.audit)
        self.audit.update(changes)
        self.replace_audit_raw(encoded(self.audit))

    def replace_stage(self, stage_id: str) -> None:
        self.spec = dataclasses.replace(self.spec, stage_id=stage_id)
        self.replace_central(stage_id=stage_id)
        self.replace_audit(
            stage_id=stage_id,
            central_validation_receipt_git_blob_sha256=self.central_locator.sha256,
        )


class BoundaryTrap:
    def __init__(self) -> None:
        self.calls = {
            "host_command": 0,
            "docker": 0,
            "wsl": 0,
            "powershell": 0,
            "sleep": 0,
            "output_writer": 0,
            "cleanup_builder": 0,
            "output_root_create": 0,
        }

    def assert_zero(self, case: unittest.TestCase) -> None:
        case.assertEqual(self.calls, {key: 0 for key in self.calls})


def runner_source() -> str:
    return Path(__file__).with_name(
        "execute_e4_r6_pc2w_p1_attempt011_admission_observation.py"
    ).read_text(encoding="utf-8")


def retained_runner_source() -> str:
    return Path(__file__).with_name(
        "execute_e4_r6_pc2w_p1_attempt008_admission_observation.py"
    ).read_text(encoding="utf-8")


def assigned_literal(source: str, name: str) -> object:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"assignment not found: {name}")


PYTHON = str(Path(sys.executable).resolve())
ATTEMPT_RUNNER = str(
    Path(__file__).with_name(
        "execute_e4_r6_pc2w_p1_attempt011_admission_observation.py"
    ).resolve()
)
ORDERED_ARGUMENTS = [
    "--repo-root", str(Path.cwd().resolve()),
    "--packet-commit", PACKET,
    "--expected-head", HEAD,
    "--central-validation-receipt", CENTRAL_PATH,
    "--central-validation-receipt-sha256", "1" * 64,
    "--fresh-audit-receipt", AUDIT_PATH,
    "--fresh-audit-receipt-sha256", "2" * 64,
    "--execution-confirmation", "CONFIRMED_SYNTHETIC_TOKEN",
]
NORMALIZED_COMMAND = [PYTHON, ATTEMPT_RUNNER, *ORDERED_ARGUMENTS]


class GateReceiptBindingTests(unittest.TestCase):
    def assert_binding_code(
        self, code: str, fixture: ReceiptFixture
    ) -> None:
        with self.assertRaises(binding.GateReceiptBindingError) as caught:
            fixture.validate()
        self.assertEqual(caught.exception.code, code)

    def test_gr_pos_01_valid_central_receipt_binds_all_required_facts(self) -> None:
        fixture = ReceiptFixture()
        result = fixture.validate()
        self.assertEqual(
            result["central_validation_receipt"],
            {
                "path": CENTRAL_PATH,
                "git_blob_sha256": fixture.central_locator.sha256,
                "verdict": fixture.spec.central_verdict,
            },
        )

    def test_gr_pos_02_valid_fresh_audit_binds_central_link_and_write_set(self) -> None:
        fixture = ReceiptFixture()
        result = fixture.validate()
        self.assertEqual(
            result["fresh_independent_audit_receipt"],
            {
                "path": AUDIT_PATH,
                "git_blob_sha256": fixture.audit_locator.sha256,
                "verdict": fixture.spec.fresh_audit_verdict,
            },
        )

    def test_gr_pos_03_valid_pair_returns_two_records_without_source_mutation(self) -> None:
        fixture = ReceiptFixture()
        central_before = copy.deepcopy(fixture.central)
        audit_before = copy.deepcopy(fixture.audit)
        result = fixture.validate()
        self.assertEqual(list(result), [
            "central_validation_receipt",
            "fresh_independent_audit_receipt",
        ])
        self.assertEqual(fixture.central, central_before)
        self.assertEqual(fixture.audit, audit_before)

    def test_gr_pos_04_generic_function_accepts_a_different_consistent_stage(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_stage("SYNTHETIC-CONSISTENT-STAGE")
        result = fixture.validate()
        self.assertEqual(result["central_validation_receipt"]["verdict"], fixture.spec.central_verdict)

    def test_gr_c_01_central_schema_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_central(schema_version="wrong")
        self.assert_binding_code("CENTRAL_SCHEMA_MISMATCH", fixture)

    def test_gr_c_02_central_verdict_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_central(verdict="wrong")
        self.assert_binding_code("CENTRAL_VERDICT_MISMATCH", fixture)

    def test_gr_c_03_central_stage_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_central(stage_id="wrong")
        self.assert_binding_code("CENTRAL_STAGE_MISMATCH", fixture)

    def test_gr_c_04_central_packet_commit_requires_exact_lowercase_full_value(self) -> None:
        for value in (PACKET.upper(), PACKET[:12]):
            with self.subTest(value=value):
                fixture = ReceiptFixture()
                fixture.replace_central(packet_commit=value)
                self.assert_binding_code("CENTRAL_PACKET_COMMIT_MISMATCH", fixture)

    def test_gr_c_05_central_packet_artifact_path_and_order_are_exact(self) -> None:
        fixture = ReceiptFixture()
        reversed_facts = list(reversed(fixture.central["packet_artifacts"]))
        fixture.replace_central(packet_artifacts=reversed_facts)
        self.assert_binding_code("CENTRAL_PACKET_ARTIFACT_MISMATCH", fixture)

    def test_gr_c_06_central_packet_artifact_byte_count_mismatch(self) -> None:
        fixture = ReceiptFixture()
        facts = copy.deepcopy(fixture.central["packet_artifacts"])
        facts[0]["git_blob_bytes"] += 1
        fixture.replace_central(packet_artifacts=facts)
        self.assert_binding_code("CENTRAL_PACKET_ARTIFACT_MISMATCH", fixture)

    def test_gr_c_07_central_packet_artifact_sha256_mismatch(self) -> None:
        fixture = ReceiptFixture()
        facts = copy.deepcopy(fixture.central["packet_artifacts"])
        facts[0]["git_blob_sha256"] = "0" * 64
        fixture.replace_central(packet_artifacts=facts)
        self.assert_binding_code("CENTRAL_PACKET_ARTIFACT_MISMATCH", fixture)

    def test_gr_c_08_central_raw_blob_sha256_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.central_locator = binding.ReceiptLocator(CENTRAL_PATH, "0" * 64)
        self.assert_binding_code("CENTRAL_RAW_HASH_MISMATCH", fixture)

    def test_gr_c_09_central_one_file_write_set_rejects_extra_path(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_central(write_set=[CENTRAL_PATH, f"{CONTROL}/extra.json"])
        self.assert_binding_code("CENTRAL_WRITE_SET_MISMATCH", fixture)

    def test_gr_c_10_central_validator_verdict_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_central(validator_verdict="wrong")
        self.assert_binding_code("CENTRAL_VALIDATOR_VERDICT_MISMATCH", fixture)

    def test_gr_a_01_fresh_audit_schema_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_audit(schema_version="wrong")
        self.assert_binding_code("FRESH_AUDIT_SCHEMA_MISMATCH", fixture)

    def test_gr_a_02_fresh_audit_verdict_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_audit(verdict="wrong")
        self.assert_binding_code("FRESH_AUDIT_VERDICT_MISMATCH", fixture)

    def test_gr_a_03_fresh_audit_stage_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_audit(stage_id="wrong")
        self.assert_binding_code("FRESH_AUDIT_STAGE_MISMATCH", fixture)

    def test_gr_a_04_fresh_audit_packet_commit_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_audit(packet_commit=PACKET.upper())
        self.assert_binding_code("FRESH_AUDIT_PACKET_COMMIT_MISMATCH", fixture)

    def test_gr_a_05_fresh_audit_packet_artifact_path_and_order_are_exact(self) -> None:
        fixture = ReceiptFixture()
        facts = list(reversed(fixture.audit["packet_artifacts"]))
        fixture.replace_audit(packet_artifacts=facts)
        self.assert_binding_code("FRESH_AUDIT_PACKET_ARTIFACT_MISMATCH", fixture)

    def test_gr_a_06_fresh_audit_packet_artifact_byte_count_mismatch(self) -> None:
        fixture = ReceiptFixture()
        facts = copy.deepcopy(fixture.audit["packet_artifacts"])
        facts[1]["git_blob_bytes"] += 1
        fixture.replace_audit(packet_artifacts=facts)
        self.assert_binding_code("FRESH_AUDIT_PACKET_ARTIFACT_MISMATCH", fixture)

    def test_gr_a_07_fresh_audit_packet_artifact_sha256_mismatch(self) -> None:
        fixture = ReceiptFixture()
        facts = copy.deepcopy(fixture.audit["packet_artifacts"])
        facts[1]["git_blob_sha256"] = "0" * 64
        fixture.replace_audit(packet_artifacts=facts)
        self.assert_binding_code("FRESH_AUDIT_PACKET_ARTIFACT_MISMATCH", fixture)

    def test_gr_a_08_fresh_audit_raw_blob_sha256_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.audit_locator = binding.ReceiptLocator(AUDIT_PATH, "0" * 64)
        self.assert_binding_code("FRESH_AUDIT_RAW_HASH_MISMATCH", fixture)

    def test_gr_a_09_fresh_audit_one_file_write_set_rejects_extra_path(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_audit(write_set=[AUDIT_PATH, f"{CONTROL}/extra.json"])
        self.assert_binding_code("FRESH_AUDIT_WRITE_SET_MISMATCH", fixture)

    def test_gr_a_10_fresh_audit_central_link_mismatch(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_audit(central_validation_receipt_git_blob_sha256="0" * 64)
        self.assert_binding_code("FRESH_AUDIT_CENTRAL_LINK_MISMATCH", fixture)

    def test_gr_j_01_exact_duplicate_key_in_central_receipt(self) -> None:
        fixture = ReceiptFixture()
        raw = encoded(fixture.central)
        fixture.replace_central_raw(raw[:-2] + b',"stage_id":"duplicate"}\n')
        self.assert_binding_code("CENTRAL_JSON_INVALID", fixture)

    def test_gr_j_02_casefold_duplicate_key_in_central_receipt(self) -> None:
        fixture = ReceiptFixture()
        raw = encoded(fixture.central)
        fixture.replace_central_raw(raw[:-2] + b',"Stage_ID":"duplicate"}\n')
        self.assert_binding_code("CENTRAL_JSON_INVALID", fixture)

    def test_gr_j_03_nan_in_central_receipt(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_central_raw(b'{"value":NaN}\n')
        self.assert_binding_code("CENTRAL_JSON_INVALID", fixture)

    def test_gr_j_04_exact_duplicate_key_in_fresh_audit_receipt(self) -> None:
        fixture = ReceiptFixture()
        raw = encoded(fixture.audit)
        fixture.replace_audit_raw(raw[:-2] + b',"verdict":"duplicate"}\n')
        self.assert_binding_code("FRESH_AUDIT_JSON_INVALID", fixture)

    def test_gr_j_05_casefold_duplicate_key_in_fresh_audit_receipt(self) -> None:
        fixture = ReceiptFixture()
        raw = encoded(fixture.audit)
        fixture.replace_audit_raw(raw[:-2] + b',"Verdict":"duplicate"}\n')
        self.assert_binding_code("FRESH_AUDIT_JSON_INVALID", fixture)

    def test_gr_j_06_infinity_in_fresh_audit_receipt(self) -> None:
        fixture = ReceiptFixture()
        fixture.replace_audit_raw(b'{"value":Infinity}\n')
        self.assert_binding_code("FRESH_AUDIT_JSON_INVALID", fixture)

    def test_gr_j_07_negative_infinity_invalid_utf8_and_nonobject_fail_closed(self) -> None:
        for raw in (b'{"value":-Infinity}\n', b'{"value":"\xff"}\n', b'[]\n'):
            with self.subTest(raw=raw):
                fixture = ReceiptFixture()
                fixture.replace_audit_raw(raw)
                self.assert_binding_code("FRESH_AUDIT_JSON_INVALID", fixture)

    def test_gr_l_01_central_and_fresh_audit_paths_must_be_distinct(self) -> None:
        fixture = ReceiptFixture()
        fixture.audit_locator = binding.ReceiptLocator(CENTRAL_PATH, fixture.audit_locator.sha256)
        self.assert_binding_code("LOCATOR_PATH_COLLISION", fixture)

    def test_gr_l_02_absolute_receipt_path_is_rejected(self) -> None:
        fixture = ReceiptFixture()
        fixture.central_locator = binding.ReceiptLocator("C:/absolute/receipt.json", fixture.central_locator.sha256)
        self.assert_binding_code("LOCATOR_PATH_INVALID", fixture)

    def test_gr_l_03_noncanonical_outside_alias_and_nonjson_paths_fail_closed(self) -> None:
        paths = (
            f"{CONTROL}/../receipt.json",
            f"{CONTROL}//receipt.json",
            "research/outside/receipt.json",
            PACKET_PATHS[0],
            f"{CONTROL}/receipt.txt",
        )
        for path in paths:
            with self.subTest(path=path):
                fixture = ReceiptFixture()
                fixture.central_locator = binding.ReceiptLocator(path, fixture.central_locator.sha256)
                self.assert_binding_code("LOCATOR_PATH_INVALID", fixture)

    def test_gr_l_04_locator_hash_requires_lowercase_64_hex(self) -> None:
        for value in ("A" * 64, "a" * 63, "g" * 64):
            with self.subTest(value=value):
                fixture = ReceiptFixture()
                fixture.central_locator = binding.ReceiptLocator(CENTRAL_PATH, value)
                self.assert_binding_code("LOCATOR_HASH_INVALID", fixture)


class CommandInterfaceTests(unittest.TestCase):
    def assert_command_fails(self, original: list[str]) -> None:
        with self.assertRaises(command_interface.CommandInterfaceError):
            command_interface.bind_exact_python_script_argv(original, NORMALIZED_COMMAND)

    def test_gr_cmd_01_exact_python_dash_b_runner_and_ordered_arguments_pass(self) -> None:
        bound = command_interface.bind_exact_python_script_argv(
            [PYTHON, "-B", ATTEMPT_RUNNER, *ORDERED_ARGUMENTS], NORMALIZED_COMMAND
        )
        self.assertEqual(bound.interpreter_flags, ("-B",))
        self.assertEqual(list(bound.normalized_argv), NORMALIZED_COMMAND)

    def test_gr_cmd_02_missing_dash_b_fails(self) -> None:
        self.assert_command_fails([PYTHON, ATTEMPT_RUNNER, *ORDERED_ARGUMENTS])

    def test_gr_cmd_03_unknown_interpreter_flag_fails(self) -> None:
        self.assert_command_fails([PYTHON, "-I", ATTEMPT_RUNNER, *ORDERED_ARGUMENTS])

    def test_gr_cmd_04_duplicate_dash_b_fails(self) -> None:
        self.assert_command_fails([PYTHON, "-B", "-B", ATTEMPT_RUNNER, *ORDERED_ARGUMENTS])

    def test_gr_cmd_05_python_dash_c_fails(self) -> None:
        self.assert_command_fails([PYTHON, "-c", "pass", *ORDERED_ARGUMENTS])

    def test_gr_cmd_06_python_dash_m_fails(self) -> None:
        self.assert_command_fails([PYTHON, "-m", "module", *ORDERED_ARGUMENTS])

    def test_gr_cmd_07_python_executable_drift_fails(self) -> None:
        self.assert_command_fails([str(Path.cwd() / "python.exe"), "-B", ATTEMPT_RUNNER, *ORDERED_ARGUMENTS])

    def test_gr_cmd_08_runner_path_drift_fails(self) -> None:
        self.assert_command_fails([PYTHON, "-B", str(Path.cwd() / "other.py"), *ORDERED_ARGUMENTS])

    def test_gr_cmd_09_argument_order_drift_fails(self) -> None:
        drift = ORDERED_ARGUMENTS.copy()
        drift[0:4] = drift[2:4] + drift[0:2]
        self.assert_command_fails([PYTHON, "-B", ATTEMPT_RUNNER, *drift])

    def test_gr_cmd_10_argument_value_drift_fails(self) -> None:
        drift = ORDERED_ARGUMENTS.copy()
        drift[1] = str(Path.cwd() / "elsewhere")
        self.assert_command_fails([PYTHON, "-B", ATTEMPT_RUNNER, *drift])

    def test_gr_cmd_11_missing_required_argument_fails(self) -> None:
        self.assert_command_fails([PYTHON, "-B", ATTEMPT_RUNNER, *ORDERED_ARGUMENTS[:-2]])

    def test_gr_cmd_12_duplicated_receipt_argument_fails(self) -> None:
        drift = ORDERED_ARGUMENTS + ["--fresh-audit-receipt", AUDIT_PATH]
        self.assert_command_fails([PYTHON, "-B", ATTEMPT_RUNNER, *drift])

    def test_gr_cmd_13_swapped_receipt_locators_or_hashes_fail(self) -> None:
        drift = ORDERED_ARGUMENTS.copy()
        drift[9], drift[13] = drift[13], drift[9]
        drift[11], drift[15] = drift[15], drift[11]
        self.assert_command_fails([PYTHON, "-B", ATTEMPT_RUNNER, *drift])


class NoRuntimeBeforeGateTests(unittest.TestCase):
    def test_gr_nr_01_central_failure_precedes_output_creation_and_dispatch(self) -> None:
        fixture = ReceiptFixture()
        trap = BoundaryTrap()
        fixture.replace_central(stage_id="wrong")
        with self.assertRaises(binding.GateReceiptBindingError):
            fixture.validate()
        trap.assert_zero(self)

    def test_gr_nr_02_fresh_audit_failure_precedes_output_creation_and_dispatch(self) -> None:
        fixture = ReceiptFixture()
        trap = BoundaryTrap()
        fixture.replace_audit(stage_id="wrong")
        with self.assertRaises(binding.GateReceiptBindingError):
            fixture.validate()
        trap.assert_zero(self)

    def test_gr_nr_03_command_mismatch_precedes_receipt_parse_output_and_dispatch(self) -> None:
        fixture = ReceiptFixture()
        trap = BoundaryTrap()
        with self.assertRaises(command_interface.CommandInterfaceError):
            command_interface.bind_exact_python_script_argv(
                [PYTHON, ATTEMPT_RUNNER, *ORDERED_ARGUMENTS], NORMALIZED_COMMAND
            )
        self.assertEqual(fixture.store.calls, [])
        trap.assert_zero(self)

    def test_gr_nr_04_frozen_hash_gate_precedes_output_and_stale_predicate_is_unreachable(self) -> None:
        source = runner_source()
        retained = retained_runner_source()
        self.assertLess(source.index("_validate_frozen_upstream"), source.index("legacy.main()"))
        self.assertLess(retained.index("frozen_upstream = validate_frozen_upstream"), retained.index("output_root.mkdir"))
        self.assertIn("legacy.validate_gate_receipts = _validate_bound_gate_receipts", source)
        self.assertNotIn("legacy.validate_gate_receipts = previous.previous._validate_gate_receipts", source)

    def test_gr_nr_05_preexisting_output_root_fails_before_dispatch_without_reuse(self) -> None:
        source = retained_runner_source()
        exists_check = source.index("if output_root.exists():")
        self.assertLess(exists_check, source.index("def invoke("))
        self.assertIn("immutable one-shot output root already exists", source[exists_check:])
        self.assertNotIn("rmtree", source)


class CleanupAndFinalStateTests(unittest.TestCase):
    def test_gr_cl_01_failed_p04_prevents_s00(self) -> None:
        source = runner_source()
        self.assertIn('invoke("P04", "POWERSHELL_MODULE_PREFLIGHT", 60)', source)
        retained = retained_runner_source()
        self.assertLess(retained.index("if all(pre_lanes.values()):"), retained.index('invoke("S00"'))

    def test_gr_cl_02_s00_exception_attempts_f00_then_f01_once(self) -> None:
        source = retained_runner_source()
        s00 = source.index('invoke("S00"')
        f00 = source.index('invoke("F00"', s00)
        f01 = source.index('invoke("F01"', f00)
        self.assertLess(s00, f00)
        self.assertLess(f00, f01)
        self.assertEqual(source.count('invoke("F00"'), 1)
        self.assertEqual(source.count('invoke("F01"'), 1)

    def test_gr_cl_03_each_d_lane_is_inside_cleanup_finally(self) -> None:
        source = retained_runner_source()
        s00 = source.index('invoke("S00"')
        f00 = source.index('invoke("F00"', s00)
        for lane in ("D00", "D01", "D02", "D03", "D04", "D05", "D06"):
            self.assertTrue(s00 < source.index(f'invoke("{lane}"', s00) < f00)

    def test_gr_cl_04_f00_exception_still_attempts_f01_through_nested_finally(self) -> None:
        source = retained_runner_source()
        fragment = source[source.index("if start_attempted:"):source.index("snapshots:")]
        self.assertIn("try:", fragment)
        self.assertIn("finally:", fragment)
        self.assertLess(
            fragment.index('invoke("F00"'),
            fragment.index("finally:", fragment.index('invoke("F00"')),
        )
        self.assertLess(
            fragment.index("finally:", fragment.index('invoke("F00"')),
            fragment.index('invoke("F01"'),
        )

    def test_gr_cl_05_success_requires_exact_a_b_c_snapshots(self) -> None:
        source = retained_runner_source()
        self.assertEqual(assigned_literal(source, "SNAPSHOT_LABELS"), ["A", "B", "C"])
        self.assertIn('collect_snapshot("A"', source)
        self.assertIn('collect_snapshot("B"', source)
        self.assertIn('collect_snapshot("C"', source)

    def test_gr_cl_06_missing_or_unstable_snapshot_is_fail_closed(self) -> None:
        source = retained_runner_source()
        self.assertIn('"three_closure_snapshots_present"', source)
        self.assertIn('"all_closure_lanes_pass"', source)
        self.assertIn('"closure_snapshots_stable"', source)
        self.assertIn("PASS_VERDICT if all(pass_conditions.values()) else FAIL_VERDICT", source)

    def test_gr_cl_07_final_state_difference_is_fail_closed(self) -> None:
        source = retained_runner_source()
        self.assertIn('"final_closure_matches_pre_start": final_matches_pre', source)
        self.assertIn("snapshots[-1][key] == pre_start[key]", source)

    def test_gr_cl_08_command_ids_are_exact_once_with_zero_retry_and_fallback(self) -> None:
        source = runner_source()
        expected = [
            "P00", "P01", "P02", "P03", "P04", "S00",
            "D00", "D01", "D02", "D03", "D04", "D05", "D06",
            "F00", "F01",
            "A00", "A01", "A02", "A03",
            "B00", "B01", "B02", "B03",
            "C00", "C01", "C02", "C03",
        ]
        self.assertEqual(assigned_literal(source, "EXPECTED_COMMAND_IDS"), expected)
        self.assertEqual(len(expected), len(set(expected)))
        self.assertIn('"automatic_retry_count": 0', source)
        self.assertIn('"fallback_count": 0', source)

    def test_gr_cl_09_output_manifest_is_exact_and_failure_evidence_is_durable(self) -> None:
        source = retained_runner_source()
        self.assertEqual(
            assigned_literal(source, "EXPECTED_OUTPUT_FILES"),
            {"admission_observation.json", "command_receipts.json", "execution_receipt.json", "handoff.json"},
        )
        self.assertLess(source.index('persist_failure_packet("IN_PROGRESS"'), source.index("def invoke("))
        invoke_fragment = source[source.index("def invoke("):source.index("pre_start, pre_lanes")]
        self.assertIn("persist_failure_packet", invoke_fragment)
        self.assertIn("exact output file set violated", source)


if __name__ == "__main__":
    unittest.main()
