"""Fail-closed structural validator for Stage 1E Rebaseline v2 Wave A."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


CONTROL = Path(__file__).resolve().parent
ROOT = CONTROL.parent / "rebaseline_v2" / "wave_a"
INPUT_SHA = "107299c026434366ed6ddb18f4ee6e25fd790d9799fd81c1c1e87871ed60744d"

EXPECTED = {
    "E1_official_repos": {
        "official_repo_registry.json",
        "training_pipeline_command_map.md",
        "implementation_provenance_matrix.md",
        "repo_exclusion_log.md",
        "lane_handoff.json",
    },
    "E2_reference_datasets": {
        "reference_dataset_registry.json",
        "dataset_repo_compatibility_matrix.md",
        "rights_and_access_matrix.md",
        "dataset_exclusion_log.md",
        "lane_handoff.json",
    },
    "E3_metric_benchmarks": {
        "official_benchmark_registry.json",
        "metric_protocol_matrix.md",
        "reported_result_locator_map.md",
        "reproduction_acceptance_rules.md",
        "lane_handoff.json",
    },
}

REQUIRED_PASSPORT_FIELDS = {
    "origin_skill",
    "origin_mode",
    "origin_date",
    "verification_status",
    "version_label",
}
VERIFICATION_STATUSES = {"VERIFIED", "UNVERIFIED", "STALE"}


def digest_bytes(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def digest_canonical_lf(path: Path) -> str:
    """Hash text artifacts after portable CRLF-to-LF normalization."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def reject_case_colliding_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject exact duplicates and case-only aliases in every JSON object."""
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


def main() -> int:
    failures: list[str] = []
    lane_receipts: dict[str, object] = {}

    for lane_id, expected_files in EXPECTED.items():
        lane = ROOT / lane_id
        missing = sorted(name for name in expected_files if not (lane / name).is_file())
        if missing:
            failures.append(f"{lane_id}: missing {', '.join(missing)}")
            lane_receipts[lane_id] = {"missing": missing}
            continue

        try:
            handoff = json.loads(
                (lane / "lane_handoff.json").read_text(encoding="utf-8"),
                object_pairs_hook=reject_case_colliding_keys,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{lane_id}: invalid handoff: {exc}")
            lane_receipts[lane_id] = {"invalid_handoff": str(exc)}
            continue

        passport = handoff.get("material_passport")
        passport_checks = {
            "object": isinstance(passport, dict),
            "required_fields": isinstance(passport, dict)
            and REQUIRED_PASSPORT_FIELDS.issubset(passport),
            "verification_status": isinstance(passport, dict)
            and passport.get("verification_status") in VERIFICATION_STATUSES,
        }
        if isinstance(passport, dict):
            passport_checks["nonempty_values"] = all(
                isinstance(passport.get(field), str) and bool(passport[field].strip())
                for field in REQUIRED_PASSPORT_FIELDS
            )
        else:
            passport_checks["nonempty_values"] = False
        for name, passed in passport_checks.items():
            if not passed:
                failures.append(f"{lane_id}: failed material_passport.{name}")

        checks = {
            "lane_id": handoff.get("lane_id") == lane_id,
            "model": handoff.get("model") == "gpt-5.6-sol",
            "reasoning": handoff.get("reasoning") == "xhigh",
            "input_manifest_sha256": handoff.get("input_manifest_sha256") == INPUT_SHA,
            "test_set_opened": handoff.get("test_set_opened") == "NO",
            "result_status": handoff.get("result_status") == "NOT_RUN",
            "status_present": bool(handoff.get("status")),
            "verdict_present": bool(handoff.get("verdict")),
        }
        for name, passed in checks.items():
            if not passed:
                failures.append(f"{lane_id}: failed {name}")

        outputs = handoff.get("outputs")
        output_rows = {
            Path(str(row.get("path", ""))).name: row
            for row in outputs
            if isinstance(outputs, list) and isinstance(row, dict)
        } if isinstance(outputs, list) else {}
        output_checks: dict[str, object] = {}
        for name in sorted(expected_files - {"lane_handoff.json"}):
            row = output_rows.get(name)
            recorded = row.get("sha256") if row else None
            canonical_lf = digest_canonical_lf(lane / name)
            worktree_bytes = digest_bytes(lane / name)
            passed = bool(row) and recorded == canonical_lf
            output_checks[name] = {
                "passed": passed,
                "recorded_sha256": recorded,
                "canonical_lf_sha256": canonical_lf,
                "worktree_byte_sha256": worktree_bytes,
            }
            if not passed:
                failures.append(f"{lane_id}: missing/wrong SHA for {name}")

        lane_receipts[lane_id] = {
            "checks": checks,
            "material_passport_checks": passport_checks,
            "output_checks": output_checks,
            "handoff_canonical_lf_sha256": digest_canonical_lf(
                lane / "lane_handoff.json"
            ),
            "handoff_worktree_byte_sha256": digest_bytes(lane / "lane_handoff.json"),
            "status": handoff.get("status"),
            "verdict": handoff.get("verdict"),
            "blockers": handoff.get("blockers", []),
        }

    receipt = {
        "schema_version": "stage1e-rebaseline-v2-wave-a-validation-1.0",
        "passed": not failures,
        "verdict": (
            "PASS_STRUCTURALLY_READY_FOR_E4"
            if not failures
            else "FAIL_NOT_READY_FOR_E4"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "lanes": lane_receipts,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
