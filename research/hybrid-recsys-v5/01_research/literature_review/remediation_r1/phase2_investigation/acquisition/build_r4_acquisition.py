#!/usr/bin/env python3
"""Build the Stage 1B R1/R4 lawful-acquisition overlay and handoff."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from validate_r4_acquisition import FIXED_NONSELF_OUTPUTS, file_receipt, input_gate, sha256, validate_bundle, workspace_root


ACCESSED_AT = "2026-08-21T19:00:00+07:00"
RESEARCH_CUTOFF = "2026-08-21"
ARS_VERSION = "0.1.26"
PHASE_BOUNDARY = {
    "r5": "NOT_PERFORMED",
    "phase3_synthesis": "NOT_PERFORMED",
    "h1_h4": "NOT_RUN",
    "stage2_production_citations": "NOT_AUTHORIZED",
}
ARTIFACT_URI_OVERRIDES = {
    "huang2023_aldi": "https://www4.comp.polyu.edu.hk/~xiaohuang/docs/2023SIGIR_Feiran.pdf",
    "meehan2025_cold_popbias": "https://arxiv.org/pdf/2510.11402",
    "meehan2026_semco": "https://arxiv.org/pdf/2604.12990",
}


def dump(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def normalized_tokens(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    stop = {"a", "an", "and", "as", "be", "can", "for", "in", "of", "on", "the", "to", "using", "with"}
    return [token for token in re.findall(r"[a-z0-9]+", value) if len(token) > 2 and token not in stop]


def verify_pdf_title(path: Path, title: str) -> dict[str, Any]:
    reader = PdfReader(str(path), strict=False)
    text = "\n".join((page.extract_text() or "") for page in reader.pages[: min(5, len(reader.pages))])
    title_tokens = set(normalized_tokens(title))
    text_tokens = set(normalized_tokens(text))
    matched = sorted(title_tokens & text_tokens)
    ratio = len(matched) / len(title_tokens) if title_tokens else 0.0
    minimum = min(3, len(title_tokens))
    if len(matched) < minimum or ratio < 0.40:
        raise RuntimeError(f"affirmative title-marker verification failed for {path.name}: matched={matched}, ratio={ratio:.3f}")
    return {
        "method": "local_pdf_text_extraction_title_marker_and_sha256",
        "reader": "pypdf",
        "pages_examined": min(5, len(reader.pages)),
        "title_token_overlap": round(ratio, 6),
        "matched_title_tokens": matched,
        "result": "PASS",
    }


def artifact_entry(path: Path, workspace: Path, role: str, source_uri: str | None, local_only: bool = True) -> dict[str, Any]:
    receipt = file_receipt(path, workspace)
    suffix = path.suffix.lower()
    media_type = {
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".gz": "application/gzip",
    }.get(suffix, "application/octet-stream")
    return {
        **receipt,
        "media_type": media_type,
        "role": role,
        "source_uri": source_uri,
        "acquired_at": ACCESSED_AT,
        "local_only": local_only,
        "redistribution_in_bundle": False,
    }


def clean_locator(source_key: str, anchor: str | None) -> str:
    overrides = {
        "dacrema2021_reproducibility": "Section 3; reproducible-setup criteria; discussion of evaluation practice",
        "gusak2025_time_split": "Figure 1; Sections 1–3; global temporal split and results subsections",
        "jin2023_amazon_m2": "Sections 2.1–2.2; Table 1; Appendix B.3",
        "krichene2020_sampled_metrics": "Abstract; empirical ordering results; Sections 7–8",
        "li2023_reliable_sampling": "Abstract; Introduction; experimental comparison section",
        "tagliabue2021_coveo": "Sections 2–4; Tables 1–2",
        "tran2024_viecomrec": "Sections 3.1 and 5.1",
        "zhao2020_alternative_settings": "Abstract; Sections 2–4; Table 2",
        "liu2009_hybrid_seq_cf": "Replacement work Sections 3 and 3.1; Figures 1–4; Conclusions",
        "jannach2026_methodological_standards": "Abstract; Sections 1–3 and 5; Appendix evaluation guidelines",
    }
    if source_key in overrides:
        return overrides[source_key]
    value = (anchor or "").strip()
    if re.search(r"(?i)(\bpage\b|\bpages\b|\bpp\.?\s*\d)", value):
        return "Named sections, tables, figures, and structural results retained from the frozen R3 original-content locator"
    return value or "Original-content structural locator retained from the frozen R3 registry"


def locator_type(value: str, basis: str) -> str:
    lowered = value.lower()
    if basis == "abstract_only" or ("abstract" in lowered and not any(word in lowered for word in ("section", "table", "figure"))):
        return "abstract"
    if "figure" in lowered:
        return "figure"
    if "table" in lowered:
        return "table"
    return "section"


def main() -> int:
    acq = Path(__file__).resolve().parent
    workspace = workspace_root(acq)
    remediation = acq.parents[1]
    integration = remediation / "phase2_investigation" / "integration"
    control = remediation / "00_control"
    artifacts_dir = acq / "source_artifacts"
    sidecars_dir = acq / "pdf_preflight"

    gate_receipt, gate_failures = input_gate(acq, workspace)
    if gate_failures:
        raise RuntimeError("HANDOFF_INCOMPLETE: " + json.dumps(gate_failures, ensure_ascii=False))

    input_manifest = json.loads((control / "r4_input_manifest.json").read_text(encoding="utf-8"))
    source_registry = json.loads((integration / "source_registry_r1.json").read_text(encoding="utf-8"))
    operational_registry = json.loads((integration / "operational_resource_registry.json").read_text(encoding="utf-8"))
    family_registry = json.loads((integration / "source_family_map_r1.json").read_text(encoding="utf-8"))
    r3_handoff = json.loads((integration / "r3_handoff.json").read_text(encoding="utf-8"))
    sources = source_registry["sources"]
    resources = operational_registry["resources"]
    source_by_key = {row["source_key"]: row for row in sources}
    resource_by_key = {row["resource_key"]: row for row in resources}
    claims = r3_handoff["claim_dispositions"]

    claim_ids_by_source: dict[str, list[str]] = defaultdict(list)
    claim_ids_by_resource: dict[str, list[str]] = defaultdict(list)
    for claim in claims:
        for key in claim["canonical_source_keys"]:
            claim_ids_by_source[key].append(claim["claim_id"])
        for key in claim["operational_resource_keys"]:
            claim_ids_by_resource[key].append(claim["claim_id"])

    queue_source_keys = {row["source_key"] for row in input_manifest["r4_queue"] if "source_key" in row}
    core_source_keys = {row["source_key"] for row in sources if row.get("record_type") == "scholarly_work" and row.get("core_shortlist") is True}
    target_source_keys = sorted(core_source_keys | queue_source_keys)
    if (len(core_source_keys), len(target_source_keys)) != (23, 29):
        raise RuntimeError(f"unexpected R4 scholarly population: core={len(core_source_keys)}, target={len(target_source_keys)}")

    source_pdf_verification: dict[str, dict[str, Any]] = {}
    for key in target_source_keys:
        path = artifacts_dir / f"{key}.pdf"
        if path.is_file():
            source_pdf_verification[key] = verify_pdf_title(path, source_by_key[key]["title"])

    complete_tar = artifacts_dir / "completejourney_1.1.1.tar.gz"
    with tarfile.open(complete_tar, "r:gz") as archive:
        tar_members = archive.getnames()
    rda_members = sorted(name for name in tar_members if name.lower().endswith(".rda"))
    if len(tar_members) != 60 or len(rda_members) != 8:
        raise RuntimeError(f"unexpected completejourney tarball structure: entries={len(tar_members)}, rda={len(rda_members)}")
    required_markers = {
        "complete_journey_provider_page_2026-08-21.html": ["Complete Journey", "2,500 households"],
        "complete_journey_provider_terms_2026-08-21.html": ["research", "non-commercial"],
        "completejourney_1.1.1_cran_page.html": ["completejourney", "1.1.1", "CC0"],
        "completejourney_1.1.1_user_guide.html": ["completejourney", "transactions"],
        "jannach2026_hkbu_identity.html": ["Improving Methodological Standards", "10.1145/3800587"],
        "liu2009_nycu_identity_abstract.html": ["A Hybrid of Sequential Rules", "10.1016/j.ins.2009.06.004"],
    }
    for name, markers in required_markers.items():
        text = (artifacts_dir / name).read_text(encoding="utf-8", errors="ignore").lower()
        missing = [marker for marker in markers if marker.lower() not in text]
        if missing:
            raise RuntimeError(f"affirmative local marker verification failed for {name}: {missing}")

    sidecar_by_pdf: dict[str, dict[str, Any]] = {}
    sidecar_manifest: list[dict[str, Any]] = []
    for sidecar_path in sorted(sidecars_dir.glob("*.preflight.json")):
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        pdf_name = sidecar_path.name.removesuffix(".preflight.json") + ".pdf"
        pdf_path = artifacts_dir / pdf_name
        if not pdf_path.is_file() or sha256(pdf_path) != data["sha256"]:
            raise RuntimeError(f"preflight PDF binding failed: {sidecar_path.name}")
        row = {
            "pdf_path": pdf_path.relative_to(workspace).as_posix(),
            "pdf_bytes": pdf_path.stat().st_size,
            "pdf_sha256": sha256(pdf_path),
            "sidecar_path": sidecar_path.relative_to(workspace).as_posix(),
            "sidecar_bytes": sidecar_path.stat().st_size,
            "sidecar_sha256": sha256(sidecar_path),
            "verdict": data["verdict"],
            "warnings": data.get("warnings", []),
            "tool": data.get("tool"),
        }
        sidecar_by_pdf[pdf_name] = row
        sidecar_manifest.append(row)
    if Counter(row["verdict"] for row in sidecar_manifest) != Counter({"PASS": 27, "UNAVAILABLE": 1}):
        raise RuntimeError(f"unexpected PDF preflight outcomes: {Counter(row['verdict'] for row in sidecar_manifest)}")

    locator_rows: list[dict[str, Any]] = []
    locator_id_by_source: dict[str, str] = {}
    all_claim_source_keys = {key for claim in claims for key in claim["canonical_source_keys"]}
    locator_source_keys = sorted(all_claim_source_keys | set(target_source_keys))
    for key in locator_source_keys:
        source = source_by_key[key]
        r3_locator = source.get("locators", [{}])[0] if source.get("locators") else {}
        value = clean_locator(key, r3_locator.get("anchor"))
        basis = r3_locator.get("basis", "original_content")
        artifact_uri = ARTIFACT_URI_OVERRIDES.get(key) or r3_locator.get("uri") or source.get("official_url")
        verification_method = "frozen_r3_original_content_verification"
        local_path: str | None = None
        preflight: dict[str, Any] | None = None
        advisory: str | None = None
        if key in source_pdf_verification:
            pdf = artifacts_dir / f"{key}.pdf"
            local_path = pdf.relative_to(workspace).as_posix()
            verification_method = source_pdf_verification[key]["method"]
            pf = sidecar_by_pdf[pdf.name]
            preflight = {
                "sidecar_path": pf["sidecar_path"],
                "sidecar_sha256": pf["sidecar_sha256"],
                "verdict": pf["verdict"],
            }
            if pf["verdict"] == "UNAVAILABLE":
                advisory = "Structural preflight is UNAVAILABLE; page anchors are prohibited and this verified non-page locator is mandatory."
        if key == "jannach2026_methodological_standards":
            artifact_uri = "https://dl.acm.org/doi/full/10.1145/3800587"
            basis = "original_content"
            verification_method = "authoritative_publisher_html_section_inspection"
        if key == "liu2009_hybrid_seq_cf":
            artifact_uri = "https://ir.lib.nycu.edu.tw/bitstream/11536/7824/1/000250044300024.pdf"
            basis = "original_content_equivalent_replacement"
            verification_method = "authoritative_repository_pdf_section_and_figure_inspection"
        locator_id = f"LOC-R4-S-{key}-01"
        locator_id_by_source[key] = locator_id
        locator_rows.append({
            "locator_id": locator_id,
            "source_key": key,
            "resource_key": None,
            "source_family_id": source["source_family_id"],
            "claim_ids": sorted(claim_ids_by_source.get(key, [])),
            "locator_type": locator_type(value, basis),
            "locator_value": value,
            "basis": basis,
            "artifact_uri": artifact_uri,
            "local_artifact_path": local_path,
            "verified_against_original": source.get("source_content_verified") is True or key in {"jannach2026_methodological_standards", "liu2009_hybrid_seq_cf"},
            "verification_method": verification_method,
            "page_anchor": False,
            "pdf_preflight": preflight,
            "advisory": advisory,
            "production_citation_authorized": False,
        })

    locator_id_by_resource: dict[str, str] = {}
    all_claim_resource_keys = sorted({key for claim in claims for key in claim["operational_resource_keys"]})
    complete_values = {
        "R-L5-COMPLETE-JOURNEY-PROVIDER": "The Complete Journey; What is inside; intended uses; source-file access form; Terms and Conditions section A.1",
        "R-L5-COMPLETEJOURNEY-R-PACKAGE": "CRAN Description, License, Downloads; package manual named data-object entries; user-guide Accessing Data and Dataset Details sections",
    }
    for key in all_claim_resource_keys:
        resource = resource_by_key[key]
        locator_id = f"LOC-R4-R-{key}-01"
        locator_id_by_resource[key] = locator_id
        is_complete = resource["source_family_id"] == "SF-R1-075"
        locator_rows.append({
            "locator_id": locator_id,
            "source_key": None,
            "resource_key": key,
            "source_family_id": resource["source_family_id"],
            "claim_ids": sorted(claim_ids_by_resource.get(key, [])),
            "locator_type": "section",
            "locator_value": complete_values.get(key, "Official provider resource description and frozen R3 operational access record"),
            "basis": "original_operational_content" if is_complete else "authoritative_operational_record",
            "artifact_uri": resource["official_url"],
            "local_artifact_path": None,
            "verified_against_original": True if is_complete else resource.get("source_content_verified") is True,
            "verification_method": "local_provider_package_terms_and_documentation_marker_verification" if is_complete else "frozen_r3_operational_verification",
            "page_anchor": False,
            "pdf_preflight": None,
            "advisory": None,
            "production_citation_authorized": False,
        })

    acquisition_rows: list[dict[str, Any]] = []
    for key in target_source_keys:
        source = source_by_key[key]
        claims_supported = sorted(claim_ids_by_source.get(key, []))
        local_artifacts: list[dict[str, Any]] = []
        pdf = artifacts_dir / f"{key}.pdf"
        exact_source_acquired = True
        replacement: dict[str, Any] | None = None
        route = "lawful_local_same_work_artifact"
        route_url = ARTIFACT_URI_OVERRIDES.get(key) or (source.get("locators") or [{}])[0].get("uri") or source.get("official_url")
        no_local_reason: str | None = None
        method: dict[str, Any]
        if pdf.is_file():
            local_artifacts.append(artifact_entry(pdf, workspace, "authoritative_original_or_same_work_copy", route_url))
            method = source_pdf_verification[key]
        elif key == "jannach2026_methodological_standards":
            identity = artifacts_dir / "jannach2026_hkbu_identity.html"
            local_artifacts.append(artifact_entry(identity, workspace, "official_identity_metadata_support", "https://scholars.hkbu.edu.hk/en/publications/improving-methodological-standards-in-recommender-systems-offline-/"))
            route = "authoritative_publisher_html_remote_original"
            route_url = "https://dl.acm.org/doi/full/10.1145/3800587"
            no_local_reason = "The official ACM article was inspected through the lawful publisher HTML route; direct automated retrieval returned HTTP 403, so no restriction was bypassed and no local publisher copy was stored."
            method = {"method": "authoritative_publisher_html_section_inspection", "sections_verified": ["Abstract", "1", "2", "3", "5", "Appendix"], "result": "PASS"}
        elif key == "liu2009_hybrid_seq_cf":
            identity = artifacts_dir / "liu2009_nycu_identity_abstract.html"
            local_artifacts.append(artifact_entry(identity, workspace, "official_2009_identity_and_abstract_support", source["official_url"]))
            exact_source_acquired = False
            route = "accepted_equivalent_same_family_replacement"
            route_url = "https://ir.lib.nycu.edu.tw/bitstream/11536/7824/1/000250044300024.pdf"
            no_local_reason = "The exact 2009 journal full text was not lawfully available. The official NYCU repository served the 2007 predecessor interactively, but scripted retrieval yielded a challenge document; no TLS or access control was bypassed."
            method = {"method": "authoritative_repository_pdf_section_and_figure_inspection", "sections_verified": ["1", "2.2.2", "3", "3.1", "Conclusions"], "figures_verified": ["1", "2", "3", "4"], "result": "PASS"}
            replacement = {
                "decision": "accepted_for_bounded_hybrid_method_evidence",
                "source_family_id": source["source_family_id"],
                "title": "A Hybrid of Sequential Rules and Collaborative Filtering for Product Recommendation",
                "authors": ["Duen-Ren Liu", "Chin-Hui Lai", "Wang-Jung Lee"],
                "publication_year": 2007,
                "venue": "IEEE International Conference on e-Business Engineering",
                "doi": "10.1109/ICEBE.2007.6",
                "official_repository_url": route_url,
                "family_relation": "Conference predecessor with the same title and authors; the 2009 Information Sciences article is the expanded journal work in the same frozen family.",
                "evidence_coverage": "Sequential-rule score, collaborative-filtering score, hybrid score, architecture, and comparative experiment structure.",
                "equivalence_scope": "Equivalent for the bounded L3-HYB-006 hybrid-method proposition only; not equivalent for journal-specific details or numerical results.",
                "exclusion_rationale": "The exact 2009 publisher record provides authoritative identity and abstract but no lawfully acquired full text; metadata alone cannot verify exact journal content.",
            }
        else:
            raise RuntimeError(f"no acquisition route for target {key}")

        pf_binding = None
        if pdf.is_file():
            pf = sidecar_by_pdf[pdf.name]
            pf_binding = {"sidecar_path": pf["sidecar_path"], "sidecar_sha256": pf["sidecar_sha256"], "verdict": pf["verdict"], "page_anchors_permitted": pf["verdict"] == "PASS"}
        queue_target = key in queue_source_keys
        terminal_disposition = None
        if queue_target:
            if key == "liu2009_hybrid_seq_cf":
                terminal_disposition = "equivalent_replacement_accepted"
            elif key == "jannach2026_methodological_standards":
                terminal_disposition = "same_work_authoritative_remote_acquired"
            else:
                terminal_disposition = "same_work_lawful_local_artifact_acquired"
        acquisition_rows.append({
            "acquisition_key": f"AQ-R4-S-{key}",
            "record_type": "scholarly_work",
            "source_key": key,
            "resource_keys": [],
            "source_family_id": source["source_family_id"],
            "priority": "core" if key in core_source_keys else "production_claim",
            "core_object": key in core_source_keys,
            "queue_target": queue_target,
            "supported_claim_ids": claims_supported,
            "identity": {
                "title": source["title"],
                "authors": source["authors"],
                "publication_year": source["publication_year"],
                "venue": source["venue"],
                "document_type": source["document_type"],
                "publication_status": source["publication_status"],
                "doi": source.get("doi"),
                "official_id": source.get("official_id"),
                "official_url": source.get("official_url"),
                "version_relation": [row.get("version_relation") for row in source.get("manifestations", [])],
            },
            "accessed_at": ACCESSED_AT,
            "acquisition_route": route,
            "acquisition_url": route_url,
            "local_artifacts": local_artifacts,
            "no_lawful_local_copy_reason": no_local_reason,
            "rights_access": {
                "availability": "lawfully accessible through the recorded official or author/repository route",
                "license": "No broader redistribution license inferred unless stated by the source",
                "access": "research inspection/download only; no paywall, authentication, TLS, robots, or provider control bypassed",
                "dataset_rights": None,
                "redistribution": "not authorized by this record; local-only original artifact",
                "commit_status": "LOCAL_ONLY",
            },
            "source_acquired": True,
            "exact_target_source_acquired": exact_source_acquired,
            "source_content_verified": True,
            "source_verified_against_original": True,
            "affirmative_verification": method,
            "locator_ready": True,
            "locator_ids": [locator_id_by_source[key]],
            "pdf_preflight": pf_binding,
            "replacement": replacement,
            "terminal_disposition": terminal_disposition,
            "limitations": source.get("limitations", []) + (["The accepted 2007 replacement cannot establish exact 2009 journal-specific content or results."] if replacement else []),
            "unresolved_blockers": [],
            "forbidden_downstream_use": ["R4 does not authorize production citation.", "Do not use before R5 claim-map rebuild and bounded synthesis."],
            "r4_contract_satisfied": True,
        })

    complete_paths = {
        "provider_page": artifacts_dir / "complete_journey_provider_page_2026-08-21.html",
        "provider_terms": artifacts_dir / "complete_journey_provider_terms_2026-08-21.html",
        "cran_page": artifacts_dir / "completejourney_1.1.1_cran_page.html",
        "package_manual": artifacts_dir / "completejourney_1.1.1_manual.pdf",
        "user_guide": artifacts_dir / "completejourney_1.1.1_user_guide.html",
        "package_tarball": complete_tar,
    }
    complete_uris = {
        "provider_page": "https://www.dunnhumby.com/source-files/",
        "provider_terms": "https://www.dunnhumby.com/terms-and-conditions/",
        "cran_page": "https://cran.r-project.org/package=completejourney",
        "package_manual": "https://cran.r-project.org/web/packages/completejourney/completejourney.pdf",
        "user_guide": "https://bradleyboehmke.github.io/completejourney/",
        "package_tarball": "https://cran.r-project.org/src/contrib/completejourney_1.1.1.tar.gz",
    }
    complete_artifacts = [artifact_entry(path, workspace, role, complete_uris[role]) for role, path in complete_paths.items()]
    complete_claims = sorted(set(claim_ids_by_resource["R-L5-COMPLETE-JOURNEY-PROVIDER"] + claim_ids_by_resource["R-L5-COMPLETEJOURNEY-R-PACKAGE"]))
    acquisition_rows.append({
        "acquisition_key": "AQ-R4-F-SF-R1-075",
        "record_type": "operational_family",
        "source_key": None,
        "resource_keys": ["R-L5-COMPLETE-JOURNEY-PROVIDER", "R-L5-COMPLETEJOURNEY-R-PACKAGE"],
        "source_family_id": "SF-R1-075",
        "priority": "core",
        "core_object": True,
        "queue_target": True,
        "supported_claim_ids": complete_claims,
        "identity": {
            "provider": "dunnhumby",
            "dataset_family": "The Complete Journey / Complete Journey 2.0",
            "selected_package_edition": "completejourney 1.1.1, CRAN publication 2025-11-26",
            "provider_page_snapshot": "2026-08-21",
            "package_doi": "10.32614/CRAN.package.completejourney",
            "package_authors": ["Brad Boehmke", "Steven Mortimer"],
        },
        "accessed_at": ACCESSED_AT,
        "acquisition_route": "official_provider_pages_plus_official_cran_package",
        "acquisition_url": "https://cran.r-project.org/package=completejourney",
        "local_artifacts": complete_artifacts,
        "no_lawful_local_copy_reason": "The provider full payload was not requested through the interactive email/terms form; only the public evidence and official CRAN package payload were acquired.",
        "rights_access": {
            "availability": "Public provider page with an interactive terms/form route; public CRAN package",
            "license": "CC0 applies to the R package only",
            "access": "CRAN package acquired; provider full payload requires interactive terms/form completion",
            "dataset_rights": "Provider terms permit one copy for research, personal, or non-commercial use subject to conditions; other rights are reserved",
            "redistribution": "No general upstream dataset redistribution permission established",
            "commit_status": "LOCAL_ONLY because the package contains derived upstream data",
        },
        "source_acquired": True,
        "exact_target_source_acquired": True,
        "source_content_verified": True,
        "source_verified_against_original": True,
        "affirmative_verification": {
            "method": "local_tar_structure_plus_provider_terms_page_manual_and_guide_marker_verification",
            "tar_entries": len(tar_members),
            "built_in_rda_objects": len(rda_members),
            "built_in_rda_members": rda_members,
            "result": "PASS",
        },
        "locator_ready": True,
        "locator_ids": [locator_id_by_resource["R-L5-COMPLETE-JOURNEY-PROVIDER"], locator_id_by_resource["R-L5-COMPLETEJOURNEY-R-PACKAGE"]],
        "pdf_preflight": {
            "sidecar_path": sidecar_by_pdf["completejourney_1.1.1_manual.pdf"]["sidecar_path"],
            "sidecar_sha256": sidecar_by_pdf["completejourney_1.1.1_manual.pdf"]["sidecar_sha256"],
            "verdict": sidecar_by_pdf["completejourney_1.1.1_manual.pdf"]["verdict"],
            "page_anchors_permitted": True,
        },
        "replacement": None,
        "terminal_disposition": "operational_family_rights_access_payload_state_resolved",
        "limitations": [
            "The full upstream provider payload was not acquired because the current route requires interactive form submission and terms consent.",
            "Package CC0 does not grant CC0 rights in upstream Complete Journey data.",
            "Local execution is established for the CRAN package and built-in data, not for the unacquired full provider payload.",
        ],
        "unresolved_blockers": [],
        "forbidden_downstream_use": ["Do not redistribute upstream data.", "R4 does not authorize production citation or benchmark execution."],
        "r4_contract_satisfied": True,
    })

    queue_dispositions: list[dict[str, Any]] = []
    acquisition_by_source = {row.get("source_key"): row for row in acquisition_rows if row.get("source_key")}
    for row in input_manifest["r4_queue"]:
        if "source_key" in row:
            acquired = acquisition_by_source[row["source_key"]]
            queue_dispositions.append({
                "queue_target_id": row["source_key"],
                "source_key": row["source_key"],
                "source_family_id": acquired["source_family_id"],
                "priority": row["priority"],
                "status": "resolved",
                "terminal": True,
                "terminal_disposition": acquired["terminal_disposition"],
                "acquisition_key": acquired["acquisition_key"],
            })
        else:
            queue_dispositions.append({
                "queue_target_id": row["source_family_id"],
                "source_key": None,
                "source_family_id": row["source_family_id"],
                "resource_keys": row["resource_keys"],
                "priority": row["priority"],
                "status": "resolved",
                "terminal": True,
                "terminal_disposition": "operational_family_rights_access_payload_state_resolved",
                "acquisition_key": "AQ-R4-F-SF-R1-075",
            })

    acquisition_manifest = {
        "schema_version": "stage1b-r1-r4-source-acquisition-manifest-1.0",
        "project": "hybrid-recsys-v5",
        "stage": "1B",
        "round": "R1",
        "step": "R4_source_acquisition_and_locator_completion",
        "ars_codex_version": ARS_VERSION,
        "research_cutoff": RESEARCH_CUTOFF,
        "generated_at": ACCESSED_AT,
        "input_gate": gate_receipt,
        "scope_rule": "23 frozen scholarly core objects plus one frozen operational core family and six additional non-core scholarly queue targets; no broad discovery.",
        "counts": {
            "acquisition_records": len(acquisition_rows),
            "scholarly_target_records": sum(row["record_type"] == "scholarly_work" for row in acquisition_rows),
            "operational_family_records": sum(row["record_type"] == "operational_family" for row in acquisition_rows),
            "core_scholarly": sum(row["record_type"] == "scholarly_work" and row["core_object"] for row in acquisition_rows),
            "core_operational_families": sum(row["record_type"] == "operational_family" and row["core_object"] for row in acquisition_rows),
            "core_total": sum(row["core_object"] for row in acquisition_rows),
            "core_acquired": sum(row["core_object"] and row["source_acquired"] for row in acquisition_rows),
            "core_content_verified": sum(row["core_object"] and row["source_content_verified"] for row in acquisition_rows),
            "core_locator_ready": sum(row["core_object"] and row["locator_ready"] for row in acquisition_rows),
            "local_artifacts": sum(len(row["local_artifacts"]) for row in acquisition_rows),
            "queue_targets": len(queue_dispositions),
            "queue_terminal_resolved": sum(row["terminal"] and row["status"] == "resolved" for row in queue_dispositions),
        },
        "acquisitions": acquisition_rows,
        "queue_dispositions": queue_dispositions,
        "degradation_ledger": [
            {"route": "ACM direct automated full-article retrieval", "target": "jannach2026_methodological_standards", "result": "HTTP 403", "handling": "No bypass; verified the official full publisher HTML through the lawful browser route and stored only official institutional identity metadata."},
            {"route": "Exact 2009 journal full text", "target": "liu2009_hybrid_seq_cf", "result": "No lawful open full copy located", "handling": "Accepted the 2007 official-repository predecessor for bounded hybrid-method evidence; retained exact 2009 identity/abstract and exclusion rationale."},
            {"route": "NYCU scripted repository download", "target": "liu2009_hybrid_seq_cf replacement", "result": "Challenge HTML instead of PDF", "handling": "Rejected the payload; no TLS/access bypass; original content was verified through the authoritative repository browser artifact."},
            {"route": "ETH proceedings PDF", "target": "liu2009_hybrid_seq_cf replacement", "result": "Table of contents only", "handling": "Rejected as non-original-content evidence."},
            {"route": "System Python structural preflight", "target": "all local PDFs", "result": "pypdf unavailable and Windows output writer incompatible", "handling": "Re-ran the unmodified ARS v0.1.26 preflight under the bundled workspace Python and mechanically retained stdout sidecars."},
            {"route": "ARS structural PDF preflight", "target": "li2023_repetition_exploration", "result": "UNAVAILABLE due stale/unreachable xref object advisory", "handling": "Prohibited page anchors; retained a verified Introduction/analysis structural locator."},
            {"route": "Frozen R3 arXiv locator", "target": "huang2023_aldi", "result": "Resolved to an unrelated Web3 money-laundering paper", "handling": "Rejected the wrong payload, acquired the exact author-hosted PolyU ALDI paper, and recorded the corrected R4 overlay locator without editing frozen R3."},
            {"route": "Frozen R3 arXiv locator", "target": "meehan2025_cold_popbias", "result": "Resolved to an unrelated multimodal target-selection paper", "handling": "Rejected the wrong payload, acquired the exact same-work arXiv manuscript 2510.11402, and recorded the corrected R4 overlay locator without editing frozen R3."},
            {"route": "Frozen R3 arXiv locator", "target": "meehan2026_semco", "result": "Resolved to an unrelated mathematics paper", "handling": "Rejected the wrong payload, acquired the exact same-work arXiv manuscript 2604.12990, and recorded the corrected R4 overlay locator without editing frozen R3."},
            {"route": "dunnhumby full provider payload", "target": "SF-R1-075", "result": "Interactive form/terms/email route required", "handling": "Did not submit or automate consent; recorded the exact access state and acquired the official CRAN package, manual, guide, provider page, and terms."},
        ],
        "phase_boundary": PHASE_BOUNDARY,
    }
    dump(acq / "source_acquisition_manifest.json", acquisition_manifest)

    locator_registry = {
        "schema_version": "stage1b-r1-r4-locator-registry-1.0",
        "project": "hybrid-recsys-v5",
        "generated_at": ACCESSED_AT,
        "locator_rule": "Only verified non-page structural locators are emitted. No page or page-range anchor is used.",
        "counts": {
            "locators": len(locator_rows),
            "source_locators": sum(row["source_key"] is not None for row in locator_rows),
            "resource_locators": sum(row["resource_key"] is not None for row in locator_rows),
            "page_anchors": 0,
            "pdf_preflight_sidecars": len(sidecar_manifest),
            "pdf_preflight_pass": sum(row["verdict"] == "PASS" for row in sidecar_manifest),
            "pdf_preflight_unavailable": sum(row["verdict"] == "UNAVAILABLE" for row in sidecar_manifest),
            "pdf_preflight_fail": sum(row["verdict"] == "FAIL" for row in sidecar_manifest),
        },
        "locators": locator_rows,
        "pdf_preflight_manifest": sidecar_manifest,
        "quotes_used": 0,
    }
    dump(acq / "locator_registry.json", locator_registry)

    overlay_acquired = {row["source_key"]: row["source_acquired"] for row in acquisition_rows if row.get("source_key")}
    overlay_content = {row["source_key"]: row["source_content_verified"] for row in acquisition_rows if row.get("source_key")}
    overlay_locator = {row["source_key"]: row["locator_ready"] for row in acquisition_rows if row.get("source_key")}
    complete_acquired = {key: True for key in ("R-L5-COMPLETE-JOURNEY-PROVIDER", "R-L5-COMPLETEJOURNEY-R-PACKAGE")}
    claim_rows: list[dict[str, Any]] = []
    for claim in claims:
        source_acquired_states = [overlay_acquired.get(key, source_by_key[key].get("source_acquired") is True) for key in claim["canonical_source_keys"]]
        resource_acquired_states = [complete_acquired.get(key, resource_by_key[key].get("source_acquired") is True) for key in claim["operational_resource_keys"]]
        acquisition_satisfied = all(source_acquired_states + resource_acquired_states)
        source_content_states = [overlay_content.get(key, source_by_key[key].get("source_content_verified") is True) for key in claim["canonical_source_keys"]]
        original_content_satisfied = all(source_content_states) and bool(source_content_states)
        source_locator_states = [overlay_locator.get(key, source_by_key[key].get("locator_ready") is True) for key in claim["canonical_source_keys"]]
        resource_locator_states = [resource_by_key[key].get("locator_ready") is True for key in claim["operational_resource_keys"]]
        locator_satisfied = all(source_locator_states + resource_locator_states) and bool(source_locator_states + resource_locator_states)
        linked_locator_ids = [locator_id_by_source[key] for key in claim["canonical_source_keys"]] + [locator_id_by_resource[key] for key in claim["operational_resource_keys"]]
        conditional = claim["central_disposition"] == "conditional_production_candidate"
        r5_prerequisites = conditional and acquisition_satisfied and original_content_satisfied and locator_satisfied
        claim_rows.append({
            "claim_id": claim["claim_id"],
            "lane": claim["lane"],
            "original_lane_state": claim["original_lane_state"],
            "central_disposition": claim["central_disposition"],
            "central_conditions": claim["central_conditions"],
            "canonical_source_keys": claim["canonical_source_keys"],
            "operational_resource_keys": claim["operational_resource_keys"],
            "source_family_ids": claim["source_family_ids"],
            "locator_ids": linked_locator_ids,
            "acquisition_satisfied": acquisition_satisfied,
            "original_content_satisfied": original_content_satisfied,
            "locator_satisfied": locator_satisfied,
            "r5_prerequisites_satisfied": r5_prerequisites,
            "downstream_eligibility": "eligible_for_r5_claim_map_rebuild_only" if r5_prerequisites else "planning_only_unchanged",
            "production_ready": False,
            "r4_note": "R4 establishes acquisition and locator prerequisites only; R5 must rebuild and bound the claim before any later citation gate." if conditional else "Original planning-only disposition is preserved.",
        })
    claim_map = {
        "schema_version": "stage1b-r1-r4-claim-acquisition-map-1.0",
        "project": "hybrid-recsys-v5",
        "generated_at": ACCESSED_AT,
        "claim_state_rule": "Original lane flags and the exclusive R3 central disposition are immutable at R4; production_ready is always false.",
        "counts": {
            "claims": len(claim_rows),
            "conditional_production_candidate": sum(row["central_disposition"] == "conditional_production_candidate" for row in claim_rows),
            "planning_only": sum(row["central_disposition"] == "planning_only" for row in claim_rows),
            "acquisition_satisfied": sum(row["acquisition_satisfied"] for row in claim_rows),
            "locator_satisfied": sum(row["locator_satisfied"] for row in claim_rows),
            "conditional_original_content_and_locator_satisfied": sum(row["r5_prerequisites_satisfied"] for row in claim_rows),
            "production_ready": sum(row["production_ready"] for row in claim_rows),
        },
        "claims": claim_rows,
        "phase_boundary": PHASE_BOUNDARY,
    }
    dump(acq / "r4_claim_acquisition_map.json", claim_map)

    complete_rights = {
        "source_family_id": "SF-R1-075",
        "resource_keys": ["R-L5-COMPLETE-JOURNEY-PROVIDER", "R-L5-COMPLETEJOURNEY-R-PACKAGE"],
        "selected_edition": {
            "provider_family": "The Complete Journey / Complete Journey 2.0",
            "provider_page_snapshot": "2026-08-21",
            "r_package": "completejourney 1.1.1",
            "r_package_published": "2025-11-26",
            "package_doi": "10.32614/CRAN.package.completejourney",
        },
        "rights_layers": {
            "provider_availability": {"status": "PUBLIC_GATED_ROUTE", "finding": "The source-files page is public; the dataset download route requires an interactive form, terms agreement, and emailed link."},
            "provider_access": {"status": "NOT_EXECUTED", "finding": "No form was submitted and no consent or authentication flow was automated. Public page and terms evidence were acquired."},
            "package_code_license": {"status": "CC0", "scope": "The completejourney R package only."},
            "paper_license": {"status": "NOT_APPLICABLE", "finding": "No separate scholarly paper is used as the operational artifact; package manual and documentation are bundled package materials."},
            "dataset_rights": {"status": "RESTRICTED", "finding": "Provider terms allow one copy for research, personal, or non-commercial use subject to conditions; other rights remain reserved."},
            "execution_access": {"status": "PARTIAL_LOCAL_EXECUTION_AVAILABLE", "finding": "The CRAN tarball and eight built-in .rda data objects are local and executable; the full provider transactions/promotions payload was not acquired."},
            "redistribution_permission": {"status": "NOT_ESTABLISHED", "finding": "No general redistribution permission for upstream Complete Journey data was established; all local artifacts remain local-only."},
        },
        "license_scope_assertion": "Package CC0 is not propagated to upstream Complete Journey data.",
        "payload_schema_dictionary_state": {
            "package_tarball": "ACQUIRED_AND_HASHED",
            "package_tar_entries": len(tar_members),
            "built_in_data_objects": {"status": "ACQUIRED", "count": len(rda_members), "members": rda_members},
            "full_transactions_payload": "NOT_ACQUIRED_INTERACTIVE_PROVIDER_ROUTE",
            "full_promotions_payload": "NOT_ACQUIRED_INTERACTIVE_PROVIDER_ROUTE",
            "schema": "ACQUIRED_IN_PACKAGE_MANUAL_MAN_PAGES_AND_VIGNETTE",
            "data_dictionary": "ACQUIRED_IN_PACKAGE_MANUAL_AND_USER_GUIDE",
        },
        "terms_evidence": [
            next(row for row in complete_artifacts if row["role"] == "provider_terms"),
            next(row for row in complete_artifacts if row["role"] == "provider_page"),
            next(row for row in complete_artifacts if row["role"] == "cran_page"),
        ],
        "decision": "RESOLVED_WITH_SEPARATE_RIGHTS_AND_ACCESS_LAYERS",
        "r4_contract_satisfied": True,
    }
    rights_registry = {
        "schema_version": "stage1b-r1-r4-rights-access-registry-1.0",
        "project": "hybrid-recsys-v5",
        "generated_at": ACCESSED_AT,
        "rights_rule": "Availability, provider access, package/code license, paper license, dataset rights, execution access, and redistribution permission are independent axes.",
        "scholarly_local_storage_policy": {
            "status": "LOCAL_ONLY",
            "finding": "No original scholarly artifact is asserted redistributable unless an explicit license says so; R4 stores research copies locally and does not authorize commit or redistribution.",
        },
        "operational_families": [complete_rights],
        "counts": {"operational_families": 1, "rights_layers": 7, "rights_layer_conflations": 0},
    }
    dump(acq / "rights_access_registry.json", rights_registry)

    queue_counts = Counter(row["terminal_disposition"] for row in queue_dispositions)
    preflight_counts = Counter(row["verdict"] for row in sidecar_manifest)
    report = f"""# R4 lawful source acquisition and locator completion report

