from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED_FILES = [
    "dataset_materialization_packet.json",
    "environment_materialization_packet.json",
    "recbole_dataset_bridge_packet.json",
    "execution_boundary_and_negative_assertions.json",
    "audit_handoff.json",
]
STAGE_ID = "R6-C1R3-LINUX"
PACKET_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_bd/"
    "E4_R6C1R3_linux_command_packet"
)
G1_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc2w_g1_backend_admission_receipt.json"
)
MANIFEST_RELATIVE = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ac/"
    "E4_R5M0_source_materialization/selected_blob_manifest.json"
)
DOCKER_EXE = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
DOCKER_BYTES = 42_748_848
DOCKER_SHA256 = "0cdb9dea2e39a0a29e5dc3f9732f572dc140547b28deab0495589b4f79b31ca1"
IMAGE_INDEX_DIGEST = "sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317"
IMAGE_MANIFEST_DIGEST = "sha256:2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
IMAGE_REF = f"docker.io/library/python@{IMAGE_MANIFEST_DIGEST}"
IMAGE_TAG = "docker.io/library/python:3.11.9-slim-bookworm"
DATA_ROOT = Path(
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6\official_source"
    r"\grouplens_ml100k\attempt-004-linux"
)
ENV_ROOT = Path(
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    r"\recbole_bpr_ml100k_py3119_cpu\attempt-004-linux"
)
SOURCE_ROOT = Path(
    r"E:\UIT\cv\backend\research\hybrid-recsys-v5\03_benchmark\stage1e"
    r"\materialized_sources\r5\recbole_v1_2_1_9a6f63d"
)
G1_BYTES = 6003
G1_SHA256 = "7fac9ee1377ad183f12d3acb04061700d5218642d809dd54fe35ad79388605b1"
MANIFEST_GIT_BYTES = 102_765
MANIFEST_GIT_SHA256 = "c5794b9daccdd01ca600c6ef7f890918825fbbb872efa67036c4565234e87016"
RECBOLE_COMMIT = "9a6f63d8d4a5b989fe27955a833f813a6d86041e"
RECBOLE_TREE = "08915121fea069a30f7e3e97a72e16e7e76d43c6"
ML100K_MD5 = "0e33842e24a9c977be4e0107933c0723"
ML100K_SHA256 = "50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229"
EXPECTED_COUNTS = {"image": 3, "dataset": 3, "environment": 11, "bridge": 3, "total": 20}
EXPECTED_NETWORK_IDS = [
    "I00_PULL_EXACT_OFFICIAL_PLATFORM_MANIFEST",
    "M00_ACQUIRE_OFFICIAL_GROUPLENS_BYTES",
    "E00_DOWNLOAD_LINUX_WHEEL_CLOSURE",
]
EXPECTED_ADAPTERS = {
    "IMAGE_IDENTITY_V1",
    "PYTHON_RUNTIME_IDENTITY_V1",
    "DATASET_ACQUISITION_V1",
    "DATASET_MATERIALIZATION_V1",
    "WHEEL_CLOSURE_V1",
    "ENVIRONMENT_MATERIALIZATION_V1",
    "BRIDGE_COPY_V1",
}
PASSPORT_FIELDS = {
    "origin_skill",
    "origin_mode",
    "origin_date",
    "verification_status",
    "version_label",
    "upstream_dependencies",
    "repro_lock",
    "experiment_intake_declaration",
    "experiment_provenance",
}


class StrictJsonError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate key: {key}")
        lowered = key.casefold()
        if lowered in folded and folded[lowered] != key:
            raise StrictJsonError(f"case-colliding keys: {folded[lowered]} / {key}")
        folded[lowered] = key
        result[key] = value
    return result


def strict_load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError(f"UTF-8 BOM forbidden: {path}")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise StrictJsonError(f"top-level object required: {path}")
    return value


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def argv_hash(argv: list[str]) -> str:
    raw = json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(raw)


