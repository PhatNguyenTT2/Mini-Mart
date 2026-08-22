from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


REPO = Path.cwd().resolve()
CONTROL = REPO / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
PACKET_ROOT = (
    REPO
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ak/"
    "E4_R6C1R2_attempt003_command_packet"
)
EXPECTED_FILES = [
    "dataset_materialization_packet.json",
    "environment_materialization_packet.json",
    "recbole_dataset_bridge_packet.json",
    "execution_boundary_and_negative_assertions.json",
    "audit_handoff.json",
]
DISPATCH = CONTROL / "rebaseline_v2_e4_r6_c1r2_dispatch.json"
SOURCE_REPLAY = CONTROL / "rebaseline_v2_e4_r6_c1r2_nuget_source_replay_receipt.json"
ATTEMPT002_FAILURE = CONTROL / "rebaseline_v2_e4_r6_m0_m1_attempt_002_failure_receipt.json"

DATA_ROOT = Path(
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6\official_source\grouplens_ml100k\attempt-003"
)
ENV_ROOT = Path(
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6\recbole_bpr_ml100k_py3119_cpu\attempt-003"
)
RUNTIME_PYTHON = str(ENV_ROOT / "runtime/python.exe")
VENV_PYTHON = str(ENV_ROOT / "venv/Scripts/python.exe")
PWSH = Path(
    r"C:\Users\ACER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe"
)

NUGET = {
    "id": "python",
    "version": "3.11.9",
    "url": "https://api.nuget.org/v3-flatcontainer/python/3.11.9/python.3.11.9.nupkg",
    "registration": "https://api.nuget.org/v3/registration5-semver1/python/3.11.9.json",
    "catalog": "https://api.nuget.org/v3/catalog0/data/2024.04.02.13.14.51/python.3.11.9.json",
    "bytes": "17478009",
    "md5": "0deb9c5d73bc95ca7b66dd72b0f8d8a2",
    "sha256": "9283876d58c017e0e846f95b490da3bca0fc0a6ee1134b2870677cfb7eec3c67",
    "sha512": "41On79FZ75irnOEBGFSjDV13j1nZb8m7EbB87SmQs1XwMEhrBwf3mMc8RCAXOrERh2qW6tWYFxi2BMTN1xxVjQ==",
    "all_inventory": "5b6fb34361dc7d120329363730678c13db857d6069d88d3505406526ba4ed63a",
    "runtime_inventory": "62f76352a94a53dd4aeb406d00a14151b23cb544bd52fde5a899a7f62cdb33bd",
}

GROUPLENS = {
    "host": "files.grouplens.org",
    "bytes": "4924029",
    "md5": "0e33842e24a9c977be4e0107933c0723",
    "sha256": "50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229",
}


class StrictJsonError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    casefolded: dict[str, str] = {}
    for key, value in pairs:
        if key in out:
            raise StrictJsonError(f"duplicate JSON key: {key}")
        folded = key.casefold()
        if folded in casefolded:
            raise StrictJsonError(
                f"case-colliding JSON keys: {casefolded[folded]} and {key}"
            )
        out[key] = value
        casefolded[folded] = key
    return out


def strict_load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError(f"UTF-8 BOM forbidden: {path}")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise StrictJsonError(f"top-level JSON object required: {path}")
    return value


