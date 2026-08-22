from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
MANIFEST_PATH = CONTROL / "e4_r6_g0_frozen_input_manifest.json"
DECISION_PATH = CONTROL / "e4_r6_g0_decision_freeze.json"

SELECTED_CANDIDATE = "R5-CAND-RECBOLE-BPR-ML100K-001"
SELECTED_REVISION = "9a6f63d8d4a5b989fe27955a833f813a6d86041e"
SELECTED_TREE = "08915121fea069a30f7e3e97a72e16e7e76d43c6"
ENTRY_COMMIT = "de3fddc853f0264aebf5a6485fec1f5e43239b6f"

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

EXPECTED_C1_OUTPUTS = [
    "dataset_materialization_packet.json",
    "environment_materialization_packet.json",
    "recbole_dataset_bridge_packet.json",
    "execution_boundary_and_negative_assertions.json",
    "audit_handoff.json",
]

EXPECTED_SOURCE_HASHES = {
    "setup.py": "9fd93b134e7586757a47a2fcad689fdf0a300c4c3033990f95e58449d568ef06",
    "MANIFEST.in": "603d44fb0a0b8424911d225907d157ee4105d0bb273c6e2c6ee44b0b4afec10c",
    "recbole/config/configurator.py": "a5f3f3ba902537d2f678c0f011e7a6d5d706606fae041074913bb651811f1aed",
    "recbole/data/dataset/dataset.py": "9e752eea85d84280f1ea5c752a3be055ab8deb1c03c1196d1a02f46065deee5e",
    "recbole/properties/dataset/ml-100k.yaml": "9890771341fe556dc14ee0f004ec6b72efeeac2fef8bfca2c78f7416e6c4f449",
    "recbole/properties/dataset/url.yaml": "6bd6c438a9b2cce7fa8d81ea6dbe0333b37f83270046d37162ce2775ada51d03",
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
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise StrictJsonError(f"top-level object required: {path}")
    return value


def raw_fingerprint(path: Path) -> tuple[int, str]:
    payload = path.read_bytes()
    return len(payload), hashlib.sha256(payload).hexdigest()


def canonical_lf_fingerprint(path: Path) -> tuple[int, str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    payload = text.encode("utf-8")
    return len(payload), hashlib.sha256(payload).hexdigest()


def check(
    checks: dict[str, bool], failures: list[str], check_id: str, condition: bool
) -> None:
    checks[check_id] = bool(condition)
    if not condition:
        failures.append(check_id)


def is_outside_repo_windows(path_text: str) -> bool:
    path = str(PureWindowsPath(path_text)).casefold().rstrip("\\")
    repo = str(PureWindowsPath(r"E:\UIT\cv\backend")).casefold().rstrip("\\")
    return path != repo and not path.startswith(repo + "\\")


def truth_is_closed(value: dict[str, Any]) -> bool:
    return (
        value.get("RESULT_STATUS") == "NOT_RUN"
        and value.get("TEST_SET_OPENED") == "NO"
        and value.get("ACCEPTED_RESULT_ROWS") == 0
        and value.get("execution_authorized") is False
        and value.get("project_benchmark_numbers") == "INVALID_FOR_PAPER"
    )


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    manifest = strict_load(MANIFEST_PATH)
    decision = strict_load(DECISION_PATH)
    rows = manifest.get("inputs", [])
    row_paths = [row.get("path") for row in rows if isinstance(row, dict)]

    check(
        checks,
        failures,
        "manifest_identity_and_counts",
        manifest.get("stage_id") == "R6-G0"
        and manifest.get("frozen_at_commit") == ENTRY_COMMIT
        and manifest.get("expected_input_count") == 31
        and len(rows) == 31
        and len(row_paths) == len(set(row_paths)) == 31
        and manifest.get("expected_strict_json_count") == 19,
    )

    fingerprint_failures: list[str] = []
    strict_json_failures: list[str] = []
    strict_json_count = 0
    for row in rows:
        if not isinstance(row, dict):
            fingerprint_failures.append("NON_OBJECT_ROW")
            continue
        relative = row.get("path")
        path = ROOT / str(relative)
        if not path.is_file():
            fingerprint_failures.append(f"MISSING:{relative}")
            continue
        raw_bytes, raw_sha = raw_fingerprint(path)
        canonical_bytes, canonical_sha = canonical_lf_fingerprint(path)
        if (
            row.get("raw_bytes") != raw_bytes
            or row.get("raw_sha256") != raw_sha
            or row.get("canonical_lf_bytes") != canonical_bytes
            or row.get("canonical_lf_sha256") != canonical_sha
        ):
            fingerprint_failures.append(f"HASH:{relative}")
        if row.get("strict_json") is True:
            strict_json_count += 1
            try:
                strict_load(path)
            except (OSError, UnicodeError, json.JSONDecodeError, StrictJsonError) as exc:
                strict_json_failures.append(f"{relative}:{exc}")

    check(
        checks,
        failures,
        "frozen_inputs_31_of_31_raw_and_canonical_hash_match",
        not fingerprint_failures,
    )
    check(
        checks,
        failures,
        "strict_json_inputs_19_of_19",
        strict_json_count == 19 and not strict_json_failures,
    )

    approval = strict_load(
        CONTROL / "e4_r5_m2_user_approval_receipt.json"
    )
    lane_receipt = strict_load(
        CONTROL / "rebaseline_v2_e4_r6_d1_e1_lanes_validation_receipt.json"
    )
    check(
        checks,
        failures,
        "user_authority_replayed_without_scope_expansion",
        approval.get("status")
        == "USER_APPROVED_BOUNDED_DATASET_ENVIRONMENT_AND_COMMAND_MATERIALIZATION_SCOPE"
        and approval.get("authorization_state", {}).get("materialization_authorized") is True
        and approval.get("authorization_state", {}).get("experiment_execution_authorized") is False
        and approval.get("still_prohibited", {}).get("vendor_training_execution") is True
        and approval.get("still_prohibited", {}).get("source_evaluator_execution") is True
        and approval.get("still_prohibited", {}).get("project_v5_test_access") is True,
    )
    check(
        checks,
        failures,
        "r6_d1_e1_central_gate_replayed",
        lane_receipt.get("validation_run", {}).get("verdict")
        == "PASS_R6_D1_E1_READY_FOR_R6_G0_FREEZE"
        and lane_receipt.get("validation_run", {}).get("checks_passed") == 30
        and lane_receipt.get("validation_run", {}).get("failure_count") == 0,
    )

    entry = decision.get("entry_gate", {})
    check(
        checks,
        failures,
        "decision_entry_candidate_revision_tree_exact",
        entry.get("commit") == ENTRY_COMMIT
        and entry.get("candidate_id") == SELECTED_CANDIDATE
        and entry.get("pinned_recbole_revision") == SELECTED_REVISION
        and entry.get("pinned_recbole_git_tree") == SELECTED_TREE,
    )
    check(
        checks,
        failures,
        "central_model_profile_exact",
        decision.get("central_profile")
        == {
            "display_name": "Sol Max Standard",
            "runtime_model_id": "gpt-5.6-sol",
            "reasoning_effort": "max",
            "service_tier": "standard",
        },
    )
    selection = decision.get("selection_rule", {})
    check(
        checks,
        failures,
        "selection_not_benchmark_or_historical_claim_driven",
        selection.get("benchmark_value_used") is False
        and selection.get("historical_environment_claimed") is False
        and selection.get("historical_checksum_claimed") is False,
    )

    dataset = decision.get("dataset_profile", {})
    check(
        checks,
        failures,
        "dataset_current_official_grouplens_identity_exact",
        dataset.get("provider") == "GroupLens Research Project, University of Minnesota"
        and dataset.get("dataset") == "MovieLens 100K"
        and dataset.get("official_archive_url")
        == "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
        and dataset.get("official_current_checksum_url")
        == "https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5",
    )
    check(
        checks,
        failures,
        "dataset_checksum_semantics_fail_closed",
        dataset.get("archive_expected_bytes_from_current_headers") == 4924029
        and dataset.get("current_provider_sidecar_expected_md5")
        == "0e33842e24a9c977be4e0107933c0723"
        and dataset.get("checksum_semantics")
        == "CURRENT_PROVIDER_SIDECAR_EXPECTATION_ONLY_NOT_A_HISTORICAL_CHECKSUM_CLAIM"
        and dataset.get("archive_sha256") is None
        and dataset.get("archive_sha256_resolution_stage") == "R6-M0_LOCAL_BYTE_REPLAY",
    )
    check(
        checks,
        failures,
        "dataset_rights_and_namespace_guards",
        dataset.get("rights_classification")
        == "CUSTOM_PROVIDER_USAGE_TERMS_NOT_AN_UNRESTRICTED_OPEN_LICENSE"
        and dataset.get("redistribution_authorized_by_this_pipeline") is False
        and dataset.get("recbole_s3_is_provider_authority") is False
        and dataset.get("repository_atomic_blob_is_provider_authority") is False
        and dataset.get("harmonized_v5_namespace_written") is False,
    )
    check(
        checks,
        failures,
        "dataset_transform_exact_no_filter_sort_or_rewrite",
        dataset.get("transformation_id") == "GL-ML100K-U-DATA-TO-RECBOLE-INTER-1.0"
        and dataset.get("expected_data_rows") == 100000
        and dataset.get("expected_user_domain_size") == 943
        and dataset.get("expected_item_domain_size") == 1682
        and dataset.get("row_filtering") is False
        and dataset.get("deduplication") is False
        and dataset.get("sorting") is False
        and dataset.get("id_rewriting_in_atomic_file") is False
        and dataset.get("timestamp_rewriting") is False
        and dataset.get("atomic_directory_exact_final_files") == ["ml-100k.inter"],
    )
    check(
        checks,
        failures,
        "dataset_root_external_non_git_and_absent",
        is_outside_repo_windows(str(dataset.get("non_git_materialization_root", "")))
        and is_outside_repo_windows(str(dataset.get("official_source_attempt_root", "")))
        and not Path(str(dataset.get("official_source_attempt_root"))).exists(),
    )

    env = decision.get("environment_profile", {})
    installer = env.get("python_installer", {})
    interpreter = env.get("interpreter_identity", {})
    check(
        checks,
        failures,
        "environment_external_non_git_immutable_attempt",
        env.get("environment_root_policy") == "EXTERNAL_NON_GIT_IMMUTABLE_ATTEMPT_ROOT"
        and env.get("inside_project_repository") is False
        and env.get("gitignore_dependency") is False
        and is_outside_repo_windows(str(env.get("environment_attempt_root", "")))
        and not Path(str(env.get("environment_attempt_root"))).exists(),
    )
    check(
        checks,
        failures,
        "official_python_3119_installer_identity_frozen",
        installer.get("release_page") == "https://www.python.org/downloads/release/python-3119/"
        and installer.get("installer_url")
        == "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
        and installer.get("sigstore_url")
        == "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe.sigstore"
        and installer.get("official_page_expected_md5")
        == "e8dcd502e34932eebcaf1be056d5cbcd"
        and installer.get("local_sha256") is None
        and installer.get("authenticode_status_required") == "Valid",
    )
    required_install_options = {
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=0",
        "AppendPath=0",
        "AssociateFiles=0",
        "Shortcuts=0",
        "Include_launcher=0",
        "Include_pip=1",
        "Include_test=0",
        "Include_exe=1",
        "Include_lib=1",
    }
    check(
        checks,
        failures,
        "python_install_options_are_local_and_nonambient",
        required_install_options.issubset(set(installer.get("installer_options", [])))
        and installer.get("allowed_exit_codes") == [0]
        and installer.get("official_install_option_evidence", "").startswith(
            "https://docs.python.org/3.11/using/windows.html"
        ),
    )
    check(
        checks,
        failures,
        "exact_interpreter_identity_no_system_reuse",
        interpreter.get("implementation") == "CPython"
        and interpreter.get("version") == "3.11.9"
        and interpreter.get("bitness") == 64
        and interpreter.get("sys_platform") == "win32"
        and interpreter.get("required_binary_tag") == "cp311-cp311-win_amd64"
        and interpreter.get("system_python_3_11_3_reuse_allowed") is False
        and interpreter.get("py_launcher_resolution_used") is False,
    )
    check(
        checks,
        failures,
        "twenty_direct_requirements_exact_and_ordered",
        env.get("direct_requirement_count") == 20
        and env.get("pinned_direct_requirements") == EXPECTED_PINS,
    )
    recbole_source = env.get("recbole_source", {})
    check(
        checks,
        failures,
        "recbole_local_source_exact_no_editable_or_pypi",
        recbole_source.get("revision") == SELECTED_REVISION
        and recbole_source.get("git_tree") == SELECTED_TREE
        and recbole_source.get("installation_source")
        == "HASH_LOCKED_LOCAL_SOURCE_WHEEL_ONLY"
        and recbole_source.get("pypi_recbole_artifact_allowed") is False
        and recbole_source.get("editable_install_allowed") is False
        and recbole_source.get("source_modification_allowed") is False,
    )
    check(
        checks,
        failures,
        "wheel_resolution_remains_materialization_fact",
        env.get("all_third_party_wheels_binary_only") is True
        and env.get("transitive_wheel_hashes_known") is False
        and env.get("transitive_wheel_hashes_resolution_stage")
        == "R6-M1_WHEELHOUSE_REPLAY",
    )

    source_tree = strict_load(
        ROOT
        / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ac/E4_R5M0_source_materialization/source_tree_manifest.json"
    )
    selected_blobs = strict_load(
        ROOT
        / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ac/E4_R5M0_source_materialization/selected_blob_manifest.json"
    )
    tree_candidate = next(
        (row for row in source_tree.get("candidates", []) if row.get("candidate_id") == SELECTED_CANDIDATE),
        {},
    )
    blob_candidate = next(
        (row for row in selected_blobs.get("candidates", []) if row.get("candidate_id") == SELECTED_CANDIDATE),
        {},
    )
    blob_map = {
        row.get("path"): row
        for row in blob_candidate.get("files", [])
        if isinstance(row, dict)
    }
    tree_map = {
        row.get("path"): row
        for row in tree_candidate.get("entries", [])
        if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "source_tree_revision_and_sparse_selection_replayed",
        tree_candidate.get("full_revision") == SELECTED_REVISION
        and tree_candidate.get("git_tree") == SELECTED_TREE
        and tree_candidate.get("selected_tree_entry_count") == blob_candidate.get("file_count") == 265,
    )
    check(
        checks,
        failures,
        "six_source_surfaces_raw_hash_and_git_selection_replayed",
        all(
            path in blob_map
            and blob_map[path].get("sha256_raw_bytes") == expected_hash
            and tree_map.get(path, {}).get("selected_by_sparse_policy") is True
            and tree_map.get(path, {}).get("git_object_id") == blob_map[path].get("git_blob_id")
            for path, expected_hash in EXPECTED_SOURCE_HASHES.items()
        ),
    )
    check(
        checks,
        failures,
        "repository_example_inter_blob_explicitly_not_materialized",
        tree_map.get("recbole/dataset_example/ml-100k/ml-100k.inter", {}).get(
            "selected_by_sparse_policy"
        )
        is False
        and "recbole/dataset_example/ml-100k/ml-100k.inter" not in blob_map,
    )

    source_root = (
        ROOT
        / "research/hybrid-recsys-v5/03_benchmark/stage1e/materialized_sources/r5/recbole_v1_2_1_9a6f63d"
    )
    configurator_text = (source_root / "recbole/config/configurator.py").read_text(
        encoding="utf-8"
    )
    dataset_text = (source_root / "recbole/data/dataset/dataset.py").read_text(
        encoding="utf-8"
    )
    url_text = (source_root / "recbole/properties/dataset/url.yaml").read_text(
        encoding="utf-8"
    )
    check(
        checks,
        failures,
        "configurator_builtin_ml100k_path_override_observed",
        'if self.dataset == "ml-100k":' in configurator_text
        and '"../dataset_example/" + self.dataset' in configurator_text,
    )
    check(
        checks,
        failures,
        "dataset_absence_triggers_downloader_observed",
        "if not os.path.exists(dataset_path):" in dataset_text
        and "self._download()" in dataset_text
        and "download_url(url, self.dataset_path)" in dataset_text,
    )
    check(
        checks,
        failures,
        "recbole_ml100k_s3_mapping_observed_noncanonical",
        "ml-100k:" in url_text and "s3" in url_text.lower(),
    )

    bridge = decision.get("recbole_dataset_bridge", {})
    bridge_evidence = {
        row.get("path"): row.get("raw_sha256")
        for row in bridge.get("source_evidence", [])
        if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "bridge_source_evidence_hashes_exact",
        bridge_evidence.get("recbole/config/configurator.py")
        == EXPECTED_SOURCE_HASHES["recbole/config/configurator.py"]
        and bridge_evidence.get("recbole/data/dataset/dataset.py")
        == EXPECTED_SOURCE_HASHES["recbole/data/dataset/dataset.py"]
        and bridge_evidence.get("recbole/properties/dataset/url.yaml")
        == EXPECTED_SOURCE_HASHES["recbole/properties/dataset/url.yaml"],
    )
    check(
        checks,
        failures,
        "bridge_is_single_file_binary_copy_not_source_patch",
        bridge.get("destination_exact_file_set") == ["ml-100k.inter"]
        and bridge.get("destination_item_or_user_files_allowed") is False
        and bridge.get("source_and_destination_sha256_must_match") is True
        and bridge.get("source_and_destination_byte_count_must_match") is True
        and bridge.get("recbole_source_edit_allowed") is False
        and bridge.get("repository_dataset_blob_used") is False
        and bridge.get("symlink_or_junction_used") is False,
    )
    check(
        checks,
        failures,
        "bridge_config_check_only_loader_and_s3_blocked",
        bridge.get("config_only_resolution_check_authorized") is True
        and bridge.get("dataset_loader_invocation_authorized") is False
        and bridge.get("recbole_s3_network_allowed") is False,
    )

    c1 = decision.get("r6_c1_contract", {})
    check(
        checks,
        failures,
        "r6_c1_model_and_exact_five_outputs",
        c1.get("model_profile")
        == {
            "display_name": "Sol High Fast",
            "runtime_model_id": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "service_tier": "priority",
        }
        and c1.get("exact_output_files") == EXPECTED_C1_OUTPUTS,
    )
    check(
        checks,
        failures,
        "r6_c1_is_proposal_only_no_materialization_write",
        c1.get("proposal_only") is True
        and c1.get("new_source_interpretation_allowed") is False
        and c1.get("commands_executed_by_worker") is False
        and c1.get("external_materialization_writes_allowed_by_worker") is False,
    )
    required_packet_fragments = [
        "ordered argv",
        "write sets",
        "allowlists",
        "cpu, memory, disk",
        "fail-closed",
        "negative assertions",
    ]
    packet_text = " ".join(c1.get("required_packet_properties", [])).lower()
    check(
        checks,
        failures,
        "r6_c1_packet_requirements_complete",
        all(fragment in packet_text for fragment in required_packet_fragments),
    )

    boundary = decision.get("execution_boundary", {})
    check(
        checks,
        failures,
        "persistent_execution_boundary_closed",
        boundary.get("r6_c1_command_assembly_authorized") is True
        and boundary.get("dataset_or_environment_materialization_authorized_by_this_decision_alone")
        is False
        and all(
            boundary.get(key) is False
            for key in [
                "training",
                "evaluation",
                "hyperparameter_search",
                "dataset_loader_invocation",
                "checkpoint_download",
                "project_v5_test_access",
                "benchmark_admission",
                "paper_numeric_claims",
            ]
        ),
    )
    check(
        checks,
        failures,
        "truth_state_remains_not_run",
        truth_is_closed(decision.get("truth_state", {}))
        and truth_is_closed(lane_receipt.get("truth_state", {})),
    )
    scope = manifest.get("scope_assertions", {})
    check(
        checks,
        failures,
        "manifest_scope_assertions_zero_execution",
        scope.get("decision_profile_count") == 2
        and scope.get("dataset_profile_count") == 1
        and scope.get("environment_profile_count") == 1
        and scope.get("selected_candidate_count") == 1
        and scope.get("benchmark_values_used_for_selection") == 0
        and scope.get("materialized_dataset_bytes") == 0
        and scope.get("materialized_environment_packages") == 0
        and scope.get("training_or_evaluation_commands_executed") == 0
        and scope.get("project_v5_test_opened") is False,
    )

    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r6-g0-validation-result-1.0",
        "passed": not failures,
        "verdict": (
            "PASS_R6_G0_FROZEN_31_OF_31_READY_FOR_R6_C1"
            if not failures
            else "FAIL_R6_G0_REWORK_REQUIRED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "mechanical_summary": {
            "checks_passed": sum(1 for value in checks.values() if value),
            "checks_expected": len(checks),
            "frozen_inputs": len(rows),
            "strict_json_inputs": strict_json_count,
            "direct_requirements": len(env.get("pinned_direct_requirements", [])),
            "r6_c1_exact_outputs": len(c1.get("exact_output_files", [])),
            "materialized_dataset_bytes": 0,
            "materialized_environment_packages": 0,
        },
        "diagnostics": {
            "fingerprint_failures": fingerprint_failures,
            "strict_json_failures": strict_json_failures,
        },
        "materialization_authorized_by_validation": False,
        "experiment_execution_authorized": False,
        "truth_state": decision.get("truth_state"),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
