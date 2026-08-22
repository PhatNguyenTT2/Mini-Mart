from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
CONTRACT_PATH = CONTROL / "e4_r5_source_materialization_contract.json"
LOCK_PATH = CONTROL / "e4_r5_candidate_lock.json"
S0_RECEIPT_PATH = CONTROL / "rebaseline_v2_e4_r5_s0_gate_receipt.json"
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}


class MaterializationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MaterializationError(f"top-level JSON is not an object: {path}")
    return value


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        rendered = " ".join(args)
        raise MaterializationError(
            f"command failed ({completed.returncode}): {rendered}\n"
            f"stdout: {completed.stdout.strip()}\n"
            f"stderr: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def git(root: Path, *args: str, input_text: str | None = None) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise MaterializationError("git executable not found")
    prefix = [
        executable,
        "-c",
        "http.sslBackend=openssl",
        "-c",
        "core.longpaths=true",
        "-c",
        "filter.lfs.process=",
        "-c",
        "filter.lfs.smudge=",
        "-c",
        "filter.lfs.required=false",
        "-C",
        str(root),
    ]
    return run(prefix + list(args), input_text=input_text)


def clone_metadata(repository_url: str, root: Path) -> None:
    executable = shutil.which("git")
    if executable is None:
        raise MaterializationError("git executable not found")
    root.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            executable,
            "-c",
            "http.sslBackend=openssl",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            "--no-recurse-submodules",
            "--origin",
            "origin",
            repository_url,
            str(root),
        ]
    )


