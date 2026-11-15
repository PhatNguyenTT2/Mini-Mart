from __future__ import annotations

import csv
import gzip
from pathlib import Path
from typing import Any

import numpy as np

from ai_service_v2.hashing import canonical_json_bytes, sha256_file


def _write_csv_gz(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_npy(path: Path, values: list[int], dtype: np.dtype[Any]) -> None:
    with path.open("wb") as stream:
        np.save(stream, np.asarray(values, dtype=dtype), allow_pickle=False)


def build_instacart_runtime_fixture(root: Path) -> tuple[Path, str]:
    root.mkdir()
    source_root = root / "source"
    source_root.mkdir()
    multiplier = 10
    admitted_users = [
        {"user_id": 10, "test_order_id": 103, "max_order_number": 3, "validation_order_id": 102},
        {"user_id": 20, "test_order_id": 203, "max_order_number": 3, "validation_order_id": 202},
        {"user_id": 30, "test_order_id": 303, "max_order_number": 3, "validation_order_id": 302},
    ]
    candidate_ids = [2, 4, 7]
    features = [
        {
            "product_id": product_id,
            "item_text": f"product {product_id}",
            "item_category": "department_id=1|aisle_id=2",
            "aisle_id": 2,
            "department_id": 1,
        }
        for product_id in candidate_ids
    ]
    assignments = [
        {"user_id": 10, "order_number": 1, "order_id": 101, "split": "train"},
        {"user_id": 10, "order_number": 2, "order_id": 102, "split": "validation"},
        {"user_id": 10, "order_number": 3, "order_id": 103, "split": "TEST_LOCKED"},
        {"user_id": 20, "order_number": 1, "order_id": 201, "split": "train"},
        {"user_id": 20, "order_number": 2, "order_id": 202, "split": "validation"},
        {"user_id": 20, "order_number": 3, "order_id": 203, "split": "TEST_LOCKED"},
        {"user_id": 30, "order_number": 1, "order_id": 301, "split": "train"},
        {"user_id": 30, "order_number": 2, "order_id": 302, "split": "validation"},
        {"user_id": 30, "order_number": 3, "order_id": 303, "split": "TEST_LOCKED"},
    ]
    novel_targets = [
        {"user_id": 10, "validation_order_id": 102, "product_id": 7},
        {"user_id": 20, "validation_order_id": 202, "product_id": 2},
    ]
    target_audit = [
        {
            "user_id": row["user_id"],
            "validation_order_id": row["validation_order_id"],
            "product_id": row["product_id"],
            "in_train_catalog": 1,
            "seen_in_train": 0,
            "novel_positive": 1,
        }
        for row in novel_targets
    ]

    _write_csv_gz(
        root / "admitted_users.csv.gz",
        ["user_id", "test_order_id", "max_order_number", "validation_order_id"],
        admitted_users,
    )
    _write_csv_gz(
        root / "candidate_catalog.csv.gz",
        ["product_id"],
        [{"product_id": value} for value in candidate_ids],
    )
    _write_csv_gz(
        root / "candidate_features.csv.gz",
        ["product_id", "item_text", "item_category", "aisle_id", "department_id"],
        features,
    )
    _write_npy(root / "candidate_product_ids.npy", candidate_ids, np.dtype(np.int32))
    _write_csv_gz(
        root / "order_assignments.csv.gz",
        ["user_id", "order_number", "order_id", "split"],
        assignments,
    )
    _write_csv_gz(
        root / "product_features.csv.gz",
        ["product_id", "item_text", "item_category", "aisle_id", "department_id"],
        features,
    )
    train_keys = [
        10 * multiplier + 2,
        10 * multiplier + 4,
        20 * multiplier + 4,
        30 * multiplier + 7,
    ]
    novel_keys = [10 * multiplier + 7, 20 * multiplier + 2]
    _write_npy(root / "train_seen_user_item_keys.npy", train_keys, np.dtype(np.int64))
    _write_csv_gz(
        root / "validation_eligible_users.csv.gz",
        ["user_id"],
        [{"user_id": 10}, {"user_id": 20}],
    )
    _write_csv_gz(
        root / "validation_novel_targets.csv.gz",
        ["user_id", "validation_order_id", "product_id"],
        novel_targets,
    )
    _write_npy(root / "validation_novel_user_item_keys.npy", novel_keys, np.dtype(np.int64))
    _write_csv_gz(
        root / "validation_target_audit.csv.gz",
        [
            "user_id",
            "validation_order_id",
            "product_id",
            "in_train_catalog",
            "seen_in_train",
            "novel_positive",
        ],
        target_audit,
    )
    prior_path = source_root / "order_products__prior.csv"
    with prior_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["order_id", "product_id", "add_to_cart_order", "reordered"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            [
                {"order_id": 101, "product_id": 2, "add_to_cart_order": 1, "reordered": 0},
                {"order_id": 101, "product_id": 4, "add_to_cart_order": 2, "reordered": 0},
                {"order_id": 102, "product_id": 7, "add_to_cart_order": 1, "reordered": 0},
                {"order_id": 201, "product_id": 4, "add_to_cart_order": 1, "reordered": 0},
                {"order_id": 202, "product_id": 2, "add_to_cart_order": 1, "reordered": 0},
                {"order_id": 301, "product_id": 7, "add_to_cart_order": 1, "reordered": 0},
                {"order_id": 302, "product_id": 2, "add_to_cart_order": 1, "reordered": 0},
            ]
        )

    artifacts = []
    for path in sorted(
        (candidate for candidate in root.iterdir() if candidate.is_file()),
        key=lambda value: value.name,
    ):
        artifacts.append(
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "contains_test_outcomes": False,
            }
        )
    locked_test_path = root / "source" / "order_products__train.csv"
    manifest: dict[str, object] = {
        "schema_version": "mp2-p3-instacart-runtime-materialization/1.0",
        "created_at": "2026-09-18T16:58:00+07:00",
        "dataset_id": "INSTACART_EXTERNAL",
        "materialized_root": str(root),
        "source_archive_sha256": "a" * 64,
        "source_archive_bytes": 1,
        "source_files": [
            {
                "name": "order_products__prior.csv",
                "absolute_path": str(prior_path),
                "bytes": prior_path.stat().st_size,
                "sha256": sha256_file(prior_path),
                "header": ["order_id", "product_id", "add_to_cart_order", "reordered"],
                "row_content_parsed": True,
            },
            {
                "name": "order_products__train.csv",
                "absolute_path": str(locked_test_path),
                "bytes": 1,
                "sha256": "c" * 64,
                "header": ["order_id", "product_id", "add_to_cart_order", "reordered"],
                "row_content_parsed": False,
            },
        ],
        "test_boundary": {
            "test_outcome_file": "order_products__train.csv",
            "content_parsed": False,
            "inspection_scope": "ARCHIVE_CRC_FILE_HASH_AND_HEADER_ONLY",
            "test_result_rows": 0,
        },
        "split_order_counts": {"train": 3, "validation": 3, "TEST_LOCKED": 3},
        "cohort": {
            "provider_prior_rows": 8,
            "ignored_unadmitted_prior_rows": 0,
            "train_interaction_rows": 4,
            "validation_interaction_rows": 2,
            "train_distinct_user_item_pairs": 4,
            "validation_distinct_user_item_pairs": 2,
            "candidate_item_count": 3,
            "validation_outside_catalog_count": 0,
            "validation_seen_repeat_count": 0,
            "validation_novel_positive_count": 2,
            "validation_eligible_user_count": 2,
            "validation_distinct_novel_item_count": 2,
            "duplicate_order_product_pairs": 0,
            "user_item_key_multiplier": multiplier,
            "main_cohort_gate": "PASS",
            "rule_aligned_gate": "PENDING_P4_TRAIN_ONLY_RULE_MINING",
        },
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "training_performed": False,
        "metrics_computed": False,
        "test_accessed": False,
    }
    manifest_path = root / "runtime_materialization_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return locked_test_path, sha256_file(manifest_path)
