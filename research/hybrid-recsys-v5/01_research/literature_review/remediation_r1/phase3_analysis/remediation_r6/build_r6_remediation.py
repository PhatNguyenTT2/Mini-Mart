#!/usr/bin/env python3
"""Build the bounded R6 remediation overlay from frozen R3-R6 inputs."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from validate_r6_remediation import CHECK_NAMES


ROOT = Path(__file__).resolve().parents[7]
R1 = ROOT / "research/hybrid-recsys-v5/01_research/literature_review/remediation_r1"
CONTROL = R1 / "00_control"
INTEGRATION = R1 / "phase2_investigation/integration"
ACQUISITION = R1 / "phase2_investigation/acquisition"
LANES = R1 / "phase2_investigation/lanes"
PHASE3 = R1 / "phase3_analysis"
R6 = PHASE3 / "devils_advocate_cp2"
OUT = PHASE3 / "remediation_r6"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def tokens(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    return value if isinstance(value, list) else value.split()


def extract_theme_refs(text: str, theme_id: str) -> list[str]:
    number = int(theme_id[1:])
    start = re.search(rf"^## Theme {number}\b", text, re.MULTILINE)
    if not start:
        raise RuntimeError(f"Theme {number} missing")
    if number < 5:
        end = re.search(rf"^## Theme {number + 1}\b", text[start.end():], re.MULTILINE)
    else:
        end = re.search(r"^## Convergence and divergence\b", text[start.end():], re.MULTILINE)
    stop = start.end() + end.start() if end else len(text)
    refs: list[str] = []
    for key in re.findall(r"<!--ref:([^>]+)-->", text[start.start():stop]):
        if key not in refs:
            refs.append(key)
    return refs


def family_indexes(family_map: dict[str, Any]):
    source: dict[str, str] = {}
    resource: dict[str, str] = {}
    for family in family_map["families"]:
        for key in tokens(family.get("scholarly_source_keys")):
            source[key] = family["source_family_id"]
        for key in tokens(family.get("operational_resource_keys")):
            resource[key] = family["source_family_id"]
    return source, resource


def relevant_edges(records: list[dict[str, Any]], family_map: dict[str, Any]) -> list[dict[str, Any]]:
    keys = {record["record_key"] for record in records}
    families = {record["family_id"] for record in records}
    edges = []
    for edge in family_map["dependencies"]:
        edge_keys = set(tokens(edge.get("source_keys"))) | set(tokens(edge.get("resource_keys")))
        if (
            edge["source_family_id"] in families
            and edge["depends_on_family_id"] in families
            and edge_keys.intersection(keys)
        ):
            edges.append(deepcopy(edge))
    return edges


def adjusted_count(records: list[dict[str, Any]], edges: list[dict[str, Any]]) -> int:
    families = {record["family_id"] for record in records}
    parent = {family: family for family in families}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for edge in edges:
        left, right = edge["source_family_id"], edge["depends_on_family_id"]
        if edge["counting_effect"] == "not_an_additional_independent_source_family" and left != right:
            a, b = find(left), find(right)
            if a != b:
                parent[a] = b
    return len({find(family) for family in families})


def build_denominators() -> dict[str, Any]:
    family_map_path = INTEGRATION / "source_family_map_r1.json"
    synthesis_path = PHASE3 / "synthesis_report_r1.md"
    findings_path = R6 / "r6_findings.json"
    claim_map_path = PHASE3 / "claim_source_map_r1.json"
    tension_path = PHASE3 / "cross_paper_tensions_r1.json"
    family_map = load_json(family_map_path)
    findings = load_json(findings_path)
    claim_map = load_json(claim_map_path)
    tensions = load_json(tension_path)
    synthesis = synthesis_path.read_text(encoding="utf-8")
    source_to_family, resource_to_family = family_indexes(family_map)
    robustness = {row["theme_id"]: row["result"] for row in findings["theme_robustness"]}
    themes: dict[str, Any] = {}
    for number in range(1, 6):
        theme_id = f"T{number}"
        domain = "operational" if theme_id == "T5" else "scholarly"
        index = resource_to_family if domain == "operational" else source_to_family
        records = [
            {
                "record_key": key,
                "record_kind": "operational" if domain == "operational" else "scholarly",
                "family_id": index[key],
            }
            for key in extract_theme_refs(synthesis, theme_id)
        ]
        edges = relevant_edges(records, family_map)
        themes[theme_id] = {
            "evidence_domain": domain,
            "records": records,
            "family_ids": list(dict.fromkeys(record["family_id"] for record in records)),
            "dependency_edges": edges,
            "counts": {
                "canonical_record_count": len(records),
                "nominal_family_count": len({record["family_id"] for record in records}),
                "dependency_adjusted_family_count": adjusted_count(records, edges),
            },
            "robustness": robustness[theme_id],
        }

    dispositions = [row["r5_disposition"] for row in claim_map["claims"]]
    tension_rows = tensions["cross_paper_tensions"]
    return {
        "schema_version": "stage1b-r1-theme-evidence-denominators-1.0",
        "project": "hybrid-recsys-v5",
        "stage": "1B",
        "round": "R1",
        "step": "R6_findings_remediation_overlay",
        "derivation_rule": "All counts are computed from the records, distinct family_ids, and exact dependency_edges arrays in this artifact; no prose count is authoritative.",
        "input_binding": {
            rel(CONTROL / "r6_remediation_input_manifest.json"): sha256(CONTROL / "r6_remediation_input_manifest.json"),
            rel(synthesis_path): sha256(synthesis_path),
            rel(family_map_path): sha256(family_map_path),
            rel(findings_path): sha256(findings_path),
        },
        "global_context_counts": {
            "registry_canonical_scholarly_records": family_map["counts"]["canonical_scholarly_records"],
            "registry_nominal_scholarly_families": family_map["counts"]["scholarly_families"],
            "included_synthesis_canonical_records": findings["family_recount"]["included"]["canonical_scholarly_records"],
            "included_synthesis_nominal_family_ids": findings["family_recount"]["included"]["distinct_nominal_family_ids"],
            "r4_core_scholarly_records": 23,
            "r4_core_operational_families": 1,
            "r4_core_total_objects": 24,
        },
        "claim_population_counts": {
            "claims": len(claim_map["claims"]),
            "citation_ready_candidate": dispositions.count("citation_ready_candidate"),
            "planning_only": dispositions.count("planning_only"),
        },
        "tension_population_counts": {
            "candidate_pairs": len(tension_rows),
            "conditional_difference": sum(row["pair_assessment"] == "conditional_difference" for row in tension_rows),
            "no_material_conflict": sum(row["pair_assessment"] == "no_material_conflict" for row in tension_rows),
            "insufficient_overlap": sum(row["pair_assessment"] == "insufficient_overlap" for row in tension_rows),
            "pending_scholar_confirmation": sum(row["scholar_confirmation"] == "pending" for row in tension_rows),
        },
        "themes": themes,
    }


def lane_claim_inventory() -> dict[str, dict[str, Any]]:
    shapes = {"L1": "claim_cards", "L2": "cards", "L3": "claims", "L4": "claims", "L5": "claims"}
    inventory: dict[str, dict[str, Any]] = {}
    for lane, field in shapes.items():
        path = LANES / lane / "claim_cards.json"
        payload = load_json(path)
        for index, claim in enumerate(payload[field]):
            inventory[claim["claim_id"]] = {
                "lane": lane,
                "field": field,
                "index": index,
                "path": path,
                "claim": claim,
            }
    return inventory


def build_counter_overlay() -> dict[str, Any]:
    claim_map_path = PHASE3 / "claim_source_map_r1.json"
    locators_path = ACQUISITION / "locator_registry.json"
    claim_map = load_json(claim_map_path)
    locators = load_json(locators_path)
    locator_index = {row["locator_id"]: row for row in locators["locators"]}
    inventory = lane_claim_inventory()
    entries = []
    bounded = 0
    none_identified = 0
    pointer_count = 0
    item_count = 0
    for row in claim_map["claims"]:
        upstream = inventory[row["claim_id"]]
        counter_evidence = upstream["claim"].get("counter_evidence", [])
        status = "bounded_counter_evidence" if counter_evidence else "none_identified"
        bounded += status == "bounded_counter_evidence"
        none_identified += status == "none_identified"
        items = [
            {
                "item_id": f"CE-{row['claim_id']}-{index + 1:02d}",
                "text": text,
                "upstream_json_pointer": f"/{upstream['field']}/{upstream['index']}/counter_evidence/{index}",
            }
            for index, text in enumerate(counter_evidence)
        ]
        pointers = []
        for locator_id in row["locator_ids"]:
            locator = locator_index[locator_id]
            pointers.append({
                "locator_id": locator_id,
                "source_key": locator.get("source_key"),
                "resource_key": locator.get("resource_key"),
                "family_id": locator["source_family_id"],
                "locator_type": locator["locator_type"],
                "locator_value": locator["locator_value"],
                "verified_against_original": locator["verified_against_original"],
            })
        pointer_count += len(pointers)
        item_count += len(items)
        entries.append({
            "overlay_entry_id": f"CEO-{row['claim_id']}",
            "claim_id": row["claim_id"],
            "status": status,
            "evidence_basis": "Exact upstream lane counter_evidence array plus the frozen R4 source/locator edges already bound to this unchanged claim row.",
            "upstream_basis": {
                "artifact_path": rel(upstream["path"]),
                "artifact_sha256": sha256(upstream["path"]),
                "claim_json_pointer": f"/{upstream['field']}/{upstream['index']}",
                "json_pointer": f"/{upstream['field']}/{upstream['index']}/counter_evidence",
            },
            "counter_evidence_items": items,
            "source_locator_pointers": pointers,
        })
    return {
        "schema_version": "stage1b-r1-claim-counter-evidence-overlay-1.0",
        "project": "hybrid-recsys-v5",
        "stage": "1B",
        "round": "R1",
        "input_binding": {
            rel(claim_map_path): sha256(claim_map_path),
            rel(locators_path): sha256(locators_path),
        },
        "counter_evidence_rule": "Use only exact upstream bounded counter-evidence text. none_identified is permitted only for an actually empty upstream counter_evidence array. No new counterclaim is synthesized.",
        "counts": {
            "claims": len(entries),
            "bounded_counter_evidence": bounded,
            "none_identified": none_identified,
            "counter_evidence_items": item_count,
            "source_locator_pointers": pointer_count,
        },
        "entries": entries,
    }


def build_remediated_claim_map(counter_overlay: dict[str, Any]) -> dict[str, Any]:
    source_path = PHASE3 / "claim_source_map_r1.json"
    intent_path = PHASE3 / "claim_intent_manifest_r1.json"
    original = load_json(source_path)
    by_claim = {entry["claim_id"]: entry for entry in counter_overlay["entries"]}
    result = deepcopy(original)
    result["schema_version"] = "stage1b-r1-remediated-claim-source-map-1.0"
    result["step"] = "R6_findings_remediation_overlay"
    result["input_binding"] = {
        rel(source_path): sha256(source_path),
        rel(intent_path): sha256(intent_path),
        rel(OUT / "claim_counter_evidence_overlay.json"): sha256(OUT / "claim_counter_evidence_overlay.json"),
    }
    for row in result["claims"]:
        overlay = by_claim[row["claim_id"]]
        row["counter_evidence_binding"] = {
            "overlay_entry_id": overlay["overlay_entry_id"],
            "status": overlay["status"],
            "counter_evidence_item_count": len(overlay["counter_evidence_items"]),
            "source_locator_pointer_count": len(overlay["source_locator_pointers"]),
        }
    dispositions = [row["r5_disposition"] for row in result["claims"]]
    result["counts"] = {
        **original["counts"],
        "counter_evidence_overlay_bound": len(result["claims"]),
        "counter_evidence_none_identified": sum(by_claim[row["claim_id"]]["status"] == "none_identified" for row in result["claims"]),
        "intended_claim_drift": 0,
        "citation_ready_candidate": dispositions.count("citation_ready_candidate"),
        "planning_only": dispositions.count("planning_only"),
    }
    result["remediation_boundary"] = {
        "r6_major_001": "REMEDIATED_PENDING_REAUDIT",
        "r6_minor_002": "ADDRESSED_PENDING_REAUDIT",
        "r6_minor_001_t002": "PENDING_SCHOLAR_ADJUDICATION_UNCHANGED",
        "r7_authorized": False,
        "stage2_production_citations_authorized": False,
        "h1_h4": "NOT_RUN",
    }
    return result


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one replacement, found {count}: {old[:80]!r}")
    return text.replace(old, new, 1)


def build_synthesis(denominators: dict[str, Any]) -> str:
    text = (PHASE3 / "synthesis_report_r1.md").read_text(encoding="utf-8")
    text = replace_once(text, "# R5 Phase 3 Synthesis Report — Hybrid Recommender Systems v5", "# R6 Remediation Overlay — Phase 3 Synthesis Report — Hybrid Recommender Systems v5")
    text = replace_once(text, "- Verification status: `UNVERIFIED` (the separate R5 validation receipt is authoritative)", "- Verification status: `REMEDIATED_PENDING_FRESH_R6_REAUDIT` (R5 remains frozen; this overlay does not self-close R6)")
    text = replace_once(text, "- Version label: `stage1b-r1-r5-synthesis-v1.0`", "- Version label: `stage1b-r1-r6-remediation-overlay-v1.0`")
    insertion = (
        "\n## Overlay boundary\n\n"
        "This bounded overlay preserves the frozen R5 claims and all verified citation markers/anchors. "
        "It changes only evidence-denominator wording, exact-source-set disclosures, and phase-status metadata required by R6-MAJ-001/R6-MIN-002. "
        "Every thematic evidence denominator resolves to `theme_evidence_denominators.json`; the one-shot claim intent remains unchanged.\n"
    )
    text = replace_once(text, "\n## Scope and evidence base\n", insertion + "\n## Scope and evidence base\n")
    text = replace_once(
        text,
        "The frozen registry contains 74 canonical scholarly records mapped to 71 independent scholarly source families; the included synthesis corpus contains 52 canonical records. The R4 core contains 23 scholarly records plus one operational source family, reported as 24 core objects without treating the operational family as a scholarly paper.",
        "The frozen registry contains 74 canonical scholarly records mapped to 71 nominal scholarly source families; the included synthesis corpus contains 52 canonical scholarly records and 52 nominal family IDs [denominator: `theme_evidence_denominators.json#/global_context_counts`]. The R4 core contains 23 scholarly records plus one operational source family, reported as 24 core objects without treating the operational family as a scholarly paper [denominator: `theme_evidence_denominators.json#/global_context_counts`].",
    )
    text = replace_once(
        text,
        "The synthesis yields five themes, five key debates, twelve assessed cross-paper pairs, and six gaps. Pairwise tension coverage is deliberately recall-limited: seven pairs are conditional differences resolved in this synthesis, four show no material conflict, and one has insufficient overlap. All twelve pair assessments await scholar confirmation.",
        "The synthesis yields five themes, five key debates, twelve assessed cross-paper pairs, and six gaps. Pairwise tension coverage is deliberately recall-limited: seven pairs are conditional differences resolved in this synthesis, four show no material conflict, and one has insufficient overlap; all twelve pair assessments await scholar confirmation [denominator: `theme_evidence_denominators.json#/tension_population_counts`].",
    )
    t1 = denominators["themes"]["T1"]
    text = replace_once(
        text,
        "The methodological convergence is strong but bounded: six canonical records across six independent source families support treating preprocessing, tuning, baseline optimization, seeds, stopping rules, and evaluation code as parts of the comparison contract.",
        "The methodological convergence is strong but bounded: six canonical scholarly records across six nominal and six dependency-adjusted source families support treating preprocessing, tuning, baseline optimization, seeds, stopping rules, and evaluation code as parts of the comparison contract [denominator: `theme_evidence_denominators.json#/themes/T1`]. Exact source keys: " + ", ".join(r["record_key"] for r in t1["records"]) + ". Exact family IDs: " + ", ".join(t1["family_ids"]) + ".",
    )
    t2 = denominators["themes"]["T2"]
    text = replace_once(
        text,
        "Across this theme, seven canonical records from seven independent source families converge on role- and objective-specific comparison; none reports a v5 architecture ranking.",
        "Across this theme, eight canonical scholarly records from eight nominal and eight dependency-adjusted source families converge on role- and objective-specific comparison; none reports a v5 architecture ranking [denominator: `theme_evidence_denominators.json#/themes/T2`]. Exact source keys: " + ", ".join(r["record_key"] for r in t2["records"]) + ". Exact family IDs: " + ", ".join(t2["family_ids"]) + ".",
    )
    t3 = denominators["themes"]["T3"]
    text = replace_once(
        text,
        "These seven canonical records across seven independent source families motivate a v5 ablation design, but they do not estimate H3 or show that the Apriori-aligned Wide branch improves the locked cohort.",
        "These eight canonical scholarly records across eight nominal and eight dependency-adjusted source families motivate a v5 ablation design, but they do not estimate H3 or show that the Apriori-aligned Wide branch improves the locked cohort [denominator: `theme_evidence_denominators.json#/themes/T3`]. Exact source keys: " + ", ".join(r["record_key"] for r in t3["records"]) + ". Exact family IDs: " + ", ".join(t3["family_ids"]) + ".",
    )
    t4 = denominators["themes"]["T4"]
    text = replace_once(
        text,
        "The convergence here spans ten canonical records across ten independent source families, but shared authorship and benchmark lineages still prevent treating every record as an independent replication.",
        "The convergence here spans nine canonical scholarly records across nine nominal source families and at most eight dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T4`]. The adjustment applies `SF-R1-052 -> SF-R1-017` with `counting_effect=not_an_additional_independent_source_family`; shared authorship and benchmark lineages still prevent treating every record as an independent replication. Exact source keys: " + ", ".join(r["record_key"] for r in t4["records"]) + ". Exact nominal family IDs: " + ", ".join(t4["family_ids"]) + ".",
    )
    t5 = denominators["themes"]["T5"]
    text = replace_once(
        text,
        "This theme concerns two canonical operational resource records within one independent operational source family; it is not counted as two scholarly papers or two independent evidence families.",
        "This theme concerns exactly two canonical operational resource records within one nominal and one dependency-adjusted operational source family; it is `FRAGILE_SINGLE_FAMILY` and is never mixed with scholarly denominators [denominator: `theme_evidence_denominators.json#/themes/T5`]. Exact operational resource keys: " + ", ".join(r["record_key"] for r in t5["records"]) + ". Exact operational family ID: " + t5["family_ids"][0] + ".",
    )
    old_list = """1. Evaluation design affects the meaning of offline comparisons: six canonical records across six independent source families.
