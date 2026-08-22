"""Fail-closed structural validator for Stage 1E Wave 1 planning handoffs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
STAGE_ROOT = CONTROL.parent
LANES_ROOT = STAGE_ROOT / "phase1_plan" / "lanes"
INPUT_MANIFEST_SHA256 = "f3ff89098e105778072602306df5c1c66361e0867b14fa688b94d78c9ee516a8"

EXPECTED = {
    "E1_dataset_protocol": {
        "dataset_manifest_draft.json",
        "protocol_lock_draft.md",
        "test_seal_audit.md",
        "lane_handoff.json",
    },
    "E2_baseline_provenance": {
        "baseline_registry_draft.json",
        "reference_reproduction_matrix.md",
        "environment_isolation_matrix.md",
        "exclusion_candidates.md",
        "lane_handoff.json",
    },
    "E3_evaluator_statistics": {
        "evaluator_contract_draft.md",
        "statistics_preregistration_draft.md",
        "schema_contracts_draft.json",
        "implementation_gap_register.md",
        "lane_handoff.json",
    },
    "E4_external_data": {
        "external_dataset_registry_draft.json",
        "compatibility_and_rights_matrix.md",
        "acquisition_plan.md",
        "lane_handoff.json",
    },
    "E5_compute_runtime": {
        "tuning_compute_protocol_draft.md",
        "runtime_preregistration_draft.md",
        "execution_dag.json",
        "command_confirmation_template.md",
        "lane_handoff.json",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    failures: list[str] = []
    lanes: dict[str, object] = {}

    for lane_id, required in EXPECTED.items():
        lane_dir = LANES_ROOT / lane_id
        missing = sorted(name for name in required if not (lane_dir / name).is_file())
        record: dict[str, object] = {"missing": missing}
        if missing:
            failures.append(f"{lane_id}: missing {', '.join(missing)}")
            lanes[lane_id] = record
            continue

        try:
            handoff = json.loads((lane_dir / "lane_handoff.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(f"{lane_id}: invalid handoff JSON: {exc}")
            lanes[lane_id] = record
            continue

        checks = {
            "lane_id": handoff.get("lane_id") == lane_id,
            "input_manifest_sha256": handoff.get("input_manifest_sha256")
            == INPUT_MANIFEST_SHA256,
            "test_set_opened": handoff.get("test_set_opened") == "NO",
            "result_status": handoff.get("result_status") == "NOT_RUN",
            "verdict_present": bool(handoff.get("verdict")),
            "status_present": bool(handoff.get("status")),
        }
        for check, passed in checks.items():
            if not passed:
                failures.append(f"{lane_id}: failed handoff check {check}")

        output_hashes = handoff.get("outputs")
        hash_checks: dict[str, bool] = {}
        if not isinstance(output_hashes, list):
            failures.append(f"{lane_id}: outputs must be a list")
        else:
            by_name = {
                Path(str(row.get("path", ""))).name: row
                for row in output_hashes
                if isinstance(row, dict)
            }
            for name in sorted(required - {"lane_handoff.json"}):
                row = by_name.get(name)
                passed = bool(row) and row.get("sha256") == sha256(lane_dir / name)
                hash_checks[name] = passed
                if not passed:
                    failures.append(f"{lane_id}: missing or wrong output hash for {name}")

        record.update(
            {
                "checks": checks,
                "hash_checks": hash_checks,
                "verdict": handoff.get("verdict"),
                "status": handoff.get("status"),
            }
        )
        lanes[lane_id] = record

    receipt = {
        "schema_version": "stage1e-wave1-validation-1.0",
        "verdict": "PASS_READY_FOR_E6" if not failures else "FAIL_NOT_READY_FOR_E6",
        "passed": not failures,
        "checks_total": sum(
            6 + len(files - {"lane_handoff.json"}) for files in EXPECTED.values()
        ),
        "failure_count": len(failures),
        "failures": failures,
        "lanes": lanes,
        "test_set_opened": "NO",
        "result_status": "NOT_RUN",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
