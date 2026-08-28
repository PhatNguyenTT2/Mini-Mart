#!/usr/bin/env python3
"""Offline static validator for the exact Attempt-013 R0/R1 packet."""

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

PYTHON = Path(r"C:\Program Files\Python311\python.exe")
CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
START = "3c7fede9dc0c1ba0925593e72ed515dccec84fcb"
R0 = "ce6377c351625ed7e029f2883520583ca97fc2b8"
RUNTIME_HELPER = CONTROL / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
RUNTIME_CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract.json"
RUNTIME_TEST = CONTROL / "test_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
AUTHORITY_HELPER = CONTROL / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority.py"
AUTHORITY_CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract.json"
AUTHORITY_TEST = CONTROL / "test_e4_r6_pc2w_p1_attempt013_pre_runtime_gate.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt013_admission_observation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt013_execution_authorization.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt013_admission_observation.py"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt013_static_packet.py"
PACKET = (
    RUNTIME_HELPER,
    RUNTIME_CONTRACT,
    RUNTIME_TEST,
    AUTHORITY_HELPER,
    AUTHORITY_CONTRACT,
    AUTHORITY_TEST,
    CONTRACT,
    AUTHORIZATION,
    RUNNER,
    VALIDATOR,
)
R0_FILES = (
    RUNTIME_CONTRACT,
    RUNTIME_TEST,
    AUTHORITY_CONTRACT,
    AUTHORITY_TEST,
)
R1_FILES = (
    RUNTIME_HELPER,
    AUTHORITY_HELPER,
    CONTRACT,
    AUTHORIZATION,
    RUNNER,
    VALIDATOR,
)
OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_av/"
    "E4_R6PC2W_P1_attempt013_admission_observation"
)
FROZEN_R0 = {
    RUNTIME_CONTRACT:
        "ed7d4323e7287643e0372e11cc1a2e6f5b5af73f4ec20fc0d0758dd12e648784",
    RUNTIME_TEST:
        "36b0e95a7b87a98325da6debfb345cb5a1df96ec672e6f1f3bb35db6b79fc21b",
    AUTHORITY_CONTRACT:
        "1cb5d8130420ae543d9f63b4d4cd0b9d16c7571577a5ad506f0217b2ebd530f0",
    AUTHORITY_TEST:
        "9c372dcd8a4cb4f87dab444a55739966936a930f098999487fd86d6f65a8c437",
}
ATTEMPT012_RECEIPTS = {
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/admission_observation.json"):
        (24292, "7295f026d57e497dfce68f768e4153b94e27436361c6e18ffe4818709ab72459"),
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/command_receipts.json"):
        (22369, "1b722165dfed8c8ba27832636fd7917f899786239d507e839cf9c7d1820d5098"),
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/execution_receipt.json"):
        (5189, "a35bcd4d70e0028a54eb6da3ace9a3da083dca15ae7100d8638e74a334c1973f"),
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/handoff.json"):
        (1488, "1da3715ac0752fcc5e967791f4a0c8561b98128283088f87b1f0ed24c5fee6a4"),
}
TEST_SUITES = (
    (RUNTIME_TEST, 15, "attempt013_runtime_identity_compatibility"),
    (AUTHORITY_TEST, 9, "attempt013_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt012_pre_runtime_gate.py", 12, "retained_attempt012_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py", 62, "retained_attempt011_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt010_command_interface.py", 10, "retained_attempt010_command_interface"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py", 9, "retained_attempt009_runtime_compatibility"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_probe_contract.py", 8, "retained_attempt008_probe_contract"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py", 9, "retained_attempt008_safe_envelopes"),
)


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


def validate_commit_shape(repo: Path, precommit: bool) -> str:
    require(commit_parent(repo, R0) == START, "R0_PARENT_MISMATCH")
    expected_r0 = sorted(f"A\t{path.as_posix()}" for path in R0_FILES)
    require(sorted(commit_delta(repo, R0)) == expected_r0, "R0_WRITE_SET_MISMATCH")
    status = str(git(repo, "status", "--porcelain=v1", "--untracked-files=all"))
    if precommit:
        require(str(git(repo, "rev-parse", "HEAD")).casefold() == R0, "PRECOMMIT_HEAD_NOT_R0")
        expected_status = sorted(f"?? {path.as_posix()}" for path in R1_FILES)
        require(sorted(status.splitlines()) == expected_status, "PRECOMMIT_WRITE_SET_MISMATCH")
        return "WORKTREE_PRECOMMIT"
    head = str(git(repo, "rev-parse", "HEAD")).casefold()
    require(commit_parent(repo, head) == R0, "R1_PARENT_MISMATCH")
    expected_r1 = sorted(f"A\t{path.as_posix()}" for path in R1_FILES)
    require(sorted(commit_delta(repo, head)) == expected_r1, "R1_WRITE_SET_MISMATCH")
    total = str(git(repo, "diff", "--name-status", f"{START}..{head}"))
    expected_total = sorted(f"A\t{path.as_posix()}" for path in PACKET)
    require(sorted(total.splitlines()) == expected_total, "TOTAL_WRITE_SET_MISMATCH")
    require(status == "", "R1_WORKTREE_NOT_CLEAN")
    return head


def validate_frozen_r0(repo: Path, revision: str, precommit: bool) -> list[dict[str, Any]]:
    facts = []
    for path, expected_sha256 in sorted(
        FROZEN_R0.items(), key=lambda item: item[0].as_posix()
    ):
        r0_raw = git_blob(repo, R0, path)
        require(sha256_bytes(r0_raw) == expected_sha256, f"R0_HASH_MISMATCH:{path}")
        if not precommit:
            require(git_blob(repo, revision, path) == r0_raw, f"R0_FIXTURE_CHANGED:{path}")
        require(normalized_checkout(repo / path) == r0_raw, f"R0_CHECKOUT_DRIFT:{path}")
        facts.append({
            "path": path.as_posix(),
            "git_blob_bytes": len(r0_raw),
            "git_blob_sha256": expected_sha256,
        })
    return facts


def packet_bytes(repo: Path, revision: str, path: Path, precommit: bool) -> bytes:
    if precommit and path in R1_FILES:
        return normalized_checkout(repo / path)
    return git_blob(repo, revision if not precommit else R0, path)


def validate_packet(repo: Path, revision: str, precommit: bool) -> list[dict[str, Any]]:
    facts = []
    for path in PACKET:
        raw = packet_bytes(repo, revision, path, precommit)
        require(normalized_checkout(repo / path) == raw, f"PACKET_CHECKOUT_DRIFT:{path}")
        facts.append({
            "path": path.as_posix(),
            "git_blob_bytes": len(raw),
            "git_blob_sha256": sha256_bytes(raw),
        })
    return facts


def validate_attempt012_receipts(repo: Path, revision: str) -> list[dict[str, Any]]:
    facts = []
    lookup_revision = R0 if revision == "WORKTREE_PRECOMMIT" else revision
    for path, (expected_bytes, expected_sha256) in sorted(
        ATTEMPT012_RECEIPTS.items(), key=lambda item: item[0].as_posix()
    ):
        raw = git_blob(repo, lookup_revision, path)
        require(len(raw) == expected_bytes, f"ATTEMPT012_RECEIPT_BYTES_MISMATCH:{path}")
        require(sha256_bytes(raw) == expected_sha256, f"ATTEMPT012_RECEIPT_HASH_MISMATCH:{path}")
        strict_json(raw, path)
        facts.append({
            "path": path.as_posix(),
            "git_blob_bytes": expected_bytes,
            "git_blob_sha256": expected_sha256,
        })
    return facts


def test_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def validate_sources(repo: Path) -> dict[str, Any]:
    python_files = (
        RUNTIME_HELPER,
        RUNTIME_TEST,
        AUTHORITY_HELPER,
        AUTHORITY_TEST,
        RUNNER,
        VALIDATOR,
    )
    trees = {
        path: ast.parse((repo / path).read_text(encoding="utf-8"), filename=path.as_posix())
        for path in python_files
    }
    validator_tree = trees[VALIDATOR]
    imported = {
        alias.name
        for node in ast.walk(validator_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(validator_tree)
        if isinstance(node, ast.ImportFrom)
    }
    require(
        not any("execute_e4_r6_pc2w_p1_attempt013" in name for name in imported),
        "STATIC_VALIDATOR_IMPORTS_RUNNER",
    )
    require("importlib" not in imported and "runpy" not in imported, "STATIC_VALIDATOR_DYNAMIC_IMPORT_CAPABILITY")
    runner = (repo / RUNNER).read_text(encoding="utf-8")
    compat = (repo / RUNTIME_HELPER).read_text(encoding="utf-8")
    authority = (repo / AUTHORITY_HELPER).read_text(encoding="utf-8")
    validator = (repo / VALIDATOR).read_text(encoding="utf-8")
    main = runner[runner.index("def main() -> int:"):]
    handoff = main.index("binding = authority.prepare_legacy_handoff")
    exact = main.index("command_interface.bind_exact_python_script_argv", handoff)
    configure = main.index("configure_attempt013_runner()", exact)
    root_rebind = main.index("legacy.EXPECTED_EXECUTION_ROOT = binding.execution_root", configure)
    legacy_main = main.index("return legacy.main()", root_rebind)
    require(handoff < exact < configure < root_rebind < legacy_main, "PRE_LEGACY_HANDOFF_ORDER_INVALID")
    configure_body = runner[runner.index("def configure_attempt013_runner() -> None:"):runner.index("def main() -> int:")]
    require("legacy.probes_v2 = compatibility" in configure_body, "PROCESS_TCP_VALIDATOR_NOT_INSTALLED")
    require("sanitize_docker_identity=compatibility.sanitize_docker_identity" in configure_body, "DOCKER_COMPARATOR_NOT_INSTALLED")
    require("compatibility.PROCESS_IDENTITY_QUERY_V3" in configure_body, "PROCESS_QUERY_NOT_INSTALLED")
    require("compatibility.TCP_IDENTITY_QUERY_V3" in configure_body, "TCP_QUERY_NOT_INSTALLED")
    require("*sys.argv[1:]" not in runner, "ACTUAL_ARGV_TAIL_COPIED")
    require("output.exists()" in authority, "OUTPUT_ABSENCE_GATE_MISSING")
    require("(1, 0, 1)" in authority, "ONE_SHOT_BUDGET_GATE_MISSING")
    require(compat.count("Get-CimInstance") == 1, "PROCESS_QUERY_NOT_SINGLE_SNAPSHOT")
    require("UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT" in compat, "PARENT_UNRESOLVED_ENUM_MISSING")
    require("FORMAT_EQUIVALENT_CIVIL_SECOND" in compat, "BUILDTIME_EQUIVALENCE_PROFILE_MISSING")
    require("root_value_sha256" in compat and "engine_value_sha256" in compat, "BUILDTIME_HASH_RECEIPT_MISSING")
    require("subprocess" not in compat and "subprocess" not in authority, "PURE_SEAM_HOST_PROCESS_CAPABILITY")
    return {
        "python_ast_files_passed": len(python_files),
        "static_validator_runner_imports": 0,
        "static_validator_runner_invocations": 0,
        "public_pre_legacy_handoff_order_valid": True,
        "parent_union_and_direct_self_validator_installed": True,
        "tcp_direct_self_index_binding_installed": True,
        "build_time_field_comparator_installed": True,
        "single_process_snapshot_query": True,
    }


def validate_documents(documents: dict[Path, dict[str, Any]]) -> None:
    runtime = documents[RUNTIME_CONTRACT]
    owner = documents[AUTHORITY_CONTRACT]
    contract = documents[CONTRACT]
    authorization = documents[AUTHORIZATION]
    require(runtime.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt013-runtime-identity-compatibility-contract-1.0", "RUNTIME_CONTRACT_SCHEMA_MISMATCH")
    require(owner.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt013-pre-runtime-authority-contract-1.0", "AUTHORITY_CONTRACT_SCHEMA_MISMATCH")
    require(contract.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt013-admission-observation-contract-1.0", "CONTRACT_SCHEMA_MISMATCH")
    require(authorization.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt013-execution-authorization-1.0", "AUTHORIZATION_SCHEMA_MISMATCH")
    seams = runtime.get("adjudicated_seams", {})
    require(seams.get("process_identity", {}).get("parent_resolution_closed_union") == ["RESOLVED", "UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT"], "PARENT_UNION_MISMATCH")
    require(seams.get("process_identity", {}).get("direct_self_identity_required") is True, "DIRECT_SELF_IDENTITY_NOT_REQUIRED")
    require(seams.get("tcp_ownership", {}).get("authority") == "VALIDATED_DIRECT_SELF_IDENTITY_INDEX", "TCP_AUTHORITY_MISMATCH")
    require(seams.get("tcp_ownership", {}).get("parent_completeness_dependency") is False, "TCP_PARENT_DEPENDENCY_RETAINED")
    require(seams.get("docker_build_time", {}).get("accepted_comparisons") == ["EXACT_RAW", "FORMAT_EQUIVALENT_CIVIL_SECOND"], "BUILDTIME_COMPARATOR_UNION_MISMATCH")
    require(seams.get("docker_build_time", {}).get("nonzero_fraction_allowed") is False, "NONZERO_FRACTION_ALLOWED")
    require(contract.get("packet_entry_gate", {}).get("packet_files") == [path.as_posix() for path in PACKET], "PACKET_ROSTER_MISMATCH")
    expected_runtime = {
        "path": RUNTIME_CONTRACT.as_posix(),
        "raw_git_blob_bytes": 4121,
        "raw_git_blob_sha256": FROZEN_R0[RUNTIME_CONTRACT],
    }
    expected_authority = {
        "path": AUTHORITY_CONTRACT.as_posix(),
        "raw_git_blob_bytes": 4526,
        "raw_git_blob_sha256": FROZEN_R0[AUTHORITY_CONTRACT],
    }
    for document in (contract, authorization):
        runtime_binding = document.get("runtime_identity_compatibility_binding", {})
        authority_binding = document.get("pre_runtime_authority_binding", {})
        require(all(runtime_binding.get(key) == value for key, value in expected_runtime.items()), "RUNTIME_BINDING_MISMATCH")
        require(all(authority_binding.get(key) == value for key, value in expected_authority.items()), "AUTHORITY_BINDING_MISMATCH")
        require(runtime_binding.get("restated_seam_values") is False, "SEAM_VALUES_RESTATED")
        require(authority_binding.get("restated_authority_values") is False, "AUTHORITY_VALUES_RESTATED")
    budget = owner.get("authority_contract", {}).get("attempt_budget")
    expected_budget = {"authorized": 1, "consumed": 0, "remaining": 1, "automatic_retry_count": 0, "fallback_count": 0}
    require(budget == expected_budget, "OWNER_ATTEMPT_BUDGET_MISMATCH")
    require(contract.get("attempt_budget") == expected_budget, "CONTRACT_ATTEMPT_BUDGET_MISMATCH")
    require(authorization.get("attempt_budget") == expected_budget, "AUTHORIZATION_ATTEMPT_BUDGET_MISMATCH")
    policy = owner.get("model_policy", {})
    require(policy.get("schema_version") == "stage1e-e4-r6-pc2w-p1-attempt013-model-policy-1.0", "MODEL_POLICY_SCHEMA_MISMATCH")
    expected_role = {"requested_model": "gpt-5.6-sol", "requested_reasoning_effort": "xhigh", "requested_service_tier": "default", "requested_display_tier": "Standard", "fast_or_priority_allowed": False}
    for role in ("implementation_static", "locked_execution"):
        require(policy.get("roles", {}).get(role) == expected_role, f"MODEL_ROLE_MISMATCH:{role}")
    observation = authorization.get("implementation_model_observation", {})
    require(observation.get("actual_model") == "gpt-5.6-sol", "ACTUAL_MODEL_MISMATCH")
    require(observation.get("actual_reasoning_effort") == "xhigh", "ACTUAL_REASONING_MISMATCH")
    require(observation.get("actual_speed") == "UNOBSERVABLE", "ACTUAL_SPEED_NOT_UNOBSERVABLE")
    require(observation.get("fast_or_priority_observed") is False, "FAST_OR_PRIORITY_OBSERVED")
    require(contract.get("output_contract", {}).get("output_root") == OUTPUT.as_posix(), "OUTPUT_ROOT_CONTRACT_MISMATCH")
    require(contract.get("output_contract", {}).get("absent_before_execution") is True, "OUTPUT_ABSENCE_NOT_CONTRACTED")
    for document in (runtime, owner, contract):
        scope = document.get("scope_boundary", {})
        require(scope.get("runtime_execution_authorized_now") is False, "RUNTIME_SCOPE_WIDENED")
    require(
        authorization.get("user_decision", {}).get("runtime_execution_authorized_now") is False,
        "AUTHORIZATION_RUNTIME_SCOPE_WIDENED",
    )
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
        require(not any(any(token in value for token in ("skip", "xfail", "expectedFailure")) for value in decorators), f"SKIP_OR_XFAIL:{label}")
        require("pytestmark" not in source and "pytest.mark.xfail" not in source, f"XFAIL_MARKER:{label}")
        completed = subprocess.run(
            [str(PYTHON.resolve()), "-B", str(repo / relative)],
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False,
        )
        require(completed.returncode == 0, f"STATIC_TEST_FAILURE:{label}")
        results.append({
            "suite": label,
            "tests_passed": expected_count,
            "tests_total": expected_count,
            "python_dash_b": True,
            "runtime_or_host_commands": 0,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--precommit", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    require(Path(sys.executable).resolve() == PYTHON.resolve(), "VALIDATOR_PYTHON_MISMATCH")
    require(Path.cwd().resolve() == repo, "VALIDATOR_CWD_MISMATCH")
    require(Path(str(git(repo, "rev-parse", "--show-toplevel"))).resolve() == repo, "REPOSITORY_ROOT_MISMATCH")
    require((repo / VALIDATOR).resolve() == Path(__file__).resolve(), "VALIDATOR_PATH_MISMATCH")
    require(not (repo / OUTPUT).exists(), "ATTEMPT013_OUTPUT_ROOT_ALREADY_EXISTS")
    revision = validate_commit_shape(repo, args.precommit)
    frozen_facts = validate_frozen_r0(repo, revision, args.precommit)
    packet_facts = validate_packet(repo, revision, args.precommit)
    receipt_facts = validate_attempt012_receipts(repo, revision)
    json_paths = (RUNTIME_CONTRACT, AUTHORITY_CONTRACT, CONTRACT, AUTHORIZATION)
    documents = {
        path: strict_json(packet_bytes(repo, revision, path, args.precommit), path)
        for path in json_paths
    }
    validate_documents(documents)
    source_checks = validate_sources(repo)
    pyc_before = bytecode_inventory(repo / CONTROL)
    test_results = run_tests(repo)
    pyc_after = bytecode_inventory(repo / CONTROL)
    require(pyc_before == pyc_after, "PYTHON_BYTECODE_INVENTORY_CHANGED")
    total = sum(row[1] for row in TEST_SUITES)
    result = {
        "schema_version": "stage1e-e4-r6-pc2w-p1-attempt013-static-validation-result-1.0",
        "material_passport": {
            "origin_skill": "experiment-agent",
            "origin_mode": "validate",
            "origin_date": "2026-08-29T00:00:00+07:00",
            "verification_status": "UNVERIFIED",
            "version_label": "stage1e_e4_r6_pc2w_p1_attempt013_static_validation_result_v1",
            "upstream_dependencies": [
                "stage1e_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract_v1",
                "stage1e_e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract_v1",
            ],
            "repro_lock": None,
            "experiment_intake_declaration": {
                "status": "no_experiments_declared",
                "declared_at": "2026-08-29T00:00:00+07:00",
                "declared_by": "scholar",
            },
            "experiment_provenance": [],
        },
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT013",
        "validation_mode": "PRECOMMIT_WORKTREE" if args.precommit else "COMMITTED_REPLAY",
        "validated_revision": revision,
        "r0_commit": R0,
        "r0_parent": START,
        "r0_exact_write_set": [path.as_posix() for path in R0_FILES],
        "r1_parent": R0,
        "r1_exact_write_set": [path.as_posix() for path in R1_FILES],
        "total_exact_write_set": [path.as_posix() for path in PACKET],
        "frozen_r0_artifacts": frozen_facts,
        "packet_artifacts": packet_facts,
        "attempt012_runtime_receipts_replayed": receipt_facts,
        "strict_json_files_passed": len(json_paths),
        "strict_json_files_total": len(json_paths),
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
            "network_operations": 0,
            "materialization_training_evaluation_benchmark_or_test_operations": 0,
            "automatic_retry_count": 0,
            "fallback_count": 0,
        },
        "attempt_budget": {"authorized": 1, "consumed": 0, "remaining": 1},
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
        "next_gate": "CENTRAL_STATIC_VALIDATION_ULTRA_STANDARD",
        "verdict": "IMPLEMENTATION_PASS_READY_FOR_CENTRAL_STATIC_VALIDATION",
    }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
