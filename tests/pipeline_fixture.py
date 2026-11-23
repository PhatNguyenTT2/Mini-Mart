"""Tiny synthetic inputs for an end-to-end run of the pipeline stages.

``build(root)`` writes a canonical snapshot (TRAIN/VAL only), item features, a pair-rule table, a
sealed TEST file with its custody receipt, and a pipeline config. Users prefer one category and
buy items in fixed pairs, so every model has some signal; nothing here is real data.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from hybrid_recsys.adapters.instacart import InstacartTrainingBasket
from hybrid_recsys.data.pair_rules import materialize_pair_rules
from hybrid_recsys.hashing import canonical_json_sha256

USERS, ITEMS, CATEGORIES, DIM = 48, 24, 4, 384
EVENT_FIELDS = (
    "event_id",
    "raw_event_id",
    "user_id",
    "item_id",
    "timestamp",
    "event_type",
    "basket_id",
    "event_origin",
    "session_id",
    "cohort_id",
)
START = 1_767_225_600_000_000  # microseconds


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _events(rng: np.random.Generator) -> dict[str, list[tuple[int, int, str]]]:
    """(user, item, type) per split; items of one category come in pairs (2k, 2k+1)."""
    per_category = ITEMS // CATEGORIES
    splits: dict[str, list[tuple[int, int, str]]] = {"train": [], "val": [], "test": []}
    for user in range(USERS):
        category = user % CATEGORIES
        pool = [category * per_category + i for i in range(per_category)]
        for split, baskets in (("train", 3), ("val", 2), ("test", 2)):
            for _ in range(baskets):
                left = int(rng.choice(pool[::2]))
                items = [left, left + 1] if rng.random() < 0.8 else [left]
                if rng.random() < 0.3:
                    items.append(int(rng.integers(ITEMS)))
                for item in items:
                    splits[split].append((user, item, "purchase"))
                splits[split].append((user, int(rng.integers(ITEMS)), "view"))
    # Every item is observed in TRAIN, so the catalog is the full item set.
    splits["train"].extend((USERS - 1, item, "view") for item in range(ITEMS))
    return splits


@dataclass(frozen=True)
class _RuleView:
    baskets: tuple[tuple[int, int, tuple[int, ...]], ...]
    raw_item_ids: tuple[int, ...]
    manifest_sha256: str = "0" * 64

    @property
    def test_access_state(self) -> str:
        return "LOCKED_NOT_ACCESSED"

    def iter_train_baskets(self) -> Iterator[InstacartTrainingBasket]:
        for index, (user, number, items) in enumerate(self.baskets):
            yield InstacartTrainingBasket(user, number, index, items)


def build(root: Path) -> Path:
    rng = np.random.default_rng(7)
    raw_users = [1000 + u for u in range(USERS)]
    raw_items = [500 + 3 * i for i in range(ITEMS)]
    splits = _events(rng)

    snapshot = root / "snapshot"
    snapshot.mkdir(parents=True)
    rows: dict[str, list[dict]] = {}
    sealed: list[dict] = []
    baskets: list[dict] = []
    event_id = 0
    for split, events in splits.items():
        rows[split] = []
        for user, item, kind in events:
            timestamp = START + event_id * 60_000_000
            row = {
                "event_id": event_id,
                "raw_event_id": f"synthetic:{split}:{event_id:09d}",
                "user_id": user,
                "item_id": item,
                "timestamp": timestamp,
                "event_type": kind,
                "basket_id": None,
                "event_origin": "organic",
                "session_id": f"synthetic:{split}:{user}",
                "cohort_id": None,
            }
            event_id += 1
            if split != "test":
                rows[split].append(row)
                continue
            moment = datetime.fromtimestamp(timestamp / 1_000_000, tz=UTC)
            sealed.append(
                {
                    "raw_event_id": row["raw_event_id"],
                    "raw_user_id": raw_users[user],
                    "raw_item_id": raw_items[item],
                    "event_ts": moment.isoformat().replace("+00:00", "Z"),
                    "event_type": kind,
                    "event_origin": "organic",
                    "session_id": row["session_id"],
                    "cohort_id": None,
                }
            )
    by_user: dict[int, list[int]] = {}
    for row in rows["train"]:
        if row["event_type"] == "purchase":
            by_user.setdefault(row["user_id"], []).append(row["item_id"])
    for user, items in sorted(by_user.items()):
        groups = [sorted(set(items[s : s + 3])) for s in range(0, len(items), 3)]
        for number, group in enumerate(g for g in groups if len(g) > 1):
            baskets.append(
                {
                    "basket_id": f"b{user}-{number}",
                    "user_id": user,
                    "timestamp": START + len(baskets),
                    "item_ids": group,
                    "origin": "organic",
                }
            )
    users = [{"user_id": u, "raw_user_id": raw} for u, raw in enumerate(raw_users)]
    items = [
        {
            "item_id": i,
            "raw_item_id": raw,
            "text": f"synthetic item {i}",
            "category": f"category {i // (ITEMS // CATEGORIES)}",
            "price": float(10 + i),
        }
        for i, raw in enumerate(raw_items)
    ]
    for name, content in (
        ("users", users),
        ("items", items),
        ("baskets", baskets),
        ("train", rows["train"]),
        ("val", rows["val"]),
    ):
        _jsonl(snapshot / f"{name}.jsonl", content)
    payload = {"users": users, "items": items, "training_baskets": baskets, "splits": rows}
    manifest = {
        "schema_version": "dataset-manifest/1.1",
        "dataset_id": "synthetic-pipeline-fixture",
        "source_kind": "fixture",
        "source_locator": "tests/pipeline_fixture.py",
        "dataset_sha256": canonical_json_sha256(payload),
        "num_users": USERS,
        "num_items": ITEMS,
        "num_interactions": sum(map(len, splits.values())),
        "num_cold_items": 0,
        "raw_user_map_sha256": canonical_json_sha256({"raw_user_ids": raw_users}),
        "raw_item_map_sha256": canonical_json_sha256({"raw_item_ids": raw_items}),
        "split_hashes": {
            "train": canonical_json_sha256({"split": "train", "rows": rows["train"]}),
            "val": canonical_json_sha256({"split": "val", "rows": rows["val"]}),
            "test": canonical_json_sha256({"split": "test", "rows": sealed}),
        },
        "item_feature_hashes": {
            name: canonical_json_sha256(
                {name: [{"item_id": row["item_id"], name: row[name]} for row in items]}
            )
            for name in ("text", "category", "price")
        },
        "cold_item_ids": [],
        "event_schema": list(EVENT_FIELDS),
        "id_convention": "dense_zero_based_internal_raw_ids_preserved",
        "basket_field": "baskets.jsonl",
        "provenance_status": "FIXTURE_ONLY",
        "license_status": "TEST_ONLY",
        "num_baskets": len(baskets),
        "basket_sha256": canonical_json_sha256({"training_baskets": baskets}),
        "source_bundle_sha256": "0" * 64,
        "source_artifact_hashes": {"generator": "0" * 64},
        "behavior_nature": "SYNTHETIC_FIXTURE",
        "observed_behavior": False,
        "language_status": "UNSPECIFIED",
    }
    (snapshot / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    features = root / "features"
    features.mkdir()
    np.save(features / "raw_item_ids.npy", np.asarray(raw_items, dtype=np.int64))
    category = np.asarray([i // (ITEMS // CATEGORIES) for i in range(ITEMS)], dtype=np.int64)
    np.save(features / "category_ids.npy", category)
    text = rng.normal(size=(ITEMS, DIM)).astype(np.float32) + category[:, None].astype(np.float32)
    np.save(features / "text_embeddings.npy", text / np.linalg.norm(text, axis=1, keepdims=True))

    view = _RuleView(
        tuple((b["user_id"], n + 1, tuple(b["item_ids"])) for n, b in enumerate(baskets)),
        tuple(raw_items),
    )
    materialize_pair_rules(view, root=root / "rules", min_support_fraction=0.001).close()

    work = root / "work"
    custody = work / "custody"
    custody.mkdir(parents=True)
    data = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in sealed).encode()
    (custody / "test_source_events.jsonl").write_bytes(data)
    receipt = {
        "reseed": 0,
        "test_events": len(sealed),
        "test_source_sha256": hashlib.sha256(data).hexdigest(),
        "metrics_computed": False,
    }
    (custody / "custody_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")

    config = root / "config.json"
    config.write_text(
        json.dumps(
            {
                "snapshot_root": "snapshot",
                "feature_root": "features",
                "rules_root": "rules",
                "work_root": "work",
                "seeds": [1, 2],
                "lambda_grid": [0.5, 1.0],
                "wd_lr_grid": [0.001, 0.01],
                "deep_epochs": 2,
                "wd_max_epochs": 2,
                "wd_patience": 1,
                "reference_max_epochs": 2,
                "reference_patience": 1,
                "itemknn_k": 5,
                "bpr": {"embedding_size": 8, "learning_rate": 0.01},
                "lightgcn": {"embedding_size": 8, "learning_rate": 0.01, "n_layers": 1},
                "cohort_gates": {
                    "eligible_users_min": 10,
                    "novel_positive_events_min": 10,
                    "distinct_target_items_min": 5,
                },
                "bootstrap_replicates": 50,
                "device": "cpu",
            }
        ),
        encoding="utf-8",
    )
    return config
