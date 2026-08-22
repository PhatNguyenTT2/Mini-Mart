from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
OUTPUT = ROOT / (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/"
    "wave_ac/E4_R5M0_source_materialization"
)
EXPECTED_FILES = {
    "materialization_receipt.json",
    "source_tree_manifest.json",
    "selected_blob_manifest.json",
    "operation_log.md",
    "materialization_handoff.json",
}
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
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


def check(checks: dict[str, bool], failures: list[str], name: str, value: bool) -> None:
    checks[name] = bool(value)
    if not value:
        failures.append(name)


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise ValidationError(result.stderr.strip())
    return result.stdout.strip()


def normalize_origin(value: str) -> str:
    return value.rstrip("/").removesuffix(".git").casefold()


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    check(checks, failures, "output_root_exists", OUTPUT.is_dir())
    observed_files = {path.name for path in OUTPUT.iterdir()} if OUTPUT.is_dir() else set()
    check(checks, failures, "exact_five_output_files", observed_files == EXPECTED_FILES)

    try:
        receipt = load_json(OUTPUT / "materialization_receipt.json")
        tree = load_json(OUTPUT / "source_tree_manifest.json")
        blobs = load_json(OUTPUT / "selected_blob_manifest.json")
        handoff = load_json(OUTPUT / "materialization_handoff.json")
        contract = load_json(CONTROL / "e4_r5_source_materialization_contract.json")
        lock = load_json(CONTROL / "e4_r5_candidate_lock.json")
        s0 = load_json(CONTROL / "rebaseline_v2_e4_r5_s0_gate_receipt.json")
    except Exception as exc:
        print(json.dumps({"passed": False, "failures": [f"parse:{exc}"]}, indent=2))
        return 1

    strict_json_count = sum(1 for name in EXPECTED_FILES if name.endswith(".json"))
    check(checks, failures, "strict_json_outputs_four", strict_json_count == 4)
    check(
        checks,
        failures,
        "s0_v2_gate_passed",
        s0.get("passed") is True
        and s0.get("verdict") == "PASS_R5_S0_SOURCE_ONLY_GATE_V2_21_OF_21_READY_FOR_R5_M0",
    )
    check(
        checks,
        failures,
        "receipt_pass_two_of_two",
        receipt.get("status") == "PASS_TWO_OF_TWO_HASH_LOCKED_SOURCE_ONLY_READY_FOR_R5_M1"
        and receipt.get("candidate_count") == 2
        and len(receipt.get("candidates", [])) == 2,
    )
    guards = receipt.get("scope_guards", {})
    check(
        checks,
        failures,
        "scope_guards_all_closed",
        guards.get("named_repository_count") == 2
        and all(value is False for key, value in guards.items() if key != "named_repository_count"),
    )
    check(
        checks,
        failures,
        "truth_state_all_outputs",
        all(payload.get("truth_state") == TRUTH for payload in (receipt, tree, blobs, handoff)),
    )

    contract_rows = {
        row["candidate_id"]: row
        for row in contract.get("materializations", [])
        if isinstance(row, dict)
    }
    receipt_rows = {
        row["candidate_id"]: row
        for row in receipt.get("candidates", [])
        if isinstance(row, dict)
    }
    tree_rows = {
        row["candidate_id"]: row
        for row in tree.get("candidates", [])
        if isinstance(row, dict)
    }
    blob_rows = {
        row["candidate_id"]: row
        for row in blobs.get("candidates", [])
        if isinstance(row, dict)
    }
    ids = set(contract_rows)
    check(
        checks,
        failures,
        "candidate_sets_exact",
        len(ids) == 2 and set(receipt_rows) == ids == set(tree_rows) == set(blob_rows),
    )

    verified_files = 0
    expected_files = 0
    for candidate_id in sorted(ids):
        contract_row = contract_rows[candidate_id]
        receipt_row = receipt_rows[candidate_id]
        tree_row = tree_rows[candidate_id]
        blob_row = blob_rows[candidate_id]
        root = ROOT / contract_row["local_root"]
        revision = contract_row["full_revision"]
        origin = git(root, "remote", "get-url", "origin")
        head = git(root, "rev-parse", "HEAD")
        tree_id = git(root, "rev-parse", f"{revision}^{{tree}}")
        status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
        check(
            checks,
            failures,
            f"git_identity_{candidate_id}",
            normalize_origin(origin) == normalize_origin(contract_row["repository_url"])
            and head == revision
            and tree_id == receipt_row.get("git_tree") == tree_row.get("git_tree")
            and status == "",
        )
        check(
            checks,
            failures,
            f"zero_scope_violations_{candidate_id}",
            all(
                receipt_row.get(key) == 0
                for key in (
                    "missing_required_path_count",
                    "selected_prohibited_artifact_count",
                    "selected_submodule_count",
                    "selected_symlink_count",
                    "selected_lfs_pointer_count",
                    "vendor_worktree_modification_count",
                )
            )
            and receipt_row.get("status") == "PASS_HASH_LOCKED_SOURCE_ONLY",
        )
        files = blob_row.get("files", [])
        expected_files += len(files)
        for file_row in files:
            path = root / file_row["path"]
            if (
                path.is_file()
                and path.stat().st_size == file_row.get("size_bytes")
                and raw_sha256(path) == file_row.get("sha256_raw_bytes")
            ):
                verified_files += 1
        check(
            checks,
            failures,
            f"blob_count_{candidate_id}",
            blob_row.get("file_count") == len(files) == receipt_row.get("materialized_file_count")
            and blob_row.get("total_size_bytes") == receipt_row.get("materialized_total_size_bytes"),
        )
        selected_tree_count = sum(
            1 for row in tree_row.get("entries", []) if row.get("selected_by_sparse_policy") is True
        )
        check(
            checks,
            failures,
            f"tree_inventory_{candidate_id}",
            tree_row.get("tree_entry_count") == len(tree_row.get("entries", []))
            and tree_row.get("selected_tree_entry_count") == selected_tree_count
            and receipt_row.get("tree_entry_count") == tree_row.get("tree_entry_count"),
        )

    check(checks, failures, "all_materialized_file_hashes_verified", verified_files == expected_files)
    check(
        checks,
        failures,
        "handoff_ready_for_parallel_audits",
        handoff.get("status") == "READY_FOR_INDEPENDENT_R5_M1_SOURCE_AUDITS"
        and handoff.get("parallel_next_stages") == ["R5-M1A", "R5-M1B"]
        and handoff.get("benchmark_admitted_candidate_count") == 0
        and handoff.get("dataset_environment_or_execution_authorized") is False
        and handoff.get("mandatory_user_checkpoint_before_data_environment_run") == "R5-M2",
    )
    operation_log = (OUTPUT / "operation_log.md").read_text(encoding="utf-8")
    check(
        checks,
        failures,
        "operation_log_boundaries",
        all(
            marker in operation_log
            for marker in (
                "R5-S0 v2 passed before checkout",
                "No dataset/checkpoint was acquired",
                "project v5 TEST was not opened",
                "invalid for the paper",
            )
        ),
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-m0-validation-result-1.0",
        "passed": passed,
        "verdict": "PASS_R5_M0_TWO_HASH_LOCKED_SOURCE_TREES_READY_FOR_R5_M1" if passed else "FAIL_R5_M0_BLOCKED",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "output_files": {"present": len(observed_files), "expected": 5, "strict_json": 4},
        "candidates": {"verified": len(ids), "expected": 2},
        "materialized_files": {"verified": verified_files, "expected": expected_files},
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
