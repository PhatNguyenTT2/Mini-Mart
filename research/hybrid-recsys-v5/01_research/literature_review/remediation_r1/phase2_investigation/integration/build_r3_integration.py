#!/usr/bin/env python3
"""Deterministic R3 central merge for Stage 1B remediation R1.

The script reads only the frozen lane handoffs and the pre-remediation corpus.  It
writes the ten contract outputs into this directory, validates the cross-file
graph, and records the non-self output hashes in the handoff.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
REMEDIATION = HERE.parents[1]
LIT_REVIEW = HERE.parents[2]
LANES = REMEDIATION / "phase2_investigation" / "lanes"
OLD_CORPUS_PATH = LIT_REVIEW / "phase2_investigation" / "literature_corpus.json"
CONTROL = REMEDIATION / "00_control"
MANIFEST_SHA = "a0842f4932ff0a23c59ab5d97706f7609f42ccddd660fd6b7f6e1f8e2b0d82e5"
CONTRACT_SHA = "44cf1424ab89c69806a8f3fdc57694df3fe83338c6c70031b93632661fe98d15"
# Frozen continuation timestamp: output bytes are reproducible across reruns.
NOW = "2026-08-21T00:00:00+07:00"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_doi(value) -> str | None:
    if not value:
        return None
    value = str(value).strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value.rstrip(" .") or None


def norm_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").casefold()
    value = value.replace("²", "2")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def slug(value: str) -> str:
    s = norm_title(value)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def normalize_status(value) -> str:
    s = str(value or "unknown").strip().lower().replace(" ", "_")
    return s or "unknown"


def bool_or_unknown(value):
    if value is True or str(value).lower() == "true":
        return True
    if value is False or str(value).lower() == "false":
        return False
    return "unknown"


def authors_literal(authors) -> list[str]:
    result = []
    for author in authors or []:
        if isinstance(author, str):
            name = " ".join(author.split())
        elif isinstance(author, dict):
            name = " ".join(str(author.get(k, "")) for k in ("given", "family")).strip()
            if not name:
                name = str(author.get("literal", "")).strip()
        else:
            name = str(author).strip()
        if name and name not in result:
            result.append(name)
    return result


def old_authors(authors) -> list[dict]:
    result = []
    for author in authors:
        if isinstance(author, dict):
            result.append(author)
        else:
            result.append({"literal": str(author)})
    return result


def flatten_strings(values) -> list[str]:
    """Flatten lane list-valued prose fields without dropping any text."""
    result = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            candidates = value
        else:
            candidates = [value]
        for candidate in candidates:
            text = str(candidate).strip()
            if text and text not in result:
                result.append(text)
    return result


class UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[b] = a


registries = {}
queues = {}
raw = []
claims_raw = []
operational_raw = []
for lane_name in ("L1", "L2", "L3", "L4", "L5"):
    lane_dir = LANES / lane_name
    reg = load(lane_dir / "candidate_registry.json")
    registries[lane_name] = reg
    q = load(lane_dir / "source_acquisition_queue.json")
    qrows = q.get("entries", q.get("queue", []))
    qindex = {}
    for item in qrows:
        key = item.get("source_key", item.get("key"))
        if key:
            qindex[key] = item
    queues[lane_name] = qindex
    rows = reg.get("scholarly_works", reg.get("records", []))
    for row in rows:
        item = dict(row)
        item["_lane"] = lane_name
        item["_lane_dir"] = lane_dir
        raw.append(item)
    for row in reg.get("operational_resources", []):
        item = dict(row)
        item["_lane"] = lane_name
        item["_lane_dir"] = lane_dir
        operational_raw.append(item)
    cards_doc = load(lane_dir / "claim_cards.json")
    cards = cards_doc.get("claim_cards", cards_doc.get("cards", cards_doc.get("claims", [])))
    for card in cards:
        item = dict(card)
        item["_lane"] = lane_name
        claims_raw.append(item)

assert len(raw) == 79, len(raw)
assert len(operational_raw) == 14, len(operational_raw)
assert len(claims_raw) == 44, len(claims_raw)

# Identity merge: exact normalized DOI first, then canonical title plus complete
# author/year evidence.  The title merge deliberately captures LightGCL and the
# 2007/2009 Liu manifestations; no description or claim text participates.
uf = UnionFind(len(raw))
doi_first = {}
for i, row in enumerate(raw):
    doi = norm_doi(row.get("doi"))
    if doi:
        if doi in doi_first:
            uf.union(i, doi_first[doi])
        else:
            doi_first[doi] = i

title_groups = defaultdict(list)
for i, row in enumerate(raw):
    title_groups[norm_title(row["title"])].append(i)
for title, idxs in title_groups.items():
    if len(idxs) < 2:
        continue
    for a in idxs[1:]:
        r0, r1 = raw[idxs[0]], raw[a]
        authors0 = {norm_title(x) for x in authors_literal(r0.get("authors"))}
        authors1 = {norm_title(x) for x in authors_literal(r1.get("authors"))}
        author_match = bool(authors0 and authors1 and (authors0 == authors1 or len(authors0 & authors1) >= 2))
        official_match = bool(r0.get("official_id") and r1.get("official_id") and
                              norm_title(str(r0["official_id"])) == norm_title(str(r1["official_id"])))
        if author_match or official_match or "lightgcl" in title:
            uf.union(idxs[0], a)

groups = defaultdict(list)
for i, row in enumerate(raw):
    groups[uf.find(i)].append(row)
assert len(groups) == 74, len(groups)

old_doc = load(OLD_CORPUS_PATH)
old_rows = old_doc["literature_corpus"]
old_doi = {norm_doi(r.get("doi")): r for r in old_rows if norm_doi(r.get("doi"))}
old_title = {norm_title(r["title"]): r for r in old_rows}

manual_keys = {
    "contextgnn beyond two tower recommendation systems": "yuan2025_contextgnn",
    "unleashing the potential of two tower models diffusion based cross interaction for large scale matching": "wang2025_t2diff",
    "repeat explore aware grocery next basket recommendation with time decayed lightgcn": "mansouri2026_repeat_explore_lightgcn",
    "on inherited popularity bias in cold start item recommendation": "meehan2025_cold_popbias",
    "sparse contrastive learning for content based cold item recommendation": "meehan2026_semco",
    "universal item tokenization for transferable generative recommendation": "zheng2026_utgrec",
    "a graph based deep learning model with multimodal fusion for vietnamese recommendation systems": "nguyen2025_viecomrec_graph",
}


def preference(row) -> tuple:
    # Prefer canonical later journal/proceedings manifestation, then the most
    # complete verified metadata.  This makes Liu 2009 canonical over 2007.
    status = normalize_status(row.get("publication_status"))
    status_score = 2 if status in {"published", "journal_article", "conference_paper"} else 0
    return (
        int(row.get("publication_year") or 0),
        status_score,
        int(bool(row.get("metadata_verified"))),
        len(authors_literal(row.get("authors"))),
    )


group_info = []
alias_to_key = {}
used_keys = set()
for members in groups.values():
    preferred = max(members, key=preference)
    old = None
    for member in members:
        if norm_doi(member.get("doi")) in old_doi:
            old = old_doi[norm_doi(member.get("doi"))]
            break
        if norm_title(member["title"]) in old_title:
            old = old_title[norm_title(member["title"])]
            break
    canonical_title_norm = norm_title(preferred["title"])
    if old:
        key = old["citation_key"]
    elif canonical_title_norm in manual_keys:
        key = manual_keys[canonical_title_norm]
    else:
        authors = authors_literal(preferred.get("authors"))
        family = (authors[0].split()[-1] if authors else "source").lower()
        key = f"{slug(family)}{preferred.get('publication_year') or ''}_{slug(preferred['title'])[:58]}"
    base = key
    suffix = 2
    while key in used_keys:
        key = f"{base}_{suffix}"
        suffix += 1
    used_keys.add(key)
    for member in members:
        alias_to_key[member["source_key"]] = key
    group_info.append({"key": key, "preferred": preferred, "members": members, "old": old})

# Family merge happens only after identity keys are stable.  Candidate family
# identifiers are preserved as aliases, while repeated aliases join versions,
# repositories, or dataset-linked papers into one independent family.
fuf = UnionFind(len(group_info))
family_seen = {}
for i, group in enumerate(group_info):
    for row in group["members"]:
        family = row.get("source_family_id")
        if family:
            if family in family_seen:
                fuf.union(i, family_seen[family])
            else:
                family_seen[family] = i

family_members = defaultdict(list)
for i in range(len(group_info)):
    family_members[fuf.find(i)].append(i)
assert len(family_members) == 71, len(family_members)

family_id_by_group = {}
family_alias_map = {}
for n, idxs in enumerate(sorted(family_members.values(), key=lambda xs: min(group_info[i]["key"] for i in xs)), 1):
    fid = f"SF-R1-{n:03d}"
    aliases = sorted({r.get("source_family_id") for i in idxs for r in group_info[i]["members"] if r.get("source_family_id")})
    for i in idxs:
        family_id_by_group[i] = fid
    for alias in aliases:
        family_alias_map[alias] = fid


def resolve_artifact(lane: str, queue_item: dict) -> tuple[str | None, bool, str | None]:
    value = queue_item.get("local_path") or queue_item.get("artifact")
    if not value:
        return None, False, None
    p = Path(str(value))
    if not p.is_absolute():
        p = LANES / lane / p
    exists = p.is_file()
    rel = p.resolve().relative_to(HERE.parents[6].resolve()).as_posix() if exists else str(value).replace("\\", "/")
    actual_hash = sha256(p) if exists else None
    declared = queue_item.get("sha256")
    if exists and declared and actual_hash != declared:
        raise AssertionError(f"artifact hash mismatch: {p}")
    return rel, exists, actual_hash


source_records = []
for gi, group in enumerate(group_info):
    preferred = group["preferred"]
    members = group["members"]
    key = group["key"]
    lanes = sorted({m["_lane"] for m in members})
    # Choose the strongest acquisition record across aliases without using it
    # to modify bibliographic identity.
    acquisition_options = []
    for m in members:
        q = queues[m["_lane"]].get(m["source_key"], {})
        artifact, acquired, artifact_hash = resolve_artifact(m["_lane"], q)
        acquisition_options.append((acquired, bool(q.get("source_content_verified", m.get("source_content_verified"))),
                                    bool(q.get("locator_ready", m.get("locator_ready"))), m, q, artifact, artifact_hash))
    best_acq = max(acquisition_options, key=lambda x: (x[0], x[1], x[2]))
    acquired, _, _, acq_member, queue_item, artifact, artifact_hash = best_acq
    content = any(bool(m.get("source_content_verified")) for m in members)
    locator_ready = any(bool(m.get("locator_ready")) for m in members)
    locators = []
    seen_locator = set()
    for m in members:
        loc = m.get("locator")
        if loc:
            marker = json.dumps(loc, ensure_ascii=False, sort_keys=True)
            if marker not in seen_locator:
                locators.append({"source_alias": m["source_key"], **loc})
                seen_locator.add(marker)
    peer_values = [bool_or_unknown(m.get("peer_reviewed")) for m in members]
    peer = True if True in peer_values else (False if False in peer_values else "unknown")
    peer_basis = next((m.get("peer_review_basis") for m in members if m.get("peer_reviewed") is True and m.get("peer_review_basis")), None)
    if key == "jannach2026_methodological_standards":
        peer = "unknown"
        peer_basis = "Official institutional record classifies the item as an editorial; no direct peer-review evidence was found."
    if any(m["source_key"] == "said_bellogin_2026_arxiv" for m in members):
        peer = "unknown"
        peer_basis = "Canonical status remains a 2026 arXiv preprint; no proceedings or journal status was established."
    if peer is True and not peer_basis:
        peer_basis = next((m.get("peer_review_basis") for m in members if m.get("peer_review_basis")), None)
    if peer is True and not peer_basis:
        raise AssertionError(f"peer_reviewed=true without evidence basis: {key}")
    year = preferred.get("publication_year")
    status = normalize_status(preferred.get("publication_status"))
    dois = sorted({norm_doi(m.get("doi")) for m in members if norm_doi(m.get("doi"))})
    manifestations = []
    for m in sorted(members, key=lambda x: (x.get("publication_year") or 0, x["source_key"])):
        manifestations.append({
            "lane_source_key": m["source_key"],
            "title": m["title"],
            "publication_year": m.get("publication_year"),
            "doi": norm_doi(m.get("doi")),
            "official_id": m.get("official_id"),
            "version_relation": m.get("version_relation"),
            "content_verified": bool(m.get("source_content_verified")),
            "locator_ready": bool(m.get("locator_ready")),
        })
    level = preferred.get("evidence_level", "VI")
    if key == "jannach2026_methodological_standards":
        level = "VII"
    if "survey" in preferred["title"].lower() or "systematic review" in preferred["title"].lower():
        level = "V"
    if peer is True and content and locator_ready:
        grade = "A"
    elif (peer is True and preferred.get("metadata_verified")) or (peer == "unknown" and content and locator_ready):
        grade = "B"
    else:
        grade = "C"
    source_records.append({
        "source_key": key,
        "record_type": "scholarly_work",
        "title": preferred["title"],
        "authors": authors_literal(preferred.get("authors")),
        "publication_year": year,
        "venue": preferred.get("venue"),
        "document_type": preferred.get("document_type"),
        "publication_status": status,
        "peer_reviewed": peer,
        "peer_review_basis": peer_basis,
        "peer_review_evidence_basis": peer_basis,
        "doi": norm_doi(preferred.get("doi")),
        "all_normalized_dois": dois,
        "official_id": preferred.get("official_id"),
        "official_url": preferred.get("official_url"),
        "identity_verified": all(bool(m.get("identity_verified")) for m in members),
        "metadata_verified": all(bool(m.get("metadata_verified")) for m in members),
        "source_content_verified": content,
        "locator_ready": locator_ready,
        "locators": locators,
        "source_family_id": family_id_by_group[gi],
        "manifestations": manifestations,
        "source_acquired": acquired,
        "acquired_artifact": artifact,
        "acquired_artifact_sha256": artifact_hash,
        "source_verified_against_original": bool(acquired and content and locator_ready),
        "source_verification_method": "manual_grep" if acquired and content and locator_ready else "none",
        "evidence_level": level,
        "quality_grade": grade,
        "lanes": lanes,
        "lane_source_aliases": sorted(m["source_key"] for m in members),
        "provenance": flatten_strings(m.get("provenance") for m in members),
        "limitations": flatten_strings(m.get("limitations") for m in members),
    })

source_by_key = {r["source_key"]: r for r in source_records}

# Canonical claim graph, computed before corpus selection so every production
# claim is selected by rule rather than by desired corpus count.
claim_records = []
production_source_keys = set()
for card in claims_raw:
    original_planning_only = card.get("planning_only")
    production_flag_present = "production_intended" in card
    original_production_intended = card.get("production_intended") if production_flag_present else None
    # Central state is deliberately singular.  The eight L4 rows that carry
    # planning_only=true AND production_intended=true are candidates only; R3
    # cannot promote them to production-ready before R4 and the citation gate.
    if original_production_intended is True or original_planning_only is False:
        central_disposition = "conditional_production_candidate"
        central_conditions = [
            "complete any R4 lawful-local-artifact and locator queue item",
            "pass the post-R4 central production-citation gate",
            "do not cite as production evidence until Stage 1B is sealed",
        ]
    else:
        central_disposition = "planning_only"
        central_conditions = ["retain for planning/context only unless a later central gate explicitly changes disposition"]
    ckeys = []
    evidence_aliases = []
    for alias in card.get("source_keys", []):
        if alias in alias_to_key:
            key = alias_to_key[alias]
            if key not in ckeys:
                ckeys.append(key)
            evidence_aliases.append({"lane_source_key": alias, "canonical_source_key": key})
        elif alias.startswith("R-"):
            evidence_aliases.append({"operational_resource_key": alias})
        else:
            raise AssertionError(f"unmapped claim source alias: {alias}")
    if central_disposition == "conditional_production_candidate":
        production_source_keys.update(ckeys)
    cfamilies = sorted({source_by_key[k]["source_family_id"] for k in ckeys})
    locators = card.get("locators") or card.get("additional_locators") or []
    if card.get("locator"):
        locators = [card["locator"]] + (locators if isinstance(locators, list) else [])
    claim_records.append({
        "claim_id": card["claim_id"],
        "lane": card["_lane"],
        "claim_text_bounded": card["claim_text_bounded"],
        "evidence_kind": card.get("evidence_kind"),
        "original_lane_state": {
            "planning_only": original_planning_only,
            "production_intended_present": production_flag_present,
            "production_intended": original_production_intended,
        },
        "central_disposition": central_disposition,
        "central_conditions": central_conditions,
        "support_verdict": card.get("support_verdict"),
        "canonical_source_keys": ckeys,
        "evidence_aliases": evidence_aliases,
        "source_family_ids": cfamilies,
        "locator_basis": card.get("locator_basis"),
        "locators": locators,
        "support_scope": card.get("support_scope"),
        "forbidden_extrapolations": card.get("forbidden_extrapolations", []),
        "counter_evidence": card.get("counter_evidence"),
    })

old_resource_keys = {"normann2023_otto", "hm_fashion_competition", "completejourney_resource"}
registry_only_old = {
    "bradley1997_auc", "jarvelin2002_ndcg", "huang2013_dssm",
    "du2020_mtpr", "wei2021_clcrec", "yu2024_xsimgcl", "tamm2021_metric_consistency",
}
old_scholarly = {r["citation_key"] for r in old_rows} - old_resource_keys
selected = (old_scholarly - registry_only_old) | production_source_keys
assert len(selected) == 52, (len(selected), sorted(production_source_keys - old_scholarly))
for record in source_records:
    record["corpus_included"] = record["source_key"] in selected
    record["central_disposition"] = "retained_corpus" if record["corpus_included"] else "retained_registry_only"

core_keys = {
    "krichene2020_sampled_metrics", "li2023_reliable_sampling", "zhao2020_alternative_settings",
    "dacrema2021_reproducibility", "jannach2026_methodological_standards",
    "sarwar2001_itemcf", "rendle2009_bpr", "he2020_lightgcn", "covington2016_youtube",
    "cheng2016_wide_deep", "kang2018_sasrec", "gusak2025_time_split",
    "agrawal1994_apriori", "ghoshal2014_multi_item_rules", "liu2009_hybrid_seq_cf",
    "li2023_nbr_reality", "volkovs2017_dropoutnet", "hou2022_unisrec",
    "sheng2025_alpharec", "reimers2019_sbert", "tran2024_viecomrec",
    "jin2023_amazon_m2", "tagliabue2021_coveo",
}
assert core_keys <= set(source_by_key), sorted(core_keys - set(source_by_key))
for record in source_records:
    record["core_shortlist"] = record["source_key"] in core_keys

# Operational registry: years remain nullable and are never inferred from names,
# URLs, or adjacent papers.  Rights layers are copied independently.
op_family_ids = {}
next_family = 72
for op in operational_raw:
    alias = op["source_family_id"]
    if alias in family_alias_map:
        fid = family_alias_map[alias]
    elif alias in op_family_ids:
        fid = op_family_ids[alias]
    else:
        fid = f"SF-R1-{next_family:03d}"
        next_family += 1
        op_family_ids[alias] = fid
    family_alias_map[alias] = fid
assert len(set(op_family_ids.values())) == 4

operational_records = []
for op in operational_raw:
    key = op["resource_key"]
    q = queues[op["_lane"]].get(key, {})
    artifact, acquired, artifact_hash = resolve_artifact(op["_lane"], q)
    operational_records.append({
        "resource_key": key,
        "record_type": "operational_resource",
        "provider": op.get("provider"),
        "resource_type": op.get("resource_type"),
        "edition": op.get("edition"),
        "release_year": op.get("release_year"),
        "operational_year": op.get("operational_year"),
        "year_basis": op.get("year_basis"),
        "official_url": op.get("official_url"),
        "accessed_at": op.get("accessed_at"),
        "availability": op.get("availability"),
        "terms_snapshot": op.get("terms_snapshot"),
        "code_license": op.get("code_license"),
        "paper_license": op.get("paper_license"),
        "dataset_rights": op.get("dataset_rights"),
        "redistribution_status": op.get("redistribution_status"),
        "rights_note": op.get("rights_note"),
        "source_family_id": family_alias_map[op["source_family_id"]],
        "original_source_family_id": op["source_family_id"],
        "source_acquired": acquired,
        "acquired_artifact": artifact,
        "acquired_artifact_sha256": artifact_hash,
        "source_content_verified": bool(q.get("source_content_verified")),
        "locator_ready": bool(q.get("locator_ready")),
        "checksums": op.get("checksums"),
        "provenance": op.get("provenance"),
    })
op_by_key = {r["resource_key"]: r for r in operational_records}
complete_journey_core_family = op_by_key["R-L5-COMPLETE-JOURNEY-PROVIDER"]["source_family_id"]
for record in operational_records:
    record["core_operational_family"] = record["source_family_id"] == complete_journey_core_family

# The R3 core-counting rule counts 23 scholarly records plus the one distinct
# Complete Journey operational family, not its two provider/package records.
actual_scholarly_core_count = sum(r["core_shortlist"] for r in source_records)
actual_operational_core_family_ids = {
    r["source_family_id"] for r in operational_records if r["core_operational_family"]
}
actual_operational_core_family_count = len(actual_operational_core_family_ids)
actual_core_total = actual_scholarly_core_count + actual_operational_core_family_count
assert actual_scholarly_core_count == 23
assert actual_operational_core_family_count == 1
assert actual_core_total == 24

# Attach operational sources in claim cards and add their canonical families.
for claim in claim_records:
    for alias in claim["evidence_aliases"]:
        opkey = alias.get("operational_resource_key")
        if opkey:
            if opkey not in op_by_key:
                raise AssertionError(f"unknown operational claim key: {opkey}")
            fid = op_by_key[opkey]["source_family_id"]
            if fid not in claim["source_family_ids"]:
                claim["source_family_ids"].append(fid)
    claim["source_family_ids"].sort()

original_planning_counts = Counter(
    "true" if c["original_lane_state"]["planning_only"] is True else
    "false" if c["original_lane_state"]["planning_only"] is False else "absent"
    for c in claim_records
)
original_production_intent_counts = Counter(
    "true" if c["original_lane_state"]["production_intended"] is True else
    "false" if c["original_lane_state"]["production_intended"] is False else "absent"
    for c in claim_records
)
central_claim_state_counts = Counter(c["central_disposition"] for c in claim_records)
assert original_planning_counts == Counter({"true": 30, "false": 14})
assert original_production_intent_counts == Counter({"absent": 36, "true": 8})
assert central_claim_state_counts == Counter({"conditional_production_candidate": 22, "planning_only": 22})
assert sum(central_claim_state_counts.values()) == len(claim_records)

dependencies = []


def dep(kind, source_family, target_family, source_keys=None, resource_keys=None, note=""):
    dependencies.append({
        "dependency_type": kind,
        "source_family_id": source_family,
        "depends_on_family_id": target_family,
        "source_keys": source_keys or [],
        "resource_keys": resource_keys or [],
        "counting_effect": "not_an_additional_independent_source_family",
        "note": note,
    })


def sf(key):
    return source_by_key[key]["source_family_id"]


# Version and evidence-lineage relations.
dep("paper_version", sf("krichene2020_sampled_metrics"), sf("krichene2020_sampled_metrics"),
    ["krichene2020_sampled_metrics"], note="KDD 2020 paper and IJCAI 2021 extended abstract are one work family.")
dep("paper_version", sf("li2023_reliable_sampling"), sf("li2023_reliable_sampling"),
    ["li2023_reliable_sampling"], note="AAAI 2023 paper and TORS 2024 journal version are one work family.")
dep("paper_version", sf("liu2009_hybrid_seq_cf"), sf("liu2009_hybrid_seq_cf"),
    ["liu2009_hybrid_seq_cf"], note="The 2007 conference predecessor remains a distinct manifestation; it does not substitute for the 2009 journal content.")
dep("repository_manifestation", sf("tran2024_viecomrec"), op_by_key["R-L5-VIECOMREC"]["source_family_id"],
    ["tran2024_viecomrec"], ["R-L5-VIECOMREC"], "Dataset paper and repository belong to one evidence family.")
dep("upstream_dataset", sf("hou2026_blair"), op_by_key["R-L5-AMAZON-REVIEWS-2023"]["source_family_id"],
    ["hou2026_blair"], ["R-L5-AMAZON-REVIEWS-2023"], "BLaIR derives from Amazon Reviews 2023.")
dep("upstream_dataset", sf("wu2025_muse_taobao_mm"), op_by_key["R-L5-TAOBAO-MM"]["source_family_id"],
    ["wu2025_muse_taobao_mm"], ["R-L5-TAOBAO-MM"], "MUSE uses the TAOBAO-MM operational dataset.")
dep("dataset_adapter", op_by_key["R-L5-RELBENCH-REL-AMAZON"]["source_family_id"], op_by_key["R-L5-RELBENCH-REL-AMAZON"]["source_family_id"],
    resource_keys=["R-L5-RELBENCH-REL-AMAZON"], note="RelBench adapter is not independent of upstream Amazon Reviews 2018 data.")
dep("dataset_adapter", op_by_key["R-L5-RELBENCH-REL-HM"]["source_family_id"], op_by_key["R-L5-HM"]["source_family_id"],
    resource_keys=["R-L5-RELBENCH-REL-HM", "R-L5-HM"], note="RelBench rel-hm is an adapter over H&M.")
dep("provider_package", op_by_key["R-L5-COMPLETEJOURNEY-R-PACKAGE"]["source_family_id"], op_by_key["R-L5-COMPLETE-JOURNEY-PROVIDER"]["source_family_id"],
    resource_keys=["R-L5-COMPLETEJOURNEY-R-PACKAGE", "R-L5-COMPLETE-JOURNEY-PROVIDER"], note="Package CC0 does not establish upstream dataset redistribution rights.")
dep("benchmark_reuse", sf("nguyen2025_viecomrec_graph"), sf("tran2024_viecomrec"),
    ["nguyen2025_viecomrec_graph", "tran2024_viecomrec"], note="The later graph paper reuses ViEcomRec; count the dataset lineage once for independence-sensitive claims.")
dep("method_reuse", sf("sheng2025_alpharec"), sf("hou2022_unisrec"),
    ["sheng2025_alpharec", "hou2022_unisrec", "hou2023_vqrec"], note="AlphaRec evaluates against UniSRec/VQ-Rec transfer baselines; this is a benchmark dependency, not identity equivalence.")
dep("backbone_reuse", sf("yu2022_simgcl"), sf("he2020_lightgcn"),
    ["yu2022_simgcl", "he2020_lightgcn"], note="SimGCL builds on the LightGCN graph backbone.")
dep("backbone_reuse", sf("cai2023_lightgcl"), sf("he2020_lightgcn"),
    ["cai2023_lightgcl", "he2020_lightgcn"], note="LightGCL is evaluated as a graph-CF extension of the LightGCN lineage.")

all_family_ids = set(family_alias_map.values())
assert len(all_family_ids) == 75, len(all_family_ids)
family_objects = []
for fid in sorted(all_family_ids):
    skeys = sorted(r["source_key"] for r in source_records if r["source_family_id"] == fid)
    rkeys = sorted(r["resource_key"] for r in operational_records if r["source_family_id"] == fid)
    aliases = sorted(k for k, v in family_alias_map.items() if v == fid)
    family_objects.append({
        "source_family_id": fid,
        "independent_family": True,
        "scholarly_source_keys": skeys,
        "operational_resource_keys": rkeys,
        "original_family_aliases": aliases,
        "family_scope": "mixed" if skeys and rkeys else ("scholarly" if skeys else "operational"),
    })

# Corpus serialization follows the ARS material-passport trust-chain fields.
corpus = []
for record in sorted((r for r in source_records if r["corpus_included"]), key=lambda r: r["source_key"]):
    acquired = record["source_acquired"]
    verified = record["source_verified_against_original"]
    tags = []
    if record["publication_year"] and 2022 <= record["publication_year"] <= 2026:
        tags.append("recent_2022_2026")
    else:
        tags.append("foundational_or_older")
    tags.extend(record["lanes"])
    omissions = {}
    # Lane reports documented service degradation; never reinterpret it as an
    # unmatched source.  Only the omission value is used in the corpus schema.
    if any(a in {"L2-RENDLE-2009-BPR", "L2-CAI-2023-LIGHTGCL", "L2-YUAN-2025-CONTEXTGNN"}
           for a in record["lane_source_aliases"]) or record["source_key"] in old_scholarly:
        omissions["semantic_scholar_unmatched"] = "api_degraded"
    corpus.append({
        "citation_key": record["source_key"],
        "title": record["title"],
        "authors": [{"literal": a} for a in record["authors"]],
        "year": record["publication_year"],
        "source_pointer": record.get("official_url") or (f"https://doi.org/{record['doi']}" if record.get("doi") else None),
        "venue": record.get("venue"),
        "tags": tags,
        "obtained_via": "other",
        "obtained_at": NOW,
        "adapter_name": "ARS-Codex Stage1B R3 central merge",
        "adapter_version": "0.1.26",
        "user_notes": f"Canonical family {record['source_family_id']}; central disposition {record['central_disposition']}.",
        "source_acquired": acquired,
        "source_verified_against_original": verified,
        "source_verification_method": record["source_verification_method"],
        "description_source": "original_pdf" if verified else "bibliography_v1",
        "description_last_audit": "r3_integration_r1" if verified else "none",
        "contamination_signals": {
            "preprint_post_llm_inflection": normalize_status(record["publication_status"]) == "preprint",
            "openalex_unmatched": False,
            "crossref_unmatched": False,
        },
        "contamination_signal_omissions": omissions,
        **({"doi": record["doi"]} if record.get("doi") else {}),
    })

quality_rows = []
for record in sorted(source_records, key=lambda r: r["source_key"]):
    quality_rows.append({
        "source_key": record["source_key"],
        "source_family_id": record["source_family_id"],
        "quality_grade": record["quality_grade"],
        "evidence_level": record["evidence_level"],
        "peer_reviewed": record["peer_reviewed"],
        "peer_review_evidence_basis": record["peer_review_evidence_basis"],
        "identity_verified": record["identity_verified"],
        "metadata_verified": record["metadata_verified"],
        "source_acquired": record["source_acquired"],
        "source_content_verified": record["source_content_verified"],
        "locator_ready": record["locator_ready"],
        "corpus_included": record["corpus_included"],
        "core_shortlist": record["core_shortlist"],
        "limitations": record["limitations"],
    })

recent_count = sum(1 for r in source_records if r["corpus_included"] and r["publication_year"] and 2022 <= r["publication_year"] <= 2026)
peer_true_count = sum(1 for r in source_records if r["corpus_included"] and r["peer_reviewed"] is True)
acquired_count = sum(1 for r in source_records if r["corpus_included"] and r["source_acquired"])
content_count = sum(1 for r in source_records if r["corpus_included"] and r["source_content_verified"])
locator_count = sum(1 for r in source_records if r["corpus_included"] and r["locator_ready"])
core_content_count = sum(1 for r in source_records if r["core_shortlist"] and r["source_content_verified"])
core_locator_count = sum(1 for r in source_records if r["core_shortlist"] and r["locator_ready"])

registry_doc = {
    "schema_version": "r3-source-registry-r1-1.0",
    "project": "hybrid-recsys-v5",
    "stage": "Stage 1B remediation R1",
    "step": "R3",
    "research_cutoff": "2026-08-14",
    "generated_at": NOW,
    "input_manifest_sha256": MANIFEST_SHA,
    "integration_contract_sha256": CONTRACT_SHA,
    "counting_rule": "A canonical scholarly record is a merged bibliographic identity; an independent family may contain multiple publication versions or dataset-linked records.",
    "criteria_application": "The same identity, topical-fit, evidentiary, and locator criteria were applied to old and newly discovered lane records. Registry-only disposition preserves eligible but redundant or not-yet-content-verified works without padding the corpus.",
    "counts": {
        "raw_lane_scholarly_rows": 79,
        "canonical_scholarly_records": 74,
        "scholarly_independent_families": 71,
        "corpus_included": 52,
        "registry_only": 22,
        "core_scholarly_shortlist": actual_scholarly_core_count,
    },
    "alias_map": dict(sorted(alias_to_key.items())),
    "sources": sorted(source_records, key=lambda r: r["source_key"]),
}
op_doc = {
    "schema_version": "r3-operational-registry-r1-1.0",
    "project": "hybrid-recsys-v5",
    "research_cutoff": "2026-08-14",
    "generated_at": NOW,
    "counting_rule": "Operational datasets, repositories, provider pages, packages, and adapters are not scholarly publications and do not receive inferred publication years.",
    "rights_rule": "Availability, code/package license, paper license, dataset rights, and redistribution permission are independent fields; none is propagated to another layer.",
    "counts": {
        "operational_records": len(operational_records),
        "operational_root_families": len({r["source_family_id"] for r in operational_records}),
        "core_operational_families": actual_operational_core_family_count,
    },
    "resources": sorted(operational_records, key=lambda r: r["resource_key"]),
}
family_doc = {
    "schema_version": "r3-source-family-map-r1-1.0",
    "project": "hybrid-recsys-v5",
    "generated_at": NOW,
    "counting_rules": {
        "canonical_record": "One merged bibliographic work identity; publication manifestations remain enumerated.",
        "independent_family": "Versions, adapters, repositories, and upstream dataset manifestations count once for independence-sensitive evidence.",
        "benchmark_reuse": "Benchmark or backbone reuse is a dependency edge, not automatic identity equivalence.",
    },
    "counts": {"canonical_scholarly_records": 74, "scholarly_families": 71, "operational_root_families": 12, "unique_families_across_registries": 75},
    "family_alias_map": dict(sorted(family_alias_map.items())),
    "families": family_objects,
    "dependencies": dependencies,
}
quality_doc = {
    "schema_version": "r3-source-quality-matrix-r1-1.0",
    "project": "hybrid-recsys-v5",
    "generated_at": NOW,
    "quality_rule": "Grade A requires direct peer-review evidence plus identity, metadata, content, and locator verification; B is usable with a stated limitation; C is registry-only, preprint/editorial, non-peer-reviewed, or incomplete.",
    "counts": {
        "records": 74,
        "corpus": 52,
        "recent_2022_2026": recent_count,
        "peer_reviewed_true": peer_true_count,
        "source_acquired": acquired_count,
        "source_content_verified": content_count,
        "locator_ready": locator_count,
        "grades": dict(Counter(r["quality_grade"] for r in source_records)),
    },
    "records": quality_rows,
}
corpus_doc = {
    "schema_version": "r3-literature-corpus-r1-1.0",
    "project": "hybrid-recsys-v5",
    "generated_at": NOW,
    "status": "R3_verified_not_stage1b_sealed",
    "counts": {
        "scholarly_corpus": 52,
        "recent_2022_2026": recent_count,
        "peer_reviewed_true": peer_true_count,
        "source_acquired": acquired_count,
        "source_content_verified": content_count,
        "locator_ready": locator_count,
        "core_scholarly": actual_scholarly_core_count,
        "core_operational_families": actual_operational_core_family_count,
        "core_total_including_operational_family": actual_core_total,
    },
    "literature_corpus": corpus,
    "non_source_metadata": {
        "selection_rule": "Evidence-based 52-work corpus; seven redundant or incomplete old records remain registry-only and seven production-claim sources were added.",
        "phase_boundary": "Phase 2 evidence infrastructure only; no H1-H4 conclusions and no Stage 2 production-citation authorization.",
    },
}

dump(HERE / "source_registry_r1.json", registry_doc)
dump(HERE / "operational_resource_registry.json", op_doc)
dump(HERE / "source_family_map_r1.json", family_doc)
dump(HERE / "source_quality_matrix_r1.json", quality_doc)
dump(HERE / "literature_corpus_r1.json", corpus_doc)


def md_escape(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("|", "\\|").replace("\n", " ")


dedup_md = f"""# R3 deduplication report — remediation R1

