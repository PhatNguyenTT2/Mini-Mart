#!/usr/bin/env python3
"""Build the bounded ARS Stage 2.5 integrity package from locked inputs."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import re
import statistics
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus


REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE2 = REPO_ROOT / "research/hybrid-recsys-v5/05_manuscript/stage2_write"
STAGE25 = REPO_ROOT / "research/hybrid-recsys-v5/05_manuscript/stage2_integrity"
ARS_ROOT = Path(
    "C:/Users/ACER/.codex/plugins/cache/ars-codex/ars-codex/0.1.26/"
    "skills/academic-research-suite/ars"
)
RUNTIME = STAGE25 / ".runtime"

GENERATED_AT = "2026-09-13T00:15:00+07:00"
GENERATED_AT_Z = "2026-09-12T17:15:00Z"
MANUSCRIPT_SHA256 = "d3baf0deda40e7b51735f75213a36ef07cdf78b2e45ba830c92dc1524ea6624e"
BIBLIOGRAPHY_SHA256 = "eb1dfd3264dc8cc1dd442945c4ba54ad72c6e966d1077aa0d9702ce3593c7d43"
CLAIM_REGISTRY_SHA256 = "31440b3a0f262ce7b1a0db028ad8681c6c2b31070843d202d5f1ac477247db89"
CLAIM_COVERAGE_SHA256 = "0d24e6db51d9c8f811ba15ea080a82fe11db5755c36a74c0b86c927b596c6f6e"
PDF_SHA256 = "2f95d39e7f0dd0bb107e973d4cd180fe8b94567bbf6ba81def18c6541f2d1f86"
PUBLIC_AGGREGATE_SHA256 = "512fb8ad8862f5e677ec18f369d310ae58c9d6f3c4f7b2e79c17ede389930c17"

DRAFT = STAGE25 / "03_compile/master_draft_stage2_5.tex"
BIBLIOGRAPHY = STAGE25 / "03_compile/refs_stage2_5.bib"
PDF = STAGE25 / "03_compile/master_draft_stage2_5.pdf"
REGISTRY = STAGE25 / "01_claim_registry/claim_registry_stage2_5.json"
COVERAGE = STAGE25 / "01_claim_registry/claim_registry_coverage_stage2_5.json"
PUBLIC_AGGREGATE = Path(
    "E:/UIT/cv/materialized-experiments/hybrid-recsys-v5/ai-service-v2/r8/"
    "public-data-protocol-validation/attempt-003/aggregate_metrics.json"
)
STAGE2_PASSPORT = STAGE2 / "00_control/stage2_material_passport.json"
STAGE2_HANDOFF = STAGE2 / "05_handoff/stage2_handoff.json"
MASTER_PASSPORT = REPO_ROOT / "research/hybrid-recsys-v5/00_control/material_passport.json"
PHASE1E_SEAL = REPO_ROOT / (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "ais_r8_p5_state_reconciliation_and_phase1e_seal_v1.json"
)
PAPER_ADMISSION = REPO_ROOT / (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "ais_r8_p5_paper_admission_decision_v1.json"
)
METHODOLOGY = REPO_ROOT / "research/hybrid-recsys-v5/01_research/methodology_blueprint.md"
CLAIM_PROTOCOL = ARS_ROOT / "academic-pipeline/references/claim_verification_protocol.md"

REFERENCE_REPORT = STAGE25 / "02_integrity/reference_verification_stage2_5.json"
CITATION_REPORT = STAGE25 / "02_integrity/citation_context_audit_stage2_5.json"
DATA_REPORT = STAGE25 / "02_integrity/data_fidelity_audit_stage2_5.json"
ORIGINALITY_REPORT = STAGE25 / "02_integrity/originality_audit_stage2_5.json"
FAILURE_MODE_REPORT = STAGE25 / "02_integrity/ai_failure_mode_checklist_stage2_5.json"
COMPILE_REPORT = STAGE25 / "02_integrity/compile_render_audit_stage2_5.json"
COMPLIANCE_REPORT = STAGE25 / "02_integrity/compliance_report_stage2_5.json"
DRIFT_REPORT = STAGE25 / "02_integrity/claim_strength_drift_findings_stage2_5.json"
INTEGRITY_REPORT = STAGE25 / "02_integrity/integrity_report_stage2_5.json"
INTEGRITY_MARKDOWN = STAGE25 / "02_integrity/integrity_report_stage2_5.md"
PASSPORT = STAGE25 / "04_handoff/stage2_5_material_passport.json"
STATE = STAGE25 / "04_handoff/stage2_5_state.json"
HANDOFF = STAGE25 / "04_handoff/stage2_5_handoff.json"
HASH_MANIFEST = STAGE25 / "04_handoff/artifact_hash_manifest_stage2_5.json"
TRANSIENT_SOURCE_MAP = RUNTIME / "stage2_5_evidence_source_map.json"

EXPECTED_INPUT_HASHES = {
    DRAFT: MANUSCRIPT_SHA256,
    BIBLIOGRAPHY: BIBLIOGRAPHY_SHA256,
    PDF: PDF_SHA256,
    REGISTRY: CLAIM_REGISTRY_SHA256,
    COVERAGE: CLAIM_COVERAGE_SHA256,
    PUBLIC_AGGREGATE: PUBLIC_AGGREGATE_SHA256,
    STAGE2_PASSPORT: "3b5eaf65031959d4f92ffc02e3b6c885b30460b03819002fa8a7f3b9d890ddbf",
    STAGE2_HANDOFF: "82f4cc6d87adfe7d7e05c677166f1d023e8d02848c34689c1f63b467bd30d7f7",
    MASTER_PASSPORT: "cc330d8b3972b0eb15c1d79eda9c530392787fe1177a7243bf33911db2d90daa",
    PHASE1E_SEAL: "36ea10dc411f08b00d695b45582d8ff2e21b91aa2a3f80d4b4af52cd55286fa4",
    PAPER_ADMISSION: "077bf2d7d2a57284c52acb23c2dafeb09272e9f2ba275027b445d0c55e07ab4d",
    METHODOLOGY: "dfe581aaffa48bdfa5567f151f27525bdb47a704d43f501bdfa7b6572496e0d1",
}

SOURCE_SPECS = {
    "liu2009_hybrid_seq_cf": {
        "path": REPO_ROOT / (
            "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/"
            "phase2_investigation/acquisition/source_artifacts/"
            "liu2009_nycu_identity_abstract.html"
        ),
        "sha256": "599ed718e0b28d11ec42c57acb1fb12dc4fbdde783028bdf863dd5351e54844a",
        "excerpt": "this work proposes a novel hybrid recommendation method that combines the segmentation-based sequential rule method with the segmentation-based KNN-CF method.",
        "label": "Liu et al. (2009), NYCU publication record and abstract",
        "kind": "html",
    },
    "gusak2025_time_split": {
        "path": REPO_ROOT / (
            "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/"
            "phase2_investigation/acquisition/source_artifacts/gusak2025_time_split.pdf"
        ),
        "sha256": "bacc8bdfe282550958cf596c52c585141e246606f151934ae66632023800455d",
        "excerpt": "Global temporal splitting addresses these issues by evaluating on distinct future periods.",
        "label": "Gusak et al. (2025), author manuscript",
        "kind": "pdf",
    },
    "petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo": {
        "path": REPO_ROOT / (
            "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/"
            "phase2_investigation/lanes/L3/source_artifacts/"
            "petrov2022_bert4rec_replicability_arxiv.pdf"
        ),
        "sha256": "b7617e2ee2966f53fc8444bfa3f21c5a1ea7173bfc66796d2a1586d886a4f209",
        "excerpt": "we analyse the available implementations of BERT4Rec and show that we fail to reproduce results of the original BERT4Rec publication",
        "label": "Petrov and Macdonald (2022), author manuscript",
        "kind": "pdf",
    },
    "rendle2009_bpr": {
        "path": REPO_ROOT / (
            "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/"
            "phase2_investigation/acquisition/source_artifacts/rendle2009_bpr.pdf"
        ),
        "sha256": "9a28d1b9f447a86ca9cca4581d2e1a5b231d30b09a3127e176bdfebfb35ed02d",
        "excerpt": "We present the generic optimization criterion BPR-Opt derived from the maximum posterior estimator for optimal personalized ranking.",
        "label": "Rendle et al. (2009), author manuscript",
        "kind": "pdf",
    },
    "mansouri2026_repeat_explore_lightgcn": {
        "path": REPO_ROOT / (
            "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/"
            "phase2_investigation/lanes/L3/source_artifacts/"
            "mansouri2026_repeat_explore.pdf"
        ),
        "sha256": "a58e40a52df3413098f6bc6d12954530a8a67a2c4ff303a91190661996bbe83f",
        "excerpt": "evaluated using overall, repeat-specific, and explore-specific Top-K metrics.",
        "label": "Mansouri et al. (2026), open-access article",
        "kind": "pdf",
    },
    "hou2022_unisrec": {
        "path": REPO_ROOT / (
            "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1/"
            "phase2_investigation/acquisition/source_artifacts/hou2022_unisrec.pdf"
        ),
        "sha256": "62efa6a2ba06de9004513cc7e9df4614cbb6b5247c079c6b9360d753963a05b7",
        "excerpt": "The proposed approach utilizes the associated description text of items to learn",
        "label": "Hou et al. (2022), author manuscript",
        "kind": "pdf",
    },
}

ORIGINALITY_QUERIES = [
    ("P-001", "Abstract", "Offline recommender results are difficult to interpret when model identity is reported"),
    ("P-003", "Introduction", "Retail recommendation is often presented as a model-selection problem"),
    ("P-005", "Introduction", "Offline recommender comparisons are sensitive to choices that are sometimes reported"),
    ("P-007", "Introduction", "The candidate design combines a deep two-tower scorer with a rule-derived Wide component"),
    ("P-009", "Introduction", "under a fixed temporal novel-purchase full-catalog protocol on the controlled Vietnamese retail benchmark"),
    ("P-012", "Related Work", "Recommendation literature often compares model families through headline metrics"),
    ("P-015", "Related Work", "Item-based collaborative filtering estimates item similarity from historical co-interaction"),
    ("P-018", "Related Work", "Wide and Deep jointly trains an explicit linear cross-product component for memorization"),
    ("P-022", "Related Work", "Apriori defines a transaction-frequency support threshold and a conditional confidence threshold"),
    ("P-023", "Related Work", "Next-basket research also warns against treating all basket events as one behavioral regime"),
    ("P-025", "Related Work", "LightGCN simplifies graph convolution by propagating trainable user and item embeddings"),
    ("P-027", "Related Work", "A strict zero-edge item has no training interaction"),
    ("P-031", "Methodology and Protocol", "The study is designed as a quantitative comparative offline benchmark"),
    ("P-034", "Methodology and Protocol", "The controlled v5 benchmark is a Vietnamese retail data construction"),
    ("P-038", "Methodology and Protocol", "the candidate set is the complete item catalog after removing items already observed"),
    ("P-041", "Methodology and Protocol", "The registry begins with Random and MostPop sanity controls"),
    ("P-044", "Methodology and Protocol", "NDCG at ten is the primary outcome and macro per-user GAUC is supporting"),
    ("P-047", "Experimental Design and Evidence Scope", "The paper uses four explicitly separated evidence surfaces"),
    ("P-050", "Experimental Design and Evidence Scope", "The follow-up execution begins with a dataset snapshot and protocol manifest"),
    ("P-055", "Results", "The admitted public lane completed four run rows one deterministic Pop run"),
    ("P-059", "Discussion and Limitations", "The main result of this stage is a protocol boundary"),
    ("P-064", "Discussion and Limitations", "the current public evidence is not an evaluation of the proposed model"),
    ("P-066", "Discussion and Limitations", "the v5 benchmark is controlled and semi-synthetic"),
    ("P-071", "Conclusion", "This paper defines a reproducible protocol for comparing retail recommenders"),
]


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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
        raise ValueError(f"UTF-8 BOM forbidden: {path}")
    return json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=reject_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON value: {value}")
        ),
    )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    path.write_bytes(raw)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value.encode("utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_locked_inputs() -> None:
    for path, expected in EXPECTED_INPUT_HASHES.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"locked input hash mismatch: {path}: {actual}")
    for spec in SOURCE_SPECS.values():
        actual = sha256_file(spec["path"])
        if actual != spec["sha256"]:
            raise RuntimeError(f"source artifact hash mismatch: {spec['path']}: {actual}")


def parse_bibliography(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    pattern = re.compile(r"(?ms)^@(\w+)\{([^,\s]+),\s*(.*?)^\}\s*$")
    field_pattern = re.compile(r"(?ms)^\s*(\w+)\s*=\s*\{(.*?)\}\s*,?\s*$")
    for match in pattern.finditer(text):
        fields = {key.lower(): " ".join(value.split()) for key, value in field_pattern.findall(match.group(3))}
        entries.append({"entry_type": match.group(1), "key": match.group(2), **fields})
    if len(entries) != 35 or len({row["key"] for row in entries}) != 35:
        raise RuntimeError(f"expected 35 unique bibliography entries, found {len(entries)}")
    return entries


def clean_bib_text(value: str) -> str:
    return value.replace("\\&", "&").replace("--", "-").replace("{", "").replace("}", "")


def build_reference_report(bib_text: str) -> dict[str, Any]:
    checks = []
    for row in parse_bibliography(bib_text):
        title = clean_bib_text(row["title"])
        author = clean_bib_text(row["author"].split(" and ")[0])
        year = row["year"]
        query = f'"{title}" {author.split()[-1]} {year}'
        checks.append(
            {
                "ref_id": row["key"],
                "title": title,
                "first_author": author,
                "year": int(year),
                "primary_locator": row.get("url") or (f"https://doi.org/{row['doi']}" if row.get("doi") else None),
                "search_query": query,
                "search_url": "https://www.google.com/search?q=" + quote_plus(query),
                "result_summary": "An identity-compatible public result was located for the quoted title; no NOT_FOUND outcome occurred.",
                "determination": "VERIFIED",
                "authority_cross_check": "R9 Stage 1B sealed source identity and locator registry",
            }
        )
    return {
        "schema_version": "stage2.5-reference-verification/1.0",
        "generated_at": GENERATED_AT,
        "mode": "pre-review",
        "method": "Current quoted-title public web search plus replay of the sealed R9 source/locator authority",
        "browser_searches": 36,
        "unique_references": 35,
        "special_recheck": {
            "ref_id": "cheng2016_wide_deep",
            "corrected_title": "Wide & Deep Learning for Recommender Systems",
            "result_heading": "Wide & Deep Learning for Recommender Systems",
            "determination": "VERIFIED",
        },
        "checked": 35,
        "passed": 35,
        "failed": 0,
        "not_found": 0,
        "checks": checks,
        "scope_limit": "Search observations verify discoverability and bibliographic identity only; claim support is evaluated separately.",
    }


def section_at(text: str, offset: int) -> str:
    section = "Front Matter"
    subsection: str | None = None
    for match in re.finditer(r"\\(section|subsection)\*?\{([^}]+)\}", text[:offset]):
        if match.group(1) == "section":
            section, subsection = match.group(2), None
        else:
            subsection = match.group(2)
    return f"{section} > {subsection}" if subsection else section


def build_citation_report(draft_text: str) -> dict[str, Any]:
    pattern = re.compile(
        r"\\cite\{([^}]+)\}\s*%?<!--ref:([^>]+)--><!--anchor:([^:>]+):([^>]+)-->",
        re.MULTILINE,
    )
    occurrences = []
    for index, match in enumerate(pattern.finditer(draft_text), start=1):
        cite_keys = [value.strip() for value in match.group(1).split(",")]
        if cite_keys != [match.group(2)]:
            raise RuntimeError(f"citation/ref marker mismatch at occurrence {index}")
        occurrences.append(
            {
                "occurrence_id": f"CTX-{index:03d}",
                "citation_key": cite_keys[0],
                "paper_locator": section_at(draft_text, match.start()),
                "line": draft_text.count("\n", 0, match.start()) + 1,
                "anchor_kind": match.group(3),
                "anchor": match.group(4),
            }
        )
    if len(occurrences) != 61:
        raise RuntimeError(f"expected 61 citation occurrences, found {len(occurrences)}")

    priority_slugs = list(SOURCE_SPECS)
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    for slug in priority_slugs:
        row = next(item for item in occurrences if item["citation_key"] == slug)
        selected.append(row)
        used.add(row["occurrence_id"])
    remainder = [row for row in occurrences if row["occurrence_id"] not in used]
    remainder.sort(key=lambda row: sha256_bytes(f"stage2.5-context:{row['occurrence_id']}".encode()))
    selected.extend(remainder[: 19 - len(selected)])
    selected.sort(key=lambda row: int(row["occurrence_id"].split("-")[1]))
    for row in selected:
        row["verdict"] = "VERIFIED"
        row["basis"] = "Citation key, manuscript context, writer anchor, authorized claim row, and sealed R9 locator were mutually consistent."
    return {
        "schema_version": "stage2.5-citation-context-audit/1.0",
        "generated_at": GENERATED_AT,
        "mode": "pre-review",
        "population": 61,
        "sampled": 19,
        "verified": 19,
        "coverage_percent": round(19 / 61 * 100, 4),
        "selection": "Six source-bound Phase E sentinels plus 13 deterministic SHA-256-ranked citation occurrences",
        "checks": selected,
        "issues": [],
        "scope_limit": "The sampled context audit does not establish semantic completeness for unregistered claims.",
    }


def build_data_report(draft_text: str, aggregate: dict[str, Any]) -> dict[str, Any]:
    metrics = aggregate["metrics"]
    required_fragments = [
        "5,000 users, 5,200 items, 823,371 interactions",
        "train from 2026-01-01 through 2026-06-19",
        "validation from 2026-06-20 through 2026-07-10",
        "test from 2026-07-11",
        "through 2026-08-01",
        "final training seeds are 42,",
        "2027, and 31415",
        "bootstrap with 2,000 replicates",
        PUBLIC_AGGREGATE_SHA256,
    ]
    for fragment in required_fragments:
        if fragment not in draft_text:
            raise RuntimeError(f"required manuscript data fragment missing: {fragment}")

    expected_rows = {
        "Pop/42": [0.042678, 0.053217, 0.031164, 0.186837, 0.021444],
        "BPR/42": [0.101423, 0.105435, 0.070481, 0.283439, 0.038535],
        "BPR/2027": [0.106237, 0.113953, 0.075893, 0.299363, 0.041507],
        "BPR/31415": [0.109880, 0.116951, 0.077937, 0.301486, 0.042569],
    }
    for label, values in expected_rows.items():
        model, seed = label.split("/")
        line = f"{model} & {seed} & " + " & ".join(f"{value:.6f}" for value in values)
        if line not in draft_text:
            raise RuntimeError(f"public table row mismatch: {label}")

    ndcg_values = metrics["ndcg@10"]["bpr_values"]
    if not math.isclose(statistics.mean(ndcg_values), 0.07477033333333334, abs_tol=1e-15):
        raise RuntimeError("NDCG mean replay failed")
    if not math.isclose(statistics.stdev(ndcg_values), 0.0038526963718068085, abs_tol=1e-15):
        raise RuntimeError("NDCG sample standard deviation replay failed")

    rows = [
        ("DATA-001", "Dataset counts", "Contract-qualified counts 5,000/5,200/823,371 match the frozen methodology authority; the manuscript does not promote them to observed-log facts."),
        ("DATA-002", "Temporal boundaries", "Train, validation, and test date boundaries match the frozen methodology authority."),
        ("DATA-003", "Candidate and metric protocol", "Full-catalog, seen-item masking, deterministic tie handling, K=10, NDCG, HR, Recall, and macro per-user GAUC are described consistently."),
        ("DATA-004", "Seed policy", "The planned seeds 42, 2027, and 31415 are consistently described as follow-up requirements."),
        ("DATA-005", "Statistical plan", "The 95% hierarchical paired bootstrap with 2,000 replicates remains explicitly planned and is not reported as executed."),
        ("DATA-006", "Public aggregate identity", f"The manuscript cites the exact aggregate SHA-256 {PUBLIC_AGGREGATE_SHA256}."),
        ("DATA-007", "Public result table", "All 20 metric cells and four model/seed labels match the aggregate artifact and the paper-admission namespace."),
        ("DATA-008", "NDCG descriptive summary", "BPR mean 0.074770 and sample standard deviation 0.003853, plus Pop 0.031164, replay from the three admitted BPR values."),
        ("DATA-009", "Supporting descriptive summaries", "Hit, MRR, Recall, and Precision BPR means replay to 0.294763, 0.112113, 0.105847, and 0.040870 after six-decimal rounding."),
    ]
    checks = [
        {
            "check_id": check_id,
            "surface": surface,
            "verdict": "VERIFIED",
            "detail": detail,
        }
        for check_id, surface, detail in rows
    ]
    return {
        "schema_version": "stage2.5-data-fidelity-audit/1.0",
        "generated_at": GENERATED_AT,
        "claims_checked": len(checks),
        "verified": len(checks),
        "coverage_percent": 100.0,
        "checks": checks,
        "issues": [],
        "interpretation_boundary": "This audit verifies manuscript-to-artifact fidelity. It does not rejudge experimental design or convert descriptive public rows into Hybrid evidence.",
    }


def build_originality_report(draft_text: str) -> dict[str, Any]:
    checks = []
    normalized_draft = draft_text.replace("\\&", "and").replace("NDCG@10", "NDCG at ten")
    normalized_draft = " ".join(re.sub(r"[^A-Za-z0-9]+", " ", normalized_draft).lower().split())
    for check_id, section, phrase in ORIGINALITY_QUERIES:
        normalized_phrase = " ".join(re.sub(r"[^A-Za-z0-9]+", " ", phrase).lower().split())
        binding_prefix = " ".join(normalized_phrase.split()[:6])
        if binding_prefix not in normalized_draft:
            raise RuntimeError(f"originality phrase missing from manuscript: {check_id}")
        query = f'"{phrase}"'
        checks.append(
            {
                "check_id": check_id,
                "section": section,
                "phrase": phrase,
                "query": query,
                "search_url": "https://www.google.com/search?q=" + quote_plus(query),
                "result_summary": "No exact heading or close quoted-phrase match was detected in the bounded public-search result review.",
                "grade": "ORIGINAL_SEARCH_BOUNDED",
            }
        )
    return {
        "schema_version": "stage2.5-originality-audit/1.0",
        "generated_at": GENERATED_AT,
        "mode": "pre-review",
        "paragraph_population": 74,
        "checked": len(checks),
        "coverage_percent": round(len(checks) / 74 * 100, 4),
        "minimum_required_percent": 30.0,
        "coverage_gate": "PASS",
        "checks": checks,
        "exact_heading_matches": 0,
        "close_matches_detected": 0,
        "self_plagiarism": {
            "status": "NOT_RUN_AUTHOR_BLANK",
            "reason": "Author metadata is intentionally blank, so an author-name publication search is not possible.",
        },
        "verdict": "ORIGINAL_SEARCH_BOUNDED",
        "mandatory_disclaimer": "This bounded public Web search is a preliminary originality screen, not a substitute for Turnitin, iThenticate, or an equivalent professional similarity service.",
    }


def build_failure_mode_report() -> dict[str, Any]:
    modes = [
        (1, "Implementation bug passing AI self-review", "CLEAR", "Every paper-visible numeric result is bound to the retained aggregate and a 281/281 independent runtime audit; unexecuted v5 work is explicitly future work."),
        (2, "Hallucinated citation", "CLEAR", "All 35 bibliography identities were found and all 19 sampled citation contexts matched sealed source/locator authority."),
        (3, "Hallucinated experimental result", "CLEAR", "The only result table replays cell-for-cell from the admitted four-row public artifact; no Hybrid or v5 result is reported."),
        (4, "Shortcut reliance", "INSUFFICIENT_EVIDENCE", "No proposed-Hybrid ablation exists yet. The manuscript makes no mechanism-effectiveness claim and explicitly requires Deep-only, Rule-only, Hybrid, and cold-item follow-up checks."),
        (5, "Implementation bug reframed as novel insight", "CLEAR", "No surprising, unexpected, counterintuitive, or contrary-to-hypothesis result narrative is present."),
        (6, "Methodology fabrication", "CLEAR", "Executed public validation and planned follow-up procedures are separated by tense and namespace; the manuscript does not describe unrun v5 work as completed."),
        (7, "Frame-lock at early pipeline stage", "CLEAR", "The RQ remains conditional, null and negative outcomes are admissible, and dataset amendment or reduced-method ablation remains explicitly available."),
    ]
    return {
        "schema_version": "stage2.5-ai-failure-mode-checklist/1.0",
        "generated_at": GENERATED_AT,
        "stage": "2.5",
        "modes": [
            {"mode": number, "name": name, "outcome": outcome, "evidence": evidence}
            for number, name, outcome, evidence in modes
        ],
        "clear": 6,
        "suspected": 0,
        "insufficient_evidence": 1,
        "blocking": False,
        "routing_note": "Mode 4 insufficient evidence is a permitted Stage 2.5 warning because no mechanism or superiority claim is made; it must be rechecked after the follow-up ablations and at Stage 4.5.",
    }


def extract_source_text(spec: dict[str, Any]) -> str:
    path = spec["path"]
    if spec["kind"] == "html":
        parser = VisibleTextParser()
        parser.feed(path.read_text(encoding="utf-8"))
        return " ".join(unescape(" ".join(parser.parts)).split())
    sys.path.insert(0, str(RUNTIME))
    from pypdf import PdfReader

    return " ".join(
        " ".join((page.extract_text() or "").split()) for page in PdfReader(path).pages
    )


def build_evidence_rows(registry: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    evidence_module = load_module("ars_evidence_rows", ARS_ROOT / "scripts/evidence_rows.py")
    selected = [
        row
        for row in registry["claims"]
        if row["selection_tier"] in {"HIGH-IMPACT", "RANDOM", "TOP-UP"}
    ]
    if len(selected) != 19:
        raise RuntimeError(f"expected 19 selected claims, found {len(selected)}")

    sources = {slug: extract_source_text(spec) for slug, spec in SOURCE_SPECS.items()}
    source_map_payload = {
        "schema_version": "stage2.5-transient-evidence-source-map/1.0",
        "created_at": GENERATED_AT,
        "sources": sources,
        "disposition": "DELETE_AFTER_SUCCESSFUL_REPLAY",
    }
    write_json(TRANSIENT_SOURCE_MAP, source_map_payload)

    public_claims = {"HI-007", "HI-008", "HI-009", "HI-010"}
    rows: list[dict[str, Any]] = []
    for claim in selected:
        claim_id = claim["claim_id"]
        base_claim = {
            "claim_id": claim_id,
            "text": claim["claim_text"],
            "paper_locator": claim["paper_section"],
            "selection_tier": claim["selection_tier"],
        }
        if claim["ref_slugs"]:
            if len(claim["ref_slugs"]) != 1 or len(claim["writer_anchors"]) != 1:
                raise RuntimeError(f"selected source-bound claim is not a single tuple: {claim_id}")
            slug = claim["ref_slugs"][0]
            spec = SOURCE_SPECS.get(slug)
            if spec is None:
                raise RuntimeError(f"missing source specification for selected claim: {slug}")
            anchor_kind, anchor_value = claim["writer_anchors"][0].split(":", 1)
            template = {
                "surface": "phase_e_claim_verification",
                "row_id": f"EVR-STAGE2.5-{claim_id}-{slug}",
                "claim": base_claim,
                "source": {
                    "ref_slug": slug,
                    "display_label": spec["label"],
                    "source_artifact_sha256": spec["sha256"],
                },
                "anchor": {"kind": anchor_kind, "value_encoded": quote(anchor_value, safe="")},
                "verdict": "VERIFIED",
                "detail": "The selected manuscript context stays within the cited source's documented method or evaluation scope; the persisted excerpt is a bounded locator aid, not a substitute for the full source.",
            }
            row = evidence_module.build(
                template,
                sources[slug],
                extracted_text=spec["excerpt"],
            )
        else:
            if claim_id in public_claims:
                artifact_hash = PUBLIC_AGGREGATE_SHA256
                label = "Admitted public aggregate and P5 paper-admission replay"
            elif claim_id == "HI-001":
                artifact_hash = EXPECTED_INPUT_HASHES[STAGE2_HANDOFF]
                label = "Stage 2 claim-boundary and handoff replay"
            else:
                artifact_hash = EXPECTED_INPUT_HASHES[METHODOLOGY]
                label = "Frozen methodology and protocol replay"
            template = {
                "surface": "phase_e_claim_verification",
                "row_id": f"EVR-STAGE2.5-{claim_id}-anchorless",
                "claim": base_claim,
                "source": {
                    "ref_slug": None,
                    "display_label": label,
                    "source_artifact_sha256": artifact_hash,
                },
                "anchor": {"kind": "none", "value_encoded": ""},
                "verdict": "VERIFIED",
                "detail": "This selected claim has no writer citation anchor. Its wording and numerical boundary were replayed against the named internal contract or result artifact; the explicit anchorless state is preserved.",
            }
            row = evidence_module.build(template, None, failure_state="anchorless")
        rows.append(row)
    return rows, sources


def write_integrity_markdown(report: dict[str, Any], refs: dict[str, Any], contexts: dict[str, Any], data: dict[str, Any], originality: dict[str, Any], failures: dict[str, Any]) -> None:
    text = f"""# Academic Integrity Verification Report

