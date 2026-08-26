#!/usr/bin/env python3
"""Offline static/synthetic validator for the dormant next-attempt packet."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
START = "4cfd9520c8e946aaef32d8f1bbb51e25f804e377"
R0 = "da18aa102567dcfef7296fafa223bcaef065e934"
BINDING = CONTROL / "e4_r6_pc2w_p1_gate_receipt_binding.py"
BINDING_CONTRACT = CONTROL / "e4_r6_pc2w_p1_gate_receipt_binding_contract.json"
TEST = CONTROL / "test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt011_admission_observation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt011_execution_authorization.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt011_admission_observation.py"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt011_static_packet.py"
R0_FILES = (
    BINDING,
    BINDING_CONTRACT,
    TEST,
    CONTRACT,
    AUTHORIZATION,
    RUNNER,
    VALIDATOR,
)
PACKET = (CONTRACT, AUTHORIZATION, RUNNER, VALIDATOR)
OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_at/"
    "E4_R6PC2W_P1_attempt011_admission_observation"
)
SUPPORT_SHA256 = {
    BINDING: "8a1ea9f854fbe81c4873b326db4a1a82b31c6557c4efb92c0e3332ecdddaa526",
    BINDING_CONTRACT: "784cd9639ae43f11bc4977155c6528c8f0f304ba9d4bcc4a394b1c93916f0e0b",
    TEST: "41e1c30a784368b713532899a86feec3fe538a1b85388621f7431a8c9eaa8c51",
}
FROZEN_INHERITED_SHA256 = {
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
    CONTROL / "e4_r6_pc2w_p1_attempt009_runtime_compatibility.py":
        "8148e6437af20d4c2b66f774adae102afe83583c7ed2b463340162beb6f342d7",
    CONTROL / "e4_r6_pc2w_p1_attempt009_runtime_compatibility_contract.json":
        "6a627d077af4389676ea458265bd8b93a132a606571fd515493dae2e4258b008",
    CONTROL / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py":
        "d486fbec952a8365828dc132d90fb8fc02cc4cd5811560c7541700054e02b1ea",
    CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt009_runtime_compatibility_revision3_validation_receipt.json":
        "c1ae7c3daf70041630b9a4c56c0241c5ce5104694a6fa53ee371a3d495ade102",
    CONTROL / "rebaseline_v2_e4_r6_pc2w_p1_attempt009_runtime_compatibility_revision3_fresh_independent_audit_receipt.json":
        "211de28607daf5e5e5e38a0d016ef6fa3a46d3cea88f566519bbfbc61629b451",
    CONTROL / "execute_e4_r6_pc2w_p1_attempt008_admission_observation.py":
        "c51c0fc6b0e089bb478fdc391979cfa0add8051f4723ff067ed81dd4c6630a89",
}
TEST_SUITES = (
    (TEST, 62, "attempt011_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt010_command_interface.py", 10, "retained_attempt010_command_interface"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py", 9, "retained_attempt009_runtime_compatibility"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_probe_contract.py", 8, "retained_attempt008_probe_contract"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py", 9, "retained_attempt008_safe_envelopes"),
)
MODEL_POLICY = {
    "requested_model": "gpt-5.6-sol",
    "requested_reasoning_effort": "high",
    "requested_service_tier": "default",
    "requested_display_tier": "Standard",
    "fast_or_priority_allowed": False,
    "actual_model": "UNOBSERVABLE",
    "actual_reasoning_effort": "UNOBSERVABLE",
    "actual_service_tier": "UNOBSERVABLE",
}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    require(completed.returncode == 0, "READ_ONLY_GIT_COMMAND_FAILED")
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8", errors="strict").strip()


def git_blob(repo: Path, revision: str, path: Path) -> bytes:
    value = git(repo, "cat-file", "blob", f"{revision}:{path.as_posix()}", binary=True)
    assert isinstance(value, bytes)
    return value


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: set[str] = set()
    for key, value in pairs:
        normalized = key.casefold()
        if key in result or normalized in folded:
            raise ValueError("duplicate JSON key")
        result[key] = value
        folded.add(normalized)
    return result


def strict_json(raw: bytes, path: Path) -> dict[str, Any]:
    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=strict_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON: {token}")
        ),
    )
    require(isinstance(value, dict), f"JSON_ROOT_NOT_OBJECT:{path.as_posix()}")
    return value


def normalized_checkout(path: Path) -> bytes:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in raw, f"BARE_CR:{path.as_posix()}")
    return raw


def commit_parent(repo: Path, revision: str) -> str:
    row = str(git(repo, "rev-list", "--parents", "-n", "1", revision)).split()
    require(len(row) == 2, f"COMMIT_NOT_SINGLE_PARENT:{revision}")
    return row[1]


def commit_delta(repo: Path, revision: str) -> list[str]:
    value = str(git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", revision))
    return value.splitlines() if value else []


def validate_commit_shapes(repo: Path) -> tuple[str, str]:
    require(commit_parent(repo, R0) == START, "R0_PARENT_MISMATCH")
    expected_r0 = sorted(f"A\t{path.as_posix()}" for path in R0_FILES)
    require(sorted(commit_delta(repo, R0)) == expected_r0, "R0_DELTA_NOT_EXACT_SEVEN_ADDS")
    head = str(git(repo, "rev-parse", "HEAD")).casefold()
    status_process = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
    )
    require(status_process.returncode == 0, "READ_ONLY_GIT_STATUS_FAILED")
    status = status_process.stdout.decode("utf-8", errors="strict").splitlines()
    packet_paths = sorted(path.as_posix() for path in PACKET)
    if head == R0:
        expected = sorted(f" M {path}" for path in packet_paths)
        require(sorted(status) == expected, "R1_DRAFT_NOT_EXACT_FOUR_MODIFICATIONS")
        return "R1_DIRTY_DRAFT_AT_R0", head
    require(status == [], "R1_COMMITTED_WORKTREE_NOT_CLEAN")
    require(commit_parent(repo, head) == R0, "R1_PARENT_MISMATCH")
    expected_delta = sorted(f"M\t{path}" for path in packet_paths)
    require(sorted(commit_delta(repo, head)) == expected_delta, "R1_DELTA_NOT_EXACT_FOUR_MODIFICATIONS")
    return "R1_COMMITTED_PACKET", head


def validate_frozen(repo: Path, head: str) -> list[dict[str, Any]]:
    facts = []
    for path, expected in sorted(
        {**SUPPORT_SHA256, **FROZEN_INHERITED_SHA256}.items(),
        key=lambda item: item[0].as_posix(),
    ):
        source_revision = R0 if path in SUPPORT_SHA256 else START
        source = git_blob(repo, source_revision, path)
        require(sha256_bytes(source) == expected, f"FROZEN_SOURCE_HASH_MISMATCH:{path.as_posix()}")
        current = git_blob(repo, head, path)
        require(current == source, f"FROZEN_POST_R0_DRIFT:{path.as_posix()}")
        require(normalized_checkout(repo / path) == source, f"FROZEN_CHECKOUT_DRIFT:{path.as_posix()}")
        facts.append(
            {
                "path": path.as_posix(),
                "git_blob_bytes": len(source),
                "git_blob_sha256": expected,
            }
        )
    return facts


def validate_packet_blobs(repo: Path, revision: str) -> list[dict[str, Any]]:
    facts = []
    for path in PACKET:
        raw = normalized_checkout(repo / path)
        if revision != R0:
            require(raw == git_blob(repo, revision, path), f"PACKET_POST_COMMIT_DRIFT:{path.as_posix()}")
        facts.append(
            {
                "path": path.as_posix(),
                "git_blob_bytes": len(raw),
                "git_blob_sha256": sha256_bytes(raw),
            }
        )
    return facts


def test_methods(path: Path) -> tuple[list[str], ast.Module, str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path.as_posix())
    names = sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    return names, tree, source


def case_id(name: str) -> str:
    match = re.match(r"^test_gr_(pos|c|a|j|l|cmd|nr|cl)_(\d{2})_", name)
    require(match is not None, f"ATTEMPT011_TEST_NAME_INVALID:{name}")
    assert match is not None
    return f"GR-{match.group(1).upper()}-{match.group(2)}"


def expected_case_ids() -> list[str]:
    groups = (("POS", 4), ("C", 10), ("A", 10), ("J", 7), ("L", 4), ("CMD", 13), ("NR", 5), ("CL", 9))
    return [f"GR-{group}-{index:02d}" for group, total in groups for index in range(1, total + 1)]


def validate_test_roster(repo: Path) -> tuple[list[str], list[dict[str, Any]]]:
    roster: list[str] = []
    suite_records = []
    for relative, expected_count, label in TEST_SUITES:
        names, tree, source = test_methods(repo / relative)
        require(len(names) == expected_count, f"TEST_COUNT_MISMATCH:{label}")
        decorators = [
            ast.unparse(decorator)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for decorator in node.decorator_list
        ]
        forbidden = ("skip", "xfail", "expectedFailure")
        require(not any(any(token in value for token in forbidden) for value in decorators), f"SKIP_OR_XFAIL:{label}")
        require("pytestmark" not in source and "pytest.mark.xfail" not in source, f"XFAIL_MARKER:{label}")
        if relative == TEST:
            roster = [case_id(name) for name in names]
            require(sorted(roster) == sorted(expected_case_ids()), "ATTEMPT011_CASE_ID_ROSTER_MISMATCH")
        suite_records.append({"suite": label, "tests": expected_count})
    require(sum(row[1] for row in ((path, count) for path, count, _ in TEST_SUITES)) == 98, "AGGREGATE_TEST_COUNT_MISMATCH")
    return sorted(roster), suite_records


def validate_sources(repo: Path) -> dict[str, Any]:
    binding_source = (repo / BINDING).read_text(encoding="utf-8")
    binding_contract_source = (repo / BINDING_CONTRACT).read_text(encoding="utf-8")
    runner_source = (repo / RUNNER).read_text(encoding="utf-8")
    retained_source = (
        repo / CONTROL / "execute_e4_r6_pc2w_p1_attempt008_admission_observation.py"
    ).read_text(encoding="utf-8")
    for path in (BINDING, TEST, RUNNER, VALIDATOR):
        ast.parse((repo / path).read_text(encoding="utf-8"), filename=path.as_posix())
    require(re.search(r"ATTEMPT[0-9]+", binding_source) is None, "GENERIC_MODULE_ATTEMPT_LITERAL")
    require(re.search(r"ATTEMPT[0-9]+", binding_contract_source) is None, "GENERIC_CONTRACT_ATTEMPT_LITERAL")
    binding_tree = ast.parse(binding_source)
    imported = [
        alias.name
        for node in ast.walk(binding_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ] + [
        node.module or ""
        for node in ast.walk(binding_tree)
        if isinstance(node, ast.ImportFrom)
    ]
    require(not any(re.search(r"attempt[0-9]+", name, re.IGNORECASE) for name in imported), "GENERIC_MODULE_ATTEMPT_IMPORT")
    require("GateReceiptSpec(" not in binding_source, "GENERIC_MODULE_MUTABLE_ATTEMPT_CONFIGURATION")
    retained_config = runner_source.index("previous.configure_attempt010_runner()")
    generic_install = runner_source.index("legacy.validate_gate_receipts = _validate_bound_gate_receipts")
    inherited_main = runner_source.index("return legacy.main()")
    require(retained_config < generic_install < inherited_main, "RUNNER_GENERIC_VALIDATOR_INSTALL_ORDER")
    require("legacy.validate_gate_receipts = previous.previous._validate_gate_receipts" not in runner_source, "STALE_GATE_PREDICATE_REACHABLE")
    frozen_gate = retained_source.index("frozen_upstream = validate_frozen_upstream")
    receipt_gate = retained_source.index("gate_receipts = validate_gate_receipts")
    mkdir = retained_source.index("output_root.mkdir")
    invoke = retained_source.index("def invoke(")
    require(frozen_gate < receipt_gate < mkdir < invoke, "PRE_RUNTIME_GATE_ORDER_INVALID")
    for forbidden in ("shell=True", "os.system(", "subprocess.Popen("):
        require(forbidden not in runner_source, f"RUNNER_FORBIDDEN_TOKEN:{forbidden}")
    return {
        "python_ast_files_passed": 4,
        "generic_attempt_literal_findings": 0,
        "generic_attempt_import_findings": 0,
        "attempt009_gate_predicate_reachable": False,
        "receipt_validation_before_output_root_and_invoke": True,
    }


def bytecode_inventory(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (len(raw), sha256_bytes(raw))
        for path in sorted(root.rglob("*.pyc"))
        for raw in [path.read_bytes()]
    }


def run_tests(repo: Path) -> list[dict[str, Any]]:
    results = []
    for relative, count, label in TEST_SUITES:
        command = [sys.executable, "-B", str(repo / relative)]
        completed = subprocess.run(
            command,
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
        )
        require(completed.returncode == 0, f"SYNTHETIC_TEST_FAILURE:{label}")
        results.append(
            {
                "suite": label,
                "tests_passed": count,
                "tests_total": count,
                "python_dash_b": True,
                "runtime_or_host_commands": 0,
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    require(Path.cwd().resolve() == repo, "VALIDATOR_CWD_MISMATCH")
    require(Path(str(git(repo, "rev-parse", "--show-toplevel"))).resolve() == repo, "REPOSITORY_ROOT_MISMATCH")
    require((repo / VALIDATOR).resolve() == Path(__file__).resolve(), "VALIDATOR_PATH_MISMATCH")
    require(not (repo / OUTPUT).exists(), "ATTEMPT011_OUTPUT_ROOT_ALREADY_EXISTS")

    mode, revision = validate_commit_shapes(repo)
    frozen_facts = validate_frozen(repo, revision)
    packet_facts = validate_packet_blobs(repo, revision)
    contract = strict_json(normalized_checkout(repo / CONTRACT), CONTRACT)
    authorization = strict_json(normalized_checkout(repo / AUTHORIZATION), AUTHORIZATION)
    strict_json(git_blob(repo, R0, BINDING_CONTRACT), BINDING_CONTRACT)
    require(contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt011-admission-observation-contract-1.0", "CONTRACT_SCHEMA_MISMATCH")
    require(authorization.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt011-execution-authorization-1.0", "AUTHORIZATION_SCHEMA_MISMATCH")
    require(contract.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT011", "CONTRACT_STAGE_MISMATCH")
    require(authorization.get("stage_id") == "E4-R6-PC2W-P1-ATTEMPT011", "AUTHORIZATION_STAGE_MISMATCH")
    require(contract.get("packet_entry_gate", {}).get("packet_files") == [path.as_posix() for path in PACKET], "PACKET_ROSTER_MISMATCH")
    require(contract.get("model_policy") == MODEL_POLICY, "CONTRACT_MODEL_POLICY_MISMATCH")
    require(authorization.get("model_policy") == MODEL_POLICY, "AUTHORIZATION_MODEL_POLICY_MISMATCH")
    require(contract.get("scope_boundary", {}).get("runtime_execution_authorized_now") is False, "CONTRACT_RUNTIME_BOUNDARY_WIDENED")
    require(authorization.get("user_decision", {}).get("runtime_execution_authorized_now") is False, "AUTHORIZATION_RUNTIME_BOUNDARY_WIDENED")
    require("RUN_OR_IMPORT_ATTEMPT011_RUNNER_ON_EXECUTION_PATH" in authorization.get("not_authorized_now", []), "RUNNER_DENIAL_MISSING")
    truth = contract.get("truth_state", {})
    require(truth.get("RESULT_STATUS") == "NOT_RUN", "RESULT_STATUS_WIDENED")
    require(truth.get("TEST_SET_OPENED") == "NO", "TEST_SET_BOUNDARY_WIDENED")
    require(truth.get("ACCEPTED_RESULT_ROWS") == 0, "ACCEPTED_RESULT_ROWS_WIDENED")

    roster, suite_roster = validate_test_roster(repo)
    source_checks = validate_sources(repo)
    pyc_before = bytecode_inventory(repo / CONTROL)
    test_results = run_tests(repo)
    pyc_after = bytecode_inventory(repo / CONTROL)
    require(pyc_after == pyc_before, "PYTHON_BYTECODE_INVENTORY_CHANGED")

    result = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt011-static-validation-result-1.0",
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT011",
        "validation_mode": mode,
        "validated_revision": revision,
        "r0_commit": R0,
        "r0_parent": START,
        "r0_exact_write_set": [path.as_posix() for path in R0_FILES],
        "r1_parent": R0,
        "r1_exact_write_set": [path.as_posix() for path in PACKET],
        "packet_artifacts": packet_facts,
        "immutable_artifacts": frozen_facts,
        "strict_json_files_passed": 3,
        "strict_json_files_total": 3,
        "source_checks": source_checks,
        "test_case_ids": roster,
        "test_suite_roster": suite_roster,
        "test_results": test_results,
        "aggregate_tests_passed": 98,
        "aggregate_tests_total": 98,
        "preexisting_python_bytecode_inventory": pyc_before,
        "post_python_bytecode_inventory": pyc_after,
        "new_or_modified_python_bytecode_files": 0,
        "command_inventory": {
            "python_dash_b_synthetic_static_test_processes": len(TEST_SUITES),
            "read_only_git_processes_only": True,
            "runner_imports_or_invocations": 0,
            "docker_commands": 0,
            "wsl_commands": 0,
            "powershell_host_probe_commands": 0,
            "real_sleeps": 0,
            "runtime_commands": 0,
            "automatic_retry_count": 0,
            "fallback_count": 0,
        },
        "output_root_absent": True,
        "runtime_commands_executed": False,
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "model_policy": MODEL_POLICY,
        "verdict": "READY_FOR_CENTRAL_STATIC_VALIDATION",
    }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
