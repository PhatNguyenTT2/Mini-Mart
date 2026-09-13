#!/usr/bin/env python3
"""Build the Stage 2.5 exact-span Claim Registry and coverage report."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE25 = REPO_ROOT / "research/hybrid-recsys-v5/05_manuscript/stage2_integrity"
DRAFT = STAGE25 / "03_compile/master_draft_stage2_5.tex"
REGISTRY = STAGE25 / "01_claim_registry/claim_registry_stage2_5.json"
COVERAGE = STAGE25 / "01_claim_registry/claim_registry_coverage_stage2_5.json"

ARS_SCRIPT = Path(
    "C:/Users/ACER/.codex/plugins/cache/ars-codex/ars-codex/0.1.26/"
    "skills/academic-research-suite/ars/scripts/claim_registry_coverage.py"
)
EXPECTED_DRAFT_SHA256 = "d3baf0deda40e7b51735f75213a36ef07cdf78b2e45ba830c92dc1524ea6624e"

REF_RE = re.compile(r"<!--ref:([^>]+)-->")
ANCHOR_RE = re.compile(r"<!--anchor:([^>]+)-->")
SECTION_RE = re.compile(r"\\(section|subsection)\*?\{([^}]+)\}")

MANUAL_HIGH_IMPACT_MARKERS = (
    "The completed public lane contains one deterministic Pop run",
    "The proposed Hybrid has not been admitted to the paper result set",
    "It also declares\n5,000 users, 5,200 items, 823,371 interactions",
    "The declared temporal boundaries are train from 2026-01-01",
    "Binary relevance is used for the top-$K$ metrics, with $K=10$",
    "The final training seeds are 42,\n2027, and 31415",
    "The planned interval is a two-sided percentile 95\\% hierarchical paired\nbootstrap with 2,000 replicates",
    "Its aggregate receipt is bound to SHA-256",
    "The lane contains one Pop run with seed 42 and three BPR runs",
    "The admitted public lane completed four run rows",
    "Pop & 42 & 0.042678",
    "For the primary descriptive metric, the three BPR values have mean 0.074770",
    "The other metrics show\nthe same row-level pattern, with BPR means of 0.294763",
    "A catalog with 5,200 items and 5,000 users is not invalid merely",
    "The evidence does not yet answer whether the proposed decoupled Wide-and-Deep",
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_coverage_module():
    spec = importlib.util.spec_from_file_location("ars_claim_registry_coverage", ARS_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load ARS coverage script: {ARS_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def byte_to_char(raw: bytes, byte_offset: int) -> int:
    return len(raw[:byte_offset].decode("utf-8", errors="strict"))


def section_at(text: str, raw: bytes, byte_offset: int) -> str | None:
    prefix = text[: byte_to_char(raw, byte_offset)]
    sections: list[tuple[str, str]] = []
    for match in SECTION_RE.finditer(prefix):
        level, title = match.groups()
        if level == "section":
            sections = [(level, title)]
        else:
            sections = [row for row in sections if row[0] == "section"]
            sections.append((level, title))
    if not sections:
        return "Front Matter"
    return " > ".join(title for _, title in sections)


def ref_slugs(text: str) -> list[str]:
    return list(dict.fromkeys(REF_RE.findall(text)))


def writer_anchors(text: str) -> list[str]:
    return list(dict.fromkeys(ANCHOR_RE.findall(text)))


def paragraph_spans(text: str) -> list[tuple[int, int, str]]:
    char_to_byte = [0]
    total = 0
    for char in text:
        total += len(char.encode("utf-8"))
        char_to_byte.append(total)

    spans: list[tuple[int, int, str]] = []
    for match in re.finditer(r"(?ms)(?:^|\n\n)(.*?)(?=\n\n|\Z)", text):
        body = match.group(1)
        if not body.strip():
            continue
        left = len(body) - len(body.lstrip())
        right = len(body.rstrip())
        start_char = match.start(1) + left
        end_char = match.start(1) + right
        spans.append((char_to_byte[start_char], char_to_byte[end_char], body[left:right]))
    return spans


def select_manual_spans(text: str) -> list[tuple[int, int, str]]:
    paragraphs = paragraph_spans(text)
    selected: list[tuple[int, int, str]] = []
    for marker in MANUAL_HIGH_IMPACT_MARKERS:
        normalized_marker = " ".join(marker.split())
        matches = [
            row
            for row in paragraphs
            if normalized_marker in " ".join(row[2].split())
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"manual high-impact marker must resolve once: {marker!r}; found {len(matches)}"
            )
        selected.append(matches[0])
    return selected


def claim_kind(text: str, candidate_kinds: list[str] | None = None) -> list[str]:
    if candidate_kinds and "quantitative_sentence" in candidate_kinds:
        return ["quantitative"]
    if re.search(r"\b\d[\d,.]*\b|\\%|@[0-9]+", text):
        return ["quantitative", "other_factual"]
    return ["other_factual"]


def main() -> None:
    draft_raw = DRAFT.read_bytes()
    if draft_raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError("draft contains a forbidden UTF-8 BOM")
    draft_text = draft_raw.decode("utf-8", errors="strict")
    if sha256(draft_raw) != EXPECTED_DRAFT_SHA256:
        raise RuntimeError("Stage 2.5 draft hash does not match the locked builder output")

    ars = load_coverage_module()
    empty_registry = {
        "schema_version": "claim-registry/1.0",
        "draft_raw_sha256": sha256(draft_raw),
        "claims": [],
    }
    empty_raw = (json.dumps(empty_registry, indent=2) + "\n").encode("utf-8")
    provisional = ars.build_report(draft_raw, empty_raw)

    claims: list[dict[str, Any]] = []
    used_spans: set[tuple[int, int]] = set()

    for index, candidate in enumerate(provisional["candidates"], start=1):
        span = (candidate["start_byte"], candidate["end_byte"])
        used_spans.add(span)
        claims.append(
            {
                "claim_id": f"LEX-{index:03d}",
                "claim_text": candidate["text"],
                "draft_span": {
                    "start_byte": candidate["start_byte"],
                    "end_byte": candidate["end_byte"],
                },
                "claim_kinds": claim_kind(
                    candidate["text"], candidate["candidate_kinds"]
                ),
                "ref_slugs": ref_slugs(candidate["text"]),
                "writer_anchors": writer_anchors(candidate["text"]),
                "paper_section": section_at(
                    draft_text, draft_raw, candidate["start_byte"]
                ),
                "selection_tier": "NOT-SELECTED",
            }
        )

    manual_count = 0
    for start, end, claim_text in select_manual_spans(draft_text):
        if (start, end) in used_spans:
            continue
        manual_count += 1
        used_spans.add((start, end))
        kinds = claim_kind(claim_text)
        basis = ["numerical"] if "quantitative" in kinds else []
        section = section_at(draft_text, draft_raw, start)
        if section in {"Front Matter", "Conclusion"}:
            basis.append("headline_conclusion")
        if section and (
            "Methodology" in section or "Experimental Design" in section
        ):
            basis.append("methods_critical")
        claims.append(
            {
                "claim_id": f"HI-{manual_count:03d}",
                "claim_text": claim_text,
                "draft_span": {"start_byte": start, "end_byte": end},
                "claim_kinds": kinds,
                "ref_slugs": ref_slugs(claim_text),
                "writer_anchors": writer_anchors(claim_text),
                "paper_section": section,
                "selection_tier": "HIGH-IMPACT",
                "high_impact_basis": list(dict.fromkeys(basis or ["methods_critical"])),
            }
        )

    claims.sort(key=lambda row: (row["draft_span"]["start_byte"], row["claim_id"]))

    remainder = [row for row in claims if row["selection_tier"] == "NOT-SELECTED"]
    random_count = min(10, max(3, math.ceil(len(remainder) * 0.10))) if remainder else 0
    random_order = sorted(
        remainder,
        key=lambda row: hashlib.sha256(
            f"stage2.5-mode1-20260912:{row['claim_id']}".encode("utf-8")
        ).hexdigest(),
    )
    for row in random_order[:random_count]:
        row["selection_tier"] = "RANDOM"

    selected_count = sum(
        row["selection_tier"] in {"HIGH-IMPACT", "RANDOM", "TOP-UP"}
        for row in claims
    )
    floor = min(10, len(claims))
    if selected_count < floor:
        top_up = floor - selected_count
        candidates = [row for row in random_order if row["selection_tier"] == "NOT-SELECTED"]
        for row in candidates[:top_up]:
            row["selection_tier"] = "TOP-UP"

    registry = {
        "schema_version": "claim-registry/1.0",
        "draft_raw_sha256": sha256(draft_raw),
        "claims": claims,
    }
    registry_raw = (
        json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    report = ars.build_report(draft_raw, registry_raw)
    report_raw = (
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_bytes(registry_raw)
    COVERAGE.write_bytes(report_raw)

    tiers: dict[str, int] = {}
    for row in claims:
        tiers[row["selection_tier"]] = tiers.get(row["selection_tier"], 0) + 1
    print(f"draft_sha256={sha256(draft_raw)}")
    print(f"registry_claims={len(claims)}")
    print(f"registry_sha256={sha256(registry_raw)}")
    print(f"coverage_candidates={len(report['candidates'])}")
    print(f"coverage_gaps={report['candidate_unregistered_count']}")
    print(f"coverage_sha256={sha256(report_raw)}")
    print(f"selection_tiers={json.dumps(tiers, sort_keys=True)}")


if __name__ == "__main__":
    main()
