from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e"
CONTROL = BASE / "00_control"
ROW_ID = "E3-LIGHTGCN-GOWALLA-PYTORCH-001"
MODEL_ID = "gpt-5.6-sol"
REASONING = "max"
SERVICE_TIER = "priority"
DISPLAY_NAME = "Sol Max Fast"
STATUS_ENUM = {
    "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW",
    "EVIDENCE_INCOMPLETE",
    "DISPOSITIVE_REJECT",
    "HANDOFF_INCOMPLETE",
}
COMMON_ROW_KEYS = {
    "row_id",
    "method",
    "dataset_scope",
    "lane_id",
    "evidence_status",
    "authoritative_sources",
    "confirmed_fields",
    "unresolved_fields",
    "dispositive_mismatches",
    "inferences_forbidden",
    "recommended_g1_disposition",
    "execution_authorized",
    "result_status",
    "test_set_opened",
}
LANES = {
    "R2-ER1-S": {
        "root": BASE / "rebaseline_v2/wave_m/E4_R2ER1S_schema_normalization",
        "files": {
            "a1_normalized_carrier.json",
            "a2_normalized_carrier.json",
            "a3_normalized_carrier.json",
            "schema_normalization_report.md",
            "er1_s_handoff.json",
        },
        "handoff": "er1_s_handoff.json",
    },
    "R2-ER1-A1": {
        "root": BASE / "rebaseline_v2/wave_n/E4_R2ER1A1_repo_license",
        "files": {
            "lightgcn_repo_license_evidence.json",
            "paper_repo_config_binding.json",
            "repo_license_report.md",
            "er1_a1_handoff.json",
        },
        "handoff": "er1_a1_handoff.json",
        "primary": "lightgcn_repo_license_evidence.json",
    },
    "R2-ER1-A2": {
        "root": BASE / "rebaseline_v2/wave_n/E4_R2ER1A2_dataset_lineage",
        "files": {
            "lightgcn_dataset_lineage_evidence.json",
            "rights_release_matrix.json",
            "processed_split_lineage_map.json",
            "er1_a2_handoff.json",
        },
        "handoff": "er1_a2_handoff.json",
        "primary": "lightgcn_dataset_lineage_evidence.json",
    },
    "R2-ER1-A3": {
        "root": BASE / "rebaseline_v2/wave_n/E4_R2ER1A3_result_evaluator",
        "files": {
            "lightgcn_result_evaluator_evidence.json",
            "center_run_checkpoint_binding.json",
            "metric_evaluator_contract.json",
            "er1_a3_handoff.json",
        },
        "handoff": "er1_a3_handoff.json",
        "primary": "lightgcn_result_evaluator_evidence.json",
    },
}


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"duplicate key: {key}")
        canonical = key.casefold()
        if canonical in folded and folded[canonical] != key:
            raise ContractError(f"case collision: {folded[canonical]} / {key}")
        folded[canonical] = key
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_or_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def recursive_key_values(value: Any, key: str) -> list[Any]:
    return [node[key] for node in walk(value) if isinstance(node, dict) and key in node]


def contains_any_key_value(value: Any, keys: set[str], expected: Any) -> bool:
    return any(
        node.get(key) == expected
        for node in walk(value)
        if isinstance(node, dict)
        for key in keys
        if key in node
    )