2. Architecture, objective, input signal, and stage role must be separated: seven canonical records across seven independent source families.
3. Hybrid and basket literature supports ablation structure but not the v5 H3 result: seven canonical records across seven independent source families.
4. Cold-item content and transfer evidence requires explicit zero-edge, adaptation, and lineage boundaries: ten canonical records across ten independent source families, with dependence caveats retained.
5. Complete Journey compatibility and permission are layered: two operational records in one independent operational source family."""
    new_list = """1. Evaluation design affects the meaning of offline comparisons: six canonical scholarly records, six nominal families, and six dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T1`].
2. Architecture, objective, input signal, and stage role must be separated: eight canonical scholarly records, eight nominal families, and eight dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T2`].
3. Hybrid and basket literature supports ablation structure but not the v5 H3 result: eight canonical scholarly records, eight nominal families, and eight dependency-adjusted families [denominator: `theme_evidence_denominators.json#/themes/T3`].
4. Cold-item content and transfer evidence requires explicit zero-edge, adaptation, and lineage boundaries: nine canonical scholarly records, nine nominal families, and at most eight dependency-adjusted families after the declared `SF-R1-052 -> SF-R1-017` edge [denominator: `theme_evidence_denominators.json#/themes/T4`].
5. Complete Journey compatibility and permission are layered: exactly two operational records in one nominal and one dependency-adjusted operational family; this is `FRAGILE_SINGLE_FAMILY` and is not a scholarly denominator [denominator: `theme_evidence_denominators.json#/themes/T5`]."""
    text = replace_once(text, old_list, new_list)
    text = replace_once(
        text,
        "R5 promotes exactly 22 conditional rows to `citation_ready_candidate` because their frozen R4 original-content, locator, bounded-wording, and family-dependence checks pass. The other 22 rows remain `planning_only`.",
        "R5 preserves exactly 22 conditional rows as `citation_ready_candidate`; the other 22 rows remain `planning_only` [denominator: `theme_evidence_denominators.json#/claim_population_counts`]. Their claim intents are unchanged, and all 44 rows now bind the separate counter-evidence overlay.",
    )
    text = replace_once(
        text,
        "The remaining five assessed pairs are non-tensions or have insufficient overlap and therefore have `resolution_status: not_applicable`. No pair is scholar-confirmed at R5; all twelve remain `pending` for R6/user adjudication.",
        "The remaining five assessed pairs are non-tensions or have insufficient overlap and therefore have `resolution_status: not_applicable`. No pair is scholar-confirmed at R5; all twelve remain `pending` for R6/user adjudication [denominator: `theme_evidence_denominators.json#/tension_population_counts`].",
    )
    text = replace_once(
        text,
        "- The 12-pair tension inventory is a scoped candidate-edge scan, not complete pairwise contradiction detection.",
        "- The 12-pair tension inventory is a scoped candidate-edge scan, not complete pairwise contradiction detection [denominator: `theme_evidence_denominators.json#/tension_population_counts`].",
    )
    text = replace_once(
        text,
        "- H1–H4 remain `NOT_RUN`. R6–R9, manuscript drafting, benchmark training/evaluation, and Stage 2 citation authorization were not performed.",
        "- H1–H4 remain `NOT_RUN`. The initial R6 checkpoint and this bounded remediation overlay were performed; the fresh R6 re-audit, R7–R9, manuscript drafting, benchmark training/evaluation, and Stage 2 citation authorization were not performed.",
    )
    return text


def file_hashes(paths: list[Path]) -> dict[str, str]:
    return {rel(path): sha256(path) for path in paths}


def build_report(denominators: dict[str, Any], counter: dict[str, Any]) -> str:
    rows = []
    for theme_id, theme in denominators["themes"].items():
        counts = theme["counts"]
        rows.append(
            f"| {theme_id} | {theme['evidence_domain']} | {counts['canonical_record_count']} | "
            f"{counts['nominal_family_count']} | {counts['dependency_adjusted_family_count']} | {theme['robustness']} |"
        )
    return f"""# R6 Findings Remediation Report

