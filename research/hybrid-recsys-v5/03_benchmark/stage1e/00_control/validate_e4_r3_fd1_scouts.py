from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
BASE = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p"
SCOUTS = {
    "R3-FD1A": BASE / "E4_R3FD1A_framework_scout",
    "R3-FD1B": BASE / "E4_R3FD1B_benchmark_scout",
    "R3-FD1C": BASE / "E4_R3FD1C_toolkit_scout",
}
EXPECTED_FILES = {"scout_candidates.json", "scout_report.md", "scout_handoff.json"}
MODEL = {
    "display_name": "Sol XHigh Standard",
    "runtime_model_id": "gpt-5.6-sol",
    "reasoning_effort": "xhigh",
    "service_tier": "standard",
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
    seen: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in seen and seen[folded] != key:
            raise ContractError(f"case-colliding JSON keys: {seen[folded]} / {key}")
        seen[folded] = key
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
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def main() -> int:
    contract = load_json(CONTROL / "e4_r3_fd1_scout_contract.json")
    required = set(contract["required_proposal_fields"])
    source_required = set(contract["source_record_fields"])
    allowed_statuses = set(contract["statuses"])
    checks: dict[str, bool] = {}
    failures: list[str] = []
    summaries: dict[str, Any] = {}
    all_proposal_ids: list[str] = []
    all_plausible_ids: list[str] = []

    for stage_id, root in SCOUTS.items():
        files = {path.name for path in root.iterdir() if path.is_file()} if root.is_dir() else set()
        directories = [path.name for path in root.iterdir() if path.is_dir()] if root.is_dir() else []
        check(checks, failures, f"{stage_id}_exact_write_set", files == EXPECTED_FILES and not directories)
        if files != EXPECTED_FILES or directories:
            summaries[stage_id] = {"imported": False}
            continue
        try:
            candidates = load_json(root / "scout_candidates.json")
            handoff = load_json(root / "scout_handoff.json")
            (root / "scout_report.md").read_bytes().decode("utf-8", errors="strict")
        except Exception as exc:
            failures.append(f"{stage_id}_parse_or_utf8:{exc}")
            summaries[stage_id] = {"imported": False}
            continue

        proposals = candidates.get("proposals")
        check(checks, failures, f"{stage_id}_proposals_is_list", isinstance(proposals, list))
        if not isinstance(proposals, list):
            proposals = []
        check(checks, failures, f"{stage_id}_proposal_count_one_to_three", 1 <= len(proposals) <= 3)
        check(checks, failures, f"{stage_id}_declared_count", candidates.get("proposal_count") == len(proposals))
        check(checks, failures, f"{stage_id}_stage_id", candidates.get("stage_id") == stage_id)
        check(checks, failures, f"{stage_id}_model", candidates.get("model_profile") == MODEL)
        check(checks, failures, f"{stage_id}_truth", candidates.get("truth_state") == TRUTH)

        proposal_ids: list[str] = []
        plausible_ids: list[str] = []
        source_count = 0
        rows_ok = True
        for index, proposal in enumerate(proposals):
            if not isinstance(proposal, dict) or not required.issubset(proposal):
                failures.append(f"{stage_id}_proposal_{index}_missing_fields")
                rows_ok = False
                continue
            proposal_id = proposal.get("proposal_id")
            expected_pattern = rf"^{re.escape(stage_id)}-PROP-[0-9]{{3}}$"
            if not isinstance(proposal_id, str) or re.fullmatch(expected_pattern, proposal_id) is None:
                failures.append(f"{stage_id}_proposal_{index}_id_invalid")
                rows_ok = False
            else:
                proposal_ids.append(proposal_id)
            status = proposal.get("scout_status")
            if status not in allowed_statuses:
                failures.append(f"{stage_id}_proposal_{index}_status_invalid")
                rows_ok = False
            elif status == "PLAUSIBLE_COMPLETE_PROPOSAL" and isinstance(proposal_id, str):
                plausible_ids.append(proposal_id)
            if not isinstance(proposal.get("unresolved_fields"), list):
                failures.append(f"{stage_id}_proposal_{index}_unresolved_not_list")
                rows_ok = False
            locator_fields = [field for field in required if field.endswith("_locator")]
            # An excluded row preserves missing locators as null plus an explicit
            # unresolved-field record. Only an admitted plausible proposal must
            # have a syntactically complete HTTPS locator surface.
            if status == "PLAUSIBLE_COMPLETE_PROPOSAL" and not all(
                is_https(proposal.get(field)) for field in locator_fields
            ):
                failures.append(f"{stage_id}_proposal_{index}_locator_invalid")
                rows_ok = False
            target = proposal.get("benchmark_target_summary")
            if not isinstance(target, dict) or not {"dataset_split", "method_config", "metric", "cutoff", "value", "result_locator", "protocol_caveats"}.issubset(target):
                failures.append(f"{stage_id}_proposal_{index}_benchmark_target_invalid")
                rows_ok = False
            inventory = proposal.get("source_inventory")
            if not isinstance(inventory, list) or not inventory:
                failures.append(f"{stage_id}_proposal_{index}_source_inventory_empty")
                rows_ok = False
                continue
            source_count += len(inventory)
            evidence_ids: list[Any] = []
            for source_index, source in enumerate(inventory):
                if not isinstance(source, dict) or not source_required.issubset(source) or not is_https(source.get("url")):
                    failures.append(f"{stage_id}_proposal_{index}_source_{source_index}_invalid")
                    rows_ok = False
                    continue
                evidence_ids.append(source.get("evidence_id"))
            if len(evidence_ids) != len(set(evidence_ids)):
                failures.append(f"{stage_id}_proposal_{index}_duplicate_evidence_id")
                rows_ok = False
        check(checks, failures, f"{stage_id}_proposal_rows", rows_ok)
        check(checks, failures, f"{stage_id}_proposal_ids_unique", len(proposal_ids) == len(set(proposal_ids)) == len(proposals))

        check(checks, failures, f"{stage_id}_handoff_model", handoff.get("model_profile") == MODEL)
        check(checks, failures, f"{stage_id}_handoff_truth", handoff.get("truth_state") == TRUTH)
        check(checks, failures, f"{stage_id}_handoff_ids", handoff.get("proposal_ids") == proposal_ids and handoff.get("plausible_proposal_ids") == plausible_ids)
        check(checks, failures, f"{stage_id}_handoff_no_selection", handoff.get("selection_performed") is False and handoff.get("selected_candidate_id") is None)
        operations = handoff.get("forbidden_operations")
        check(checks, failures, f"{stage_id}_forbidden_operations", isinstance(operations, dict) and bool(operations) and all(value is False for value in operations.values()))

        all_proposal_ids.extend(proposal_ids)
        all_plausible_ids.extend(plausible_ids)
        summaries[stage_id] = {
            "imported": True,
            "proposal_ids": proposal_ids,
            "plausible_proposal_ids": plausible_ids,
            "source_record_count": source_count,
        }

    check(checks, failures, "global_proposal_ids_unique", len(all_proposal_ids) == len(set(all_proposal_ids)))
    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r3-fd1-scouts-validation-result-1.0",
        "passed": passed,
        "verdict": "PASS_R3_FD1_SCOUTS_READY_FOR_CENTRAL_COMPOSITION" if passed else "FAIL_R3_FD1_SCOUT_IMPORT_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "scouts": summaries,
        "total_proposal_count": len(all_proposal_ids),
        "plausible_proposal_count": len(all_plausible_ids),
        "plausible_proposal_ids": all_plausible_ids,
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
