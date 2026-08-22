from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
OUTPUT = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery"
EXPECTED_FILES = {
    "candidate_bundle_seeds.json",
    "source_search_log.json",
    "excluded_candidate_log.json",
    "fd1_report.md",
    "fd1_handoff.json",
}
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
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


def check(checks: dict[str, bool], failures: list[str], name: str, condition: bool) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def is_https(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def model_is_xhigh_standard(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    model = value.get("runtime_model_id", value.get("model"))
    reasoning = value.get("reasoning_effort", value.get("reasoning"))
    tier = value.get("service_tier")
    display = value.get("display_name", value.get("model_profile"))
    return (
        model == "gpt-5.6-sol"
        and reasoning == "xhigh"
        and tier == "standard"
        and display == "Sol XHigh Standard"
    )


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    if not OUTPUT.is_dir():
        print(json.dumps({"passed": False, "failures": ["output_root_missing"]}, indent=2))
        return 1

    files = {path.name for path in OUTPUT.iterdir() if path.is_file()}
    directories = [path.name for path in OUTPUT.iterdir() if path.is_dir()]
    check(checks, failures, "exact_five_file_write_set", files == EXPECTED_FILES and not directories)

    documents: dict[str, dict[str, Any]] = {}
    for name in sorted(EXPECTED_FILES):
        path = OUTPUT / name
        if not path.is_file():
            failures.append(f"missing:{name}")
            continue
        try:
            path.read_bytes().decode("utf-8", errors="strict")
            if path.suffix == ".json":
                documents[name] = load_json(path)
        except Exception as exc:
            failures.append(f"parse_or_utf8:{name}:{exc}")

    if failures:
        print(json.dumps({
            "schema_version": "stage1e-rebaseline-v2-e4-r3-fd1-validation-result-1.0",
            "passed": False,
            "verdict": "FAIL_R3_FD1_IMPORT_BLOCKED",
            "failure_count": len(failures),
            "failures": failures,
            "checks": checks,
        }, indent=2, ensure_ascii=False))
        return 1

    contract = load_json(CONTROL / "e4_r3_candidate_bundle_contract.json")
    seeds_doc = documents["candidate_bundle_seeds.json"]
    candidates = seeds_doc.get("candidates")
    check(checks, failures, "candidates_is_list", isinstance(candidates, list))
    if not isinstance(candidates, list):
        candidates = []
    check(checks, failures, "candidate_count_three_to_five", 3 <= len(candidates) <= 5)
    declared_count = seeds_doc.get("candidate_count", seeds_doc.get("seed_count"))
    check(checks, failures, "declared_candidate_count_matches", declared_count == len(candidates))

    id_pattern = re.compile(contract["candidate_id_pattern"])
    required = set(contract["required_seed_fields"])
    source_required = set(contract["source_record_fields"])
    old_registry = load_json(CONTROL / "e4_r3_supersession_registry.json")
    old_ids = {row.get("row_id") for row in old_registry.get("rows", []) if isinstance(row, dict)}
    ids: list[str] = []
    all_required = True
    all_https = True
    all_sources_valid = True
    all_seed_status = True
    locator_fields = [
        "repository_locator",
        "immutable_revision_locator",
        "repository_license_locator",
        "reference_paper_locator",
        "dataset_provider_locator",
        "dataset_terms_locator",
        "preprocessing_split_locator",
        "training_entrypoint_locator",
        "configuration_locator",
        "evaluator_locator",
        "benchmark_target_locator",
    ]
    source_count = 0
    for index, row in enumerate(candidates):
        if not isinstance(row, dict):
            failures.append(f"candidate_{index}_not_object")
            all_required = False
            continue
        row_id = row.get("candidate_id")
        if not isinstance(row_id, str) or id_pattern.fullmatch(row_id) is None:
            failures.append(f"candidate_{index}_id_invalid")
        else:
            ids.append(row_id)
        missing = sorted(required - set(row))
        if missing:
            failures.append(f"candidate_{index}_missing_fields:{','.join(missing)}")
            all_required = False
        if row.get("bundle_label") != "FRAMEWORK_REPRODUCTION_REFERENCE" or row.get("fd1_status") != "PLAUSIBLE_COMPLETE_SEED":
            all_seed_status = False
        if not all(is_https(row.get(field)) for field in locator_fields):
            all_https = False
        unresolved = row.get("unresolved_fields")
        if not isinstance(unresolved, list):
            failures.append(f"candidate_{index}_unresolved_fields_not_list")
            all_required = False
        inventory = row.get("source_inventory")
        if not isinstance(inventory, list) or not inventory:
            failures.append(f"candidate_{index}_source_inventory_empty")
            all_sources_valid = False
            continue
        source_count += len(inventory)
        evidence_ids: list[str] = []
        for source_index, source in enumerate(inventory):
            if not isinstance(source, dict) or not source_required.issubset(source):
                failures.append(f"candidate_{index}_source_{source_index}_invalid_fields")
                all_sources_valid = False
                continue
            if not is_https(source.get("url")):
                failures.append(f"candidate_{index}_source_{source_index}_url_invalid")
                all_sources_valid = False
            evidence_ids.append(source.get("evidence_id"))
        if len(evidence_ids) != len(set(evidence_ids)):
            failures.append(f"candidate_{index}_duplicate_evidence_id")
            all_sources_valid = False

    check(checks, failures, "candidate_ids_unique", len(ids) == len(candidates) == len(set(ids)))
    check(checks, failures, "candidate_ids_do_not_reuse_old_rows", set(ids).isdisjoint(old_ids))
    check(checks, failures, "all_required_seed_fields_present", all_required)
    check(checks, failures, "all_seed_rows_have_closed_label_and_status", all_seed_status)
    check(checks, failures, "all_primary_locators_are_https", all_https)
    check(checks, failures, "source_inventories_structurally_valid", all_sources_valid)

    handoff = documents["fd1_handoff.json"]
    handoff_ids = handoff.get("candidate_ids")
    if handoff_ids is None and isinstance(handoff.get("candidate_summary"), dict):
        handoff_ids = handoff["candidate_summary"].get("candidate_ids")
    check(checks, failures, "handoff_candidate_ids_exact", isinstance(handoff_ids, list) and set(handoff_ids) == set(ids) and len(handoff_ids) == len(ids))
    check(checks, failures, "handoff_model_xhigh_standard", model_is_xhigh_standard(handoff.get("model_profile", handoff.get("runtime_model_profile"))))
    check(checks, failures, "seeds_model_xhigh_standard", model_is_xhigh_standard(seeds_doc.get("model_profile", seeds_doc.get("runtime_model_profile"))))
    check(checks, failures, "handoff_truth_state", handoff.get("truth_state") == TRUTH)
    check(checks, failures, "seeds_truth_state", seeds_doc.get("truth_state") == TRUTH)

    forbidden = handoff.get("forbidden_operations", handoff.get("operation_assertions"))
    if isinstance(forbidden, dict):
        forbidden_ok = all(value is False for value in forbidden.values())
    elif isinstance(forbidden, list):
        forbidden_ok = bool(forbidden) and all(isinstance(row, dict) and row.get("performed") is False for row in forbidden)
    else:
        forbidden_ok = False
    check(checks, failures, "forbidden_operations_not_performed", forbidden_ok)

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r3-fd1-validation-result-1.0",
        "passed": passed,
        "verdict": "PASS_R3_FD1_SEEDS_READY_FOR_FREEZE_AND_PARALLEL_VERIFICATION" if passed else "FAIL_R3_FD1_IMPORT_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "candidate_count": len(candidates),
        "candidate_ids": ids,
        "source_record_count": source_count,
        "exact_output_files": sorted(EXPECTED_FILES),
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
