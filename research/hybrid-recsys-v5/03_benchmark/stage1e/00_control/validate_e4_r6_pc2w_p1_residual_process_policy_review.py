#!/usr/bin/env python3
"""Deterministically validate the E4-R6-PC2W-P1 residual-process policy review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


BASE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e")
CONTROL = BASE / "00_control"
OUTPUT = (
    BASE
    / "rebaseline_v2"
    / "wave_am"
    / "E4_R6PC2W_P1_residual_process_policy_review"
)
EXPECTED_OUTPUTS = {
    "official_source_evidence_register.json",
    "attempt004_evidence_gap_analysis.json",
    "prospective_residual_process_admission_policy.md",
    "policy_review_handoff.json",
}
FROZEN_INPUTS = {
    CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt004_failure_receipt.json":
        "f2c589e54662e96ec62679fb8215abb25737f0401aac167e300e699ad5756fcf",
    BASE / "rebaseline_v2/wave_al/E4_R6PC2W_P1_docker_query_preflight/attempt-004/command_receipts.json":
        "9dffc35e21970386d312a9ed19778d4dca5d30f5f5e23c69bb59fe20f7aaed6d",
    BASE / "rebaseline_v2/wave_al/E4_R6PC2W_P1_docker_query_preflight/attempt-004/p1_execution_receipt.json":
        "fda12183132f77078c25e2a46008989a6586701084e89337403efab3f8c412f2",
    BASE / "rebaseline_v2/wave_al/E4_R6PC2W_P1_docker_query_preflight/attempt-004/p1_handoff.json":
        "1bf3a13bee187cd061bf679601dcb6536720355b557405a5ae556629da0d9844",
    BASE / "rebaseline_v2/wave_al/E4_R6PC2W_P1_docker_query_preflight/attempt-004/runtime_inventory.json":
        "3095483788ef3b38562660ef5eaf8f15053e426d3097c93bf93a4ad4d6750390",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"root is not an object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD^"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    check("expected_head", head == args.expected_head)

    output_dir = root / OUTPUT
    check("output_root_exists", output_dir.is_dir())
    actual_outputs = {p.name for p in output_dir.iterdir() if p.is_file()}
    check("exact_output_file_set", actual_outputs == EXPECTED_OUTPUTS)

    json_paths = [
        root / CONTROL / "e4_r6_pc2w_p1_residual_process_policy_review_contract.json",
        output_dir / "official_source_evidence_register.json",
        output_dir / "attempt004_evidence_gap_analysis.json",
        output_dir / "policy_review_handoff.json",
        root / CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_residual_process_policy_review_validation_receipt.json",
        root / CONTROL / "pipeline_state_stage1e.json",
    ]
    parsed: dict[str, dict[str, Any]] = {}
    for path in json_paths:
        try:
            parsed[path.name] = load_json(path)
            check(f"strict_json:{path.name}", True)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            check(f"strict_json:{path.name}", False)

    for relative_path, expected_hash in FROZEN_INPUTS.items():
        path = root / relative_path
        check(f"frozen_input_exists:{path.name}", path.is_file())
        check(
            f"frozen_input_hash:{path.name}",
            path.is_file() and sha256(path) == expected_hash,
        )

    contract = parsed.get(
        "e4_r6_pc2w_p1_residual_process_policy_review_contract.json", {}
    )
    check("contract_stage", contract.get("stage_id") == "E4-R6-PC2W-P1-RPR1")
    check("contract_evidence_only", contract.get("scope", {}).get("evidence_only") is True)
    check("contract_attempt005_closed", contract.get("scope", {}).get("attempt005_authorized") is False)
    check("contract_execution_closed", contract.get("scope", {}).get("scientific_execution_authorized") is False)
    check("contract_test_closed", contract.get("scope", {}).get("test_access_authorized") is False)
    check("contract_standard_only", contract.get("model_policy", {}).get("fast_or_priority_allowed") is False)

    sources = parsed.get("official_source_evidence_register.json", {})
    source_rows = sources.get("sources", [])
    check("source_count_9", len(source_rows) == 9)
    check(
        "source_ids_unique",
        len({row.get("source_id") for row in source_rows}) == len(source_rows),
    )
    check(
        "source_urls_https",
        all(str(row.get("url", "")).startswith("https://") for row in source_rows),
    )
    check(
        "six_normative_sources",
        sum("USER_REPORTED" not in str(row.get("authority_class")) for row in source_rows) == 6,
    )
    check(
        "three_risk_signal_sources",
        sum("USER_REPORTED" in str(row.get("authority_class")) for row in source_rows) == 3,
    )
    synthesis = sources.get("synthesis", {})
    check("component_legitimacy", synthesis.get("legitimate_component_identity_established") is True)
    check("cleanup_sla_absent", synthesis.get("post_stop_cleanup_sla_found") is False)
    check("name_allowlist_absent", synthesis.get("name_only_harmlessness_rule_found") is False)
    check("residual_risk_signal", synthesis.get("credible_residual_failure_risk_signal_found") is True)
    check("no_retrieval_failures", sources.get("retrieval_failures") == [])

    gaps = parsed.get("attempt004_evidence_gap_analysis.json", {})
    frozen = gaps.get("frozen_attempt", {})
    check("attempt004_failure_preserved", frozen.get("verdict") == "FAIL_CLOSED_PC2W_P1_ATTEMPT004_BACKEND_OR_POLICY_NOT_ADMISSIBLE")
    check("attempt004_one_execution", frozen.get("execution_attempts") == 1)
    check("attempt004_zero_retry", frozen.get("automatic_retry_count") == 0)
    check("attempt004_wslrelay_a", frozen.get("snapshot_a_runtime_process_names") == ["wslrelay"])
    check("attempt004_wslrelay_b", frozen.get("snapshot_b_runtime_process_names") == ["wslrelay"])
    missing = set(gaps.get("missing_residual_process_fields", []))
    check("pid_gap_recorded", "process identifier" in missing)
    check("parent_gap_recorded", "parent process identifier and parent executable identity" in missing)
    check("socket_gap_recorded", "per-process TCP listener and connection ownership" in missing)
    retrospective = gaps.get("retrospective_decision", {})
    check("attempt004_not_admissible", retrospective.get("attempt004_admissible") is False)
    check("no_retro_repair", retrospective.get("later_observation_may_repair_attempt004") is False)
    check("allowlist_forbidden", retrospective.get("process_name_allowlist_permitted") is False)
    check("policy_relaxation_denied", retrospective.get("policy_relaxation_verdict") == "POLICY_RELAXATION_DENIED_ATTEMPT004_REMAINS_FAIL_CLOSED")

    policy_path = output_dir / "prospective_residual_process_admission_policy.md"
    policy_text = policy_path.read_text(encoding="utf-8") if policy_path.is_file() else ""
    for marker in [
        "POLICY_RELAXATION_DENIED_ATTEMPT004_REMAINS_FAIL_CLOSED",
        "MUST NOT be allowlisted solely by name",
        "wsl --shutdown",
        "Final target runtime process population MUST be empty",
        "There MUST be no automatic retry",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
    ]:
        check(f"policy_marker:{marker}", marker in policy_text)

    handoff = parsed.get("policy_review_handoff.json", {})
    check("handoff_verdict", handoff.get("verdict") == "POLICY_RELAXATION_DENIED_ATTEMPT004_REMAINS_FAIL_CLOSED")
    check("handoff_mandatory_checkpoint", handoff.get("next_decision", {}).get("checkpoint_type") == "MANDATORY")
    option_ids = {row.get("option_id") for row in handoff.get("next_decision", {}).get("options", [])}
    check(
        "handoff_exact_options",
        option_ids == {
            "AUTHORIZE_ATTEMPT005_INSTRUMENTED_CURRENT_HOST",
            "SELECT_CHANGED_HOST",
            "PAUSE_PHASE1E",
        },
    )
    phase = handoff.get("phase1e_status", {})
    check("phase1e_not_complete", phase.get("phase1e_complete") is False)
    check("official_reproduction_not_run", phase.get("official_reproduction") == "NOT_RUN")
    check("harmonized_not_run", phase.get("harmonized_v5_benchmark") == "NOT_RUN")
    check("stage2_not_authorized", phase.get("stage2_formal_entry_authorized") is False)

    for document_name in [
        "official_source_evidence_register.json",
        "attempt004_evidence_gap_analysis.json",
        "policy_review_handoff.json",
    ]:
        truth = parsed.get(document_name, {}).get("truth_state", {})
        check(f"truth_not_run:{document_name}", truth.get("RESULT_STATUS") == "NOT_RUN")
        check(f"truth_test_closed:{document_name}", truth.get("TEST_SET_OPENED") == "NO")
        check(f"truth_zero_rows:{document_name}", truth.get("ACCEPTED_RESULT_ROWS") == 0)

    state = parsed.get("pipeline_state_stage1e.json", {})
    check(
        "state_root",
        state.get("state") == "stage1e_rebaseline_v2_r6_pc2w_p1_attempt004_residual_policy_review_centrally_validated_current_attempt_not_admissible_user_decision_required",
    )
    r6 = state.get("rebaseline_v2", {}).get("e4_r5", {}).get("r6", {})
    check(
        "state_r6_status_attempt004",
        r6.get("status") == "R6_PC2W_P1_ATTEMPT004_RESIDUAL_POLICY_REVIEW_CENTRALLY_VALIDATED_CURRENT_ATTEMPT_NOT_ADMISSIBLE_USER_DECISION_REQUIRED",
    )
    pc2w = r6.get("pc2w", {})
    check(
        "state_pc2w_status_attempt004",
        pc2w.get("status") == "P1_ATTEMPT004_RESIDUAL_POLICY_REVIEW_CENTRALLY_VALIDATED_CURRENT_ATTEMPT_NOT_ADMISSIBLE_USER_DECISION_REQUIRED",
    )
    review = pc2w.get("p1_residual_process_policy_review", {})
    check("state_review_verdict", review.get("verdict") == "POLICY_RELAXATION_DENIED_ATTEMPT004_REMAINS_FAIL_CLOSED")
    check("state_attempt005_closed", review.get("attempt005_authorized") is False)
    check("state_zero_retry", review.get("automatic_retry_count") == 0)
    check("state_mandatory_decision", pc2w.get("next_gate") == "MANDATORY_USER_DECISION_AUTHORIZE_ATTEMPT005_INSTRUMENTED_CURRENT_HOST_OR_SELECT_CHANGED_HOST_OR_PAUSE")
    check("state_result_not_run", state.get("result_status") == "NOT_RUN")
    check("state_test_closed", state.get("test_set_opened") == "NO")
    check("state_harmonized_blocked", state.get("harmonized_v5") == "BLOCKED")
    check("state_external_blocked", state.get("external_validation") == "BLOCKED")

    receipt = parsed.get(
        "rebaseline_v2_e4_r6_pc2w_p1_residual_process_policy_review_validation_receipt.json",
        {},
    )
    check("receipt_verdict", receipt.get("verdict") == "PASS_PC2W_P1_RESIDUAL_PROCESS_POLICY_REVIEW_VALIDATED")
    check("receipt_validated_base_head", receipt.get("validated_head") == "999fdb0e9ae010d65292fe8d4ad962bd65a5cad3")
    check("receipt_packet_commit", receipt.get("packet_commit") in {head, parent})
    check("receipt_check_count", receipt.get("validator_checks") == "90/90")
    check("receipt_no_runtime", receipt.get("runtime_commands_executed") is False)
    check("receipt_attempt005_closed", receipt.get("attempt005_authorized") is False)
    receipt_truth = receipt.get("truth_state", {})
    check("receipt_result_not_run", receipt_truth.get("RESULT_STATUS") == "NOT_RUN")
    check("receipt_test_closed", receipt_truth.get("TEST_SET_OPENED") == "NO")
    check("receipt_zero_rows", receipt_truth.get("ACCEPTED_RESULT_ROWS") == 0)

    failures = [name for name, passed in checks if not passed]
    result = {
        "verdict": (
            "PASS_PC2W_P1_RESIDUAL_PROCESS_POLICY_REVIEW_VALIDATED"
            if not failures
            else "FAIL_PC2W_P1_RESIDUAL_PROCESS_POLICY_REVIEW_VALIDATION"
        ),
        "head": head,
        "parent": parent,
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
