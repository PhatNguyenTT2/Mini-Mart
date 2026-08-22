from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
FD1_ROOT = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery"
BASE = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2"
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
MODEL = {
    "display_name": "Sol XHigh Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "xhigh",
    "service_tier": "standard",
}
LANES = {
    "fd2": {
        "root": BASE / "wave_q/E4_R3FD2_rights_lineage_verification",
        "handoff": "fd2_handoff.json",
    },
    "fd3": {
        "root": BASE / "wave_r/E4_R3FD3_benchmark_evaluator_verification",
        "handoff": "fd3_handoff.json",
    },
    "fd4": {
        "root": BASE / "wave_s/E4_R3FD4_v5_compatibility_stress_test",
        "handoff": "fd4_handoff.json",
    },
}


class ContractError(ValueError):
    pass


def reject_duplicate_or_case_colliding_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded_seen: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in folded_seen and folded_seen[folded] != key:
            raise ContractError(f"case-colliding JSON keys: {folded_seen[folded]} / {key}")
        folded_seen[folded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    value = json.loads(raw, object_pairs_hook=reject_duplicate_or_case_colliding_keys)
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def model_matches(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return all(value.get(key) == expected for key, expected in MODEL.items())


def is_https(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def check(checks: dict[str, bool], failures: list[str], name: str, condition: bool) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    contract = load_json(CONTROL / "e4_r3_verification_lane_contract.json")
    seeds = load_json(FD1_ROOT / "candidate_bundle_seeds.json")
    seed_rows = seeds.get("candidates", [])
    seed_ids = [row.get("candidate_id") for row in seed_rows if isinstance(row, dict)]
    seed_path = "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery/candidate_bundle_seeds.json"
    seed_bytes = canonical_lf(FD1_ROOT / "candidate_bundle_seeds.json")
    seed_binding = {
        "path": seed_path,
        "canonical_lf_bytes": len(seed_bytes),
        "canonical_lf_sha256": hashlib.sha256(seed_bytes).hexdigest(),
    }
    check(checks, failures, "seed_candidate_count_three_to_five", 3 <= len(seed_ids) <= 5)
    check(checks, failures, "seed_candidate_ids_unique", len(seed_ids) == len(set(seed_ids)))

    source_fields = set(contract["source_record_fields"])
    common_fields = set(contract["common_top_level_fields"])
    common_row_fields = set(contract["common_row_fields"])
    lane_results: dict[str, Any] = {}

    for lane_id, runtime in LANES.items():
        specification = contract[lane_id]
        root = runtime["root"]
        expected_files = set(specification["exact_files"])
        actual_files = {path.name for path in root.iterdir() if path.is_file()} if root.is_dir() else set()
        directories = [path.name for path in root.iterdir() if path.is_dir()] if root.is_dir() else []
        check(checks, failures, f"{lane_id}_exact_write_set", actual_files == expected_files and not directories)
        if actual_files != expected_files or directories:
            lane_results[lane_id] = {"imported": False}
            continue

        parsed: dict[str, dict[str, Any]] = {}
        for name in expected_files:
            path = root / name
            try:
                path.read_bytes().decode("utf-8", errors="strict")
                if path.suffix == ".json":
                    parsed[name] = load_json(path)
            except Exception as exc:
                failures.append(f"{lane_id}_parse_or_utf8:{name}:{exc}")

        data = parsed.get(specification["data_file"], {})
        handoff = parsed.get(runtime["handoff"], {})
        check(checks, failures, f"{lane_id}_common_top_fields", common_fields.issubset(data))
        check(checks, failures, f"{lane_id}_stage_id", data.get("stage_id") == specification["stage_id"])
        check(checks, failures, f"{lane_id}_model_profile", model_matches(data.get("model_profile")))
        check(checks, failures, f"{lane_id}_truth_state", data.get("truth_state") == TRUTH)
        check(checks, failures, f"{lane_id}_seed_binding", data.get("seed_manifest_binding") == seed_binding)
        check(checks, failures, f"{lane_id}_candidate_count", data.get("candidate_count") == len(seed_ids))
        check(checks, failures, f"{lane_id}_candidate_ids_exact_order", data.get("candidate_ids") == seed_ids)

        rows = data.get("rows")
        check(checks, failures, f"{lane_id}_rows_is_list", isinstance(rows, list))
        if not isinstance(rows, list):
            rows = []
        row_ids = [row.get("candidate_id") for row in rows if isinstance(row, dict)]
        check(checks, failures, f"{lane_id}_rows_exact_seed_set", len(rows) == len(seed_ids) and row_ids == seed_ids)
        allowed_status = set(specification["statuses"])
        required_row = common_row_fields | set(specification["row_fields"])
        row_shape_ok = True
        sources_ok = True
        statuses: dict[str, str] = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not required_row.issubset(row):
                failures.append(f"{lane_id}_row_{index}_missing_fields")
                row_shape_ok = False
                continue
            if row.get("status") not in allowed_status:
                failures.append(f"{lane_id}_row_{index}_status_invalid")
                row_shape_ok = False
            if not isinstance(row.get("unresolved_fields"), list):
                failures.append(f"{lane_id}_row_{index}_unresolved_not_list")
                row_shape_ok = False
            statuses[str(row.get("candidate_id"))] = str(row.get("status"))
            sources = row.get("decision_bearing_sources")
            if not isinstance(sources, list) or not sources:
                failures.append(f"{lane_id}_row_{index}_sources_empty")
                sources_ok = False
                continue
            evidence_ids: list[Any] = []
            for source_index, source in enumerate(sources):
                if not isinstance(source, dict) or not source_fields.issubset(source) or not is_https(source.get("url")):
                    failures.append(f"{lane_id}_row_{index}_source_{source_index}_invalid")
                    sources_ok = False
                    continue
                evidence_ids.append(source.get("evidence_id"))
            if len(evidence_ids) != len(set(evidence_ids)):
                failures.append(f"{lane_id}_row_{index}_duplicate_evidence_id")
                sources_ok = False
        check(checks, failures, f"{lane_id}_row_shapes", row_shape_ok)
        check(checks, failures, f"{lane_id}_source_records", sources_ok)

        check(checks, failures, f"{lane_id}_handoff_model", model_matches(handoff.get("model_profile")))
        check(checks, failures, f"{lane_id}_handoff_truth", handoff.get("truth_state") == TRUTH)
        check(checks, failures, f"{lane_id}_handoff_candidate_ids", handoff.get("candidate_ids") == seed_ids)
        operations = handoff.get("forbidden_operations")
        check(checks, failures, f"{lane_id}_forbidden_operations", isinstance(operations, dict) and bool(operations) and all(value is False for value in operations.values()))
        check(checks, failures, f"{lane_id}_no_selection", handoff.get("selected_candidate_id") is None and handoff.get("selection_performed") is False)
        lane_results[lane_id] = {
            "imported": True,
            "candidate_count": len(rows),
            "statuses": statuses,
        }

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r3-verification-lanes-validation-result-1.0",
        "passed": passed,
        "verdict": "PASS_R3_FD2_FD4_READY_FOR_CENTRAL_G1_FREEZE" if passed else "FAIL_R3_FD2_FD4_IMPORT_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "seed_binding": seed_binding,
        "candidate_ids": seed_ids,
        "lane_results": lane_results,
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
