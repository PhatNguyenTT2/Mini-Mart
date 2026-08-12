"""Immutable snapshot construction with strict temporal and cold-start isolation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

from ai_service.config import Settings
from ai_service.contracts import SnapshotManifest, SplitName
from ai_service.data.sources import RawDataset
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError


@dataclass(frozen=True)
class Snapshot:
    manifest: SnapshotManifest
    snapshot_dir: Path
    catalog_df: pd.DataFrame
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    order_baskets_df: pd.DataFrame
    product_map: dict[int, int]
    raw_product_map: dict[int, int]
    user_map: dict[int, int]
    raw_user_map: dict[int, int]
    persona_map: dict[int, int]
    cold_item_ids: tuple[int, ...]
    price_boundaries: np.ndarray


def fit_price_boundaries(unit_prices: np.ndarray, num_buckets: int) -> np.ndarray:
    if unit_prices.size == 0:
        raise DataIntegrityError("warm catalog is empty")
    quantiles = np.linspace(0, 1, num_buckets + 1)[1:-1]
    return np.unique(np.quantile(unit_prices.astype(np.float64), quantiles))


def map_price_bucket(unit_price: float, boundaries: np.ndarray) -> int:
    return int(np.digitize(unit_price, boundaries) + 1)


def _frame_hash(frame: pd.DataFrame) -> bytes:
    normalized = frame.sort_index(axis=1).reset_index(drop=True)
    values = pd.util.hash_pandas_object(normalized, index=False).to_numpy(np.uint64)
    return bytes(values.tobytes())


def _content_hash(frames: tuple[pd.DataFrame, ...], cold_ids: tuple[int, ...]) -> str:
    digest = hashlib.sha256()
    for frame in frames:
        digest.update(_frame_hash(frame))
    digest.update(np.asarray(cold_ids, dtype=np.int64).tobytes())
    return digest.hexdigest()


def _metadata_sha256(frame: pd.DataFrame, columns: tuple[str, ...]) -> str | None:
    present = [column for column in columns if column in frame.columns]
    if not present:
        return None
    normalized = frame[present].sort_values(present, kind="stable").reset_index(drop=True)
    return hashlib.sha256(_frame_hash(normalized)).hexdigest()


def _semantic_cohort_document(events: pd.DataFrame) -> list[dict[str, object]]:
    """Materialize target-query metadata into the immutable snapshot."""

    rows = events.loc[
        events.event_origin.astype(str) == "semantic_trap",
        ["event_id", "user_id", "product_id", "event_ts", "cohort_id"],
    ].sort_values(["cohort_id", "event_ts", "event_id"], kind="stable")
    document: list[dict[str, object]] = []
    for (_, _), group in rows.groupby(["user_id", "cohort_id"], sort=False, dropna=False):
        ordered = group.sort_values(["event_ts", "event_id"], kind="stable")
        target_products = sorted(
            {
                int(row["product_id"])
                for row in ordered.to_dict(orient="records")
                if ":target:" in str(row["event_id"])
            }
        )
        prior_product: int | None = None
        for row in ordered.to_dict(orient="records"):
            event_id = str(row["event_id"])
            is_target = ":target:" in event_id
            record: dict[str, object] = {str(key): value for key, value in row.items()}
            record["anchor_product_id"] = prior_product
            record["target_product_ids"] = target_products if is_target else []
            document.append(record)
            prior_product = int(row["product_id"])
    return document


def _split_timestamp_groups(
    events: pd.DataFrame,
    *,
    train_count: int,
    val_count: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered = events.sort_values(["event_ts", "event_id"], kind="stable").reset_index(drop=True)
    group_sizes = ordered.groupby("event_ts", sort=True).size()
    if len(group_sizes) < 3:
        raise DataIntegrityError("at least three distinct timestamps are required")
    cumulative = group_sizes.cumsum().to_numpy()
    expected_boundaries = (train_count, train_count + val_count)
    if any(boundary not in cumulative for boundary in expected_boundaries):
        raise DataIntegrityError("a timestamp group crosses a frozen split boundary")
    train_group = int(np.searchsorted(cumulative, expected_boundaries[0], side="left"))
    val_group = int(np.searchsorted(cumulative, expected_boundaries[1], side="left"))
    timestamps = group_sizes.index
    train_end = timestamps[train_group]
    val_end = timestamps[val_group]
    train = ordered[ordered.event_ts <= train_end].copy().reset_index(drop=True)
    val = (
        ordered[(ordered.event_ts > train_end) & (ordered.event_ts <= val_end)]
        .copy()
        .reset_index(drop=True)
    )
    test = ordered[ordered.event_ts > val_end].copy().reset_index(drop=True)
    if train.empty or val.empty or test.empty:
        raise DataIntegrityError("temporal split produced an empty partition")
    return train, val, test


class SnapshotBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build(self, raw: RawDataset, snapshot_id: str | None = None) -> Snapshot:
        data = self.settings.data
        snapshot_id = snapshot_id or data.snapshot_id
        products = raw.products_df.copy()
        events = raw.events_df.copy()
        orders = raw.orders_df.copy()

        required_event_columns = {
            "event_id",
            "store_id",
            "user_id",
            "product_id",
            "persona_cluster",
            "event_type",
            "event_ts",
            "interaction_weight",
            "session_id",
            "event_origin",
            "cohort_id",
            "benchmark_run_id",
        }
        if missing := required_event_columns - set(events.columns):
            raise DataIntegrityError(f"missing event columns: {sorted(missing)}")
        if len(products) != data.num_items:
            raise DataIntegrityError(f"catalog count {len(products)} != {data.num_items}")
        if products.product_id.duplicated().any():
            raise DataIntegrityError("catalog product_id must be unique")
        if len(events) != data.expected_event_count:
            raise DataIntegrityError(
                f"event count {len(events)} != expected {data.expected_event_count}"
            )
        if events.event_id.duplicated().any():
            raise DataIntegrityError("event_id must be unique")
        if set(events.event_type.unique()) - {"view", "purchase"}:
            raise DataIntegrityError("event_type must be view or purchase")
        if events.session_id.isna().any() or (events.session_id.astype(str).str.len() == 0).any():
            raise DataIntegrityError("session_id must be non-empty")
        if set(events.event_origin.astype(str).unique()) - {
            "organic",
            "semantic_trap",
            "cold_start",
        }:
            raise DataIntegrityError("event_origin is outside the benchmark contract")
        expected_weights = events.event_type.map({"view": 0.5, "purchase": 1.0}).to_numpy(
            np.float32
        )
        actual_weights = events.interaction_weight.to_numpy(np.float32)
        if not np.isfinite(actual_weights).all() or not np.array_equal(
            actual_weights, expected_weights
        ):
            raise DataIntegrityError("interaction weights must be view=0.5 and purchase=1.0")
        if set(events.store_id.astype(int)) != {raw.store_id}:
            raise DataIntegrityError("event store does not match raw dataset store")
        if set(events.benchmark_run_id.astype(str)) != {raw.benchmark_run_id}:
            raise DataIntegrityError("events contain another benchmark lineage")

        product_ids = tuple(sorted(int(value) for value in products.product_id.unique()))
        cold_raw_ids = tuple(sorted(int(value) for value in raw.cold_product_ids))
        if (
            len(cold_raw_ids) != data.num_cold_items
            or len(set(cold_raw_ids)) != len(cold_raw_ids)
            or not set(cold_raw_ids) <= set(product_ids)
        ):
            raise DataIntegrityError("cold partition does not contain the expected catalog items")
        product_map = {raw_id: idx for idx, raw_id in enumerate(product_ids)}
        raw_product_map = {idx: raw_id for raw_id, idx in product_map.items()}

        user_ids = tuple(sorted(int(value) for value in events.user_id.unique()))
        if len(user_ids) != data.num_users:
            raise DataIntegrityError(f"user count {len(user_ids)} != {data.num_users}")
        user_map = {raw_id: idx + 1 for idx, raw_id in enumerate(user_ids)}
        raw_user_map = {idx: raw_id for raw_id, idx in user_map.items()}
        persona_counts = events.groupby("user_id").persona_cluster.nunique()
        if (persona_counts != 1).any():
            raise DataIntegrityError("each user must have exactly one persona")
        if not set(events.persona_cluster.astype(int)) <= set(range(data.num_personas)):
            raise DataIntegrityError("persona_cluster is outside the configured range")
        persona_map = {
            cast(int, user_id): int(persona)
            for user_id, persona in events.groupby("user_id").persona_cluster.first().items()
        }

        categories = tuple(sorted(int(value) for value in products.leaf_category_id.unique()))
        category_map = {raw_id: idx + 1 for idx, raw_id in enumerate(categories)}
        products["internal_product_id"] = products.product_id.map(product_map).astype(np.int64)
        products["internal_leaf_category_id"] = products.leaf_category_id.map(category_map).astype(
            np.int64
        )
        cold_internal = tuple(product_map[value] for value in cold_raw_ids)
        warm_products = products[~products.internal_product_id.isin(cold_internal)]
        boundaries = fit_price_boundaries(
            warm_products.unit_price.to_numpy(), data.num_price_buckets
        )
        products["price_bucket_id"] = products.unit_price.map(
            lambda value: map_price_bucket(float(value), boundaries)
        ).astype(np.int64)
        products = products.sort_values("internal_product_id", kind="stable").reset_index(drop=True)

        events["event_ts"] = pd.to_datetime(events.event_ts, utc=True)
        if events.event_ts.isna().any():
            raise DataIntegrityError("event_ts contains an invalid timestamp")
        events["internal_user_id"] = events.user_id.map(user_map).astype(np.int64)
        events["internal_product_id"] = events.product_id.map(product_map)
        if events.internal_product_id.isna().any():
            raise DataIntegrityError("events reference products outside the catalog")
        events["internal_product_id"] = events.internal_product_id.astype(np.int64)
        train, val, test = _split_timestamp_groups(
            events,
            train_count=data.expected_train_count,
            val_count=data.expected_val_count,
        )
        actual_split_counts = (len(train), len(val), len(test))
        expected_split_counts = (
            data.expected_train_count,
            data.expected_val_count,
            data.expected_test_count,
        )
        if actual_split_counts != expected_split_counts:
            raise DataIntegrityError(
                f"split counts {actual_split_counts} != expected {expected_split_counts}"
            )
        split_sessions = [set(frame.session_id.astype(str)) for frame in (train, val, test)]
        if any(
            split_sessions[left] & split_sessions[right] for left, right in ((0, 1), (0, 2), (1, 2))
        ):
            raise DataIntegrityError("session_id must not cross a temporal split boundary")

        cold_set = set(cold_internal)
        if cold_set & set(train.internal_product_id) or cold_set & set(val.internal_product_id):
            raise DataIntegrityError("cold items leaked into train or validation")
        warm_set = set(range(len(product_ids))) - cold_set
        if set(train.internal_product_id.astype(int)) != warm_set:
            raise DataIntegrityError("train split does not cover every warm catalog item")
        cold_test_purchases = set(
            test.loc[test.event_type == "purchase", "internal_product_id"].astype(int)
        )
        if missing_cold := cold_set - cold_test_purchases:
            raise DataIntegrityError(
                f"cold purchase ground truth missing for {len(missing_cold)} items"
            )
        if not (cold_test_purchases - cold_set):
            raise DataIntegrityError("test split has no warm purchase ground truth")
        if not (
            train.event_ts.max() < val.event_ts.min() and val.event_ts.max() < test.event_ts.min()
        ):
            raise DataIntegrityError("strict temporal boundaries are not satisfied")

        orders["order_ts"] = pd.to_datetime(orders.order_ts, utc=True)
        orders = orders[orders.order_ts <= train.event_ts.max()].copy()
        orders["internal_user_id"] = orders.user_id.map(user_map)
        orders["internal_product_id"] = orders.product_id.map(product_map)
        if orders.internal_product_id.isna().any():
            raise DataIntegrityError("orders reference products outside the catalog")
        if orders.internal_user_id.isna().any():
            raise DataIntegrityError("orders reference users outside the benchmark")
        orders["internal_product_id"] = orders.internal_product_id.astype(np.int64)
        if cold_set & set(orders.internal_product_id):
            raise DataIntegrityError("cold items leaked into train-period orders")
        if int(orders.order_id.nunique()) != data.expected_order_count:
            raise DataIntegrityError(
                f"train order count {orders.order_id.nunique()} != {data.expected_order_count}"
            )
        orders = orders.sort_values(["order_ts", "order_id", "internal_product_id"], kind="stable")

        content_sha = _content_hash((products, train, val, test, orders), cold_internal)
        cold_sha = hashlib.sha256(np.asarray(cold_raw_ids, dtype=np.int64).tobytes()).hexdigest()
        # Persist the serving query alongside every held-out target.  The
        # runtime semantic gate must not consult the tracked fixture to recover
        # an anchor/target mapping: the immutable snapshot is the authority.
        cohort_document = _semantic_cohort_document(events)
        cohort_json = json.dumps(
            cohort_document, sort_keys=True, default=str, separators=(",", ":")
        )
        semantic_cohort_sha = hashlib.sha256(cohort_json.encode("utf-8")).hexdigest()
        order_metadata_sha = _metadata_sha256(
            orders,
            ("benchmark_kind", "benchmark_template_id", "benchmark_trap_id"),
        )
        manifest = SnapshotManifest(
            artifact_id=snapshot_id,
            content_sha256=content_sha,
            parent_sha256={"cold_partition": cold_sha},
            benchmark_run_id=raw.benchmark_run_id,
            store_id=raw.store_id,
            source_kind=raw.source_kind,
            num_events=len(events),
            num_users=len(user_ids),
            num_items=len(product_ids),
            num_cold_items=len(cold_internal),
            split_counts={
                SplitName.TRAIN: len(train),
                SplitName.VAL: len(val),
                SplitName.TEST: len(test),
            },
            split_boundaries={
                "train_max": train.event_ts.max().to_pydatetime(),
                "val_min": val.event_ts.min().to_pydatetime(),
                "val_max": val.event_ts.max().to_pydatetime(),
                "test_min": test.event_ts.min().to_pydatetime(),
            },
            benchmark_spec_sha256=raw.benchmark_metadata.spec_sha256,
            semantic_cohort_sha256=semantic_cohort_sha,
            order_metadata_sha256=order_metadata_sha,
        )

        benchmark_spec_document: str | None = None
        if data.rule_feature_schema_version == "3.0.0":
            if data.benchmark_spec_path is None or not data.benchmark_spec_path.is_file():
                raise DataIntegrityError(
                    "R3 snapshot publication requires an explicit benchmark spec document"
                )
            try:
                parsed_spec = json.loads(data.benchmark_spec_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise DataIntegrityError("benchmark spec document cannot be read") from error
            benchmark_spec_document = json.dumps(parsed_spec, sort_keys=True, separators=(",", ":"))
            if (
                raw.benchmark_metadata.spec_sha256 is None
                or hashlib.sha256(benchmark_spec_document.encode("utf-8")).hexdigest()
                != raw.benchmark_metadata.spec_sha256
            ):
                raise DataIntegrityError("benchmark spec hash does not match database receipt")

        snapshots_root = data.artifact_root.resolve() / "snapshots"
        snapshots_root.mkdir(parents=True, exist_ok=True)
        destination = snapshots_root / snapshot_id
        if destination.exists():
            raise ArtifactIntegrityError(f"immutable snapshot already exists: {destination}")
        temporary = Path(tempfile.mkdtemp(prefix=f".{snapshot_id}-", dir=snapshots_root))
        try:
            products.to_parquet(temporary / "catalog.parquet", index=False)
            train.to_parquet(temporary / "train.parquet", index=False)
            val.to_parquet(temporary / "val.parquet", index=False)
            test.to_parquet(temporary / "test.parquet", index=False)
            orders.to_parquet(temporary / "train_orders.parquet", index=False)
            (temporary / "mappings.json").write_text(
                json.dumps(
                    {
                        "product_map": product_map,
                        "user_map": user_map,
                        "persona_map": persona_map,
                        "cold_raw_product_ids": cold_raw_ids,
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            np.save(temporary / "price_boundaries.npy", boundaries)
            (temporary / "semantic-cohort.json").write_text(
                cohort_json, encoding="utf-8", newline="\n"
            )
            if benchmark_spec_document is not None:
                (temporary / "benchmark-spec.json").write_text(
                    benchmark_spec_document, encoding="utf-8", newline="\n"
                )
            (temporary / "manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8"
            )
            os.replace(temporary, destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

        return Snapshot(
            manifest=manifest,
            snapshot_dir=destination,
            catalog_df=products,
            train_df=train,
            val_df=val,
            test_df=test,
            order_baskets_df=orders,
            product_map=product_map,
            raw_product_map=raw_product_map,
            user_map=user_map,
            raw_user_map=raw_user_map,
            persona_map=persona_map,
            cold_item_ids=cold_internal,
            price_boundaries=boundaries,
        )


def load_snapshot(snapshot_id: str, settings: Settings) -> Snapshot:
    path = settings.data.artifact_root.resolve() / "snapshots" / snapshot_id
    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        raise ArtifactIntegrityError(f"snapshot does not exist: {path}")
    manifest = SnapshotManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if settings.data.rule_feature_schema_version == "3.0.0":
        expanded_lineage = (
            manifest.benchmark_spec_sha256,
            manifest.semantic_cohort_sha256,
            manifest.order_metadata_sha256,
        )
        if not all(isinstance(value, str) for value in expanded_lineage):
            raise ArtifactIntegrityError(
                "v5 R3 snapshot manifest is missing expanded lineage hashes"
            )
    products = pd.read_parquet(path / "catalog.parquet")
    train = pd.read_parquet(path / "train.parquet")
    val = pd.read_parquet(path / "val.parquet")
    test = pd.read_parquet(path / "test.parquet")
    orders = pd.read_parquet(path / "train_orders.parquet")
    mappings = json.loads((path / "mappings.json").read_text(encoding="utf-8"))
    product_map = {int(key): int(value) for key, value in mappings["product_map"].items()}
    user_map = {int(key): int(value) for key, value in mappings["user_map"].items()}
    persona_map = {int(key): int(value) for key, value in mappings["persona_map"].items()}
    cold_internal = tuple(product_map[int(value)] for value in mappings["cold_raw_product_ids"])
    actual_sha = _content_hash((products, train, val, test, orders), cold_internal)
    if actual_sha != manifest.content_sha256:
        raise ArtifactIntegrityError("snapshot content checksum mismatch")
    if manifest.semantic_cohort_sha256 is not None:
        cohort_path = path / "semantic-cohort.json"
        if not cohort_path.is_file():
            raise ArtifactIntegrityError("snapshot semantic cohort is missing")
        cohort_sha = hashlib.sha256(cohort_path.read_bytes()).hexdigest()
        if cohort_sha != manifest.semantic_cohort_sha256:
            raise ArtifactIntegrityError("snapshot semantic cohort checksum mismatch")
        if settings.data.rule_feature_schema_version == "3.0.0":
            try:
                cohort_document = json.loads(cohort_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ArtifactIntegrityError("snapshot semantic cohort cannot be parsed") from error
            if not isinstance(cohort_document, list):
                raise ArtifactIntegrityError("snapshot semantic cohort must be a list")
            for row in cohort_document:
                if not isinstance(row, dict):
                    raise ArtifactIntegrityError("snapshot semantic cohort row is invalid")
                event_id = str(row.get("event_id", ""))
                if ":target:" not in event_id:
                    continue
                anchor = row.get("anchor_product_id")
                targets = row.get("target_product_ids")
                if not isinstance(anchor, int) or not isinstance(targets, list) or not targets:
                    raise ArtifactIntegrityError(
                        "v5 semantic cohort target is missing anchor/target metadata"
                    )
                if not all(isinstance(target, int) for target in targets):
                    raise ArtifactIntegrityError("v5 semantic cohort targets must be integers")
    if manifest.benchmark_spec_sha256 is not None:
        spec_path = path / "benchmark-spec.json"
        if not spec_path.is_file():
            raise ArtifactIntegrityError("snapshot benchmark spec is missing")
        try:
            spec_document = json.loads(spec_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ArtifactIntegrityError("snapshot benchmark spec cannot be parsed") from error
        canonical_spec = json.dumps(spec_document, sort_keys=True, separators=(",", ":"))
        if (
            hashlib.sha256(canonical_spec.encode("utf-8")).hexdigest()
            != manifest.benchmark_spec_sha256
        ):
            raise ArtifactIntegrityError("snapshot benchmark spec checksum mismatch")
    if manifest.order_metadata_sha256 is not None:
        order_sha = _metadata_sha256(
            orders,
            ("benchmark_kind", "benchmark_template_id", "benchmark_trap_id"),
        )
        if order_sha != manifest.order_metadata_sha256:
            raise ArtifactIntegrityError("snapshot order metadata checksum mismatch")
    return Snapshot(
        manifest=manifest,
        snapshot_dir=path,
        catalog_df=products,
        train_df=train,
        val_df=val,
        test_df=test,
        order_baskets_df=orders,
        product_map=product_map,
        raw_product_map={value: key for key, value in product_map.items()},
        user_map=user_map,
        raw_user_map={value: key for key, value in user_map.items()},
        persona_map=persona_map,
        cold_item_ids=cold_internal,
        price_boundaries=np.load(path / "price_boundaries.npy"),
    )
