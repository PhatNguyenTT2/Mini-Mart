from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[5]
CONTROL = REPO / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
RUNNER = CONTROL / "execute_e4_r6_pc0_query_only_attempt002.py"
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_pc0_query_only_attempt002_dispatch.json"
SOURCE_LOCK = CONTROL / "e4_r6_pc0_query_api_source_lock.json"
SUPERSESSION = CONTROL / "e4_r6_pc0_query_only_v1_supersession_record.json"
ATTEMPT001_RECEIPT = CONTROL / "rebaseline_v2_e4_r6_pc0_query_preflight_attempt001_failure_receipt.json"

RECOVERY_CHECKPOINT = "4f07d20c056b06cb255117e7b0d1284fdd40c320"
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
QUERY_EXPORT = "Experimental_QuerySandboxSupport"
CREATE_EXPORT = "Experimental_CreateProcessInSandbox"
PROCESSMODEL_DLL = r"C:\Windows\System32\processmodel.dll"
PYTHON_EXE = (
    r"C:\Users\ACER\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe"
)
PYTHON_BYTES = 91_648
PYTHON_SHA256 = "d8e3f0adf246db00358c0c4ed349cf714898178f9558fb0e944f79f5c07f8eaa"
GIT_EXE = r"C:\Program Files\Git\mingw64\bin\git.exe"
GIT_BYTES = 4_238_224
GIT_SHA256 = "1f2ee2de971b6d0a7a13f053014998b66c22df47f30f1907a767346392eb8d78"
V1_IDENTITIES = {
    "execute_e4_r6_pc0_mxc_probe.py": (
        27_982,
        "4c8025276eaf834480d0575043d9b6bd6e8e33b1edcba9329e554252dced94c1",
        "SUPERSEDED_NEVER_RERUN",
    ),
    "rebaseline_v2_e4_r6_pc0_mxc_probe_dispatch.json": (
        8_167,
        "637b02241d0d94cde610495b17f686e6c0652cafcea86449dbab1961a2426927",
        "SUPERSEDED_NEVER_REDISPATCH",
    ),
    "validate_e4_r6_pc0_mxc_probe.py": (
        21_039,
        "27cb10515eaed6e16a54d317c3a15f44fecf8a8e66fcf5656983be228d791880",
        "INVALIDATED_SEMANTIC_COVERAGE_GAP",
    ),
    "rebaseline_v2_e4_r6_pc0_query_only_static_validation_receipt.json": (
        4_009,
        "b59eedc40840f40eb7b95ed6ba7b8e103cda71c59661ff7f01aa7b8c36ee41e0",
        "SUPERSEDED_SEMANTIC_FALSE_PASS_97_OF_97",
    ),
}

