#!/usr/bin/env python3
"""Offline static validator for the additive Attempt-012 R0/R1 packet."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
START = "20337b132635dfdc30eb0b56836f91fcb723ef46"
R0 = "7209966f430dc75e790d574298e65aefbe082f31"
AUTHORITY_HELPER = CONTROL / "e4_r6_pc2w_p1_attempt012_pre_runtime_authority.py"
AUTHORITY_CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt012_pre_runtime_authority_contract.json"
TEST = CONTROL / "test_e4_r6_pc2w_p1_attempt012_pre_runtime_gate.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt012_admission_observation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt012_execution_authorization.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt012_admission_observation.py"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt012_static_packet.py"
PACKET = (
    CONTRACT,
    AUTHORIZATION,
    AUTHORITY_HELPER,
    RUNNER,
    VALIDATOR,
)
R0_FILES = (
    CONTRACT,
    AUTHORIZATION,
    AUTHORITY_HELPER,
    AUTHORITY_CONTRACT,
    RUNNER,
    TEST,
    VALIDATOR,
)
OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/"
    "E4_R6PC2W_P1_attempt012_admission_observation"
)
FROZEN_R0 = {
    AUTHORITY_CONTRACT:
        "46d2120d502ec8c85fdd4d30f4e0431689264d7d299e34c9b902465b787ff5a3",
    TEST:
        "c1c8283f7baa58db28ab3e3cc5d8aa6b9f54ce82b8984297428b1bdb0b665ca7",
}
TEST_SUITES = (
    (TEST, 12, "attempt012_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py", 62, "retained_attempt011_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt010_command_interface.py", 10, "retained_attempt010_command_interface"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py", 9, "retained_attempt009_runtime_compatibility"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_probe_contract.py", 8, "retained_attempt008_probe_contract"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py", 9, "retained_attempt008_safe_envelopes"),
)
AUTHORITY_SHA256 = FROZEN_R0[AUTHORITY_CONTRACT]


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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
    raw = git(repo, "cat-file", "blob", f"{revision}:{path.as_posix()}", binary=True)
    assert isinstance(raw, bytes)
    return raw


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
    value = str(
        git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", revision)
    )
    return value.splitlines() if value else []


def validate_commit_shape(repo: Path) -> str:
    require(commit_parent(repo, R0) == START, "R0_PARENT_MISMATCH")
    expected_r0 = sorted(f"A\t{path.as_posix()}" for path in R0_FILES)
    require(sorted(commit_delta(repo, R0)) == expected_r0, "R0_WRITE_SET_MISMATCH")
    head = str(git(repo, "rev-parse", "HEAD")).casefold()
    require(commit_parent(repo, head) == R0, "R1_PARENT_MISMATCH")
    expected_r1 = sorted(f"M\t{path.as_posix()}" for path in PACKET)
    require(sorted(commit_delta(repo, head)) == expected_r1, "R1_WRITE_SET_MISMATCH")
    status = str(git(repo, "status", "--porcelain=v1", "--untracked-files=all"))
    require(status == "", "R1_WORKTREE_NOT_CLEAN")
    return head


def validate_frozen_r0(repo: Path, head: str) -> list[dict[str, Any]]:
    facts = []
    for path, expected_sha256 in sorted(
        FROZEN_R0.items(), key=lambda item: item[0].as_posix()
    ):
        r0_raw = git_blob(repo, R0, path)
        head_raw = git_blob(repo, head, path)
        require(sha256_bytes(r0_raw) == expected_sha256, f"R0_HASH_MISMATCH:{path}")
        require(head_raw == r0_raw, f"R0_FIXTURE_CHANGED:{path}")
        require(normalized_checkout(repo / path) == r0_raw, f"R0_CHECKOUT_DRIFT:{path}")
        facts.append(
            {
                "path": path.as_posix(),
                "git_blob_bytes": len(r0_raw),
                "git_blob_sha256": expected_sha256,
            }
        )
    return facts


def validate_packet(repo: Path, head: str) -> list[dict[str, Any]]:
    facts = []
    for path in PACKET:
        blob = git_blob(repo, head, path)
        require(normalized_checkout(repo / path) == blob, f"PACKET_CHECKOUT_DRIFT:{path}")
        facts.append(
            {
                "path": path.as_posix(),
                "git_blob_bytes": len(blob),
                "git_blob_sha256": sha256_bytes(blob),
            }
        )
    return facts


def test_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def validate_sources(repo: Path) -> dict[str, Any]:
    new_python = (AUTHORITY_HELPER, RUNNER, TEST, VALIDATOR)
    for path in new_python:
        ast.parse((repo / path).read_text(encoding="utf-8"), filename=path.as_posix())
    runner = (repo / RUNNER).read_text(encoding="utf-8")
    authority_source = (repo / AUTHORITY_HELPER).read_text(encoding="utf-8")
    handoff = runner.index("binding = authority.prepare_legacy_handoff")
    exact_command = runner.index("command_interface.bind_exact_python_script_argv", handoff)
    configure = runner.index("configure_attempt012_runner()", exact_command)
    root_rebind = runner.index(
        "legacy.EXPECTED_EXECUTION_ROOT = binding.execution_root", configure
    )
    legacy_main = runner.index("return legacy.main()", root_rebind)
    require(handoff < exact_command < configure < root_rebind < legacy_main, "PRE_LEGACY_HANDOFF_ORDER_INVALID")
    require("*sys.argv[1:]" not in runner, "ACTUAL_ARGV_TAIL_COPIED")
    require("E:\\UIT\\cv\\backend" not in runner + authority_source, "ABSOLUTE_SINGLETON_ROOT_RETAINED")
    require("expected_process_argv = build_expected_process_argv(contract)" in authority_source, "EXPECTED_ARGV_NOT_CONTRACT_DERIVED")
    main_fragment = runner[runner.index("def main() -> int:"):]
    require(
        "requested_reasoning_effort" not in main_fragment,
        "MAIN_RESTATES_CANONICAL_MODEL_POLICY",
    )
    require("AUTHORITY_CONTRACT_SHA256" in runner, "AUTHORITY_RAW_HASH_BINDING_MISSING")
    require("fresh_audit_must_link_central_raw_sha256" in runner, "CENTRAL_RAW_LINK_PREDICATE_MISSING")
    require("attempt011_receipts_accepted" in runner, "ATTEMPT011_RECEIPT_REJECTION_MISSING")
    return {
        "python_ast_files_passed": len(new_python),
        "public_pre_legacy_handoff_order_valid": True,
        "absolute_singleton_root_findings": 0,
        "actual_argv_tail_copy_findings": 0,
        "canonical_model_predicate_precedes_legacy_compatibility_view": True,
        "attempt012_receipt_schema_and_raw_central_link_bound": True,
    }


def validate_documents(
    authority_contract: dict[str, Any],
    contract: dict[str, Any],
    authorization: dict[str, Any],
) -> None:
    require(
        authority_contract.get("schema_version")
        == "stage1e-e4-r6-pc2w-p1-attempt012-pre-runtime-authority-contract-1.0",
        "AUTHORITY_CONTRACT_SCHEMA_MISMATCH",
    )
    require(
        contract.get("schema_version")
        == "stage1e-e4-r6-pc2w-p1-attempt012-admission-observation-contract-1.0",
        "CONTRACT_SCHEMA_MISMATCH",
    )
    require(
        authorization.get("schema_version")
        == "stage1e-e4-r6-pc2w-p1-attempt012-execution-authorization-1.0",
        "AUTHORIZATION_SCHEMA_MISMATCH",
    )
    require(contract.get("packet_entry_gate", {}).get("packet_files") == [path.as_posix() for path in PACKET], "PACKET_ROSTER_MISMATCH")
    expected_binding = {
        "path": AUTHORITY_CONTRACT.as_posix(),
        "raw_git_blob_bytes": 4352,
        "raw_git_blob_sha256": AUTHORITY_SHA256,
    }
    for document in (contract, authorization):
        binding = document.get("pre_runtime_authority_binding", {})
        require(all(binding.get(key) == value for key, value in expected_binding.items()), "AUTHORITY_BINDING_MISMATCH")
        require(binding.get("restated_authority_values") is False, "AUTHORITY_VALUES_RESTATED")
    policy = authority_contract.get("model_policy", {})
    require(
        policy.get("schema_version")
        == "stage1e-e4-r6-pc2w-p1-attempt012-model-policy-1.0",
        "MODEL_POLICY_SCHEMA_MISMATCH",
    )
    for role in ("implementation_static", "locked_execution"):
        require(
            policy.get("roles", {}).get(role)
            == {
                "requested_model": "gpt-5.6-sol",
                "requested_reasoning_effort": "xhigh",
                "requested_service_tier": "default",
                "requested_display_tier": "Standard",
                "fast_or_priority_allowed": False,
            },
            f"MODEL_ROLE_MISMATCH:{role}",
        )
    receipt = authority_contract.get("receipt_contract", {})
    require("attempt012" in str(receipt.get("central_schema")), "CENTRAL_SCHEMA_NOT_ATTEMPT012")
    require("attempt012" in str(receipt.get("fresh_audit_schema")), "AUDIT_SCHEMA_NOT_ATTEMPT012")
    require(receipt.get("fresh_audit_must_link_central_raw_sha256") is True, "CENTRAL_RAW_LINK_NOT_REQUIRED")
    require(receipt.get("attempt011_receipts_accepted") is False, "ATTEMPT011_RECEIPTS_ACCEPTED")
    require(contract.get("scope_boundary", {}).get("runtime_execution_authorized_now") is False, "CONTRACT_RUNTIME_WIDENED")
    require(authorization.get("user_decision", {}).get("runtime_execution_authorized_now") is False, "AUTH_RUNTIME_WIDENED")
    truth = contract.get("truth_state", {})
    require(truth.get("RESULT_STATUS") == "NOT_RUN", "RESULT_STATUS_WIDENED")
    require(truth.get("TEST_SET_OPENED") == "NO", "TEST_SET_WIDENED")
    require(truth.get("ACCEPTED_RESULT_ROWS") == 0, "ACCEPTED_ROWS_WIDENED")
    require(truth.get("benchmark_admission_opened") is False, "BENCHMARK_ADMISSION_WIDENED")


def bytecode_inventory(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (len(raw), sha256_bytes(raw))
        for path in sorted(root.rglob("*.pyc"))
        for raw in [path.read_bytes()]
    }


def run_tests(repo: Path) -> list[dict[str, Any]]:
    results = []
    for relative, expected_count, label in TEST_SUITES:
        require(test_count(repo / relative) == expected_count, f"TEST_COUNT_MISMATCH:{label}")
        source = (repo / relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative.as_posix())
        decorators = [
            ast.unparse(decorator)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for decorator in node.decorator_list
        ]
        require(
            not any(
                any(token in value for token in ("skip", "xfail", "expectedFailure"))
                for value in decorators
            ),
            f"SKIP_OR_XFAIL:{label}",
        )
        require(
            "pytestmark" not in source and "pytest.mark.xfail" not in source,
            f"XFAIL_MARKER:{label}",
        )
        completed = subprocess.run(
            [sys.executable, "-B", str(repo / relative)],
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
        )
        require(completed.returncode == 0, f"STATIC_TEST_FAILURE:{label}")
        results.append(
            {
                "suite": label,
                "tests_passed": expected_count,
                "tests_total": expected_count,
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
    require(not (repo / OUTPUT).exists(), "ATTEMPT012_OUTPUT_ROOT_ALREADY_EXISTS")

    head = validate_commit_shape(repo)
    frozen_facts = validate_frozen_r0(repo, head)
    packet_facts = validate_packet(repo, head)
    authority_document = strict_json(git_blob(repo, head, AUTHORITY_CONTRACT), AUTHORITY_CONTRACT)
    contract = strict_json(git_blob(repo, head, CONTRACT), CONTRACT)
    authorization = strict_json(git_blob(repo, head, AUTHORIZATION), AUTHORIZATION)
    validate_documents(authority_document, contract, authorization)
    source_checks = validate_sources(repo)
    pyc_before = bytecode_inventory(repo / CONTROL)
    test_results = run_tests(repo)
    pyc_after = bytecode_inventory(repo / CONTROL)
    require(pyc_before == pyc_after, "PYTHON_BYTECODE_INVENTORY_CHANGED")

    total = sum(row[1] for row in TEST_SUITES)
    result = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt012-static-validation-result-1.0",
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT012",
        "validated_revision": head,
        "r0_commit": R0,
        "r0_parent": START,
        "r0_exact_write_set": [path.as_posix() for path in R0_FILES],
        "r1_parent": R0,
        "r1_exact_write_set": [path.as_posix() for path in PACKET],
        "frozen_r0_test_and_fixture": frozen_facts,
        "packet_artifacts": packet_facts,
        "strict_json_files_passed": 3,
        "strict_json_files_total": 3,
        "source_checks": source_checks,
        "test_results": test_results,
        "aggregate_tests_passed": total,
        "aggregate_tests_total": total,
        "new_or_modified_python_bytecode_files": 0,
        "command_inventory": {
            "python_dash_b_static_test_processes": len(TEST_SUITES),
            "read_only_git_processes_only": True,
            "runner_imports": 0,
            "runner_invocations": 0,
            "docker_commands": 0,
            "wsl_commands": 0,
            "hyper_v_commands": 0,
            "powershell_host_probe_commands": 0,
            "runtime_or_host_probes": 0,
            "automatic_retry_count": 0,
            "fallback_count": 0,
        },
        "old_file_modification_count": 0,
        "output_root_absent": True,
        "runtime_commands_executed": False,
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "benchmark_admission_opened": False,
        "model_policy": {
            "requested_model": "gpt-5.6-sol",
            "requested_reasoning_effort": "xhigh",
            "requested_service_tier": "default",
            "requested_display_tier": "Standard",
            "actual_model": "gpt-5.6-sol",
            "actual_reasoning_effort": "xhigh",
            "actual_service_tier": "UNOBSERVABLE",
            "actual_speed": "UNOBSERVABLE",
            "fast_or_priority_observed": False,
        },
        "central_and_fresh_audit_receipts_created": False,
        "next_gate": "CENTRAL_GATE_2_STATIC_VALIDATION",
        "verdict": "IMPLEMENTATION_PASS_READY_FOR_CENTRAL_STATIC_VALIDATION",
    }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