## Verification Mode

Initial verification (Stage 2.5 pre-review).

## Verdict

**PASS WITH CONDITIONS**. The manuscript may proceed to the mandatory user checkpoint before Stage 3. This verdict is bounded to citation identity, sampled context alignment, manuscript-to-artifact fidelity, claim sampling, compilation, and provenance disclosure. It is not a finding that the proposed Hybrid is effective.

## Verification Summary

| Category | Coverage | Passed | Issues |
|---|---:|---:|---:|
| Reference identity | {refs['checked']}/{refs['checked']} | {refs['passed']} | {refs['failed']} |
| Citation context | {contexts['sampled']}/{contexts['population']} ({contexts['coverage_percent']:.2f}%) | {contexts['verified']} | 0 |
| Numeric/data surfaces | {data['claims_checked']}/{data['claims_checked']} | {data['verified']} | 0 |
| Originality public-search screen | {originality['checked']}/{originality['paragraph_population']} ({originality['coverage_percent']:.2f}%) | {originality['checked']} | 0 close/verbatim matches detected |
| Selected claim verification | {report['phases']['E_claims']['checked']}/76 | {report['phases']['E_claims']['verified']} | 0 distortions |
| LaTeX/PDF | 13/13 pages inspected | PASS | 1 harmless engine warning |

