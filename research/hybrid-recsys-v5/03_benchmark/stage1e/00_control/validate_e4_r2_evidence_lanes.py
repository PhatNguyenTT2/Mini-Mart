"""Central fail-closed validator for Stage 1E R2-A1/A2/A3 evidence lanes."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parents[4]
WAVE_G = CONTROL.parent / "rebaseline_v2" / "wave_g"

CANDIDATES = [
    "E3-LIGHTGCN-GOWALLA-PYTORCH-001",
    "E3-SIMGCL-YELP2018-QREC-001",
    "E3-XSIMGCL-YELP2018-SELFREC-001",
    "E3-LIGHTGCL-YELP-UPDATED-001",
    "E3-UNISREC-SCIENTIFIC-TRANS-001",
    "E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001",
    "E3-ALPHAREC-MOVIES-TV-001",
]

LANES = {
    "R2-A1": {
        "root": WAVE_G / "E4_R2A1_repo_evidence",
        "files": {
            "repo_evidence_register.json",
            "paper_repo_config_binding.json",
            "source_license_decisions.md",
            "a1_handoff.json",
        },
        "handoff": "a1_handoff.json",
        "handoff_sha256": "1b181e2162054d95c45bf9f3f04065093de440a760b70d2806b1030884d9635c",
        "register": "repo_evidence_register.json",
        "rows_key": "candidate_rows",
        "status_key": "evidence_status",
        "expected_counts": {
            "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW": 0,
            "EVIDENCE_INCOMPLETE": 6,
            "DISPOSITIVE_REJECT": 1,
        },
    },
    "R2-A2": {
        "root": WAVE_G / "E4_R2A2_dataset_evidence",
        "files": {
            "dataset_evidence_register.json",
            "provider_release_rights_matrix.json",
            "lineage_requirement_map.json",
            "a2_handoff.json",
        },
        "handoff": "a2_handoff.json",
        "handoff_sha256": "f4cbfa3c393ec8b52381165f52767b4d5c5defee9e275ae8c1510da6528206ff",
        "register": "dataset_evidence_register.json",
        "rows_key": "candidate_rows",
        "status_key": "lane_evidence_status",
        "expected_counts": {
            "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW": 0,
            "EVIDENCE_INCOMPLETE": 7,
            "DISPOSITIVE_REJECT": 0,
        },
    },
    "R2-A3": {
        "root": WAVE_G / "E4_R2A3_metric_evidence",
        "files": {
            "result_center_register.json",
            "center_config_seed_checkpoint_binding.json",
            "metric_evaluator_contracts.json",
            "a3_handoff.json",
        },
        "handoff": "a3_handoff.json",
        "handoff_sha256": "1ad305a3418d025b8a4fc5a1d148fdea2770d5ee6e32e68f50388112e39f8c40",
        "register": "result_center_register.json",
        "rows_key": "rows",
        "status_key": "evidence_status",
        "expected_counts": {
            "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW": 0,
            "EVIDENCE_INCOMPLETE": 7,
            "DISPOSITIVE_REJECT": 0,
        },
    },
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


def reject_duplicate_or_case_colliding_keys(
    pairs: Iterable[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    seen: dict[str, str] = {}
    for key, value in pairs:
        folded = key.casefold()
        if folded in seen:
            raise ValueError(
                f"duplicate/case-colliding JSON keys: {seen[folded]!r} and {key!r}"
            )
        seen[folded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_or_case_colliding_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"root JSON value is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def digest(path: Path) -> dict[str, object]:
    data = canonical_lf(path)
    return {
        "canonical_lf_bytes": len(data),
        "canonical_lf_sha256": hashlib.sha256(data).hexdigest(),
    }


def actual_model_and_reasoning(handoff: dict[str, object]) -> tuple[object, object]:
    actual_model = handoff.get("actual_model")
    if isinstance(actual_model, dict):
        model = actual_model.get("id")
        reasoning = actual_model.get("reasoning_effort")
    else:
        model = actual_model
        reasoning = handoff.get("actual_reasoning")
    passport = handoff.get("material_passport")
    repro = passport.get("repro_lock") if isinstance(passport, dict) else None
    repro_model = repro.get("model") if isinstance(repro, dict) else None
    if reasoning is None and isinstance(repro_model, dict):
        reasoning = repro_model.get("reasoning")
    return model, reasoning


def closed_truth_state(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("RESULT_STATUS") == "NOT_RUN"
        and value.get("TEST_SET_OPENED") == "NO"
        and value.get("ACCEPTED_RESULT_ROWS") == 0
        and value.get("execution_authorized") is False
    )


def main() -> int:
    hard_failures: list[str] = []
    contract_findings: list[dict[str, object]] = []
    lane_results: dict[str, object] = {}
    row_statuses: dict[str, dict[str, str]] = {row_id: {} for row_id in CANDIDATES}
    parsed_json_documents = 0

    for lane_id, cfg in LANES.items():
        lane_root = cfg["root"]
        assert isinstance(lane_root, Path)
        expected_files = cfg["files"]
        assert isinstance(expected_files, set)
        present_files = (
            {path.name for path in lane_root.iterdir() if path.is_file()}
            if lane_root.is_dir()
            else set()
        )
        if present_files != expected_files:
            hard_failures.append(f"{lane_id}:exact_four_file_set")
            continue

        loaded: dict[str, dict[str, object]] = {}
        try:
            for name in sorted(expected_files):
                path = lane_root / name
                canonical_lf(path)
                if name.endswith(".json"):
                    loaded[name] = load_json(path)
                    parsed_json_documents += 1
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            hard_failures.append(f"{lane_id}:strict_parse:{exc}")
            continue

        handoff_name = str(cfg["handoff"])
        register_name = str(cfg["register"])
        handoff = loaded[handoff_name]
        register = loaded[register_name]

        handoff_digest = digest(lane_root / handoff_name)
        if handoff_digest["canonical_lf_sha256"] != cfg["handoff_sha256"]:
            hard_failures.append(f"{lane_id}:handoff_hash")

        output_rows = handoff.get("outputs")
        output_index = {
            Path(str(row.get("path", ""))).name: row
            for row in output_rows
            if isinstance(output_rows, list) and isinstance(row, dict)
        } if isinstance(output_rows, list) else {}
        expected_non_handoff = expected_files - {handoff_name}
        output_checks: dict[str, object] = {}
        if set(output_index) != expected_non_handoff:
            hard_failures.append(f"{lane_id}:handoff_output_index")
        for name in sorted(expected_non_handoff):
            observed = digest(lane_root / name)
            declared = output_index.get(name)
            passed = (
                isinstance(declared, dict)
                and declared.get("canonical_lf_bytes") == observed["canonical_lf_bytes"]
                and declared.get("canonical_lf_sha256") == observed["canonical_lf_sha256"]
            )
            if not passed:
                hard_failures.append(f"{lane_id}:output_hash:{name}")
            output_checks[name] = {"passed": passed, **observed}

        passport = handoff.get("material_passport")
        repro = passport.get("repro_lock") if isinstance(passport, dict) else None
        declaration = (
            passport.get("experiment_intake_declaration")
            if isinstance(passport, dict)
            else None
        )
        model, reasoning = actual_model_and_reasoning(handoff)
        if not (
            isinstance(passport, dict)
            and passport.get("verification_status") == "UNVERIFIED"
            and isinstance(passport.get("version_label"), str)
            and bool(passport.get("version_label"))
            and isinstance(repro, dict)
            and isinstance(declaration, dict)
            and declaration.get("status") == "no_experiments_declared"
            and model == "gpt-5.6-sol"
            and reasoning == "xhigh"
        ):
            hard_failures.append(f"{lane_id}:passport_model_or_declaration")
        if handoff.get("verdict", handoff.get("lane_verdict")) != "COMPLETE_FAIL_CLOSED_READY_FOR_CENTRAL_G1":
            hard_failures.append(f"{lane_id}:lane_verdict")
        if not closed_truth_state(handoff.get("truth_state")):
            hard_failures.append(f"{lane_id}:truth_state")

        rows = register.get(str(cfg["rows_key"]))
        if not isinstance(rows, list) or [row.get("row_id") for row in rows if isinstance(row, dict)] != CANDIDATES:
            hard_failures.append(f"{lane_id}:candidate_order")
            continue
        status_key = str(cfg["status_key"])
        counts: Counter[str] = Counter()
        for row in rows:
            if not isinstance(row, dict):
                hard_failures.append(f"{lane_id}:non_object_row")
                continue
            status = row.get(status_key)
            if not isinstance(status, str):
                hard_failures.append(f"{lane_id}:{row.get('row_id')}:missing_status")
                continue
            counts[status] += 1
            row_statuses[str(row["row_id"])][lane_id] = status
            if lane_id in {"R2-A1", "R2-A3"} and not (
                row.get("execution_authorized") is False
                and row.get("result_status") == "NOT_RUN"
                and row.get("test_set_opened") == "NO"
            ):
                hard_failures.append(f"{lane_id}:{row['row_id']}:truth_guards")

        normalized_counts = {
            "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW": counts.get(
                "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW", 0
            ),
            "EVIDENCE_INCOMPLETE": counts.get("EVIDENCE_INCOMPLETE", 0),
            "DISPOSITIVE_REJECT": counts.get("DISPOSITIVE_REJECT", 0),
        }
        if normalized_counts != cfg["expected_counts"]:
            hard_failures.append(f"{lane_id}:status_counts")

        if lane_id == "R2-A1":
            coverage = handoff.get("coverage")
            status_counts = coverage.get("status_counts") if isinstance(coverage, dict) else None
            if isinstance(status_counts, dict) and "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW" not in status_counts:
                contract_findings.append({
                    "finding_id": "R2-CF-A1-001",
                    "severity": "SCHEMA_NONCONFORMANCE",
                    "lane_id": lane_id,
                    "detail": "Handoff status_counts abbreviates the required sufficient-status enum as EVIDENCE_SUFFICIENT.",
                    "selection_effect": "POSITIVE_SELECTION_PROHIBITED; row-level statuses remain readable.",
                })
        if lane_id == "R2-A2":
            missing_by_row = {
                str(row.get("row_id")): sorted(COMMON_ROW_KEYS - set(row))
                for row in rows
                if isinstance(row, dict) and COMMON_ROW_KEYS - set(row)
            }
            if missing_by_row:
                contract_findings.append({
                    "finding_id": "R2-CF-A2-001",
                    "severity": "SCHEMA_NONCONFORMANCE",
                    "lane_id": lane_id,
                    "detail": "dataset_evidence_register rows do not implement the common row contract; lane_evidence_status is used instead of evidence_status and several required guards/fields are absent.",
                    "missing_keys_by_row": missing_by_row,
                    "selection_effect": "POSITIVE_SELECTION_PROHIBITED; explicit incomplete statuses may support NO_SELECTION only.",
                })
        if lane_id == "R2-A3" and handoff.get("lane_id") != lane_id:
            contract_findings.append({
                "finding_id": "R2-CF-A3-001",
                "severity": "SCHEMA_NONCONFORMANCE",
                "lane_id": lane_id,
                "detail": f"Handoff lane_id is {handoff.get('lane_id')!r}, expected {lane_id!r}.",
                "selection_effect": "POSITIVE_SELECTION_PROHIBITED; output-root identity remains unambiguous.",
            })

        lane_results[lane_id] = {
            "exact_file_set": sorted(present_files),
            "handoff": {**handoff_digest, "expected_sha256": cfg["handoff_sha256"]},
            "output_checks": output_checks,
            "candidate_status_counts": normalized_counts,
            "model": model,
            "reasoning": reasoning,
            "verdict": handoff.get("verdict", handoff.get("lane_verdict")),
        }

    candidate_intersection = []
    selectable = []
    for row_id in CANDIDATES:
        statuses = row_statuses[row_id]
        positive = (
            len(statuses) == 3
            and all(
                status == "EVIDENCE_SUFFICIENT_FOR_G1_REVIEW"
                for status in statuses.values()
            )
        )
        if positive:
            selectable.append(row_id)
        candidate_intersection.append(
            {
                "row_id": row_id,
                "lane_statuses": statuses,
                "positive_selection_eligible": positive,
            }
        )

    if len(selectable) != 0:
        hard_failures.append("unexpected_positive_selection_candidate")

    mechanical_import_passed = not hard_failures
    contract_conformity_passed = not contract_findings
    no_selection_only = mechanical_import_passed and len(selectable) == 0
    overall_passed = mechanical_import_passed and contract_conformity_passed
    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e4-r2-lanes-validation-1.0",
        "created_at": "2026-08-22",
        "overall_passed": overall_passed,
        "mechanical_import_passed": mechanical_import_passed,
        "contract_conformity_passed": contract_conformity_passed,
        "positive_selection_gate_passed": False,
        "no_selection_synthesis_allowed": no_selection_only,
        "verdict": (
            "PASS_R2_A1_A2_A3_IMPORTED_VALIDATED_READY_FOR_G1"
            if overall_passed
            else (
                "R2_LANES_IMPORTED_HASH_VALIDATED_CONTRACT_NONCONFORMANT_NO_SELECTION_ONLY"
                if no_selection_only
                else "FAIL_R2_A1_A2_A3_CENTRAL_INTAKE"
            )
        ),
        "hard_failure_count": len(hard_failures),
        "hard_failures": hard_failures,
        "contract_finding_count": len(contract_findings),
        "contract_findings": contract_findings,
        "strict_json_documents_parsed": parsed_json_documents,
        "expected_json_documents": 11,
        "candidate_order": CANDIDATES,
        "selectable_candidate_count": len(selectable),
        "selectable_candidates": selectable,
        "candidate_intersection": candidate_intersection,
        "lanes": lane_results,
        "truth_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "execution_authorized": False,
        },
        "next_gate": (
            "R2_G1_NO_SELECTION_FAIL_CLOSED_SYNTHESIS"
            if no_selection_only
            else "R2_A_LANE_REMEDIATION_REQUIRED"
        ),
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if no_selection_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