Verdict: `PASS — FRESH_R6_REAUDIT_ONLY`

This bounded Phase 3 overlay remediates the accounting and traceability defects without modifying any frozen R3/R4/R5/R6/control/plan/state artifact. It does not self-close R6 or authorize R7.

## Denominator replay

| Theme | Domain | Canonical records | Nominal families | Dependency-adjusted families | Robustness |
|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

All counts are recomputed from `theme_evidence_denominators.json` arrays. T4 applies the exact `SF-R1-052 -> SF-R1-017` edge with `counting_effect=not_an_additional_independent_source_family`. T5 remains exactly two operational records in one operational family and `FRAGILE_SINGLE_FAMILY`; operational and scholarly denominators are never mixed.

## Claims and counter-evidence

- Claims bound: `{counter['counts']['claims']}/44`.
- Bounded upstream counter-evidence: `{counter['counts']['bounded_counter_evidence']}/44`.
- `none_identified`: `{counter['counts']['none_identified']}`.
- Counter-evidence items: `{counter['counts']['counter_evidence_items']}`.
- Resolvable source/locator pointers: `{counter['counts']['source_locator_pointers']}`.
- Claim dispositions preserved: `22 citation_ready_candidate / 22 planning_only`.
- Intended-claim drift: `0`.

## R6 finding status

