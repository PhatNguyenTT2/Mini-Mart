#!/usr/bin/env python3
"""Read-only validator for the E4-R6-PC2W current-host WSL2 preflight."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


CONTROL = Path(__file__).resolve().parent
REPO = CONTROL.parents[4]
CONTRACT = CONTROL / "e4_r6_pc2w_current_host_wsl2_linux_admission_contract.md"
RECEIPT = CONTROL / "rebaseline_v2_e4_r6_pc2w_read_only_preflight_receipt.json"
P1 = CONTROL / "e4_r6_pc2w_p1_docker_query_preflight_requirements.json"
STATE = CONTROL / "pipeline_state_stage1e.json"
PC1 = CONTROL / "rebaseline_v2_e4_r6_pc1_alternative_containment_admission_receipt.json"
PC2_CHANGED = CONTROL / "e4_r6_pc2_changed_host_preflight_requirements.json"


class DuplicateKeyError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key: {key}")
        folded_key = key.casefold()
        if folded_key in folded:
            raise DuplicateKeyError(
                f"case-colliding keys: {folded[folded_key]} and {key}"
            )
        result[key] = value
        folded[folded_key] = key
    return result


def load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    value = json.loads(text, object_pairs_hook=strict_object)
    if not isinstance(value, dict):
        raise ValueError(f"root is not an object: {path}")
    return value


def canonical_lf(path: Path) -> tuple[int, str]:
    text = path.read_bytes().decode("utf-8", errors="strict").replace("\r\n", "\n")
    data = text.encode("utf-8")
    return len(data), hashlib.sha256(data).hexdigest()


checks: list[dict[str, Any]] = []


def check(name: str, condition: bool, observed: Any = None) -> None:
    checks.append({"name": name, "pass": bool(condition), "observed": observed})


def passport_checks(prefix: str, value: dict[str, Any]) -> None:
    required = {
        "origin_skill",
        "origin_mode",
        "origin_date",
        "verification_status",
        "version_label",
        "repro_lock",
        "experiment_intake_declaration",
    }
    check(f"{prefix}.passport_required_fields", required <= set(value), sorted(value))
    check(f"{prefix}.origin_skill", value.get("origin_skill") == "experiment-agent", value.get("origin_skill"))
    check(f"{prefix}.origin_mode", value.get("origin_mode") == "plan", value.get("origin_mode"))
    check(f"{prefix}.verification_status", value.get("verification_status") == "UNVERIFIED", value.get("verification_status"))
    check(f"{prefix}.repro_lock_honest_opt_out", "repro_lock" in value and value.get("repro_lock") is None, value.get("repro_lock"))
    intake = value.get("experiment_intake_declaration", {})
    check(f"{prefix}.no_experiment_declared", intake.get("status") == "no_experiments_declared", intake)
    check(f"{prefix}.scholar_declaration", intake.get("declared_by") == "scholar", intake.get("declared_by"))


try:
    receipt = load_json(RECEIPT)
    p1 = load_json(P1)
    state = load_json(STATE)
    pc1 = load_json(PC1)
    pc2_changed = load_json(PC2_CHANGED)
    contract_text = CONTRACT.read_text(encoding="utf-8")
except Exception as exc:
    print(json.dumps({"verdict": "FAIL", "error": str(exc)}, indent=2))
    sys.exit(1)

check("receipt_schema", receipt.get("schema_version") == "stage1e-e4-r6-pc2w-current-host-read-only-preflight-receipt-1.0", receipt.get("schema_version"))
check("receipt_stage", receipt.get("stage_id") == "E4-R6-PC2W", receipt.get("stage_id"))
check("p1_schema", p1.get("schema_version") == "stage1e-e4-r6-pc2w-p1-docker-query-preflight-requirements-1.0", p1.get("schema_version"))
check("p1_stage", p1.get("stage_id") == "E4-R6-PC2W-P1", p1.get("stage_id"))
passport_checks("receipt", receipt.get("material_passport", {}))
passport_checks("p1", p1.get("material_passport", {}))

contract_bytes, contract_hash = canonical_lf(CONTRACT)
check("contract_bytes", receipt["contract"].get("canonical_lf_bytes") == contract_bytes, contract_bytes)
check("contract_hash", receipt["contract"].get("canonical_lf_sha256") == contract_hash, contract_hash)

expected_upstream = {
    str(PC1.relative_to(REPO)).replace("\\", "/"): canonical_lf(PC1),
    str(PC2_CHANGED.relative_to(REPO)).replace("\\", "/"): canonical_lf(PC2_CHANGED),
}
observed_upstream = {
    row["path"]: (row["canonical_lf_bytes"], row["canonical_lf_sha256"])
    for row in receipt.get("upstream_evidence", [])
}
check("upstream_exact_set", set(observed_upstream) == set(expected_upstream), sorted(observed_upstream))
for path, expected in expected_upstream.items():
    check(f"upstream_hash:{path}", observed_upstream.get(path) == expected, observed_upstream.get(path))

candidate = "DOCKER_DESKTOP_WSL2_LINUX_CONTAINER_FOR_TRUSTED_PINNED_RESEARCH_CODE"
disposition = "CONDITIONAL_CURRENT_HOST_WSL2_DOCKER_LINUX_LANE_DISCOVERED_QUERY_ONLY_BACKEND_PROBE_REQUIRED"
check("candidate_binding", receipt.get("candidate") == candidate == p1.get("candidate"), [receipt.get("candidate"), p1.get("candidate")])
check("entry_disposition", receipt.get("disposition") == disposition == p1.get("entry_verdict"), [receipt.get("disposition"), p1.get("entry_verdict")])
check("trusted_source_threat_model", receipt.get("threat_model", {}).get("scope") == "TRUSTED_PINNED_RESEARCH_CODE", receipt.get("threat_model"))
check("no_hostile_boundary_claim", receipt.get("threat_model", {}).get("hostile_workload_boundary_claimed") is False, receipt.get("threat_model"))
check("no_hyperv_equivalence_claim", receipt.get("threat_model", {}).get("hyperv_isolated_equivalence_claimed") is False, receipt.get("threat_model"))

host = receipt.get("host", {})
check("home_edition_retained", host.get("edition_id") == "CoreSingleLanguage", host.get("edition_id"))
check("cim_os_identity", host.get("cim_os_caption") == "Microsoft Windows 11 Home Single Language", host.get("cim_os_caption"))
check("host_64_bit", host.get("architecture") == "64-bit", host.get("architecture"))
check("hypervisor_observed", host.get("hypervisor_present") is True, host.get("hypervisor_present"))
check("virtualization_observed", host.get("virtualization_firmware_enabled") is True, host.get("virtualization_firmware_enabled"))
check("slat_ambiguity_preserved", "AMBIGUITY" in host.get("virtualization_interpretation", ""), host.get("virtualization_interpretation"))

wsl = receipt.get("wsl", {})
check("wsl_version", wsl.get("version") == "2.6.1.0", wsl.get("version"))
check("wsl_kernel", wsl.get("kernel_version") == "6.6.87.2-1", wsl.get("kernel_version"))
check("default_wsl2", wsl.get("default_version") == 2, wsl.get("default_version"))
check("docker_desktop_only_distro", [row.get("name") for row in wsl.get("distributions", [])] == ["docker-desktop"], wsl.get("distributions"))
check("no_user_distro", wsl.get("user_linux_distribution_present") is False, wsl.get("user_linux_distribution_present"))

docker = receipt.get("docker", {})
check("docker_version", docker.get("desktop_version") == "4.78.0.229452", docker.get("desktop_version"))
check("docker_executable_hash", docker.get("desktop_executable_sha256") == "5b8ab7161b88c45bd4b036e9988349356c18cf5409adb77fdfb8c73b279d8fce", docker.get("desktop_executable_sha256"))
check("desktop_linux_context", docker.get("context_name") == "desktop-linux", docker.get("context_name"))
check("linux_engine_pipe", docker.get("context_endpoint") == "npipe:////./pipe/dockerDesktopLinuxEngine", docker.get("context_endpoint"))
check("backend_stopped", docker.get("desktop_running") is False and docker.get("daemon_endpoint_available") is False, docker)
check("docker_users_membership", docker.get("docker_users_member") is True, docker.get("docker_users_member"))

storage = receipt.get("storage", {})
check("c_disk_threshold", storage.get("c_free_bytes", 0) >= storage.get("c_pre_image_threshold_bytes", 1), storage)
check("e_disk_threshold", storage.get("e_free_bytes", 0) >= storage.get("e_pre_materialization_threshold_bytes", 1), storage)

check("official_source_count", len(receipt.get("official_sources", [])) == 8, len(receipt.get("official_sources", [])))
check("blockers_visible", len(receipt.get("ambiguities_and_blockers", [])) >= 8, len(receipt.get("ambiguities_and_blockers", [])))

for prefix, auth in (("receipt", receipt.get("authorization_state", {})), ("p1", p1.get("authorization_state", {}))):
    true_keys = sorted(key for key, value in auth.items() if value is True)
    check(f"{prefix}_all_authorizations_false", not true_keys, true_keys)

truth = {
    "result_status": receipt.get("result_status"),
    "test_set_opened": receipt.get("test_set_opened"),
    "accepted_result_rows": receipt.get("accepted_result_rows"),
}
check("receipt_truth_state", truth == {"result_status": "NOT_RUN", "test_set_opened": "NO", "accepted_result_rows": 0}, truth)
check("p1_truth_state", p1.get("truth_state") == {"RESULT_STATUS": "NOT_RUN", "TEST_SET_OPENED": "NO", "ACCEPTED_RESULT_ROWS": 0}, p1.get("truth_state"))
check("no_scientific_execution", receipt.get("scientific_execution_performed") is False, receipt.get("scientific_execution_performed"))
check("no_backend_start", receipt.get("backend_start_performed") is False, receipt.get("backend_start_performed"))
check("no_container_or_image_mutation", receipt.get("container_or_image_mutation_performed") is False, receipt.get("container_or_image_mutation_performed"))

pc2w = state.get("rebaseline_v2", {}).get("e4_r5_reproduction_path", {}).get("r6", {}).get("pc2w")
if pc2w is None:
    # The historical state nests R5/R6 under e4_r5 in older schema revisions.
    def find_pc2w(value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            if "pc2w" in value and isinstance(value["pc2w"], dict):
                return value["pc2w"]
            for child in value.values():
                found = find_pc2w(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = find_pc2w(child)
                if found is not None:
                    return found
        return None
    pc2w = find_pc2w(state)

check("pipeline_pc2w_present", isinstance(pc2w, dict), pc2w)
if isinstance(pc2w, dict):
    check("pipeline_pc2w_status", pc2w.get("status") == disposition, pc2w.get("status"))
    check("pipeline_no_hostile_claim", pc2w.get("hostile_workload_boundary_claimed") is False, pc2w.get("hostile_workload_boundary_claimed"))
    check("pipeline_pc1_preserved", pc2w.get("pc1_windows_backend_rejections_preserved") is True, pc2w.get("pc1_windows_backend_rejections_preserved"))
    check("pipeline_result_not_run", pc2w.get("result_status") == "NOT_RUN", pc2w.get("result_status"))
    check("pipeline_test_sealed", pc2w.get("test_set_opened") == "NO", pc2w.get("test_set_opened"))
    check("pipeline_zero_rows", pc2w.get("accepted_result_rows") == 0, pc2w.get("accepted_result_rows"))
    check("pipeline_all_authorizations_false", not [k for k, v in pc2w.get("authorization_state", {}).items() if v is True], pc2w.get("authorization_state"))

check("contract_truth_lock", all(token in contract_text for token in ("RESULT_STATUS=NOT_RUN", "TEST_SET_OPENED=NO", "ACCEPTED_RESULT_ROWS=0")), None)
check("contract_fast_prohibited", "Fast/Priority profiles are prohibited" in contract_text, None)
check("contract_linux_packet_required", "R6-C1R3-LINUX" in contract_text, None)
check("contract_no_network_controls", "--network none" in contract_text and "--pull=never" in contract_text, None)

failures = [row for row in checks if not row["pass"]]
verdict = "PASS_PC2W_READ_ONLY_PREFLIGHT_CONDITIONAL_P1_AUTHORIZATION_REQUIRED" if not failures else "FAIL"
print(
    json.dumps(
        {
            "verdict": verdict,
            "checks": f"{len(checks) - len(failures)}/{len(checks)}",
            "failure_count": len(failures),
            "failures": failures,
        },
        indent=2,
        ensure_ascii=False,
    )
)
sys.exit(1 if failures else 0)
