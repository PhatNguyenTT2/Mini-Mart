from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r6_s0_frozen_input_manifest.json"
SOURCE = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/materialized_sources/r5"
    / "recbole_v1_2_1_9a6f63d"
)
SELECTION_ROOT = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_af"
    / "E4_R5G1_source_evidence_selection"
)
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
SELECTED_CANDIDATE = "R5-CAND-RECBOLE-BPR-ML100K-001"
SELECTED_REVISION = "9a6f63d8d4a5b989fe27955a833f813a6d86041e"


class ContractError(ValueError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate key: {key}")
        casefolded = key.casefold()
        if casefolded in folded and folded[casefolded] != key:
            raise ContractError(f"case-colliding keys: {folded[casefolded]} / {key}")
        folded[casefolded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check(checks: dict[str, bool], failures: list[str], name: str, value: bool) -> None:
    checks[name] = bool(value)
    if not value:
        failures.append(name)


def exact_profile(display_name: str, effort: str, tier: str) -> dict[str, str]:
    return {
        "display_name": display_name,
        "runtime_model_id": "gpt-5.6-sol",
        "reasoning_effort": effort,
        "service_tier": tier,
    }


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    try:
        manifest = load_json(MANIFEST)
    except Exception as exc:
        print(json.dumps({"passed": False, "failures": [f"manifest:{exc}"]}, indent=2))
        return 1

    inputs = manifest.get("inputs", [])
    paths = [row.get("path") for row in inputs if isinstance(row, dict)]
    check(checks, failures, "manifest_count_36", manifest.get("input_count") == 36 == len(inputs))
    check(checks, failures, "manifest_paths_unique", len(paths) == len(inputs) == len(set(paths)))
    matched = 0
    json_verified = 0
    for row in inputs:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            failures.append("invalid_manifest_row")
            continue
        path = ROOT / row["path"]
        if not path.is_file():
            failures.append(f"missing:{row['path']}")
            continue
        try:
            payload = canonical_lf(path)
            digest = hashlib.sha256(payload).hexdigest()
            if len(payload) != row.get("canonical_lf_bytes") or digest != row.get("canonical_lf_sha256"):
                failures.append(f"hash:{row['path']}")
                continue
            if path.suffix.casefold() == ".json":
                load_json(path)
                json_verified += 1
            matched += 1
        except Exception as exc:
            failures.append(f"parse:{row['path']}:{exc}")
    check(checks, failures, "frozen_inputs_36_of_36", matched == 36)
    check(
        checks,
        failures,
        "strict_json_17_of_17",
        manifest.get("json_input_count") == 17 == json_verified,
    )
    check(
        checks,
        failures,
        "manifest_entry_and_candidate_lock",
        manifest.get("entry_gate")
        == "R5_M2_USER_APPROVED_BOUNDED_DATASET_ENVIRONMENT_AND_COMMAND_MATERIALIZATION"
        and manifest.get("selected_candidate", {}).get("candidate_id") == SELECTED_CANDIDATE
        and manifest.get("selected_candidate", {}).get("source_revision") == SELECTED_REVISION
        and manifest.get("parallel_stages") == ["R6-D1", "R6-E1"]
        and manifest.get("parallel_stage_count") == 2,
    )
    check(
        checks,
        failures,
        "manifest_model_profiles",
        manifest.get("model_policy", {}).get("central")
        == exact_profile("Sol Max Standard", "max", "standard")
        and manifest.get("model_policy", {}).get("parallel_workers")
        == exact_profile("Sol XHigh Fast", "xhigh", "priority"),
    )
    boundary = manifest.get("stage_boundary", {})
    check(
        checks,
        failures,
        "manifest_no_execution_boundary",
        boundary.get("worker_web_research_on_authoritative_sources") is True
        and boundary.get("worker_download_or_extraction") is False
        and boundary.get("worker_environment_creation_or_package_install") is False
        and boundary.get("worker_vendor_source_execution") is False
        and boundary.get("worker_training_or_evaluation") is False
        and boundary.get("worker_project_v5_test_access") is False
        and boundary.get("central_materialization_before_r6_g0_and_validated_r6_c1") is False
        and boundary.get("experiment_execution_authorized") is False
        and boundary.get("benchmark_admission_authorized") is False,
    )
    check(checks, failures, "manifest_truth", manifest.get("truth_state") == TRUTH)

    approval = load_json(CONTROL / "e4_r5_m2_user_approval_receipt.json")
    grants = approval.get("authorization_grants", {})
    prohibited = approval.get("still_prohibited", {})
    state = approval.get("authorization_state", {})
    check(
        checks,
        failures,
        "user_approval_is_bounded_materialization_only",
        approval.get("stage_id") == "R5-M2"
        and approval.get("status")
        == "USER_APPROVED_BOUNDED_DATASET_ENVIRONMENT_AND_COMMAND_MATERIALIZATION_SCOPE"
        and grants.get("official_dataset_archive_download") is True
        and grants.get("recbole_atomic_representation_materialization") is True
        and grants.get("isolated_environment_creation") is True
        and grants.get("test_safe_command_config_and_wrapper_proposal") is True
        and state.get("materialization_authorized") is True
        and state.get("experiment_execution_authorized") is False
        and state.get("test_access_authorized") is False
        and state.get("benchmark_admission_authorized") is False,
    )
    check(
        checks,
        failures,
        "user_prohibitions_remain_locked",
        prohibited.get("non_grouplens_dataset_or_mirror_download") is True
        and prohibited.get("checkpoint_or_pretrained_weight_download") is True
        and prohibited.get("vendor_training_execution") is True
        and prohibited.get("hyperparameter_search") is True
        and prohibited.get("source_evaluator_execution") is True
        and prohibited.get("harmonized_v5_evaluation") is True
        and prohibited.get("project_v5_test_access") is True
        and prohibited.get("paper_benchmark_admission") is True
        and prohibited.get("acceptance_of_documented_ndcg_0_2768") is True,
    )
    check(checks, failures, "approval_truth", approval.get("truth_state") == TRUTH)

    decision = load_json(SELECTION_ROOT / "selection_decision.json")
    selected = decision.get("selected_candidate", {})
    decision_boundaries = decision.get("selection_boundaries", {})
    check(
        checks,
        failures,
        "r5_g1_exact_single_candidate",
        decision.get("decision") == "PROVISIONAL_SINGLE_CANDIDATE_FOR_DATA_ENVIRONMENT_PROPOSAL"
        and decision.get("selected_count") == 1
        and selected.get("candidate_id") == SELECTED_CANDIDATE
        and selected.get("source_revision") == SELECTED_REVISION
        and selected.get("reference_dataset") == "MovieLens 100K",
    )
    check(
        checks,
        failures,
        "r5_g1_selection_is_not_admission_or_execution",
        decision_boundaries.get("selection_is_benchmark_admission") is False
        and decision_boundaries.get("selection_verifies_reproducibility") is False
        and decision_boundaries.get("selection_accepts_documented_numeric_target") is False
        and decision_boundaries.get("selection_authorizes_vendor_source_execution") is False
        and decision_boundaries.get("selection_authorizes_preprocessing_training_or_evaluation") is False
        and decision_boundaries.get("selection_authorizes_project_v5_test_access") is False,
    )
    check(checks, failures, "decision_truth", decision.get("truth_state") == TRUTH)

    g1_receipt = load_json(CONTROL / "rebaseline_v2_e4_r5_g1_validation_receipt.json")
    check(
        checks,
        failures,
        "r5_g1_central_validation_passed",
        g1_receipt.get("passed") is True
        and g1_receipt.get("failure_count") == 0
        and g1_receipt.get("decision", {}).get("selected_candidate_id") == SELECTED_CANDIDATE
        and g1_receipt.get("decision", {}).get("benchmark_admitted_candidates") == 0,
    )

    candidate_lock = load_json(CONTROL / "e4_r5_candidate_lock.json")
    candidate_rows = {
        row.get("candidate_id"): row
        for row in candidate_lock.get("candidates", [])
        if isinstance(row, dict)
    }
    locked = candidate_rows.get(SELECTED_CANDIDATE, {})
    check(
        checks,
        failures,
        "source_revision_and_numeric_status_locked",
        locked.get("full_revision") == SELECTED_REVISION
        and locked.get("dataset") == "MovieLens 100K"
        and locked.get("benchmark_admission_status") == "NOT_ADMITTED"
        and locked.get("reference_surface", {}).get("numeric_target_status")
        == "PROVISIONAL_NOT_REPRODUCED_INVALID_FOR_PAPER",
    )

    policy = load_json(CONTROL / "e4_r5_future_subagent_model_policy.json")
    profiles = policy.get("future_subagent_profiles", {})
    central_profile = policy.get("central_profile", {})
    check(
        checks,
        failures,
        "future_fast_model_policy_replayed",
        profiles.get("critical_judgment", {}).get("display_name") == "Sol XHigh Fast"
        and profiles.get("critical_judgment", {}).get("reasoning_effort") == "xhigh"
        and profiles.get("critical_judgment", {}).get("service_tier") == "priority"
        and profiles.get("bounded_execution", {}).get("display_name") == "Sol High Fast"
        and profiles.get("bounded_execution", {}).get("reasoning_effort") == "high"
        and profiles.get("bounded_execution", {}).get("service_tier") == "priority"
        and central_profile.get("display_name") == "Sol Max Standard"
        and central_profile.get("runtime_model_id") == "gpt-5.6-sol"
        and central_profile.get("reasoning_effort") == "max"
        and central_profile.get("service_tier") == "standard"
        and central_profile.get("unchanged") is True,
    )
    check(checks, failures, "model_policy_truth", policy.get("truth_state") == TRUTH)

    stage_map = load_json(CONTROL / "e4_r6_materialization_stage_map.json")
    phases = {
        row.get("id"): row
        for row in stage_map.get("phases", [])
        if isinstance(row, dict)
    }
    expected_phase_ids = {
        "R6-S0",
        "R6-D1",
        "R6-E1",
        "R6-G0",
        "R6-C1",
        "R6-M0",
        "R6-M1",
        "R6-A1",
        "R6-G1",
    }
    check(checks, failures, "exact_r6_stage_set", set(phases) == expected_phase_ids)
    check(
        checks,
        failures,
        "parallel_lanes_are_disjoint_and_gated",
        phases.get("R6-D1", {}).get("dependencies") == ["R6-S0"]
        and phases.get("R6-E1", {}).get("dependencies") == ["R6-S0"]
        and phases.get("R6-D1", {}).get("parallel_group") == "R6-DE"
        and phases.get("R6-E1", {}).get("parallel_group") == "R6-DE"
        and phases.get("R6-D1", {}).get("write_root")
        != phases.get("R6-E1", {}).get("write_root")
        and phases.get("R6-G0", {}).get("dependencies")
        == ["R6-D1", "R6-E1", "CENTRAL_LANE_VALIDATION"],
    )
    check(
        checks,
        failures,
        "r6_stage_models_match_importance",
        phases.get("R6-S0", {}).get("model_profile") == "central"
        and phases.get("R6-D1", {}).get("model_profile") == "critical_judgment_worker"
        and phases.get("R6-E1", {}).get("model_profile") == "critical_judgment_worker"
        and phases.get("R6-C1", {}).get("model_profile") == "bounded_execution_worker"
        and phases.get("R6-A1", {}).get("model_profile") == "critical_judgment_worker"
        and phases.get("R6-G1", {}).get("model_profile") == "central",
    )
    execution_boundary = stage_map.get("execution_boundary", {})
    check(
        checks,
        failures,
        "stage_map_scientific_execution_closed",
        execution_boundary.get("training") is False
        and execution_boundary.get("evaluation") is False
        and execution_boundary.get("hyperparameter_search") is False
        and execution_boundary.get("checkpoint_download") is False
        and execution_boundary.get("project_v5_test_access") is False
        and execution_boundary.get("paper_benchmark_admission") is False
        and execution_boundary.get("experiment_execution_authorized") is False,
    )
    check(checks, failures, "stage_map_truth", stage_map.get("truth_state") == TRUTH)

    contract = (CONTROL / "e4_r6_bounded_materialization_contract.md").read_text(encoding="utf-8")
    required_contract_fragments = [
        "E4_R6D1_movielens100k_authority_lineage",
        "provider_authority.json",
        "rights_and_release_record.md",
        "data_lineage_plan.json",
        "materialization_command_proposal.json",
        "E4_R6E1_recbole_environment_closure",
        "compatibility_matrix.json",
        "environment_lock_proposal.json",
        "environment_command_proposal.json",
        "risk_report.md",
        "audit_handoff.json",
        "Training, evaluation and TEST remain blocked",
    ]
    check(
        checks,
        failures,
        "bounded_contract_has_exact_outputs_and_stop_boundary",
        all(fragment in contract for fragment in required_contract_fragments),
    )

    recbole_urls = (SOURCE / "recbole/properties/dataset/url.yaml").read_text(encoding="utf-8")
    check(
        checks,
        failures,
        "recbole_processed_s3_route_detected_but_not_provider_authority",
        "ml-100k: https://recbole.s3-accelerate.amazonaws.com/ProcessedDatasets/MovieLens/ml-100k.zip"
        in recbole_urls
        and manifest.get("source_hierarchy", {}).get(
            "recbole_processed_dataset_s3_route_is_canonical_provider_authority"
        )
        is False,
    )
    setup_text = (SOURCE / "setup.py").read_text(encoding="utf-8")
    check(
        checks,
        failures,
        "environment_lane_has_pinned_dependency_surface",
        all(
            token in setup_text
            for token in [
                "torch>=1.10.0",
                "numpy>=1.17.2",
                "scipy>=1.6.0",
                "pandas>=1.3.0",
                "scikit_learn>=0.23.2",
                "pyyaml>=5.1.0",
            ]
        ),
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r6-s0-gate-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R6_S0_FROZEN_36_OF_36_READY_FOR_PARALLEL_R6_D1_R6_E1"
            if passed
            else "FAIL_R6_S0_GATE_BLOCKED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {
            "matched": matched,
            "expected": 36,
            "strict_json": json_verified,
            "strict_json_expected": 17,
        },
        "parallel_stages": ["R6-D1", "R6-E1"],
        "model_profile": exact_profile("Sol XHigh Fast", "xhigh", "priority"),
        "materialization_authorized": True,
        "experiment_execution_authorized": False,
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