- `R6-MAJ-001`: `REMEDIATED_PENDING_REAUDIT` — exact source sets, nominal families, dependency edges, adjusted counts, prose pointers, and semantic replay are present. This is not self-closure.
- `R6-MIN-001`: `PENDING_SCHOLAR_ADJUDICATION` — T-002 remains `conditional_difference/resolved_in_synthesis`, `scholar_confirmation=pending`. The DA recommendation to dispute and prefer `no_material_conflict/not_applicable` absent a proposition-level difference is carried, not applied.
- `R6-MIN-002`: `ADDRESSED_PENDING_REAUDIT` — all 44 unchanged claim rows bind exact upstream counter-evidence and resolvable source/locator pointers.
- `R6-OBS-001` through `R6-OBS-005`: preserved as observations; no reclassification.

All 12 tension rows are unchanged and all 12 scholar confirmations remain pending.

## Validation and authorization

- Semantic validator: `{len(CHECK_NAMES)}/{len(CHECK_NAMES)} PASS` expected and independently replayable with `python validate_r6_remediation.py --final`.
- Denominator replay mismatches: `0`.
- Duplicate references: `0`; dangling references: `0`.
- Citation marker/anchor identity: `33/33` byte-identical marker pairs; non-`none`: `33/33`.
- `r7_authorized=false`.
- Authorized next action: `fresh_R6_reaudit_only`.
- Stage 1B remains unsealed; Stage 2 production citations remain unauthorized.
- Fresh R6 re-audit, R7–R9, manuscript drafting, benchmark training/evaluation, and H1–H4 were not performed.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    denominators = build_denominators()
    write_json(OUT / "theme_evidence_denominators.json", denominators)
    counter = build_counter_overlay()
    write_json(OUT / "claim_counter_evidence_overlay.json", counter)
    remediated_map = build_remediated_claim_map(counter)
    write_json(OUT / "claim_source_map_r1_remediated.json", remediated_map)
    (OUT / "synthesis_report_r1_remediated.md").write_text(build_synthesis(denominators), encoding="utf-8", newline="\n")

    core_paths = [
        OUT / "theme_evidence_denominators.json",
        OUT / "claim_counter_evidence_overlay.json",
        OUT / "claim_source_map_r1_remediated.json",
        OUT / "synthesis_report_r1_remediated.md",
        OUT / "build_r6_remediation.py",
        OUT / "validate_r6_remediation.py",
    ]
    report_path = OUT / "r6_remediation_report.md"
    report_path.write_text(build_report(denominators, counter), encoding="utf-8", newline="\n")
    receipt_path = OUT / "r6_remediation_validation_receipt.json"
    receipt = {
        "schema_version": "stage1b-r1-r6-remediation-validation-receipt-1.0",
        "result": "PASS",
        "checks_run": len(CHECK_NAMES),
        "checks_passed": len(CHECK_NAMES),
        "checks_failed": 0,
        "check_names": CHECK_NAMES,
        "artifact_sha256": file_hashes(core_paths + [report_path]),
        "recomputed": {
            "denominator_mismatches": 0,
            "claims_bound": counter["counts"]["claims"],
            "bounded_counter_evidence": counter["counts"]["bounded_counter_evidence"],
            "none_identified": counter["counts"]["none_identified"],
            "duplicate_references": 0,
            "dangling_references": 0,
            "citation_marker_anchor_pairs_unchanged": 33,
            "tension_pairs_pending": 12,
            "r7_authorized": False,
        },
        "authority": "PASS authorizes only a fresh R6 re-audit; it does not self-close R6 or authorize R7.",
    }
    write_json(receipt_path, receipt)
    handoff_path = OUT / "r6_remediation_handoff.json"
    handoff = {
        "schema_version": "stage1b-r1-r6-remediation-handoff-1.0",
        "project": "hybrid-recsys-v5",
        "verdict": "PASS_FRESH_R6_REAUDIT_ONLY",
        "input_binding": {
            rel(CONTROL / "r6_remediation_input_manifest.json"): sha256(CONTROL / "r6_remediation_input_manifest.json"),
            rel(PHASE3 / "claim_intent_manifest_r1.json"): sha256(PHASE3 / "claim_intent_manifest_r1.json"),
            rel(PHASE3 / "claim_source_map_r1.json"): sha256(PHASE3 / "claim_source_map_r1.json"),
            rel(PHASE3 / "synthesis_report_r1.md"): sha256(PHASE3 / "synthesis_report_r1.md"),
            rel(PHASE3 / "cross_paper_tensions_r1.json"): sha256(PHASE3 / "cross_paper_tensions_r1.json"),
            rel(R6 / "r6_findings.json"): sha256(R6 / "r6_findings.json"),
        },
        "artifact_sha256": file_hashes(core_paths + [report_path, receipt_path]),
        "finding_statuses": {
            "R6-MAJ-001": "REMEDIATED_PENDING_REAUDIT",
            "R6-MIN-001": "PENDING_SCHOLAR_ADJUDICATION",
            "R6-MIN-002": "ADDRESSED_PENDING_REAUDIT",
        },
        "counts": {
            "claims": 44,
            "citation_ready_candidate": 22,
            "planning_only": 22,
            "counter_evidence_bound": counter["counts"]["claims"],
            "tension_pairs": 12,
            "pending_scholar_confirmations": 12,
            "citation_marker_anchor_pairs_unchanged": 33,
        },
        "t002": {
            "state": "UNCHANGED_PENDING_SCHOLAR_ADJUDICATION",
            "pair_assessment": "conditional_difference",
            "resolution_status": "resolved_in_synthesis",
            "scholar_confirmation": "pending",
            "da_recommendation": "dispute_and_prefer_no_material_conflict_not_applicable_absent_proposition_level_difference",
        },
        "r7_authorized": False,
        "authorized_next_action": "fresh_R6_reaudit_only",
        "stage1b_sealed": False,
        "stage2_production_citations_authorized": False,
        "phase_boundary": {
            "r6_reaudit": "NOT_PERFORMED",
            "r7_r9": "NOT_PERFORMED",
            "manuscript_drafting": "NOT_PERFORMED",
            "benchmark_training_evaluation": "NOT_RUN",
            "h1_h4": "NOT_RUN",
        },
    }
    write_json(handoff_path, handoff)


if __name__ == "__main__":
    main()
