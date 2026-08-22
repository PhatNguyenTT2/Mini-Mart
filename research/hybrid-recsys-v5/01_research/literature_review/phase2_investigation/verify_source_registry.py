#!/usr/bin/env python3
"""Run ARS tri-index verification against the frozen Stage 1B source registry.

This tool is read-only: it emits JSON to stdout and does not modify artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

def _year_from_crossref(item: dict[str, Any]) -> int | None:
    for field in ("issued", "published-print", "published-online"):
        parts = item.get(field, {}).get("date-parts", [])
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                pass
    return None

def _crossref_title(item: dict[str, Any]) -> str | None:
    title = item.get("title")
    if isinstance(title, list) and title:
        return str(title[0])
    if isinstance(title, str):
        return title
    return None

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--ars-scripts", required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--indexes",
        default="semantic_scholar,openalex,crossref",
        help="Comma-separated subset of semantic_scholar,openalex,crossref",
    )
    args = parser.parse_args()

    sys.path.insert(0, args.ars_scripts)
    from contamination_signals import SemanticScholarUnavailable
    from semantic_scholar_client import SemanticScholarClient
    from openalex_client import OpenAlexClient, OpenAlexUnavailable
    from crossref_client import CrossrefClient, CrossrefUnavailable

    registry_path = Path(args.registry)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    all_sources = registry["sources"]
    stop = None if args.limit <= 0 else args.start + args.limit
    sources = all_sources[args.start:stop]
    selected_indexes = {item.strip() for item in args.indexes.split(",") if item.strip()}

    s2 = SemanticScholarClient() if "semantic_scholar" in selected_indexes else None
    openalex = OpenAlexClient() if "openalex" in selected_indexes else None
    crossref = CrossrefClient() if "crossref" in selected_indexes else None

    records: list[dict[str, Any]] = []
    s2_batch_latched = False
    openalex_batch_latched = False
    crossref_batch_latched = False

    for index, source in enumerate(sources, start=args.start + 1):
        entry = {"title": source["title"], "year": source.get("year"), "doi": source.get("doi")}
        record: dict[str, Any] = {
            "ordinal": index,
            "citation_key": source["key"],
            "title": source["title"],
            "doi": source.get("doi"),
            "year": source.get("year"),
        }

        if "semantic_scholar" in selected_indexes and s2_batch_latched:
            record["semantic_scholar"] = {"state": "degraded", "reason": "batch_latched_after_api_degradation"}
        elif "semantic_scholar" in selected_indexes:
            try:
                assert s2 is not None
                result = s2.lookup(entry)
                record["semantic_scholar"] = {
                    "state": "matched" if result.get("matched") else "unmatched",
                    "paper_id": result.get("paperId"),
                }
            except SemanticScholarUnavailable as exc:
                reason = str(exc)
                record["semantic_scholar"] = {"state": "degraded", "reason": reason}
                if any(token in reason.lower() for token in ("network", "latched", "i/o", "429", "rate limit")):
                    s2_batch_latched = True

        if "openalex" in selected_indexes and openalex_batch_latched:
            record["openalex"] = {"state": "degraded", "reason": "batch_latched_after_api_degradation"}
        elif "openalex" in selected_indexes:
          try:
            assert openalex is not None
            oa_result = None
            if source.get("doi"):
                oa_result = openalex.doi_lookup_with_title_check(source["doi"], source["title"])
            if oa_result is None:
                oa_result = openalex.title_search(source["title"], source.get("year"))
            record["openalex"] = {
                "state": "matched" if oa_result else "unmatched",
                "id": oa_result.get("id") if oa_result else None,
                "title": oa_result.get("title") if oa_result else None,
                "year": oa_result.get("publication_year") if oa_result else None,
                "doi": oa_result.get("doi") if oa_result else None,
            }
          except OpenAlexUnavailable as exc:
            record["openalex"] = {"state": "degraded", "reason": str(exc)}
            openalex_batch_latched = True

        if "crossref" in selected_indexes and crossref_batch_latched:
            record["crossref"] = {"state": "degraded", "reason": "batch_latched_after_api_degradation"}
        elif "crossref" in selected_indexes:
          try:
            assert crossref is not None
            cr_result = None
            if source.get("doi"):
                cr_result = crossref.doi_lookup_with_title_check(source["doi"], source["title"])
            if cr_result is None:
                cr_result = crossref.title_search(source["title"], source.get("year"))
            record["crossref"] = {
                "state": "matched" if cr_result else "unmatched",
                "doi": cr_result.get("DOI") if cr_result else None,
                "title": _crossref_title(cr_result) if cr_result else None,
                "year": _year_from_crossref(cr_result) if cr_result else None,
            }
          except CrossrefUnavailable as exc:
            record["crossref"] = {"state": "degraded", "reason": str(exc)}
            crossref_batch_latched = True

        records.append(record)

    summary: dict[str, Any] = {"total": len(records)}
    for name in sorted(selected_indexes):
        summary[name] = {
            state: sum(1 for record in records if record[name]["state"] == state)
            for state in ("matched", "unmatched", "degraded")
        }

    print(json.dumps({"schema_version": "ars-tri-index-verification-1.0", "summary": summary, "records": records}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
