from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[5]
CONTROL = REPO / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
RUNNER = CONTROL / "execute_e4_r6_pc0_mxc_probe.py"
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc0_mxc_probe_dispatch.json"

ENTRY_COMMIT = "36a0ae1"
EXTERNAL_ROOT = (
    r"E:\UIT\cv\materialized-tools\hybrid-recsys-v5\stage1e\r6"
    r"\mxc_v0_7_0_rc1\attempt-001"
)
DATA_ROOT = (
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6"
    r"\official_source\grouplens_ml100k\attempt-003"
)
ENV_ROOT = (
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    r"\recbole_bpr_ml100k_py3119_cpu\attempt-003"
)
ASSET_URL = (
    "https://github.com/microsoft/mxc/releases/download/"
    "v0.7.0-rc1/mxc-release-binaries.zip"
)
ASSET_BYTES = 180_948_670
ASSET_SHA256 = "450ad608bd2268a8cbe126597be209601c51fbfe36141cec08abb017e828aba5"
PROCESSMODEL_DLL = r"C:\Windows\System32\processmodel.dll"
QUERY_EXPORT = "Experimental_QuerySandboxSupport"
CREATE_EXPORT = "Experimental_CreateProcessInSandbox"
GIT_EXE = r"C:\Program Files\Git\mingw64\bin\git.exe"
GIT_BYTES = 4_238_224
GIT_SHA256 = "1f2ee2de971b6d0a7a13f053014998b66c22df47f30f1907a767346392eb8d78"

REQUIRED_FROZEN_INPUTS = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_mxc_containment_feasibility_contract.md",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_c1r2_runner_compatibility_audit_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_c1r2_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_future_agent_model_policy_standard.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_query_api_source_lock.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc0_initial_runner_audit_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/dataset_materialization_packet.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/environment_materialization_packet.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/recbole_dataset_bridge_packet.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/execution_boundary_and_negative_assertions.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet/audit_handoff.json",
}


class StrictJsonError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def strict_load(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            StrictJsonError(f"NONFINITE_NUMBER:{value}")
        ),
    )
    if not isinstance(value, dict):
        raise StrictJsonError(f"ROOT_NOT_OBJECT:{path}")
    return value


