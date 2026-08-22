from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r4_g0_frozen_input_manifest.json"
LANE_ROOTS = [
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_u/E4_R4D1A_artifact_package_scout",
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_v/E4_R4D1B_benchmark_suite_scout",
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_w/E4_R4D1C_framework_packet_scout",
]
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
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
        "manifest_input_count_22",
        manifest.get("input_count") == 22 == len(inputs),
    )
    check(
        checks,
        failures,
        "manifest_paths_unique",
        len(paths) == len(inputs) == len(set(paths)),
    )

    matched = 0
    json_verified = 0
    worker_outputs = 0
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
        if any(root in path.parents for root in LANE_ROOTS):
            worker_outputs += 1
        matched += 1

    check(checks, failures, "frozen_inputs_22_of_22", matched == 22)
    check(
        checks,
        failures,
        "strict_json_inputs_17_of_17",
        json_verified == 17,
    )
    check(
        checks,
        failures,
        "worker_outputs_15_of_15",
        worker_outputs == 15,
    )

    entry = manifest.get("entry_gate", {})
    check(
        checks,
        failures,
        "entry_gate_counts",
        entry.get("verdict")
        == "PASS_R4_D1_SCOUTS_READY_FOR_CENTRAL_HASH_FREEZE"
        and entry.get("lane_count") == 3
        and entry.get("proposals_examined") == 18
        and entry.get("proposals_admitted") == 0
        and entry.get("proposals_excluded") == 18
        and entry.get("source_record_mentions") == 90,
    )
    replay = manifest.get("central_replay_policy", {})
    check(
        checks,
        failures,
        "zero_admission_zero_replay_scope",
        replay.get("worker_admitted_proposal_count") == 0
        and replay.get("central_replay_required_proposal_count") == 0
        and replay.get("central_replay_required_url_count") == 0
        and replay.get("central_repair_allowed") is False
        and replay.get("cross_join_allowed") is False,
    )
    check(
        checks,
        failures,
        "manifest_truth_state",
        manifest.get("truth_state") == TRUTH,
    )

    admitted_total = 0
    excluded_total = 0
    source_total = 0
    proposal_ids: list[str] = []
    source_urls: list[str] = []
    for root in LANE_ROOTS:
        candidates = load_json(root / "scout_candidates.json")
        excluded = load_json(root / "excluded_candidate_log.json")
        sources = load_json(root / "source_replay_log.json")
        admitted_total += candidates.get("proposals_admitted_count", -1000)
        excluded_total += excluded.get("excluded_count", -1000)
        source_total += len(sources.get("source_records", []))
        proposal_ids.extend(
            row.get("proposal_id")
            for row in excluded.get("excluded_candidates", [])
            if isinstance(row, dict)
        )
        source_urls.extend(
            row.get("url")
            for row in sources.get("source_records", [])
            if isinstance(row, dict)
        )
    check(
        checks,
        failures,
        "recomputed_lane_totals",
        admitted_total == 0
        and excluded_total == 18
        and source_total == 90,
    )
    check(
        checks,
        failures,
        "proposal_ids_unique",
        len(proposal_ids) == 18 == len(set(proposal_ids)),
    )
    check(
        checks,
        failures,
        "source_dedup_recomputed",
        len(source_urls) == 90 and len(set(source_urls)) == 88,
    )

    lane_validator = subprocess.run(
        [
            sys.executable,
            str(CONTROL / "validate_e4_r4_d1_scouts.py"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    lane_result: dict[str, Any] = {}
    if lane_validator.returncode == 0:
        try:
            lane_result = json.loads(lane_validator.stdout)
        except Exception as exc:
            failures.append(f"lane_validator_output_parse:{exc}")
    check(
        checks,
        failures,
        "lane_validator_replay_passed",
        lane_validator.returncode == 0
        and lane_result.get("passed") is True
        and lane_result.get("failure_count") == 0
        and lane_result.get("aggregate", {}).get("admitted") == 0,
    )

    contract = (
        CONTROL / "e4_r4_g0_central_admission_contract.md"
    ).read_text(encoding="utf-8")
    markers = [
        "does not choose the convenient representation",
        "NO_ADMISSIBLE_BUNDLE_STOP_FAIL_CLOSED",
        "R4-A1–A3 are not launched",
        "RESULT_STATUS=NOT_RUN",
        "TEST_SET_OPENED=NO",
        "ACCEPTED_RESULT_ROWS=0",
    ]
    check(
        checks,
        failures,
        "g0_contract_markers",
        all(marker in contract for marker in markers),
    )

    passed = not failures
    result = {
        "schema_version": (
            "stage1e-rebaseline-v2-e4-r4-g0-frozen-input-gate-result-1.0"
        ),
        "passed": passed,
        "verdict": (
            "PASS_R4_G0_FROZEN_22_OF_22_READY_FOR_CENTRAL_SYNTHESIS"
            if passed
            else "FAIL_R4_G0_FROZEN_INPUT_GATE_BLOCKED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_inputs": {
            "expected": 22,
            "matched": matched,
            "strict_json_expected": 17,
            "strict_json_verified": json_verified,
            "worker_outputs_expected": 15,
            "worker_outputs_matched": worker_outputs,
        },
        "recomputed": {
            "examined": len(proposal_ids),
            "admitted": admitted_total,
            "excluded": excluded_total,
            "source_mentions": source_total,
            "unique_source_urls": len(set(source_urls)),
        },
        "central_replay_required_proposals": 0,
        "central_replay_required_urls": 0,
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
