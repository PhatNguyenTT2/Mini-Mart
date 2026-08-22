from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r5_s0_frozen_input_manifest.json"
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
CANDIDATES = {
    "R5-CAND-RECBOLE-BPR-ML100K-001": {
        "origin": "R4-D1C-PROP-001",
        "repo": "https://github.com/RUCAIBox/RecBole.git",
        "canonical_repo": "https://github.com/RUCAIBox/RecBole",
        "revision": "9a6f63d8d4a5b989fe27955a833f813a6d86041e",
        "failed": {
            "D03_BYTE_VERIFIABLE_LINEAGE",
            "D05_ENVIRONMENT_LOCK",
            "D07_EXACT_PROTOCOL_CONFIG_SEEDS",
            "D08_EVALUATOR_SEMANTICS",
            "D09_SAME_SURFACE_NUMERIC_TARGET",
            "D10_NO_TEST_DERIVATION",
            "D11_BOUNDED_V5_ADAPTER",
        },
    },
    "R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001": {
        "origin": "R4-D1B-PROP-003",
        "repo": "https://github.com/RUCAIBox/RecBole-GNN.git",
        "canonical_repo": "https://github.com/RUCAIBox/RecBole-GNN",
        "revision": "632ef888589944c190ad8f449b49ca559618d4df",
        "failed": {
            "D01_AFFIRMATIVE_CODE_LICENSE",
            "D02_CANONICAL_DATASET_RIGHTS",
            "D03_BYTE_VERIFIABLE_LINEAGE",
            "D05_ENVIRONMENT_LOCK",
            "D07_EXACT_PROTOCOL_CONFIG_SEEDS",
            "D08_EVALUATOR_SEMANTICS",
            "D09_SAME_SURFACE_NUMERIC_TARGET",
            "D10_NO_TEST_DERIVATION",
            "D11_BOUNDED_V5_ADAPTER",
        },
    },
}
R4_IDS = {
    *{f"R4-D1A-PROP-{index:03d}" for index in range(1, 6)},
    *{f"R4-D1B-PROP-{index:03d}" for index in range(1, 6)},
    *{f"R4-D1C-PROP-{index:03d}" for index in range(1, 9)},
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


def find_r4_row(log: dict[str, Any], proposal_id: str) -> dict[str, Any] | None:
    for row in log.get("excluded_candidates", []):
        if isinstance(row, dict) and row.get("proposal_id") == proposal_id:
            return row
    return None


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    try:
        manifest = load_json(MANIFEST)
    except Exception as exc:
        print(json.dumps({"passed": False, "failures": [f"manifest_parse:{exc}"]}, indent=2))
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
    check(checks, failures, "manifest_rows_are_objects", len(paths) == len(inputs))
    check(checks, failures, "manifest_paths_unique", len(paths) == len(set(paths)))

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
    check(checks, failures, "strict_json_inputs_13_of_13", json_verified == 13)
    check(
        checks,
        failures,
        "manifest_entry_decision",
        manifest.get("entry_decision", {}).get("source_verdict")
        == "NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED"
        and manifest.get("entry_decision", {}).get("user_scope_decision")
        == "AUTHORIZE_TARGETED_SOURCE_ONLY_EVIDENCE_MATERIALIZATION_REDESIGN"
        and manifest.get("entry_decision", {}).get("r4_admitted_bundle_count") == 0,
    )
    check(
        checks,
        failures,
        "manifest_gate_redesign",
        manifest.get("gate_redesign")
        == {
            "pre_source_candidate_count": 2,
            "final_r4_d01_d12_gate_retained": True,
            "source_materialization_is_benchmark_admission": False,
            "dataset_environment_or_execution_authorized": False,
            "next_user_checkpoint": "R5-M2",
        },
    )
    check(
        checks,
        failures,
        "manifest_model_policy",
        manifest.get("model_policy") == {"central": CENTRAL_MODEL, "workers": WORKER_MODEL},
    )
    check(checks, failures, "manifest_truth_state", manifest.get("truth_state") == TRUTH)

    stage_map = load_json(CONTROL / "e4_r5_stage_map.json")
    phases = {
        row.get("id"): row
        for row in stage_map.get("phases", [])
        if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "all_stage_ids_present",
        set(phases) == {"R5-S0", "R5-M0", "R5-M1A", "R5-M1B", "R5-G1", "R5-M2"},
    )
    check(
        checks,
        failures,
        "m1_parallel_fresh_workers",
        {phases[s].get("parallel_group") for s in ("R5-M1A", "R5-M1B")} == {"R5-M1"}
        and all(phases[s].get("context") == "fresh_worker" for s in ("R5-M1A", "R5-M1B")),
    )
    check(
        checks,
        failures,
        "central_stages_and_m2_checkpoint",
        all(phases[s].get("context") == "current_central" for s in ("R5-S0", "R5-M0", "R5-G1"))
        and phases["R5-M2"].get("context") == "user_and_central_control",
    )
    map_models = stage_map.get("model_policy", {})
    check(
        checks,
        failures,
        "central_sol_max_standard",
        all(map_models.get("central", {}).get(k) == v for k, v in CENTRAL_MODEL.items()),
    )
    check(
        checks,
        failures,
        "workers_sol_xhigh_standard",
        all(map_models.get("workers", {}).get(k) == v for k, v in WORKER_MODEL.items()),
    )
    boundary = stage_map.get("execution_boundary", {})
    check(
        checks,
        failures,
        "stage_map_source_only_fail_closed",
        boundary.get("named_repository_metadata_and_allowlisted_source_after_s0") is True
        and boundary.get("generic_repository_or_archive_download") is False
        and boundary.get("dataset_checkpoint_or_asset_download") is False
        and boundary.get("package_install_or_environment_creation") is False
        and boundary.get("vendor_source_execution") is False
        and boundary.get("preprocessing_training_evaluation") is False
        and boundary.get("test_access") is False
        and boundary.get("execution_authorized") is False,
    )
    check(checks, failures, "stage_map_truth_state", stage_map.get("truth_state") == TRUTH)

    lock = load_json(CONTROL / "e4_r5_candidate_lock.json")
    rows = {
        row.get("candidate_id"): row
        for row in lock.get("candidates", [])
        if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "exact_two_locked_candidates",
        lock.get("candidate_count") == 2 and set(rows) == set(CANDIDATES),
    )
    for candidate_id, expected in CANDIDATES.items():
        row = rows.get(candidate_id, {})
        gate = row.get("pre_materialization_gate", {})
        check(
            checks,
            failures,
            f"candidate_identity_{candidate_id}",
            row.get("origin_r4_proposal_id") == expected["origin"]
            and row.get("repository_url") == expected["repo"]
            and row.get("canonical_repository_url") == expected["canonical_repo"]
            and row.get("full_revision") == expected["revision"]
            and set(row.get("r4_failed_dimension_ids", [])) == expected["failed"]
            and row.get("r4_exclusion_status") == "EXCLUDE_INCOMPLETE_BUNDLE"
            and row.get("dispositive_conflicts") == [],
        )
        check(
            checks,
            failures,
            f"candidate_pre_source_gate_{candidate_id}",
            set(gate) == {
                "named_repository_and_owner_verified",
                "full_immutable_revision_verified",
                "affirmative_code_license_verified",
                "public_unauthenticated_source_access",
                "no_dispositive_conflict",
                "scope_and_sparse_path_policy_locked",
            }
            and all(str(value).startswith("PASS") for value in gate.values())
            and row.get("benchmark_admission_status") == "NOT_ADMITTED",
        )
    check(checks, failures, "candidate_lock_truth_state", lock.get("truth_state") == TRUTH)

    materialization = load_json(CONTROL / "e4_r5_source_materialization_contract.json")
    mats = {
        row.get("candidate_id"): row
        for row in materialization.get("materializations", [])
        if isinstance(row, dict)
    }
    expected_roots = {
        "research/hybrid-recsys-v5/03_benchmark/stage1e/materialized_sources/r5/recbole_v1_2_1_9a6f63d",
        "research/hybrid-recsys-v5/03_benchmark/stage1e/materialized_sources/r5/recbole_gnn_632ef88",
    }
    check(
        checks,
        failures,
        "materialization_exact_two_locked_sources",
        materialization.get("candidate_count") == 2
        and set(mats) == set(CANDIDATES)
        and {row.get("local_root") for row in mats.values()} == expected_roots
        and all(mats[cid].get("repository_url") == CANDIDATES[cid]["repo"] for cid in CANDIDATES)
        and all(mats[cid].get("full_revision") == CANDIDATES[cid]["revision"] for cid in CANDIDATES),
    )
    check(
        checks,
        failures,
        "materialization_sparse_scopes",
        mats.get("R5-CAND-RECBOLE-BPR-ML100K-001", {}).get("sparse_cone_directories") == ["recbole"]
        and mats.get("R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001", {}).get("sparse_cone_directories")
        == ["recbole_gnn", "properties", "results"],
    )
    scope = materialization.get("source_scope", {})
    forbidden = materialization.get("forbidden_operations", {})
    exit_gate = materialization.get("exit_gate", {})
    check(
        checks,
        failures,
        "source_scope_rejects_assets_and_execution",
        scope.get("git_submodules_allowed") is False
        and scope.get("git_lfs_objects_allowed") is False
        and scope.get("selected_symlinks_allowed") is False
        and scope.get("vendor_source_modification_allowed") is False
        and scope.get("vendor_source_execution_allowed") is False
        and "dataset" in scope.get("prohibited_top_level_directories", [])
        and "dataset_example" in scope.get("prohibited_top_level_directories", []),
    )
    check(
        checks,
        failures,
        "all_forbidden_operations_true",
        len(forbidden) == 11 and all(value is True for value in forbidden.values()),
    )
    check(
        checks,
        failures,
        "materialization_exit_truth",
        exit_gate.get("dataset_bytes_acquired") is False
        and exit_gate.get("execution_performed") is False
        and exit_gate.get("test_opened") is False
        and materialization.get("truth_state") == TRUTH,
    )

    d1c_log = load_json(
        ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_w/"
        "E4_R4D1C_framework_packet_scout/excluded_candidate_log.json"
    )
    d1b_log = load_json(
        ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_v/"
        "E4_R4D1B_benchmark_suite_scout/excluded_candidate_log.json"
    )
    r4_core = find_r4_row(d1c_log, "R4-D1C-PROP-001")
    r4_gnn = find_r4_row(d1b_log, "R4-D1B-PROP-003")
    check(
        checks,
        failures,
        "r4_target_rows_non_dispositive_exact_identity",
        isinstance(r4_core, dict)
        and isinstance(r4_gnn, dict)
        and r4_core.get("exclusion_status") == "EXCLUDE_INCOMPLETE_BUNDLE"
        and r4_gnn.get("exclusion_status") == "EXCLUDE_INCOMPLETE_BUNDLE"
        and r4_core.get("dispositive_conflicts") == []
        and r4_gnn.get("dispositive_conflicts") == []
        and r4_core.get("identity_summary", {}).get("full_revision") == CANDIDATES["R5-CAND-RECBOLE-BPR-ML100K-001"]["revision"]
        and r4_gnn.get("identity_summary", {}).get("full_revision") == CANDIDATES["R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001"]["revision"],
    )

    d1c_sources = load_json(
        ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_w/"
        "E4_R4D1C_framework_packet_scout/source_replay_log.json"
    )
    source_by_id = {
        row.get("evidence_id"): row
        for row in d1c_sources.get("source_records", [])
        if isinstance(row, dict)
    }
    core_license = source_by_id.get("R4-D1C-EVID-008", {})
    check(
        checks,
        failures,
        "recbole_license_and_revision_primary_replayed",
        core_license.get("access_status") == "REPLAYED_PRIMARY"
        and "MIT" in core_license.get("evidence_note", "")
        and CANDIDATES["R5-CAND-RECBOLE-BPR-ML100K-001"]["revision"] in core_license.get("url", ""),
    )
    e5_replay = load_json(
        ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_c/"
        "E5_independent_lock_audit/replay_receipt.json"
    )
    e5_by_id = {
        row.get("replay_id"): row
        for row in e5_replay.get("external_source_replays", [])
        if isinstance(row, dict)
    }
    gnn_license = e5_by_id.get("SR019", {})
    check(
        checks,
        failures,
        "recbole_gnn_license_primary_replayed",
        gnn_license.get("result") == "CONFIRMED"
        and gnn_license.get("claim") == "MIT code license grant"
        and gnn_license.get("immutable_revision")
        == CANDIDATES["R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001"]["revision"],
    )

    r4_decision = load_json(
        ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_x/"
        "E4_R4G0_strict_admission_freeze/r4_g0_admission_decision.json"
    )
    r4_receipt = load_json(CONTROL / "rebaseline_v2_e4_r4_g0_validation_receipt.json")
    check(
        checks,
        failures,
        "r4_closed_zero_admissions",
        r4_decision.get("decision", {}).get("verdict") == "NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED"
        and r4_decision.get("decision", {}).get("frozen_bundle_count") == 0
        and r4_decision.get("decision", {}).get("materialization_allowed") is False
        and r4_receipt.get("passed") is True
        and r4_receipt.get("failure_count") == 0,
    )
    check(
        checks,
        failures,
        "r4_truth_retained",
        r4_decision.get("truth_state") == TRUTH and r4_receipt.get("truth_state") == TRUTH,
    )

    registry = load_json(CONTROL / "e4_r5_transition_registry.json")
    registry_rows = [row for row in registry.get("rows", []) if isinstance(row, dict)]
    targeted = {
        row.get("row_id")
        for row in registry_rows
        if row.get("r5_status") == "TARGETED_SOURCE_INSPECTION_ONLY_NOT_ADMITTED"
    }
    archived = {
        row.get("row_id")
        for row in registry_rows
        if row.get("r5_status") == "ARCHIVED_R4_EXCLUSION_NOT_RECONSIDERED"
    }
    check(
        checks,
        failures,
        "transition_registry_exact_r4_rows",
        len(registry_rows) == 18
        and {row.get("row_id") for row in registry_rows} == R4_IDS
        and targeted == {"R4-D1B-PROP-003", "R4-D1C-PROP-001"}
        and len(archived) == 16
        and registry.get("r4_proposal_count") == 18
        and registry.get("targeted_source_inspection_count") == 2,
    )
    policy = registry.get("policy", {})
    check(
        checks,
        failures,
        "transition_preserves_r4_and_no_admission",
        policy.get("r4_artifact_deletion_performed") is False
        and policy.get("r4_exclusion_statuses_overwritten") is False
        and policy.get("r4_rows_execution_eligible") is False
        and policy.get("r5_targeted_rows_benchmark_admitted") is False
        and policy.get("cross_join_allowed") is False
        and policy.get("source_only_materialization_is_reproducibility_verification") is False,
    )
    check(checks, failures, "transition_truth_state", registry.get("truth_state") == TRUTH)

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    check(
        checks,
        failures,
        "vendor_source_root_exactly_ignored",
        gitignore.count("research/hybrid-recsys-v5/03_benchmark/stage1e/materialized_sources/r5/") == 1,
    )
    contract = (CONTROL / "e4_r5_source_only_materialization_change_control.md").read_text(encoding="utf-8")
    markers = [
        "AUTHORIZE_TARGETED_SOURCE_ONLY_EVIDENCE_MATERIALIZATION_REDESIGN",
        "Execution authority: SOURCE_ONLY_CONDITIONAL_AFTER_R5_S0",
        "R5-M1A",
        "R5-M1B",
        "R5-G1",
        "R5-M2",
        "Sol XHigh Standard",
        "Sol Max Standard",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
        "ACCEPTED_RESULT_ROWS=0",
    ]
    check(checks, failures, "contract_policy_markers", all(marker in contract for marker in markers))

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-s0-gate-result-1.0",
        "passed": passed,
        "verdict": "PASS_R5_S0_SOURCE_ONLY_GATE_20_OF_20_READY_FOR_R5_M0" if passed else "FAIL_R5_S0_GATE_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {
            "expected": 20,
            "matched": matched,
            "strict_json_expected": 13,
            "strict_json_verified": json_verified,
        },
        "candidate_lock": {
            "locked": len(rows),
            "source_materialization_maximum": 2,
            "benchmark_admitted": 0,
        },
        "model_policy": {"central": CENTRAL_MODEL, "workers": WORKER_MODEL},
        "execution_boundary": {
            "named_source_only_after_gate": True,
            "dataset_environment_execution": False,
            "test_access": False,
        },
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