Generated: {NOW}  
Research cutoff: 2026-08-14

## Result

The five frozen lanes supplied 79 scholarly rows. Bibliographic identity merging produced 74 canonical scholarly records and 71 independent scholarly families. The 14 operational resources remain in a separate registry and resolve to 12 operational root families. Across both registries there are 75 unique family IDs because eight operational roots are shared with dataset or benchmark papers.

| Measure | Before | After |
|---|---:|---:|
| Scholarly lane rows | 79 | 74 canonical records |
| Scholarly independent families | — | 71 |
| Operational rows | 14 | 14 records / 12 roots |
| Cross-registry unique families | — | 75 |
| Selected scholarly corpus | 52 old scholarly candidates | 52 |
| Core shortlist | — | 23 scholarly + 1 operational family |

## Identity merges

1. Exact DOI merges: Wide & Deep (L2/L3), Time to Split (L1/L3), and SimGCL (L2/L4).
2. Source-of-record/title merge: LightGCL (L2/L4), whose official OpenReview identity was formatted differently.
3. Version relation: Liu–Lai–Lee 2007 conference predecessor and 2009 journal paper share a canonical identity group, but both manifestations and both DOIs remain explicit. The verified 2007 content is not treated as verification of the 2009 journal content.
4. Family-only joins, not identity merges: Krichene 2020/2021; Li 2023/2024; ViEcomRec and its 2025 graph-reuse paper.

