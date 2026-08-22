from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r4_s0_frozen_input_manifest.json"
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
CENTRAL_MODEL = {
    "display_name": "Sol Max Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "max",
    "service_tier": "standard",
}
WORKER_MODEL = {
    "display_name": "Sol XHigh Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "xhigh",
    "service_tier": "standard",
}
DIMENSIONS = {
    "D01_AFFIRMATIVE_CODE_LICENSE",
    "D02_CANONICAL_DATASET_RIGHTS",
    "D03_BYTE_VERIFIABLE_LINEAGE",
    "D04_IMMUTABLE_FULL_REVISION",
    "D05_ENVIRONMENT_LOCK",
    "D06_EXECUTABLE_TRAIN_ENTRYPOINT",
    "D07_EXACT_PROTOCOL_CONFIG_SEEDS",
    "D08_EVALUATOR_SEMANTICS",
    "D09_SAME_SURFACE_NUMERIC_TARGET",
    "D10_NO_TEST_DERIVATION",
    "D11_BOUNDED_V5_ADAPTER",
    "D12_ALL_LOCATORS_REPLAYED",
}


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    lowered: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in lowered and lowered[folded] != key:
            raise ContractError(
                f"case-colliding JSON keys: {lowered[folded]} / {key}"
            )
        lowered[folded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_or_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check(
    checks: dict[str, bool],
    failures: list[str],
    name: str,
    condition: bool,
) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    try:
        manifest = load_json(MANIFEST)
    except Exception as exc:
        print(
            json.dumps(
                {"passed": False, "failures": [f"manifest_parse:{exc}"]},
                indent=2,
            )
        )
        return 1

    inputs = manifest.get("inputs")
    check(checks, failures, "manifest_inputs_is_list", isinstance(inputs, list))
    if not isinstance(inputs, list):
        inputs = []
    paths = [row.get("path") for row in inputs if isinstance(row, dict)]
    check(
        checks,
        failures,
        "manifest_input_count_20",
        manifest.get("input_count") == 20 == len(inputs),
    )
    check(
        checks,
        failures,
        "manifest_rows_are_objects",
        len(paths) == len(inputs),
    )
    check(
        checks,
        failures,
        "manifest_paths_unique",
        len(paths) == len(set(paths)),
    )

    matched = 0
    json_verified = 0
    for index, row in enumerate(inputs):
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            failures.append(f"input_{index}_invalid")
            continue
        relative = row["path"]
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        try:
            payload = canonical_lf(path)
            digest = hashlib.sha256(payload).hexdigest()
        except Exception as exc:
            failures.append(f"read_or_utf8:{relative}:{exc}")
            continue
        if len(payload) != row.get("canonical_lf_bytes"):
            failures.append(f"byte_mismatch:{relative}")
            continue
        if digest != row.get("canonical_lf_sha256"):
            failures.append(f"hash_mismatch:{relative}")
            continue
        if path.suffix.lower() == ".json":
            try:
                load_json(path)
                json_verified += 1
            except Exception as exc:
                failures.append(f"strict_json:{relative}:{exc}")
                continue
        matched += 1

    check(checks, failures, "frozen_inputs_20_of_20", matched == 20)
    check(
        checks,
        failures,
        "strict_json_inputs_12_of_12",
        json_verified == 12,
    )
    check(
        checks,
        failures,
        "manifest_entry_decision",
        manifest.get("entry_decision", {}).get("user_scope_decision")
        == "START_NEW_STRICT_DISCOVERY_WAVE"
        and manifest.get("entry_decision", {}).get("source_verdict")
        == "NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT"
        and manifest.get("entry_decision", {}).get("r3_selected_count") == 0,
    )
    check(
        checks,
        failures,
        "manifest_admission_policy",
        manifest.get("admission_policy")
        == {
            "mandatory_dimension_count": 12,
            "all_dimensions_must_pass": True,
            "unresolved_mandatory_fields_allowed": 0,
            "scout_admitted_minimum": 0,
            "central_frozen_maximum": 3,
            "selection_cardinality_max": 1,
            "cross_join_allowed": False,
            "automatic_fallback_allowed": False,
        },
    )
    check(
        checks,
        failures,
        "manifest_model_policy",
        manifest.get("model_policy")
        == {"central": CENTRAL_MODEL, "workers": WORKER_MODEL},
    )
    check(
        checks,
        failures,
        "manifest_truth_state",
        manifest.get("truth_state") == TRUTH,
    )

    stage_map = load_json(CONTROL / "e4_r4_stage_map.json")
    phases = {
        row.get("id"): row
        for row in stage_map.get("phases", [])
        if isinstance(row, dict)
    }
    expected_phases = {
        "R4-S0",
        "R4-D1A",
        "R4-D1B",
        "R4-D1C",
        "R4-G0",
        "R4-A1",
        "R4-A2",
        "R4-A3",
        "R4-G1",
        "R4-M0",
    }
    check(
        checks,
        failures,
        "stage_map_entry_decision",
        stage_map.get("entry_checkpoint", {}).get("decision")
        == "START_NEW_STRICT_DISCOVERY_WAVE",
    )
    check(
        checks,
        failures,
        "all_stage_ids_present",
        set(phases) == expected_phases,
    )
    check(
        checks,
        failures,
        "d1_parallel_group",
        {
            phases[stage].get("parallel_group")
            for stage in ("R4-D1A", "R4-D1B", "R4-D1C")
        }
        == {"R4-D1"},
    )
    check(
        checks,
        failures,
        "audits_conditional_and_parallel",
        {
            phases[stage].get("parallel_group")
            for stage in ("R4-A1", "R4-A2", "R4-A3")
        }
        == {"R4-A"}
        and all(
            phases[stage].get("status") == "CONDITIONAL_ON_POSITIVE_R4_G0"
            for stage in ("R4-A1", "R4-A2", "R4-A3")
        ),
    )
    map_models = stage_map.get("model_policy", {})
    check(
        checks,
        failures,
        "central_sol_max_standard",
        all(
            map_models.get("central", {}).get(key) == value
            for key, value in CENTRAL_MODEL.items()
        ),
    )
    check(
        checks,
        failures,
        "workers_sol_xhigh_standard",
        all(
            map_models.get("workers", {}).get(key) == value
            for key, value in WORKER_MODEL.items()
        ),
    )
    check(
        checks,
        failures,
        "stage_map_fail_closed",
        stage_map.get("candidate_policy", {}).get("cross_join_allowed") is False
        and stage_map.get("candidate_policy", {}).get(
            "automatic_fallback_allowed"
        )
        is False
        and stage_map.get("candidate_policy", {}).get(
            "unresolved_mandatory_fields_allowed"
        )
        == 0
        and stage_map.get("execution_boundary", {}).get(
            "execution_authorized"
        )
        is False
        and stage_map.get("execution_boundary", {}).get("test_access") is False,
    )
    check(
        checks,
        failures,
        "stage_map_truth_state",
        stage_map.get("truth_state") == TRUTH,
    )

    admission = load_json(CONTROL / "e4_r4_strict_admission_contract.json")
    dimension_rows = admission.get("mandatory_dimensions", [])
    dimension_ids = {
        row.get("id") for row in dimension_rows if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "exact_twelve_mandatory_dimensions",
        len(dimension_rows) == 12 and dimension_ids == DIMENSIONS,
    )
    check(
        checks,
        failures,
        "proposal_patterns_valid",
        re.compile(admission.get("proposal_id_pattern", "")).pattern
        == "^R4-D1[ABC]-PROP-[0-9]{3}$"
        and re.compile(
            admission.get("central_bundle_id_pattern", "")
        ).pattern.startswith("^R4-BUNDLE-"),
    )
    invariant = admission.get("admission_invariant", {})
    check(
        checks,
        failures,
        "admission_is_strict_conjunction",
        invariant.get("mandatory_dimension_count") == 12
        and invariant.get("required_dimension_status")
        == "PASS_PRIMARY_REPLAYED"
        and invariant.get("unresolved_mandatory_field_count") == 0
        and invariant.get("dispositive_conflict_count") == 0
        and invariant.get("same_surface_join_required") is True
        and invariant.get("cross_join_allowed") is False
        and invariant.get("inference_can_satisfy_dimension") is False
        and invariant.get("weighted_compensation_allowed") is False,
    )
    outputs = admission.get("scout_output_contract", {})
    check(
        checks,
        failures,
        "scout_exact_five_outputs",
        outputs.get("exact_filenames")
        == [
            "scout_candidates.json",
            "source_replay_log.json",
            "excluded_candidate_log.json",
            "scout_report.md",
            "scout_handoff.json",
        ]
        and outputs.get("extra_files_allowed") is False
        and outputs.get("zero_admission_is_valid") is True,
    )
    check(
        checks,
        failures,
        "g0_independent_replay_no_repair",
        admission.get("central_g0_contract", {}).get(
            "independent_central_replay_required"
        )
        is True
        and admission.get("central_g0_contract", {}).get(
            "central_repair_or_evidence_substitution_allowed"
        )
        is False,
    )
    check(
        checks,
        failures,
        "admission_truth_state",
        admission.get("truth_state") == TRUTH,
    )

    prior_decision = load_json(
        ROOT
        / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
        "wave_t/E4_R3G1_bundle_selection/selection_decision.json"
    )
    prior_ids = set(prior_decision.get("candidate_ids", []))
    registry = load_json(CONTROL / "e4_r4_supersession_registry.json")
    archived_ids = {
        row.get("row_id")
        for row in registry.get("rows", [])
        if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "r3_no_selection_frozen",
        prior_decision.get("decision", {}).get("verdict")
        == "NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT"
        and prior_decision.get("decision", {}).get("selected_candidate_count")
        == 0
        and prior_decision.get("decision", {}).get("materialization_allowed")
        is False,
    )
    check(
        checks,
        failures,
        "supersession_exact_r3_id_set",
        len(prior_ids) == 3
        and archived_ids == prior_ids
        and registry.get("row_count") == 3,
    )
    check(
        checks,
        failures,
        "all_r3_rows_non_executable",
        all(
            row.get("new_status")
            == "ARCHIVED_R3_NO_SELECTION_NOT_EXECUTION_ELIGIBLE"
            for row in registry.get("rows", [])
            if isinstance(row, dict)
        ),
    )
    check(
        checks,
        failures,
        "supersession_no_deletion_or_cross_join",
        registry.get("policy", {}).get("artifact_deletion_performed") is False
        and registry.get("policy", {}).get(
            "materialized_asset_deletion_required"
        )
        is False
        and registry.get("policy", {}).get(
            "r3_rows_may_be_cross_joined_into_r4"
        )
        is False,
    )
    check(
        checks,
        failures,
        "registry_truth_state",
        registry.get("truth_state") == TRUTH,
    )

    prior_receipt = load_json(
        CONTROL / "rebaseline_v2_e4_r3_g1_validation_receipt.json"
    )
    check(
        checks,
        failures,
        "r3_central_validation_passed",
        prior_receipt.get("passed") is True
        and prior_receipt.get("failure_count") == 0
        and prior_receipt.get("selection", {}).get("selected_candidate_count")
        == 0
        and prior_receipt.get("downstream", {}).get("R3-M0")
        == "NOT_OPENED_NO_SELECTION",
    )
    check(
        checks,
        failures,
        "truth_unchanged_from_r3",
        prior_decision.get("truth_state") == TRUTH
        and prior_receipt.get("truth_state") == TRUTH,
    )

    contract = (
        CONTROL / "e4_r4_strict_discovery_change_control_contract.md"
    ).read_text(encoding="utf-8")
    markers = [
        "User scope decision: START_NEW_STRICT_DISCOVERY_WAVE",
        "Execution authority: DENIED",
        "Sol XHigh Standard",
        "Sol Max Standard",
        "service_tier=standard",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
        "ACCEPTED_RESULT_ROWS=0",
        "R4-M0",
    ]
    check(
        checks,
        failures,
        "contract_policy_markers",
        all(marker in contract for marker in markers),
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r4-s0-gate-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R4_S0_STRICT_GATE_20_OF_20_READY_FOR_R4_D1"
            if passed
            else "FAIL_R4_S0_GATE_BLOCKED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {
            "expected": 20,
            "matched": matched,
            "strict_json_expected": 12,
            "strict_json_verified": json_verified,
        },
        "strict_admission": {
            "mandatory_dimensions": len(dimension_ids),
            "required_dimension_status": "PASS_PRIMARY_REPLAYED",
            "unresolved_mandatory_fields_allowed": 0,
            "scout_admitted_minimum": 0,
            "central_frozen_maximum": 3,
        },
        "model_policy": {
            "central": CENTRAL_MODEL,
            "workers": WORKER_MODEL,
        },
        "archived_r3_candidate_count": len(archived_ids),
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