def find_rows(value: Any, row_id: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in walk(value):
        if not isinstance(node, dict) or "row_id" not in node:
            continue
        if row_id is not None and node.get("row_id") != row_id:
            continue
        marker = id(node)
        if marker not in seen:
            seen.add(marker)
            rows.append(node)
    return rows


def check(checks: dict[str, bool], failures: list[str], name: str, condition: bool) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def output_hash_record(handoff: dict[str, Any], relative_path: str) -> dict[str, Any] | None:
    for node in walk(handoff):
        if not isinstance(node, dict):
            continue
        candidate = node.get("path")
        if isinstance(candidate, str) and candidate.replace("\\", "/") == relative_path.replace("\\", "/"):
            if "canonical_lf_sha256" in node and "canonical_lf_bytes" in node:
                return node
    return None


def source_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("candidate_rows", "rows"):
        value = document.get(key)
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return value
    return find_rows(document)


def validate_handoff(
    lane_id: str,
    lane_root: Path,
    handoff: dict[str, Any],
    handoff_name: str,
    expected_files: set[str],
    checks: dict[str, bool],
    failures: list[str],
) -> None:
    prefix = lane_id.lower().replace("-", "_")
    check(checks, failures, f"{prefix}_model", contains_any_key_value(handoff, {"actual_model", "runtime_model_id", "model_id", "id"}, MODEL_ID))
    check(checks, failures, f"{prefix}_reasoning", contains_any_key_value(handoff, {"actual_reasoning", "reasoning", "reasoning_effort"}, REASONING))
    check(checks, failures, f"{prefix}_service_tier", contains_any_key_value(handoff, {"actual_service_tier", "service_tier"}, SERVICE_TIER))
    check(checks, failures, f"{prefix}_display_name", contains_any_key_value(handoff, {"actual_display", "display", "display_name", "model_profile"}, DISPLAY_NAME))
    check(checks, failures, f"{prefix}_unverified", contains_any_key_value(handoff, {"verification_status"}, "UNVERIFIED"))
    check(checks, failures, f"{prefix}_no_experiment", contains_any_key_value(handoff, {"status"}, "no_experiments_declared"))

    truth_ok = any(
        isinstance(node, dict)
        and node.get("RESULT_STATUS") == "NOT_RUN"
        and node.get("TEST_SET_OPENED") == "NO"
        and node.get("ACCEPTED_RESULT_ROWS") == 0
        and node.get("execution_authorized") is False
        for node in walk(handoff)
    )
    check(checks, failures, f"{prefix}_truth_state", truth_ok)

    forbidden = recursive_key_values(handoff, "forbidden_operation_flags")
    check(checks, failures, f"{prefix}_forbidden_flags_present", len(forbidden) == 1 and isinstance(forbidden[0], dict))
    if len(forbidden) == 1 and isinstance(forbidden[0], dict):
        check(checks, failures, f"{prefix}_forbidden_flags_false", bool(forbidden[0]) and all(value is False for value in forbidden[0].values()))

    manifest_counts = [
        node
        for node in walk(handoff)
        if isinstance(node, dict)
        and (
            (node.get("expected") == 31 and node.get("matched") == 31)
            or (node.get("expected_inputs") == 31 and node.get("verified_inputs") == 31)
            or (node.get("expected_inputs") == 31 and node.get("matched_inputs") == 31)
            or (
                node.get("manifest_entries_expected") == 31
                and node.get("manifest_entries_present") == 31
                and node.get("manifest_entries_byte_count_matched") == 31
                and node.get("manifest_entries_hash_matched") == 31
            )
        )
    ]
    check(checks, failures, f"{prefix}_input_replay_31_of_31", bool(manifest_counts) or "31/31" in json.dumps(handoff))

    for name in expected_files - {handoff_name}:
        path = lane_root / name
        relative = path.relative_to(ROOT).as_posix()
        record = output_hash_record(handoff, relative)
        check(checks, failures, f"{prefix}_{name}_hash_record", record is not None)
        if record is not None:
            payload = canonical_lf(path)
            check(checks, failures, f"{prefix}_{name}_bytes", record.get("canonical_lf_bytes") == len(payload))
            check(checks, failures, f"{prefix}_{name}_sha256", record.get("canonical_lf_sha256") == hashlib.sha256(payload).hexdigest())


def main() -> int:
    failures: list[str] = []
    checks: dict[str, bool] = {}

    gate = load_json(CONTROL / "rebaseline_v2_e4_r2_er1_gate_receipt.json")
    check(checks, failures, "entry_gate_pass", gate.get("passed") is True and gate.get("verdict") == "PASS_R2_ER1_GATE_31_OF_31_READY_FOR_PARALLEL_DISPATCH")

    loaded: dict[str, dict[str, dict[str, Any]]] = {}
    for lane_id, spec in LANES.items():
        lane_root = spec["root"]
        expected_files = spec["files"]
        prefix = lane_id.lower().replace("-", "_")
        check(checks, failures, f"{prefix}_root_exists", lane_root.is_dir())
        if not lane_root.is_dir():
            continue
        actual_files = {path.name for path in lane_root.iterdir() if path.is_file()}
        check(checks, failures, f"{prefix}_exact_file_set", actual_files == expected_files)
        documents: dict[str, dict[str, Any]] = {}
        for name in sorted(expected_files):
            path = lane_root / name
            if not path.is_file():
                continue
            canonical_lf(path)
            if path.suffix == ".json":
                try:
                    documents[name] = load_json(path)
                except Exception as exc:
                    failures.append(f"{prefix}_strict_json:{name}:{exc}")
        handoff_name = spec["handoff"]
        if handoff_name in documents:
            validate_handoff(lane_id, lane_root, documents[handoff_name], handoff_name, expected_files, checks, failures)
        else:
            failures.append(f"{prefix}_handoff_missing_or_invalid")
        loaded[lane_id] = documents

    expected_order = [
        row["row_id"]
        for row in source_rows(load_json(BASE / "rebaseline_v2/wave_g/E4_R2A1_repo_evidence/repo_evidence_register.json"))
    ]
    original_specs = {
        "a1_normalized_carrier.json": load_json(BASE / "rebaseline_v2/wave_g/E4_R2A1_repo_evidence/repo_evidence_register.json"),
        "a2_normalized_carrier.json": load_json(BASE / "rebaseline_v2/wave_g/E4_R2A2_dataset_evidence/dataset_evidence_register.json"),
        "a3_normalized_carrier.json": load_json(BASE / "rebaseline_v2/wave_g/E4_R2A3_metric_evidence/result_center_register.json"),
    }
    normalized = loaded.get("R2-ER1-S", {})
    for name, original in original_specs.items():
        prefix = name.split("_")[0]
        if name not in normalized:
            failures.append(f"schema_{name}_missing")
            continue
        new_rows = source_rows(normalized[name])
        old_rows = source_rows(original)
        check(checks, failures, f"schema_{prefix}_seven_rows", len(new_rows) == 7)
        check(checks, failures, f"schema_{prefix}_order", [row.get("row_id") for row in new_rows] == expected_order)
        check(checks, failures, f"schema_{prefix}_common_keys", all(COMMON_ROW_KEYS.issubset(row) for row in new_rows))
        old_by_id = {row.get("row_id"): row for row in old_rows}
        preserved = True
        for row in new_rows:
            old = old_by_id.get(row.get("row_id"), {})
            old_status = old.get("evidence_status", old.get("lane_evidence_status"))
            compared = {
                "method": old.get("method"),
                "dataset_scope": old.get("dataset_scope"),
                "evidence_status": old_status,
                "authoritative_sources": old.get("authoritative_sources"),
                "unresolved_fields": old.get("unresolved_fields"),
                "dispositive_mismatches": old.get("dispositive_mismatches"),
                "recommended_g1_disposition": old.get("recommended_g1_disposition"),
            }
            if any(row.get(key) != value for key, value in compared.items()):
                preserved = False
        check(checks, failures, f"schema_{prefix}_scientific_fields_preserved", preserved)

    lane_statuses: dict[str, str | None] = {}
    for lane_id in ("R2-ER1-A1", "R2-ER1-A2", "R2-ER1-A3"):
        spec = LANES[lane_id]
        primary = spec["primary"]
        document = loaded.get(lane_id, {}).get(primary)
        prefix = lane_id.lower().replace("-", "_")
        if document is None:
            failures.append(f"{prefix}_primary_missing")
            lane_statuses[lane_id] = None
            continue
        rows = source_rows(document)
        check(checks, failures, f"{prefix}_one_row", len(rows) == 1)
        if len(rows) != 1:
            lane_statuses[lane_id] = None
            continue
        row = rows[0]
        check(checks, failures, f"{prefix}_row_id", row.get("row_id") == ROW_ID)
        check(checks, failures, f"{prefix}_common_keys", COMMON_ROW_KEYS.issubset(row))
        check(checks, failures, f"{prefix}_lane_id", row.get("lane_id") == lane_id)
        check(checks, failures, f"{prefix}_status_enum", row.get("evidence_status") in STATUS_ENUM)
        check(checks, failures, f"{prefix}_row_truth", row.get("execution_authorized") is False and row.get("result_status") == "NOT_RUN" and row.get("test_set_opened") == "NO")
        sources = row.get("authoritative_sources")
        source_shape = isinstance(sources, list) and all(
            isinstance(source, dict)
            and isinstance(source.get("url"), str)
            and isinstance(source.get("locator"), str)
            and isinstance(source.get("supports"), list)
            and isinstance(source.get("does_not_support"), list)
            for source in sources
        )
        check(checks, failures, f"{prefix}_source_shape", source_shape)
        lane_statuses[lane_id] = row.get("evidence_status")

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r2-er1-lane-validation-result-1.0",
        "passed": passed,
        "verdict": "PASS_R2_ER1_PARALLEL_LANES_READY_FOR_FRESH_G1" if passed else "FAIL_R2_ER1_PARALLEL_LANES_BLOCKED_BEFORE_G1",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "lane_statuses": lane_statuses,
        "model_policy": {
            "display_name": DISPLAY_NAME,
            "runtime_model_id": MODEL_ID,
            "reasoning_effort": REASONING,
            "service_tier": SERVICE_TIER,
        },
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "execution_authorized": False,
            "project_benchmark_numbers": "INVALID_FOR_PAPER",
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
