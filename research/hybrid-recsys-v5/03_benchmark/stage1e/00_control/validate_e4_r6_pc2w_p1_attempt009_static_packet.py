#!/usr/bin/env python3
"""Offline, read-only static validator for dormant Attempt-009 Revision 2."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

CONTROL_RELATIVE = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt009_admission_observation.py"
CONTRACT_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt009_admission_observation_contract.json"
AUTHORIZATION_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt009_execution_authorization.json"
VALIDATOR_RELATIVE = CONTROL_RELATIVE / "validate_e4_r6_pc2w_p1_attempt009_static_packet.py"
PACKET_PARENT = "91466f7dd5a004cbcabfac61815f49c6fcef4606"
PACKET_RELATIVES = {
    RUNNER_RELATIVE,
    CONTRACT_RELATIVE,
    AUTHORIZATION_RELATIVE,
    VALIDATOR_RELATIVE,
}
OUTPUT_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ar/"
    "E4_R6PC2W_P1_attempt009_admission_observation"
)
LEGACY_RUNNER_RELATIVE = CONTROL_RELATIVE / "execute_e4_r6_pc2w_p1_attempt008_admission_observation.py"
LEGACY_RUNNER_SHA256 = "c51c0fc6b0e089bb478fdc391979cfa0add8051f4723ff067ed81dd4c6630a89"
COMPATIBILITY_RELATIVE = CONTROL_RELATIVE / "e4_r6_pc2w_p1_attempt009_runtime_compatibility.py"
COMPATIBILITY_TEST_RELATIVE = CONTROL_RELATIVE / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py"
POWERSHELL = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
EXPECTED_COMMAND_IDS = [
    "P00", "P01", "P02", "P03", "P04", "S00",
    "D00", "D01", "D02", "D03", "D04", "D05", "D06",
    "F00", "F01",
    "A00", "A01", "A02", "A03",
    "B00", "B01", "B02", "B03",
    "C00", "C01", "C02", "C03",
]
MODEL_POLICY = {
    "requested_model": "gpt-5.6-sol",
    "requested_reasoning_effort": "max",
    "requested_service_tier": "default",
    "requested_display_name": "Sol Max Standard",
    "fresh_audit_requested_model": "gpt-5.6-sol",
    "fresh_audit_requested_reasoning_effort": "xhigh",
    "fast_or_priority_allowed": False,
    "actual_model_reasoning_and_service_tier": "UNOBSERVABLE",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: set[str] = set()
    for key, value in pairs:
        normalized = key.casefold()
        if key in result or normalized in folded:
            raise ValueError("duplicate or casefold-duplicate JSON key")
        result[key] = value
        folded.add(normalized)
    return result


def canonical_lf_bytes(path: Path) -> bytes:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in raw:
        raise ValueError(f"bare carriage return: {path}")
    return raw


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        canonical_lf_bytes(path).decode("utf-8"),
        object_pairs_hook=strict_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {token}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def git_blob(repo_root: Path, revision: str, relative: Path) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{relative.as_posix()}"],
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=True,
    )
    return completed.stdout


def packet_facts(repo_root: Path, revision: str) -> list[dict[str, Any]]:
    facts = []
    for relative in sorted(PACKET_RELATIVES, key=lambda path: path.as_posix()):
        raw = git_blob(repo_root, revision, relative)
        facts.append({
            "path": relative.as_posix(),
            "git_blob_bytes": len(raw),
            "git_blob_sha256": sha256_bytes(raw),
        })
    return facts


def bytecode_facts(control_root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(control_root).as_posix(): (
            len(raw),
            sha256_bytes(raw),
        )
        for path in sorted(control_root.rglob("*.pyc"))
        for raw in [path.read_bytes()]
    }


def validate_json_contract(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    authorization = load_json(repo_root / AUTHORIZATION_RELATIVE)
    if contract.get("schema_version") != (
        "stage1e-e4-r6-pc2w-p1-attempt009-admission-observation-contract-2.0"
    ):
        raise RuntimeError("Attempt-009 contract schema mismatch")
    if authorization.get("schema_version") != (
        "stage1e-e4-r6-pc2w-p1-attempt009-execution-authorization-2.0"
    ):
        raise RuntimeError("Attempt-009 authorization schema mismatch")
    if contract.get("stage_id") != "E4-R6-PC2W-P1-ATTEMPT009" or authorization.get(
        "stage_id"
    ) != "E4-R6-PC2W-P1-ATTEMPT009":
        raise RuntimeError("Attempt-009 stage mismatch")
    if contract.get("model_policy") != MODEL_POLICY or authorization.get(
        "model_policy"
    ) != MODEL_POLICY:
        raise RuntimeError("Standard-only model policy mismatch")
    if contract.get("packet_entry_gate", {}).get("packet_parent_checkpoint") != PACKET_PARENT:
        raise RuntimeError("packet parent contract mismatch")
    if contract.get("packet_entry_gate", {}).get("packet_files") != sorted(
        path.as_posix() for path in PACKET_RELATIVES
    ):
        raise RuntimeError("packet file contract mismatch")
    if contract.get("controlled_observation_window", {}).get("command_ids") != EXPECTED_COMMAND_IDS:
        raise RuntimeError("command sequence contract mismatch")
    if contract.get("static_packet_verdict") != "READY_FOR_CENTRAL_STATIC_VALIDATION":
        raise RuntimeError("static packet verdict mismatch")
    decision = authorization.get("user_decision", {})
    if (
        decision.get("status") != "CONFIRMED"
        or decision.get("confirmed_scope")
        != "REMEDIATE_DOCKER_ERRORS_AND_PREPARE_ATTEMPT009_DORMANT_PACKET"
        or decision.get("runtime_execution_authorized_now") is not False
        or decision.get("exact_process_command_confirmed_now") is not False
        or decision.get("automatic_retry_authorized") is not False
    ):
        raise RuntimeError("authorization truth widened")
    future = authorization.get("future_exact_confirmation", {})
    if (
        future.get("required_after_central_validation_and_fresh_audit") is not True
        or future.get("execution_attempts_maximum") != 1
        or future.get("automatic_retry_count") != 0
        or future.get("fallback_count") != 0
    ):
        raise RuntimeError("future exact confirmation gate malformed")
    truth = authorization.get("truth_state", {})
    if (
        truth.get("RESULT_STATUS") != "NOT_RUN"
        or truth.get("TEST_SET_OPENED") != "NO"
        or truth.get("ACCEPTED_RESULT_ROWS") != 0
        or truth.get("benchmark_admission_opened") is not False
    ):
        raise RuntimeError("scientific truth state widened")
    return contract, authorization


def function_for_line(tree: ast.AST, line: int) -> str | None:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= line <= end:
                found.append((end - node.lineno, node.name))
    return min(found)[1] if found else None


def validate_runner_source(repo_root: Path) -> dict[str, int]:
    source = canonical_lf_bytes(repo_root / RUNNER_RELATIVE).decode("utf-8")
    tree = ast.parse(source, filename=RUNNER_RELATIVE.as_posix())
    required_fragments = (
        "PACKET_PARENT = \"91466f7dd5a004cbcabfac61815f49c6fcef4606\"",
        "invoke(\"P04\", \"POWERSHELL_MODULE_PREFLIGHT\", 60)",
        "compatibility.validate_powershell_module_preflight",
        "compatibility.windows_powershell_child_environment(os.environ)",
        "env=child_environment",
        "compatibility.wrap_process_identity_probe",
        "compatibility.wrap_tcp_identity_probe",
        "compatibility.wrap_desktop_file_identity_probe",
        "sanitize_docker_identity=compatibility.sanitize_docker_identity",
        "legacy.pre_start_snapshot = _pre_start_snapshot",
        "legacy.base.run_command = _run_command",
        "legacy.validate_gate_receipts = _validate_gate_receipts",
        "legacy.validate_frozen_upstream = _validate_frozen_upstream",
        "USER_CONFIRMED_EXACT_ATTEMPT009_REVISION2_PROCESS_COMMAND_AFTER_",
        "E4_R6PC2W_P1_attempt009_admission_observation",
    )
    missing = [fragment for fragment in required_fragments if fragment not in source]
    if missing:
        raise RuntimeError(f"runner required fragments missing: {missing}")
    subprocess_lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    if len(subprocess_lines) != 1 or function_for_line(tree, subprocess_lines[0]) != "_run_command":
        raise RuntimeError("runner subprocess boundary widened")
    main_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "legacy"
        and node.func.attr == "main"
    ]
    if len(main_calls) != 1 or function_for_line(tree, main_calls[0].lineno) != "main":
        raise RuntimeError("legacy runner invocation boundary invalid")
    if source.index('"P04",') > source.index('"S00",'):
        raise RuntimeError("P04 is not before S00")
    return {
        "python_ast_files_passed": 1,
        "subprocess_calls_in_exact_wrapper": 1,
        "legacy_main_calls_in_main_only": 1,
        "required_fragments_passed": len(required_fragments),
    }


def validate_frozen_legacy(repo_root: Path, revision: str) -> None:
    raw = git_blob(repo_root, revision, LEGACY_RUNNER_RELATIVE)
    if sha256_bytes(raw) != LEGACY_RUNNER_SHA256:
        raise RuntimeError("frozen Attempt-008 legacy runner drift")


def run_compatibility_regression(repo_root: Path) -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", str(repo_root / COMPATIBILITY_TEST_RELATIVE)],
        cwd=repo_root / CONTROL_RELATIVE,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError("Attempt-009 compatibility regression failed")


def powershell_ast_only(repo_root: Path) -> int:
    sys.path.insert(0, str(repo_root / CONTROL_RELATIVE))
    compatibility = importlib.import_module(
        "e4_r6_pc2w_p1_attempt009_runtime_compatibility"
    )
    scripts = [
        compatibility.POWERSHELL_MODULE_PREFLIGHT_QUERY,
        compatibility.wrap_process_identity_probe("ORIGINAL_PROCESS_PROBE"),
        compatibility.wrap_tcp_identity_probe("ORIGINAL_TCP_PROBE"),
        compatibility.wrap_desktop_file_identity_probe("ORIGINAL_DESKTOP_FILE_PROBE"),
    ]
    parser_command = (
        "$raw=[Console]::In.ReadToEnd();$items=ConvertFrom-Json $raw;"
        "$count=0;foreach($script in $items){$tokens=$null;$errors=$null;"
        "[System.Management.Automation.Language.Parser]::ParseInput([string]$script,"
        "[ref]$tokens,[ref]$errors)|Out-Null;if($errors.Count-ne 0){exit 7};$count++};"
        "if($count-ne 4){exit 8}"
    )
    completed = subprocess.run(
        [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", parser_command],
        input=json.dumps(scripts, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("PowerShell AST-only parse failed")
    return len(scripts)


def validate_packet_git_state(
    repo_root: Path, mode: str, packet_commit: str | None, expected_head: str | None
) -> tuple[str, list[dict[str, Any]]]:
    head = git(repo_root, "rev-parse", "HEAD").casefold()
    expected_paths = sorted(path.as_posix() for path in PACKET_RELATIVES)
    if mode == "draft":
        if head != PACKET_PARENT or packet_commit is not None:
            raise RuntimeError("draft mode requires exact packet parent HEAD")
        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repo_root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=True,
        )
        status = status_result.stdout.decode("utf-8", errors="strict").splitlines()
        observed = sorted(line[3:].replace("\\", "/") for line in status)
        if observed != expected_paths or any(not line.startswith(" M ") for line in status):
            raise RuntimeError("draft worktree must contain exactly four unstaged modified packet files")
        return head, []
    if packet_commit is None or not re.fullmatch(r"[0-9a-f]{40}", packet_commit):
        raise RuntimeError("committed mode requires full packet commit")
    commit = packet_commit.casefold()
    parents = git(repo_root, "rev-list", "--parents", "-n", "1", commit).split()
    if len(parents) != 2 or parents[1].casefold() != PACKET_PARENT:
        raise RuntimeError("packet commit parent mismatch")
    delta = git(
        repo_root, "diff-tree", "--no-commit-id", "--name-status", "-r", commit
    ).splitlines()
    expected_delta = sorted(f"M\t{path}" for path in expected_paths)
    if sorted(delta) != expected_delta:
        raise RuntimeError("packet commit must modify exactly four packet files")
    if expected_head is None or head != expected_head.casefold():
        raise RuntimeError("exact committed validation HEAD mismatch")
    if git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("committed validation worktree must be clean")
    git(repo_root, "merge-base", "--is-ancestor", commit, head)
    facts = packet_facts(repo_root, commit)
    for fact in facts:
        relative = Path(fact["path"])
        raw = canonical_lf_bytes(repo_root / relative)
        if len(raw) != fact["git_blob_bytes"] or sha256_bytes(raw) != fact["git_blob_sha256"]:
            raise RuntimeError("packet checkout differs from committed Git blob")
        if git_blob(repo_root, head, relative) != git_blob(repo_root, commit, relative):
            raise RuntimeError("packet artifact drift after packet commit")
    return commit, facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--mode", choices=("draft", "committed"), required=True)
    parser.add_argument("--packet-commit")
    parser.add_argument("--expected-head")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if Path(git(repo_root, "rev-parse", "--show-toplevel")).resolve() != repo_root:
        raise RuntimeError("repository root mismatch")
    if Path.cwd().resolve() != repo_root:
        raise RuntimeError("validator working directory mismatch")
    if (repo_root / OUTPUT_RELATIVE).exists():
        raise RuntimeError("Attempt-009 immutable output root already exists")
    control_root = repo_root / CONTROL_RELATIVE
    pycache_before = bytecode_facts(control_root)

    revision, facts = validate_packet_git_state(
        repo_root, args.mode, args.packet_commit, args.expected_head
    )
    contract, authorization = validate_json_contract(repo_root)
    source_checks = validate_runner_source(repo_root)
    ast.parse(
        canonical_lf_bytes(repo_root / VALIDATOR_RELATIVE).decode("utf-8"),
        filename=VALIDATOR_RELATIVE.as_posix(),
    )
    validate_frozen_legacy(repo_root, "HEAD")
    run_compatibility_regression(repo_root)
    powershell_scripts = powershell_ast_only(repo_root)
    pycache_after = bytecode_facts(control_root)
    if pycache_after != pycache_before:
        raise RuntimeError("Python bytecode set changed during validation")

    result = {
        "verdict": "READY_FOR_CENTRAL_STATIC_VALIDATION",
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT009",
        "mode": args.mode,
        "validated_revision": revision,
        "packet_parent": PACKET_PARENT,
        "packet_artifacts": facts,
        "strict_json_files_passed": 2,
        "strict_json_files_total": 2,
        "python_ast_files_passed": source_checks["python_ast_files_passed"] + 1,
        "python_ast_files_total": 2,
        "compatibility_tests_passed": 9,
        "compatibility_tests_total": 9,
        "powershell_ast_scripts_passed": powershell_scripts,
        "powershell_ast_scripts_total": 4,
        "p04_before_s00": True,
        "runtime_commands_executed": False,
        "runner_imported_or_invoked": False,
        "docker_commands_executed": 0,
        "wsl_commands_executed": 0,
        "host_probe_executions": 0,
        "preexisting_python_bytecode_files": len(pycache_before),
        "new_or_modified_python_bytecode_files": 0,
        "automatic_retry_count": 0,
        "fallback_count": 0,
        "benchmark_admission_opened": False,
        "result_status": "NOT_RUN",
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
        "contract_authorization_model_policy_equal": contract["model_policy"]
        == authorization["model_policy"],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