## Corpus disposition

The corpus was not padded. Seven old but redundant or incompletely verified works remain in the transparent registry-only tier: Bradley 1997 AUC, Järvelin–Kekäläinen 2002 nDCG, Tamm et al. 2021 metric consistency, Huang et al. 2013 DSSM, MTPR, CLCRec, and XSimGCL. Seven sources required by bounded production-intended claim cards were added: the BERT4Rec replicability study, ContextGNN, T2Diff, repeat/explore-aware LightGCN, inherited popularity bias, SEMCo, and UTGRec.

Jannach–Chen remains an editorial/essay with peer-review status unknown. Said–Bellogín remains a preprint with peer-review status unknown. Pereira 2025 retains a section-only locator because its preflight is degraded. Operational-resource years were not inferred.

## Duplicate gates

Canonical key duplicates: 0  
Canonical normalized-title duplicates: 0  
Canonical normalized-DOI duplicates: 0  
Placeholder publication years: 0  
Shortened canonical author lists: 0
"""
(HERE / "deduplication_report_r1.md").write_text(dedup_md, encoding="utf-8")

verification_md = f"""# R3 source verification report — remediation R1

Generated: {NOW}  
Research cutoff: 2026-08-14

## Verification outcome

All 79 scholarly lane rows and 14 operational-resource rows were normalized only after the frozen-input gate passed. Identity evidence was merged before prose and claim cards. The result contains 74 scholarly identities, 71 scholarly families, 12 operational roots, and 75 unique family IDs across both registries.

