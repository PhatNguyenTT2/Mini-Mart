from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
SOURCE_ROOT = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ai/"
    "E4_R6C1_materialization_command_packet"
)
OUTPUT_ROOT = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_aj/"
    "E4_R6C1R1_attempt002_command_packet"
)

EXPECTED_FILES = [
    "dataset_materialization_packet.json",
    "environment_materialization_packet.json",
    "recbole_dataset_bridge_packet.json",
    "execution_boundary_and_negative_assertions.json",
    "audit_handoff.json",
]

SOURCE_FINGERPRINTS = {
    "dataset_materialization_packet.json": (51905, "0f2daf0f4f9441046019991549006258aa0411b5d3c439b052f457e5f75eae66"),
    "environment_materialization_packet.json": (171024, "896fb502b7492d39fd8fd33489c1d739a04181d83a016ecf2be6d03a910cba6e"),
    "recbole_dataset_bridge_packet.json": (20469, "eb4b276a554360a24378061ba09319c540507270175bb3c083432d9cd63aa56b"),
    "execution_boundary_and_negative_assertions.json": (42087, "d0c775370b3bb618d926b1b36dc79379f8ca5ebd3b8be9e9fc7cc8697ad733a6"),
    "audit_handoff.json": (16739, "382977df2bf8ee903e75052226954e3287e80b6de853df75ee1c2d0b2f40cfb3"),
}

FAILURE_RECEIPT = CONTROL / "rebaseline_v2_e4_r6_m0_m1_attempt_001_failure_receipt.json"
FAILURE_RECEIPT_BYTES = 9902
FAILURE_RECEIPT_SHA256 = "79f90bf974ad19a364b6f09d0270e0f9211144470aeab3ab046d68634a9f0745"
HISTORICAL_C1_RECEIPT = CONTROL / "rebaseline_v2_e4_r6_c1_validation_receipt.json"
HISTORICAL_C1_RECEIPT_SHA256 = "058a6dfaf3fac9fa81c6544a03a88669992ff072be693073af7e14dd96f108e8"

DATA_ROOT_001 = (
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6"
    r"\official_source\grouplens_ml100k\attempt-001"
)
ENV_ROOT_001 = (
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    r"\recbole_bpr_ml100k_py3119_cpu\attempt-001"
)
DATA_ROOT_002 = DATA_ROOT_001[:-3] + "002"
ENV_ROOT_002 = ENV_ROOT_001[:-3] + "002"
PWSH = (
    r"C:\Users\ACER\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\powershell\pwsh.exe"
)
PWSH_BYTES = 301368
PWSH_SHA256 = "db6dd81183fe57d22e03b911ec9a30a2fd7c40542e97743615355a6fb44f458f"

DATA_IDS = [
    "M00_CREATE_EMPTY_NON_GIT_ATTEMPT",
    "M01_FETCH_OFFICIAL_README",
    "M02_FETCH_OFFICIAL_CHECKSUM",
    "M03_FETCH_OFFICIAL_ARCHIVE",
    "M04_VERIFY_AND_PROMOTE_DOWNLOADS",
    "M05_SAFE_EXTRACT_AND_HASH",
    "M06_CONVERT_U_DATA_TO_RECBOLE_INTER_AND_EXPECTED_MAPS",
    "M07_RECONCILE_RAW_TO_ATOMIC",
]
ENV_IDS = [
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
BRIDGE_IDS = [
    "B00_RESOLVE_INSTALLED_PACKAGE_AND_REQUIRE_ABSENT_TARGET",
    "B01_BINARY_COPY_CANONICAL_INTER_AND_WRITE_RECEIPT",
    "B02_CONFIG_ONLY_RESOLVED_PATH_CHECK",
]
ALL_IDS = DATA_IDS + ENV_IDS + BRIDGE_IDS

TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}