REQUIRED_FROZEN_INPUTS = {
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_mxc_containment_feasibility_contract.md",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_c1r2_validation_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_c1r2_runner_compatibility_audit_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_future_agent_model_policy_standard.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_query_api_source_lock.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc0_initial_runner_audit_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc0_query_preflight_attempt001_failure_receipt.json",
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "e4_r6_pc0_query_only_v1_supersession_record.json",
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
    folded: set[str] = set()
    for key, value in pairs:
        if key in result or key.casefold() in folded:
            raise StrictJsonError(f"DUPLICATE_OR_CASE_COLLIDING_KEY:{key}")
        result[key] = value
        folded.add(key.casefold())
    return result


def strict_load(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=lambda token: (_ for _ in ()).throw(
            StrictJsonError(f"NONFINITE_NUMBER:{token}")
        ),
    )
    if not isinstance(value, dict):
        raise StrictJsonError(f"ROOT_NOT_OBJECT:{path}")
    return value


def fingerprint(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {"raw_bytes": len(payload), "raw_sha256": hashlib.sha256(payload).hexdigest()}


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


def function_node(tree: ast.Module | None, name: str) -> ast.FunctionDef | None:
    if tree is None:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def function_source(source: str, tree: ast.Module | None, name: str) -> str:
    node = function_node(tree, name)
    if node is None:
        return ""
    lines = source.splitlines()
    return "\n".join(lines[node.lineno - 1 : node.end_lineno])


def validate_runner_ast(
    source: str,
    checks: list[dict[str, Any]],
    failures: list[str],
) -> ast.Module | None:
    try:
        tree = ast.parse(source, filename=str(RUNNER))
    except SyntaxError as exc:
        check(checks, failures, "runner_python_ast_parse", False, str(exc))
        return None
    check(checks, failures, "runner_python_ast_parse", True)

    imported_roots: set[str] = set()
    dangerous_calls: list[str] = []
    shell_defects: list[int] = []
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
                mode_node: ast.AST | None = node.args[1] if len(node.args) >= 2 else None
                for keyword in node.keywords:
                    if keyword.arg == "mode":
                        mode_node = keyword.value
                if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
                    if any(flag in mode_node.value for flag in "wax+"):
                        write_calls.append(f"{name}:{getattr(node, 'lineno', -1)}:{mode_node.value}")
            if name in subprocess_calls:
                shell_keyword = next((kw for kw in node.keywords if kw.arg == "shell"), None)
                if not (
                    shell_keyword is not None
                    and isinstance(shell_keyword.value, ast.Constant)
                    and shell_keyword.value.value is False
                ):
                    shell_defects.append(getattr(node, "lineno", -1))

    non_stdlib = sorted(name for name in imported_roots if name not in sys.stdlib_module_names)
    check(checks, failures, "runner_stdlib_only", not non_stdlib, str(non_stdlib))
    check(checks, failures, "runner_no_eval_exec_or_os_shell", not dangerous_calls, str(dangerous_calls))
    check(checks, failures, "runner_no_filesystem_write_primitives", not write_calls, str(write_calls))
    check(checks, failures, "runner_subprocess_explicit_shell_false", not shell_defects, str(shell_defects))
    return tree


def validate_frozen_inputs(
    dispatch: dict[str, Any],
    checks: list[dict[str, Any]],
    failures: list[str],
) -> None:
    rows = dispatch.get("frozen_inputs")
    valid_rows = rows if isinstance(rows, list) else []
    paths = [row.get("path") for row in valid_rows if isinstance(row, dict)]
    check(checks, failures, "frozen_input_count_exact", len(valid_rows) == 13)
    check(checks, failures, "frozen_input_paths_unique", len(paths) == len(set(paths)))
    check(
        checks,
        failures,
        "required_frozen_input_set_exact",
        set(paths) == REQUIRED_FROZEN_INPUTS,
        f"missing={sorted(REQUIRED_FROZEN_INPUTS - set(paths))}",
    )
    for index, row in enumerate(valid_rows):
        if not isinstance(row, dict):
            check(checks, failures, f"frozen_{index:02d}_object", False)
            continue
        relative = row.get("path")
        path = REPO / relative if isinstance(relative, str) else Path("")
        exists = path.is_file() and not path.is_symlink()
        check(checks, failures, f"frozen_{index:02d}_ordinary_file", exists, str(relative))
        if exists:
            observed = fingerprint(path)
            check(
                checks,
                failures,
                f"frozen_{index:02d}_fingerprint",
                row.get("raw_bytes") == observed["raw_bytes"]
                and row.get("raw_sha256") == observed["raw_sha256"],
                str(relative),
            )


def load_runner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("r6_pc0_attempt002_static_target", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("RUNNER_IMPORT_SPEC_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    for identifier, path in (
        ("runner_exists", RUNNER),
        ("dispatch_exists", DISPATCH),
        ("source_lock_exists", SOURCE_LOCK),
        ("supersession_exists", SUPERSESSION),
        ("attempt001_receipt_exists", ATTEMPT001_RECEIPT),
    ):
        check(checks, failures, identifier, path.is_file() and not path.is_symlink())
    if failures:
        print(json.dumps({"checks": checks, "failures": failures}, indent=2, sort_keys=True))
        return 1

    dispatch = strict_load(DISPATCH)
    source_lock = strict_load(SOURCE_LOCK)
    supersession = strict_load(SUPERSESSION)
    attempt001 = strict_load(ATTEMPT001_RECEIPT)
    runner_source = RUNNER.read_text(encoding="utf-8")
    runner_lower = runner_source.casefold()
    dispatch_text = scalar_text(dispatch)
    dispatch_lower = dispatch_text.casefold()

    validate_frozen_inputs(dispatch, checks, failures)
    tree = validate_runner_ast(runner_source, checks, failures)
    query_source = function_source(runner_source, tree, "query_sandbox_support")
    classify_source = function_source(runner_source, tree, "classify_query_result")
    preflight_source = function_source(runner_source, tree, "run_preflight")
    materialize_source = function_source(runner_source, tree, "run_materialize")
    probe_source = function_source(runner_source, tree, "run_probe")
    git_source = function_source(runner_source, tree, "verify_git_control") + function_source(
        runner_source, tree, "git_run"
    )

    runner_identity = fingerprint(RUNNER)
    runner_record = dispatch.get("runner", {})
    check(
        checks,
        failures,
        "dispatch_runner_identity_exact",
        isinstance(runner_record, dict)
        and runner_record.get("path") == RUNNER.relative_to(REPO).as_posix()
        and runner_record.get("raw_bytes") == runner_identity["raw_bytes"]
        and runner_record.get("raw_sha256") == runner_identity["raw_sha256"],
    )
    check(checks, failures, "recovery_checkpoint_bound", dispatch.get("recovery_checkpoint") == RECOVERY_CHECKPOINT)
    binding = dispatch.get("checkpoint_binding", {})
    check(
        checks,
        failures,
        "caller_supplied_exact_head_binding",
        isinstance(binding, dict)
        and binding.get("method") == "CALLER_SUPPLIED_EXACT_40_HEX_MUST_EQUAL_RUNTIME_HEAD"
        and binding.get("argument") == "--checkpoint"
        and binding.get("self_referential_head_embedded") is False,
    )
    check(checks, failures, "runner_requires_checkpoint_argument", '"--checkpoint", required=True' in runner_source)
    check(checks, failures, "runner_exact_head_comparison", "head != expected_head" in git_source)
    check(checks, failures, "runner_recovery_ancestor_guard", "RECOVERY_CHECKPOINT" in git_source and "merge-base" in git_source)

    python_control = dispatch.get("python_control", {})
    check(
        checks,
        failures,
        "python_control_identity_frozen",
        isinstance(python_control, dict)
        and python_control.get("path") == PYTHON_EXE
        and python_control.get("raw_bytes") == PYTHON_BYTES
        and python_control.get("raw_sha256") == PYTHON_SHA256
        and python_control.get("version_info") == [3, 12, 13, "final", 0]
        and python_control.get("architecture_bits") == 64
        and python_control.get("required_flags") == ["-I", "-B"],
    )
    check(checks, failures, "runner_verifies_python_flags", "sys.flags.isolated" in runner_source and "sys.flags.dont_write_bytecode" in runner_source)
    check(
        checks,
        failures,
        "git_identity_frozen",
        GIT_EXE in runner_source
        and "GIT_BYTES = 4_238_224" in runner_source
        and GIT_SHA256 in runner_source,
    )
    check(
        checks,
        failures,
        "git_config_isolated_and_read_only",
        all(
            token in git_source
            for token in (
                "GIT_OPTIONAL_LOCKS",
                "GIT_CONFIG_NOSYSTEM",
                "GIT_CONFIG_GLOBAL",
                "core.fsmonitor=false",
                "core.untrackedCache=false",
                "--git-dir",
                "--work-tree",
            )
        ),
    )

    api_contract = source_lock.get("api_contract", {})
    check(
        checks,
        failures,
        "source_lock_nonzero_bool_success",
        isinstance(api_contract, dict)
        and api_contract.get("success_semantics") == "nonzero BOOL means the u64 capability mask is valid"
        and api_contract.get("failure_semantics") == "zero BOOL means unknown/failure and must not be interpreted as unsupported",
    )
    query_api = dispatch.get("query_api", {})
    check(
        checks,
        failures,
        "dispatch_binds_bool_semantics",
        isinstance(query_api, dict)
        and query_api.get("success_semantics") == "NONZERO_BOOL_OUTPUT_MASK_VALID"
        and query_api.get("failure_semantics") == "ZERO_BOOL_QUERY_FAILED_OUTPUT_MASK_INVALID"
        and query_api.get("restype") == "ctypes.c_int32"
        and query_api.get("output_type") == "ctypes.c_uint64",
    )
    check(checks, failures, "query_uses_exact_export", QUERY_EXPORT in query_source)
    check(checks, failures, "query_never_calls_create_export", CREATE_EXPORT not in query_source)
    check(checks, failures, "query_explicit_i32_restype", "query.restype = ctypes.c_int32" in query_source)
    check(checks, failures, "query_explicit_u64_pointer", "ctypes.POINTER(ctypes.c_uint64)" in query_source)
    check(checks, failures, "query_bool_zero_failure", "if bool_return == 0:" in query_source)
    check(checks, failures, "query_does_not_require_bool_one", "bool_return == 1" not in query_source)
    check(checks, failures, "query_no_inverted_nonzero_condition", "bool_return != 0" not in query_source)
    bool_call_position = query_source.find("bool_return = int(query(")
    bool_guard_position = query_source.find("if bool_return == 0:")
    zero_mask_position = query_source.find('"capability_mask": None')
    mask_read_position = query_source.find("capability_mask = int(capabilities.value)")
    check(
        checks,
        failures,
        "output_mask_consumed_only_after_nonzero_success",
        -1 not in (bool_call_position, bool_guard_position, mask_read_position)
        and bool_call_position < bool_guard_position < mask_read_position,
    )
    check(
        checks,
        failures,
        "bool_zero_returns_without_raise_or_mask_consumption",
        -1 not in (bool_guard_position, zero_mask_position, mask_read_position)
        and bool_guard_position < zero_mask_position < mask_read_position
        and "QUERY_SANDBOX_SUPPORT_FAILED_BOOL_ZERO_OUTPUT_MASK_INVALID" not in query_source,
    )
    query_node = function_node(tree, "query_sandbox_support")
    query_invocations = 0
    if query_node is not None:
        query_invocations = sum(
            1
            for node in ast.walk(query_node)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "query"
        )
    check(checks, failures, "query_call_count_exactly_one", query_invocations == 1, str(query_invocations))

    check(checks, failures, "classifier_zero_branch", "if bool_return == 0:" in classify_source)
    check(checks, failures, "classifier_bit_clear_branch", "mask & CREATE_CAPABILITY_BIT == 0" in classify_source)
    check(checks, failures, "classifier_pass_unreachable", "EXIT_PASS" not in classify_source)
    check(checks, failures, "preflight_calls_query_once", preflight_source.count("query_sandbox_support()") == 1)
    check(checks, failures, "preflight_uses_classifier", "classify_query_result(" in preflight_source)
    query_position = preflight_source.find("query = query_sandbox_support()")
    classify_position = preflight_source.find("classification = classify_query_result(")
    closure_position = preflight_source.find("closure = post_query_closure(")
    check(
        checks,
        failures,
        "post_query_closure_order",
        -1 not in (query_position, classify_position, closure_position)
        and query_position < closure_position < classify_position,
    )
    check(checks, failures, "loaded_module_path_verified", "loaded_module_path" in query_source and "PROCESSMODEL_LOADED_PATH_MISMATCH" in query_source)
    check(checks, failures, "post_query_git_root_dll_closure", all(token in runner_source for token in ("verify_git_control(expected_head", "verify_absent_roots_and_ancestry()", "PROCESSMODEL_POST_QUERY_IDENTITY_CHANGED")))

    check(checks, failures, "materialize_hard_denied", "DENIED" in materialize_source and "subprocess" not in materialize_source)
    check(checks, failures, "probe_hard_denied", "DENIED" in probe_source and "subprocess" not in probe_source)
    check(checks, failures, "exception_scope_not_baseexception", "except BaseException" not in runner_source and "except Exception as exc" in runner_source)

    forbidden_terms = {
        "urllib": "import urllib",
        "socket": "import socket",
        "zipfile": "import zipfile",
        "requests": "import requests",
        "powershell": "powershell",
        "authenticode": "authenticode",
        "download_call": "urlopen(",
        "dataset_constructor": "create_dataset(",
        "trainer": "trainer(",
        "fit": ".fit(",
        "evaluate": ".evaluate(",
        "priority_tier": "service_tier",
    }
    for identifier, token in forbidden_terms.items():
        check(checks, failures, f"runner_forbids_{identifier}", token not in runner_lower)

    check(checks, failures, "dispatch_no_fast_profile", " fast" not in dispatch_lower)
    check(checks, failures, "dispatch_standard_models", all(token in dispatch_lower for token in ("sol xhigh standard", "sol high standard", "sol max standard")))
    check(checks, failures, "dispatch_result_not_run", dispatch.get("truth_state", {}).get("result_status") == "NOT_RUN")
    check(checks, failures, "dispatch_test_closed", dispatch.get("truth_state", {}).get("test_set_opened") == "NO")
    check(checks, failures, "dispatch_zero_rows", dispatch.get("truth_state", {}).get("accepted_result_rows") == 0)
    check(checks, failures, "dispatch_pass_unreachable", dispatch.get("admission_logic", {}).get("pass_reachable_in_this_runner_version") is False)
    check(checks, failures, "dispatch_source_not_downloaded", dispatch.get("source_materialization", {}).get("status") == "NOT_DOWNLOADED")
    check(checks, failures, "dispatch_roots_exact", all(value in dispatch_text for value in (EXTERNAL_ROOT, DATA_ROOT, ENV_ROOT)))
    check(checks, failures, "dispatch_processmodel_exact", PROCESSMODEL_DLL in dispatch_text)
    check(checks, failures, "dispatch_parent_bootstrap_not_authorized", "PARENT_BOOTSTRAP_REQUIRED_BUT_NOT_AUTHORIZED" in dispatch_text)
    check(checks, failures, "dispatch_exit_mapping", dispatch.get("exit_codes", {}).get("summary") == "0=PASS;1=FAIL;2=INCOMPLETE")

    old_rows = supersession.get("superseded_artifacts")
    old_map = {
        Path(row.get("path", "")).name: (row.get("raw_bytes"), row.get("raw_sha256"), row.get("disposition"))
        for row in old_rows
        if isinstance(row, dict)
    } if isinstance(old_rows, list) else {}
    for filename, (expected_bytes, expected_sha, expected_disposition) in V1_IDENTITIES.items():
        observed = fingerprint(CONTROL / filename)
        row = old_map.get(filename)
        check(
            checks,
            failures,
            f"v1_immutable_{filename}",
            observed == {"raw_bytes": expected_bytes, "raw_sha256": expected_sha}
            and row is not None
            and row[0] == expected_bytes
            and row[1] == expected_sha
            and row[2] == expected_disposition,
        )

    check(
        checks,
        failures,
        "attempt001_capability_unclassified",
        attempt001.get("execution_observation", {}).get("raw_api_return_observed") == 1
        and attempt001.get("execution_observation", {}).get("capability_output_mask_recorded") is False
        and attempt001.get("failure_analysis", {}).get("mxc_candidate_rejected") is False
        and attempt001.get("failure_analysis", {}).get("mxc_candidate_admitted") is False,
    )

    module: ModuleType | None = None
    try:
        module = load_runner_module()
        check(checks, failures, "runner_import_without_main", True)
    except Exception as exc:
        check(checks, failures, "runner_import_without_main", False, f"{type(exc).__name__}:{exc}")

    truth_cases = [
        (0, None, "QUERY_FAILURE_OUTPUT_MASK_INVALID", 1, False, None),
        (1, 0, "FAIL_HOST_CAPABILITY_ABSENT", 1, True, False),
        (1, 1, "INCOMPLETE_POLICY_TEST_REQUIRED", 2, True, True),
        (-1, 1, "INCOMPLETE_POLICY_TEST_REQUIRED", 2, True, True),
        (2, 0, "FAIL_HOST_CAPABILITY_ABSENT", 1, True, False),
    ]
    if module is not None:
        for bool_return, mask, classification, exit_code, mask_valid, present in truth_cases:
            try:
                observed = module.classify_query_result(bool_return, mask)
                passed = observed == {
                    "classification": classification,
                    "exit_code": exit_code,
                    "capability_mask_valid": mask_valid,
                    "create_process_capability_present": present,
                }
            except Exception as exc:
                passed = False
                observed = {"error": f"{type(exc).__name__}:{exc}"}
            check(
                checks,
                failures,
                f"truth_table_bool_{bool_return}_mask_{mask}",
                passed,
                json.dumps(observed, sort_keys=True),
            )

        originals = {
            name: getattr(module, name)
            for name in (
                "verify_checkpoint_argument",
                "verify_python_control_runtime",
                "verify_dispatch",
                "verify_git_control",
                "verify_host",
                "verify_absent_roots_and_ancestry",
                "verify_processmodel_identity_and_exports",
                "query_sandbox_support",
                "post_query_closure",
                "emit",
            )
        }
        closure_calls: list[tuple[str, list[str], dict[str, Any]]] = []
        emitted: list[dict[str, Any]] = []
        try:
            module.verify_checkpoint_argument = lambda checkpoint: None
            module.verify_python_control_runtime = lambda: {"status": "MOCKED_STATIC_TEST"}
            module.verify_dispatch = lambda: ({"created_at": "STATIC_TEST"}, [])
            module.verify_git_control = lambda checkpoint, paths: {"status": "MOCKED_STATIC_TEST"}
            module.verify_host = lambda: {"status": "MOCKED_STATIC_TEST"}
            module.verify_absent_roots_and_ancestry = lambda: {"status": "MOCKED_STATIC_TEST"}
            module.verify_processmodel_identity_and_exports = lambda: {"status": "MOCKED_STATIC_TEST"}
            module.query_sandbox_support = lambda: {
                "query_export": QUERY_EXPORT,
                "bool_return": 0,
                "capability_mask": None,
                "call_count": 1,
                "fallback_create_call": False,
                "loaded_module": {"dll": PROCESSMODEL_DLL},
            }

            def record_closure(
                checkpoint: str,
                tracked_paths: list[str],
                loaded_module: dict[str, Any],
            ) -> dict[str, Any]:
                closure_calls.append((checkpoint, tracked_paths, loaded_module))
                return {"status": "MOCKED_STATIC_TEST"}

            module.post_query_closure = record_closure
            module.emit = emitted.append
            observed_exit = module.run_preflight("0" * 40)
            observed_result = emitted[-1] if emitted else {}
            check(
                checks,
                failures,
                "bool_zero_path_executes_post_query_closure",
                observed_exit == 1
                and len(closure_calls) == 1
                and observed_result.get("classification", {}).get("classification")
                == "QUERY_FAILURE_OUTPUT_MASK_INVALID"
                and observed_result.get("post_query_closure", {}).get("status")
                == "MOCKED_STATIC_TEST",
                json.dumps(
                    {
                        "exit_code": observed_exit,
                        "closure_calls": len(closure_calls),
                        "result": observed_result,
                    },
                    sort_keys=True,
                ),
            )
        except Exception as exc:
            check(
                checks,
                failures,
                "bool_zero_path_executes_post_query_closure",
                False,
                f"{type(exc).__name__}:{exc}",
            )
        finally:
            for name, value in originals.items():
                setattr(module, name, value)

    summary = {
        "schema_version": "stage1e-e4-r6-pc0-query-attempt002-static-validation-1.0",
        "validator_execution_scope": "STATIC_AST_PLUS_PURE_CLASSIFIER_TRUTH_TABLE_RUNNER_MAIN_AND_API_NOT_EXECUTED",
        "checks_total": len(checks),
        "checks_passed": sum(1 for row in checks if row["passed"]),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "runner": fingerprint(RUNNER),
        "dispatch": fingerprint(DISPATCH),
        "truth_table_cases": len(truth_cases),
        "runner_main_executed": False,
        "query_api_called": False,
        "scientific_execution_performed": False,
        "test_accessed": False,
        "benchmark_admitted": False,
        "verdict": (
            "PASS_R6_PC0_QUERY_ATTEMPT002_STATIC_VALIDATION"
            if not failures
            else "REWORK_REQUIRED_R6_PC0_QUERY_ATTEMPT002"
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
