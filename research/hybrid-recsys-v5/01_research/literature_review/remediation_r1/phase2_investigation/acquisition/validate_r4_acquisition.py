#!/usr/bin/env python3
"""Fail-closed validator for the Stage 1B R1/R4 acquisition bundle."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_INPUT_MANIFEST_SHA256 = "56cac16b697d6bde6878e1274bef397face00ec5697b8291a4d8e5ed13627aeb"
EXPECTED_R3_HANDOFF_SHA256 = "caaaa51b1cfda308bac8603287b41dc5e3ae42f6aa3eb6bfe7f9cf623712c888"
FIXED_NONSELF_OUTPUTS = (
    "source_acquisition_manifest.json",
    "locator_registry.json",
    "r4_claim_acquisition_map.json",
    "rights_access_registry.json",
    "r4_acquisition_report.md",
)


def workspace_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("workspace root not found")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_receipt(path: Path, workspace: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(workspace).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def count_field(obj: Any, names: set[str]) -> int:
    if isinstance(obj, dict):
        return sum((1 if key in names else 0) + count_field(value, names) for key, value in obj.items())
    if isinstance(obj, list):
        return sum(count_field(value, names) for value in obj)
    return 0


def input_gate(acq: Path, workspace: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = acq.parents[1]
    control = root / "00_control"
    integration = root / "phase2_investigation" / "integration"
    failures: list[dict[str, Any]] = []
    manifest_path = control / "r4_input_manifest.json"
    actual_manifest_hash = sha256(manifest_path)
    if actual_manifest_hash != EXPECTED_INPUT_MANIFEST_SHA256:
        failures.append({"check": "input_manifest_sha256", "expected": EXPECTED_INPUT_MANIFEST_SHA256, "actual": actual_manifest_hash})
    manifest = load_json(manifest_path)

    contract_row = manifest["r4_contract"]
    contract_path = workspace / contract_row["path"]
    contract_actual = file_receipt(contract_path, workspace)
    if contract_actual["bytes"] != contract_row["bytes"] or contract_actual["sha256"] != contract_row["sha256"]:
        failures.append({"check": "contract_bytes_hash", "expected": contract_row, "actual": contract_actual})

    frozen_checked = 0
    for row in manifest["integration_files"]:
        path = integration / row["path"]
        actual = file_receipt(path, workspace)
        frozen_checked += 1
        if actual["bytes"] != row["bytes"] or actual["sha256"] != row["sha256"]:
            failures.append({"check": "frozen_r3_bytes_hash", "expected": row, "actual": actual})

    handoff_path = integration / "r3_handoff.json"
    handoff_hash = sha256(handoff_path)
    handoff = load_json(handoff_path)
    if handoff_hash != EXPECTED_R3_HANDOFF_SHA256:
        failures.append({"check": "r3_handoff_sha256", "expected": EXPECTED_R3_HANDOFF_SHA256, "actual": handoff_hash})
    if handoff.get("verdict") != "PASS":
        failures.append({"check": "r3_verdict", "actual": handoff.get("verdict")})
    audit = handoff.get("independent_audit", {})
    if not (audit.get("result") == "PASS" and audit.get("checks_passed") == 20 and audit.get("checks_failed") == 0):
        failures.append({"check": "r3_independent_audit", "actual": audit})

    sources = load_json(integration / "source_registry_r1.json")["sources"]
    resources = load_json(integration / "operational_resource_registry.json")["resources"]
    artifact_failures: list[dict[str, Any]] = []
    scholarly_checked = 0
    operational_checked = 0
    for kind, rows, key_name in (
        ("scholarly", sources, "source_key"),
        ("operational", resources, "resource_key"),
    ):
        for row in rows:
            if not row.get("source_acquired"):
                continue
            if kind == "scholarly":
                scholarly_checked += 1
            else:
                operational_checked += 1
            rel = row.get("acquired_artifact")
            path = workspace / rel if rel else None
            if path is None or not path.is_file():
                artifact_failures.append({"kind": kind, "key": row[key_name], "path": rel, "error": "missing"})
            elif sha256(path) != row.get("acquired_artifact_sha256"):
                artifact_failures.append({"kind": kind, "key": row[key_name], "path": rel, "error": "hash_mismatch"})
    if artifact_failures:
        failures.append({"check": "transitive_r3_artifacts", "failures": artifact_failures})
    if scholarly_checked + operational_checked != 64:
        failures.append({"check": "transitive_r3_artifact_count", "expected": 64, "actual": scholarly_checked + operational_checked})

    core_scholarly = sum(row.get("record_type") == "scholarly_work" and row.get("core_shortlist") is True for row in sources)
    core_operational = len({row["source_family_id"] for row in resources if row.get("core_operational_family") is True})
    if (core_scholarly, core_operational) != (23, 1):
        failures.append({"check": "r3_core_population", "expected": [23, 1], "actual": [core_scholarly, core_operational]})
    if len(manifest.get("r4_queue", [])) != 13:
        failures.append({"check": "frozen_queue_count", "expected": 13, "actual": len(manifest.get("r4_queue", []))})

    receipt = {
        "input_manifest": file_receipt(manifest_path, workspace),
        "contract": contract_actual,
        "frozen_r3_files_checked": frozen_checked,
        "r3_handoff_sha256": handoff_hash,
        "r3_verdict": handoff.get("verdict"),
        "r3_independent_audit": f"{audit.get('checks_passed', 0)}/20 PASS" if audit.get("result") == "PASS" else "FAIL",
        "transitive_artifacts_revalidated": scholarly_checked + operational_checked,
        "transitive_artifact_failures": len(artifact_failures),
        "core_population_recomputed": {"scholarly": core_scholarly, "operational_families": core_operational, "total": core_scholarly + core_operational},
        "frozen_queue_targets": len(manifest.get("r4_queue", [])),
        "result": "PASS" if not failures else "FAIL",
    }
    return receipt, failures


def validate_bundle(acq: Path, require_handoff: bool = True) -> dict[str, Any]:
    workspace = workspace_root(acq)
    failures: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any) -> None:
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            failures.append({"check": name, "detail": detail})

    gate_receipt, gate_failures = input_gate(acq, workspace)
    check("fail_closed_input_gate", not gate_failures, {"receipt": gate_receipt, "failures": gate_failures})

    required = list(FIXED_NONSELF_OUTPUTS)
    if require_handoff:
        required.append("r4_handoff.json")
    missing = [name for name in required if not (acq / name).is_file()]
    check("required_output_files_exist", not missing, {"missing": missing})
    if missing:
        return {"result": "FAIL", "checks": checks, "failures": failures}

    json_names = [name for name in required if name.endswith(".json")]
    parsed: dict[str, Any] = {}
    parse_failures: list[dict[str, str]] = []
    for name in json_names:
        try:
            parsed[name] = load_json(acq / name)
        except Exception as exc:  # pragma: no cover - validation failure path
            parse_failures.append({"path": name, "error": str(exc)})
    check("all_required_json_parses", not parse_failures, {"parsed": len(parsed), "failures": parse_failures})
    if parse_failures:
        return {"result": "FAIL", "checks": checks, "failures": failures}

    source_manifest = parsed["source_acquisition_manifest.json"]
    locator_registry = parsed["locator_registry.json"]
    claim_map = parsed["r4_claim_acquisition_map.json"]
    rights_registry = parsed["rights_access_registry.json"]

    integration = acq.parent / "integration"
    source_keys = {row["source_key"] for row in load_json(integration / "source_registry_r1.json")["sources"]}
    resource_keys = {row["resource_key"] for row in load_json(integration / "operational_resource_registry.json")["resources"]}
    family_ids = {row["source_family_id"] for row in load_json(integration / "source_family_map_r1.json")["families"]}
    claim_ids = {row["claim_id"] for row in load_json(integration / "r3_handoff.json")["claim_dispositions"]}

    acquisitions = source_manifest["acquisitions"]
    acquisition_keys = [row["acquisition_key"] for row in acquisitions]
    duplicate_acquisition_keys = len(acquisition_keys) - len(set(acquisition_keys))
    check("duplicate_acquisition_keys_zero", duplicate_acquisition_keys == 0, {"duplicates": duplicate_acquisition_keys})

    locators = locator_registry["locators"]
    locator_ids = [row["locator_id"] for row in locators]
    duplicate_locator_ids = len(locator_ids) - len(set(locator_ids))
    check("duplicate_locator_ids_zero", duplicate_locator_ids == 0, {"duplicates": duplicate_locator_ids})

    dangling: list[dict[str, str]] = []
    for row in acquisitions:
        if row.get("source_key") and row["source_key"] not in source_keys:
            dangling.append({"kind": "source", "key": row["source_key"]})
        if row.get("source_family_id") not in family_ids:
            dangling.append({"kind": "family", "key": row.get("source_family_id")})
        for key in row.get("resource_keys", []):
            if key not in resource_keys:
                dangling.append({"kind": "resource", "key": key})
        for key in row.get("supported_claim_ids", []):
            if key not in claim_ids:
                dangling.append({"kind": "claim", "key": key})
    for row in locators:
        if row.get("source_key") and row["source_key"] not in source_keys:
            dangling.append({"kind": "locator_source", "key": row["source_key"]})
        if row.get("resource_key") and row["resource_key"] not in resource_keys:
            dangling.append({"kind": "locator_resource", "key": row["resource_key"]})
        if row.get("source_family_id") and row["source_family_id"] not in family_ids:
            dangling.append({"kind": "locator_family", "key": row["source_family_id"]})
        for key in row.get("claim_ids", []):
            if key not in claim_ids:
                dangling.append({"kind": "locator_claim", "key": key})
    for row in claim_map["claims"]:
        for key in row.get("canonical_source_keys", []):
            if key not in source_keys:
                dangling.append({"kind": "claim_source", "key": key})
        for key in row.get("operational_resource_keys", []):
            if key not in resource_keys:
                dangling.append({"kind": "claim_resource", "key": key})
        for key in row.get("source_family_ids", []):
            if key not in family_ids:
                dangling.append({"kind": "claim_family", "key": key})
        for key in row.get("locator_ids", []):
            if key not in set(locator_ids):
                dangling.append({"kind": "claim_locator", "key": key})
    check("dangling_references_zero", not dangling, {"count": len(dangling), "items": dangling})

    artifact_failures: list[dict[str, Any]] = []
    artifact_paths: list[str] = []
    for row in acquisitions:
        for artifact in row.get("local_artifacts", []):
            artifact_paths.append(artifact["path"])
            path = workspace / artifact["path"]
            if not path.is_file():
                artifact_failures.append({"path": artifact["path"], "error": "missing"})
            elif path.stat().st_size != artifact["bytes"] or sha256(path) != artifact["sha256"]:
                artifact_failures.append({"path": artifact["path"], "error": "bytes_or_hash_mismatch"})
    source_artifact_files = sorted(path.relative_to(workspace).as_posix() for path in (acq / "source_artifacts").iterdir() if path.is_file())
    unbound_artifacts = sorted(set(source_artifact_files) - set(artifact_paths))
    duplicate_artifact_bindings = len(artifact_paths) - len(set(artifact_paths))
    check("artifact_bytes_and_hashes_match", not artifact_failures, {"checked": len(artifact_paths), "failures": artifact_failures})
    check("all_local_artifacts_bound_once", not unbound_artifacts and duplicate_artifact_bindings == 0, {"unbound": unbound_artifacts, "duplicate_bindings": duplicate_artifact_bindings})

    sidecar_failures: list[dict[str, Any]] = []
    sidecar_paths: set[str] = set()
    preflight_counts: Counter[str] = Counter()
    for row in locator_registry.get("pdf_preflight_manifest", []):
        sidecar_paths.add(row["sidecar_path"])
        sidecar = workspace / row["sidecar_path"]
        pdf = workspace / row["pdf_path"]
        if not sidecar.is_file() or not pdf.is_file():
            sidecar_failures.append({"sidecar": row["sidecar_path"], "error": "missing_sidecar_or_pdf"})
            continue
        actual = load_json(sidecar)
        preflight_counts[actual.get("verdict", "MISSING")] += 1
        if sha256(sidecar) != row["sidecar_sha256"] or sidecar.stat().st_size != row["sidecar_bytes"]:
            sidecar_failures.append({"sidecar": row["sidecar_path"], "error": "sidecar_bytes_or_hash_mismatch"})
        if sha256(pdf) != row["pdf_sha256"] or actual.get("sha256") != row["pdf_sha256"]:
            sidecar_failures.append({"sidecar": row["sidecar_path"], "error": "pdf_hash_binding_mismatch"})
    actual_sidecars = {path.relative_to(workspace).as_posix() for path in (acq / "pdf_preflight").iterdir() if path.is_file()}
    check("pdf_preflight_sidecars_valid", not sidecar_failures and actual_sidecars == sidecar_paths, {"counts": dict(preflight_counts), "failures": sidecar_failures, "unbound": sorted(actual_sidecars - sidecar_paths)})

    page_pattern = re.compile(r"(?i)(\bpage\b|\bpages\b|\bpp\.?\s*\d|page_range)")
    page_locators = [row for row in locators if row.get("page_anchor") is True or row.get("locator_type") in {"page", "page_range"}]
    prohibited_text_locators = [row["locator_id"] for row in locators if page_pattern.search(row.get("locator_value", ""))]
    page_without_pass = [row["locator_id"] for row in page_locators if (row.get("pdf_preflight") or {}).get("verdict") != "PASS"]
    check("prohibited_page_anchors_zero", not page_locators and not prohibited_text_locators and not page_without_pass, {"page_anchors": len(page_locators), "textual_page_anchors": prohibited_text_locators, "without_pass": page_without_pass})

    core_scholarly = [row for row in acquisitions if row.get("record_type") == "scholarly_work" and row.get("core_object") is True]
    core_operational = [row for row in acquisitions if row.get("record_type") == "operational_family" and row.get("core_object") is True]
    core_satisfied = [row for row in core_scholarly + core_operational if row.get("r4_contract_satisfied") is True]
    check("core_population_and_outcomes_recomputed", len(core_scholarly) == 23 and len(core_operational) == 1 and len(core_satisfied) == 24, {"scholarly": len(core_scholarly), "operational_families": len(core_operational), "satisfied": len(core_satisfied)})

    queue = source_manifest["queue_dispositions"]
    queue_ids = [row["queue_target_id"] for row in queue]
    terminal = [row for row in queue if row.get("terminal") is True and row.get("status") == "resolved"]
    check("queue_terminal_dispositions_recomputed", len(queue) == 13 and len(set(queue_ids)) == 13 and len(terminal) == 13, {"total": len(queue), "unique": len(set(queue_ids)), "terminal_resolved": len(terminal), "dispositions": dict(Counter(row.get("terminal_disposition") for row in queue))})

    claims = claim_map["claims"]
    central_counts = Counter(row.get("central_disposition") for row in claims)
    production_ready = sum(row.get("production_ready") is True for row in claims)
    conditional = [row for row in claims if row.get("central_disposition") == "conditional_production_candidate"]
    conditional_satisfied = [row for row in conditional if row.get("acquisition_satisfied") is True and row.get("original_content_satisfied") is True and row.get("locator_satisfied") is True]
    claim_exclusive = all(row.get("central_disposition") in {"conditional_production_candidate", "planning_only"} and row.get("production_ready") is False for row in claims)
    check("claim_population_and_exclusive_dispositions", len(claims) == 44 and len({row["claim_id"] for row in claims}) == 44 and central_counts == Counter({"conditional_production_candidate": 22, "planning_only": 22}) and claim_exclusive, {"total": len(claims), "central_counts": dict(central_counts), "exclusive": claim_exclusive})
    check("conditional_claim_prerequisites", len(conditional_satisfied) == 22, {"conditional": len(conditional), "satisfied": len(conditional_satisfied)})
    check("production_ready_zero", production_ready == 0, {"production_ready": production_ready})

    complete = rights_registry["operational_families"][0]
    required_layers = {"provider_availability", "provider_access", "package_code_license", "paper_license", "dataset_rights", "execution_access", "redistribution_permission"}
    rights_conflation = 0
    if set(complete.get("rights_layers", {})) != required_layers:
        rights_conflation += 1
    if complete.get("license_scope_assertion") != "Package CC0 is not propagated to upstream Complete Journey data.":
        rights_conflation += 1
    if complete.get("rights_layers", {}).get("dataset_rights", {}).get("status") == "CC0":
        rights_conflation += 1
    check("rights_layer_conflations_zero", rights_conflation == 0, {"conflations": rights_conflation, "layers": sorted(complete.get("rights_layers", {}))})

    prohibited_fields = sum(count_field(parsed[name], {"human_read_source", "human_read_at"}) for name in parsed)
    check("prohibited_human_read_fields_zero", prohibited_fields == 0, {"count": prohibited_fields})

    phase_boundary = source_manifest.get("phase_boundary", {})
    expected_phase = {"r5": "NOT_PERFORMED", "phase3_synthesis": "NOT_PERFORMED", "h1_h4": "NOT_RUN", "stage2_production_citations": "NOT_AUTHORIZED"}
    check("phase_boundary_intact", phase_boundary == expected_phase, {"actual": phase_boundary, "expected": expected_phase})

    if require_handoff:
        handoff = parsed["r4_handoff.json"]
        expected_outputs = {row["path"]: row for row in handoff.get("output_manifest", [])}
        output_failures: list[dict[str, Any]] = []
        for name in FIXED_NONSELF_OUTPUTS:
            path = acq / name
            rel = path.relative_to(workspace).as_posix()
            expected = expected_outputs.get(rel)
            actual = file_receipt(path, workspace)
            if expected is None or expected.get("bytes") != actual["bytes"] or expected.get("sha256") != actual["sha256"]:
                output_failures.append({"path": rel, "expected": expected, "actual": actual})
        check("all_nonself_output_hashes_match", not output_failures and len(expected_outputs) == len(FIXED_NONSELF_OUTPUTS), {"checked": len(FIXED_NONSELF_OUTPUTS), "failures": output_failures})
        handoff_artifacts = {row["path"]: row for row in handoff.get("source_artifact_manifest", [])}
        artifact_manifest_failures = [path for path in source_artifact_files if path not in handoff_artifacts or handoff_artifacts[path].get("sha256") != sha256(workspace / path)]
        check("handoff_source_artifact_manifest_complete", not artifact_manifest_failures and len(handoff_artifacts) == len(source_artifact_files), {"checked": len(handoff_artifacts), "failures": artifact_manifest_failures})
        handoff_sidecars = {row["path"]: row for row in handoff.get("pdf_preflight_manifest", [])}
        sidecar_manifest_failures = [path for path in actual_sidecars if path not in handoff_sidecars or handoff_sidecars[path].get("sha256") != sha256(workspace / path)]
        check("handoff_pdf_preflight_manifest_complete", not sidecar_manifest_failures and len(handoff_sidecars) == len(actual_sidecars), {"checked": len(handoff_sidecars), "failures": sidecar_manifest_failures})
        check("handoff_verdict_and_authorization", handoff.get("verdict") == "PASS" and handoff.get("r5_authorized") is True and handoff.get("stage2_production_citations_authorized") is False, {"verdict": handoff.get("verdict"), "r5_authorized": handoff.get("r5_authorized"), "stage2": handoff.get("stage2_production_citations_authorized")})

    receipt = {
        "schema_version": "stage1b-r1-r4-validation-receipt-1.0",
        "result": "PASS" if not failures else "FAIL",
        "checks_run": len(checks),
        "checks_passed": sum(row["status"] == "PASS" for row in checks),
        "checks_failed": sum(row["status"] == "FAIL" for row in checks),
        "checks": checks,
        "failures": failures,
        "recomputed": {
            "core": {"scholarly": len(core_scholarly), "operational_families": len(core_operational), "total": len(core_scholarly) + len(core_operational), "contract_satisfied": len(core_satisfied)},
            "queue": {"total": len(queue), "terminal_resolved": len(terminal), "dispositions": dict(Counter(row.get("terminal_disposition") for row in queue))},
            "claims": {"total": len(claims), "acquisition_satisfied": sum(row.get("acquisition_satisfied") is True for row in claims), "locator_satisfied": sum(row.get("locator_satisfied") is True for row in claims), "conditional_original_content_satisfied": len(conditional_satisfied), "production_ready": production_ready},
            "pdf_preflight": dict(preflight_counts),
            "page_anchors": len(page_locators),
            "rights_layer_conflations": rights_conflation,
            "dangling_references": len(dangling),
        },
        "input_gate": gate_receipt,
    }
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    receipt["receipt_payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return receipt


def main() -> int:
    acq = Path(__file__).resolve().parent
    receipt = validate_bundle(acq, require_handoff=True)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