## Verdict

**PASS.** All 24 frozen core objects satisfy the R4 acquisition, affirmative original-content verification, and locator contract. All 13 frozen queue targets have one resolved terminal disposition. This PASS authorizes only R5 claim-map rebuild and Phase 3 synthesis; it does not authorize Stage 2 production citations.

## Scope and method

Execution followed ARS-Codex v{ARS_VERSION} Deep Research Phase 2. The input-manifest hash, contract, all twelve frozen R3 integration files, the R3 PASS/20-of-20 independent audit, and all 64 transitively bound prior artifacts were revalidated before the R4 handoff was generated. Searches were limited to exact lawful copies, authoritative identity/version evidence, same-work manifestations, and one bounded replacement. External pages, PDFs, repositories, and datasets were treated only as untrusted evidence.

## Acquisition results

- Core: 23/23 scholarly plus 1/1 operational family acquired through a lawful authoritative route or accepted bounded replacement; 24/24 content verified; 24/24 locator ready.
- Frozen queue: {len(queue_dispositions)}/13 terminal and resolved.
- Queue dispositions: {dict(queue_counts)}.
- Claims: {sum(row['acquisition_satisfied'] for row in claim_rows)}/44 acquisition satisfied; {sum(row['locator_satisfied'] for row in claim_rows)}/44 locator satisfied; {sum(row['r5_prerequisites_satisfied'] for row in claim_rows)}/22 conditional candidates have original-content and locator prerequisites for R5; 0 production-ready.
- Local artifacts: {sum(len(row['local_artifacts']) for row in acquisition_rows)} files, each byte-counted and SHA-256 bound.

