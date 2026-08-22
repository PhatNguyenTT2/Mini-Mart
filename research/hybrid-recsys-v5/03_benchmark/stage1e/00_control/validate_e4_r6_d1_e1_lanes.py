from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[5]
CONTROL = ROOT / "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control"
D1_ROOT = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ag"
    / "E4_R6D1_movielens100k_authority_lineage"
)
E1_ROOT = (
    ROOT
    / "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ah"
    / "E4_R6E1_recbole_environment_closure"
)
SELECTED_CANDIDATE = "R5-CAND-RECBOLE-BPR-ML100K-001"
SELECTED_REVISION = "9a6f63d8d4a5b989fe27955a833f813a6d86041e"
SELECTED_TREE = "08915121fea069a30f7e3e97a72e16e7e76d43c6"
TRUTH = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}
D1_FILES = {
    "provider_authority.json",
    "rights_and_release_record.md",
    "data_lineage_plan.json",
    "materialization_command_proposal.json",
    "audit_handoff.json",
}
E1_FILES = {
    "compatibility_matrix.json",
    "environment_lock_proposal.json",
    "environment_command_proposal.json",
    "risk_report.md",
    "audit_handoff.json",
}
FORBIDDEN_COMMAND_PATTERNS = {
    "run_recbole.py",
    "run_hyper.py",
    "trainer.fit(",
    "trainer.evaluate(",
    "tune.run(",
    "ray.init(",
    "create_dataset(",
    "data_preparation(",
    "objective_function(",
    "project_v5/test",
    "project_v5\\test",
    "harmonized_v5/test",
    "harmonized_v5\\test",
}