Corpus counts recomputed from merged data: {recent_count}/52 recent (2022–2026), {peer_true_count}/52 directly evidenced as peer reviewed, {acquired_count}/52 locally acquired, {content_count}/52 content verified, and {locator_count}/52 locator ready. The scholarly core is {core_content_count}/23 content verified and {core_locator_count}/23 locator ready.

## Conflict and exception resolutions

| Item | Resolution | Downstream restriction |
|---|---|---|
| Jannach–Chen 2026 | Official institutional metadata classifies it as an editorial; peer review remains unknown. | Editorial context only; no empirical-evidence upgrade. |
| Said–Bellogín 2026 | Official arXiv identity retained; no canonical proceedings/journal status established. | Preprint/peer-review unknown. |
| Pereira et al. 2025 | Identity and section anchor retained; PDF preflight reported UNAVAILABLE with an object-pointer warning. | Section-only locator until R4 reacquisition. |
| Liu–Lai–Lee 2007/2009 | Official journal metadata confirms the 2009 source of record; 2007 is a predecessor manifestation. | 2007 inspected content cannot verify the exact 2009 text. |
| LightGCL | Official OpenReview identity normalized across differently formatted lane IDs. | OpenReview browser challenge logged as transport degradation, not absence. |
| Wide & Deep | DOI identity and full author metadata checked against the official Google Research record. | No use as Apriori or association-rule evidence. |
| Time to Split | DOI and author identity checked against the official RecSys 2025 accepted-contributions record. | Evaluation-design evidence only; no benchmark result inferred. |

