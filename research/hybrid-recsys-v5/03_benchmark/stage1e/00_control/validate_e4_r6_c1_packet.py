from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
OUTPUT_ROOT = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ai/"
    "E4_R6C1_materialization_command_packet"
)

EXPECTED_FILES = [
    "dataset_materialization_packet.json",
    "environment_materialization_packet.json",
    "recbole_dataset_bridge_packet.json",
    "execution_boundary_and_negative_assertions.json",
    "audit_handoff.json",
]
EXPECTED_CANDIDATE = "R5-CAND-RECBOLE-BPR-ML100K-001"
EXPECTED_REVISION = "9a6f63d8d4a5b989fe27955a833f813a6d86041e"
EXPECTED_TREE = "08915121fea069a30f7e3e97a72e16e7e76d43c6"
ENTRY_COMMIT = "60e51b017f5a37e9839c09e2ab014ba0f9a29b4d"
DATA_ROOT = (
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6"
    r"\official_source\grouplens_ml100k\attempt-001"
)
ENV_ROOT = (
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    r"\recbole_bpr_ml100k_py3119_cpu\attempt-001"
)
SOURCE_ROOT = (
    r"E:\UIT\cv\backend\research\hybrid-recsys-v5\03_benchmark\stage1e"
    r"\materialized_sources\r5\recbole_v1_2_1_9a6f63d"
)
STAGING_ROOT = ENV_ROOT + r"\source-staging\recbole_v1_2_1_9a6f63d"

EXPECTED_PINS = [
    "pip==24.0",
    "setuptools==69.5.1",
    "wheel==0.43.0",
    "torch==2.2.2+cpu",
    "numpy==1.26.4",
    "scipy==1.11.4",
    "pandas==2.1.4",
    "scikit-learn==1.3.2",
    "PyYAML==6.0.2",
    "tqdm==4.66.5",
    "colorlog==4.7.2",
    "colorama==0.4.4",
    "texttable==1.7.0",
    "tensorboard==2.15.2",
    "ray==2.6.3",
    "thop==0.1.1.post2207130030",
    "tabulate==0.9.0",
    "plotly==5.18.0",
    "psutil==5.9.8",
    "recbole==1.2.1+local.9a6f63d",
]

DATA_COMMAND_IDS = [
    "M00_CREATE_EMPTY_NON_GIT_ATTEMPT",
    "M01_FETCH_OFFICIAL_README",
    "M02_FETCH_OFFICIAL_CHECKSUM",
    "M03_FETCH_OFFICIAL_ARCHIVE",
    "M04_VERIFY_AND_PROMOTE_DOWNLOADS",
    "M05_SAFE_EXTRACT_AND_HASH",
    "M06_CONVERT_U_DATA_TO_RECBOLE_INTER_AND_EXPECTED_MAPS",
    "M07_RECONCILE_RAW_TO_ATOMIC",
]
ENV_COMMAND_IDS = [
    "E00_CREATE_EXTERNAL_IMMUTABLE_ATTEMPT",
    "E01_FETCH_OFFICIAL_CPYTHON_INSTALLER",
    "E02_FETCH_OFFICIAL_CPYTHON_SIGSTORE",
    "E03_VERIFY_AND_PROMOTE_CPYTHON_BOOTSTRAP",
    "E04_INSTALL_LOCAL_CPYTHON_3119_AMD64",
    "E05_VERIFY_EXACT_LOCAL_RUNTIME_IDENTITY",
    "E06_VERIFY_FROZEN_SOURCE_MANIFEST",
    "E07_CREATE_ISOLATED_VENV",
    "E08_VERIFY_BUNDLED_PIP_24",
    "E09_WRITE_LITERAL_PIN_FILES",
    "E10_DOWNLOAD_TORCH_CPU_WHEEL",
    "E11_RESOLVE_AND_DOWNLOAD_PYPI_WHEELS",
    "E12_ASSERT_WHEEL_ONLY_CPU_CLOSURE",
    "E13_CAPTURE_WHEEL_HASHES_AND_HASHED_REQUIREMENTS",
    "E14_OFFLINE_RESOLUTION_REPORT",
    "E15_INSTALL_HASHED_THIRD_PARTY_CLOSURE",
    "E16_COPY_VERIFIED_SOURCE_TO_STAGING",
    "E17_BUILD_LOCAL_RECBOLE_WHEEL",
    "E18_HASH_LOCAL_RECBOLE_WHEEL",
    "E19_INSTALL_HASHED_LOCAL_RECBOLE_WHEEL",
    "E20_CAPTURE_PIP_CHECK",
    "E21_CAPTURE_FROZEN_INVENTORY",
    "E22_CAPTURE_PIP_INSPECT",
    "E23_BOUNDED_IMPORT_AND_VERSION_CHECK",
    "E24_BOUNDED_SYNTAX_CHECK",
]
BRIDGE_COMMAND_IDS = [
    "B00_RESOLVE_INSTALLED_PACKAGE_AND_REQUIRE_ABSENT_TARGET",
    "B01_BINARY_COPY_CANONICAL_INTER_AND_WRITE_RECEIPT",
    "B02_CONFIG_ONLY_RESOLVED_PATH_CHECK",
]

DATA_URLS = [
    "https://files.grouplens.org/datasets/movielens/ml-100k-README.txt",
    "https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5",
    "https://files.grouplens.org/datasets/movielens/ml-100k.zip",
]
ENV_BOOTSTRAP_URLS = [
    "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe",
    "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe.sigstore",
]
ENV_INDEXES = [
    "https://pypi.org/simple",
    "https://download.pytorch.org/whl/cpu",
]
ENV_HOSTS = [
    "www.python.org",
    "pypi.org",
    "files.pythonhosted.org",
    "download.pytorch.org",
    "download-r2.pytorch.org",
]

TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}

FORBIDDEN_EXECUTABLE_PATTERNS = {
    "run_recbole": re.compile(r"\brun_recbole(?:\.py)?\b", re.I),
    "quick_start_execution": re.compile(
        r"quick_start\.(?:run_recbole|objective_function)|"
        r"from\s+recbole\.quick_start\s+import",
        re.I,
    ),
    "trainer_construction": re.compile(r"\bTrainer\s*\(", re.I),
    "fit_call": re.compile(r"\.fit\s*\(", re.I),
    "evaluate_call": re.compile(r"\.evaluate\s*\(", re.I),
    "dataset_construction": re.compile(r"\bDataset\s*\(", re.I),
    "create_dataset": re.compile(r"\bcreate_dataset\s*\(", re.I),
    "data_preparation": re.compile(r"\bdata_preparation\s*\(", re.I),
    "load_data": re.compile(r"\bload_data\s*\(", re.I),
    "hyper_tuning": re.compile(r"\bHyperTuning\s*\(", re.I),
    "hyperopt": re.compile(r"\bhyperopt\b", re.I),
    "ray_worker": re.compile(r"\btune\.run\s*\(|\bray\.init\s*\(|\bray\s+start\b", re.I),
    "distributed": re.compile(
        r"torchrun|torch\.distributed\.init_process_group|distributed\.launch", re.I
    ),
    "wandb": re.compile(r"\bwandb\.init\s*\(|\blog_wandb['\"]?\s*[:=]\s*true", re.I),
    "checkpoint_result_retrieval": re.compile(
        r"download[^\r\n]{0,40}(?:checkpoint|pretrained|result)|"
        r"(?:checkpoint|pretrained)[^\r\n]{0,40}(?:http|s3)",
        re.I,
    ),
    "project_v5_test": re.compile(
        r"project[-_\\/]?v5[\\\/][^\r\n]*test|"
        r"harmonized[_-]?v5[\\\/][^\r\n]*test",
        re.I,
    ),
    "benchmark_admission": re.compile(
        r"admit_benchmark|accept_result|paper_metric|paper_number", re.I
    ),
}


class StrictJsonError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate key: {key}")
        normalized = key.casefold()
        if normalized in folded and folded[normalized] != key:
            raise StrictJsonError(f"case-colliding keys: {folded[normalized]} / {key}")
        folded[normalized] = key
        result[key] = value
    return result


def strict_load(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=strict_object
    )
    if not isinstance(value, dict):
        raise StrictJsonError(f"top-level object required: {path}")
    return value


def fingerprint(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    canonical = text.encode("utf-8")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "raw_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_lf_bytes": len(canonical),
        "canonical_lf_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def check(
    checks: dict[str, bool], failures: list[str], check_id: str, condition: bool
) -> None:
    checks[check_id] = bool(condition)
    if not condition:
        failures.append(check_id)


def is_reparse(path: Path) -> bool:
    try:
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def windows_under(path_text: str, root_text: str) -> bool:
    path = str(PureWindowsPath(path_text)).casefold().rstrip("\\")
    root = str(PureWindowsPath(root_text)).casefold().rstrip("\\")
    return path == root or path.startswith(root + "\\")


