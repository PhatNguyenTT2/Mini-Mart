from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST = CONTROL / "e4_r3_fd1_frozen_output_manifest.json"
EXPECTED_IDS = [
    "R3-BUNDLE-CORNAC-ML100K-001",
    "R3-BUNDLE-ELLIOT-ML1M-001",
    "R3-BUNDLE-DAISYREC-ML1M-001",
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


def check(checks: dict[str, bool], failures: list[str], name: str, condition: bool) -> None:
    checks[name] = bool(condition)
    if not condition:
        failures.append(name)


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    try:
        manifest = load_json(MANIFEST)
    except Exception as exc:
        print(json.dumps({"passed": False, "failures": [f"manifest_parse:{exc}"]}, indent=2))
        return 1

    inputs = manifest.get("inputs")
    check(checks, failures, "inputs_is_list", isinstance(inputs, list))
    if not isinstance(inputs, list):
        inputs = []
    paths = [row.get("path") for row in inputs if isinstance(row, dict)]
    check(checks, failures, "input_count_16", manifest.get("input_count") == 16 == len(inputs))
    check(checks, failures, "paths_unique", len(paths) == len(inputs) == len(set(paths)))
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
        except Exception as exc:
            failures.append(f"read_or_utf8:{relative}:{exc}")
            continue
        if len(payload) != row.get("canonical_lf_bytes"):
            failures.append(f"byte_mismatch:{relative}")
            continue
        if hashlib.sha256(payload).hexdigest() != row.get("canonical_lf_sha256"):
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
    check(checks, failures, "frozen_outputs_16_of_16", matched == 16)
    check(checks, failures, "strict_json_12_of_12", json_verified == 12)
    check(checks, failures, "candidate_ids_frozen", manifest.get("candidate_ids") == EXPECTED_IDS and manifest.get("candidate_count") == 3)
    check(checks, failures, "truth_state_frozen", manifest.get("truth_state") == TRUTH)

    seed_path = ROOT / manifest.get("seed_binding", {}).get("path", "")
    if seed_path.is_file():
        seed_payload = canonical_lf(seed_path)
        expected_binding = {
            "path": "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery/candidate_bundle_seeds.json",
            "canonical_lf_bytes": len(seed_payload),
            "canonical_lf_sha256": hashlib.sha256(seed_payload).hexdigest(),
        }
    else:
        expected_binding = None
    check(checks, failures, "seed_binding_replays", expected_binding is not None and manifest.get("seed_binding") == expected_binding)

    seeds = load_json(ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery/candidate_bundle_seeds.json")
    seed_ids = [row.get("candidate_id") for row in seeds.get("candidates", []) if isinstance(row, dict)]
    check(checks, failures, "seed_ids_exact_order", seed_ids == EXPECTED_IDS)
    check(checks, failures, "seed_truth_state", seeds.get("truth_state") == TRUTH)
    check(checks, failures, "no_selection", seeds.get("selection_performed") is False and seeds.get("selected_candidate_id") is None)

    scout_receipt = load_json(CONTROL / "rebaseline_v2_e4_r3_fd1_scouts_validation_receipt.json")
    fd1_receipt = load_json(CONTROL / "rebaseline_v2_e4_r3_fd1_validation_receipt.json")
    check(checks, failures, "scout_receipt_pass", scout_receipt.get("passed") is True and scout_receipt.get("failure_count") == 0)
    check(checks, failures, "fd1_receipt_pass", fd1_receipt.get("passed") is True and fd1_receipt.get("candidate_ids") == EXPECTED_IDS)

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r3-fd1-frozen-output-gate-result-1.0",
        "passed": passed,
        "verdict": "PASS_R3_FD1_FROZEN_16_OF_16_READY_FOR_PARALLEL_FD2_FD4" if passed else "FAIL_R3_FD1_FROZEN_OUTPUT_GATE",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_outputs": {"expected": 16, "matched": matched, "strict_json_verified": json_verified},
        "candidate_ids": EXPECTED_IDS,
        "seed_binding": expected_binding,
        "execution_authorized": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
