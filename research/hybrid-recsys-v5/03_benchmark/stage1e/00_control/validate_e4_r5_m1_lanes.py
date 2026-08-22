from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
CONTRACT_PATH = CONTROL / "e4_r5_m1_source_audit_contract.json"
BLOB_MANIFEST_PATH = ROOT / (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_ac/E4_R5M0_source_materialization/selected_blob_manifest.json"
)
EXPECTED_FILES = {
    "source_fact_matrix.json",
    "gap_closure_assessment.json",
    "v5_adapter_feasibility.json",
    "audit_report.md",
    "audit_handoff.json",
}
LANES = {
    "R5-M1A": {
        "candidate_id": "R5-CAND-RECBOLE-BPR-ML100K-001",
        "other_candidate_id": "R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001",
        "output_root": ROOT / (
            "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
            "wave_ad/E4_R5M1A_recbole_source_audit"
        ),
    },
    "R5-M1B": {
        "candidate_id": "R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001",
        "other_candidate_id": "R5-CAND-RECBOLE-BPR-ML100K-001",
        "output_root": ROOT / (
            "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
            "wave_ae/E4_R5M1B_recbole_gnn_source_audit"
        ),
    },
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


class ValidationError(ValueError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate key: {key}")
        casefolded = key.casefold()
        if casefolded in folded and folded[casefolded] != key:
            raise ValidationError(f"case-colliding keys: {folded[casefolded]} / {key}")
        folded[casefolded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValidationError(f"top-level JSON is not an object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(checks: dict[str, bool], failures: list[str], name: str, value: bool) -> None:
    checks[name] = bool(value)
    if not value:
        failures.append(name)


def model_matches(payload: dict[str, Any]) -> bool:
    model = payload.get("model_profile", {})
    return isinstance(model, dict) and all(model.get(key) == value for key, value in MODEL.items())


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    contract = load_json(CONTRACT_PATH)
    blob_manifest = load_json(BLOB_MANIFEST_PATH)
    closed_dimension_statuses = set(contract["closed_status_sets"]["dimension"])
    closed_candidate_statuses = set(contract["closed_status_sets"]["candidate"])
    closed_repro_statuses = set(contract["closed_status_sets"]["reproducibility"])
    dimension_ids = {
        row["id"] for row in contract.get("mandatory_audit_dimensions", []) if isinstance(row, dict)
    }
    required_fact_fields = set(contract["required_source_fact_fields"])
    contract_lanes = {
        row["stage_id"]: row for row in contract.get("lanes", []) if isinstance(row, dict)
    }
    blob_candidates = {
        row["candidate_id"]: row for row in blob_manifest.get("candidates", []) if isinstance(row, dict)
    }
    check(checks, failures, "exact_lane_contract", set(contract_lanes) == set(LANES))
    check(checks, failures, "exact_dimension_contract", len(dimension_ids) == 9)

    total_files = 0
    strict_json = 0
    total_facts = 0
    positive_hash_facts = 0
    candidate_statuses: dict[str, str | None] = {}
    reproducibility_statuses: dict[str, str | None] = {}

    for stage_id, lane in LANES.items():
        output_root: Path = lane["output_root"]
        check(checks, failures, f"{stage_id}_root_exists", output_root.is_dir())
        files = {path.name for path in output_root.iterdir()} if output_root.is_dir() else set()
        check(checks, failures, f"{stage_id}_exact_five_files", files == EXPECTED_FILES)
        total_files += len(files)
        try:
            fact_matrix = load_json(output_root / "source_fact_matrix.json")
            gap = load_json(output_root / "gap_closure_assessment.json")
            adapter = load_json(output_root / "v5_adapter_feasibility.json")
            handoff = load_json(output_root / "audit_handoff.json")
            strict_json += 4
        except Exception as exc:
            failures.append(f"{stage_id}_parse:{exc}")
            continue

        payloads = (fact_matrix, gap, adapter, handoff)
        check(
            checks,
            failures,
            f"{stage_id}_identity_and_truth",
            all(payload.get("stage_id") == stage_id for payload in payloads)
            and all(payload.get("candidate_id") == lane["candidate_id"] for payload in payloads)
            and all(payload.get("truth_state") == TRUTH for payload in payloads),
        )
        check(
            checks,
            failures,
            f"{stage_id}_model_profile",
            model_matches(fact_matrix) and model_matches(handoff),
        )
        serialized = "\n".join(json.dumps(payload, ensure_ascii=False) for payload in payloads)
        check(
            checks,
            failures,
            f"{stage_id}_no_cross_candidate_join",
            lane["other_candidate_id"] not in serialized,
        )

        dimensions = fact_matrix.get("dimensions", fact_matrix.get("dimension_assessments", []))
        observed_dimension_ids = {
            row.get("dimension_id", row.get("id"))
            for row in dimensions
            if isinstance(row, dict)
        }
        check(
            checks,
            failures,
            f"{stage_id}_nine_dimensions_exactly_once",
            len(dimensions) == 9 and observed_dimension_ids == dimension_ids,
        )
        check(
            checks,
            failures,
            f"{stage_id}_dimension_statuses_closed",
            all(
                isinstance(row, dict) and row.get("status") in closed_dimension_statuses
                for row in dimensions
            ),
        )

        facts = fact_matrix.get("facts", fact_matrix.get("source_facts", []))
        fact_ids = [row.get("fact_id") for row in facts if isinstance(row, dict)]
        check(
            checks,
            failures,
            f"{stage_id}_fact_schema_and_unique_ids",
            len(facts) == len(fact_ids) == len(set(fact_ids))
            and all(required_fact_fields.issubset(row) for row in facts if isinstance(row, dict)),
        )
        file_map = {
            row["path"]: row
            for row in blob_candidates[lane["candidate_id"]].get("files", [])
            if isinstance(row, dict)
        }
        source_root = Path(contract_lanes[stage_id]["source_root"])
        lane_positive = 0
        for index, fact in enumerate(facts):
            if not isinstance(fact, dict):
                failures.append(f"{stage_id}_fact_{index}_not_object")
                continue
            status = fact.get("status")
            if status not in closed_dimension_statuses:
                failures.append(f"{stage_id}_fact_{index}_status")
                continue
            if status in {"PASS_SOURCE_ESTABLISHED", "PARTIAL_SOURCE_BOUND"}:
                relative = fact.get("source_relative_path")
                digest = fact.get("source_sha256_raw_bytes")
                manifest_row = file_map.get(relative)
                source_path = source_root / relative if isinstance(relative, str) else source_root
                if (
                    not isinstance(relative, str)
                    or not isinstance(digest, str)
                    or manifest_row is None
                    or manifest_row.get("sha256_raw_bytes") != digest
                    or not source_path.is_file()
                    or raw_sha256(source_path) != digest
                    or not str(fact.get("symbol_or_line_locator", "")).strip()
                ):
                    failures.append(f"{stage_id}_fact_{index}_hash_binding")
                else:
                    lane_positive += 1
        total_facts += len(facts)
        positive_hash_facts += lane_positive
        check(
            checks,
            failures,
            f"{stage_id}_positive_facts_hash_bound",
            lane_positive
            == sum(
                1
                for row in facts
                if isinstance(row, dict)
                and row.get("status") in {"PASS_SOURCE_ESTABLISHED", "PARTIAL_SOURCE_BOUND"}
            ),
        )

        candidate_status = handoff.get("candidate_status")
        repro_status = handoff.get("reproducibility_status")
        candidate_statuses[stage_id] = candidate_status
        reproducibility_statuses[stage_id] = repro_status
        status_counts = handoff.get("status_counts", {})
        check(
            checks,
            failures,
            f"{stage_id}_handoff_closed_statuses",
            candidate_status in closed_candidate_statuses
            and repro_status in closed_repro_statuses
            and handoff.get("source_fact_count") == len(facts)
            and isinstance(status_counts, dict)
            and sum(value for value in status_counts.values() if isinstance(value, int)) == 9
            and isinstance(handoff.get("dispositive_conflicts"), list)
            and isinstance(handoff.get("remaining_blockers"), list)
            and isinstance(handoff.get("r5_g1_recommendation"), str)
            and bool(handoff.get("r5_g1_recommendation", "").strip()),
        )
        report = (output_root / "audit_report.md").read_text(encoding="utf-8")
        check(
            checks,
            failures,
            f"{stage_id}_report_truth_markers",
            all(
                marker in report
                for marker in (
                    stage_id,
                    lane["candidate_id"],
                    "NOT_RUN",
                    "TEST_SET_OPENED=NO",
                    "INVALID_FOR_PAPER",
                )
            ),
        )

    check(checks, failures, "output_files_10_of_10", total_files == 10)
    check(checks, failures, "strict_json_outputs_8_of_8", strict_json == 8)
    check(checks, failures, "both_lanes_have_source_facts", total_facts > 0 and positive_hash_facts > 0)
    check(
        checks,
        failures,
        "no_lane_claims_verified_reproducibility",
        all(value != "VERIFIED" for value in reproducibility_statuses.values()),
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-m1-lanes-validation-result-1.0",
        "passed": passed,
        "verdict": "PASS_R5_M1_TWO_SOURCE_AUDITS_READY_FOR_CENTRAL_R5_G1_FREEZE" if passed else "FAIL_R5_M1_LANES_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "outputs": {"files": total_files, "expected": 10, "strict_json": strict_json},
        "source_facts": {"total": total_facts, "positive_hash_bound": positive_hash_facts},
        "candidate_statuses": candidate_statuses,
        "reproducibility_statuses": reproducibility_statuses,
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