def fingerprint(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(REPO).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def check(
    checks: dict[str, bool], failures: list[str], key: str, condition: bool
) -> None:
    value = bool(condition)
    checks[key] = value
    if not value:
        failures.append(key)


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def scalar_text(value: Any) -> str:
    return "\n".join(
        str(item)
        for item in walk(value)
        if isinstance(item, (str, int, float, bool))
    )


def normalized_control_text(value: Any) -> tuple[str, str]:
    text = scalar_text(value).lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(text.split())
    compact = "".join(character for character in normalized if character.isalnum())
    return normalized, compact


def top_level_commands(document: dict[str, Any]) -> list[dict[str, Any]]:
    commands = document.get("commands")
    if not isinstance(commands, list) or not all(
        isinstance(command, dict) for command in commands
    ):
        return []
    return commands


def argv_urls(argv: list[str]) -> list[str]:
    return [token for token in argv if token.lower().startswith("https://")]


def option_value(argv: list[str], option: str) -> str | None:
    try:
        index = argv.index(option)
    except ValueError:
        return None
    return argv[index + 1] if index + 1 < len(argv) else None


def command_rows(document: dict[str, Any], lane: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_objects: set[int] = set()
    for value in walk(document):
        if not isinstance(value, dict) or id(value) in seen_objects:
            continue
        identifier = value.get("id", value.get("command_id"))
        argv = value.get("argv")
        if isinstance(identifier, str) and isinstance(argv, list):
            row = dict(value)
            row["_lane"] = lane
            row["_id"] = identifier
            rows.append(row)
            seen_objects.add(id(value))
    return rows


def argv_hash(argv: list[str]) -> str:
    canonical = json.dumps(argv, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def script_after(argv: list[str], switch: str) -> str | None:
    try:
        index = argv.index(switch)
    except ValueError:
        return None
    return argv[index + 1] if index + 1 < len(argv) else None


def syntax_scan(rows: list[dict[str, Any]]) -> dict[str, Any]:
    python_ok = 0
    python_errors: list[str] = []
    powershell_ok = 0
    powershell_errors: list[str] = []
    for row in rows:
        argv = row["argv"]
        label = f"{row['_lane']}:{row['_id']}"
        py_source = script_after(argv, "-c")
        if py_source is not None and str(argv[0]).lower().endswith("python.exe"):
            try:
                ast.parse(py_source, filename=label, mode="exec")
                python_ok += 1
            except SyntaxError as exc:
                python_errors.append(f"{label}:{exc}")
        ps_source = script_after(argv, "-Command")
        if ps_source is not None and Path(str(argv[0])).name.lower() == "pwsh.exe":
            parser = (
                "$source=[Console]::In.ReadToEnd();$tokens=$null;$errors=$null;"
                "[System.Management.Automation.Language.Parser]::ParseInput("
                "$source,[ref]$tokens,[ref]$errors)|Out-Null;"
                "if($errors.Count -gt 0){$errors|ForEach-Object{$_.Message};exit 1}"
            )
            proc = subprocess.run(
                [
                    str(PWSH),
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    parser,
                ],
                input=ps_source,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if proc.returncode == 0:
                powershell_ok += 1
            else:
                powershell_errors.append(
                    f"{label}:exit={proc.returncode}:{proc.stderr.strip()}"
                )
    return {
        "python_sources_parsed": python_ok,
        "python_errors": python_errors,
        "powershell_sources_parsed": powershell_ok,
        "powershell_errors": powershell_errors,
    }


def exact_frozen_inputs(dispatch: dict[str, Any]) -> tuple[int, list[str]]:
    passed = 0
    errors: list[str] = []
    for item in dispatch.get("frozen_inputs", []):
        path = REPO / item.get("path", "")
        if not path.is_file():
            errors.append(f"missing:{item.get('path')}")
            continue
        fp = fingerprint(path)
        if fp["bytes"] != item.get("raw_bytes") or fp["sha256"] != item.get(
            "raw_sha256"
        ):
            errors.append(f"fingerprint:{item.get('path')}")
            continue
        passed += 1
    return passed, errors


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []
    diagnostics: dict[str, Any] = {}

    check(checks, failures, "repository_cwd", (REPO / ".git").exists())
    observed = (
        sorted(path.name for path in PACKET_ROOT.iterdir() if path.is_file())
        if PACKET_ROOT.is_dir()
        else []
    )
    check(checks, failures, "exact_five_file_set", observed == sorted(EXPECTED_FILES))
    if observed != sorted(EXPECTED_FILES):
        result = {
            "verdict": "FAIL_R6_C1R2_REWORK_REQUIRED",
            "checks": checks,
            "failures": failures,
            "observed_files": observed,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    try:
        documents = {name: strict_load(PACKET_ROOT / name) for name in EXPECTED_FILES}
        dispatch = strict_load(DISPATCH)
        replay = strict_load(SOURCE_REPLAY)
        failure_receipt = strict_load(ATTEMPT002_FAILURE)
    except (OSError, UnicodeError, json.JSONDecodeError, StrictJsonError) as exc:
        print(
            json.dumps(
                {
                    "verdict": "FAIL_R6_C1R2_REWORK_REQUIRED",
                    "failures": [f"strict_json:{exc}"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    check(checks, failures, "strict_json_outputs_5_of_5", len(documents) == 5)
    frozen_passed, frozen_errors = exact_frozen_inputs(dispatch)
    diagnostics["frozen_input_errors"] = frozen_errors
    check(
        checks,
        failures,
        "dispatch_frozen_inputs_12_of_12",
        frozen_passed == 12 and not frozen_errors,
    )
    check(
        checks,
        failures,
        "source_replay_gate_pass",
        replay.get("status") == "PASS_OFFICIAL_CPYTHON_NUGET_3119_INERT_BYTE_REPLAY",
    )
    check(
        checks,
        failures,
        "attempt002_failure_gate_exact",
        failure_receipt.get("status")
        == "FAIL_CLOSED_PACKET_RUNTIME_AND_AMBIENT_INSTALLER_COLLISION",
    )
    check(checks, failures, "dataset_attempt003_root_absent", not DATA_ROOT.exists())
    check(checks, failures, "environment_attempt003_root_absent", not ENV_ROOT.exists())

    texts = {
        name: json.dumps(doc, ensure_ascii=False, sort_keys=True)
        for name, doc in documents.items()
    }
    plain_texts = {name: scalar_text(doc) for name, doc in documents.items()}
    dataset_text = plain_texts[EXPECTED_FILES[0]]
    environment_text = plain_texts[EXPECTED_FILES[1]]
    bridge_text = plain_texts[EXPECTED_FILES[2]]
    boundary_text = plain_texts[EXPECTED_FILES[3]].lower()
    handoff_text = plain_texts[EXPECTED_FILES[4]].lower()
    combined_text = "\n".join(texts.values())
    combined_plain_text = "\n".join(plain_texts.values())

    check(
        checks,
        failures,
        "attempt003_roots_present_in_packet",
        str(DATA_ROOT) in combined_plain_text and str(ENV_ROOT) in combined_plain_text,
    )
    check(
        checks,
        failures,
        "attempt003_pairing_in_bridge",
        str(DATA_ROOT) in bridge_text
        and str(ENV_ROOT) in bridge_text
        and "attempt-002" not in bridge_text,
    )
    check(
        checks,
        failures,
        "group_lens_archive_lock_preserved",
        all(value in dataset_text for value in GROUPLENS.values()),
    )
    check(
        checks,
        failures,
        "nuget_source_lock_complete",
        all(value in environment_text for value in NUGET.values()),
    )
    for marker in (
        "1773",
        "45644754",
        "1766",
        "45610489",
        "tools/python.exe",
        "tools/python311.dll",
        "tools/Lib/venv/__init__.py",
        "tools/Lib/site-packages/pip/__init__.py",
        ".signature.p7s",
        "python.nuspec",
    ):
        check(
            checks,
            failures,
            f"nuget_inventory_marker_{hashlib.sha256(marker.encode()).hexdigest()[:8]}",
            marker in environment_text,
        )

    lane_documents = {
        "dataset": documents[EXPECTED_FILES[0]],
        "environment": documents[EXPECTED_FILES[1]],
        "bridge": documents[EXPECTED_FILES[2]],
    }
    rows_by_lane = {
        lane: command_rows(document, lane)
        for lane, document in lane_documents.items()
    }
    expected_counts = {"dataset": 8, "environment": 26, "bridge": 3}
    for lane, document in lane_documents.items():
        commands = top_level_commands(document)
        command_ids = [
            command.get("id", command.get("command_id")) for command in commands
        ]
        check(
            checks,
            failures,
            f"{lane}_commands_top_level_only",
            len(commands) == len(rows_by_lane[lane]),
        )
        check(
            checks,
            failures,
            f"{lane}_command_count_exact",
            len(commands) == expected_counts[lane]
            and document.get("command_count") == expected_counts[lane],
        )
        check(
            checks,
            failures,
            f"{lane}_command_order_exact",
            document.get("command_order") == command_ids,
        )
    all_rows = [row for rows in rows_by_lane.values() for row in rows]
    diagnostics["command_counts"] = {
        lane: len(rows) for lane, rows in rows_by_lane.items()
    }
    identifiers = [row["_id"] for row in all_rows]
    check(checks, failures, "command_ids_unique", len(identifiers) == len(set(identifiers)))
    check(checks, failures, "dataset_has_exactly_eight_commands", len(rows_by_lane["dataset"]) == 8)
    check(checks, failures, "environment_has_exactly_twenty_six_commands", len(rows_by_lane["environment"]) == 26)
    check(checks, failures, "bridge_has_exactly_three_commands", len(rows_by_lane["bridge"]) == 3)

    argv_failures: list[str] = []
    command_contract_failures: list[str] = []
    banned_executables = {
        "msiexec.exe",
        "nuget.exe",
        "winget.exe",
        "py.exe",
        "conda.exe",
        "uv.exe",
        "python-3.11.9-amd64.exe",
        "powershell.exe",
        "cmd.exe",
    }
    allowed_python = {RUNTIME_PYTHON.lower(), VENV_PYTHON.lower()}
    for row in all_rows:
        argv = row.get("argv")
        executable = row.get("executable")
        label = f"{row['_lane']}:{row['_id']}"
        if not argv or not all(isinstance(token, str) for token in argv):
            argv_failures.append(f"{label}:literal-string-argv")
            continue
        if executable is not None and (
            not isinstance(executable, str) or argv[0] != executable
        ):
            argv_failures.append(f"{label}:argv0-executable")
        arguments = row.get("arguments")
        if arguments is not None and arguments != argv[1:]:
            argv_failures.append(f"{label}:arguments-not-argv-tail")
        base = Path(argv[0]).name.lower()
        if base in banned_executables:
            argv_failures.append(f"{label}:banned-executable:{base}")
        if base == "python.exe" and argv[0].lower() not in allowed_python:
            argv_failures.append(f"{label}:ambient-python:{argv[0]}")
        if base == "pwsh.exe" and Path(argv[0]) != PWSH:
            argv_failures.append(f"{label}:ambient-pwsh:{argv[0]}")
        joined = "\n".join(argv)
        if "attempt-001" in joined or "attempt-002" in joined:
            argv_failures.append(f"{label}:historical-attempt-in-command")
        if row.get("shell") is True or row.get("shell_reassembly") is True:
            argv_failures.append(f"{label}:shell-reassembly")
        if not isinstance(row.get("network"), bool):
            command_contract_failures.append(f"{label}:network-bool")
        timeout = row.get("timeout_seconds")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            command_contract_failures.append(f"{label}:positive-timeout")
        for field in ("write_set", "required_outputs", "postconditions"):
            value = row.get(field)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                command_contract_failures.append(f"{label}:{field}")
    diagnostics["argv_failures"] = argv_failures
    diagnostics["command_contract_failures"] = command_contract_failures
    diagnostics["argv_sha256"] = {
        row["_id"]: argv_hash(row["argv"])
        for row in all_rows
        if isinstance(row.get("argv"), list)
        and all(isinstance(token, str) for token in row["argv"])
    }
    check(checks, failures, "literal_argv_policy", not argv_failures)
    check(
        checks,
        failures,
        "per_command_contract_complete",
        not command_contract_failures,
    )

    m05 = next((row for row in all_rows if row["_id"] == "M05_SAFE_EXTRACT_AND_HASH"), None)
    m05_source = "\n".join(m05["argv"]) if m05 else ""
    check(checks, failures, "m05_present", m05 is not None)
    check(
        checks,
        failures,
        "m05_two_argument_enumerable_constructor_removed",
        "::new($names,[StringComparer]::Ordinal)" not in m05_source.replace(" ", ""),
    )
    check(
        checks,
        failures,
        "m05_comparer_constructor_and_typed_add",
        "HashSet[string]]::new([StringComparer]::Ordinal)" in m05_source
        and ".Add(" in m05_source,
    )

    m04 = next(
        (row for row in all_rows if row["_id"] == "M04_VERIFY_AND_PROMOTE_DOWNLOADS"),
        None,
    )
    m04_source = "\n".join(m04["argv"]) if m04 else ""
    expected_sha_index = m04_source.find(GROUPLENS["sha256"])
    first_promotion_index = m04_source.find("Move-Item")
    check(checks, failures, "m04_present", m04 is not None)
    check(
        checks,
        failures,
        "m04_sha256_guard_precedes_promotion",
        expected_sha_index >= 0
        and first_promotion_index >= 0
        and expected_sha_index < first_promotion_index
        and "ARCHIVE_SHA256_MISMATCH" in m04_source,
    )

    network_failures: list[str] = []
    expected_network_ids = {
        "dataset": {
            "M01_FETCH_OFFICIAL_README",
            "M02_FETCH_OFFICIAL_CHECKSUM",
            "M03_FETCH_OFFICIAL_ARCHIVE",
        },
        "environment": {
            "E01_FETCH_NUGET_REGISTRATION_METADATA",
            "E02_FETCH_NUGET_CATALOG_METADATA",
            "E03_FETCH_OFFICIAL_CPYTHON_NUPKG_BYTES",
            "E11_DOWNLOAD_TORCH_CPU_WHEEL",
            "E12_DOWNLOAD_PINNED_PYPI_WHEELS",
        },
        "bridge": set(),
    }
    allowed_hosts = {
        "dataset": {"files.grouplens.org"},
        "environment": {
            "api.nuget.org",
            "download.pytorch.org",
            "pypi.org",
        },
        "bridge": set(),
    }
    for lane, rows in rows_by_lane.items():
        actual_network_ids = {row["_id"] for row in rows if row.get("network") is True}
        if actual_network_ids != expected_network_ids[lane]:
            network_failures.append(
                f"{lane}:network-ids:{sorted(actual_network_ids)}"
            )
        for row in rows:
            if row.get("network") is not True:
                continue
            argv = row["argv"]
            label = f"{lane}:{row['_id']}"
            hosts = {
                (urlparse(url).hostname or "").lower() for url in argv_urls(argv)
            }
            if not hosts or not hosts.issubset(allowed_hosts[lane]):
                network_failures.append(f"{label}:hosts:{sorted(hosts)}")
            if Path(argv[0]).name.lower() == "curl.exe":
                if not (
                    "--disable" in argv
                    and option_value(argv, "--proxy") == ""
                    and option_value(argv, "--max-redirs") == "0"
                    and option_value(argv, "--proto") == "=https"
                    and option_value(argv, "--proto-redir") == "=https"
                    and "--dump-header" in argv
                    and "--fail" in argv
                ):
                    network_failures.append(f"{label}:curl-hardening")
            elif Path(argv[0]).name.lower() == "python.exe":
                if not (
                    argv[0].lower() == VENV_PYTHON.lower()
                    and "-I" in argv
                    and "--isolated" in argv
                    and "--only-binary=:all:" in argv
                    and "download" in argv
                ):
                    network_failures.append(f"{label}:pip-download-isolation")
            else:
                network_failures.append(f"{label}:network-executable:{argv[0]}")
    diagnostics["network_failures"] = network_failures
    check(
        checks,
        failures,
        "network_command_ids_hosts_and_hardening",
        not network_failures,
    )

    environment_executable_text = "\n".join(
        str(row["argv"][0]) for row in rows_by_lane["environment"] if row.get("argv")
    ).lower()
    check(
        checks,
        failures,
        "no_windows_installer_or_package_manager_executable",
        not any(
            token in environment_executable_text
            for token in (
                "python-3.11.9-amd64.exe",
                "msiexec",
                "nuget.exe",
                "winget",
                "uv.exe",
                "conda",
                "py.exe",
            )
        ),
    )

    e05 = next(
        (
            row
            for row in all_rows
            if row["_id"] == "E05_SAFE_SCAN_EXTRACT_AND_PROMOTE_RUNTIME"
        ),
        None,
    )
    e05_source = "\n".join(e05["argv"]) if e05 else ""
    e05_markers = (
        "UNSAFE_OR_DIRECTORY",
        "TRAVERSAL",
        "UNIX_TYPE",
        "DUPLICATE_OR_CASE",
        "MEMBER_LIMIT",
        "TOTAL_LIMIT",
        "TARGET_ESCAPE",
        "REPARSE",
        "ARCHIVE_INVENTORY",
        "RUNTIME_INVENTORY",
        NUGET["all_inventory"],
        NUGET["runtime_inventory"],
    )
    check(checks, failures, "e05_present", e05 is not None)
    check(
        checks,
        failures,
        "e05_safe_scan_and_inventory_contract",
        all(marker in e05_source for marker in e05_markers)
        and e05_source.find("ARCHIVE_INVENTORY") < e05_source.find("Move-Item")
        and e05_source.find("RUNTIME_INVENTORY") < e05_source.find("Move-Item"),
    )

    e06 = next(
        (
            row
            for row in all_rows
            if row["_id"] == "E06_VERIFY_EXACT_PROMOTED_RUNTIME_IDENTITY"
        ),
        None,
    )
    e06_source = "\n".join(e06["argv"]) if e06 else ""
    check(checks, failures, "e06_present", e06 is not None)
    check(
        checks,
        failures,
        "e06_exact_runtime_identity_contract",
        e06 is not None
        and e06["argv"][0].lower() == RUNTIME_PYTHON.lower()
        and all(
            marker in e06_source
            for marker in (
                "CPython",
                "3.11.9",
                "cp311-cp311-win_amd64",
                "sys_executable",
                "sys_prefix",
                "sys_base_prefix",
                "python_sha256",
                "5f7b89a612c9b8af1d6456cdfcd1dbe5ca630849e79aebced9bee9a6694952ec",
            )
        ),
    )

    syntax = syntax_scan(all_rows)
    diagnostics["syntax"] = syntax
    check(checks, failures, "python_inline_ast_parse", not syntax["python_errors"])
    check(checks, failures, "powershell_scriptblock_parse", not syntax["powershell_errors"])

    scientific_patterns = (
        "create_dataset(",
        "data_preparation(",
        "run_recbole(",
        "trainer(",
        ".fit(",
        ".evaluate(",
        "full_sort_topk(",
    )
    scientific_matches: list[str] = []
    for row in all_rows:
        source = "\n".join(row["argv"]).lower()
        for pattern in scientific_patterns:
            if pattern in source:
                scientific_matches.append(f"{row['_id']}:{pattern}")
    diagnostics["scientific_execution_matches"] = scientific_matches
    check(checks, failures, "no_scientific_execution_callables", not scientific_matches)
    check(
        checks,
        failures,
        "truth_state_locked",
        '"RESULT_STATUS": "NOT_RUN"' in combined_text
        and '"TEST_SET_OPENED": "NO"' in combined_text
        and '"ACCEPTED_RESULT_ROWS": 0' in combined_text,
    )

    proposal_state_failures: list[str] = []
    for name, document in documents.items():
        if document.get("proposal_only") is not True:
            proposal_state_failures.append(f"{name}:proposal_only")
        if document.get("execution_performed") is not False:
            proposal_state_failures.append(f"{name}:execution_performed")
        if document.get("execution_authorized") is not False:
            proposal_state_failures.append(f"{name}:execution_authorized")
    diagnostics["proposal_state_failures"] = proposal_state_failures
    check(
        checks,
        failures,
        "all_five_files_remain_proposal_only",
        not proposal_state_failures,
    )

    handoff = documents[EXPECTED_FILES[4]]
    assembler = handoff.get("assembler", {})
    assembler_text = scalar_text(assembler).lower()
    check(
        checks,
        failures,
        "standard_model_policy_for_current_rework",
        isinstance(assembler, dict)
        and assembler.get("display_name") == "Sol High Standard"
        and assembler.get("runtime_model_id") == "gpt-5.6-sol"
        and assembler.get("reasoning_effort") == "high"
        and "fast" not in assembler_text
        and "priority" not in assembler_text,
    )

    control_text, control_compact = normalized_control_text(
        {
            "boundary": documents[EXPECTED_FILES[3]],
            "handoff": handoff.get("runner_controls_encoded", {}),
            "canonical": handoff.get("runner_required_controls", []),
        }
    )
    control_groups = {
        "oserror": "oserror" in control_compact,
        "file_not_found": "filenotfounderror" in control_compact
        or "file not found" in control_text,
        "append_only_journal": "append only" in control_text
        and "journal" in control_text,
        "required_outputs_postconditions": "required output" in control_text
        and "postcondition" in control_text,
        "command_lane_write_sets": "write set" in control_text
        and "lane" in control_text,
        "sentinels": "sentinel" in control_text
        and "registry" in control_text
        and "filesystem" in control_text
        and "before" in control_text
        and "after" in control_text,
        "fail_closed_bounds": "fail closed" in control_text
        and "timeout" in control_text
        and "network" in control_text,
        "no_retry_cleanup_rollback_fallback": "noretry" in control_compact
        and "cleanup" in control_text
        and "rollback" in control_text
        and "fallback" in control_text,
    }
    diagnostics["runner_control_groups"] = control_groups
    check(
        checks,
        failures,
        "runner_handoff_controls_explicit",
        all(control_groups.values()),
    )
    check(
        checks,
        failures,
        "bridge_gate_requires_two_pass_receipts",
        "dataset" in bridge_text.lower()
        and "environment" in bridge_text.lower()
        and "pass" in bridge_text.lower()
        and "blocked" in bridge_text.lower(),
    )

    diagnostics["packet_fingerprints"] = [
        fingerprint(PACKET_ROOT / name) for name in EXPECTED_FILES
    ]
    diagnostics["check_count"] = len(checks)
    diagnostics["passed_check_count"] = sum(checks.values())
    verdict = (
        "PASS_R6_C1R2_ATTEMPT003_PACKET_READY_FOR_BOUNDED_R6_M0_R6_M1_DISPATCH"
        if not failures
        else "FAIL_R6_C1R2_REWORK_REQUIRED"
    )
    result = {
        "verdict": verdict,
        "checks": checks,
        "failures": failures,
        "diagnostics": diagnostics,
        "scientific_execution_performed": False,
        "materialization_executed": False,
        "test_set_opened": "NO",
        "accepted_result_rows": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
