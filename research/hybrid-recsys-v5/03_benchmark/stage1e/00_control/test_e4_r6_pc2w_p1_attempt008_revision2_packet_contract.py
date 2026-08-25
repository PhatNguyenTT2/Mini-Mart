from __future__ import annotations

import json
import unittest
from pathlib import Path


CONTROL_ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = CONTROL_ROOT / "e4_r6_pc2w_p1_attempt008_admission_observation_contract.json"
AUTHORIZATION_PATH = CONTROL_ROOT / "e4_r6_pc2w_p1_attempt008_execution_authorization.json"
RUNNER_PATH = CONTROL_ROOT / "execute_e4_r6_pc2w_p1_attempt008_admission_observation.py"
VALIDATOR_PATH = CONTROL_ROOT / "validate_e4_r6_pc2w_p1_attempt008_static_packet.py"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class Attempt008Revision2PacketContractTests(unittest.TestCase):
    def test_runner_consumes_the_authorization_schema_that_the_artifact_exposes(self) -> None:
        authorization = load_json(AUTHORIZATION_PATH)
        runner_source = RUNNER_PATH.read_text(encoding="utf-8")

        decision = authorization["user_decision"]
        self.assertEqual(decision["status"], "CONFIRMED")
        self.assertFalse(decision["runtime_execution_authorized_now"])
        self.assertFalse(decision["exact_process_command_confirmed_now"])
        self.assertTrue(
            'authorization.get("user_decision", {})' in runner_source,
            "runner must consume authorization.user_decision",
        )
        self.assertTrue(
            'authorization.get("current_authorization", {})' not in runner_source,
            "runner must not consume an absent current_authorization object",
        )

    def test_contract_and_authorization_share_one_exact_model_policy(self) -> None:
        contract = load_json(CONTRACT_PATH)
        authorization = load_json(AUTHORIZATION_PATH)

        expected = {
            "requested_model": "gpt-5.6-sol",
            "requested_reasoning_effort": "max",
            "requested_service_tier": "default",
            "requested_display_name": "Sol Max Standard",
            "fresh_audit_requested_model": "gpt-5.6-sol",
            "fresh_audit_requested_reasoning_effort": "xhigh",
            "fast_or_priority_allowed": False,
            "actual_model_reasoning_and_service_tier": "UNOBSERVABLE",
        }
        self.assertEqual(contract["model_policy"], expected)
        self.assertEqual(authorization["model_policy"], expected)

    def test_static_validator_checks_the_runner_consumer_interface(self) -> None:
        validator_source = VALIDATOR_PATH.read_text(encoding="utf-8")

        self.assertTrue(
            '"runner_authorization_consumer_user_decision"' in validator_source,
            "validator must check the runner authorization consumer",
        )
        self.assertTrue(
            '"model_policy_exact_match"' in validator_source,
            "validator must compare both model-policy objects exactly",
        )
        self.assertTrue(
            '"model_policy_expected_values"' in validator_source,
            "validator must check the canonical model-policy values",
        )


if __name__ == "__main__":
    unittest.main()