class ContractError(ValueError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate key: {key}")
        casefolded = key.casefold()
        if casefolded in folded and folded[casefolded] != key:
            raise ContractError(f"case-colliding keys: {folded[casefolded]} / {key}")
        folded[casefolded] = key
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON is not an object: {path}")
    return value


def canonical_lf(path: Path) -> bytes:
    raw = path.read_bytes()
    raw.decode("utf-8", errors="strict")
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def check(checks: dict[str, bool], failures: list[str], name: str, value: bool) -> None:
    checks[name] = bool(value)
    if not value:
        failures.append(name)


def truth_of(document: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("truth_state", "persistent_truth"):
        value = document.get(key)
        if isinstance(value, dict):
            return value
    return None


def exact_file_set(path: Path) -> set[str]:
    if not path.is_dir():
        return set()
    return {row.name for row in path.iterdir() if row.is_file()}


def output_hash_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        payload = canonical_lf(path)
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "canonical_lf_bytes": len(payload),
                "canonical_lf_sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return rows


def d1_command_text(document: dict[str, Any]) -> str:
    commands = document.get("commands", [])
    pieces: list[str] = []
    for command in commands:
        if not isinstance(command, dict):
            continue
        argv = command.get("argv", [])
        if isinstance(argv, list):
            pieces.append(" ".join(str(value) for value in argv))
    return "\n".join(pieces).casefold()


def e1_command_text(document: dict[str, Any]) -> str:
    pieces: list[str] = []
    for group in document.get("command_groups", []):
        if not isinstance(group, dict):
            continue
        for command in group.get("commands", []):
            if not isinstance(command, dict):
                continue
            pieces.append(str(command.get("executable", "")))
            arguments = command.get("arguments", [])
            if isinstance(arguments, list):
                pieces.append(" ".join(str(value) for value in arguments))
    return "\n".join(pieces).casefold()


def package_map(entries: list[Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in entries:
        if not isinstance(row, dict) or not isinstance(row.get("package_identity"), str):
            continue
        result[row["package_identity"].casefold()] = row
    return result


def pin_map(entries: list[Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in entries:
        if not isinstance(row, dict) or not isinstance(row.get("identity"), str):
            continue
        result[row["identity"].casefold()] = row
    return result


def main() -> int:
    checks: dict[str, bool] = {}
    failures: list[str] = []

    check(checks, failures, "d1_exact_five_file_set", exact_file_set(D1_ROOT) == D1_FILES)
    check(checks, failures, "e1_exact_five_file_set", exact_file_set(E1_ROOT) == E1_FILES)

    json_paths = [
        D1_ROOT / "provider_authority.json",
        D1_ROOT / "data_lineage_plan.json",
        D1_ROOT / "materialization_command_proposal.json",
        D1_ROOT / "audit_handoff.json",
        E1_ROOT / "compatibility_matrix.json",
        E1_ROOT / "environment_lock_proposal.json",
        E1_ROOT / "environment_command_proposal.json",
        E1_ROOT / "audit_handoff.json",
    ]
    documents: dict[str, dict[str, Any]] = {}
    strict_json_count = 0
    for path in json_paths:
        try:
            documents[path.as_posix()] = load_json(path)
            strict_json_count += 1
        except Exception as exc:
            failures.append(f"strict_json:{path.relative_to(ROOT).as_posix()}:{exc}")
    check(checks, failures, "strict_json_8_of_8", strict_json_count == 8)
    if failures:
        result = {
            "schema_version": "stage1e-rebaseline-v2-e4-r6-d1-e1-lanes-validation-result-1.0",
            "passed": False,
            "verdict": "FAIL_R6_D1_E1_REWORK_REQUIRED",
            "failure_count": len(failures),
            "failures": failures,
            "checks": checks,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    provider = documents[(D1_ROOT / "provider_authority.json").as_posix()]
    lineage = documents[(D1_ROOT / "data_lineage_plan.json").as_posix()]
    data_commands = documents[(D1_ROOT / "materialization_command_proposal.json").as_posix()]
    d1_handoff = documents[(D1_ROOT / "audit_handoff.json").as_posix()]
    matrix = documents[(E1_ROOT / "compatibility_matrix.json").as_posix()]
    env_lock = documents[(E1_ROOT / "environment_lock_proposal.json").as_posix()]
    env_commands = documents[(E1_ROOT / "environment_command_proposal.json").as_posix()]
    e1_handoff = documents[(E1_ROOT / "audit_handoff.json").as_posix()]

    s0 = load_json(CONTROL / "rebaseline_v2_e4_r6_s0_gate_receipt.json")
    dispatch = load_json(CONTROL / "rebaseline_v2_e4_r6_d1_e1_dispatch.json")
    check(
        checks,
        failures,
        "entry_gate_and_dispatch_replayed",
        s0.get("passed") is True
        and s0.get("failure_count") == 0
        and s0.get("verdict")
        == "PASS_R6_S0_FROZEN_36_OF_36_READY_FOR_PARALLEL_R6_D1_R6_E1"
        and dispatch.get("expected_stage_count") == 2
        and {row.get("stage_id") for row in dispatch.get("stages", []) if isinstance(row, dict)}
        == {"R6-D1", "R6-E1"},
    )

    d1_profile = d1_handoff.get("actual_model_profile", {})
    e1_profile = e1_handoff.get("actual_model_profile", {})
    expected_profile = {
        "display_name": "Sol XHigh Fast",
        "runtime_model_id": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "service_tier": "priority",
    }
    check(
        checks,
        failures,
        "actual_worker_model_profiles_match",
        d1_profile == expected_profile and e1_profile == expected_profile,
    )
    check(
        checks,
        failures,
        "all_lane_truth_states_unchanged",
        all(
            truth_of(document) == TRUTH
            for document in [lineage, data_commands, d1_handoff, env_lock, env_commands, e1_handoff]
        ),
    )

    authority = provider.get("authority_decision", {})
    distribution = provider.get("canonical_distribution", {})
    checksum = distribution.get("provider_checksum", {})
    check(
        checks,
        failures,
        "d1_group_lens_authority_and_release",
        provider.get("stage_id") == "R6-D1"
        and provider.get("candidate_id") == SELECTED_CANDIDATE
        and authority.get("canonical_provider")
        == "GroupLens Research Project, University of Minnesota"
        and authority.get("canonical_dataset_name") == "MovieLens 100K"
        and authority.get("release_date") == "1998-04"
        and authority.get("exact_record_counts")
        == {"ratings": 100000, "users": 943, "movies": 1682},
    )
    check(
        checks,
        failures,
        "d1_current_provider_archive_checksum_bounded",
        distribution.get("archive_filename") == "ml-100k.zip"
        and distribution.get("final_url")
        == "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
        and distribution.get("provider_content_length_bytes") == 4924029
        and distribution.get("archive_retrieved_in_this_stage") is False
        and distribution.get("archive_sha256") is None
        and checksum.get("algorithm") == "MD5"
        and checksum.get("value") == "0e33842e24a9c977be4e0107933c0723"
        and checksum.get("sidecar_bytes_replayed") is True
        and checksum.get("archive_bytes_checked_against_sidecar_in_this_stage") is False
        and checksum.get("historical_release_checksum_claimed") is False,
    )
    sources = provider.get("sources", [])
    source_ids = [row.get("source_id") for row in sources if isinstance(row, dict)]
    source_urls = [str(row.get("final_url", "")) for row in sources if isinstance(row, dict)]
    check(
        checks,
        failures,
        "d1_seven_unique_official_sources",
        len(sources) == len(source_ids) == len(set(source_ids)) == 7
        and all(url.startswith("https://grouplens.org/") or url.startswith("https://files.grouplens.org/") for url in source_urls),
    )
    rejected = provider.get("noncanonical_source_rejections", [])
    check(
        checks,
        failures,
        "d1_recbole_s3_and_atomic_blobs_noncanonical",
        any("recbole.s3-accelerate.amazonaws.com" in str(row.get("source", "")) for row in rejected if isinstance(row, dict))
        and all(row.get("canonical_provider_authority") is False for row in rejected if isinstance(row, dict)),
    )
    rights_text = (D1_ROOT / "rights_and_release_record.md").read_text(encoding="utf-8").casefold()
    check(
        checks,
        failures,
        "d1_rights_terms_not_open_license",
        all(
            fragment in rights_text
            for fragment in [
                "may not redistribute",
                "commercial or revenue-bearing",
                "acknowledgment",
                "non-endorsement",
                "custom provider usage terms",
                "not as an unrestricted open license",
            ]
        ),
    )

    atomic = lineage.get("normative_raw_to_atomic_transformation", {})
    row_policy = atomic.get("row_policy", {})
    reconciliation = lineage.get("raw_to_atomic_reconciliation_checks", {})
    namespace = lineage.get("namespace_separation", {})
    check(
        checks,
        failures,
        "d1_exact_candidate_revision_and_u_data_transform",
        lineage.get("candidate_id") == SELECTED_CANDIDATE
        and lineage.get("pinned_recbole_revision") == SELECTED_REVISION
        and atomic.get("input")
        == "official_source/grouplens_ml100k/attempt-001/raw/ml-100k/u.data"
        and atomic.get("output")
        == "official_source/grouplens_ml100k/attempt-001/recbole_atomic/ml-100k/ml-100k.inter"
        and row_policy.get("expected_input_rows") == 100000
        and row_policy.get("expected_output_rows_excluding_header") == 100000
        and row_policy.get("drop_rows") is False
        and row_policy.get("deduplicate_rows") is False
        and row_policy.get("sort_rows") is False,
    )
    check(
        checks,
        failures,
        "d1_reconciliation_and_namespace_separation",
        bool(reconciliation)
        and namespace.get("official_source_namespace") != namespace.get("harmonized_v5_namespace")
        and any("No file is copied" in rule for rule in namespace.get("cross_namespace_rules", [])),
    )
    data_command_rows = data_commands.get("commands", [])
    data_text = d1_command_text(data_commands)
    check(
        checks,
        failures,
        "d1_exact_eight_unexecuted_materialization_commands",
        data_commands.get("proposal_only") is True
        and data_commands.get("execution_performed") is False
        and data_commands.get("execution_authorized") is False
        and len(data_command_rows) == 8
        and data_commands.get("command_order")
        == [row.get("command_id") for row in data_command_rows if isinstance(row, dict)],
    )
    check(
        checks,
        failures,
        "d1_command_network_and_no_scientific_execution",
        data_commands.get("network_allowlist", {}).get("exact_urls")
        == [
            "https://files.grouplens.org/datasets/movielens/ml-100k-README.txt",
            "https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5",
            "https://files.grouplens.org/datasets/movielens/ml-100k.zip",
        ]
        and data_commands.get("network_allowlist", {}).get("recbole_s3_allowed") is False
        and not any(pattern in data_text for pattern in FORBIDDEN_COMMAND_PATTERNS),
    )
    d1_negative = data_commands.get("negative_assertions", {})
    check(
        checks,
        failures,
        "d1_negative_assertions_hold",
        d1_negative.get("recbole_entrypoint_invoked") is False
        and d1_negative.get("trainer_invoked") is False
        and d1_negative.get("evaluator_invoked") is False
        and d1_negative.get("hyperparameter_tuning_invoked") is False
        and d1_negative.get("project_v5_test_opened") is False
        and d1_negative.get("benchmark_admitted") is False,
    )
    check(
        checks,
        failures,
        "d1_handoff_pass_fail_closed",
        d1_handoff.get("status") == "COMPLETE_PROPOSAL_ONLY"
        and str(d1_handoff.get("verdict", "")).startswith("PASS_R6_D1_")
        and d1_handoff.get("file_count") == 5
        and d1_handoff.get("fail_closed_gate", {}).get("materialization_authorized_by_this_handoff") is False
        and d1_handoff.get("fail_closed_gate", {}).get("experiment_execution_authorized") is False,
    )

    packages = package_map(matrix.get("entries", []))
    pins = pin_map(env_lock.get("exact_direct_pins", []))
    required_versions = {
        "torch": "2.2.2+cpu",
        "numpy": "1.26.4",
        "scipy": "1.11.4",
        "pandas": "2.1.4",
        "scikit-learn": "1.3.2",
        "pyyaml": "6.0.2",
        "tensorboard": "2.15.2",
        "ray": "2.6.3",
        "thop": "0.1.1.post2207130030",
        "colorlog": "4.7.2",
        "colorama": "0.4.4",
    }
    check(
        checks,
        failures,
        "e1_high_confidence_current_not_historical_profile",
        matrix.get("stage") == "R6-E1"
        and matrix.get("decision") == "HIGH_CONFIDENCE_CURRENT_CPU_PROFILE_PROPOSED"
        and matrix.get("pinned_source", {}).get("candidate_id") == SELECTED_CANDIDATE
        and matrix.get("pinned_source", {}).get("revision") == SELECTED_REVISION
        and matrix.get("pinned_source", {}).get("git_tree") == SELECTED_TREE
        and len(matrix.get("entries", [])) == 23,
    )
    check(
        checks,
        failures,
        "e1_required_compatibility_rows_and_versions",
        all(
            identity in packages and packages[identity].get("proposed_version") == version
            for identity, version in required_versions.items()
        )
        and packages.get("cpython", {}).get("proposed_version") == "3.11.9 (64-bit Windows installer)"
        and packages.get("recbole", {}).get("proposed_version", "").startswith("1.2.1+local.9a6f63d")
        and packages.get("hyperopt", {}).get("role") == "excluded"
        and packages.get("hyperopt", {}).get("lock_included") is False,
    )
    check(
        checks,
        failures,
        "e1_exact_twenty_direct_pins",
        len(env_lock.get("exact_direct_pins", [])) == len(pins) == 20
        and all(identity in pins and pins[identity].get("version") == version for identity, version in required_versions.items())
        and pins.get("recbole", {}).get("source_revision") == SELECTED_REVISION
        and pins.get("recbole", {}).get("source_git_tree") == SELECTED_TREE
        and all(row.get("sha256") is None for row in env_lock.get("exact_direct_pins", []) if isinstance(row, dict)),
    )
    selected_profile = env_lock.get("selected_profile", {})
    check(
        checks,
        failures,
        "e1_cpu_profile_and_interpreter_exact",
        env_lock.get("proposal_status") == "SELECTED_CURRENT_COMPATIBLE_PROFILE_NOT_MATERIALIZED"
        and env_lock.get("execution_performed") is False
        and selected_profile.get("interpreter", {}).get("version") == "3.11.9"
        and selected_profile.get("platform_markers", {}).get("required_binary_tag")
        == "cp311-cp311-win_amd64"
        and selected_profile.get("cpu_policy", {}).get("torch_distribution_version") == "2.2.2+cpu"
        and selected_profile.get("cpu_policy", {}).get("prohibited")
        and env_lock.get("current_host_observation", {}).get("fitness_for_target_profile")
        == "NOT_ACCEPTABLE_AS_IS",
    )
    check(
        checks,
        failures,
        "e1_current_compatible_not_historical_disclaimer",
        env_lock.get("disclaimer", {}).get("current_compatibility_only") is True
        and env_lock.get("disclaimer", {}).get("historical_producer_environment_known") is False
        and env_lock.get("disclaimer", {}).get("readme_number_status")
        == "PROVISIONAL_DOCUMENTATION_ONLY_NOT_PRODUCER_BOUND"
        and "never evidence" in env_lock.get("disclaimer", {}).get("statement", ""),
    )
    env_groups = env_commands.get("command_groups", [])
    env_command_rows = [
        row
        for group in env_groups
        if isinstance(group, dict)
        for row in group.get("commands", [])
        if isinstance(row, dict)
    ]
    env_text = e1_command_text(env_commands)
    check(
        checks,
        failures,
        "e1_exact_twenty_two_unexecuted_commands",
        env_commands.get("proposal_only") is True
        and env_commands.get("execution_performed") is False
        and [group.get("group") for group in env_groups if isinstance(group, dict)]
        == [
            "preflight",
            "central_environment_creation",
            "package_resolution_and_download",
            "offline_install_and_local_source_build",
            "frozen_inventory_and_bounded_checks",
        ]
        and len(env_command_rows) == 22,
    )
    allow_hosts = {
        row.get("host")
        for row in env_commands.get("official_package_host_allowlist", [])
        if isinstance(row, dict)
    }
    check(
        checks,
        failures,
        "e1_official_host_allowlist_and_no_scientific_commands",
        allow_hosts
        == {
            "www.python.org",
            "pypi.org",
            "files.pythonhosted.org",
            "download.pytorch.org",
            "download-r2.pytorch.org",
        }
        and not any(pattern in env_text for pattern in FORBIDDEN_COMMAND_PATTERNS),
    )
    env_negative = env_commands.get("negative_assertions", {})
    check(
        checks,
        failures,
        "e1_negative_assertions_hold",
        all(
            env_negative.get(key) is True
            for key in [
                "no_recbole_train_command",
                "no_recbole_evaluate_command",
                "no_project_test_command",
                "no_preprocess_command",
                "no_checkpoint_command",
                "no_tuning_command",
                "no_vendor_entrypoint_command",
                "no_dataset_open_or_download_command",
            ]
        ),
    )
    check(
        checks,
        failures,
        "e1_handoff_proposal_only",
        e1_handoff.get("verdict") == "HIGH_CONFIDENCE_CURRENT_CPU_PROFILE_PROPOSED"
        and e1_handoff.get("selected_environment_profile", {}).get("runtime_verified") is False
        and e1_handoff.get("selected_environment_profile", {}).get("historical_producer_profile") is False
        and e1_handoff.get("handoff_conditions", {}).get("environment_materialization_allowed_by_this_artifact") is False,
    )

    check(
        checks,
        failures,
        "cross_lane_candidate_revision_coherent",
        lineage.get("candidate_id") == matrix.get("pinned_source", {}).get("candidate_id") == SELECTED_CANDIDATE
        and lineage.get("pinned_recbole_revision")
        == matrix.get("pinned_source", {}).get("revision")
        == SELECTED_REVISION,
    )
    check(
        checks,
        failures,
        "cross_lane_data_download_not_hidden_in_environment",
        env_negative.get("no_dataset_open_or_download_command") is True
        and "recbole.s3-accelerate.amazonaws.com" not in env_text
        and "ml-100k.zip" not in env_text,
    )
    check(
        checks,
        failures,
        "cross_lane_r6_g0_and_c1_still_required",
        d1_handoff.get("fail_closed_gate", {}).get("next_allowed_stage", "").startswith("R6-G0_")
        and e1_handoff.get("handoff_conditions", {}).get("required_next_authority", "").startswith(
            "A separate central R6"
        ),
    )

    all_output_paths = [D1_ROOT / name for name in D1_FILES] + [E1_ROOT / name for name in E1_FILES]
    output_rows = output_hash_rows(all_output_paths)
    check(checks, failures, "output_hash_rows_10_of_10", len(output_rows) == 10)

    passed = not failures
    result = {
        "schema_version": "stage1e-rebaseline-v2-e4-r6-d1-e1-lanes-validation-result-1.0",
        "passed": passed,
        "verdict": (
            "PASS_R6_D1_E1_READY_FOR_R6_G0_FREEZE"
            if passed
            else "FAIL_R6_D1_E1_REWORK_REQUIRED"
        ),
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "mechanical_summary": {
            "exact_output_files": 10,
            "strict_json_outputs": strict_json_count,
            "d1_official_sources": len(sources),
            "e1_compatibility_rows": len(matrix.get("entries", [])),
            "e1_direct_pins": len(env_lock.get("exact_direct_pins", [])),
            "proposed_command_arrays": len(data_command_rows) + len(env_command_rows),
        },
        "outputs": output_rows,
        "central_reconciliation_required_before_r6_c1": [
            "Freeze an explicit CPython 3.11.9 acquisition/identity route because the current host is 3.11.3.",
            "Freeze a Git-ignore or non-Git policy for the environment materialization root.",
            "Assemble an explicit data_path/config seam that consumes only the GroupLens-derived atomic directory and disables RecBole S3 fallback.",
            "Carry the provider MD5 as a current sidecar expectation and require local archive MD5 plus SHA-256 replay; do not label it historical.",
        ],
        "materialization_authorized_by_validation": False,
        "experiment_execution_authorized": False,
        "truth_state": TRUTH,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
