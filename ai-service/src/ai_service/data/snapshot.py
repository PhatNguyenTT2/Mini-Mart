"""Snapshot Builder and Artifact Manager with Temporal & Cold-Start Validation."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

from ai_service.config import Settings, DATA_ARTIFACTS_DIR
from ai_service.contracts import SnapshotManifestV2
from ai_service.errors import DataIntegrityError
from ai_service.data.sources import RawDataset, DatasetSource, PostgresDatasetSource, SyntheticDatasetSource


def fit_price_boundaries(unit_prices: np.ndarray, num_buckets: int = 8) -> np.ndarray:
    """Fit quantile price boundaries on warm product catalog."""
    quantiles = np.linspace(0, 100, num_buckets + 1)[1:-1]
    boundaries = np.percentile(unit_prices, quantiles)
    return np.unique(boundaries)


def map_price_bucket(unit_price: float, boundaries: np.ndarray) -> int:
    """Map unit price to 1-based bucket ID (1..8)."""
    return int(np.digitize(unit_price, boundaries) + 1)


@dataclass
class Snapshot:
    """Container for loaded dataset snapshot DataFrames and mappings."""

    manifest: SnapshotManifestV2
    snapshot_dir: Path
    catalog_df: pd.DataFrame
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    order_baskets_df: pd.DataFrame
    product_map: Dict[int, int]         # raw product_id -> internal_product_id (0..5199)
    raw_product_map: Dict[int, int]     # internal_product_id -> raw product_id
    user_map: Dict[int, int]            # raw user_id -> internal_user_id (1..5000)
    raw_user_map: Dict[int, int]        # internal_user_id -> raw user_id
    persona_map: Dict[int, int]         # raw user_id -> persona_cluster (0..7)
    cold_item_ids: List[int]            # internal cold item IDs (0..5199)
    price_boundaries: np.ndarray


class SnapshotBuilder:
    """Builds and validates versioned dataset snapshot artifacts."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def build(self, raw: RawDataset, snapshot_id: Optional[str] = None) -> Snapshot:
        if snapshot_id is None:
            snapshot_id = self.settings.data.snapshot_id

        out_dir = DATA_ARTIFACTS_DIR / snapshot_id
        out_dir.mkdir(parents=True, exist_ok=True)

        events_df = raw.events_df.copy()
        products_df = raw.products_df.copy()
        orders_df = raw.orders_df.copy()

        # 1. Product Mappings
        sorted_raw_products = sorted(products_df["product_id"].unique())
        product_map = {int(pid): int(idx) for idx, pid in enumerate(sorted_raw_products)}
        raw_product_map = {int(idx): int(pid) for idx, pid in enumerate(sorted_raw_products)}

        # 2. User Mappings
        sorted_raw_users = sorted(events_df["user_id"].unique())
        user_map = {int(uid): int(idx + 1) for idx, uid in enumerate(sorted_raw_users)}
        raw_user_map = {int(idx + 1): int(uid) for idx, uid in enumerate(sorted_raw_users)}

        # 3. Category & Persona Mappings
        sorted_leaf_cats = sorted(products_df["leaf_category_id"].unique())
        leaf_category_map = {int(cid): int(idx + 1) for idx, cid in enumerate(sorted_leaf_cats)}
        
        user_persona_df = events_df[["user_id", "persona_cluster"]].drop_duplicates()
        persona_map = dict(zip(user_persona_df["user_id"].values, user_persona_df["persona_cluster"].values))

        # 4. Identify 250 highest-ID products as Cold items
        cold_count = self.settings.data.num_cold_items
        cold_raw_ids = sorted_raw_products[-cold_count:]
        cold_internal_ids = [product_map[pid] for pid in cold_raw_ids]
        cold_set = set(cold_internal_ids)

        # 5. Add mapped columns
        products_df["internal_product_id"] = products_df["product_id"].map(product_map)
        products_df["internal_leaf_category_id"] = products_df["leaf_category_id"].map(leaf_category_map)

        # Fit price boundaries on warm catalog only
        warm_catalog = products_df[~products_df["internal_product_id"].isin(cold_set)]
        price_boundaries = fit_price_boundaries(warm_catalog["unit_price"].values, self.settings.data.num_price_buckets)

        products_df["price_bucket_id"] = products_df["unit_price"].apply(lambda p: map_price_bucket(p, price_boundaries))

        events_df["internal_user_id"] = events_df["user_id"].map(user_map)
        events_df["internal_product_id"] = events_df["product_id"].map(product_map)
        events_df["event_ts"] = pd.to_datetime(events_df["event_ts"], utc=True)

        orders_df["internal_user_id"] = orders_df["user_id"].map(user_map)
        orders_df["internal_product_id"] = orders_df["product_id"].map(product_map)
        if "created_at" in orders_df.columns:
            orders_df["order_ts"] = pd.to_datetime(orders_df["created_at"], utc=True)

        # 6. Perform Temporal 80/10/10 Split on Events
        events_df = events_df.sort_values(by=["event_ts", "event_id"]).reset_index(drop=True)
        total_events = len(events_df)
        train_end = int(0.80 * total_events)
        val_end = int(0.90 * total_events)

        train_df = events_df.iloc[:train_end].copy().reset_index(drop=True)
        val_df = events_df.iloc[train_end:val_end].copy().reset_index(drop=True)
        test_df = events_df.iloc[val_end:].copy().reset_index(drop=True)

        # 7. Validate Temporal Boundaries Invariant
        train_max_ts = train_df["event_ts"].max()
        val_min_ts = val_df["event_ts"].min()
        val_max_ts = val_df["event_ts"].max()
        test_min_ts = test_df["event_ts"].min()

        if train_max_ts >= val_min_ts:
            raise DataIntegrityError(f"Temporal Leakage Violation: train_max_ts ({train_max_ts}) >= val_min_ts ({val_min_ts})")
        if val_max_ts >= test_min_ts:
            raise DataIntegrityError(f"Temporal Leakage Violation: val_max_ts ({val_max_ts}) >= test_min_ts ({test_min_ts})")

        # 8. Validate Cold Item Isolation Invariant (C ^ Train = C ^ Val = Empty)
        train_items = set(train_df["internal_product_id"].unique())
        val_items = set(val_df["internal_product_id"].unique())
        
        train_cold_leak = cold_set.intersection(train_items)
        val_cold_leak = cold_set.intersection(val_items)

        if len(train_cold_leak) > 0:
            raise DataIntegrityError(f"Cold-Start Leakage Violation: {len(train_cold_leak)} cold items present in Train split!")
        if len(val_cold_leak) > 0:
            raise DataIntegrityError(f"Cold-Start Leakage Violation: {len(val_cold_leak)} cold items present in Val split!")

        # 9. Compute Checksum
        data_bytes = f"{len(train_df)}-{len(val_df)}-{len(test_df)}-{raw.source_kind}".encode("utf-8")
        checksum = hashlib.sha256(data_bytes).hexdigest()[:16]

        manifest = SnapshotManifestV2(
            store_id=self.settings.data.store_id,
            source_kind=raw.source_kind,
            num_events=total_events,
            num_users=len(sorted_raw_users),
            num_items=len(sorted_raw_products),
            num_cold_items=cold_count,
            train_count=len(train_df),
            val_count=len(val_df),
            test_count=len(test_df),
            train_max_ts=str(train_max_ts),
            val_min_ts=str(val_min_ts),
            val_max_ts=str(val_max_ts),
            test_min_ts=str(test_min_ts),
            checksum=checksum,
        )

        # Save Parquet artifacts
        products_df.to_parquet(out_dir / "catalog.parquet", index=False)
        train_df.to_parquet(out_dir / "train_events.parquet", index=False)
        val_df.to_parquet(out_dir / "val_events.parquet", index=False)
        test_df.to_parquet(out_dir / "test_events.parquet", index=False)
        orders_df.to_parquet(out_dir / "order_baskets.parquet", index=False)

        manifest_json = manifest.model_dump_json(indent=2)
        (out_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")

        return Snapshot(
            manifest=manifest,
            snapshot_dir=out_dir,
            catalog_df=products_df,
            train_df=train_df,
            val_df=val_df,
            test_df=test_df,
            order_baskets_df=orders_df,
            product_map=product_map,
            raw_product_map=raw_product_map,
            user_map=user_map,
            raw_user_map=raw_user_map,
            persona_map=persona_map,
            cold_item_ids=cold_internal_ids,
            price_boundaries=price_boundaries,
        )


def load_snapshot(snapshot_id: str = "scaled-v1", settings: Optional[Settings] = None) -> Snapshot:
    """Load pre-built snapshot artifacts from disk."""
    if settings is None:
        settings = Settings()

    snap_dir = DATA_ARTIFACTS_DIR / snapshot_id
    if not (snap_dir / "manifest.json").exists():
        # Fallback to building synthetic snapshot for standalone tests/CLI
        source = SyntheticDatasetSource(settings)
        raw = source.load(settings.data.store_id)
        builder = SnapshotBuilder(settings)
        return builder.build(raw, snapshot_id)

    manifest_data = (snap_dir / "manifest.json").read_text(encoding="utf-8")
    manifest = SnapshotManifestV2.model_validate_json(manifest_data)

    catalog_df = pd.read_parquet(snap_dir / "catalog.parquet")
    train_df = pd.read_parquet(snap_dir / "train_events.parquet")
    val_df = pd.read_parquet(snap_dir / "val_events.parquet")
    test_df = pd.read_parquet(snap_dir / "test_events.parquet")
    order_baskets_df = pd.read_parquet(snap_dir / "order_baskets.parquet")

    sorted_raw_products = sorted(catalog_df["product_id"].unique())
    product_map = {int(pid): int(idx) for idx, pid in enumerate(sorted_raw_products)}
    raw_product_map = {int(idx): int(pid) for idx, pid in enumerate(sorted_raw_products)}

    sorted_raw_users = sorted(train_df["user_id"].unique())
    user_map = {int(uid): int(idx + 1) for idx, uid in enumerate(sorted_raw_users)}
    raw_user_map = {int(idx + 1): int(uid) for idx, uid in enumerate(sorted_raw_users)}

    user_persona_df = train_df[["user_id", "persona_cluster"]].drop_duplicates()
    persona_map = dict(zip(user_persona_df["user_id"].values, user_persona_df["persona_cluster"].values))

    cold_count = settings.data.num_cold_items
    cold_raw_ids = sorted_raw_products[-cold_count:]
    cold_internal_ids = [product_map[pid] for pid in cold_raw_ids]

    warm_catalog = catalog_df[~catalog_df["internal_product_id"].isin(cold_internal_ids)]
    price_boundaries = fit_price_boundaries(warm_catalog["unit_price"].values, settings.data.num_price_buckets)

    return Snapshot(
        manifest=manifest,
        snapshot_dir=snap_dir,
        catalog_df=catalog_df,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        order_baskets_df=order_baskets_df,
        product_map=product_map,
        raw_product_map=raw_product_map,
        user_map=user_map,
        raw_user_map=raw_user_map,
        persona_map=persona_map,
        cold_item_ids=cold_internal_ids,
        price_boundaries=price_boundaries,
    )
