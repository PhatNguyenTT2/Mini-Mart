#!/usr/bin/env python3
"""Offline fail-closed validator for the dormant Attempt-010 packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
PACKET_PARENT = "fe9f334e555639ed61781388421e8f8f7c228b46"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt010_admission_observation.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt010_admission_observation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt010_execution_authorization.json"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt010_static_packet.py"
PACKET = [CONTRACT, AUTHORIZATION, RUNNER, VALIDATOR]
OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_as/"
    "E4_R6PC2W_P1_attempt010_admission_observation"
)
FROZEN = {
    CONTROL / "e4_r6_pc2w_p1_attempt010_command_interface.py":
        "970f5b5269c36dc3f2e0e1639db591adbd4623aeb6f97b86e049957dde1a9559",
    CONTROL / "e4_r6_pc2w_p1_attempt010_command_interface_contract.json":
        "6f31ec175bbd142fb588379ba312e0fa16d66b905340879a4648a65b821ee429",
    CONTROL / "test_e4_r6_pc2w_p1_attempt010_command_interface.py":
        "faa6b3b5884482996b34303f6efc72a412b4fa3c8ad76c3bb3511b803890911a",
    CONTROL / "stage1e_legacy_source_cleanup_manifest.json":
        "7c618ef482e260a5b81207a8e6b70793a4afbf288dffa4af57e67fc77df1d45e",
    CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt009_pre_runtime_failure_receipt.json":
        "0e74e4f3d594a521fc4cee9b3ee2e2e5131b47246473d452ae55bfe5fddbda12",
}


class DuplicateKeyError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root must be object: {path.as_posix()}")
    return value


def git(repo: Path, *args: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=text,
    )
    if completed.returncode != 0:
        raise RuntimeError("read-only git command failed")
    return completed.stdout


def git_blob(repo: Path, revision: str, relative: Path) -> tuple[int, str]:
    payload = git(repo, "show", f"{revision}:{relative.as_posix()}", text=False)
    assert isinstance(payload, bytes)
    return len(payload), hashlib.sha256(payload).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_packet_state(repo: Path) -> tuple[str, str]:
    head = str(git(repo, "rev-parse", "HEAD")).strip().casefold()
    status = str(git(repo, "status", "--porcelain=v1", "--untracked-files=all")).splitlines()
    packet_names = sorted(path.as_posix() for path in PACKET)
    if head == PACKET_PARENT:
        expected_status = sorted(f" M {path}" for path in packet_names)
        require(sorted(status) == expected_status, "precommit dirty set is not exact four-file packet")
        return "PRECOMMIT_WORKTREE", head
    require(not status, "committed packet checkout must be clean")
    parents = str(git(repo, "rev-list", "--parents", "-n", "1", head)).split()
    require(len(parents) == 2 and parents[1].casefold() == PACKET_PARENT, "packet parent mismatch")
    delta = str(git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", head)).splitlines()
    require(sorted(delta) == sorted(f"M\t{path}" for path in packet_names), "packet commit delta mismatch")
    return "COMMITTED_PACKET", head


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    require(Path.cwd().resolve() == repo, "validator cwd mismatch")
    require((repo / VALIDATOR).resolve() == Path(__file__).resolve(), "validator path mismatch")

    mode, head = validate_packet_state(repo)
    contract = load_json(repo / CONTRACT)
    authorization = load_json(repo / AUTHORIZATION)
    interface_contract = load_json(repo / CONTROL / "e4_r6_pc2w_p1_attempt010_command_interface_contract.json")
    cleanup = load_json(repo / CONTROL / "stage1e_legacy_source_cleanup_manifest.json")
    failure = load_json(repo / CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt009_pre_runtime_failure_receipt.json")

    require(contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt010-admission-observation-contract-1.0", "contract schema mismatch")
    require(authorization.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt010-execution-authorization-1.0", "authorization schema mismatch")
    require(contract.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT010", "contract stage mismatch")
    require(authorization.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT010", "authorization stage mismatch")
    require(interface_contract.get("expected_test_count") == 10, "synthetic test contract mismatch")
    require(cleanup.get("cleanup_scope", {}).get("deleted_file_count") == 28, "cleanup manifest mismatch")
    require(failure.get("observed_failure", {}).get("matched_static_failure") == "exact original process argv mismatch", "Attempt-009 root-cause binding mismatch")
    require(contract.get("packet_entry_gate", {}).get("packet_files") == [path.as_posix() for path in PACKET], "packet file roster mismatch")
    require(contract.get("scope_boundary", {}).get("runtime_execution_authorized_now") is False, "runtime must remain denied")
    require(authorization.get("user_decision", {}).get("runtime_execution_authorized_now") is False, "authorization runtime boundary mismatch")
    require("RUN_ATTEMPT010_RUNNER" in authorization.get("not_authorized_now", []), "runner denial missing")
    truth = contract.get("truth_state", {})
    require(truth.get("RESULT_STATUS") == "NOT_RUN", "result status mismatch")
    require(truth.get("TEST_SET_OPENED") == "NO", "test-set boundary mismatch")
    require(truth.get("ACCEPTED_RESULT_ROWS") == 0, "accepted result rows mismatch")
    require(contract.get("model_policy", {}).get("fast_or_priority_allowed") is False, "fast tier forbidden")
    require(authorization.get("model_policy", {}).get("requested_service_tier") == "default", "standard tier binding missing")
    require(not (repo / OUTPUT).exists(), "immutable Attempt-010 output root already exists")

    frozen_facts = []
    for relative, expected_sha256 in sorted(FROZEN.items(), key=lambda item: item[0].as_posix()):
        blob_bytes, blob_sha256 = git_blob(repo, "HEAD", relative)
        require(blob_sha256 == expected_sha256, "frozen remediation Git blob mismatch")
        checkout = (repo / relative).read_bytes().replace(b"\r\n", b"\n")
        require(hashlib.sha256(checkout).hexdigest() == expected_sha256, "frozen remediation checkout drift")
        frozen_facts.append({"path": relative.as_posix(), "git_blob_bytes": blob_bytes, "git_blob_sha256": blob_sha256})

    runner_source = (repo / RUNNER).read_text(encoding="utf-8")
    validator_source = (repo / VALIDATOR).read_text(encoding="utf-8")
    compile(runner_source, RUNNER.as_posix(), "exec")
    compile(validator_source, VALIDATOR.as_posix(), "exec")
    for token in [
        "bind_exact_python_script_argv",
        "sys.orig_argv = list(_COMMAND_BINDING.normalized_argv)",
        "finally:",
        "sys.orig_argv = original",
        "previous._ORIGINAL_VALIDATE_FROZEN",
        "automatic_retry_count\": 0",
    ]:
        require(token in runner_source, f"runner control token missing: {token}")
    for forbidden in ["shell=True", "os.system(", "subprocess.Popen("]:
        require(forbidden not in runner_source, f"runner forbidden token present: {forbidden}")

    result = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt010-static-validation-result-1.0",
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT010",
        "validation_mode": mode,
        "validated_head": head,
        "packet_parent": PACKET_PARENT,
        "packet_files": [path.as_posix() for path in PACKET],
        "frozen_remediation_artifacts": frozen_facts,
        "synthetic_test_command_required_separately": True,
        "runtime_commands_executed": False,
        "docker_wsl_or_host_probe_commands_executed": False,
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "verdict": "READY_FOR_CENTRAL_STATIC_VALIDATION",
    }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
