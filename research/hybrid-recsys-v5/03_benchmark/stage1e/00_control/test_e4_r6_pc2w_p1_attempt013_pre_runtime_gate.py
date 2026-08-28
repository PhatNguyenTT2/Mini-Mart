#!/usr/bin/env python3
"""Pure RED-to-GREEN tests for the dormant Attempt-013 authority gate."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any

import e4_r6_pc2w_p1_attempt012_pre_runtime_authority as authority012

try:
    import e4_r6_pc2w_p1_attempt013_pre_runtime_authority as authority013
except ModuleNotFoundError:
    authority013 = None


CONTROL = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
OUTPUT = (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_av/"
    "E4_R6PC2W_P1_attempt013_admission_observation"
)


def authority_document() -> dict[str, Any]:
    raw = Path(__file__).with_name(
        "e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract.json"
    ).read_bytes()
    return authority012.strict_json_object(raw)


POLICY = authority_document()["model_policy"]
ATTESTATION = {
    "actual_model": "gpt-5.6-sol",
    "actual_reasoning_effort": "xhigh",
    "actual_service_tier": "UNOBSERVABLE",
    "actual_speed": "UNOBSERVABLE",
    "fast_or_priority_observed": False,
    "basis": "SYNTHETIC_EXPLICIT_TASK_CREATION_METADATA",
}


class FrozenAttempt012AuthorityEvidenceTests(unittest.TestCase):
    def test_attempt012_authority_has_no_one_shot_budget_fields(self) -> None:
        fields = set(authority012.AuthorityContract.__dataclass_fields__)
        self.assertNotIn("attempts_authorized", fields)
        self.assertNotIn("attempts_consumed", fields)
        self.assertNotIn("attempts_remaining", fields)

    def test_r0_contract_freezes_absent_output_and_unused_budget(self) -> None:
        document = authority_document()
        budget = document["authority_contract"]["attempt_budget"]
        self.assertEqual(budget, {
            "authorized": 1,
            "consumed": 0,
            "remaining": 1,
            "automatic_retry_count": 0,
            "fallback_count": 0,
        })
        self.assertTrue(document["output_contract"]["must_be_absent_before_execution"])
        self.assertFalse(document["scope_boundary"]["runtime_execution_authorized_now"])


class Attempt013AuthorityTests(unittest.TestCase):
    def require_new(self) -> Any:
        if authority013 is None:
            self.fail("ATTEMPT013_AUTHORITY_MODULE_ABSENT")
        return authority013

    def fixture(self) -> tuple[Any, Any]:
        module = self.require_new()
        root = Path.cwd().resolve()
        contract = module.AuthorityContract(
            schema_version=module.AUTHORITY_SCHEMA,
            stage_id="E4-R6-PC2W-P1-ATTEMPT013",
            execution_root=str(root),
            runner_relative=(
                f"{CONTROL}/execute_e4_r6_pc2w_p1_attempt013_admission_observation.py"
            ),
            output_relative=OUTPUT,
            packet_commit="c" * 40,
            expected_head="d" * 40,
            python_executable=str(Path(sys.executable).resolve()),
            confirmation_token="CONFIRMED_ATTEMPT013_SYNTHETIC",
            central_receipt=module.ReceiptLocator(
                f"{CONTROL}/rebaseline_v2_e4_r6_pc2w_p1_attempt013_central_static_validation_receipt.json",
                "1" * 64,
            ),
            fresh_audit_receipt=module.ReceiptLocator(
                f"{CONTROL}/rebaseline_v2_e4_r6_pc2w_p1_attempt013_fresh_independent_audit_receipt.json",
                "2" * 64,
            ),
            model_role="locked_execution",
            attempts_authorized=1,
            attempts_consumed=0,
            attempts_remaining=1,
        )
        observation = module.RuntimeObservation(
            working_directory=str(root),
            git_toplevel=str(root),
            head="d" * 40,
            model_attestation=copy.deepcopy(ATTESTATION),
        )
        return contract, observation

    def test_unused_one_shot_budget_and_absent_output_pass_static_handoff(self) -> None:
        module = self.require_new()
        contract, observation = self.fixture()
        self.assertFalse((Path.cwd() / OUTPUT).exists())
        binding = module.prepare_legacy_handoff(contract, observation, POLICY)
        self.assertEqual(binding.output_path, (Path.cwd() / OUTPUT).resolve())
        self.assertEqual(binding.attempt_budget, (1, 0, 1))

    def test_any_non_one_shot_budget_fails_closed(self) -> None:
        module = self.require_new()
        contract, observation = self.fixture()
        for mutation in (
            {"attempts_authorized": 2},
            {"attempts_consumed": 1},
            {"attempts_remaining": 0},
        ):
            with self.subTest(mutation=mutation):
                changed = module.AuthorityContract(
                    **{**contract.__dict__, **mutation}
                )
                with self.assertRaises(module.AuthorityError) as caught:
                    module.prepare_legacy_handoff(changed, observation, POLICY)
                self.assertEqual(caught.exception.code, "ATTEMPT_BUDGET_INVALID")

    def test_preexisting_output_root_fails_before_legacy_handoff(self) -> None:
        module = self.require_new()
        contract, observation = self.fixture()
        contract = module.AuthorityContract(
            **{**contract.__dict__, "output_relative": contract.runner_relative}
        )
        with self.assertRaises(module.AuthorityError) as caught:
            module.prepare_legacy_handoff(contract, observation, POLICY)
        self.assertEqual(caught.exception.code, "OUTPUT_ROOT_ALREADY_EXISTS")

    def test_unobservable_speed_is_allowed_without_standard_inference(self) -> None:
        module = self.require_new()
        record = module.validate_model_policy(POLICY, "locked_execution", ATTESTATION)
        self.assertEqual(record["requested"]["requested_display_tier"], "Standard")
        self.assertEqual(record["actual"]["actual_speed"], "UNOBSERVABLE")

    def test_positive_fast_or_priority_and_wrong_reasoning_fail_closed(self) -> None:
        module = self.require_new()
        for mutation, code in (
            ({"fast_or_priority_observed": True}, "FAST_OR_PRIORITY_OBSERVED"),
            ({"actual_reasoning_effort": "high"}, "MODEL_OR_REASONING_MISMATCH"),
        ):
            changed = {**ATTESTATION, **mutation}
            with self.subTest(code=code):
                with self.assertRaises(module.AuthorityError) as caught:
                    module.validate_model_policy(POLICY, "locked_execution", changed)
                self.assertEqual(caught.exception.code, code)

    def test_strict_json_rejects_duplicate_casefold_and_nonfinite(self) -> None:
        module = self.require_new()
        for raw in (b'{"a":1,"A":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaises(module.AuthorityError) as caught:
                    module.strict_json_object(raw)
                self.assertEqual(caught.exception.code, "JSON_INVALID")

    def test_expected_argv_is_named_contract_derived_and_has_no_retry_flag(self) -> None:
        module = self.require_new()
        contract, _ = self.fixture()
        argv = module.build_expected_process_argv(contract)
        self.assertEqual(argv[2::2], (
            "--repo-root", "--packet-commit", "--expected-head",
            "--central-validation-receipt", "--central-validation-receipt-sha256",
            "--fresh-audit-receipt", "--fresh-audit-receipt-sha256",
            "--execution-confirmation",
        ))
        self.assertNotIn("--retry", argv)
        self.assertNotIn("--fallback", argv)


if __name__ == "__main__":
    unittest.main()