def fingerprint(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def scalar_text(value: Any) -> str:
    return "\n".join(str(item) for item in walk(value) if isinstance(item, (str, int, bool)))


def check(
    checks: list[dict[str, Any]],
    failures: list[str],
    identifier: str,
    passed: bool,
    detail: str = "",
) -> None:
    checks.append({"id": identifier, "passed": bool(passed), "detail": detail})
    if not passed:
        failures.append(identifier)


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def frozen_rows(dispatch: dict[str, Any]) -> list[dict[str, Any]]:
    rows = dispatch.get("frozen_inputs")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def frozen_path(row: dict[str, Any]) -> str:
    value = row.get("path")
    return value.replace("\\", "/") if isinstance(value, str) else ""


def row_expected_fingerprint(row: dict[str, Any]) -> tuple[int | None, str | None]:
    byte_count = row.get("raw_bytes", row.get("bytes"))
    digest = row.get("raw_sha256", row.get("sha256"))
    return (
        byte_count if isinstance(byte_count, int) else None,
        digest if isinstance(digest, str) else None,
    )


def validate_frozen_rows(
    dispatch: dict[str, Any], checks: list[dict[str, Any]], failures: list[str]
) -> None:
    rows = frozen_rows(dispatch)
    paths = [frozen_path(row) for row in rows]
    check(checks, failures, "frozen_artifacts_is_nonempty_list", bool(rows))
    check(
        checks,
        failures,
        "frozen_artifact_paths_are_unique",
        len(paths) == len(set(paths)),
    )
    check(
        checks,
        failures,
        "required_frozen_inputs_present",
        REQUIRED_FROZEN_INPUTS.issubset(set(paths)),
        f"missing={sorted(REQUIRED_FROZEN_INPUTS - set(paths))}",
    )
    check(checks, failures, "frozen_input_count_exact", len(rows) == 11)
    for index, row in enumerate(rows):
        relative = frozen_path(row)
        path = REPO / relative
        expected_bytes, expected_sha = row_expected_fingerprint(row)
        exists = bool(relative) and path.is_file() and not path.is_symlink()
        check(checks, failures, f"frozen_{index:02d}_regular_file", exists, relative)
        if exists:
            actual = fingerprint(path)
            check(
                checks,
                failures,
                f"frozen_{index:02d}_fingerprint",
                expected_bytes == actual["bytes"] and expected_sha == actual["sha256"],
                relative,
            )


def validate_runner_ast(
    source: str, checks: list[dict[str, Any]], failures: list[str]
) -> ast.Module | None:
    try:
        tree = ast.parse(source, filename=str(RUNNER))
    except SyntaxError as exc:
        check(checks, failures, "runner_python_ast_parse", False, str(exc))
        return None
    check(checks, failures, "runner_python_ast_parse", True)

    imported_roots: set[str] = set()
    dangerous_calls: list[str] = []
    shell_true: list[int] = []
    subprocess_without_shell_false: list[int] = []
    write_calls: list[str] = []
    subprocess_calls = {
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            name = qualified_name(node.func)
            if name in {"eval", "exec", "os.system", "os.popen"}:
                dangerous_calls.append(name)
            if name in {
                "os.mkdir",
                "os.makedirs",
                "os.rename",
                "os.replace",
                "os.remove",
                "os.unlink",
                "shutil.copy",
                "shutil.copy2",
                "shutil.copyfile",
                "shutil.copytree",
                "shutil.move",
                "shutil.rmtree",
            } or name.endswith(
                (
                    ".mkdir",
                    ".rename",
                    ".replace",
                    ".unlink",
                    ".rmdir",
                    ".write_bytes",
                    ".write_text",
                )
            ):
                write_calls.append(f"{name}:{getattr(node, 'lineno', -1)}")
            if name.endswith(".open") or name == "open":
                mode_node: ast.AST | None = None
                if len(node.args) >= 2:
                    mode_node = node.args[1]
                for keyword in node.keywords:
                    if keyword.arg == "mode":
                        mode_node = keyword.value
                if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
                    if any(flag in mode_node.value for flag in "wax+"):
                        write_calls.append(
                            f"{name}:{getattr(node, 'lineno', -1)}:{mode_node.value}"
                        )
            if name in subprocess_calls:
                shell_keyword = next((kw for kw in node.keywords if kw.arg == "shell"), None)
                if shell_keyword is None:
                    subprocess_without_shell_false.append(getattr(node, "lineno", -1))
                elif isinstance(shell_keyword.value, ast.Constant):
                    if shell_keyword.value.value is True:
                        shell_true.append(getattr(node, "lineno", -1))
                    elif shell_keyword.value.value is not False:
                        subprocess_without_shell_false.append(getattr(node, "lineno", -1))
                else:
                    subprocess_without_shell_false.append(getattr(node, "lineno", -1))

    non_stdlib = sorted(
        name for name in imported_roots if name not in sys.stdlib_module_names
    )
    check(checks, failures, "runner_stdlib_only", not non_stdlib, str(non_stdlib))
    check(checks, failures, "runner_no_eval_exec_or_os_shell", not dangerous_calls, str(dangerous_calls))
    check(checks, failures, "runner_no_shell_true", not shell_true, str(shell_true))
    check(checks, failures, "runner_no_filesystem_write_primitives", not write_calls, str(write_calls))
    check(
        checks,
        failures,
        "runner_subprocess_explicit_shell_false",
        not subprocess_without_shell_false,
        str(subprocess_without_shell_false),
    )
    return tree


def ast_literal_constants(tree: ast.Module | None) -> tuple[set[str], set[int]]:
    if tree is None:
        return set(), set()
    strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    integers = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    }
    return strings, integers


def function_source(source: str, tree: ast.Module | None, name: str) -> str:
    if tree is None:
        return ""
    lines = source.splitlines()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            end = getattr(node, "end_lineno", node.lineno)
            return "\n".join(lines[node.lineno - 1 : end])
    return ""


def main() -> int:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    check(checks, failures, "runner_exists", RUNNER.is_file())
    check(checks, failures, "dispatch_exists", DISPATCH.is_file())
    if failures:
        print(json.dumps({"checks": checks, "failures": failures}, indent=2, sort_keys=True))
        return 1

    dispatch = strict_load(DISPATCH)
    runner_source = RUNNER.read_text(encoding="utf-8")
    dispatch_text = scalar_text(dispatch)
    runner_lower = runner_source.casefold()
    dispatch_lower = dispatch_text.casefold()

    validate_frozen_rows(dispatch, checks, failures)
    tree = validate_runner_ast(runner_source, checks, failures)
    string_constants, integer_constants = ast_literal_constants(tree)
    git_function = function_source(runner_source, tree, "git_run")
    query_function = function_source(runner_source, tree, "query_sandbox_support")
    materialize_function = function_source(runner_source, tree, "run_materialize")
    probe_function = function_source(runner_source, tree, "run_probe")

    runner_record = dispatch.get("runner")
    runner_identity = fingerprint(RUNNER)
    check(
        checks,
        failures,
        "dispatch_runner_identity_exact",
        isinstance(runner_record, dict)
        and runner_record.get("path") == RUNNER.relative_to(REPO).as_posix()
        and runner_record.get("raw_bytes") == runner_identity["bytes"]
        and runner_record.get("raw_sha256") == runner_identity["sha256"],
    )

    check(checks, failures, "entry_commit_frozen", ENTRY_COMMIT in dispatch_text)
    check(checks, failures, "external_root_exact_runner", EXTERNAL_ROOT in string_constants)
    check(checks, failures, "external_root_exact_dispatch", EXTERNAL_ROOT in dispatch_text)
    check(checks, failures, "attempt003_data_root_guarded", DATA_ROOT in string_constants)
    check(checks, failures, "attempt003_environment_root_guarded", ENV_ROOT in string_constants)
    check(checks, failures, "asset_url_exact_runner", ASSET_URL in string_constants)
    check(checks, failures, "asset_url_exact_dispatch", ASSET_URL in dispatch_text)
    check(checks, failures, "asset_bytes_exact_runner", ASSET_BYTES in integer_constants)
    check(checks, failures, "asset_bytes_exact_dispatch", str(ASSET_BYTES) in dispatch_text)
    check(checks, failures, "asset_sha256_exact_runner", ASSET_SHA256 in runner_source)
    check(checks, failures, "asset_sha256_exact_dispatch", ASSET_SHA256 in dispatch_text)

    for mode in ("preflight", "materialize", "probe"):
        check(checks, failures, f"mode_{mode}_runner", mode in runner_lower)
        check(checks, failures, f"mode_{mode}_dispatch", mode in dispatch_lower)

    required_runner_terms = {
        "query_export": QUERY_EXPORT.casefold(),
        "create_export": CREATE_EXPORT.casefold(),
        "query_capability_mask": "capabilities",
        "query_bit_zero": "0x1",
        "incomplete_classification": "policy_test_required",
        "materialize_denial": "materialize",
        "probe_denial": "probe",
        "reparse_guard": "reparse",
        "parent_bootstrap": "parent_bootstrap_required",
    }
    for identifier, token in required_runner_terms.items():
        check(checks, failures, f"runner_term_{identifier}", token in runner_lower)

    required_integer_constants = {"create_capability_bit": 0x1, "incomplete_exit": 2}
    for identifier, value in required_integer_constants.items():
        check(
            checks,
            failures,
            f"runner_integer_{identifier}",
            value in integer_constants,
        )

    forbidden_runner_terms = {
        "requests_import": "import requests",
        "urllib_import": "import urllib",
        "socket_import": "import socket",
        "zipfile_import": "import zipfile",
        "powershell": "powershell",
        "authenticode": "authenticode",
        "downloaded_probe_flag": "--probe",
        "download_call": "urlopen(",
        "dataset_constructor": "create_dataset(",
        "recbole_trainer": "trainer(",
        "model_fit": ".fit(",
        "model_evaluate": ".evaluate(",
        "fast_profile": "max fast",
        "priority_tier": "service_tier",
    }
    for identifier, token in forbidden_runner_terms.items():
        check(checks, failures, f"runner_forbids_{identifier}", token not in runner_lower)

    check(
        checks,
        failures,
        "dispatch_model_sol_high_standard",
        "sol high standard" in dispatch_lower,
    )
    check(checks, failures, "dispatch_no_fast_profile", " fast" not in dispatch_lower)
    check(checks, failures, "dispatch_truth_result_not_run", "not_run" in dispatch_lower)
    check(checks, failures, "dispatch_truth_test_no", "test_set_opened" in dispatch_lower and "no" in dispatch_lower)
    check(checks, failures, "dispatch_truth_zero_rows", "accepted_result_rows" in dispatch_lower and "0" in dispatch_lower)
    check(
        checks,
        failures,
        "dispatch_pass_unreachable_and_query_incomplete",
        "incomplete" in dispatch_lower
        and "policy" in dispatch_lower
        and dispatch.get("admission_logic", {}).get("pass_reachable_in_this_runner_version") is False,
    )
    check(
        checks,
        failures,
        "materialize_mode_hard_denied_without_mutation",
        "DENIED" in materialize_function
        and all(token not in materialize_function for token in ("mkdir(", "open(", "subprocess", "urllib")),
    )
    check(
        checks,
        failures,
        "probe_mode_hard_denied_without_execution",
        "DENIED" in probe_function
        and all(token not in probe_function for token in ("Popen(", "subprocess", "--probe", "open(")),
    )
    check(
        checks,
        failures,
        "query_is_in_process_and_exact",
        QUERY_EXPORT in query_function
        and "ctypes" in query_function
        and "subprocess" not in query_function,
    )
    check(
        checks,
        failures,
        "git_observation_disables_optional_locks",
        "GIT_OPTIONAL_LOCKS" in git_function and '"0"' in git_function,
    )
    check(
        checks,
        failures,
        "git_identity_frozen_in_runner",
        GIT_EXE in string_constants
        and GIT_BYTES in integer_constants
        and GIT_SHA256 in runner_source,
    )
    check(
        checks,
        failures,
        "git_explicit_repository_and_config_isolation",
        all(
            token in git_function
            for token in (
                "--git-dir",
                "--work-tree",
                "core.fsmonitor=false",
                "core.untrackedCache=false",
                "GIT_CONFIG_NOSYSTEM",
                "GIT_CONFIG_GLOBAL",
            )
        ),
    )
    check(
        checks,
        failures,
        "processmodel_and_exports_frozen",
        PROCESSMODEL_DLL in string_constants
        and QUERY_EXPORT in string_constants
        and CREATE_EXPORT in string_constants,
    )
    check(
        checks,
        failures,
        "dispatch_read_only_preflight_only",
        "read_only_capability_preflight_only" in dispatch_lower
        and "materialize" in dispatch_lower
        and "probe" in dispatch_lower
        and "denied" in dispatch_lower,
    )
    check(
        checks,
        failures,
        "dispatch_no_network_and_no_write",
        "no_network" in dispatch_lower and "no_write" in dispatch_lower,
    )
    check(
        checks,
        failures,
        "dispatch_source_not_downloaded",
        "not_downloaded" in dispatch_lower,
    )
    check(
        checks,
        failures,
        "dispatch_parent_bootstrap_not_authorized",
        "parent_bootstrap_required" in dispatch_lower
        and "bootstrap" in dispatch_lower
        and "not_authorized" in dispatch_lower,
    )
    check(
        checks,
        failures,
        "dispatch_exit_mapping_fail_closed",
        "0=pass" in dispatch_lower
        and "1=fail" in dispatch_lower
        and "2=incomplete" in dispatch_lower,
    )
    check(
        checks,
        failures,
        "dispatch_forbids_host_mutation",
        all(token in dispatch_lower for token in ("dacl", "firewall", "elevation", "host prep")),
    )
    check(
        checks,
        failures,
        "dispatch_forbids_scientific_execution",
        all(token in dispatch_lower for token in ("training", "evaluation", "benchmark")),
    )

    summary = {
        "schema_version": "stage1e-r6-pc0-mxc-probe-static-validation-1.0",
        "validator_execution_scope": "STATIC_ONLY_RUNNER_NOT_EXECUTED",
        "checks_total": len(checks),
        "checks_passed": sum(1 for row in checks if row["passed"]),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "runner": fingerprint(RUNNER),
        "dispatch": fingerprint(DISPATCH),
        "scientific_execution_performed": False,
        "test_accessed": False,
        "benchmark_admitted": False,
        "verdict": (
            "PASS_R6_PC0_RUNNER_DISPATCH_STATIC_VALIDATION"
            if not failures
            else "REWORK_REQUIRED_R6_PC0_RUNNER_DISPATCH"
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