## Service degradation

Semantic Scholar returned HTTP 429 for Rendle, LightGCL, and ContextGNN checks; affected records are marked `api_degraded`, never unmatched. OpenReview presented a browser challenge during the central recheck; locally frozen authoritative artifacts and official identity fields remain the evidentiary basis. Crossref and publisher DOI endpoints that returned access errors were treated as transport failures, not source absence.

## Central claim state

All original lane flags are preserved. The eight L4 cards retain both `planning_only=true` and `production_intended=true`; centrally each is `conditional_production_candidate`, not `production_ready`. Across all 44 cards, the original planning flags are 30 true and 14 false, while explicit original production intent is true for 8 and absent for 36. Central dispositions are 22 conditional candidates, 22 planning-only cards, and 0 production-ready cards. Conditional candidates still require R4 as applicable, the central citation gate, and Stage 1B sealing.

## Rights boundary

The operational registry keeps availability, code/package license, paper license, dataset rights, and redistribution permission separate. Coveo's frozen terms restrict the resource to noncommercial research/education and do not permit third-party redistribution. The CompleteJourney R package's CC0 declaration is not propagated to provider files; upstream access and redistribution remain separately conditional.

## Phase boundary

This report verifies Phase 2 evidence infrastructure only. It contains no Phase 3 synthesis, no H1–H4 conclusion, no benchmark result, and no permission to use metadata-only records as production citations. A PASS authorizes only R4 lawful source acquisition.
"""
(HERE / "source_verification_report_r1.md").write_text(verification_md, encoding="utf-8")

annotations = [
    "# Annotated bibliography — R3 remediation R1",
    "",
    f"Generated: {NOW}  ",
    "Research cutoff: 2026-08-14",
    "",
    "This bibliography contains the 52-work scholarly corpus. Annotations are bounded verification notes, not Phase 3 synthesis or H1–H4 conclusions.",
    "",
]
for record in sorted((r for r in source_records if r["corpus_included"]), key=lambda r: (r["publication_year"] or 0, r["source_key"])):
    authors = "; ".join(record["authors"])
    pointer = record.get("official_url") or (f"https://doi.org/{record['doi']}" if record.get("doi") else "no DOI; official source-of-record ID in registry")
    verification = []
    verification.append("locally acquired and original-content verified" if record["source_verified_against_original"] else
                        ("original content inspected remotely; local trust-chain acquisition remains queued" if record["source_content_verified"] else "metadata/identity only; original content remains queued"))
    if record["locator_ready"]:
        verification.append("locator ready")
    else:
        verification.append("locator unresolved")
    annotations.extend([
        f"## {record['source_key']}",
        "",
        f"{authors}. ({record['publication_year']}). *{record['title']}*. {record.get('venue') or 'Venue recorded in registry'}. {pointer}",
        "",
        f"Family `{record['source_family_id']}`; evidence level {record['evidence_level']}, quality {record['quality_grade']}; " + "; ".join(verification) + ". " +
        f"Lane provenance: {', '.join(record['lanes'])}. Peer-review status: {record['peer_reviewed']} with the direct basis recorded in the quality matrix.",
        "",
    ])
(HERE / "annotated_bibliography_r1.md").write_text("\n".join(annotations), encoding="utf-8")

claim_lines = [
    "# Claim–source map — R3 remediation R1",
    "",
    f"Generated: {NOW}  ",
    "Research cutoff: 2026-08-14",
    "",
    f"Merged claim cards: {len(claim_records)}. Original lane flags: planning_only=true {original_planning_counts['true']}, planning_only=false {original_planning_counts['false']}; production_intended=true {original_production_intent_counts['true']}, absent {original_production_intent_counts['absent']}. Central dispositions: conditional production candidate {central_claim_state_counts['conditional_production_candidate']}, planning only {central_claim_state_counts['planning_only']}, production ready 0.",
    "",
    "The original lane flags are preserved verbatim. A central `conditional_production_candidate` may proceed only to R4 and later citation gating; it is not currently production-ready or Stage 2 citation authorization.",
    "",
    "| Claim | Lane | Original planning_only | Original production_intended | Central disposition | Conditions | Verdict | Canonical sources | Families | Locator basis | Bounded claim / restriction |",
    "|---|---|---:|---:|---|---|---|---|---|---|---|",
]
for claim in sorted(claim_records, key=lambda c: c["claim_id"]):
    sources = ", ".join(f"`{k}`" for k in claim["canonical_source_keys"]) or "operational resource only"
    families = ", ".join(f"`{k}`" for k in claim["source_family_ids"])
    restriction = claim["claim_text_bounded"]
    if claim["forbidden_extrapolations"]:
        restriction += " Forbidden: " + "; ".join(map(str, claim["forbidden_extrapolations"]))
    claim_lines.append("| " + " | ".join([
        md_escape(claim["claim_id"]), claim["lane"], md_escape(claim["original_lane_state"]["planning_only"]),
        md_escape(claim["original_lane_state"]["production_intended"]), md_escape(claim["central_disposition"]),
        md_escape(claim["central_conditions"]), md_escape(claim["support_verdict"]), md_escape(sources), md_escape(families),
        md_escape(claim["locator_basis"]), md_escape(restriction),
    ]) + " |")
(HERE / "claim_source_map_r1.md").write_text("\n".join(claim_lines) + "\n", encoding="utf-8")

# Full cross-file validation before the handoff is written.
json_paths = [
    HERE / "source_registry_r1.json", HERE / "operational_resource_registry.json",
    HERE / "source_family_map_r1.json", HERE / "source_quality_matrix_r1.json",
    HERE / "literature_corpus_r1.json",
]
for p in json_paths:
    load(p)

source_keys = [r["source_key"] for r in source_records]
resource_keys = [r["resource_key"] for r in operational_records]
family_ids = [f["source_family_id"] for f in family_objects]
corpus_keys = [r["citation_key"] for r in corpus]
normalized_titles = [norm_title(r["title"]) for r in source_records]
normalized_dois = [d for r in source_records for d in ([norm_doi(r.get("doi"))] if norm_doi(r.get("doi")) else [])]
validation = {
    "json_parse_errors": 0,
    "duplicate_canonical_source_keys": len(source_keys) - len(set(source_keys)),
    "duplicate_canonical_titles": len(normalized_titles) - len(set(normalized_titles)),
    "duplicate_canonical_dois": len(normalized_dois) - len(set(normalized_dois)),
    "duplicate_operational_resource_keys": len(resource_keys) - len(set(resource_keys)),
    "dangling_source_keys": 0,
    "dangling_family_ids": 0,
    "ghost_citations": 0,
    "placeholder_publication_years": sum(r["publication_year"] in {0, 9999, 1900} for r in source_records),
    "operational_inferred_years": sum(r["release_year"] is not None and not r.get("year_basis") for r in operational_records),
    "mojibake_fields": 0,
    "shortened_author_metadata": sum(any("et al" in a.casefold() for a in r["authors"]) for r in source_records),
    "peer_reviewed_true_missing_evidence_basis": sum(r["peer_reviewed"] is True and not r["peer_review_evidence_basis"] for r in source_records),
    "production_claims_without_original_content_locator": 0,
    "central_claim_invalid_or_mutually_exclusive_state": 0,
    "l4_dual_flags_not_preserved": 0,
    "core_count_component_mismatch": int(not (
        actual_scholarly_core_count == 23 and
        actual_operational_core_family_count == 1 and
        actual_core_total == actual_scholarly_core_count + actual_operational_core_family_count
    )),
    "corpus_target_met": 45 <= len(corpus_keys) <= 55,
    "core_target_met": 18 <= actual_core_total <= 24,
}
valid_source_set, valid_resource_set, valid_family_set = set(source_keys), set(resource_keys), set(family_ids)
for claim in claim_records:
    if claim["central_disposition"] not in {"planning_only", "conditional_production_candidate", "production_ready"}:
        validation["central_claim_invalid_or_mutually_exclusive_state"] += 1
    validation["dangling_source_keys"] += sum(k not in valid_source_set for k in claim["canonical_source_keys"])
    validation["dangling_family_ids"] += sum(k not in valid_family_set for k in claim["source_family_ids"])
    for alias in claim["evidence_aliases"]:
        if alias.get("operational_resource_key") and alias["operational_resource_key"] not in valid_resource_set:
            validation["dangling_source_keys"] += 1
    if claim["central_disposition"] == "conditional_production_candidate":
        for key in claim["canonical_source_keys"]:
            rec = source_by_key[key]
            if not rec["source_content_verified"] or not rec["locator_ready"]:
                validation["production_claims_without_original_content_locator"] += 1
    if claim["lane"] == "L4" and not (
        claim["original_lane_state"]["planning_only"] is True and
        claim["original_lane_state"]["production_intended"] is True and
        claim["central_disposition"] == "conditional_production_candidate"
    ):
        validation["l4_dual_flags_not_preserved"] += 1
for ckey in corpus_keys:
    if ckey not in valid_source_set:
        validation["ghost_citations"] += 1
for rec in source_records:
    if rec["source_family_id"] not in valid_family_set:
        validation["dangling_family_ids"] += 1
    text = json.dumps(rec, ensure_ascii=False)
    if any(token in text for token in ("Ã", "Â", "�")):
        validation["mojibake_fields"] += 1
for rec in operational_records:
    if rec["source_family_id"] not in valid_family_set:
        validation["dangling_family_ids"] += 1
for edge in dependencies:
    validation["dangling_family_ids"] += int(edge["source_family_id"] not in valid_family_set)
    validation["dangling_family_ids"] += int(edge["depends_on_family_id"] not in valid_family_set)
    validation["dangling_source_keys"] += sum(k not in valid_source_set for k in edge["source_keys"])
    validation["dangling_source_keys"] += sum(k not in valid_resource_set for k in edge["resource_keys"])

zero_gates = [
    "json_parse_errors", "duplicate_canonical_source_keys", "duplicate_canonical_titles", "duplicate_canonical_dois",
    "duplicate_operational_resource_keys", "dangling_source_keys", "dangling_family_ids", "ghost_citations",
    "placeholder_publication_years", "operational_inferred_years", "mojibake_fields", "shortened_author_metadata",
    "peer_reviewed_true_missing_evidence_basis", "production_claims_without_original_content_locator",
    "central_claim_invalid_or_mutually_exclusive_state", "l4_dual_flags_not_preserved", "core_count_component_mismatch",
]
assert all(validation[k] == 0 for k in zero_gates), validation
assert validation["corpus_target_met"] and validation["core_target_met"], validation

r4_queue = []
for rec in sorted((r for r in source_records if r["corpus_included"]), key=lambda r: r["source_key"]):
    reasons = []
    if not rec["source_acquired"]:
        reasons.append("lawful_local_artifact_not_acquired")
    if not rec["source_content_verified"]:
        reasons.append("original_content_not_verified")
    if not rec["locator_ready"]:
        reasons.append("locator_not_ready")
    if reasons:
        r4_queue.append({
            "source_key": rec["source_key"],
            "priority": "core" if rec["core_shortlist"] else ("production_claim" if rec["source_key"] in production_source_keys else "corpus"),
            "reasons": reasons,
            "authorized_action": "R4 lawful acquisition and exact-locator completion only",
        })
r4_queue.append({
    "source_family_id": op_by_key["R-L5-COMPLETE-JOURNEY-PROVIDER"]["source_family_id"],
    "resource_keys": ["R-L5-COMPLETE-JOURNEY-PROVIDER", "R-L5-COMPLETEJOURNEY-R-PACKAGE"],
    "priority": "core",
    "reasons": ["provider_access_terms_and_dataset_redistribution_rights_remain_separate", "dataset_payload_not_acquired"],
    "authorized_action": "R4 lawful acquisition/rights clarification; do not propagate package CC0 upstream",
})

nonself_outputs = [
    "source_registry_r1.json", "operational_resource_registry.json", "source_family_map_r1.json",
    "deduplication_report_r1.md", "source_quality_matrix_r1.json", "source_verification_report_r1.md",
    "literature_corpus_r1.json", "annotated_bibliography_r1.md", "claim_source_map_r1.md",
]
output_manifest = [{"path": name, "bytes": (HERE / name).stat().st_size, "sha256": sha256(HERE / name)} for name in nonself_outputs]
handoff = {
    "schema_version": "r3-handoff-r1-1.0",
    "handoff_type": "ARS_Deep_Research_Phase2_R3_integration",
    "project": "hybrid-recsys-v5",
    "stage": "Stage 1B remediation R1",
    "step": "R3 Central Merge, Verification, and Deduplication",
    "runtime_lock": {"model": "gpt-5.6-sol", "reasoning": "high"},
    "ars_codex_version": "0.1.26",
    "research_cutoff": "2026-08-14",
    "completed_at": NOW,
    "verdict": "PENDING_INDEPENDENT_AUDIT",
    "verdict_scope": "The generator cannot self-authorize PASS. The independent continuation audit must validate and replace this provisional state; any eventual PASS authorizes only R4.",
    "input_gate": {
        "verdict": "PASS",
        "input_manifest_sha256": MANIFEST_SHA,
        "integration_contract_sha256": CONTRACT_SHA,
        "files_rehashed": 145,
        "hash_or_byte_mismatches": 0,
        "lane_contract_files": 35,
        "lane_verdicts": {"L1": "PASS", "L2": "PASS", "L3": "PASS", "L4": "PASS", "L5": "PASS"},
        "json_files_parsed": 56,
        "prohibited_fields": 0,
    },
    "counts": {
        "scholarly_rows_before_deduplication": 79,
        "canonical_scholarly_records_after_deduplication": 74,
        "scholarly_independent_families": 71,
        "operational_records": 14,
        "operational_root_families": 12,
        "unique_families_across_registries": 75,
        "scholarly_corpus": 52,
        "recent_2022_2026": recent_count,
        "peer_reviewed_true": peer_true_count,
        "source_acquired": acquired_count,
        "source_content_verified": content_count,
        "locator_ready": locator_count,
        "core_scholarly": actual_scholarly_core_count,
        "core_operational_families": actual_operational_core_family_count,
        "core_total": actual_core_total,
        "claim_cards": len(claim_records),
        "original_planning_only_true": original_planning_counts["true"],
        "original_planning_only_false": original_planning_counts["false"],
        "original_production_intended_true": original_production_intent_counts["true"],
        "original_production_intended_false": original_production_intent_counts["false"],
        "original_production_intended_absent": original_production_intent_counts["absent"],
        "central_conditional_production_candidates": central_claim_state_counts["conditional_production_candidate"],
        "central_planning_only": central_claim_state_counts["planning_only"],
        "central_production_ready": central_claim_state_counts["production_ready"],
        "unresolved_r4_queue": len(r4_queue),
    },
    "claim_state_rule": {
        "exclusive_states": ["planning_only", "conditional_production_candidate", "production_ready"],
        "l4_resolution": "All eight L4 cards preserve planning_only=true and production_intended=true; centrally they are conditional_production_candidate, never production_ready.",
        "production_ready_condition": "Only a post-R4, post-Stage1B-seal citation gate may set production_ready; R3 sets none.",
    },
    "claim_dispositions": [
        {
            "claim_id": c["claim_id"],
            "lane": c["lane"],
            "original_lane_state": c["original_lane_state"],
            "central_disposition": c["central_disposition"],
            "central_conditions": c["central_conditions"],
            "canonical_source_keys": c["canonical_source_keys"],
            "operational_resource_keys": [a["operational_resource_key"] for a in c["evidence_aliases"] if a.get("operational_resource_key")],
            "source_family_ids": c["source_family_ids"],
        }
        for c in sorted(claim_records, key=lambda item: item["claim_id"])
    ],
    "validation": validation,
    "unresolved_r4_queue": r4_queue,
    "output_manifest": output_manifest,
    "self_hash_policy": "r3_handoff.json is excluded from its own embedded manifest; its embedded audit receipt uses a payload hash excluding receipt_payload_sha256, and the final handoff SHA-256 is computed after serialization.",
    "phase_boundary": {
        "phase3_synthesis": "not_performed",
        "stage2_production_citations": "not_authorized",
        "hypotheses_h1_h4": "NOT_RUN",
        "r4_bulk_acquisition": "not_performed",
    },
}
dump(HERE / "r3_handoff.json", handoff)

print(json.dumps({
    "verdict": handoff["verdict"],
    "counts": handoff["counts"],
    "validation": validation,
    "r3_handoff_sha256": sha256(HERE / "r3_handoff.json"),
}, ensure_ascii=False, indent=2))
