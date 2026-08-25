#!/usr/bin/env python3
"""Read-only offline validator for the dormant Attempt-008 packet."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
PACKET_PARENT = "b973ed673a314d6223265712b95d2a7ce51b02f3"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt008_admission_observation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt008_execution_authorization.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt008_admission_observation.py"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt008_static_packet.py"
PACKET_FILES = {CONTRACT, AUTHORIZATION, RUNNER, VALIDATOR}
OUTPUT_ROOT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_aq/"
    "E4_R6PC2W_P1_attempt008_admission_observation"
)
EXPECTED_COMMAND_IDS = [
    "P00", "P01", "P02", "P03", "S00", "D00", "D01", "D02",
    "D03", "D04", "D05", "D06", "F00", "F01", "A00", "A01",
    "A02", "A03", "B00", "B01", "B02", "B03", "C00", "C01",
    "C02", "C03",
]
EXPECTED_OUTPUT_FILES = {
    "admission_observation.json",
    "command_receipts.json",
    "execution_receipt.json",
    "handoff.json",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(repo_root: Path, *args: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        shell=False,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    return completed.stdout.strip() if text else completed.stdout


def git_blob(repo_root: Path, revision: str, relative: Path) -> bytes:
    return git(repo_root, "show", f"{revision}:{relative.as_posix()}", text=False)


def strict_json_bytes(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("BOM or carriage return forbidden")
    text = raw.decode("utf-8", errors="strict")

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        folded: set[str] = set()
        for key, value in pairs:
            if key in result or key.casefold() in folded:
                raise ValueError("duplicate or casefold-duplicate key")
            result[key] = value
            folded.add(key.casefold())
        return result

    value = json.loads(
        text,
        object_pairs_hook=pairs_hook,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite constant: {token}")
        ),
    )

    def reject_nonfinite(node: Any) -> None:
        if isinstance(node, float) and not math.isfinite(node):
            raise ValueError("nonfinite number")
        if isinstance(node, dict):
            for item in node.values():
                reject_nonfinite(item)
        elif isinstance(node, list):
            for item in node:
                reject_nonfinite(item)

    reject_nonfinite(value)
    return value


def assigned_literal(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                try:
                    return ast.literal_eval(node.value)
                except Exception:
                    return None
    return None


def imported_aliases(tree: ast.AST) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                result[item.asname or item.name] = item.name
    return result


def duplicate_literal_dict_keys(tree: ast.AST) -> list[str]:
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys: list[str] = []
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.append(key.value)
        if len(keys) != len(set(keys)):
            findings.append("exact")
        folded = [key.casefold() for key in keys]
        if len(folded) != len(set(folded)):
            findings.append("casefold")
    return findings


def function_node(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError(f"function missing: {name}")


def invoke_ids(node: ast.AST) -> list[str]:
    result: list[str] = []
    for item in ast.walk(node):
        if not isinstance(item, ast.Call) or not isinstance(item.func, ast.Name):
            continue
        if item.func.id == "invoke" and item.args and isinstance(item.args[0], ast.Constant):
            if isinstance(item.args[0].value, str):
                result.append(item.args[0].value)
    return result


def nested_cleanup_finally_ok(tree: ast.AST) -> bool:
    main = function_node(tree, "main")
    for outer in ast.walk(main):
        if not isinstance(outer, ast.Try):
            continue
        outer_final_ids = invoke_ids(ast.Module(body=outer.finalbody, type_ignores=[]))
        if "F00" not in outer_final_ids or "F01" not in outer_final_ids:
            continue
        for inner in ast.walk(ast.Module(body=outer.finalbody, type_ignores=[])):
            if isinstance(inner, ast.Try):
                body_ids = invoke_ids(ast.Module(body=inner.body, type_ignores=[]))
                final_ids = invoke_ids(ast.Module(body=inner.finalbody, type_ignores=[]))
                if "F00" in body_ids and "F01" in final_ids:
                    return True
    return False


def status_paths(repo_root: Path) -> set[Path]:
    raw = str(git(repo_root, "status", "--porcelain=v1", "--untracked-files=all"))
    paths: set[Path] = set()
    for line in raw.splitlines():
        if not line:
            continue
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.add(Path(value.replace("\\", "/")))
    return paths


def validate(repo_root: Path, packet_commit: str | None) -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    head = str(git(repo_root, "rev-parse", "HEAD"))
    mode = "committed" if packet_commit else "draft"
    if packet_commit:
        packet_commit = str(git(repo_root, "rev-parse", packet_commit))
        parents = str(git(repo_root, "rev-list", "--parents", "-n", "1", packet_commit)).split()
        check("packet_one_parent", len(parents) == 2)
        check("packet_parent_exact", len(parents) == 2 and parents[1] == PACKET_PARENT)
        changed = {
            Path(value)
            for value in str(
                git(repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", packet_commit)
            ).splitlines()
            if value
        }
        check("packet_exact_four_file_delta", changed == PACKET_FILES)
        check("packet_ancestor_of_head", subprocess.run(
            ["git", "merge-base", "--is-ancestor", packet_commit, head],
            cwd=repo_root,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0)
        for relative in PACKET_FILES:
            check(
                f"checkout_matches_packet:{relative.name}",
                (repo_root / relative).read_bytes() == git_blob(repo_root, packet_commit, relative),
            )
    else:
        check("draft_head_is_packet_parent", head == PACKET_PARENT)
        check("draft_exact_four_file_status", status_paths(repo_root) == PACKET_FILES)

    check("output_root_absent", not (repo_root / OUTPUT_ROOT).exists())
    for relative in PACKET_FILES:
        check(f"packet_file_present:{relative.name}", (repo_root / relative).is_file())
        raw = (repo_root / relative).read_bytes()
        check(f"canonical_lf:{relative.name}", b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"))

    contract = strict_json_bytes((repo_root / CONTRACT).read_bytes())
    authorization = strict_json_bytes((repo_root / AUTHORIZATION).read_bytes())
    check("contract_schema", contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt008-admission-observation-contract-1.0")
    check("authorization_schema", authorization.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt008-execution-authorization-1.0")
    check("stage_ids", contract.get("stage_id") == authorization.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT008")
    check("contract_packet_parent", contract.get("packet_entry_gate", {}).get("packet_parent_checkpoint") == PACKET_PARENT)
    check("contract_packet_files", set(map(Path, contract.get("packet_entry_gate", {}).get("packet_files", []))) == PACKET_FILES)
    check("runtime_denied", contract.get("scope_boundary", {}).get("runtime_execution_authorized_now") is False and authorization.get("user_decision", {}).get("runtime_execution_authorized_now") is False)
    check("exact_confirmation_absent", contract.get("scope_boundary", {}).get("exact_command_confirmation_received_now") is False and authorization.get("user_decision", {}).get("exact_process_command_confirmed_now") is False)
    check("one_shot", contract.get("packet_entry_gate", {}).get("execution_attempts_maximum") == 1)
    check("no_retry_contract", contract.get("packet_entry_gate", {}).get("automatic_retry_count") == 0 and authorization.get("future_exact_confirmation", {}).get("automatic_retry_count") == 0)
    check("truth_not_run", contract.get("truth_state", {}).get("RESULT_STATUS") == authorization.get("truth_state", {}).get("RESULT_STATUS") == "NOT_RUN")
    check("truth_test_closed", contract.get("truth_state", {}).get("TEST_SET_OPENED") == authorization.get("truth_state", {}).get("TEST_SET_OPENED") == "NO")
    check("truth_rows_zero", contract.get("truth_state", {}).get("ACCEPTED_RESULT_ROWS") == authorization.get("truth_state", {}).get("ACCEPTED_RESULT_ROWS") == 0)
    check("fast_prohibited", contract.get("model_policy", {}).get("fast_or_priority_allowed") is False and authorization.get("model_policy", {}).get("fast_or_priority_allowed") is False)

    runner_raw = (repo_root / RUNNER).read_bytes()
    runner_source = runner_raw.decode("utf-8")
    runner_tree = ast.parse(runner_source)
    check("runner_no_duplicate_literal_dict_keys", not duplicate_literal_dict_keys(runner_tree))
    aliases = imported_aliases(runner_tree)
    check("runner_imports_r1_parser", aliases.get("parser_v2") == "e4_r6_pc2w_p1_attempt008_probe_contract")
    check("runner_imports_r2_probes", aliases.get("probes_v2") == "e4_r6_pc2w_p1_attempt008_safe_probe_envelopes")
    check("runner_packet_parent", assigned_literal(runner_tree, "PACKET_PARENT") == PACKET_PARENT)
    check("runner_command_ids", assigned_literal(runner_tree, "EXPECTED_COMMAND_IDS") == EXPECTED_COMMAND_IDS)
    check("runner_output_files", set(assigned_literal(runner_tree, "EXPECTED_OUTPUT_FILES") or []) == EXPECTED_OUTPUT_FILES)
    check("runner_output_root", "wave_aq/" in runner_source and "E4_R6PC2W_P1_attempt008_admission_observation" in runner_source)
    check("runner_safe_query_bindings", all(token in runner_source for token in (
        "PROCESS_IDENTITY_QUERY = probes_v2.PROCESS_IDENTITY_QUERY_V2",
        "TCP_IDENTITY_QUERY = probes_v2.TCP_IDENTITY_QUERY_V2",
        "DOCKER_DESKTOP_FILE_IDENTITY_QUERY = probes_v2.DOCKER_DESKTOP_FILE_IDENTITY_QUERY_V2",
    )))
    check("runner_no_legacy_identity_validators", all(token not in runner_source for token in (
        "def parse_rfc3339_utc", "def validate_rich_process_envelope",
        "def validate_rich_tcp_envelope", "def validate_desktop_file_identity",
        "def sanitize_docker_identity",
    )))
    check("runner_uses_structured_process_probe", "probes_v2.validate_process_probe_envelope" in runner_source)
    check("runner_uses_structured_tcp_probe", "probes_v2.validate_tcp_probe_envelope" in runner_source)
    check("runner_uses_structured_file_probe", "probes_v2.validate_desktop_file_probe_envelope" in runner_source)
    check("runner_uses_r1_docker_parser", "parser_v2.sanitize_docker_identity" in runner_source)
    check("runner_structured_identity_failures", all(token in runner_source for token in (
        "identity_failures: list[dict[str, Any]]", "record_identity_failure",
        "identity_failures_absent",
    )))
    check("runner_no_duplicate_wsl_shutdown_pass_key", runner_source.count('"wsl_shutdown_succeeded":') == 1)
    check("runner_nested_cleanup_finally", nested_cleanup_finally_ok(runner_tree))
    check("runner_prestart_ids", invoke_ids(function_node(runner_tree, "pre_start_snapshot")) == ["P00", "P01", "P02", "P03"])
    main_ids = invoke_ids(function_node(runner_tree, "main"))
    check("runner_main_window_ids", all(main_ids.count(value) == 1 for value in ("S00", "D00", "D01", "D02", "D03", "D04", "D05", "D06", "F00", "F01")))
    check("runner_no_direct_subprocess_or_network_import", not any(name in aliases.values() for name in ("subprocess", "requests", "urllib", "socket")))
    check("runner_truth_closed_literals", all(token in runner_source for token in (
        '"RESULT_STATUS": "NOT_RUN"', '"TEST_SET_OPENED": "NO"',
        '"ACCEPTED_RESULT_ROWS": 0', '"benchmark_admission_opened": False',
    )))
    check("runner_no_auto_retry", '"automatic_retry_count": 0' in runner_source and '"fallback_count": 0' in runner_source)
    check("runner_exact_output_writes", all(f'write_json(output_root / "{name}"' in runner_source for name in EXPECTED_OUTPUT_FILES))

    frozen = assigned_literal(runner_tree, "FROZEN_UPSTREAM_SHA256_LITERAL")
    check("runner_frozen_map_is_dict", isinstance(frozen, dict))
    check("runner_frozen_map_count", isinstance(frozen, dict) and len(frozen) == 15)
    if isinstance(frozen, dict):
        for raw_path, expected_hash in frozen.items():
            relative = Path(raw_path)
            blob = git_blob(repo_root, PACKET_PARENT, relative)
            check(f"frozen_hash:{relative.name}", sha256_bytes(blob) == expected_hash)
            check(f"frozen_checkout:{relative.name}", (repo_root / relative).read_bytes() == blob)
    check("runner_frozen_state_literal", "stage1e_rebaseline_v2_r6_pc2w_p1_attempt008_r2_safe_probe_envelopes_" in runner_source and "complete_r3_dormant_runtime_packet_design" in runner_source)
    check("runner_frozen_r1_verdict", "PASS_PC2W_P1_ATTEMPT008_R1_SYNTHETIC_PROBE_PARSER_REMEDIATION" in runner_source)
    check("runner_frozen_r2_verdict", "PASS_PC2W_P1_ATTEMPT008_R2_SAFE_PROBE_ENVELOPES_STATIC_SYNTHETIC" in runner_source)

    validator_source = (repo_root / VALIDATOR).read_text(encoding="utf-8")
    validator_tree = ast.parse(validator_source)
    check("validator_no_duplicate_literal_dict_keys", not duplicate_literal_dict_keys(validator_tree))
    validator_imports = imported_aliases(validator_tree)
    check("validator_does_not_import_runner", "execute_e4_r6_pc2w_p1_attempt008_admission_observation" not in validator_imports.values())
    subprocess_calls = [
        node for node in ast.walk(validator_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    ]
    check("validator_subprocess_calls_are_git_only", bool(subprocess_calls) and all(
        node.args
        and isinstance(node.args[0], ast.List)
        and node.args[0].elts
        and isinstance(node.args[0].elts[0], ast.Constant)
        and node.args[0].elts[0].value == "git"
        for node in subprocess_calls
    ))

    pycache = repo_root / CONTROL / "__pycache__"
    generated = [] if not pycache.exists() else [
        path.name for path in pycache.iterdir()
        if "attempt008" in path.name and path.suffix == ".pyc"
    ]
    check("no_attempt008_bytecode", not generated)

    failures = [name for name, passed in checks if not passed]
    return {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt008-static-validation-result-1.0",
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT008",
        "mode": mode,
        "packet_parent": PACKET_PARENT,
        "packet_commit": packet_commit,
        "head": head,
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failure_count": len(failures),
        "failures": failures,
        "runtime_commands_executed": False,
        "runner_imported_or_invoked": False,
        "verdict": (
            "PASS_PC2W_P1_ATTEMPT008_STATIC_PACKET"
            if not failures else "FAIL_CLOSED_PC2W_P1_ATTEMPT008_STATIC_PACKET"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--packet-commit")
    args = parser.parse_args()
    result = validate(Path(args.repo_root).resolve(), args.packet_commit)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