def parse_tree(output: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in output.splitlines():
        left, path = line.split("\t", 1)
        mode, object_type, object_id = left.split(" ", 2)
        rows.append(
            {
                "mode": mode,
                "object_type": object_type,
                "git_object_id": object_id,
                "path": path.replace("\\", "/"),
            }
        )
    return rows


def selected_by_patterns(path: str, patterns: list[str]) -> bool:
    if "/" not in path:
        return True
    positive_dirs = [
        value.strip("/")
        for value in patterns
        if value.startswith("/") and value.endswith("/") and not value.startswith("!/")
    ]
    negative_dirs = [
        value[2:].strip("/")
        for value in patterns
        if value.startswith("!/") and value.endswith("/") and value != "!/*/"
    ]
    included = any(path == value or path.startswith(value + "/") for value in positive_dirs)
    excluded = any(path == value or path.startswith(value + "/") for value in negative_dirs)
    return included and not excluded


def iter_worktree_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == ".git":
            continue
        if path.is_file() or path.is_symlink():
            files.append(path)
    return sorted(files, key=lambda value: value.as_posix().casefold())


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_origin(value: str) -> str:
    return value.rstrip("/").removesuffix(".git").casefold()


def main() -> int:
    contract = load_json(CONTRACT_PATH)
    candidate_lock = load_json(LOCK_PATH)
    s0_receipt = load_json(S0_RECEIPT_PATH)
    if s0_receipt.get("passed") is not True or s0_receipt.get("verdict") != (
        "PASS_R5_S0_SOURCE_ONLY_GATE_V2_21_OF_21_READY_FOR_R5_M0"
    ):
        raise MaterializationError("R5-S0 v2 gate is not passing")
    if contract.get("truth_state") != TRUTH or candidate_lock.get("truth_state") != TRUTH:
        raise MaterializationError("persistent truth state mismatch")

    locked = {
        row["candidate_id"]: row
        for row in candidate_lock.get("candidates", [])
        if isinstance(row, dict) and isinstance(row.get("candidate_id"), str)
    }
    materializations = contract.get("materializations", [])
    if len(materializations) != 2 or set(locked) != {
        row.get("candidate_id") for row in materializations if isinstance(row, dict)
    }:
        raise MaterializationError("candidate lock/materialization cardinality mismatch")

    output_root = ROOT / contract["artifact_contract"]["write_root"]
    if output_root.exists():
        raise MaterializationError(f"fail closed: output root already exists: {output_root}")

    prohibited_extensions = {
        value.casefold() for value in contract["source_scope"]["root_level_prohibited_extensions"]
    }
    prohibited_top = {
        value.casefold() for value in contract["source_scope"]["prohibited_top_level_directories"]
    }
    tree_manifests: list[dict[str, Any]] = []
    blob_manifests: list[dict[str, Any]] = []
    receipt_rows: list[dict[str, Any]] = []
    log_rows: list[str] = []

    for materialization in materializations:
        candidate_id = materialization["candidate_id"]
        lock_row = locked[candidate_id]
        repository_url = materialization["repository_url"]
        revision = materialization["full_revision"]
        if repository_url != lock_row["repository_url"] or revision != lock_row["full_revision"]:
            raise MaterializationError(f"lock mismatch: {candidate_id}")
        root = ROOT / materialization["local_root"]
        root_resolved = root.resolve(strict=False)
        workspace_resolved = ROOT.resolve()
        if workspace_resolved not in root_resolved.parents:
            raise MaterializationError(f"source root escaped workspace: {root_resolved}")

        metadata_state = "PREEXISTING_METADATA_CLONE_VERIFIED"
        if not root.exists():
            clone_metadata(repository_url, root)
            metadata_state = "CLONED_BY_MATERIALIZER"
        if not (root / ".git").is_dir():
            raise MaterializationError(f"not an isolated Git repository: {root}")
        pre_checkout_files = iter_worktree_files(root)
        if pre_checkout_files:
            raise MaterializationError(
                f"fail closed: source files existed before locked sparse checkout: {candidate_id}"
            )

        origin = git(root, "remote", "get-url", "origin")
        if normalize_origin(origin) != normalize_origin(repository_url):
            raise MaterializationError(f"origin mismatch: {candidate_id}: {origin}")
        if git(root, "cat-file", "-t", revision) != "commit":
            raise MaterializationError(f"locked object is not a commit: {candidate_id}")
        tree_id = git(root, "rev-parse", f"{revision}^{{tree}}")
        entries = parse_tree(git(root, "ls-tree", "-r", revision))
        patterns = materialization["sparse_non_cone_patterns"]
        for entry in entries:
            entry["selected_by_sparse_policy"] = selected_by_patterns(entry["path"], patterns)
        selected_entries = [row for row in entries if row["selected_by_sparse_policy"]]
        selected_paths = {row["path"] for row in selected_entries}
        required_paths = set(materialization["required_materialized_paths"])
        missing_required_tree = sorted(required_paths - selected_paths)
        selected_submodules = [row["path"] for row in selected_entries if row["mode"] == "160000"]
        selected_symlinks = [row["path"] for row in selected_entries if row["mode"] == "120000"]
        selected_prohibited = []
        for row in selected_entries:
            path = row["path"]
            top = path.split("/", 1)[0].casefold()
            suffix = Path(path).suffix.casefold()
            if top in prohibited_top or suffix in prohibited_extensions:
                selected_prohibited.append(path)
        if missing_required_tree or selected_submodules or selected_symlinks or selected_prohibited:
            raise MaterializationError(
                f"tree preflight rejected {candidate_id}: missing={missing_required_tree}; "
                f"submodules={selected_submodules}; symlinks={selected_symlinks}; "
                f"prohibited={selected_prohibited}"
            )

        git(root, "update-ref", "--no-deref", "HEAD", revision)
        if git(root, "rev-parse", "HEAD") != revision:
            raise MaterializationError(f"failed to detach HEAD before checkout: {candidate_id}")
        git(root, "sparse-checkout", "init", "--no-cone")
        git(
            root,
            "sparse-checkout",
            "set",
            "--no-cone",
            "--stdin",
            input_text="\n".join(patterns) + "\n",
        )
        git(root, "checkout", "--detach", revision)

        head = git(root, "rev-parse", "HEAD")
        if head != revision:
            raise MaterializationError(f"detached HEAD mismatch: {candidate_id}: {head}")
        materialized_files = iter_worktree_files(root)
        materialized_relative = {
            path.relative_to(root).as_posix() for path in materialized_files
        }
        unexpected_scope = sorted(
            path for path in materialized_relative if not selected_by_patterns(path, patterns)
        )
        missing_required = sorted(required_paths - materialized_relative)
        lfs_pointers: list[str] = []
        selected_prohibited_after: list[str] = []
        selected_symlinks_after: list[str] = []
        git_entries = {row["path"]: row for row in entries}
        blob_rows: list[dict[str, Any]] = []
        for path in materialized_files:
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                selected_symlinks_after.append(relative)
                continue
            raw_prefix = path.read_bytes()[:128]
            if raw_prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
                lfs_pointers.append(relative)
            top = relative.split("/", 1)[0].casefold()
            suffix = path.suffix.casefold()
            if top in prohibited_top or suffix in prohibited_extensions:
                selected_prohibited_after.append(relative)
            tree_row = git_entries.get(relative, {})
            blob_rows.append(
                {
                    "path": relative,
                    "size_bytes": path.stat().st_size,
                    "sha256_raw_bytes": raw_sha256(path),
                    "git_blob_id": tree_row.get("git_object_id"),
                    "git_mode": tree_row.get("mode"),
                }
            )
        if (
            unexpected_scope
            or missing_required
            or lfs_pointers
            or selected_prohibited_after
            or selected_symlinks_after
        ):
            raise MaterializationError(
                f"post-checkout scope rejected {candidate_id}: unexpected={unexpected_scope}; "
                f"missing={missing_required}; lfs={lfs_pointers}; "
                f"prohibited={selected_prohibited_after}; symlinks={selected_symlinks_after}"
            )
        status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
        if status:
            raise MaterializationError(f"vendor worktree is modified: {candidate_id}: {status}")

        total_bytes = sum(row["size_bytes"] for row in blob_rows)
        tree_manifests.append(
            {
                "candidate_id": candidate_id,
                "repository_url": repository_url,
                "full_revision": revision,
                "git_tree": tree_id,
                "tree_entry_count": len(entries),
                "selected_tree_entry_count": len(selected_entries),
                "sparse_non_cone_patterns": patterns,
                "entries": entries,
            }
        )
        blob_manifests.append(
            {
                "candidate_id": candidate_id,
                "local_root": materialization["local_root"],
                "file_count": len(blob_rows),
                "total_size_bytes": total_bytes,
                "files": blob_rows,
            }
        )
        receipt_rows.append(
            {
                "candidate_id": candidate_id,
                "metadata_clone_state": metadata_state,
                "repository_url_expected": repository_url,
                "repository_url_observed": origin,
                "full_revision_expected": revision,
                "detached_head_observed": head,
                "git_tree": tree_id,
                "local_root": materialization["local_root"],
                "tree_entry_count": len(entries),
                "selected_tree_entry_count": len(selected_entries),
                "materialized_file_count": len(blob_rows),
                "materialized_total_size_bytes": total_bytes,
                "required_paths_verified": len(required_paths),
                "missing_required_path_count": 0,
                "selected_prohibited_artifact_count": 0,
                "selected_submodule_count": 0,
                "selected_symlink_count": 0,
                "selected_lfs_pointer_count": 0,
                "vendor_worktree_modification_count": 0,
                "status": "PASS_HASH_LOCKED_SOURCE_ONLY",
            }
        )
        log_rows.append(
            f"- {candidate_id}: origin and detached HEAD verified; tree {tree_id}; "
            f"{len(entries)} tree entries, {len(blob_rows)} materialized files, "
            f"{total_bytes} bytes; zero prohibited artifacts, submodules, symlinks, "
            "LFS pointers or worktree modifications."
        )

    output_root.mkdir(parents=True, exist_ok=False)
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    receipt = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-m0-materialization-receipt-1.0",
        "created_at": created_at,
        "stage_id": "R5-M0",
        "status": "PASS_TWO_OF_TWO_HASH_LOCKED_SOURCE_ONLY_READY_FOR_R5_M1",
        "candidate_count": 2,
        "candidates": receipt_rows,
        "scope_guards": {
            "named_repository_count": 2,
            "unlisted_repository_accessed": False,
            "release_or_source_archive_downloaded": False,
            "submodule_initialized": False,
            "git_lfs_object_downloaded": False,
            "dataset_or_example_dataset_bytes_acquired": False,
            "checkpoint_or_pretrained_asset_acquired": False,
            "package_installed": False,
            "environment_or_container_created": False,
            "vendor_source_modified": False,
            "vendor_source_executed": False,
            "preprocessing_training_evaluation_performed": False,
            "project_v5_test_opened": False,
        },
        "truth_state": TRUTH,
    }
    tree_manifest = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-m0-source-tree-manifest-1.0",
        "created_at": created_at,
        "stage_id": "R5-M0",
        "hash_semantics": "Git object IDs record immutable source identity; no blob size fetch was used during preflight.",
        "candidates": tree_manifests,
        "truth_state": TRUTH,
    }
    blob_manifest = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-m0-selected-blob-manifest-1.0",
        "created_at": created_at,
        "stage_id": "R5-M0",
        "hash_algorithm": "sha256_raw_bytes",
        "candidates": blob_manifests,
        "truth_state": TRUTH,
    }
    handoff = {
        "schema_version": "stage1e-rebaseline-v2-e4-r5-m0-materialization-handoff-1.0",
        "created_at": created_at,
        "stage_id": "R5-M0",
        "status": "READY_FOR_INDEPENDENT_R5_M1_SOURCE_AUDITS",
        "candidate_ids": [row["candidate_id"] for row in receipt_rows],
        "parallel_next_stages": ["R5-M1A", "R5-M1B"],
        "benchmark_admitted_candidate_count": 0,
        "dataset_environment_or_execution_authorized": False,
        "next_central_stage_after_audits": "R5-G1",
        "mandatory_user_checkpoint_before_data_environment_run": "R5-M2",
        "truth_state": TRUTH,
    }
    operation_log = "\n".join(
        [
            "# R5-M0 source-only materialization operation log",
            "",
            f"Created: {created_at}",
            "",
            "R5-S0 v2 passed before checkout. The preflight correction narrowed the",
            "RecBole sparse policy to exclude nested example-data files and corrected",
            "nonexistent RecBole-GNN paths. The initial Windows Schannel metadata-clone",
            "attempt failed before target creation; the OpenSSL retry materialized Git",
            "metadata only. No source blob was checked out before the correction.",
            "",
            "## Candidate receipts",
            "",
            *log_rows,
            "",
            "## Persistent boundary",
            "",
            "No dataset/checkpoint was acquired; no package/environment was created;",
            "vendor source was neither modified nor executed; preprocessing, training",
            "and evaluation were not run; project v5 TEST was not opened. Numeric",
            "targets remain provisional and invalid for the paper.",
            "",
        ]
    )
    payloads = {
        "materialization_receipt.json": receipt,
        "source_tree_manifest.json": tree_manifest,
        "selected_blob_manifest.json": blob_manifest,
        "materialization_handoff.json": handoff,
    }
    for filename, payload in payloads.items():
        (output_root / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    (output_root / "operation_log.md").write_text(
        operation_log,
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2), file=sys.stderr)
        sys.exit(1)