## Substitution and bounded use

The exact 2009 Information Sciences full text for `liu2009_hybrid_seq_cf` was not lawfully acquired. The official NYCU repository copy of the 2007 conference predecessor—same title, authors, and frozen source family; DOI `10.1109/ICEBE.2007.6`—is accepted only for the bounded hybrid-method proposition in `L3-HYB-006`. Its verified coverage includes the sequential-rule score, collaborative-filtering score, hybrid score, architecture, and comparative experiment structure. It must not support 2009-journal-specific details or numerical results. The exact 2009 official identity and abstract remain separately recorded.

## Complete Journey rights and access

The selected operational edition is `completejourney` 1.1.1 (CRAN publication 2025-11-26) linked to The Complete Journey / Complete Journey 2.0 provider family. The official CRAN tarball, manual, user guide, provider page, and provider terms were acquired and verified. The tarball contains {len(tar_members)} entries and {len(rda_members)} built-in `.rda` objects. The full upstream provider transactions/promotions payload was not acquired because the current route requires interactive form submission, terms consent, and an emailed link.

The rights decision keeps seven layers separate: public-but-gated provider availability; provider access not executed; package CC0 scoped only to the package; no separate paper license; upstream dataset rights restricted by provider terms; local execution available for the package/built-ins but not established for the unacquired full payload; and no general upstream redistribution permission. Package CC0 is not propagated to upstream data.