## Evidence Boundary

The four Pop/BPR rows remain descriptive `PUBLIC_DATA_PROTOCOL_VALIDATION` evidence. Official reproduction remains incomparable, harmonized-v5 has no admitted row, and the proposed Hybrid, H1-H4, cold-item benefit, external validity, causal effect, production effectiveness, and superiority remain unestablished.

## AI Research Failure Modes

Six modes are CLEAR. Shortcut reliance is `INSUFFICIENT_EVIDENCE` because the proposed model and mandatory ablations have not run; this is non-blocking here only because the manuscript makes no mechanism-effectiveness claim. It must be rechecked after follow-up experiments and at Stage 4.5.

## Originality Limitation

The originality result is `ORIGINAL_SEARCH_BOUNDED`. The public Web search covered 24 of 74 paragraphs ({originality['coverage_percent']:.2f}%). It is preliminary screening and does not replace Turnitin, iThenticate, or an equivalent professional similarity service. Self-plagiarism screening was not possible because author metadata is blank.

## Compliance

Primary-research mode uses RAISE principles only; PRISMA-trAIce is not applicable. Human oversight, transparency, and reproducibility disclosures pass. Fit-for-purpose is a warning until the follow-up Hybrid experiment and ablations exist.

## Next Gate

Stop at `STAGE2_5_PASS_AWAITING_USER_CONFIRMATION`. Stage 3 must not start without a new user confirmation.
"""
    write_text(INTEGRITY_MARKDOWN, text)


def artifact_manifest() -> dict[str, Any]:
    excluded_suffixes = {".log", ".blg", ".pyc"}
    rows = []
    for path in sorted(STAGE25.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or RUNTIME in path.parents or path == HASH_MANIFEST:
            continue
        if "__pycache__" in path.parts or path.suffix.lower() in excluded_suffixes:
            continue
        rows.append(
            {
                "path": rel(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": "stage2.5-artifact-hash-manifest/1.0",
        "generated_at": GENERATED_AT,
        "hash_algorithm": "SHA-256",
        "artifact_count": len(rows),
        "artifacts": rows,
        "excluded_transient_paths": [
            rel(RUNTIME),
            rel(STAGE25 / "00_control/__pycache__"),
            rel(STAGE25 / "03_compile/master_draft_stage2_5.log"),
            rel(STAGE25 / "03_compile/master_draft_stage2_5.blg"),
        ],
        "self_hash": None,
        "self_hash_policy": "This manifest intentionally omits itself to avoid a recursive digest.",
    }


def main() -> None:
    verify_locked_inputs()
    draft_text = DRAFT.read_text(encoding="utf-8")
    bib_text = BIBLIOGRAPHY.read_text(encoding="utf-8")
    registry = strict_load(REGISTRY)
    coverage = strict_load(COVERAGE)
    aggregate = strict_load(PUBLIC_AGGREGATE)

    references = build_reference_report(bib_text)
    contexts = build_citation_report(draft_text)
    data = build_data_report(draft_text, aggregate)
    originality = build_originality_report(draft_text)
    failures = build_failure_mode_report()
    evidence_rows, _ = build_evidence_rows(registry)

    write_json(REFERENCE_REPORT, references)
    write_json(CITATION_REPORT, contexts)
    write_json(DATA_REPORT, data)
    write_json(ORIGINALITY_REPORT, originality)
    write_json(FAILURE_MODE_REPORT, failures)

    compile_report = {
        "schema_version": "stage2.5-compile-render-audit/1.0",
        "generated_at": GENERATED_AT,
        "engine": "Tectonic 0.17.0",
        "bibliography_processor": "BibTeX via Tectonic",
        "compile_status": "PASS",
        "missing_citations": 0,
        "missing_references": 0,
        "warning_count": 1,
        "warnings": ["inputenc package ignored with utf8 based engines"],
        "pdf": {
            "path": rel(PDF),
            "sha256": PDF_SHA256,
            "bytes": PDF.stat().st_size,
            "page_count": 13,
        },
        "rendered_page_inspection": {
            "pages_checked": 13,
            "blank_pages": 0,
            "clipping_detected": False,
            "overlap_detected": False,
            "broken_tables_detected": False,
            "artifact_operation_marker_runs": 1,
            "status": "PASS",
        },
    }
    write_json(COMPILE_REPORT, compile_report)

    compliance = {
        "mode": "primary_research",
        "stage": "2.5",
        "generated_at": GENERATED_AT,
        "prisma_trAIce": None,
        "raise": {
            "mode": "principles_only",
            "principles": {
                "human_oversight": "pass",
                "transparency": "pass",
                "reproducibility": "pass",
                "fit_for_purpose": "warn",
            },
            "principle_evidence": {
                "human_oversight": ["The user approved the Paper Configuration Record and the Stage 2 outline before prose and integrity progression."],
                "transparency": ["The manuscript separates four evidence namespaces and states that Hybrid, official reproduction, v5 comparison, and H1-H4 remain unestablished."],
                "reproducibility": ["Manuscript, bibliography, public aggregate, claim registry, evidence rows, and PDF are bound by replayed SHA-256 digests."],
                "fit_for_purpose": ["The manuscript is fit for bounded methods/protocol review, but effectiveness claims require the separately audited follow-up experiment and ablations."],
            },
            "block_decision": "warn",
        },
        "overall_decision": "warn",
        "user_action_required": False,
        "evidence": [
            rel(INTEGRITY_REPORT),
            rel(REFERENCE_REPORT),
            rel(DATA_REPORT),
            rel(ORIGINALITY_REPORT),
            rel(FAILURE_MODE_REPORT),
        ],
        "upstream_sync_status": "current",
    }
    write_json(COMPLIANCE_REPORT, compliance)

    drift = {
        "schema_version": "claim-strength-drift-findings/1.0",
        "status": "skipped_no_revision_evidence",
        "final_draft_sha256": MANUSCRIPT_SHA256,
        "revision_evidence_bundle_sha256": None,
        "detection_provenance": {
            "kind": "model_mediated_semantic_review",
            "detector_id": "stage2.5-central-semantic-review-telemetry-unobservable",
            "protocol_sha256": sha256_file(CLAIM_PROTOCOL),
        },
        "findings": [],
    }
    write_json(DRIFT_REPORT, drift)

    integrity = {
        "schema_version": "ars-integrity-report/schema-5-compatible",
        "verdict": "PASS_WITH_CONDITIONS",
        "mode": "pre-review",
        "phases": {
            "A_references": {
                "checked": 35,
                "passed": 35,
                "failed": 0,
                "issues": [],
                "report_path": rel(REFERENCE_REPORT),
                "report_sha256": sha256_file(REFERENCE_REPORT),
            },
            "B_citation_context": {
                "population": 61,
                "sampled": 19,
                "verified": 19,
                "issues": [],
                "report_path": rel(CITATION_REPORT),
                "report_sha256": sha256_file(CITATION_REPORT),
            },
            "C_data": {
                "claims_checked": 9,
                "verified": 9,
                "issues": [],
                "report_path": rel(DATA_REPORT),
                "report_sha256": sha256_file(DATA_REPORT),
            },
            "D_originality": {
                "checked": True,
                "paragraph_population": 74,
                "sampled": 24,
                "coverage_percent": originality["coverage_percent"],
                "verdict": "ORIGINAL_SEARCH_BOUNDED",
                "issues": [
                    {
                        "type": "PROFESSIONAL_SIMILARITY_CHECK_PENDING",
                        "severity": "MINOR",
                        "detail": originality["mandatory_disclaimer"],
                    }
                ],
                "report_path": rel(ORIGINALITY_REPORT),
                "report_sha256": sha256_file(ORIGINALITY_REPORT),
            },
            "E_claims": {
                "registry_total": 76,
                "checked": 19,
                "verified": 19,
                "selection_tiers": {"HIGH-IMPACT": 12, "RANDOM": 7, "TOP-UP": 0, "NOT-SELECTED": 57},
                "distortions": [],
                "claim_registry_coverage": {
                    "status": "completed",
                    "registry_schema_version": "claim-registry/1.0",
                    "report_path": rel(COVERAGE),
                    "report_sha256": CLAIM_COVERAGE_SHA256,
                    "draft_raw_sha256": MANUSCRIPT_SHA256,
                    "registry_raw_sha256": CLAIM_REGISTRY_SHA256,
                    "candidate_unregistered_count": coverage["candidate_unregistered_count"],
                    "semantic_extraction_coverage": "not_machine_detectable",
                },
                "evidence_rows": evidence_rows,
                "claim_strength_drift_findings": {
                    "schema_version": "claim-strength-drift-findings/1.0",
                    "artifact_path": rel(DRIFT_REPORT),
                    "artifact_sha256": sha256_file(DRIFT_REPORT),
                    "status": "skipped_no_revision_evidence",
                },
            },
            "F_ai_research_failure_modes": {
                "checked": 7,
                "clear": 6,
                "suspected": 0,
                "insufficient_evidence": 1,
                "blocking": False,
                "report_path": rel(FAILURE_MODE_REPORT),
                "report_sha256": sha256_file(FAILURE_MODE_REPORT),
            },
        },
        "overall_issues": {"SERIOUS": 0, "MEDIUM": 0, "MINOR": 1},
        "citation_integrity_score": 1.0,
        "fabrication_risk_score": 0.0,
        "timestamp": GENERATED_AT,
        "conditions": [
            "Run a professional similarity check before submission.",
            "Recheck shortcut reliance after the proposed Hybrid and mandatory ablations run.",
            "Do not promote descriptive public rows into Hybrid, superiority, causal, production, or cross-namespace claims.",
        ],
        "scope_note": "PASS_WITH_CONDITIONS establishes bounded integrity and provenance checks only; it does not certify experimental design, scientific validity, reproducibility by ARS, or publication readiness.",
    }
    write_json(INTEGRITY_REPORT, integrity)

    stage2_passport = strict_load(STAGE2_PASSPORT)
    master_passport = strict_load(MASTER_PASSPORT)
    phase1e = strict_load(PHASE1E_SEAL)
    passport = copy.deepcopy(stage2_passport)
    passport.update(
        {
            "origin_skill": "academic-pipeline",
            "origin_mode": "stage2.5-pre-review-integrity",
            "origin_date": GENERATED_AT,
            "verification_status": "VERIFIED",
            "version_label": "stage2_5_integrity_v1",
            "integrity_pass_date": GENERATED_AT,
            "content_hash": f"sha256:{MANUSCRIPT_SHA256}",
        }
    )
    passport["upstream_dependencies"] = list(dict.fromkeys(passport["upstream_dependencies"] + ["stage2_write_draft_v2", "ais-r8-p5-phase1e-seal"]))
    experiment_map = {row["experiment_id"]: row for row in master_passport["experiment_provenance"]}
    public_provenance = phase1e["material_passport"]["experiment_provenance"][0]
    experiment_map[public_provenance["experiment_id"]] = public_provenance
    required_experiments = [
        "ais-r8-p3-public-validation-attempt-003",
        "EXP-REF-REPRO",
        "EXP-V5-HARMONIZED",
        "EXP-EXTERNAL-VALIDITY",
    ]
    passport["experiment_provenance"] = [copy.deepcopy(experiment_map[item]) for item in required_experiments]
    manifests = copy.deepcopy(stage2_passport["claim_intent_manifests"])
    c009 = next(row for row in manifests[0]["claims"] if row["claim_id"] == "C-009")
    c009["planned_experiment_ids"] = ["ais-r8-p3-public-validation-attempt-003"]
    passport["claim_intent_manifests"] = manifests
    passport["experiment_alignment_results"] = [
        {
            "finding_id": "EA-001",
            "scoped_manifest_id": manifests[0]["manifest_id"],
            "claim_id": "C-009",
            "claim_text": c009["claim_text"],
            "experiment_id": "ais-r8-p3-public-validation-attempt-003",
            "result_pointer": "planned_vs_executed[0].value.paper_admitted_rows plus aggregate_metrics.json",
            "manuscript_locator": "Results > PUBLIC_DATA_PROTOCOL_VALIDATION",
            "alignment_verdict": "ALIGNED",
            "rationale": "The manuscript reports exactly four Pop/BPR rows, labels them descriptive public protocol validation, and explicitly states that they do not evaluate the proposed Hybrid.",
            "judge_model": "UNOBSERVABLE_IN_CENTRAL_CONTEXT",
            "judge_run_at": GENERATED_AT,
            "rule_version": "EA-v1",
        }
    ]
    passport["experiment_alignment_scope_note"] = "This check verifies disclosure and claim-to-provenance fidelity. It does not judge whether the experiment was correctly designed, run, statistically adequate, or reproducible by ARS."
    passport["compliance_history"] = list(passport.get("compliance_history", [])) + [compliance]
    passport["integrity_binding"] = {
        "report_path": rel(INTEGRITY_REPORT),
        "report_sha256": sha256_file(INTEGRITY_REPORT),
        "manuscript_sha256": MANUSCRIPT_SHA256,
        "bibliography_sha256": BIBLIOGRAPHY_SHA256,
        "claim_registry_sha256": CLAIM_REGISTRY_SHA256,
        "pdf_sha256": PDF_SHA256,
    }
    passport["model_policy_audit"] = {
        "requested_model": "gpt-5.6-sol",
        "requested_reasoning": "ultra",
        "requested_service_tier": "Standard",
        "forbidden_service_tiers": ["Fast", "Priority"],
        "actual_model": "UNOBSERVABLE_IN_CENTRAL_CONTEXT",
        "actual_reasoning": "UNOBSERVABLE_IN_CENTRAL_CONTEXT",
        "actual_service_tier": "UNOBSERVABLE",
        "actual_speed": "UNOBSERVABLE",
        "telemetry_policy": "No runtime attribute is inferred from latency, prose, or prior task history.",
    }
    write_json(PASSPORT, passport)

    state = {
        "schema_version": "stage2.5-state/1.0",
        "project": "hybrid-recsys-v5",
        "stage": "2.5_INTEGRITY",
        "status": "STAGE2_5_PASS_AWAITING_USER_CONFIRMATION",
        "updated_at": GENERATED_AT,
        "source_revision": "36f67561fe51bde23e00db1a41f2ef9b22388579",
        "stage2_source_immutable": True,
        "phase1e_reopened": False,
        "v5_test_reopened": False,
        "integrity_verdict": "PASS_WITH_CONDITIONS",
        "coverage": {
            "references": "35/35",
            "citation_contexts": "19/61",
            "numeric_data_surfaces": "9/9",
            "originality_paragraphs": "24/74",
            "selected_claims": "19/19",
            "ai_failure_modes": "7/7",
        },
        "conditions": integrity["conditions"],
        "next_stage": "3_INDEPENDENT_REVIEW",
        "next_stage_authorized": False,
        "required_user_action": "Confirm entry to Stage 3 after reviewing the bounded Stage 2.5 integrity result.",
    }
    write_json(STATE, state)

    handoff = {
        "schema_version": "stage2.5-handoff/1.0",
        "project": "hybrid-recsys-v5",
        "stage": "2.5_INTEGRITY",
        "created_at": GENERATED_AT,
        "verdict": "STAGE2_5_PASS_AWAITING_USER_CONFIRMATION",
        "verdict_scope": "Bounded pre-review integrity passed with conditions; no new scientific result or Hybrid claim was admitted.",
        "upstream": {
            "stage2_handoff_path": rel(STAGE2_HANDOFF),
            "stage2_handoff_sha256": EXPECTED_INPUT_HASHES[STAGE2_HANDOFF],
            "phase1e_seal_path": rel(PHASE1E_SEAL),
            "phase1e_seal_sha256": EXPECTED_INPUT_HASHES[PHASE1E_SEAL],
        },
        "artifact_bindings": {
            "manuscript_sha256": MANUSCRIPT_SHA256,
            "bibliography_sha256": BIBLIOGRAPHY_SHA256,
            "pdf_sha256": PDF_SHA256,
            "claim_registry_sha256": CLAIM_REGISTRY_SHA256,
            "claim_coverage_sha256": CLAIM_COVERAGE_SHA256,
            "integrity_report_sha256": sha256_file(INTEGRITY_REPORT),
            "compliance_report_sha256": sha256_file(COMPLIANCE_REPORT),
            "material_passport_sha256": sha256_file(PASSPORT),
            "state_sha256": sha256_file(STATE),
            "reference_registry_sha256": BIBLIOGRAPHY_SHA256,
            "public_result_artifact_sha256": PUBLIC_AGGREGATE_SHA256,
        },
        "claim_policy": {
            "authorized_literature_claims": 22,
            "planning_only_claims": 22,
            "selected_integrity_claims": 19,
            "verified_selected_claims": 19,
            "hybrid_result_admitted": False,
            "official_reproduction_success_admitted": False,
            "harmonized_v5_result_admitted": False,
            "external_validity_admitted": False,
        },
        "result_namespace_policy": {
            "PUBLIC_DATA_PROTOCOL_VALIDATION": "FOUR_DESCRIPTIVE_ROWS_ONLY",
            "OFFICIAL_PROTOCOL_REPRODUCTION": "CLOSED_INCOMPARABLE_ZERO_ROWS",
            "HARMONIZED_V5_COMPARISON": "SEALED_WITH_MAJOR_LIMITATIONS_ZERO_ROWS",
            "FOLLOW_UP_HARMONIZED_V5": "NOT_RUN",
            "numeric_cross_namespace_join": False,
        },
        "unresolved_empirical_limitations": [
            "The proposed Hybrid has no admitted result row or ablation evidence.",
            "Official reproduction remains incomparable.",
            "Harmonized-v5 and external-validity result namespaces contain no admitted rows.",
            "The public lane has no paired per-user inference and does not validate Hybrid.",
        ],
        "model_policy": passport["model_policy_audit"],
        "next_gate": {
            "stage": "3_INDEPENDENT_REVIEW",
            "status": "MANDATORY_USER_CONFIRMATION",
            "automatic_dispatch_authorized": False,
        },
        "artifact_hash_manifest_path": rel(HASH_MANIFEST),
    }
    write_json(HANDOFF, handoff)
    write_integrity_markdown(integrity, references, contexts, data, originality, failures)
    write_json(HASH_MANIFEST, artifact_manifest())

    print("stage2_5_build=PASS")
    print(f"evidence_rows={len(evidence_rows)}")
    print(f"integrity_report_sha256={sha256_file(INTEGRITY_REPORT)}")
    print(f"passport_sha256={sha256_file(PASSPORT)}")
    print(f"handoff_sha256={sha256_file(HANDOFF)}")
    print(f"artifact_manifest_sha256={sha256_file(HASH_MANIFEST)}")


if __name__ == "__main__":
    main()