FORBIDDEN_PATTERNS = {
    "run_recbole": re.compile(r"\brun_recbole(?:\.py)?\b", re.I),
    "quick_start_execution": re.compile(
        r"quick_start\.(?:run_recbole|objective_function)|from\s+recbole\.quick_start\s+import",
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
        r"project[-_\\/]?v5[\\/][^\r\n]*test|harmonized[_-]?v5[\\/][^\r\n]*test",
        re.I,
    ),
    "benchmark_admission": re.compile(
        r"admit_benchmark|accept_result|paper_metric|paper_number", re.I
    ),
}

DROP_ENV_NAMES = {
    "all_proxy",
    "conda_default_env",
    "conda_prefix",
    "cuda_home",
    "cuda_path",
    "cuda_visible_devices",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "pip_config_file",
    "pip_extra_index_url",
    "pip_find_links",
    "pip_index_url",
    "pip_no_index",
    "pip_proxy",
    "pip_trusted_host",
    "pythonhome",
    "pythonpath",
    "virtual_env",
}


class StrictJsonError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, item in pairs:
        if key in value:
            raise StrictJsonError(f"duplicate key: {key}")
        normalized = key.casefold()
        if normalized in folded and folded[normalized] != key:
            raise StrictJsonError(f"case-colliding keys: {folded[normalized]} / {key}")
        folded[normalized] = key
        value[key] = item
    return value


def strict_load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError(f"UTF-8 BOM forbidden: {path}")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise StrictJsonError(f"top-level object required: {path}")
    return value


def fingerprint(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    canonical = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "raw_bytes": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_lf_bytes": len(canonical),
        "canonical_lf_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def raw_fingerprint(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"raw_bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest()}


def is_reparse(path: Path) -> bool:
    try:
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def check(checks: dict[str, bool], failures: list[str], key: str, value: bool) -> None:
    checks[key] = bool(value)
    if not value:
        failures.append(key)


def command_rows(document: dict[str, Any], lane: str) -> list[dict[str, Any]]:
    if lane in {"dataset", "bridge"}:
        rows = document.get("commands", [])
    else:
        rows = [
            row
            for group in document.get("command_groups", [])
            if isinstance(group, dict)
            for row in group.get("commands", [])
            if isinstance(row, dict)
        ]
    return [row for row in rows if isinstance(row, dict)]


def row_id(row: dict[str, Any]) -> str:
    value = row.get("command_id", row.get("id"))
    return value if isinstance(value, str) else ""


def normalize_command_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_command_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_command_value(item) for item in value]
    if isinstance(value, str):
        return (
            value.replace(DATA_ROOT_002.replace("\\", "\\\\"), DATA_ROOT_001.replace("\\", "\\\\"))
            .replace(ENV_ROOT_002.replace("\\", "\\\\"), ENV_ROOT_001.replace("\\", "\\\\"))
            .replace(DATA_ROOT_002, DATA_ROOT_001)
            .replace(ENV_ROOT_002, ENV_ROOT_001)
            .replace(PWSH, "powershell.exe")
        )
    return value


def argv_hash(argv: list[str]) -> str:
    payload = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_python_source(source: str, label: str, errors: list[str]) -> None:
    try:
        tree = ast.parse(source, filename=label, mode="exec")
    except SyntaxError as exc:
        errors.append(f"{label}:{exc.msg}:{exc.lineno}:{exc.offset}")
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