## Locator and PDF-preflight results

All emitted locators are verified non-page section/table/figure/abstract anchors. Page anchors: 0. Structural sidecars: {len(sidecar_manifest)} total — {preflight_counts['PASS']} PASS, {preflight_counts['UNAVAILABLE']} UNAVAILABLE, {preflight_counts['FAIL']} FAIL. The sole UNAVAILABLE result is `li2023_repetition_exploration.pdf` because of an xref-coverage advisory; page anchors are prohibited and its non-page Introduction/analysis locator is used. No quote was needed.

## Failed routes, degradation, and residual constraints

- ACM direct automated retrieval for Jannach–Chen returned HTTP 403. No bypass was attempted; the exact official publisher HTML was inspected through the lawful browser route, while only official institutional identity metadata was stored locally.
- The Liu 2009 exact full text remained unavailable through a lawful open route. A scripted NYCU fetch returned a challenge page and an ETH proceedings file was only a table of contents; both were rejected as artifacts. Service degradation is not treated as evidence of absence.
- The frozen R3 locator for ALDI resolved to an unrelated Web3 paper. That payload was rejected and replaced with the exact author-hosted PolyU paper; the correction exists only in this R4 overlay, preserving frozen R3 bytes.
- The frozen R3 locator for the 2025 inherited-popularity-bias paper resolved to an unrelated multimodal target-selection paper. That payload was rejected and replaced with the exact same-work arXiv manuscript `2510.11402`; the correction likewise exists only in R4.
- The frozen R3 locator for SEMCo resolved to an unrelated mathematics paper. That payload was rejected and replaced with the exact same-work arXiv manuscript `2604.12990`; the correction likewise exists only in R4.
- Initial system-Python PDF preflight lacked `pypdf` and hit the ARS tool's POSIX-only output writer on Windows. The unmodified ARS v0.1.26 preflight was rerun with the bundled workspace Python, and stdout JSON was retained mechanically.
- The Complete Journey full provider payload remains unacquired; this is an explicit access state, not a rights inference or a package-to-dataset license propagation.
- R4-blocking unresolved targets: 0. The bounded substitution and access restrictions above remain mandatory downstream constraints.

