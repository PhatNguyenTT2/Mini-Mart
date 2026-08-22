from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = Path(__file__).resolve().parent
MANIFEST = CONTROL / "e4_r2_evidence_frozen_input_manifest.json"

EXPECTED_TASKS = ["R2-A1", "R2-A2", "R2-A3"]
EXPECTED_CANDIDATES = [
    "E3-LIGHTGCN-GOWALLA-PYTORCH-001",
    "E3-SIMGCL-YELP2018-QREC-001",
    "E3-XSIMGCL-YELP2018-SELFREC-001",
    "E3-LIGHTGCL-YELP-UPDATED-001",
    "E3-UNISREC-SCIENTIFIC-TRANS-001",
    "E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001",
    "E3-ALPHAREC-MOVIES-TV-001",
]
EXPECTED_OUTPUTS = {
    "R2-A1": [
        "repo_evidence_register.json",
        "paper_repo_config_binding.json",
        "source_license_decisions.md",
        "a1_handoff.json",
    ],
    "R2-A2": [
        "dataset_evidence_register.json",
        "provider_release_rights_matrix.json",
        "lineage_requirement_map.json",
        "a2_handoff.json",
    ],
    "R2-A3": [
        "result_center_register.json",
        "center_config_seed_checkpoint_binding.json",
        "metric_evaluator_contracts.json",
        "a3_handoff.json",
    ],
}


class GateFailure(RuntimeError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise GateFailure(f"duplicate JSON key: {key}")
        lowered = key.casefold()
        if lowered in folded:
            raise GateFailure(
                f"case-colliding JSON keys: {folded[lowered]} and {key}"
            )
        result[key] = value
        folded[lowered] = key
    return result


def read_lf(path: Path) -> tuple[bytes, str]:
    text = path.read_bytes().decode("utf-8", errors="strict")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return canonical, hashlib.sha256(canonical).hexdigest()


def load_json(path: Path) -> Any:
    raw, _ = read_lf(path)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateFailure(message)


def main() -> None:
    manifest = load_json(MANIFEST)

    require(
        manifest.get("schema_version")
        == "stage1e-rebaseline-v2-e4-r2-evidence-input-1.0",
        "unexpected manifest schema_version",
    )
    require(manifest.get("tasks") == EXPECTED_TASKS, "task order mismatch")
    require(
        manifest.get("model_policy", {}).get("model") == "gpt-5.6-sol"
        and manifest.get("model_policy", {}).get("reasoning") == "xhigh",
        "R2-A model policy mismatch",
    )
    require(
        manifest.get("entry_gate", {}).get("e5_r1_validation")
        == "PASS_E5_R1_REMEDIATION_INTEGRITY_EXECUTION_DENIED",
        "E5-R1 entry gate mismatch",
    )
    require(
        manifest.get("entry_gate", {}).get("r2_plan_validation")
        == "PASS_E4_R2_PLAN_PREPARED_NOT_DISPATCHED_EXECUTION_DENIED",
        "R2 plan entry gate mismatch",
    )
    require(
        manifest.get("candidate_scope", {}).get("ordered_row_ids")
        == EXPECTED_CANDIDATES,
        "candidate scope/order mismatch",
    )
    require(
        manifest.get("candidate_scope", {}).get("selection_cardinality_in_lane")
        == 0,
        "lane candidate selection is not forbidden",
    )

    inputs = manifest.get("inputs")
    require(isinstance(inputs, list) and len(inputs) == 35, "expected 35 inputs")
    require(
        manifest.get("verification_totals")
        == {"inputs": 35, "required_matches": 35},
        "verification totals mismatch",
    )

    roles: set[str] = set()
    paths: set[str] = set()
    json_inputs = 0
    for index, row in enumerate(inputs):
        require(isinstance(row, dict), f"input {index} is not an object")
        role = row.get("role")
        relative = row.get("path")
        require(isinstance(role, str) and role, f"input {index} missing role")
        require(isinstance(relative, str) and relative, f"input {index} missing path")
        require(role not in roles, f"duplicate input role: {role}")
        require(relative.casefold() not in paths, f"duplicate/case-colliding path: {relative}")
        roles.add(role)
        paths.add(relative.casefold())

        target = (ROOT / relative).resolve()
        require(target.is_relative_to(ROOT), f"input escapes repository root: {relative}")
        require(target.is_file(), f"missing input: {relative}")
        canonical, digest = read_lf(target)
        require(
            row.get("canonical_lf_bytes") == len(canonical),
            f"byte count mismatch: {relative}",
        )
        require(
            row.get("canonical_lf_sha256") == digest,
            f"hash mismatch: {relative}",
        )
        if target.suffix.casefold() == ".json":
            load_json(target)
            json_inputs += 1

    output_contracts = manifest.get("output_contracts")
    require(isinstance(output_contracts, dict), "missing output contracts")
    roots: set[str] = set()
    for task in EXPECTED_TASKS:
        contract = output_contracts.get(task, {})
        require(
            contract.get("required_outputs") == EXPECTED_OUTPUTS[task],
            f"output file set mismatch for {task}",
        )
        root = contract.get("write_root")
        require(isinstance(root, str) and root, f"missing write root for {task}")
        require(root.casefold() not in roots, f"colliding write root for {task}")
        roots.add(root.casefold())
        target_root = (ROOT / root).resolve()
        require(target_root.is_relative_to(ROOT), f"write root escapes repository: {root}")
        require(not target_root.exists(), f"write root already exists before dispatch: {root}")

    authority = manifest.get("execution_authority", {})
    forbidden_true = [
        "repository_clone_or_fetch",
        "dataset_download_or_authenticated_access",
        "package_install_or_environment_creation",
        "source_model_or_data_modification",
        "preprocessing_training_evaluation_smoke_or_benchmark",
        "test_access",
        "execute_repository_commands",
        "modify_control_wave_a_through_f_or_other_lanes",
        "select_candidate",
        "authorize_execution",
    ]
    require(
        all(authority.get(key) is False for key in forbidden_true),
        "one or more forbidden authority flags are not false",
    )
    truth = manifest.get("truth_state", {})
    require(truth.get("RESULT_STATUS") == "NOT_RUN", "RESULT_STATUS changed")
    require(truth.get("TEST_SET_OPENED") == "NO", "TEST state changed")
    require(truth.get("ACCEPTED_RESULT_ROWS") == 0, "accepted results changed")
    require(truth.get("execution_authorized") is False, "execution was authorized")
    require(truth.get("confirmed") is False, "packet was confirmed")

    manifest_bytes, manifest_hash = read_lf(MANIFEST)
    print("PASS_R2_EVIDENCE_GATE_35_OF_35_READY_FOR_PARALLEL_DISPATCH")
    print(f"manifest_bytes={len(manifest_bytes)}")
    print(f"manifest_sha256={manifest_hash}")
    print("inputs_verified=35")
    print(f"json_inputs_strict_parsed={json_inputs}")
    print("candidate_rows=7")
    print("tasks=R2-A1,R2-A2,R2-A3")
    print("execution_authorized=false")
    print("test_set_opened=NO")


if __name__ == "__main__":
    try:
        main()
    except (GateFailure, UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
        print(f"FAIL_R2_EVIDENCE_GATE: {exc}")
        raise SystemExit(1)
