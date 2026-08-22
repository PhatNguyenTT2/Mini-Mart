from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
CONTRACT = CONTROL / "e4_r4_strict_admission_contract.json"
EXPECTED_FILES = {
    "scout_candidates.json",
    "source_replay_log.json",
    "excluded_candidate_log.json",
    "scout_report.md",
    "scout_handoff.json",
}
LANES = {
    "R4-D1A": ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_u/E4_R4D1A_artifact_package_scout",
    "R4-D1B": ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_v/E4_R4D1B_benchmark_suite_scout",
    "R4-D1C": ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_w/E4_R4D1C_framework_packet_scout",
}
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
CONTRACT_BINDING = {
    "path": (
        "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
        "e4_r4_strict_admission_contract.json"
    ),
    "canonical_lf_sha256": (
        "19006183b216f9b5b7f83dd39d9b5e6256ff0f70b5b285f9f521b526fb623816"
    ),
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


def direct_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


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
    contract = load_json(CONTRACT)
    required_proposal = set(contract["required_proposal_fields"])
    required_source = set(contract["required_source_fields"])
    identity_fields = set(contract["identity_tuple_fields"])
    dimensions = {
        row["id"] for row in contract["mandatory_dimensions"]
    }
    dimension_statuses = set(
        contract["closed_status_sets"]["dimension"]
    )
    proposal_statuses = set(contract["closed_status_sets"]["proposal"])
    source_statuses = set(contract["closed_status_sets"]["source_access"])
    proposal_pattern = re.compile(contract["proposal_id_pattern"])

    aggregate = {
        "admitted": 0,
        "excluded": 0,
        "examined": 0,
        "sources": 0,
    }
    lane_summary: dict[str, Any] = {}

    for lane, root in LANES.items():
        prefix = lane.lower().replace("-", "_")
        check(
            checks,
            failures,
            f"{prefix}_root_exists",
            root.is_dir(),
        )
        if not root.is_dir():
            continue
        actual_files = {
            path.name for path in root.iterdir() if path.is_file()
        }
        actual_dirs = [
            path.name for path in root.iterdir() if path.is_dir()
        ]
        check(
            checks,
            failures,
            f"{prefix}_exact_five_files",
            actual_files == EXPECTED_FILES and not actual_dirs,
        )
        if actual_files != EXPECTED_FILES:
            continue

        try:
            candidates = load_json(root / "scout_candidates.json")
            sources = load_json(root / "source_replay_log.json")
            excluded = load_json(root / "excluded_candidate_log.json")
            handoff = load_json(root / "scout_handoff.json")
            report = (root / "scout_report.md").read_text(encoding="utf-8")
        except Exception as exc:
            failures.append(f"{prefix}_parse:{exc}")
            continue

        payloads = (candidates, sources, excluded, handoff)
        check(
            checks,
            failures,
            f"{prefix}_stage_ids",
            all(payload.get("stage_id") == lane for payload in payloads),
        )
        check(
            checks,
            failures,
            f"{prefix}_truth_state",
            all(payload.get("truth_state") == TRUTH for payload in payloads),
        )
        check(
            checks,
            failures,
            f"{prefix}_worker_model",
            candidates.get("model_profile") == MODEL
            and handoff.get("model_profile") == MODEL,
        )
        check(
            checks,
            failures,
            f"{prefix}_contract_binding",
            candidates.get("admission_contract_binding")
            == CONTRACT_BINDING,
        )

        source_rows = sources.get("source_records")
        if not isinstance(source_rows, list):
            failures.append(f"{prefix}_source_records_not_list")
            source_rows = []
        source_ids: list[Any] = []
        source_urls: list[Any] = []
        source_by_id: dict[str, dict[str, Any]] = {}
        source_rows_valid = True
        for index, row in enumerate(source_rows):
            if not isinstance(row, dict):
                failures.append(f"{prefix}_source_{index}_not_object")
                source_rows_valid = False
                continue
            if set(row) != required_source:
                failures.append(f"{prefix}_source_{index}_field_set")
                source_rows_valid = False
            evidence_id = row.get("evidence_id")
            source_ids.append(evidence_id)
            source_urls.append(row.get("url"))
            if isinstance(evidence_id, str):
                source_by_id[evidence_id] = row
            if not direct_url(row.get("url")):
                failures.append(f"{prefix}_source_{index}_not_direct_url")
                source_rows_valid = False
            if row.get("access_status") not in source_statuses:
                failures.append(f"{prefix}_source_{index}_access_status")
                source_rows_valid = False
            if row.get("retrieved_at") != "2026-08-22":
                failures.append(f"{prefix}_source_{index}_retrieved_at")
                source_rows_valid = False
            for field in (
                "evidence_id",
                "authority_type",
                "claim_scope",
                "evidence_note",
            ):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    failures.append(
                        f"{prefix}_source_{index}_{field}_empty"
                    )
                    source_rows_valid = False
        check(
            checks,
            failures,
            f"{prefix}_source_rows_schema",
            source_rows_valid,
        )
        check(
            checks,
            failures,
            f"{prefix}_source_ids_unique",
            len(source_ids) == len(set(source_ids)),
        )
        check(
            checks,
            failures,
            f"{prefix}_source_urls_deduplicated",
            len(source_urls) == len(set(source_urls)),
        )

        admitted = candidates.get("admitted_candidates")
        if not isinstance(admitted, list):
            failures.append(f"{prefix}_admitted_not_list")
            admitted = []
        admitted_ids: list[Any] = []
        admitted_valid = True
        for index, row in enumerate(admitted):
            if not isinstance(row, dict):
                failures.append(f"{prefix}_admitted_{index}_not_object")
                admitted_valid = False
                continue
            if not required_proposal.issubset(row):
                failures.append(f"{prefix}_admitted_{index}_missing_fields")
                admitted_valid = False
            proposal_id = row.get("proposal_id")
            admitted_ids.append(proposal_id)
            if (
                not isinstance(proposal_id, str)
                or proposal_pattern.fullmatch(proposal_id) is None
                or not proposal_id.startswith(lane + "-PROP-")
            ):
                failures.append(f"{prefix}_admitted_{index}_id")
                admitted_valid = False
            if (
                row.get("proposal_status")
                != "ADMIT_COMPLETE_BUNDLE_FOR_INDEPENDENT_AUDIT"
            ):
                failures.append(f"{prefix}_admitted_{index}_status")
                admitted_valid = False
            if not re.fullmatch(
                r"[0-9a-fA-F]{40,64}", str(row.get("full_revision", ""))
            ):
                failures.append(f"{prefix}_admitted_{index}_revision")
                admitted_valid = False
            identity = row.get("identity_tuple")
            if not isinstance(identity, dict) or set(identity) != identity_fields:
                failures.append(f"{prefix}_admitted_{index}_identity_fields")
                admitted_valid = False
            elif any(identity.get(field) != row.get(field) for field in identity_fields):
                failures.append(f"{prefix}_admitted_{index}_identity_values")
                admitted_valid = False
            matrix = row.get("admission_matrix")
            if not isinstance(matrix, list):
                matrix = []
            matrix_ids = [
                item.get("dimension_id")
                for item in matrix
                if isinstance(item, dict)
            ]
            matrix_valid = (
                len(matrix) == 12
                and len(matrix_ids) == 12
                and set(matrix_ids) == dimensions
            )
            for item in matrix:
                if (
                    not isinstance(item, dict)
                    or set(item)
                    != {
                        "dimension_id",
                        "status",
                        "evidence_ids",
                        "rationale",
                    }
                    or item.get("status") != "PASS_PRIMARY_REPLAYED"
                    or not isinstance(item.get("evidence_ids"), list)
                    or not item.get("evidence_ids")
                    or not set(item.get("evidence_ids", [])).issubset(
                        source_by_id
                    )
                    or not isinstance(item.get("rationale"), str)
                    or not item.get("rationale", "").strip()
                ):
                    matrix_valid = False
            if not matrix_valid:
                failures.append(f"{prefix}_admitted_{index}_matrix")
                admitted_valid = False
            decision_ids = row.get("decision_bearing_sources")
            if (
                not isinstance(decision_ids, list)
                or not decision_ids
                or not set(decision_ids).issubset(source_by_id)
                or any(
                    source_by_id[evidence_id].get("access_status")
                    not in {"REPLAYED_PRIMARY", "REPLAYED_AUTHORITATIVE"}
                    for evidence_id in decision_ids
                    if evidence_id in source_by_id
                )
            ):
                failures.append(
                    f"{prefix}_admitted_{index}_decision_sources"
                )
                admitted_valid = False
            if row.get("unresolved_mandatory_fields") != []:
                failures.append(f"{prefix}_admitted_{index}_unresolved")
                admitted_valid = False
            if row.get("dispositive_conflicts") != []:
                failures.append(f"{prefix}_admitted_{index}_conflicts")
                admitted_valid = False
        check(
            checks,
            failures,
            f"{prefix}_admitted_strict_gate",
            admitted_valid,
        )
        check(
            checks,
            failures,
            f"{prefix}_admitted_ids_unique",
            len(admitted_ids) == len(set(admitted_ids)),
        )

        excluded_rows = excluded.get("excluded_candidates")
        if not isinstance(excluded_rows, list):
            failures.append(f"{prefix}_excluded_not_list")
            excluded_rows = []
        excluded_ids: list[Any] = []
        excluded_valid = True
        required_excluded = {
            "proposal_id",
            "identity_summary",
            "failed_dimension_ids",
            "dispositive_conflicts",
            "unresolved_mandatory_fields",
            "evidence_ids",
            "exclusion_status",
            "reason",
        }
        for index, row in enumerate(excluded_rows):
            if not isinstance(row, dict):
                excluded_valid = False
                failures.append(f"{prefix}_excluded_{index}_not_object")
                continue
            if not required_excluded.issubset(row):
                excluded_valid = False
                failures.append(f"{prefix}_excluded_{index}_missing_fields")
            proposal_id = row.get("proposal_id")
            excluded_ids.append(proposal_id)
            if (
                not isinstance(proposal_id, str)
                or proposal_pattern.fullmatch(proposal_id) is None
                or not proposal_id.startswith(lane + "-PROP-")
            ):
                excluded_valid = False
                failures.append(f"{prefix}_excluded_{index}_id")
            if row.get("exclusion_status") not in {
                "EXCLUDE_INCOMPLETE_BUNDLE",
                "DISPOSITIVE_REJECT",
            }:
                excluded_valid = False
                failures.append(f"{prefix}_excluded_{index}_status")
            failed_dimensions = row.get("failed_dimension_ids")
            if (
                not isinstance(failed_dimensions, list)
                or not failed_dimensions
                or not set(failed_dimensions).issubset(dimensions)
            ):
                excluded_valid = False
                failures.append(f"{prefix}_excluded_{index}_dimensions")
            evidence_ids = row.get("evidence_ids")
            if (
                not isinstance(evidence_ids, list)
                or not set(evidence_ids).issubset(source_by_id)
            ):
                excluded_valid = False
                failures.append(f"{prefix}_excluded_{index}_evidence")
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                excluded_valid = False
                failures.append(f"{prefix}_excluded_{index}_reason")
        check(
            checks,
            failures,
            f"{prefix}_excluded_schema",
            excluded_valid,
        )
        check(
            checks,
            failures,
            f"{prefix}_excluded_ids_unique",
            len(excluded_ids) == len(set(excluded_ids)),
        )
        check(
            checks,
            failures,
            f"{prefix}_proposal_ids_disjoint",
            not (set(admitted_ids) & set(excluded_ids)),
        )

        admitted_count = len(admitted)
        excluded_count = len(excluded_rows)
        examined_count = admitted_count + excluded_count
        check(
            checks,
            failures,
            f"{prefix}_candidate_counts",
            candidates.get("proposals_admitted_count") == admitted_count
            and candidates.get("proposals_examined_count") == examined_count,
        )
        check(
            checks,
            failures,
            f"{prefix}_excluded_counts",
            excluded.get("excluded_count") == excluded_count
            and excluded.get("screened_leads_count") == examined_count,
        )
        handoff_counts = handoff.get("counts", {})
        check(
            checks,
            failures,
            f"{prefix}_handoff_counts_and_ids",
            handoff_counts.get("examined") == examined_count
            and handoff_counts.get("admitted") == admitted_count
            and handoff_counts.get("excluded") == excluded_count
            and handoff_counts.get("source_records") == len(source_rows)
            and handoff.get("admitted_proposal_ids") == admitted_ids
            and handoff.get("excluded_proposal_ids") == excluded_ids,
        )
        check(
            checks,
            failures,
            f"{prefix}_handoff_exact_files",
            set(handoff.get("exact_filenames", [])) == EXPECTED_FILES
            and len(handoff.get("exact_filenames", [])) == 5,
        )
        check(
            checks,
            failures,
            f"{prefix}_handoff_next_gate",
            handoff.get("next_gate")
            == "R4_D1_CENTRAL_SCHEMA_HASH_VALIDATION",
        )
        forbidden = handoff.get("forbidden_operation_receipts", {})
        check(
            checks,
            failures,
            f"{prefix}_forbidden_operations_preserved",
            isinstance(forbidden, dict)
            and forbidden
            and all(value is False for value in forbidden.values()),
        )
        check(
            checks,
            failures,
            f"{prefix}_report_nontrivial",
            len(report.strip()) >= 500
            and lane in report
            and "12" in report,
        )

        aggregate["admitted"] += admitted_count
        aggregate["excluded"] += excluded_count
        aggregate["examined"] += examined_count
        aggregate["sources"] += len(source_rows)
        lane_summary[lane] = {
            "examined": examined_count,
            "admitted": admitted_count,
            "excluded": excluded_count,
            "source_records": len(source_rows),
        }

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r4-d1-validation-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R4_D1_SCOUTS_READY_FOR_CENTRAL_HASH_FREEZE"
            if passed
            else "FAIL_R4_D1_SCOUTS_BLOCKED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "lane_summary": lane_summary,
        "aggregate": aggregate,
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
