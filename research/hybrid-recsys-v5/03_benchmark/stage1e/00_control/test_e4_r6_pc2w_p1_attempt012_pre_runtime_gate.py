#!/usr/bin/env python3
"""Pure same-seam and static regression tests for dormant Attempt-012."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

import e4_r6_pc2w_p1_attempt010_command_interface as command_interface
import e4_r6_pc2w_p1_attempt012_pre_runtime_authority as authority
import e4_r6_pc2w_p1_gate_receipt_binding as receipt_binding


CONTROL = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
PACKET = "c" * 40
HEAD = "d" * 40
CENTRAL_PATH = (
    f"{CONTROL}/rebaseline_v2_e4_r6_pc2w_p1_attempt012_"
    "central_static_validation_receipt.json"
)
AUDIT_PATH = (
    f"{CONTROL}/rebaseline_v2_e4_r6_pc2w_p1_attempt012_"
    "fresh_independent_audit_receipt.json"
)
PACKET_PATHS = (
    f"{CONTROL}/e4_r6_pc2w_p1_attempt012_admission_observation_contract.json",
    f"{CONTROL}/e4_r6_pc2w_p1_attempt012_execution_authorization.json",
    f"{CONTROL}/execute_e4_r6_pc2w_p1_attempt012_admission_observation.py",
    f"{CONTROL}/validate_e4_r6_pc2w_p1_attempt012_static_packet.py",
)


def load_authority_document() -> dict[str, object]:
    raw = Path(__file__).with_name(
        "e4_r6_pc2w_p1_attempt012_pre_runtime_authority_contract.json"
    ).read_bytes()
    return authority.strict_json_object(raw)


POLICY = load_authority_document()["model_policy"]
ATTESTATION = {
    "actual_model": "gpt-5.6-sol",
    "actual_reasoning_effort": "xhigh",
    "actual_service_tier": "UNOBSERVABLE",
    "actual_speed": "UNOBSERVABLE",
    "fast_or_priority_observed": False,
    "basis": "SYNTHETIC_PLATFORM_TASK_METADATA",
}


def fixture() -> tuple[authority.AuthorityContract, authority.RuntimeObservation]:
    root = Path.cwd().resolve()
    contract = authority.AuthorityContract(
        schema_version=authority.AUTHORITY_SCHEMA,
        stage_id="E4-R6-PC2W-P1-ATTEMPT012",
        execution_root=str(root),
        runner_relative=(
            f"{CONTROL}/execute_e4_r6_pc2w_p1_attempt012_admission_observation.py"
        ),
        output_relative=(
            "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
            "wave_au/E4_R6PC2W_P1_attempt012_admission_observation"
        ),
        packet_commit=PACKET,
        expected_head=HEAD,
        python_executable=str(Path(sys.executable).resolve()),
        confirmation_token="CONFIRMED_ATTEMPT012_SYNTHETIC",
        central_receipt=authority.ReceiptLocator(CENTRAL_PATH, "1" * 64),
        fresh_audit_receipt=authority.ReceiptLocator(AUDIT_PATH, "2" * 64),
        model_role="locked_execution",
    )
    observation = authority.RuntimeObservation(
        working_directory=str(root),
        git_toplevel=str(root),
        head=HEAD,
        model_attestation=copy.deepcopy(ATTESTATION),
    )
    return contract, observation


class AuthorityBoundaryTests(unittest.TestCase):
    def assert_code(
        self,
        code: str,
        contract: authority.AuthorityContract,
        observation: authority.RuntimeObservation,
    ) -> None:
        with self.assertRaises(authority.AuthorityError) as caught:
            authority.prepare_legacy_handoff(contract, observation, POLICY)
        self.assertEqual(caught.exception.code, code)

    def test_same_public_pre_legacy_handoff_accepts_canonical_bound_root(self) -> None:
        contract, observation = fixture()
        binding = authority.prepare_legacy_handoff(contract, observation, POLICY)
        self.assertEqual(binding.execution_root, Path.cwd().resolve())
        self.assertEqual(binding.expected_process_argv, authority.build_expected_process_argv(contract))
        self.assertEqual(binding.model_record["role"], "locked_execution")

    def test_relative_root_is_stably_unbound(self) -> None:
        contract, observation = fixture()
        contract = authority.AuthorityContract(
            **{**contract.__dict__, "execution_root": "relative/repository"}
        )
        self.assert_code("ROOT_AUTHORITY_UNBOUND", contract, observation)

    def test_cwd_and_git_toplevel_must_equal_authorized_root(self) -> None:
        contract, observation = fixture()
        other = str((Path.cwd().resolve().parent / "other-checkout").resolve())
        with self.subTest(field="cwd"):
            changed = authority.RuntimeObservation(
                other, observation.git_toplevel, observation.head, observation.model_attestation
            )
            self.assert_code("CWD_AUTHORITY_MISMATCH", contract, changed)
        with self.subTest(field="git"):
            changed = authority.RuntimeObservation(
                observation.working_directory, other, observation.head, observation.model_attestation
            )
            self.assert_code("GIT_TOPLEVEL_AUTHORITY_MISMATCH", contract, changed)

    def test_expected_head_is_bound_before_handoff(self) -> None:
        contract, observation = fixture()
        changed = authority.RuntimeObservation(
            observation.working_directory,
            observation.git_toplevel,
            "e" * 40,
            observation.model_attestation,
        )
        self.assert_code("EXECUTION_HEAD_MISMATCH", contract, changed)

    def test_runner_and_output_must_be_strictly_contained(self) -> None:
        contract, observation = fixture()
        outside = str((Path.cwd().resolve().parent / "outside").resolve())
        with self.subTest(kind="runner"):
            changed = authority.AuthorityContract(
                **{**contract.__dict__, "runner_relative": outside}
            )
            self.assert_code("RUNNER_OUTSIDE_AUTHORIZED_ROOT", changed, observation)
        with self.subTest(kind="output"):
            changed = authority.AuthorityContract(
                **{**contract.__dict__, "output_relative": outside}
            )
            self.assert_code("OUTPUT_OUTSIDE_AUTHORIZED_ROOT", changed, observation)

    def test_expected_argv_is_built_from_fixed_named_contract_fields(self) -> None:
        contract, _ = fixture()
        expected = authority.build_expected_process_argv(contract)
        self.assertEqual(expected[2::2], (
            "--repo-root", "--packet-commit", "--expected-head",
            "--central-validation-receipt", "--central-validation-receipt-sha256",
            "--fresh-audit-receipt", "--fresh-audit-receipt-sha256",
            "--execution-confirmation",
        ))
        with self.assertRaises(command_interface.CommandInterfaceError) as caught:
            command_interface.bind_exact_python_script_argv(
                [expected[0], "-B", expected[1], *expected[2:], "--repo-root", contract.execution_root],
                expected,
            )
        self.assertEqual(caught.exception.code, "NORMALIZED_PROCESS_ARGV_MISMATCH")


class ModelPolicyTests(unittest.TestCase):
    def test_xhigh_standard_role_accepts_unobservable_speed_without_inference(self) -> None:
        record = authority.validate_model_policy(POLICY, "locked_execution", ATTESTATION)
        self.assertEqual(record["actual"]["actual_speed"], "UNOBSERVABLE")

    def test_reasoning_mismatch_fails_closed(self) -> None:
        changed = {**ATTESTATION, "actual_reasoning_effort": "high"}
        with self.assertRaises(authority.AuthorityError) as caught:
            authority.validate_model_policy(POLICY, "locked_execution", changed)
        self.assertEqual(caught.exception.code, "MODEL_OR_REASONING_MISMATCH")

    def test_observed_fast_or_priority_fails_closed(self) -> None:
        changed = {**ATTESTATION, "fast_or_priority_observed": True}
        with self.assertRaises(authority.AuthorityError) as caught:
            authority.validate_model_policy(POLICY, "locked_execution", changed)
        self.assertEqual(caught.exception.code, "FAST_OR_PRIORITY_OBSERVED")


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_casefold_duplicate_and_nonfinite_are_rejected(self) -> None:
        for raw in (
            b'{"a":1,"a":2}',
            b'{"a":1,"A":2}',
            b'{"a":NaN}',
            b'{"a":Infinity}',
            b'{"a":-Infinity}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(authority.AuthorityError) as caught:
                    authority.strict_json_object(raw)
                self.assertEqual(caught.exception.code, "JSON_INVALID")


class BlobStore:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], bytes] = {}

    def __call__(self, _repo: Path, revision: str, path: str) -> bytes:
        return self.values[(revision, path)]


class ReceiptBindingTests(unittest.TestCase):
    def receipt_fixture(self) -> tuple[BlobStore, receipt_binding.GateReceiptSpec, receipt_binding.ReceiptLocator, receipt_binding.ReceiptLocator]:
        store = BlobStore()
        for index, path in enumerate(PACKET_PATHS):
            store.values[(PACKET, path)] = f"packet-{index}\n".encode()
        facts = [
            {
                "path": path,
                "git_blob_bytes": len(store.values[(PACKET, path)]),
                "git_blob_sha256": hashlib.sha256(store.values[(PACKET, path)]).hexdigest(),
            }
            for path in PACKET_PATHS
        ]
        spec = receipt_binding.GateReceiptSpec(
            stage_id="E4-R6-PC2W-P1-ATTEMPT012",
            packet_files=PACKET_PATHS,
            central_schema="stage1e-e4-r6-pc2w-p1-attempt012-central-static-validation-receipt-1.0",
            central_verdict="PASS_PC2W_P1_ATTEMPT012_CENTRAL_STATIC_VALIDATION",
            central_validator_verdict="IMPLEMENTATION_PASS_READY_FOR_CENTRAL_STATIC_VALIDATION",
            fresh_audit_schema="stage1e-e4-r6-pc2w-p1-attempt012-fresh-independent-audit-receipt-1.0",
            fresh_audit_verdict="PASS_PC2W_P1_ATTEMPT012_FRESH_INDEPENDENT_AUDIT_READY_FOR_EXACT_COMMAND_CONFIRMATION",
        )
        central = {
            "schema_version": spec.central_schema,
            "stage_id": spec.stage_id,
            "verdict": spec.central_verdict,
            "packet_commit": PACKET,
            "packet_artifacts": facts,
            "validator_verdict": spec.central_validator_verdict,
            "runtime_commands_executed": False,
            "write_set": [CENTRAL_PATH],
        }
        central_raw = (json.dumps(central, separators=(",", ":"), allow_nan=False) + "\n").encode()
        central_hash = hashlib.sha256(central_raw).hexdigest()
        audit = {
            "schema_version": spec.fresh_audit_schema,
            "stage_id": spec.stage_id,
            "verdict": spec.fresh_audit_verdict,
            "packet_commit": PACKET,
            "packet_artifacts": facts,
            "central_validation_receipt_git_blob_sha256": central_hash,
            "runtime_commands_executed": False,
            "write_set": [AUDIT_PATH],
        }
        audit_raw = (json.dumps(audit, separators=(",", ":"), allow_nan=False) + "\n").encode()
        store.values[(HEAD, CENTRAL_PATH)] = central_raw
        store.values[(HEAD, AUDIT_PATH)] = audit_raw
        return (
            store,
            spec,
            receipt_binding.ReceiptLocator(CENTRAL_PATH, central_hash),
            receipt_binding.ReceiptLocator(AUDIT_PATH, hashlib.sha256(audit_raw).hexdigest()),
        )

    def test_attempt012_receipts_bind_new_schema_and_raw_hash_link(self) -> None:
        store, spec, central, audit = self.receipt_fixture()
        result = receipt_binding.validate_bound_gate_receipts(
            repository_root=Path("synthetic"),
            execution_head=HEAD,
            packet_commit=PACKET,
            spec=spec,
            central_locator=central,
            fresh_audit_locator=audit,
            read_git_blob=store,
        )
        self.assertEqual(result["central_validation_receipt"]["git_blob_sha256"], central.sha256)

    def test_attempt011_receipt_schema_is_rejected_for_attempt012(self) -> None:
        store, spec, central, audit = self.receipt_fixture()
        document = json.loads(store.values[(HEAD, CENTRAL_PATH)])
        document["schema_version"] = "stage1e-e4-r6-pc2w-p1-attempt011-central-static-validation-receipt-1.0"
        raw = (json.dumps(document, separators=(",", ":"), allow_nan=False) + "\n").encode()
        store.values[(HEAD, CENTRAL_PATH)] = raw
        central = receipt_binding.ReceiptLocator(CENTRAL_PATH, hashlib.sha256(raw).hexdigest())
        with self.assertRaises(receipt_binding.GateReceiptBindingError) as caught:
            receipt_binding.validate_bound_gate_receipts(
                repository_root=Path("synthetic"),
                execution_head=HEAD,
                packet_commit=PACKET,
                spec=spec,
                central_locator=central,
                fresh_audit_locator=audit,
                read_git_blob=store,
            )
        self.assertEqual(caught.exception.code, "CENTRAL_SCHEMA_MISMATCH")


if __name__ == "__main__":
    unittest.main()