def is_reparse(path: Path) -> bool:
    try:
        stat_result = path.lstat()
    except OSError:
        return False
    attributes = getattr(stat_result, "st_file_attributes", 0)
    return bool(attributes & getattr(os, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("REPOSITORY_ROOT_NOT_FOUND")


def check(
    checks: list[dict[str, Any]],
    failures: list[str],
    name: str,
    passed: bool,
    detail: Any = None,
) -> None:
    row: dict[str, Any] = {"name": name, "passed": bool(passed)}
    if detail is not None:
        row["detail"] = detail
    checks.append(row)
    if not passed:
        failures.append(name if detail is None else f"{name}:{detail}")


def option_value(argv: list[str], option: str) -> str | None:
    try:
        index = argv.index(option)
    except ValueError:
        return None
    return argv[index + 1] if index + 1 < len(argv) else None


def git_blob(repo: Path, relative: Path) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=repo,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-root", type=Path)
    args = parser.parse_args()
    repo = find_repo_root(Path(__file__).resolve())
    packet_root = (args.packet_root or (repo / PACKET_RELATIVE)).resolve()
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    diagnostics: dict[str, Any] = {"packet_root": str(packet_root), "repo": str(repo)}

    check(checks, failures, "packet_root_exists", packet_root.is_dir())
    if not packet_root.is_dir():
        print(json.dumps({"verdict": "FAIL_R6_C1R3_LINUX_REWORK_REQUIRED", "checks": checks, "failures": failures}, indent=2))
        return 1

    entries = list(packet_root.iterdir())
    observed = sorted(path.name for path in entries)
    check(checks, failures, "exact_five_file_set", observed == sorted(EXPECTED_FILES), observed)
    check(checks, failures, "all_outputs_regular_non_reparse", all(path.is_file() and not path.is_symlink() and not is_reparse(path) for path in entries))

    try:
        docs = {name: strict_load(packet_root / name) for name in EXPECTED_FILES}
    except Exception as exc:
        failures.append(f"strict_json:{type(exc).__name__}:{exc}")
        print(json.dumps({"verdict": "FAIL_R6_C1R3_LINUX_REWORK_REQUIRED", "checks": checks, "failures": failures}, indent=2))
        return 1
    check(checks, failures, "strict_json_outputs_5_of_5", len(docs) == 5)
    check(checks, failures, "utf8_lf_final_newline", all((packet_root / name).read_bytes().endswith(b"\n") and b"\r\n" not in (packet_root / name).read_bytes() for name in EXPECTED_FILES))

    for name, doc in docs.items():
        check(checks, failures, f"{name}:stage_id", doc.get("stage_id") == STAGE_ID)
        check(checks, failures, f"{name}:proposal_only", doc.get("proposal_only") is True)
        check(checks, failures, f"{name}:execution_performed", doc.get("execution_performed") is False)
        check(checks, failures, f"{name}:execution_authorized", doc.get("execution_authorized") is False)
        passport = doc.get("material_passport")
        check(checks, failures, f"{name}:material_passport", isinstance(passport, dict) and PASSPORT_FIELDS <= set(passport))
        truth = doc.get("truth_state")
        check(
            checks,
            failures,
            f"{name}:truth_state",
            isinstance(truth, dict)
            and truth.get("RESULT_STATUS") == "NOT_RUN"
            and truth.get("TEST_SET_OPENED") == "NO"
            and truth.get("ACCEPTED_RESULT_ROWS") == 0
            and truth.get("execution_authorized") is False
            and truth.get("phase_1e_complete") is False,
        )

    dataset = docs[EXPECTED_FILES[0]]
    environment = docs[EXPECTED_FILES[1]]
    bridge = docs[EXPECTED_FILES[2]]
    boundary = docs[EXPECTED_FILES[3]]
    handoff = docs[EXPECTED_FILES[4]]

    check(checks, failures, "attempt_names_exact", dataset.get("attempt") == "attempt-004-linux" and environment.get("attempt") == "attempt-004-linux")
    check(checks, failures, "host_attempt_roots_exact", dataset.get("roots", {}).get("host_attempt_root") == str(DATA_ROOT) and environment.get("roots", {}).get("host_attempt_root") == str(ENV_ROOT))
    check(checks, failures, "attempt_roots_absent", not DATA_ROOT.exists() and not ENV_ROOT.exists())
    check(checks, failures, "attempt_root_ancestors_not_reparse", not any(is_reparse(path) for root in (DATA_ROOT, ENV_ROOT) for path in root.parents if path.exists()))

    image_lock = environment.get("base_image_lock", {})
    check(checks, failures, "image_index_digest_exact", image_lock.get("index_digest") == IMAGE_INDEX_DIGEST)
    check(checks, failures, "image_platform_manifest_exact", image_lock.get("platform_manifest_digest") == IMAGE_MANIFEST_DIGEST)
    check(checks, failures, "image_execution_ref_digest_only", image_lock.get("immutable_execution_reference") == IMAGE_REF)
    check(checks, failures, "floating_tag_execution_forbidden", image_lock.get("historical_tag_evidence_only") == IMAGE_TAG and image_lock.get("floating_tag_execution_allowed") is False)
    check(checks, failures, "image_platform_python_exact", image_lock.get("os") == "linux" and image_lock.get("architecture") == "amd64" and image_lock.get("python_version") == "3.11.9")
    check(checks, failures, "image_candidate_has_no_fallback", image_lock.get("candidate_fallback") is None)

    official = dataset.get("official_identity", {})
    check(checks, failures, "dataset_provider_hashes_exact", official.get("provider_md5") == ML100K_MD5 and official.get("locally_recomputed_frozen_sha256") == ML100K_SHA256)
    check(checks, failures, "dataset_expected_size_exact", official.get("archive_expected_bytes") == 4_924_029)
    transform = dataset.get("frozen_transformation", {})
    check(checks, failures, "dataset_cardinalities_exact", transform.get("input_rows") == 100_000 and transform.get("output_rows") == 100_000 and transform.get("users") == 943 and transform.get("items") == 1682)
    check(checks, failures, "dataset_no_semantic_rewrite", transform.get("row_order_preserved") is True and transform.get("filtering_deduplication_sorting_id_or_timestamp_rewrite") is False)
    zip_contract = dataset.get("safe_zip_contract", {})
    check(checks, failures, "dataset_zip_inventory_exact", zip_contract.get("exact_file_count") == 23 and len(zip_contract.get("exact_files", [])) == 23 and len(set(zip_contract.get("exact_files", []))) == 23)

    source_lock = environment.get("recbole_source_lock", {})
    check(checks, failures, "recbole_revision_tree_exact", source_lock.get("revision") == RECBOLE_COMMIT and source_lock.get("git_tree") == RECBOLE_TREE)
    check(checks, failures, "recbole_manifest_lock_exact", source_lock.get("selected_manifest_git_blob_bytes") == MANIFEST_GIT_BYTES and source_lock.get("selected_manifest_git_blob_sha256") == MANIFEST_GIT_SHA256)
    check(checks, failures, "recbole_source_cardinality_exact", source_lock.get("selected_file_count") == 265 and source_lock.get("selected_total_bytes") == 1_541_044 and source_lock.get("selected_python_file_count") == 150 and source_lock.get("selected_python_total_bytes") == 1_378_341)

    image_commands = boundary.get("image_acquisition_and_probe_commands", [])
    dataset_commands = dataset.get("commands", [])
    environment_commands = environment.get("commands", [])
    bridge_commands = bridge.get("commands", [])
    lanes = {
        "image": image_commands,
        "dataset": dataset_commands,
        "environment": environment_commands,
        "bridge": bridge_commands,
    }
    all_commands = image_commands + dataset_commands + environment_commands + bridge_commands
    actual_counts = {name: len(rows) for name, rows in lanes.items()}
    actual_counts["total"] = len(all_commands)
    check(checks, failures, "command_counts_exact", actual_counts == EXPECTED_COUNTS and boundary.get("command_counts") == EXPECTED_COUNTS, actual_counts)
    ids = [row.get("id") for row in all_commands]
    check(checks, failures, "command_ids_unique", len(ids) == len(set(ids)) and all(isinstance(value, str) and value for value in ids))
    check(checks, failures, "lane_orders_exact", dataset.get("command_order") == [row.get("id") for row in dataset_commands] and environment.get("command_order") == [row.get("id") for row in environment_commands] and bridge.get("command_order") == [row.get("id") for row in bridge_commands])
    network_ids = [row.get("id") for row in all_commands if row.get("network") is True]
    check(checks, failures, "network_command_ids_exact", network_ids == EXPECTED_NETWORK_IDS and boundary.get("network_command_ids") == EXPECTED_NETWORK_IDS, network_ids)

    command_failures: list[str] = []
    script_failures: list[str] = []
    run_count = 0
    allowed_mounts = {
        (str(DATA_ROOT), "/stage1e/data", False),
        (str(DATA_ROOT), "/stage1e/data", True),
        (str(ENV_ROOT), "/stage1e/env", False),
        (str(SOURCE_ROOT), "/stage1e/recbole-source", True),
    }
    scientific_forbidden = [
        "run_recbole",
        "create_dataset",
        "Trainer(",
        ".fit(",
        ".evaluate(",
        "calculate_metric",
        "HyperTuning",
        "project-v5/TEST",
        "04_experiments",
    ]
    for row in all_commands:
        command_id = row.get("id", "<missing>")
        argv = row.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(token, str) and token for token in argv):
            command_failures.append(f"{command_id}:argv")
            continue
        if row.get("argv_sha256") != argv_hash(argv):
            command_failures.append(f"{command_id}:argv_hash")
        if argv[0] != str(DOCKER_EXE):
            command_failures.append(f"{command_id}:docker_executable")
        if not isinstance(row.get("network"), bool):
            command_failures.append(f"{command_id}:network_bool")
        if not isinstance(row.get("timeout_seconds"), int) or row["timeout_seconds"] <= 0:
            command_failures.append(f"{command_id}:timeout")
        for field in ("write_set", "required_outputs", "postconditions"):
            if not isinstance(row.get(field), list):
                command_failures.append(f"{command_id}:{field}")
        text = "\n".join(argv)
        if IMAGE_TAG in text:
            command_failures.append(f"{command_id}:tag_in_execution")
        for token in scientific_forbidden:
            if token.casefold() in text.casefold():
                command_failures.append(f"{command_id}:scientific_surface:{token}")
        if any(old in text.casefold() for old in ("attempt-001", "attempt-002", "attempt-003")):
            command_failures.append(f"{command_id}:old_attempt_locator")
        if argv[1:2] == ["run"]:
            run_count += 1
            required_flags = ["--rm", "--pull=never", "--read-only", "--tmpfs", "--user", "--cap-drop", "--security-opt", "--pids-limit", "--cpus", "--memory", "--stop-timeout", "--workdir"]
            missing = [flag for flag in required_flags if flag not in argv]
            if missing:
                command_failures.append(f"{command_id}:missing_flags:{','.join(missing)}")
            expectations = {
                "--platform": "linux/amd64",
                "--user": "10001:10001",
                "--cap-drop": "ALL",
                "--security-opt": "no-new-privileges",
                "--pids-limit": "256",
                "--cpus": "2",
                "--memory": "4g",
                "--stop-timeout": "10",
            }
            for flag, expected in expectations.items():
                if option_value(argv, flag) != expected:
                    command_failures.append(f"{command_id}:{flag}")
            expected_network = "bridge" if row.get("network") else "none"
            if option_value(argv, "--network") != expected_network:
                command_failures.append(f"{command_id}:network_mode")
            if argv.count(IMAGE_REF) != 1:
                command_failures.append(f"{command_id}:image_ref")
            if any(flag in argv for flag in ("--privileged", "--volume", "-v")):
                command_failures.append(f"{command_id}:forbidden_container_flag")
            mount_values = [argv[index + 1] for index, token in enumerate(argv[:-1]) if token == "--mount"]
            for value in mount_values:
                parts = {item.split("=", 1)[0]: item.split("=", 1)[1] if "=" in item else True for item in value.split(",")}
                candidate = (str(parts.get("src")), str(parts.get("dst")), bool(parts.get("readonly", False)))
                if candidate not in allowed_mounts:
                    command_failures.append(f"{command_id}:mount:{value}")
                lowered = value.casefold()
                if "docker.sock" in lowered or "c:\\users\\acer,dst=" in lowered or "src=e:\\,dst=" in lowered:
                    command_failures.append(f"{command_id}:broad_or_socket_mount")
            if command_id.startswith("B") and not any("src=" + str(DATA_ROOT) in value and "readonly" in value for value in mount_values):
                command_failures.append(f"{command_id}:dataset_mount_not_readonly")
            for index, token in enumerate(argv[:-1]):
                if token == "-c" and index > 0 and (argv[index - 1].endswith("python") or argv[index - 1] == "/usr/local/bin/python"):
                    try:
                        compile(argv[index + 1], f"<{command_id}>", "exec")
                    except Exception as exc:
                        script_failures.append(f"{command_id}:{type(exc).__name__}:{exc}")
        elif command_id == "I00_PULL_EXACT_OFFICIAL_PLATFORM_MANIFEST":
            if argv != [str(DOCKER_EXE), "pull", "--platform", "linux/amd64", IMAGE_REF]:
                command_failures.append(f"{command_id}:exact_pull_argv")
        elif command_id == "I01_INSPECT_LOCAL_IMAGE_IDENTITY":
            if argv != [str(DOCKER_EXE), "image", "inspect", IMAGE_REF]:
                command_failures.append(f"{command_id}:exact_inspect_argv")
        else:
            command_failures.append(f"{command_id}:unexpected_docker_surface")

    diagnostics["command_failures"] = command_failures
    diagnostics["script_failures"] = script_failures
    diagnostics["docker_run_count"] = run_count
    check(checks, failures, "all_command_contracts_and_hashes", not command_failures, command_failures)
    check(checks, failures, "all_inline_python_scripts_compile", not script_failures, script_failures)
    check(checks, failures, "docker_run_count_exact", run_count == 18, run_count)

    adapter_rows = boundary.get("typed_postcondition_adapters", [])
    adapter_ids = {row.get("schema_id") for row in adapter_rows if isinstance(row, dict)}
    producers = {row.get("producer") for row in adapter_rows if isinstance(row, dict)}
    check(checks, failures, "typed_adapter_set_exact", adapter_ids == EXPECTED_ADAPTERS, sorted(value for value in adapter_ids if isinstance(value, str)))
    check(checks, failures, "typed_adapter_producers_exist", producers <= set(ids) and all(isinstance(row.get("required_fields"), dict) and row.get("invariants") for row in adapter_rows))
    policy = boundary.get("container_policy", {})
    check(checks, failures, "container_policy_fail_closed", all(policy.get(key) is True for key in ("immutable_digest_only", "pull_never_for_every_container_run", "offline_network_none", "read_only_root", "tmpfs_only_scratch", "no_new_privileges")) and policy.get("capabilities_dropped") == "ALL" and policy.get("non_root_uid_gid") == "10001:10001")
    auth = boundary.get("authorization_boundary", {})
    check(checks, failures, "authorization_remains_closed", auth.get("packet_design_authorized") is True and auth.get("static_validation_authorized") is True and auth.get("independent_audit_required") is True and auth.get("image_pull_build_or_run_authorized") is False and auth.get("materialization_authorized") is False and auth.get("training_or_evaluation_authorized") is False and auth.get("test_access_authorized") is False)
    check(checks, failures, "bridge_still_blocked", bridge.get("execution_gate", {}).get("current_status") == "BLOCKED_PENDING_R6_M0_AND_R6_M1" and bridge.get("negative_assertions", {}).get("currently_executable") is False)
    check(checks, failures, "handoff_verdict_proposal_only", handoff.get("verdict") == "PROPOSAL_R6_C1R3_LINUX_READY_FOR_CENTRAL_STATIC_VALIDATION_THEN_FRESH_XHIGH_AUDIT")
    audit_profile = handoff.get("required_fresh_audit_profile", {})
    check(checks, failures, "fresh_audit_profile_xhigh_standard", audit_profile.get("model") == "gpt-5.6-sol" and audit_profile.get("reasoning_effort") == "xhigh" and audit_profile.get("service_tier") == "default" and audit_profile.get("fast_or_priority_forbidden") is True)

    g1_path = repo / G1_RELATIVE
    g1_raw = g1_path.read_bytes() if g1_path.is_file() else b""
    check(checks, failures, "g1_receipt_raw_binding", len(g1_raw) == G1_BYTES and sha256_bytes(g1_raw) == G1_SHA256)
    try:
        g1 = strict_load(g1_path)
        g1_semantics = g1.get("verdict") == "PASS_R6_PC2W_G1_CURRENT_HOST_BACKEND_ADMITTED_FOR_TRUSTED_PINNED_PACKET_DESIGN_ONLY" and g1.get("authorization_state", {}).get("r6_c1r3_linux_packet_design_authorized") is True and g1.get("authorization_state", {}).get("materialization_authorized") is False
    except Exception:
        g1_semantics = False
    check(checks, failures, "g1_receipt_semantics", g1_semantics)

    try:
        manifest_blob = git_blob(repo, MANIFEST_RELATIVE)
        manifest_blob_ok = len(manifest_blob) == MANIFEST_GIT_BYTES and sha256_bytes(manifest_blob) == MANIFEST_GIT_SHA256
    except Exception as exc:
        manifest_blob = b""
        manifest_blob_ok = False
        diagnostics["manifest_git_error"] = f"{type(exc).__name__}:{exc}"
    check(checks, failures, "source_manifest_git_blob_binding", manifest_blob_ok)

    source_failures: list[str] = []
    source_files = 0
    source_bytes = 0
    try:
        manifest = json.loads(manifest_blob.decode("utf-8"), object_pairs_hook=strict_object)
        candidate = next(row for row in manifest["candidates"] if row["candidate_id"] == "R5-CAND-RECBOLE-BPR-ML100K-001")
        expected_paths = set()
        for row in candidate["files"]:
            expected_paths.add(row["path"])
            path = SOURCE_ROOT / Path(row["path"])
            if not path.is_file() or path.is_symlink() or is_reparse(path):
                source_failures.append(f"missing_or_nonregular:{row['path']}")
                continue
            raw = path.read_bytes()
            source_files += 1
            source_bytes += len(raw)
            if len(raw) != row["size_bytes"] or sha256_bytes(raw) != row["sha256_raw_bytes"]:
                source_failures.append(f"hash:{row['path']}")
        actual_paths = {
            path.relative_to(SOURCE_ROOT).as_posix()
            for path in SOURCE_ROOT.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(SOURCE_ROOT).parts
        }
        if actual_paths != expected_paths:
            source_failures.append("exact_file_set")
    except Exception as exc:
        source_failures.append(f"{type(exc).__name__}:{exc}")
    diagnostics["source_replay"] = {"files": source_files, "bytes": source_bytes, "failures": source_failures[:20], "failure_count": len(source_failures)}
    check(checks, failures, "recbole_source_replay_265_of_265", not source_failures and source_files == 265 and source_bytes == 1_541_044, diagnostics["source_replay"])

    docker_ok = DOCKER_EXE.is_file() and not DOCKER_EXE.is_symlink() and not is_reparse(DOCKER_EXE)
    if docker_ok:
        docker_raw = DOCKER_EXE.read_bytes()
        docker_ok = len(docker_raw) == DOCKER_BYTES and sha256_bytes(docker_raw) == DOCKER_SHA256
    check(checks, failures, "docker_executable_static_identity", docker_ok)

    packet_fingerprints = []
    for name in EXPECTED_FILES:
        raw = (packet_root / name).read_bytes()
        packet_fingerprints.append({"path": name, "bytes": len(raw), "sha256": sha256_bytes(raw)})
    diagnostics["packet_fingerprints"] = packet_fingerprints
    diagnostics["check_count"] = len(checks)
    diagnostics["passed_count"] = sum(1 for row in checks if row["passed"])
    verdict = "PASS_R6_C1R3_LINUX_PACKET_READY_FOR_FRESH_XHIGH_AUDIT" if not failures else "FAIL_R6_C1R3_LINUX_REWORK_REQUIRED"
    result = {
        "schema_version": "stage1e-r6-c1r3-linux-static-validation-result-1.0",
        "verdict": verdict,
        "checks": checks,
        "failures": failures,
        "diagnostics": diagnostics,
        "truth_state": {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0, "execution_authorized": False},
    }
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
