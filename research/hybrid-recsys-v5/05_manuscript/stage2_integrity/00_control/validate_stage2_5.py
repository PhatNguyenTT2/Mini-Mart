#!/usr/bin/env python3
"""Replay-validate the complete bounded Stage 2.5 integrity package."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE25 = REPO_ROOT / "research/hybrid-recsys-v5/05_manuscript/stage2_integrity"
ARS_ROOT = Path(
    "C:/Users/ACER/.codex/plugins/cache/ars-codex/ars-codex/0.1.26/"
    "skills/academic-research-suite/ars"
)
RUNTIME = STAGE25 / ".runtime"
MANUSCRIPT = STAGE25 / "03_compile/master_draft_stage2_5.tex"
BIBLIOGRAPHY = STAGE25 / "03_compile/refs_stage2_5.bib"
PDF = STAGE25 / "03_compile/master_draft_stage2_5.pdf"
REGISTRY = STAGE25 / "01_claim_registry/claim_registry_stage2_5.json"
COVERAGE = STAGE25 / "01_claim_registry/claim_registry_coverage_stage2_5.json"
INTEGRITY = STAGE25 / "02_integrity/integrity_report_stage2_5.json"
COMPLIANCE = STAGE25 / "02_integrity/compliance_report_stage2_5.json"
DRIFT = STAGE25 / "02_integrity/claim_strength_drift_findings_stage2_5.json"
PASSPORT = STAGE25 / "04_handoff/stage2_5_material_passport.json"
STATE = STAGE25 / "04_handoff/stage2_5_state.json"
HANDOFF = STAGE25 / "04_handoff/stage2_5_handoff.json"
HASH_MANIFEST = STAGE25 / "04_handoff/artifact_hash_manifest_stage2_5.json"
TRANSIENT_SOURCE_MAP = RUNTIME / "stage2_5_evidence_source_map.json"
PUBLIC_AGGREGATE = Path(
    "E:/UIT/cv/materialized-experiments/hybrid-recsys-v5/ai-service-v2/r8/"
    "public-data-protocol-validation/attempt-003/aggregate_metrics.json"
)

EXPECTED = {
    MANUSCRIPT: "d3baf0deda40e7b51735f75213a36ef07cdf78b2e45ba830c92dc1524ea6624e",
    BIBLIOGRAPHY: "eb1dfd3264dc8cc1dd442945c4ba54ad72c6e966d1077aa0d9702ce3593c7d43",
    PDF: "2f95d39e7f0dd0bb107e973d4cd180fe8b94567bbf6ba81def18c6541f2d1f86",
    REGISTRY: "31440b3a0f262ce7b1a0db028ad8681c6c2b31070843d202d5f1ac477247db89",
    COVERAGE: "0d24e6db51d9c8f811ba15ea080a82fe11db5755c36a74c0b86c927b596c6f6e",
    PUBLIC_AGGREGATE: "512fb8ad8862f5e677ec18f369d310ae58c9d6f3c4f7b2e79c17ede389930c17",
}

SOURCE_PATHS = {
    "liu2009_hybrid_seq_cf": REPO_ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/acquisition/source_artifacts/liu2009_nycu_identity_abstract.html",
    "gusak2025_time_split": REPO_ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/acquisition/source_artifacts/gusak2025_time_split.pdf",
    "petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo": REPO_ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/lanes/L3/source_artifacts/petrov2022_bert4rec_replicability_arxiv.pdf",
    "rendle2009_bpr": REPO_ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/acquisition/source_artifacts/rendle2009_bpr.pdf",
    "mansouri2026_repeat_explore_lightgcn": REPO_ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/lanes/L3/source_artifacts/mansouri2026_repeat_explore.pdf",
    "hou2022_unisrec": REPO_ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/phase2_investigation/acquisition/source_artifacts/hou2022_unisrec.pdf",
}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    folded: set[str] = set()
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key: {key}")
        canonical = key.casefold()
        if canonical in folded:
            raise ValueError(f"case-colliding JSON key: {key}")
        folded.add(canonical)
        output[key] = value
    return output


def strict_load(path: Path) -> Any:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM forbidden: {path}")
    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")),
    )


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_source(path: Path) -> str:
    if path.suffix.lower() == ".html":
        parser = VisibleTextParser()
        parser.feed(path.read_text(encoding="utf-8"))
        return " ".join(unescape(" ".join(parser.parts)).split())
    sys.path.insert(0, str(RUNTIME))
    from pypdf import PdfReader

    return " ".join(
        " ".join((page.extract_text() or "").split()) for page in PdfReader(path).pages
    )


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: expected {expected!r}, got {actual!r}")


def validate_json_population() -> int:
    count = 0
    for path in STAGE25.rglob("*.json"):
        if RUNTIME in path.parents:
            continue
        strict_load(path)
        count += 1
    return count


def validate_claim_coverage() -> None:
    coverage_module = load_module("ars_claim_coverage", ARS_ROOT / "scripts/claim_registry_coverage.py")
    replay = coverage_module.build_report(MANUSCRIPT.read_bytes(), REGISTRY.read_bytes())
    persisted = strict_load(COVERAGE)
    assert_equal(replay, persisted, "claim registry coverage replay")
    assert_equal(persisted["candidate_unregistered_count"], 0, "claim coverage gaps")


def validate_evidence_rows(integrity: dict[str, Any]) -> None:
    evidence_module = load_module("ars_evidence_rows", ARS_ROOT / "scripts/evidence_rows.py")
    rows = integrity["phases"]["E_claims"]["evidence_rows"]
    assert_equal(len(rows), 19, "evidence row count")
    assert_equal(len({row["claim"]["claim_id"] for row in rows}), 19, "evidence claim count")
    source_map = {slug: extract_source(path) for slug, path in SOURCE_PATHS.items()}
    source_artifact_hashes = {slug: sha256(path) for slug, path in SOURCE_PATHS.items()}
    for row in rows:
        slug = row["source"]["ref_slug"]
        if slug:
            if slug not in SOURCE_PATHS:
                raise RuntimeError(f"unknown evidence source: {slug}")
            assert_equal(
                row["source"]["source_artifact_sha256"],
                source_artifact_hashes[slug],
                f"evidence source artifact hash {row['row_id']}",
            )
        evidence_module.validate(row, source_map.get(slug) if slug else None)
    registry = strict_load(REGISTRY)
    selected = {
        row["claim_id"]
        for row in registry["claims"]
        if row["selection_tier"] in {"HIGH-IMPACT", "RANDOM", "TOP-UP"}
    }
    assert_equal({row["claim"]["claim_id"] for row in rows}, selected, "selected claim/evidence set")


def validate_compliance(report: dict[str, Any]) -> None:
    sys.path.insert(0, str(RUNTIME))
    import jsonschema

    schema = strict_load(ARS_ROOT / "shared/compliance_report.schema.json")
    errors = sorted(
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
        ).iter_errors(report),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise RuntimeError("compliance schema errors: " + "; ".join(error.message for error in errors))
    assert_equal(report["mode"], "primary_research", "compliance mode")
    assert_equal(report["prisma_trAIce"], None, "PRISMA-trAIce applicability")
    assert_equal(report["raise"]["mode"], "principles_only", "RAISE mode")


def validate_drift(report: dict[str, Any]) -> None:
    sys.path.insert(0, str(RUNTIME))
    import jsonschema

    schema = strict_load(ARS_ROOT / "shared/contracts/revision/claim_strength_drift_findings.schema.json")
    jsonschema.Draft202012Validator(schema).validate(report)
    assert_equal(report["status"], "skipped_no_revision_evidence", "E6 status")
    assert_equal(report["findings"], [], "E6 findings")


def validate_passport(passport: dict[str, Any]) -> None:
    sys.path.insert(0, str(RUNTIME))
    import jsonschema

    provenance_schema = strict_load(ARS_ROOT / "shared/contracts/passport/experiment_provenance_entry.schema.json")
    manifest_schema = strict_load(ARS_ROOT / "shared/contracts/passport/claim_intent_manifest.schema.json")
    alignment_schema = strict_load(ARS_ROOT / "shared/contracts/passport/experiment_alignment_result.schema.json")
    for row in passport["experiment_provenance"]:
        jsonschema.Draft202012Validator(provenance_schema).validate(row)
    for row in passport["claim_intent_manifests"]:
        jsonschema.Draft202012Validator(manifest_schema).validate(row)
    for row in passport["experiment_alignment_results"]:
        jsonschema.Draft202012Validator(
            alignment_schema,
            format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
        ).validate(row)
    ids = [row["experiment_id"] for row in passport["experiment_provenance"]]
    assert_equal(
        ids,
        [
            "ais-r8-p3-public-validation-attempt-003",
            "EXP-REF-REPRO",
            "EXP-V5-HARMONIZED",
            "EXP-EXTERNAL-VALIDITY",
        ],
        "experiment provenance IDs",
    )
    manifest = passport["claim_intent_manifests"][0]
    claim = next(row for row in manifest["claims"] if row["claim_id"] == "C-009")
    assert_equal(claim["planned_experiment_ids"], [ids[0]], "C-009 experiment binding")
    assert_equal(passport["experiment_alignment_results"][0]["alignment_verdict"], "ALIGNED", "experiment alignment")
    required_note = "This check verifies disclosure and claim-to-provenance fidelity. It does not judge whether the experiment was correctly designed, run, statistically adequate, or reproducible by ARS."
    assert_equal(passport["experiment_alignment_scope_note"], required_note, "experiment alignment disclaimer")


def validate_citations(draft: str, bib: str) -> None:
    cite_occurrences = re.findall(r"\\cite\{([^}]+)\}", draft)
    cite_keys = [item.strip() for group in cite_occurrences for item in group.split(",")]
    bib_keys = re.findall(r"(?m)^@\w+\{([^,\s]+),", bib)
    ref_markers = re.findall(r"<!--ref:([^>]+)-->", draft)
    anchor_markers = re.findall(r"<!--anchor:[^>]+-->", draft)
    assert_equal(len(cite_keys), 61, "citation occurrence count")
    assert_equal(len(ref_markers), 61, "reference marker count")
    assert_equal(len(anchor_markers), 61, "anchor marker count")
    assert_equal(set(cite_keys), set(bib_keys), "citation/bibliography key set")
    assert_equal(set(ref_markers), set(bib_keys), "marker/bibliography key set")
    assert_equal(len(bib_keys), 35, "bibliography entry count")


def validate_manuscript_boundaries(draft: str) -> None:
    forbidden_literals = ["1,380", "0.4940", "0.8507", "0.2768"]
    for literal in forbidden_literals:
        if literal in draft:
            raise RuntimeError(f"stale literal in manuscript: {literal}")
    prohibited = [
        r"\bstate-of-the-art\b",
        r"\boutperforms?\b",
        r"\bsuperior(?:ity)?\b",
        r"\bproves?\b",
        r"production effectiveness",
        r"causal improvement",
    ]
    for pattern in prohibited:
        if re.search(pattern, draft, flags=re.IGNORECASE):
            raise RuntimeError(f"blocked claim language in manuscript: {pattern}")
    required_boundaries = [
        "descriptive protocol evidence only",
        "The proposed Hybrid has not been admitted to the paper result set",
        "does not yet answer whether the proposed",
    ]
    for phrase in required_boundaries:
        if phrase not in " ".join(draft.split()):
            raise RuntimeError(f"missing empirical boundary: {phrase}")


def validate_numeric_report(report: dict[str, Any]) -> None:
    assert_equal(report["claims_checked"], 9, "data checks")
    assert_equal(report["verified"], 9, "data verified")
    aggregate = strict_load(PUBLIC_AGGREGATE)
    ndcg = aggregate["metrics"]["ndcg@10"]
    mean = sum(ndcg["bpr_values"]) / len(ndcg["bpr_values"])
    assert math.isclose(mean, ndcg["bpr_mean"], abs_tol=1e-15)
    assert_equal(aggregate["seed_order"], [42, 2027, 31415], "public seed order")


def validate_pdf() -> None:
    sys.path.insert(0, str(RUNTIME))
    from pypdf import PdfReader

    assert_equal(len(PdfReader(PDF).pages), 13, "PDF page count")
    compile_report = strict_load(STAGE25 / "02_integrity/compile_render_audit_stage2_5.json")
    assert_equal(compile_report["compile_status"], "PASS", "compile status")
    assert_equal(compile_report["rendered_page_inspection"]["pages_checked"], 13, "rendered pages checked")
    assert_equal(compile_report["rendered_page_inspection"]["artifact_operation_marker_runs"], 1, "PDF operation marker count")


def validate_hash_manifest() -> None:
    manifest = strict_load(HASH_MANIFEST)
    rows = manifest["artifacts"]
    assert_equal(len(rows), manifest["artifact_count"], "artifact manifest count")
    for row in rows:
        path = REPO_ROOT / row["path"]
        assert_equal(path.stat().st_size, row["bytes"], f"artifact bytes {row['path']}")
        assert_equal(sha256(path), row["sha256"], f"artifact hash {row['path']}")


def main() -> None:
    sys.path.insert(0, str(RUNTIME))
    for path, expected in EXPECTED.items():
        assert_equal(sha256(path), expected, f"locked hash {path}")
    json_count = validate_json_population()
    validate_claim_coverage()
    integrity = strict_load(INTEGRITY)
    validate_evidence_rows(integrity)
    validate_compliance(strict_load(COMPLIANCE))
    validate_drift(strict_load(DRIFT))
    validate_passport(strict_load(PASSPORT))
    draft = MANUSCRIPT.read_text(encoding="utf-8")
    bib = BIBLIOGRAPHY.read_text(encoding="utf-8")
    validate_citations(draft, bib)
    validate_manuscript_boundaries(draft)
    validate_numeric_report(strict_load(STAGE25 / "02_integrity/data_fidelity_audit_stage2_5.json"))
    validate_pdf()

    reference_report = strict_load(STAGE25 / "02_integrity/reference_verification_stage2_5.json")
    citation_report = strict_load(STAGE25 / "02_integrity/citation_context_audit_stage2_5.json")
    originality = strict_load(STAGE25 / "02_integrity/originality_audit_stage2_5.json")
    failures = strict_load(STAGE25 / "02_integrity/ai_failure_mode_checklist_stage2_5.json")
    assert_equal((reference_report["checked"], reference_report["passed"]), (35, 35), "reference audit")
    assert_equal((citation_report["sampled"], citation_report["verified"]), (19, 19), "citation context audit")
    assert originality["coverage_percent"] >= 30.0
    assert_equal(originality["verdict"], "ORIGINAL_SEARCH_BOUNDED", "originality verdict")
    assert_equal(failures["suspected"], 0, "suspected AI failure modes")
    assert_equal(failures["blocking"], False, "AI failure-mode block")
    assert_equal(integrity["verdict"], "PASS_WITH_CONDITIONS", "integrity verdict")
    assert_equal(integrity["overall_issues"], {"SERIOUS": 0, "MEDIUM": 0, "MINOR": 1}, "issue counts")
    assert_equal(strict_load(STATE)["status"], "STAGE2_5_PASS_AWAITING_USER_CONFIRMATION", "state checkpoint")
    assert_equal(strict_load(HANDOFF)["next_gate"]["automatic_dispatch_authorized"], False, "Stage 3 automatic dispatch")
    validate_hash_manifest()

    print("stage2_5_validation=PASS")
    print(f"strict_json_files={json_count}")
    print("references=35/35")
    print("citation_contexts=19/61")
    print("numeric_data_surfaces=9/9")
    print("originality=24/74")
    print("selected_claims=19/19")
    print("pdf_pages=13")
    print("checkpoint=STAGE2_5_PASS_AWAITING_USER_CONFIRMATION")


if __name__ == "__main__":
    main()