def syntax_scan(rows: list[dict[str, Any]]) -> tuple[int, list[str], int, list[str]]:
    python_count = 0
    python_errors: list[str] = []
    powershell_count = 0
    powershell_errors: list[str] = []
    parser = (
        "$s=[Console]::In.ReadToEnd();$t=$null;$e=$null;"
        "[System.Management.Automation.Language.Parser]::ParseInput($s,[ref]$t,[ref]$e)"
        "|Out-Null;if($e.Count -gt 0){$e|ForEach-Object{$_.Message};exit 1}"
    )
    for row in rows:
        identifier = row_id(row) or "UNKNOWN"
        argv = row.get("argv", [])
        executable = str(row.get("executable", ""))
        if executable.casefold().endswith("python.exe") and "-c" in argv:
            index = argv.index("-c")
            if index + 1 < len(argv) and isinstance(argv[index + 1], str):
                python_count += 1
                parse_python_source(argv[index + 1], identifier, python_errors)
        if executable == PWSH and "-Command" in argv:
            index = argv.index("-Command")
            powershell_count += 1
            if index + 1 >= len(argv):
                powershell_errors.append(f"{identifier}:missing script")
                continue
            completed = subprocess.run(
                [PWSH, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", parser],
                input=str(argv[index + 1]),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
                shell=False,
            )
            if completed.returncode != 0:
                detail = (completed.stdout + completed.stderr).strip()
                powershell_errors.append(f"{identifier}:{detail}")
    return python_count, python_errors, powershell_count, powershell_errors


def tree_observation(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    directories = 1
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if path.is_symlink() or is_reparse(path):
            raise RuntimeError(f"link or reparse: {path}")
        if path.is_dir():
            directories += 1
        elif path.is_file():
            raw = path.read_bytes()
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        else:
            raise RuntimeError(f"non-regular path: {path}")
    return {
        "files": files,
        "file_count": len(files),
        "directories_including_root": directories,
        "bytes": sum(row["bytes"] for row in files),
    }


def sanitized_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold() not in DROP_ENV_NAMES and not key.casefold().startswith("pip_")
    }
    environment.update(
        {
            "CUDA_VISIBLE_DEVICES": "",
            "NO_COLOR": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "SOURCE_DATE_EPOCH": "1740319008",
        }
    )
    return environment


def run_json_validator(path: Path) -> tuple[int, dict[str, Any] | None, str]:
    completed = subprocess.run(
        [sys.executable, "-B", str(path)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
        shell=False,
    )
    try:
        payload = json.loads(completed.stdout.decode("utf-8", "strict"), object_pairs_hook=strict_object)
    except Exception:
        payload = None
    return completed.returncode, payload, completed.stderr.decode("utf-8", "replace")


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    diagnostics: dict[str, Any] = {}

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
    output_fingerprints: list[dict[str, Any]] = []
    strict_errors: list[str] = []
    for name in EXPECTED_FILES:
        path = OUTPUT_ROOT / name
        try:
            raw = path.read_bytes()
            if b"\r" in raw:
                raise StrictJsonError("CR byte present; LF-only required")
            documents[name] = strict_load(path)
            output_fingerprints.append(fingerprint(path))
        except Exception as exc:
            strict_errors.append(f"{name}:{exc}")
    check(
        checks,
        failures,
        "strict_utf8_no_bom_lf_json_5_of_5",
        not strict_errors and len(documents) == 5,
    )
    diagnostics["strict_errors"] = strict_errors
    if strict_errors:
        result = {
            "schema_version": "stage1e-r6-c1r1-central-validation-result-1.0",
            "passed": False,
            "verdict": "FAIL_R6_C1R1_REWORK_REQUIRED",
            "failure_count": len(failures) + len(strict_errors),
            "failures": failures + strict_errors,
            "checks": checks,
            "diagnostics": diagnostics,
        }
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 1

    source_documents = {name: strict_load(SOURCE_ROOT / name) for name in EXPECTED_FILES}
    source_rows = {name: fingerprint(SOURCE_ROOT / name) for name in EXPECTED_FILES}
    check(
        checks,
        failures,
        "source_c1_packet_5_of_5_hash_replay",
        all(
            source_rows[name]["raw_bytes"] == SOURCE_FINGERPRINTS[name][0]
            and source_rows[name]["raw_sha256"] == SOURCE_FINGERPRINTS[name][1]
            and source_rows[name]["canonical_lf_bytes"] == SOURCE_FINGERPRINTS[name][0]
            and source_rows[name]["canonical_lf_sha256"] == SOURCE_FINGERPRINTS[name][1]
            for name in EXPECTED_FILES
        ),
    )

    failure_fp = fingerprint(FAILURE_RECEIPT)
    failure_receipt = strict_load(FAILURE_RECEIPT)
    historical_fp = fingerprint(HISTORICAL_C1_RECEIPT)
    historical_receipt = strict_load(HISTORICAL_C1_RECEIPT)
    check(
        checks,
        failures,
        "attempt001_failure_receipt_hash_status_and_truth_replay",
        failure_fp["raw_bytes"] == FAILURE_RECEIPT_BYTES
        and failure_fp["raw_sha256"] == FAILURE_RECEIPT_SHA256
        and failure_fp["canonical_lf_bytes"] == FAILURE_RECEIPT_BYTES
        and failure_fp["canonical_lf_sha256"] == FAILURE_RECEIPT_SHA256
        and failure_receipt.get("status") == "FAIL_CLOSED_CONTROL_PLANE_CAPABILITY_MISMATCH"
        and failure_receipt.get("truth_state") == TRUTH,
    )
    check(
        checks,
        failures,
        "historical_c1_pass_receipt_replayed",
        historical_fp["raw_sha256"] == HISTORICAL_C1_RECEIPT_SHA256
        and historical_receipt.get("validation_run", {}).get("verdict")
        == "PASS_R6_C1_EXACT_COMMAND_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1"
        and historical_receipt.get("validation_run", {}).get("checks_passed") == 44
        and historical_receipt.get("validation_run", {}).get("checks_expected") == 44
        and historical_receipt.get("validation_run", {}).get("failure_count") == 0,
    )

    g0_code, g0_result, g0_stderr = run_json_validator(CONTROL / "validate_e4_r6_g0_gate.py")
    c1_code, c1_result, c1_stderr = run_json_validator(CONTROL / "validate_e4_r6_c1_packet.py")
    diagnostics["historical_live_replay"] = {
        "g0_exit_code": g0_code,
        "g0_stderr": g0_stderr[-1000:],
        "c1_exit_code": c1_code,
        "c1_stderr": c1_stderr[-1000:],
    }
    check(
        checks,
        failures,
        "g0_live_replay_degrades_only_on_consumed_attempt001_roots",
        isinstance(g0_result, dict)
        and set(g0_result.get("failures", []))
        == {"dataset_root_external_non_git_and_absent", "environment_external_non_git_immutable_attempt"}
        and g0_result.get("mechanical_summary", {}).get("checks_passed") == 33
        and g0_result.get("mechanical_summary", {}).get("checks_expected") == 35
        and g0_result.get("diagnostics", {}).get("fingerprint_failures") == []
        and g0_result.get("diagnostics", {}).get("strict_json_failures") == [],
    )
    check(
        checks,
        failures,
        "historical_c1_live_replay_degrades_only_on_expected_post_attempt_state",
        isinstance(c1_result, dict)
        and set(c1_result.get("failures", []))
        == {
            "r6_g0_replay_still_passes",
            "dataset_external_root_only_harmonized_and_repo_writes_denied",
            "environment_external_exact_python_3119_no_ambient_interpreter",
        }
        and c1_result.get("mechanical_summary", {}).get("checks_passed") == 41
        and c1_result.get("mechanical_summary", {}).get("checks_expected") == 44,
    )

    dataset_attempt = tree_observation(Path(DATA_ROOT_001))
    environment_attempt = tree_observation(Path(ENV_ROOT_001))
    failure_dataset = failure_receipt.get("lanes", {}).get("dataset", {})
    failure_environment = failure_receipt.get("lanes", {}).get("environment", {})
    check(
        checks,
        failures,
        "attempt001_dataset_root_immutable_inventory_replay",
        dataset_attempt["files"] == failure_dataset.get("files")
        and dataset_attempt["file_count"] == 6
        and dataset_attempt["directories_including_root"] == 9
        and dataset_attempt["bytes"] == 4931527,
    )
    check(
        checks,
        failures,
        "attempt001_environment_root_immutable_inventory_replay",
        environment_attempt["files"] == failure_environment.get("files")
        and environment_attempt["file_count"] == 4
        and environment_attempt["directories_including_root"] == 9
        and environment_attempt["bytes"] == 26223921,
    )
    check(
        checks,
        failures,
        "attempt002_roots_absent_before_dispatch",
        not Path(DATA_ROOT_002).exists()
        and not Path(DATA_ROOT_002).is_symlink()
        and not Path(ENV_ROOT_002).exists()
        and not Path(ENV_ROOT_002).is_symlink(),
    )

    expected_schemas = {
        "dataset_materialization_packet.json": "stage1e-rebaseline-v2-e4-r6-c1r1-attempt002-dataset-materialization-packet-1.0",
        "environment_materialization_packet.json": "stage1e-rebaseline-v2-e4-r6-c1r1-attempt002-environment-materialization-packet-1.0",
        "recbole_dataset_bridge_packet.json": "stage1e-rebaseline-v2-e4-r6-c1r1-attempt002-recbole-dataset-bridge-packet-1.0",
        "execution_boundary_and_negative_assertions.json": "stage1e-rebaseline-v2-e4-r6-c1r1-attempt002-execution-boundary-and-negative-assertions-1.1",
        "audit_handoff.json": "stage1e-rebaseline-v2-e4-r6-c1r1-attempt002-audit-handoff-1.1",
    }
    check(
        checks,
        failures,
        "recovery_schema_stage_and_proposal_only_exact",
        all(
            documents[name].get("schema_version") == expected_schemas[name]
            and documents[name].get("stage_id") == "R6-C1R1"
            and documents[name].get("proposal_only") is True
            and documents[name].get("execution_performed") is False
            and documents[name].get("execution_authorized") is False
            and documents[name].get("truth_state") == TRUTH
            for name in EXPECTED_FILES
        ),
    )

    expected_source_artifacts = [
        {
            "file": name,
            "raw_bytes": SOURCE_FINGERPRINTS[name][0],
            "raw_sha256": SOURCE_FINGERPRINTS[name][1],
            "canonical_lf_bytes": SOURCE_FINGERPRINTS[name][0],
            "canonical_lf_sha256": SOURCE_FINGERPRINTS[name][1],
        }
        for name in EXPECTED_FILES
    ]
    recovery_rows = [documents[name].get("recovery_provenance", {}) for name in EXPECTED_FILES]
    check(
        checks,
        failures,
        "recovery_provenance_5_of_5_exact_and_hash_bound",
        all(
            row.get("recovery_stage") == "R6-C1R1"
            and row.get("recovery_attempt") == "attempt-002"
            and row.get("source_packet_stage") == "R6-C1"
            and row.get("source_packet_artifacts") == expected_source_artifacts
            and row.get("attempt_001_failure_receipt") == FAILURE_RECEIPT.relative_to(ROOT).as_posix()
            and row.get("failure_receipt_raw_bytes") == FAILURE_RECEIPT_BYTES
            and row.get("failure_receipt_raw_sha256") == FAILURE_RECEIPT_SHA256
            and row.get("failure_receipt_canonical_lf_bytes") == FAILURE_RECEIPT_BYTES
            and row.get("failure_receipt_canonical_lf_sha256") == FAILURE_RECEIPT_SHA256
            and row.get("failure_receipt_status_observed") == failure_receipt.get("status")
            and row.get("failure_receipt_truth_state_observed") == TRUTH
            and row.get("exact_control_plane_executable") == PWSH
            and row.get("source_packet_modified") is False
            and row.get("prior_attempt_root_modified_deleted_or_reused") is False
            and row.get("scientific_scope_changed") is False
            and row.get("command_ids_order_or_counts_changed") is False
            and row.get("network_or_scientific_command_executed_during_generation") is False
            for row in recovery_rows
        ),
    )

    dataset = documents[EXPECTED_FILES[0]]
    environment = documents[EXPECTED_FILES[1]]
    bridge = documents[EXPECTED_FILES[2]]
    boundary = documents[EXPECTED_FILES[3]]
    handoff = documents[EXPECTED_FILES[4]]
    old_dataset = source_documents[EXPECTED_FILES[0]]
    old_environment = source_documents[EXPECTED_FILES[1]]
    old_bridge = source_documents[EXPECTED_FILES[2]]

    data_rows = command_rows(dataset, "dataset")
    env_rows = command_rows(environment, "environment")
    bridge_rows = command_rows(bridge, "bridge")
    all_rows = data_rows + env_rows + bridge_rows
    old_rows = (
        command_rows(old_dataset, "dataset")
        + command_rows(old_environment, "environment")
        + command_rows(old_bridge, "bridge")
    )
    ids = [row_id(row) for row in all_rows]
    check(
        checks,
        failures,
        "exact_8_25_3_unique_ordered_command_ids",
        [row_id(row) for row in data_rows] == DATA_IDS
        and [row_id(row) for row in env_rows] == ENV_IDS
        and [row_id(row) for row in bridge_rows] == BRIDGE_IDS
        and len(set(ids)) == 36
        and dataset.get("command_order") == DATA_IDS
        and environment.get("command_order") == ENV_IDS
        and bridge.get("command_order") == BRIDGE_IDS,
    )
    check(
        checks,
        failures,
        "all_36_literal_argv_coherent_and_bounded",
        len(all_rows) == 36
        and all(
            isinstance(row.get("executable"), str)
            and isinstance(row.get("arguments"), list)
            and isinstance(row.get("argv"), list)
            and row["argv"] == [row["executable"], *row["arguments"]]
            and isinstance(row.get("timeout_seconds"), int)
            and row["timeout_seconds"] > 0
            and isinstance(row.get("network"), bool)
            for row in all_rows
        ),
    )
    check(
        checks,
        failures,
        "all_36_commands_semantically_equal_to_validated_c1_after_allowed_normalization",
        len(old_rows) == len(all_rows)
        and all(
            row_id(old) == row_id(new)
            and normalize_command_value(new) == old
            for old, new in zip(old_rows, all_rows)
        ),
    )
    check(
        checks,
        failures,
        "exact_eight_pwsh_commands_and_no_ambient_powershell_token",
        sum(row.get("executable") == PWSH for row in all_rows) == 8
        and all(
            row.get("executable") != "powershell.exe"
            and (not row.get("argv") or row["argv"][0] != "powershell.exe")
            for row in all_rows
        ),
    )

    python_count, python_errors, powershell_count, powershell_errors = syntax_scan(all_rows)
    diagnostics["syntax"] = {
        "python_sources": python_count,
        "python_errors": python_errors,
        "powershell_scripts": powershell_count,
        "powershell_errors": powershell_errors,
    }
    check(
        checks,
        failures,
        "embedded_python_ast_and_pwsh_parser_pass",
        python_count == 16
        and not python_errors
        and powershell_count == 8
        and not powershell_errors,
    )

    forbidden_matches: list[str] = []
    for row in all_rows:
        text = "\n".join(str(token) for token in row.get("argv", []))
        for rule, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                forbidden_matches.append(f"{row_id(row)}:{rule}")
    diagnostics["forbidden_execution_matches"] = forbidden_matches
    check(
        checks,
        failures,
        "independent_forbidden_execution_scan_36_of_36",
        not forbidden_matches,
    )

    scan = boundary.get("executable_argv_scan", {})
    scan_entries = scan.get("entries", []) if isinstance(scan, dict) else []
    scan_by_id = {
        row.get("command_id"): row for row in scan_entries if isinstance(row, dict)
    }
    command_by_id = {row_id(row): row for row in all_rows}
    check(
        checks,
        failures,
        "boundary_36_scan_entries_recomputed_exact",
        scan.get("scanned_command_count") == 36
        and scan.get("rejected_command_count") == 0
        and scan.get("all_literal_argv") is True
        and list(scan_by_id) == ALL_IDS
        and all(
            identifier in command_by_id
            and scan_by_id[identifier].get("executable") == command_by_id[identifier].get("executable")
            and scan_by_id[identifier].get("argv_canonical_sha256")
            == argv_hash(command_by_id[identifier]["argv"])
            and scan_by_id[identifier].get("argv_recomposition_match") is True
            and scan_by_id[identifier].get("forbidden_execution_matches") == []
            and scan_by_id[identifier].get("scan_verdict") == "PASS"
            for identifier in ALL_IDS
        ),
    )

    data_network_ids = [row_id(row) for row in data_rows if row.get("network") is True]
    env_network_ids = [row_id(row) for row in env_rows if row.get("network") is True]
    bridge_network_ids = [row_id(row) for row in bridge_rows if row.get("network") is True]
    check(
        checks,
        failures,
        "network_surface_unchanged_and_bridge_offline",
        data_network_ids == DATA_IDS[1:4]
        and env_network_ids == [ENV_IDS[1], ENV_IDS[2], ENV_IDS[10], ENV_IDS[11]]
        and bridge_network_ids == []
        and all(normalize_command_value(new) == old for old, new in zip(old_rows, all_rows)),
    )

    counts = boundary.get("command_counts", {})
    graph = boundary.get("cross_packet_dependency_graph", {})
    roots = boundary.get("aggregate_write_roots", {})
    resources = boundary.get("aggregate_resource_bounds", {})
    negative = boundary.get("negative_assertions", {})
    check(
        checks,
        failures,
        "boundary_counts_dependencies_roots_resources_exact",
        counts
        == {
            "dataset_materialization_packet": 8,
            "environment_materialization_packet": 25,
            "recbole_dataset_bridge_packet": 3,
            "total": 36,
        }
        and graph.get("prerequisite")
        == "CENTRAL_VALIDATION_OF_EXACT_R6_C1R1_ATTEMPT002_FIVE_FILE_PACKET"
        and [row.get("stage") for row in graph.get("independent_after_prerequisite", [])]
        == ["R6-M0", "R6-M1"]
        and graph.get("bridge", {}).get("depends_on")
        == ["R6-M0_SUCCESS_WITH_INDEPENDENT_RECEIPTS", "R6-M1_SUCCESS_WITH_INDEPENDENT_RECEIPTS"]
        and graph.get("training_evaluation_or_test_dependency_present") is False
        and roots.get("future_materialization_persistent_roots") == [DATA_ROOT_002, ENV_ROOT_002]
        and roots.get("repository_materialization_writes_allowed") is False
        and roots.get("harmonized_v5_writes_allowed") is False
        and roots.get("project_v5_test_writes_allowed") is False
        and resources.get("aggregate_materialization_concurrency") == 2
        and resources.get("gpu_devices") == 0
        and resources.get("ray_workers") == 0
        and resources.get("dataset_retry_count") == 0
        and resources.get("bridge_retry_count") == 0,
    )
    check(
        checks,
        failures,
        "boundary_negative_assertions_and_authority_closed",
        len(negative) >= 15
        and all(value is True for value in negative.values())
        and boundary.get("authorization_effect", {}).get("central_validation_only") is True
        and boundary.get("authorization_effect", {}).get("materialization_authorized_by_this_artifact") is False
        and boundary.get("authorization_effect", {}).get("experiment_execution_authorized") is False,
    )

    no_execution = handoff.get("no_execution_assertions", {})
    handoff_counts = handoff.get("command_counts", {})
    handoff_auth = handoff.get("authorization", {})
    check(
        checks,
        failures,
        "handoff_zero_execution_exact_counts_and_central_validation_only",
        handoff.get("verdict") == "READY_FOR_CENTRAL_VALIDATION_OF_R6_C1R1_ATTEMPT002_ONLY_FAIL_CLOSED"
        and len(no_execution) >= 13
        and all(value is False for value in no_execution.values())
        and handoff_counts.get("dataset_materialization_packet") == 8
        and handoff_counts.get("environment_materialization_packet") == 25
        and handoff_counts.get("recbole_dataset_bridge_packet") == 3
        and handoff_counts.get("total_proposed_commands") == 36
        and handoff_counts.get("proposed_commands_executed") == 0
        and handoff_counts.get("materialization_commands_executed") == 0
        and handoff_counts.get("experiment_commands_executed") == 0
        and handoff_auth.get("authorized_next_action") == "CENTRAL_VALIDATION_OF_R6_C1R1_ATTEMPT002"
        and handoff_auth.get("materialization_authorized") is False
        and handoff_auth.get("bridge_execution_authorized") is False
        and handoff_auth.get("experiment_execution_authorized") is False,
    )

    non_self = handoff.get("output_integrity_non_self_referential", {})
    expected_non_self = [
        {
            "file": Path(row["path"]).name,
            "raw_bytes": row["raw_bytes"],
            "raw_sha256": row["raw_sha256"],
            "canonical_lf_bytes": row["canonical_lf_bytes"],
            "canonical_lf_sha256": row["canonical_lf_sha256"],
        }
        for row in output_fingerprints[:4]
    ]
    check(
        checks,
        failures,
        "handoff_non_self_referential_output_hashes_recomputed",
        non_self.get("files") == expected_non_self,
    )

    pwsh_path = Path(PWSH)
    pwsh_fp = raw_fingerprint(pwsh_path) if pwsh_path.is_file() else {}
    capability_script = (
        "$ErrorActionPreference='Stop';$a=Get-Command Get-FileHash;"
        "$b=Get-Command Get-AuthenticodeSignature;"
        "[ordered]@{PSVersion=$PSVersionTable.PSVersion.ToString();"
        "GetFileHashSource=$a.Source;GetAuthenticodeSignatureSource=$b.Source}"
        "|ConvertTo-Json -Compress"
    )
    capability = subprocess.run(
        [PWSH, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", capability_script],
        env=sanitized_environment(),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        shell=False,
    )
    try:
        capability_json = json.loads(capability.stdout.decode("utf-8", "strict"))
    except Exception:
        capability_json = {}
    diagnostics["control_plane_capability"] = {
        "exit_code": capability.returncode,
        "stdout_sha256": hashlib.sha256(capability.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(capability.stderr).hexdigest(),
        "observation": capability_json,
    }
    check(
        checks,
        failures,
        "exact_pwsh_bytes_version_and_required_capabilities",
        pwsh_path.is_file()
        and not pwsh_path.is_symlink()
        and not is_reparse(pwsh_path)
        and pwsh_fp.get("raw_bytes") == PWSH_BYTES
        and pwsh_fp.get("raw_sha256") == PWSH_SHA256
        and capability.returncode == 0
        and capability_json
        == {
            "PSVersion": "7.6.4",
            "GetFileHashSource": "Microsoft.PowerShell.Utility",
            "GetAuthenticodeSignatureSource": "Microsoft.PowerShell.Security",
        },
    )

    passed = not failures
    result = {
        "schema_version": "stage1e-r6-c1r1-central-validation-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R6_C1R1_ATTEMPT_002_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1"
            if passed
            else "FAIL_R6_C1R1_REWORK_REQUIRED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "mechanical_summary": {
            "checks_passed": sum(checks.values()),
            "checks_expected": len(checks),
            "output_files": len(output_fingerprints),
            "strict_json_outputs": len(documents),
            "literal_argv_commands": len(all_rows),
            "dataset_commands": len(data_rows),
            "environment_commands": len(env_rows),
            "bridge_commands": len(bridge_rows),
            "pwsh_commands": powershell_count,
            "python_inline_sources": python_count,
            "forbidden_execution_matches": len(forbidden_matches),
        },
        "outputs": output_fingerprints,
        "diagnostics": diagnostics,
        "materialization_gate_opened_by_this_validation": passed,
        "bridge_execution_authorized": False,
        "experiment_execution_authorized": False,
        "test_access_authorized": False,
        "benchmark_admission_authorized": False,
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