## Phase boundary

R5 was not performed. Phase 3 synthesis was not performed. H1–H4 remain NOT_RUN. Stage 2 production citations remain NOT_AUTHORIZED.
"""
    (acq / "r4_acquisition_report.md").write_text(report, encoding="utf-8", newline="\n")

    generation_receipt = validate_bundle(acq, require_handoff=False)
    if generation_receipt["result"] != "PASS":
        raise RuntimeError("R4 generation validation failed: " + json.dumps(generation_receipt["failures"], ensure_ascii=False))

    output_manifest = [file_receipt(acq / name, workspace) for name in FIXED_NONSELF_OUTPUTS]
    all_source_artifacts = [file_receipt(path, workspace) for path in sorted(artifacts_dir.iterdir()) if path.is_file()]
    all_sidecars = [file_receipt(path, workspace) for path in sorted(sidecars_dir.iterdir()) if path.is_file()]
    handoff = {
        "schema_version": "stage1b-r1-r4-handoff-1.0",
        "handoff_type": "R4_SOURCE_ACQUISITION_AND_LOCATOR_COMPLETION",
        "project": "hybrid-recsys-v5",
        "stage": "1B",
        "round": "R1",
        "step": "R4",
        "runtime_lock": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
        "ars_codex_version": ARS_VERSION,
        "research_cutoff": RESEARCH_CUTOFF,
        "completed_at": ACCESSED_AT,
        "verdict": "PASS",
        "verdict_scope": "PASS authorizes only R5 claim-map rebuild and Phase 3 synthesis. It does not seal Stage 1B or authorize Stage 2 production citations.",
        "r5_authorized": True,
        "stage2_production_citations_authorized": False,
        "counts": {
            "core": {"scholarly": 23, "operational_families": 1, "total": 24, "acquired": 24, "content_verified": 24, "locator_ready": 24},
            "queue": {"total": 13, "terminal_resolved": 13, "dispositions": dict(queue_counts)},
            "claims": claim_map["counts"],
            "pdf_preflight": {"total": len(sidecar_manifest), **{key.lower(): value for key, value in preflight_counts.items()}},
            "local_source_artifacts": len(all_source_artifacts),
            "production_ready": 0,
        },
        "substitutions": [{"target_source_key": "liu2009_hybrid_seq_cf", "replacement_doi": "10.1109/ICEBE.2007.6", "decision": "ACCEPTED_FOR_BOUNDED_HYBRID_METHOD_EVIDENCE", "forbidden_scope": "No exact 2009 journal-specific detail or numerical result."}],
        "unresolved_blockers": [],
        "residual_constraints": ["Jannach official full HTML remains remote-only.", "Complete Journey full provider payload was not acquired through the interactive form.", "li2023_repetition_exploration page anchors remain prohibited.", "Liu replacement scope remains bounded."],
        "complete_journey_result": {"decision": complete_rights["decision"], "package": "completejourney 1.1.1", "provider_full_payload_acquired": False, "package_local_execution": True, "upstream_redistribution_permission": False, "license_scope_assertion": complete_rights["license_scope_assertion"]},
        "validation_receipt": generation_receipt,
        "output_manifest": output_manifest,
        "source_artifact_manifest": all_source_artifacts,
        "pdf_preflight_manifest": all_sidecars,
        "self_hash_policy": "r4_handoff.json excludes its own hash; every other fixed handoff output, every local source artifact, and every PDF-preflight sidecar is byte-counted and SHA-256 bound here.",
        "phase_boundary": PHASE_BOUNDARY,
    }
    dump(acq / "r4_handoff.json", handoff)

    final_receipt = validate_bundle(acq, require_handoff=True)
    if final_receipt["result"] != "PASS":
        raise RuntimeError("R4 final validation failed: " + json.dumps(final_receipt["failures"], ensure_ascii=False))
    print(json.dumps({
        "verdict": "PASS",
        "r5_authorized": True,
        "core": handoff["counts"]["core"],
        "queue": handoff["counts"]["queue"],
        "claims": handoff["counts"]["claims"],
        "pdf_preflight": handoff["counts"]["pdf_preflight"],
        "outputs": output_manifest + [file_receipt(acq / "r4_handoff.json", workspace)],
        "validation": {"result": final_receipt["result"], "checks_run": final_receipt["checks_run"], "checks_failed": final_receipt["checks_failed"], "receipt_payload_sha256": final_receipt["receipt_payload_sha256"]},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