def command_rows(
    dataset: dict[str, Any], environment: dict[str, Any], bridge: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    data_rows = [row for row in dataset.get("commands", []) if isinstance(row, dict)]
    env_rows = [
        row
        for group in environment.get("command_groups", [])
        if isinstance(group, dict)
        for row in group.get("commands", [])
        if isinstance(row, dict)
    ]
    bridge_rows = [row for row in bridge.get("commands", []) if isinstance(row, dict)]
    return data_rows, env_rows, bridge_rows


def row_id(row: dict[str, Any]) -> str | None:
    value = row.get("command_id", row.get("id"))
    return value if isinstance(value, str) else None


def argv_is_literal_and_coherent(row: dict[str, Any]) -> bool:
    executable = row.get("executable")
    arguments = row.get("arguments")
    argv = row.get("argv")
    return (
        isinstance(executable, str)
        and bool(executable)
        and isinstance(arguments, list)
        and isinstance(argv, list)
        and all(isinstance(token, str) for token in arguments)
        and all(isinstance(token, str) for token in argv)
        and argv == [executable, *arguments]
        and isinstance(row.get("timeout_seconds"), int)
        and row["timeout_seconds"] > 0
        and isinstance(row.get("network"), bool)
    )


def command_text(row: dict[str, Any]) -> str:
    return "\n".join(str(token) for token in row.get("argv", []))


def parse_python_source(source: str, label: str, errors: list[str]) -> None:
    try:
        tree = ast.parse(source, filename=label, mode="exec")
    except SyntaxError as exc:
        errors.append(f"{label}:{exc.msg}:line={exc.lineno}:offset={exc.offset}")
        return
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "exec"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            parse_python_source(node.args[0].value, f"{label}:nested_exec", errors)


def syntax_scan(rows: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    python_errors: list[str] = []
    powershell_errors: list[str] = []
    parser = (
        "$s=[Console]::In.ReadToEnd();$t=$null;$e=$null;"
        "[System.Management.Automation.Language.Parser]::ParseInput($s,[ref]$t,[ref]$e)"
        "|Out-Null;if($e.Count -gt 0){$e|ForEach-Object{$_.Message};exit 1}"
    )
    for row in rows:
        command_id = row_id(row) or "UNKNOWN"
        argv = row.get("argv", [])
        if not isinstance(argv, list):
            continue
        for index, token in enumerate(argv[:-1]):
            if token in {"-c", "-B"}:
                source_index = index + 1
                if token == "-B" and argv[source_index] == "-c" and source_index + 1 < len(argv):
                    source_index += 1
                if argv[source_index] == "-c" and source_index + 1 < len(argv):
                    source_index += 1
                source = argv[source_index]
                if isinstance(source, str) and (
                    token == "-c" or (token == "-B" and "python.exe" in str(argv[0]).casefold())
                ):
                    parse_python_source(source, command_id, python_errors)
                    break
        executable = str(row.get("executable", "")).casefold()
        if executable.endswith("powershell.exe") and "-Command" in argv:
            index = argv.index("-Command")
            if index + 1 >= len(argv):
                powershell_errors.append(f"{command_id}:missing -Command script")
                continue
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", parser],
                input=str(argv[index + 1]),
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stdout + completed.stderr).strip()
                powershell_errors.append(f"{command_id}:{detail}")
    return python_errors, powershell_errors


def exact_network_tokens(rows: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        if row.get("network") is not True:
            continue
        values.extend(
            token
            for token in row.get("argv", [])
            if isinstance(token, str) and token.startswith("https://")
        )
    return values


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    observed = sorted(path.name for path in OUTPUT_ROOT.iterdir()) if OUTPUT_ROOT.is_dir() else []
    check(checks, failures, "exact_five_file_set", observed == sorted(EXPECTED_FILES))
    check(
        checks,
        failures,
        "five_regular_non_link_non_reparse_files",
        OUTPUT_ROOT.is_dir()
        and not OUTPUT_ROOT.is_symlink()
        and not is_reparse(OUTPUT_ROOT)
        and all(
            (OUTPUT_ROOT / name).is_file()
            and not (OUTPUT_ROOT / name).is_symlink()
            and not is_reparse(OUTPUT_ROOT / name)
            for name in EXPECTED_FILES
        ),
    )

    documents: dict[str, dict[str, Any]] = {}
    output_rows: list[dict[str, Any]] = []
    strict_errors: list[str] = []
    for name in EXPECTED_FILES:
        path = OUTPUT_ROOT / name
        try:
            documents[name] = strict_load(path)
            output_rows.append(fingerprint(path))
        except Exception as exc:
            strict_errors.append(f"{name}:{exc}")
    check(checks, failures, "strict_utf8_json_5_of_5", not strict_errors and len(documents) == 5)
    if strict_errors:
        result = {
            "schema_version": "stage1e-rebaseline-v2-e4-r6-c1-validation-result-1.0",
            "passed": False,
            "verdict": "FAIL_R6_C1_REWORK_REQUIRED",
            "failure_count": len(failures) + len(strict_errors),
            "failures": failures + strict_errors,
            "checks": checks,
            "outputs": output_rows,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    dataset = documents["dataset_materialization_packet.json"]
    environment = documents["environment_materialization_packet.json"]
    bridge = documents["recbole_dataset_bridge_packet.json"]
    boundary = documents["execution_boundary_and_negative_assertions.json"]
    handoff = documents["audit_handoff.json"]

    g0 = subprocess.run(
        [sys.executable, str(CONTROL / "validate_e4_r6_g0_gate.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    check(
        checks,
        failures,
        "r6_g0_replay_still_passes",
        g0.returncode == 0
        and "PASS_R6_G0_FROZEN_31_OF_31_READY_FOR_R6_C1" in g0.stdout,
    )

    dispatch = strict_load(CONTROL / "rebaseline_v2_e4_r6_c1_dispatch.json")
    frozen_controls_ok = True
    for row in dispatch.get("frozen_controls", []):
        path = ROOT / str(row.get("path", ""))
        if not path.is_file():
            frozen_controls_ok = False
            continue
        actual = fingerprint(path)
        frozen_controls_ok &= (
            row.get("canonical_lf_bytes") == actual["canonical_lf_bytes"]
            and row.get("canonical_lf_sha256") == actual["canonical_lf_sha256"]
        )
    check(
        checks,
        failures,
        "entry_commit_dispatch_and_three_frozen_controls_replayed",
        dispatch.get("entry_commit") == ENTRY_COMMIT
        and dispatch.get("entry_gate") == "PASS_R6_G0_FROZEN_31_OF_31_READY_FOR_R6_C1"
        and len(dispatch.get("frozen_controls", [])) == 3
        and frozen_controls_ok,
    )

    check(
        checks,
        failures,
        "all_artifacts_proposal_only_no_execution",
        all(
            document.get("proposal_only") is True
            and document.get("execution_performed") is False
            and document.get("execution_authorized") is False
            for document in documents.values()
        ),
    )
    check(
        checks,
        failures,
        "truth_state_closed_5_of_5",
        all(document.get("truth_state") == TRUTH for document in documents.values()),
    )

    entry = handoff.get("entry_state", {})
    replay = handoff.get("input_replay", {})
    model = handoff.get("actual_model_profile", {})
    authorship = handoff.get("authorship_boundary", {})
    check(
        checks,
        failures,
        "worker_entry_and_31_19_replay_exact",
        handoff.get("source_commit") == ENTRY_COMMIT
        and entry.get("exact_entry_commit") == ENTRY_COMMIT
        and entry.get("entry_gate_verdict") == "PASS_R6_G0_FROZEN_31_OF_31_READY_FOR_R6_C1"
        and entry.get("frozen_inputs_verified") == entry.get("frozen_inputs_expected") == 31
        and entry.get("strict_json_inputs_verified") == entry.get("strict_json_inputs_expected") == 19
        and replay.get("raw_and_canonical_lf_replay") == "31_OF_31"
        and replay.get("strict_json_duplicate_and_case_collision_replay") == "19_OF_19"
        and replay.get("candidate_id") == EXPECTED_CANDIDATE
        and replay.get("recbole_revision") == EXPECTED_REVISION
        and replay.get("recbole_git_tree") == EXPECTED_TREE,
    )
    check(
        checks,
        failures,
        "actual_worker_sol_high_fast",
        model
        == {
            "display": "Sol High Fast",
            "runtime_model": "gpt-5.6-sol",
            "reasoning": "high",
            "service_tier": "priority",
        },
    )
    check(
        checks,
        failures,
        "exclusive_authorship_boundary_and_no_commit",
        authorship.get("exclusive_write_root")
        == OUTPUT_ROOT.relative_to(ROOT).as_posix()
        and authorship.get("exact_file_count") == 5
        and authorship.get("exact_files") == EXPECTED_FILES
        and authorship.get("files_outside_exclusive_root_written_by_worker") == 0
        and authorship.get("worker_commit_created") is False
        and authorship.get("new_source_interpretation_performed") is False
        and authorship.get("scientific_choice_changed") is False,
    )

    data_rows, env_rows, bridge_rows = command_rows(dataset, environment, bridge)
    all_rows = data_rows + env_rows + bridge_rows
    data_ids = [row_id(row) for row in data_rows]
    env_ids = [row_id(row) for row in env_rows]
    bridge_ids = [row_id(row) for row in bridge_rows]
    check(
        checks,
        failures,
        "exact_8_25_3_unique_ordered_command_ids",
        data_ids == DATA_COMMAND_IDS
        and env_ids == ENV_COMMAND_IDS
        and bridge_ids == BRIDGE_COMMAND_IDS
        and len(set(data_ids + env_ids + bridge_ids)) == 36
        and dataset.get("command_order") == DATA_COMMAND_IDS
        and environment.get("command_order") == ENV_COMMAND_IDS
        and bridge.get("command_order") == BRIDGE_COMMAND_IDS,
    )
    check(
        checks,
        failures,
        "all_36_literal_argv_coherent_and_bounded",
        len(all_rows) == 36 and all(argv_is_literal_and_coherent(row) for row in all_rows),
    )

    python_errors, powershell_errors = syntax_scan(all_rows)
    check(checks, failures, "embedded_python_ast_parse_pass", not python_errors)
    check(checks, failures, "powershell_parser_pass_without_execution", not powershell_errors)

    forbidden_matches: list[str] = []
    for row in all_rows:
        text = command_text(row)
        for rule, pattern in FORBIDDEN_EXECUTABLE_PATTERNS.items():
            if pattern.search(text):
                forbidden_matches.append(f"{row_id(row)}:{rule}")
    check(checks, failures, "independent_forbidden_execution_scan_36_of_36", not forbidden_matches)

    data_network_ids = [row_id(row) for row in data_rows if row.get("network") is True]
    env_network_ids = [row_id(row) for row in env_rows if row.get("network") is True]
    bridge_network_ids = [row_id(row) for row in bridge_rows if row.get("network") is True]
    check(
        checks,
        failures,
        "exact_network_command_ids",
        data_network_ids == DATA_COMMAND_IDS[1:4]
        and env_network_ids
        == [
            "E01_FETCH_OFFICIAL_CPYTHON_INSTALLER",
            "E02_FETCH_OFFICIAL_CPYTHON_SIGSTORE",
            "E10_DOWNLOAD_TORCH_CPU_WHEEL",
            "E11_RESOLVE_AND_DOWNLOAD_PYPI_WHEELS",
        ]
        and bridge_network_ids == [],
    )
    data_network_tokens = exact_network_tokens(data_rows)
    env_network_tokens = exact_network_tokens(env_rows)
    check(
        checks,
        failures,
        "exact_network_urls_indexes_and_hosts",
        data_network_tokens == DATA_URLS
        and env_network_tokens
        == [ENV_BOOTSTRAP_URLS[0], ENV_BOOTSTRAP_URLS[1], ENV_INDEXES[1], ENV_INDEXES[0]]
        and all(urlparse(url).hostname in ENV_HOSTS for url in env_network_tokens)
        and dataset.get("network_allowlist", {}).get("exact_urls") == DATA_URLS
        and environment.get("network_allowlist", {}).get("hosts") == ENV_HOSTS
        and environment.get("network_allowlist", {}).get("exact_bootstrap_urls")
        == ENV_BOOTSTRAP_URLS
        and environment.get("network_allowlist", {}).get("indexes") == ENV_INDEXES,
    )
    curl_rows = [
        row
        for row in data_rows + env_rows
        if str(row.get("executable", "")).casefold() == "curl.exe"
    ]
    check(
        checks,
        failures,
        "curl_ignores_ambient_config_and_proxy",
        len(curl_rows) == 5
        and all(
            row.get("arguments", [])[:1] == ["--disable"]
            and "--proxy" in row.get("arguments", [])
            and row.get("arguments", [])[row.get("arguments", []).index("--proxy") + 1] == ""
            for row in curl_rows
        ),
    )

    official = dataset.get("official_identity", {})
    checksum = dataset.get("checksum_semantics", {})
    inventory = dataset.get("safe_zip_inventory", {})
    transform = dataset.get("frozen_transformation", {})
    data_roots = dataset.get("intended_write_roots", {})
    check(
        checks,
        failures,
        "dataset_candidate_provider_archive_checksum_exact",
        dataset.get("candidate_id") == EXPECTED_CANDIDATE
        and dataset.get("pinned_recbole_revision") == EXPECTED_REVISION
        and official.get("provider") == "GroupLens Research Project, University of Minnesota"
        and official.get("dataset") == "MovieLens 100K"
        and official.get("official_archive_url") == DATA_URLS[2]
        and official.get("official_current_checksum_url") == DATA_URLS[1]
        and official.get("archive_expected_bytes") == 4_924_029
        and checksum.get("current_provider_sidecar_expected_md5")
        == "0e33842e24a9c977be4e0107933c0723"
        and checksum.get("meaning")
        == "CURRENT_PROVIDER_SIDECAR_EXPECTATION_ONLY_NOT_A_HISTORICAL_CHECKSUM_CLAIM"
        and checksum.get("archive_local_md5_replay_required") is True
        and checksum.get("archive_local_sha256_capture_required") is True,
    )
    check(
        checks,
        failures,
        "dataset_safe_zip_exact_23_regular_members",
        inventory.get("exact_logical_file_count") == 23
        and len(inventory.get("exact_logical_files", [])) == 23
        and len(set(inventory.get("exact_logical_files", []))) == 23
        and "u.data" in inventory.get("exact_logical_files", [])
        and inventory.get("regular_files_only") is True
        and inventory.get("links_allowed") is False
        and inventory.get("reparse_points_allowed") is False
        and inventory.get("unexpected_files_allowed") is False
        and inventory.get("path_escape_allowed") is False,
    )
    check(
        checks,
        failures,
        "dataset_transform_100000_no_filter_sort_rewrite",
        transform.get("transformation_id") == "GL-ML100K-U-DATA-TO-RECBOLE-INTER-1.0"
        and transform.get("input_rows") == transform.get("output_data_rows") == 100_000
        and transform.get("user_domain_size") == 943
        and transform.get("item_domain_size") == 1682
        and transform.get("row_order_preserved") is True
        and all(
            transform.get(key) is False
            for key in ["row_filtering", "deduplication", "sorting", "id_rewriting", "timestamp_rewriting"]
        )
        and transform.get("rating_cutoff") is None
        and transform.get("destination_exact_file_set") == ["ml-100k.inter"]
        and len(transform.get("id_map_receipts", [])) == 2
        and transform.get("reconciliation_receipt")
        == r"receipts\raw_to_atomic_reconciliation.json",
    )
    check(
        checks,
        failures,
        "dataset_external_root_only_harmonized_and_repo_writes_denied",
        data_roots.get("official_source_attempt_root") == DATA_ROOT
        and data_roots.get("harmonized_v5_write_allowed") is False
        and data_roots.get("writes_inside_project_repository_allowed") is False
        and not windows_under(DATA_ROOT, r"E:\UIT\cv\backend")
        and not Path(DATA_ROOT).exists(),
    )
    data_resources = dataset.get("resource_and_timeout_bounds", {})
    check(
        checks,
        failures,
        "dataset_resource_retry_concurrency_bounds",
        data_resources.get("hard_packet_timeout_seconds") == 1800
        and data_resources.get("maximum_attempt_root_bytes") == 2_147_483_648
        and data_resources.get("maximum_resident_memory_bytes_per_process") == 536_870_912
        and data_resources.get("maximum_cpu_processes") == 1
        and data_resources.get("maximum_parallel_commands") == 1
        and data_resources.get("retry_count") == 0,
    )

    profile = environment.get("environment_profile", {})
    bootstrap = environment.get("cpython_bootstrap", {})
    source_lock = environment.get("recbole_source_lock", {})
    env_write = environment.get("expected_write_set", {})
    check(
        checks,
        failures,
        "environment_external_exact_python_3119_no_ambient_interpreter",
        profile.get("attempt_root") == ENV_ROOT
        and profile.get("system_python_3_11_3_reuse_allowed") is False
        and profile.get("py_launcher_resolution_used") is False
        and not windows_under(ENV_ROOT, r"E:\UIT\cv\backend")
        and not Path(ENV_ROOT).exists()
        and bootstrap.get("installer_url") == ENV_BOOTSTRAP_URLS[0]
        and bootstrap.get("sigstore_url") == ENV_BOOTSTRAP_URLS[1]
        and bootstrap.get("official_page_expected_md5")
        == "e8dcd502e34932eebcaf1be056d5cbcd"
        and bootstrap.get("authenticode_status_required") == "Valid"
        and bootstrap.get("runtime_identity")
        == {
            "implementation": "CPython",
            "version": "3.11.9",
            "bitness": 64,
            "sys_platform": "win32",
            "required_binary_tag": "cp311-cp311-win_amd64",
        },
    )
    check(
        checks,
        failures,
        "environment_exact_twenty_direct_requirements",
        environment.get("direct_requirement_count") == 20
        and environment.get("exact_direct_requirements") == EXPECTED_PINS,
    )
    check(
        checks,
        failures,
        "environment_local_recbole_revision_tree_no_pypi_editable_or_source_edit",
        source_lock.get("revision") == EXPECTED_REVISION
        and source_lock.get("git_tree") == EXPECTED_TREE
        and source_lock.get("installation_source") == "HASH_LOCKED_LOCAL_SOURCE_WHEEL_ONLY"
        and source_lock.get("pypi_recbole_allowed") is False
        and source_lock.get("editable_install_allowed") is False
        and source_lock.get("source_modification_allowed") is False,
    )
    install = next(row for row in env_rows if row_id(row) == "E04_INSTALL_LOCAL_CPYTHON_3119_AMD64")
    required_installer_args = {
        "/quiet",
        "InstallAllUsers=0",
        f"TargetDir={ENV_ROOT}\\runtime",
        "PrependPath=0",
        "AppendPath=0",
        "AssociateFiles=0",
        "Shortcuts=0",
        "Include_launcher=0",
        "Include_pip=1",
        "Include_test=0",
    }
    check(
        checks,
        failures,
        "python_installer_literal_local_nonambient_options",
        required_installer_args.issubset(set(install.get("arguments", [])))
        and not any("py.exe" in token.casefold() for token in install.get("argv", [])),
    )
    check(
        checks,
        failures,
        "environment_write_root_offline_hash_and_cpu_contract",
        env_write.get("only_allowed_persistent_root") == ENV_ROOT
        and env_write.get("outside_root_write_policy") == "STOP"
        and environment.get("wheelhouse_receipt_contract", {}).get("binary_wheels_only") is True
        and environment.get("wheelhouse_receipt_contract", {}).get("offline_flags")
        == ["--no-index", "--find-links", "--require-hashes"]
        and environment.get("wheelhouse_receipt_contract", {}).get("pip_check_required") is True,
    )
    env_resources = environment.get("resource_and_timeout_bounds", {})
    check(
        checks,
        failures,
        "environment_resource_retry_concurrency_bounds",
        env_resources.get("hard_packet_timeout_seconds") == 7200
        and env_resources.get("maximum_total_attempt_bytes") == 4_294_967_296
        and env_resources.get("maximum_resident_memory_bytes_per_process") == 2_147_483_648
        and env_resources.get("maximum_cpu_processes") == 1
        and env_resources.get("maximum_parallel_commands") == 1
        and env_resources.get("internal_pip_retry_count") == 0
        and env_resources.get("external_identical_transient_retry_count") == 1
        and env_resources.get("gpu_devices") == 0
        and env_resources.get("maximum_ray_workers") == 0,
    )

    env_by_id = {row_id(row): row for row in env_rows}
    pip_isolated_ids = [
        "E10_DOWNLOAD_TORCH_CPU_WHEEL",
        "E11_RESOLVE_AND_DOWNLOAD_PYPI_WHEELS",
        "E14_OFFLINE_RESOLUTION_REPORT",
        "E15_INSTALL_HASHED_THIRD_PARTY_CLOSURE",
        "E17_BUILD_LOCAL_RECBOLE_WHEEL",
        "E19_INSTALL_HASHED_LOCAL_RECBOLE_WHEEL",
    ]
    check(
        checks,
        failures,
        "pip_resolution_build_install_commands_are_isolated",
        all("--isolated" in command_text(env_by_id[key]) for key in pip_isolated_ids),
    )
    e16_text = command_text(env_by_id["E16_COPY_VERIFIED_SOURCE_TO_STAGING"])
    e17_text = command_text(env_by_id["E17_BUILD_LOCAL_RECBOLE_WHEEL"])
    staging_receipt_markers = [
        "source-staging",
        "selected_blob_manifest.json",
        "source_tree_manifest.json",
        EXPECTED_REVISION,
        EXPECTED_TREE,
        "sha256",
        "receipt",
    ]
    check(
        checks,
        failures,
        "staging_copy_replays_exact_source_and_destination_hash_manifest",
        all(marker.casefold() in e16_text.casefold() for marker in staging_receipt_markers)
        and SOURCE_ROOT.casefold() in e16_text.casefold()
        and STAGING_ROOT.casefold() in e16_text.casefold()
        and any(token in e16_text.casefold() for token in ["reparse", "st_file_attributes"])
        and any(token in e16_text.casefold() for token in ["unexpected", "set(", "setequals"]),
    )
    check(
        checks,
        failures,
        "wheel_build_revalidates_staging_immediately_before_build",
        STAGING_ROOT.casefold() in e17_text.casefold()
        and "pip" in e17_text.casefold()
        and "wheel" in e17_text.casefold()
        and "sha256" in e17_text.casefold()
        and "source-staging" in e17_text.casefold()
        and any(token in e17_text.casefold() for token in ["selected_blob_manifest", "staging-verification", "staging_verification"]),
    )
    check(
        checks,
        failures,
        "wheel_build_uses_verified_ephemeral_copy_and_preserves_staging",
        all(
            marker in e17_text.casefold()
            for marker in ["source-staging", "temp", "build-source", "sha256", "pip", "wheel"]
        )
        and any(
            marker in e17_text.casefold()
            for marker in ["postbuild", "post_build", "post-build", "after_build"]
        )
        and any(marker in e17_text.casefold() for marker in ["unexpected", "exact_file", "set("])
        and any(marker in e17_text.casefold() for marker in ["subprocess", "start-process", "& '"]),
    )
    e24_text = command_text(env_by_id["E24_BOUNDED_SYNTAX_CHECK"])
    check(
        checks,
        failures,
        "syntax_check_is_read_only_and_generates_no_bytecode",
        "compileall" not in e24_text.casefold()
        and "compile(" in e24_text.casefold()
        and "exec" in e24_text.casefold()
        and "syntax" in e24_text.casefold()
        and any(marker in e24_text.casefold() for marker in ["read_bytes", "read_text", "open("])
        and any(
            marker in e24_text.casefold()
            for marker in ["write_text", "writealltext", "stream.write", ".open('xb')"]
        ),
    )
    deterministic_rows = [env_by_id[key] for key in ENV_COMMAND_IDS[20:23] + [ENV_COMMAND_IDS[24]]]
    deterministic_text = "\n".join(command_text(row) for row in deterministic_rows).casefold()
    check(
        checks,
        failures,
        "powershell_text_receipts_are_utf8_no_bom_deterministic",
        "set-content" not in deterministic_text
        and all(
            "UTF-8_NO_BOM" in str(row.get("receipt_encoding", ""))
            and any(
                marker in command_text(row).casefold()
                for marker in ["writealltext", "stream.write", ".open('xb')"]
            )
            for row in deterministic_rows
        ),
    )

    source_fact = bridge.get("source_fact", {})
    bridge_contract = bridge.get("bridge_contract", {})
    bridge_write = bridge.get("expected_write_set", {})
    allowed_check = bridge.get("allowed_check", {})
    evidence = {
        row.get("path"): row.get("raw_sha256")
        for row in source_fact.get("evidence", [])
        if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "bridge_pinned_config_loader_s3_source_facts_hash_bound",
        evidence
        == {
            "recbole/config/configurator.py": "a5f3f3ba902537d2f678c0f011e7a6d5d706606fae041074913bb651811f1aed",
            "recbole/data/dataset/dataset.py": "9e752eea85d84280f1ea5c752a3be055ab8deb1c03c1196d1a02f46065deee5e",
            "recbole/properties/dataset/url.yaml": "6bd6c438a9b2cce7fa8d81ea6dbe0333b37f83270046d37162ce2775ada51d03",
        }
        and source_fact.get("recbole_s3_provider_authority") is False,
    )
    check(
        checks,
        failures,
        "bridge_binary_exact_one_file_copy_no_links_or_source_edit",
        bridge_contract.get("canonical_source_file")
        == DATA_ROOT + r"\recbole_atomic\ml-100k\ml-100k.inter"
        and bridge_contract.get("destination_exact_file_set") == ["ml-100k.inter"]
        and bridge_contract.get("item_or_user_files_allowed") is False
        and bridge_contract.get("repository_dataset_blob_used") is False
        and bridge_contract.get("source_modification_allowed") is False
        and bridge_contract.get("symlink_hardlink_or_junction_allowed") is False
        and bridge_contract.get("copy_mode") == "BINARY_BYTES_ONLY_NO_DECODE_OR_TRANSFORMATION"
        and bridge_contract.get("source_destination_byte_count_equal_required") is True
        and bridge_contract.get("source_destination_sha256_equal_required") is True
        and bridge_contract.get("source_destination_data_row_count_equal_required") is True
        and bridge_contract.get("expected_data_rows") == 100_000
        and bridge_contract.get("receipts_outside_consumer_directory") is True
        and bridge_write.get("destination_directory_exact_final_files") == ["ml-100k.inter"]
        and bridge_write.get("writes_outside_environment_attempt_root_allowed") is False
        and bridge_write.get("writes_to_repository_allowed") is False
        and bridge_write.get("writes_to_canonical_source_allowed") is False,
    )
    check(
        checks,
        failures,
        "bridge_config_only_no_dataset_load_rows_or_s3",
        bridge.get("network_allowlist", {}).get("all_network_denied") is True
        and allowed_check.get("dataset_construction") is False
        and allowed_check.get("dataset_loading") is False
        and allowed_check.get("interaction_rows_opened_by_config_check") == 0
        and allowed_check.get("s3_access") is False,
    )

    counts = boundary.get("command_counts", {})
    order = boundary.get("command_order", {})
    graph = boundary.get("cross_packet_dependency_graph", {})
    scan = boundary.get("executable_argv_scan", {})
    scan_entries = scan.get("entries", []) if isinstance(scan, dict) else []
    check(
        checks,
        failures,
        "boundary_counts_orders_and_36_scan_entries_exact",
        counts
        == {
            "dataset_materialization_packet": 8,
            "environment_materialization_packet": 25,
            "recbole_dataset_bridge_packet": 3,
            "total": 36,
        }
        and order.get("dataset") == DATA_COMMAND_IDS
        and order.get("environment") == ENV_COMMAND_IDS
        and order.get("bridge") == BRIDGE_COMMAND_IDS
        and scan.get("scanned_command_count") == 36
        and scan.get("rejected_command_count") == 0
        and scan.get("all_literal_argv") is True
        and len(scan_entries) == 36
        and [row.get("command_id") for row in scan_entries]
        == DATA_COMMAND_IDS + ENV_COMMAND_IDS + BRIDGE_COMMAND_IDS
        and all(
            row.get("argv_recomposition_match") is True
            and row.get("forbidden_execution_matches") == []
            and row.get("scan_verdict") == "PASS"
            for row in scan_entries
        ),
    )
    check(
        checks,
        failures,
        "boundary_dependency_graph_has_only_m0_m1_then_bridge",
        graph.get("prerequisite") == "CENTRAL_VALIDATION_OF_EXACT_R6_C1_FIVE_FILE_PACKET"
        and [row.get("stage") for row in graph.get("independent_after_prerequisite", [])]
        == ["R6-M0", "R6-M1"]
        and all(
            row.get("scientific_execution") is False
            for row in graph.get("independent_after_prerequisite", [])
        )
        and graph.get("bridge", {}).get("depends_on")
        == ["R6-M0_SUCCESS_WITH_INDEPENDENT_RECEIPTS", "R6-M1_SUCCESS_WITH_INDEPENDENT_RECEIPTS"]
        and graph.get("bridge", {}).get("may_run_in_parallel_with_m0_or_m1") is False
        and graph.get("training_evaluation_or_test_dependency_present") is False,
    )
    roots = boundary.get("aggregate_write_roots", {})
    resources = boundary.get("aggregate_resource_bounds", {})
    check(
        checks,
        failures,
        "boundary_exact_roots_resources_and_fail_closed_retry",
        roots.get("future_materialization_persistent_roots") == [DATA_ROOT, ENV_ROOT]
        and roots.get("repository_materialization_writes_allowed") is False
        and roots.get("harmonized_v5_writes_allowed") is False
        and roots.get("project_v5_test_writes_allowed") is False
        and resources.get("maximum_cpu_processes") == 1
        and resources.get("maximum_parallel_commands_per_packet") == 1
        and resources.get("aggregate_materialization_concurrency") == 2
        and resources.get("gpu_devices") == 0
        and resources.get("ray_workers") == 0
        and resources.get("dataset_retry_count") == 0
        and resources.get("environment_retry_count_per_network_command") == 1
        and resources.get("bridge_retry_count") == 0
        and len(boundary.get("failure_cleanup_and_immutable_retry_rules", [])) >= 7,
    )
    negative = boundary.get("negative_assertions", {})
    check(
        checks,
        failures,
        "boundary_all_negative_assertions_true",
        len(negative) >= 15 and all(value is True for value in negative.values()),
    )
    check(
        checks,
        failures,
        "boundary_and_handoff_do_not_authorize_materialization_or_science",
        boundary.get("authorization_effect", {}).get("central_validation_only") is True
        and boundary.get("authorization_effect", {}).get("materialization_authorized_by_this_artifact") is False
        and boundary.get("authorization_effect", {}).get("experiment_execution_authorized") is False
        and handoff.get("authorization", {}).get("authorized_next_action") == "CENTRAL_VALIDATION_OF_R6_C1"
        and handoff.get("authorization", {}).get("materialization_authorized") is False
        and handoff.get("authorization", {}).get("bridge_execution_authorized") is False
        and handoff.get("authorization", {}).get("experiment_execution_authorized") is False,
    )
    no_execution = handoff.get("no_execution_assertions", {})
    handoff_counts = handoff.get("command_counts", {})
    check(
        checks,
        failures,
        "handoff_zero_execution_and_exact_counts",
        handoff.get("verdict")
        in {
            "READY_FOR_CENTRAL_VALIDATION_OF_R6_C1_ONLY_FAIL_CLOSED",
            "READY_FOR_CENTRAL_REVALIDATION_OF_R6_C1_ONLY_FAIL_CLOSED",
        }
        and len(no_execution) >= 13
        and all(value is False for value in no_execution.values())
        and handoff_counts.get("dataset_materialization_packet") == 8
        and handoff_counts.get("environment_materialization_packet") == 25
        and handoff_counts.get("recbole_dataset_bridge_packet") == 3
        and handoff_counts.get("total_proposed_commands") == 36
        and handoff_counts.get("proposed_commands_executed") == 0
        and handoff_counts.get("materialization_commands_executed") == 0
        and handoff_counts.get("experiment_commands_executed") == 0,
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r6-c1-validation-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R6_C1_EXACT_COMMAND_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1"
            if passed
            else "FAIL_R6_C1_REWORK_REQUIRED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "mechanical_summary": {
            "checks_passed": sum(checks.values()),
            "checks_expected": len(checks),
            "output_files": len(output_rows),
            "strict_json_outputs": len(documents),
            "literal_argv_commands": len(all_rows),
            "python_syntax_errors": python_errors,
            "powershell_syntax_errors": powershell_errors,
            "forbidden_execution_matches": forbidden_matches,
            "data_network_tokens": data_network_tokens,
            "environment_network_tokens": env_network_tokens,
        },
        "outputs": output_rows,
        "central_rework_history": [
            {
                "finding_id": "R6-C1-F001",
                "severity": "BLOCKER",
                "finding": "The first packet revision verified the repository source before copy but did not replay the frozen file/hash manifest over source-staging before the wheel build.",
                "required_resolution": "Exact pre-copy and post-copy source/staging replay plus immediate pre-build staging verification.",
            },
            {
                "finding_id": "R6-C1-F002",
                "severity": "HARDENING",
                "finding": "The first packet revision used Windows PowerShell 5.1 Set-Content -Encoding utf8 for text receipts, which is BOM-dependent.",
                "required_resolution": "Deterministic UTF-8 without BOM receipt writes.",
            },
            {
                "finding_id": "R6-C1-F003",
                "severity": "MAJOR",
                "finding": "The first B02 record had a literal argv array that did not equal executable plus arguments.",
                "required_resolution": "All 36 records must satisfy argv == [executable] + arguments exactly.",
            },
            {
                "finding_id": "R6-C1-F004",
                "severity": "BLOCKER",
                "finding": "The first E24 syntax check used compileall and would create bytecode inside the hash-locked source-staging tree.",
                "required_resolution": "Perform read-only in-memory compile checks and write only an external deterministic receipt.",
            },
            {
                "finding_id": "R6-C1-F005",
                "severity": "BLOCKER",
                "finding": "A local setuptools wheel build can create build metadata in its input directory.",
                "required_resolution": "Build from an independently hash-replayed ephemeral copy and prove source-staging remains exact after the build.",
            },
            {
                "finding_id": "R6-C1-F006",
                "severity": "MAJOR",
                "finding": "Curl commands could inherit a user curl configuration or proxy route.",
                "required_resolution": "Disable default curl config and ambient proxy routing in every curl argv.",
            },
            {
                "finding_id": "R6-C1-F007",
                "severity": "MAJOR",
                "finding": "Pip resolution/build/install commands could inherit user configuration and PIP environment state.",
                "required_resolution": "Use pip isolated mode in every resolution, build and install surface.",
            },
        ],
        "materialization_gate_opened_by_this_validation": passed,
        "bridge_execution_authorized": False,
        "experiment_execution_authorized": False,
        "test_access_authorized": False,
        "benchmark_admission_authorized": False,
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
