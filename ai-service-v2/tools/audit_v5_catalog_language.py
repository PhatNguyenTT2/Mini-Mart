#!/usr/bin/env python3
"""Audit one private v5 catalog export without opening benchmark TEST results."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "catalog-language-audit/1.0"
EXPECTED_SOURCE_FILES = {
    "source_manifest.json",
    "benchmark_spec.json",
    "users.jsonl",
    "items.jsonl",
    "events.jsonl",
    "baskets.jsonl",
}
ITEM_FIELDS = {"raw_item_id", "name", "category", "vendor", "price", "partition"}
REVIEW_SALT = "ais-r2-v5-language-review-v1"
VIETNAMESE_ORTHOGRAPHIC = frozenset(
    "ăâđêôơưĂÂĐÊÔƠƯ"
    "áàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩị"
    "óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊ"
    "ÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ"
)
VIETNAMESE_RETAIL_LEXICON = frozenset(
    """
    ăn áo ba bánh băng bắp bột bò bông bưởi cà cá cải cam canh cao cay chả chai
    chanh cháo chén chua có cồn cơm cua cuộn củ dầu dẻo dừa đậm đặc đậu đen điện
    đường đông gà gạo gấu gia giấy giặt gió gói gội hạt hào hành hạnh hảo hầm heo
    hộp hương ít kem khăn khô khoai không khẩu kẹo lá lạnh lẩu lên liền lọ lốc lon
    lông lúa mặt mắm mật mè mềm mì miếng muối mùi mực nạc nấm ngậm ngon ngọt nguyên
    nhập nướng ớt pha phi phô phòng quả rau rửa sạch sấy sữa tã tắm tẩy táo tay tôm
    thạch thảo thơm thịt thùng thuốc tương tươi túi trứng uống vệ vị xả xay xanh
    xốt xúc xuất yến cho bé chai gói hộp thùng lon túi miếng cây bộ lít ml kg gram
    """.split()
)
TOKEN_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


class AuditError(RuntimeError):
    """Raised when immutable audit inputs violate the frozen contract."""


def _duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"duplicate JSON key: {key}")
        normalized = key.casefold()
        if normalized in folded:
            raise AuditError(f"case-colliding JSON keys: {folded[normalized]} / {key}")
        folded[normalized] = key
        result[key] = value
    return result


def _json_loads(payload: bytes, source: Path | str) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise AuditError(f"UTF-8 BOM is forbidden: {source}")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_duplicate_object_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuditError(f"non-finite JSON constant: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditError(f"invalid JSON: {source}") from error
    if not isinstance(value, dict):
        raise AuditError(f"JSON root must be an object: {source}")
    return value


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return _json_loads(path.read_bytes(), path)


def _load_items(source_root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items_path = source_root / "items.jsonl"
    file_hashes = manifest.get("file_sha256")
    if not isinstance(file_hashes, dict) or file_hashes.get("items.jsonl") != _sha256(items_path):
        raise AuditError("items.jsonl does not match source_manifest.json")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(items_path.read_bytes().splitlines(), start=1):
        if not line:
            raise AuditError(f"blank items.jsonl row: {line_number}")
        row = _json_loads(line, f"{items_path}:{line_number}")
        if set(row) != ITEM_FIELDS:
            raise AuditError(f"item fields violate contract at row {line_number}")
        if line != _canonical_json(row):
            raise AuditError(f"item row is not canonical JSON at row {line_number}")
        raw_id = row.get("raw_item_id")
        if isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id < 1:
            raise AuditError(f"invalid raw_item_id at row {line_number}")
        for field in ("name", "category", "vendor", "partition"):
            if not isinstance(row.get(field), str):
                raise AuditError(f"item.{field} is not a string at row {line_number}")
        if row["partition"] not in {"warm", "cold"}:
            raise AuditError(f"invalid item partition at row {line_number}")
        if isinstance(row.get("price"), bool) or not isinstance(row.get("price"), (int, float)):
            raise AuditError(f"invalid item price at row {line_number}")
        rows.append(row)
    ids = [int(row["raw_item_id"]) for row in rows]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise AuditError("item IDs must be unique and ascending")
    expected_items = manifest.get("expected_counts", {}).get("items")
    if len(rows) != expected_items:
        raise AuditError("item count does not match source manifest")
    return rows


def _split_sql_tuple(line: str) -> list[str]:
    raw = line.strip()
    if raw.endswith((",", ";")):
        raw = raw[:-1].rstrip()
    if len(raw) < 2 or raw[0] != "(" or raw[-1] != ")":
        raise AuditError("unsupported SQL tuple shape")
    values: list[str] = []
    buffer: list[str] = []
    quoted = False
    index = 1
    while index < len(raw) - 1:
        character = raw[index]
        if character == "'":
            if quoted and index + 1 < len(raw) - 1 and raw[index + 1] == "'":
                buffer.append("'")
                index += 2
                continue
            quoted = not quoted
        elif character == "," and not quoted:
            values.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(character)
        index += 1
    if quoted:
        raise AuditError("unterminated SQL string literal")
    values.append("".join(buffer).strip())
    return values


def _insert_rows(path: Path, table: str) -> list[list[str]]:
    marker = f"INSERT INTO {table} "
    rows: list[list[str]] = []
    active = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(marker):
            if active or rows:
                raise AuditError(f"multiple {table} INSERT blocks are unsupported: {path}")
            active = True
            continue
        if active and line.lstrip().startswith("("):
            rows.append(_split_sql_tuple(line))
            if line.rstrip().endswith(";"):
                active = False
    if active or not rows:
        raise AuditError(f"incomplete or missing {table} INSERT block: {path}")
    return rows


def _seed_catalog(path: Path) -> tuple[dict[int, str], dict[int, dict[str, Any]]]:
    categories: dict[int, str] = {}
    for row in _insert_rows(path, "category"):
        if len(row) != 5:
            raise AuditError(f"category tuple has {len(row)} fields: {path}")
        category_id = int(row[0])
        if category_id in categories:
            raise AuditError(f"duplicate category ID {category_id}: {path}")
        categories[category_id] = row[2]

    products: dict[int, dict[str, Any]] = {}
    for row in _insert_rows(path, "product"):
        if len(row) != 6:
            raise AuditError(f"product tuple has {len(row)} fields: {path}")
        raw_id = int(row[0])
        category_id = int(row[1])
        if raw_id in products or category_id not in categories:
            raise AuditError(f"invalid product/category identity {raw_id}: {path}")
        try:
            price = Decimal(row[3])
        except InvalidOperation as error:
            raise AuditError(f"invalid product price {raw_id}: {path}") from error
        products[raw_id] = {
            "name": row[2],
            "category": categories[category_id],
            "vendor": row[4],
            "price": price,
        }
    return categories, products


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _tuple_key(row: dict[str, Any], fields: tuple[str, ...]) -> tuple[Any, ...]:
    values: list[Any] = []
    for field in fields:
        value = row[field]
        values.append(_normalized(value) if isinstance(value, str) else Decimal(str(value)))
    return tuple(values)


def _duplicate_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    name_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    full_groups: Counter[tuple[Any, ...]] = Counter()
    for item in items:
        name_groups[_normalized(str(item["name"]))].append(item)
        full_groups[_tuple_key(item, ("name", "category", "vendor", "price"))] += 1
    duplicate_name_groups = [rows for rows in name_groups.values() if len(rows) > 1]
    duplicate_name_excess = sum(len(rows) - 1 for rows in duplicate_name_groups)
    conflicting_groups = [
        rows
        for rows in duplicate_name_groups
        if len({_tuple_key(row, ("category", "vendor", "price")) for row in rows}) > 1
    ]
    full_duplicate_excess = sum(count - 1 for count in full_groups.values() if count > 1)
    total = len(items)
    return {
        "normalization": "Unicode NFKC + casefold + collapsed whitespace",
        "normalized_name_duplicate_groups": len(duplicate_name_groups),
        "normalized_name_duplicate_excess_rows": duplicate_name_excess,
        "normalized_name_duplicate_excess_rate": duplicate_name_excess / total,
        "normalized_name_conflicting_metadata_groups": len(conflicting_groups),
        "normalized_name_conflicting_metadata_rows": sum(len(rows) for rows in conflicting_groups),
        "exact_normalized_full_metadata_duplicate_excess_rows": full_duplicate_excess,
        "exact_normalized_full_metadata_duplicate_excess_rate": full_duplicate_excess / total,
    }


def _tokens(value: str) -> set[str]:
    return {_normalized(token) for token in TOKEN_RE.findall(value)}


def _language_evidence(text: str, detector: Any) -> dict[str, Any]:
    detected = detector.detect_language_of(text)
    lexicon_hits = sorted(_tokens(text) & VIETNAMESE_RETAIL_LEXICON)
    return {
        "lingua_vietnamese": detected is not None and detected.name == "VIETNAMESE",
        "orthographic_vietnamese": any(char in VIETNAMESE_ORTHOGRAPHIC for char in text),
        "retail_lexicon_hits": lexicon_hits,
    }


def _hash_order(raw_id: int) -> str:
    return hashlib.sha256(f"{REVIEW_SALT}:{raw_id}".encode()).hexdigest()


def _semantic_trap_ids(spec: dict[str, Any]) -> set[int]:
    traps = spec.get("semantic_traps")
    if not isinstance(traps, list) or not traps:
        raise AuditError("benchmark spec has no semantic_traps")
    ids: set[int] = set()
    for trap in traps:
        if not isinstance(trap, dict) or not isinstance(trap.get("targets"), list):
            raise AuditError("malformed semantic trap")
        members = [trap.get("anchor"), *trap["targets"]]
        if any(isinstance(value, bool) or not isinstance(value, int) for value in members):
            raise AuditError("semantic trap IDs must be integers")
        ids.update(members)
    return ids


def _catalog_lineage(
    items: list[dict[str, Any]],
    catalog_seed: Path,
    historical_seed: Path,
    trap_ids: set[int],
) -> dict[str, Any]:
    _, catalog_products = _seed_catalog(catalog_seed)
    _, historical_products = _seed_catalog(historical_seed)
    exported_ids = {int(item["raw_item_id"]) for item in items}
    if exported_ids != set(catalog_products):
        raise AuditError("exported item IDs do not exactly equal catalog seed IDs")

    mismatches: list[int] = []
    for item in items:
        raw_id = int(item["raw_item_id"])
        expected = catalog_products[raw_id]
        if (
            str(item["name"]) != expected["name"]
            or str(item["category"]) != expected["category"]
            or str(item["vendor"]) != expected["vendor"]
            or Decimal(str(item["price"])) != expected["price"]
        ):
            mismatches.append(raw_id)
    if mismatches:
        raise AuditError(f"catalog seed metadata mismatch for {len(mismatches)} items")

    historical_sets = {
        "name": {_tuple_key(row, ("name",)) for row in historical_products.values()},
        "name_category": {
            _tuple_key(row, ("name", "category")) for row in historical_products.values()
        },
        "name_category_vendor": {
            _tuple_key(row, ("name", "category", "vendor")) for row in historical_products.values()
        },
        "full_metadata": {
            _tuple_key(row, ("name", "category", "vendor", "price"))
            for row in historical_products.values()
        },
    }
    fields = {
        "name": ("name",),
        "name_category": ("name", "category"),
        "name_category_vendor": ("name", "category", "vendor"),
        "full_metadata": ("name", "category", "vendor", "price"),
    }
    historical_matches = {
        label: sum(_tuple_key(item, tuple_fields) in historical_sets[label] for item in items)
        for label, tuple_fields in fields.items()
    }
    if not trap_ids <= exported_ids:
        raise AuditError("semantic-trap catalog IDs are missing from the export")
    return {
        "catalog_seed_path": catalog_seed.as_posix(),
        "catalog_seed_sha256": _sha256(catalog_seed),
        "catalog_seed_product_rows": len(catalog_products),
        "catalog_seed_exact_export_matches": len(items),
        "catalog_seed_exact_export_match_rate": 1.0,
        "historical_seed_path": historical_seed.as_posix(),
        "historical_seed_sha256": _sha256(historical_seed),
        "historical_seed_product_rows": len(historical_products),
        "historical_content_match_diagnostics": historical_matches,
        "semantic_trap_items": len(trap_ids),
        "non_trap_catalog_items": len(items) - len(trap_ids),
        "original_catalog_items": None,
        "controlled_addition_items": None,
        "composition_status": "UNRESOLVED_WITH_AVAILABLE_ACQUISITION_LINEAGE",
        "composition_reason": (
            "The export exactly matches seed-5000.sql, but no immutable acquisition manifest "
            "maps its non-trap rows to original versus controlled additions. Content matches "
            "against seed-1000.sql are diagnostics and are not promoted to lineage."
        ),
        "price_and_vendor_temporal_classification": "EXPORT_TIME_METADATA",
    }


def _select_review_sample(
    items: list[dict[str, Any]],
    evidence: dict[int, dict[str, Any]],
    trap_ids: set[int],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    selected: dict[int, set[str]] = defaultdict(set)
    disagreements = {
        raw_id for raw_id, result in evidence.items() if not bool(result["lingua_vietnamese"])
    }
    for raw_id in disagreements:
        selected[raw_id].add("all_lingua_single_language_disagreements")
    for raw_id in trap_ids:
        selected[raw_id].add("all_semantic_trap_items")
    for partition in ("warm", "cold"):
        candidates = [
            int(item["raw_item_id"])
            for item in items
            if item["partition"] == partition and int(item["raw_item_id"]) not in selected
        ]
        for raw_id in sorted(candidates, key=_hash_order)[:20]:
            selected[raw_id].add(f"deterministic_{partition}_sample")

    item_by_id = {int(item["raw_item_id"]): item for item in items}
    rows: list[dict[str, Any]] = []
    for raw_id in sorted(selected):
        item = item_by_id[raw_id]
        result = evidence[raw_id]
        rows.append(
            {
                "raw_item_id": raw_id,
                "name": item["name"],
                "category": item["category"],
                "vendor": item["vendor"],
                "partition": item["partition"],
                "lingua_vietnamese": result["lingua_vietnamese"],
                "orthographic_vietnamese": result["orthographic_vietnamese"],
                "retail_lexicon_hits": result["retail_lexicon_hits"],
                "review_strata": sorted(selected[raw_id]),
                "semantic_review_status": "PENDING_REVIEW",
            }
        )
    return rows, {
        "total_unique_rows": len(rows),
        "lingua_disagreements": len(disagreements),
        "semantic_trap_items": len(trap_ids),
        "deterministic_warm_requested": 20,
        "deterministic_cold_requested": 20,
    }


def _all_language_smoke(items: list[dict[str, Any]], builder: Any) -> list[dict[str, Any]]:
    detector = builder.from_all_languages().build()
    by_id = {int(item["raw_item_id"]): item for item in items}
    smoke_ids = sorted(by_id)[:5]
    results: list[dict[str, Any]] = []
    for raw_id in smoke_ids:
        item = by_id[raw_id]
        text = f"{item['name']}. {item['category']}."
        values = detector.compute_language_confidence_values(text)[:3]
        results.append(
            {
                "raw_item_id": raw_id,
                "top_three": [
                    {"language": value.language.name, "confidence": value.value} for value in values
                ],
            }
        )
    return results


def run_audit(
    source_root: Path,
    benchmark_spec: Path,
    catalog_seed: Path,
    historical_seed: Path,
    detector_wheel: Path,
    expected_detector_sha256: str,
    output_root: Path,
) -> dict[str, Any]:
    if output_root.exists():
        raise AuditError(f"output root already exists: {output_root}")
    staging = output_root.with_name(f".{output_root.name}.staging")
    if staging.exists():
        raise AuditError(f"staging root already exists: {staging}")
    if {path.name for path in source_root.iterdir()} != EXPECTED_SOURCE_FILES:
        raise AuditError("source bundle does not contain the exact six-file set")
    manifest = _load_json(source_root / "source_manifest.json")
    if manifest.get("catalog_language_status") != "PENDING_POST_EXPORT_AUDIT":
        raise AuditError("source bundle is not pending post-export language audit")
    for name, expected_hash in manifest.get("file_sha256", {}).items():
        if _sha256(source_root / name) != expected_hash:
            raise AuditError(f"source file hash mismatch: {name}")
    items = _load_items(source_root, manifest)
    spec = _load_json(benchmark_spec)
    trap_ids = _semantic_trap_ids(spec)

    detector_hash = _sha256(detector_wheel)
    if detector_hash != expected_detector_sha256:
        raise AuditError("language-detector wheel hash does not match the frozen value")
    try:
        from lingua import Language, LanguageDetectorBuilder
    except ImportError as error:
        raise AuditError("lingua-language-detector is not installed") from error
    detector_version = importlib.metadata.version("lingua-language-detector")
    if detector_version != "1.4.2":
        raise AuditError(f"unexpected lingua-language-detector version: {detector_version}")
    detector = LanguageDetectorBuilder.from_languages(Language.VIETNAMESE).build()

    evidence: dict[int, dict[str, Any]] = {}
    for item in items:
        raw_id = int(item["raw_item_id"])
        text = f"{item['name']}. {item['category']}."
        evidence[raw_id] = _language_evidence(text, detector)

    total = len(items)
    lingua_pass = sum(bool(result["lingua_vietnamese"]) for result in evidence.values())
    orthographic_pass = sum(bool(result["orthographic_vietnamese"]) for result in evidence.values())
    lexicon_pass = sum(bool(result["retail_lexicon_hits"]) for result in evidence.values())
    combined_pass = sum(
        bool(result["lingua_vietnamese"])
        or (bool(result["orthographic_vietnamese"]) and bool(result["retail_lexicon_hits"]))
        for result in evidence.values()
    )
    review_rows, review_summary = _select_review_sample(items, evidence, trap_ids)
    lineage = _catalog_lineage(items, catalog_seed, historical_seed, trap_ids)
    audit = {
        "schema_version": SCHEMA_VERSION,
        "source_binding": {
            "source_bundle_id": manifest.get("source_bundle_id"),
            "source_manifest_file_sha256": _sha256(source_root / "source_manifest.json"),
            "source_manifest_canonical_sha256": hashlib.sha256(
                _canonical_json(manifest)
            ).hexdigest(),
            "items_sha256": _sha256(source_root / "items.jsonl"),
            "benchmark_spec_source_sha256": _sha256(benchmark_spec),
        },
        "catalog_counts": {
            "items": total,
            "warm_items": sum(item["partition"] == "warm" for item in items),
            "cold_items": sum(item["partition"] == "cold" for item in items),
            "nonempty_names": sum(bool(str(item["name"]).strip()) for item in items),
            "nonempty_categories": sum(bool(str(item["category"]).strip()) for item in items),
            "nonempty_vendors": sum(bool(str(item["vendor"]).strip()) for item in items),
        },
        "catalog_lineage": lineage,
        "duplicate_and_collision_audit": _duplicate_summary(items),
        "language_detector": {
            "package": "lingua-language-detector",
            "version": detector_version,
            "wheel_filename": detector_wheel.name,
            "wheel_sha256": detector_hash,
            "primary_configuration": "LanguageDetectorBuilder.from_languages(VIETNAMESE)",
            "primary_confidence_policy": (
                "Binary Vietnamese detection in one-language mode; no fabricated comparative "
                "confidence threshold. False negatives are reviewed using orthographic evidence, "
                "a frozen retail lexicon, and the private semantic-review sample."
            ),
            "all_language_smoke_role": "DIAGNOSTIC_ONLY_NOT_AN_ADMISSION_GATE",
            "all_language_smoke": _all_language_smoke(items, LanguageDetectorBuilder),
        },
        "language_coverage": {
            "lingua_single_language_vietnamese": lingua_pass,
            "lingua_single_language_rate": lingua_pass / total,
            "vietnamese_orthographic_evidence": orthographic_pass,
            "vietnamese_orthographic_rate": orthographic_pass / total,
            "retail_lexicon_evidence": lexicon_pass,
            "retail_lexicon_rate": lexicon_pass / total,
            "combined_automated_pass": combined_pass,
            "combined_automated_pass_rate": combined_pass / total,
            "lingua_disagreement_count": total - lingua_pass,
        },
        "semantic_review_sample": {
            **review_summary,
            "selection_salt": REVIEW_SALT,
            "selection_policy": (
                "all Lingua disagreements + all semantic-trap items + 20 deterministic "
                "previously-unselected items from each warm/cold partition"
            ),
            "reviewer_kind": "PENDING",
            "human_read_attested": False,
        },
        "automated_gate": {
            "minimum_lingua_rate": 0.99,
            "required_combined_rate": 1.0,
            "lingua_rate_pass": lingua_pass / total >= 0.99,
            "combined_rate_pass": combined_pass == total,
            "nonempty_field_pass": all(
                bool(str(item[field]).strip())
                for item in items
                for field in ("name", "category", "vendor")
            ),
            "verdict": "PASS_AUTOMATED_LANGUAGE_EVIDENCE_PENDING_SEMANTIC_REVIEW",
        },
        "scientific_state": {
            "RESULT_STATUS": "NOT_RUN",
            "TEST_SET_OPENED": "NO",
            "ACCEPTED_RESULT_ROWS": 0,
            "execution_authorized": False,
        },
    }
    if not all(
        (
            audit["automated_gate"]["lingua_rate_pass"],
            audit["automated_gate"]["combined_rate_pass"],
            audit["automated_gate"]["nonempty_field_pass"],
        )
    ):
        raise AuditError("automated language gate did not pass")

    try:
        staging.mkdir(parents=True)
        review_path = staging / "semantic_review_sample.jsonl"
        review_path.write_bytes(b"".join(_canonical_json(row) + b"\n" for row in review_rows))
        audit["semantic_review_sample"]["file_sha256"] = _sha256(review_path)
        (staging / "automated_language_audit.json").write_bytes(_canonical_json(audit) + b"\n")
        staging.replace(output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return {
        "status": "PASS_AUTOMATED_LANGUAGE_EVIDENCE_PENDING_SEMANTIC_REVIEW",
        "items": total,
        "lingua_vietnamese": lingua_pass,
        "combined_pass": combined_pass,
        "review_rows": len(review_rows),
        "output_root": str(output_root),
        "automated_audit_sha256": _sha256(output_root / "automated_language_audit.json"),
        "review_sample_sha256": _sha256(output_root / "semantic_review_sample.jsonl"),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--benchmark-spec", type=Path, required=True)
    parser.add_argument("--catalog-seed", type=Path, required=True)
    parser.add_argument("--historical-seed", type=Path, required=True)
    parser.add_argument("--detector-wheel", type=Path, required=True)
    parser.add_argument("--expected-detector-sha256", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_audit(
            source_root=args.source_root.resolve(),
            benchmark_spec=args.benchmark_spec.resolve(),
            catalog_seed=args.catalog_seed.resolve(),
            historical_seed=args.historical_seed.resolve(),
            detector_wheel=args.detector_wheel.resolve(),
            expected_detector_sha256=args.expected_detector_sha256,
            output_root=args.output_root.resolve(),
        )
    except (AuditError, OSError, ValueError) as error:
        print(json.dumps({"status": "AUDIT_FAILED", "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
