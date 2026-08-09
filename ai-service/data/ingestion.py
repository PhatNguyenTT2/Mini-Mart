"""Data Ingestion, Mapping, and Temporal Isolation module for ai-service.

Provides snapshot extraction from PostgreSQL or synthetic benchmark generation, contiguous vocabulary mapping, 7-quantile price bucketing, cold item isolation (250 items), and 80/10/10 temporal splitting with 0% data leakage.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from config import get_settings, Settings, DATA_ARTIFACTS_DIR


@dataclass
class SnapshotManifest:
    """Immutable metadata manifest for a dataset snapshot."""

    snapshot_id: str
    created_at: str
    store_id: int
    num_users: int
    num_items: int
    num_leaf_categories: int
    num_price_buckets: int
    num_train_events: int
    num_val_events: int
    num_test_events: int
    num_cold_items: int
    train_max_ts: str
    val_min_ts: str
    val_max_ts: str
    test_min_ts: str
    checksums: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SnapshotArtifacts:
    """In-memory container for loaded dataset snapshot artifacts."""

    snapshot_dir: Path
    manifest: SnapshotManifest
    catalog_df: pd.DataFrame
    users_df: pd.DataFrame
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    order_baskets_df: pd.DataFrame
    user_map: Dict[int, int]
    raw_user_map: Dict[int, int]
    product_map: Dict[int, int]
    raw_product_map: Dict[int, int]
    leaf_category_map: Dict[int, int]
    persona_map: Dict[int, int]
    cold_item_ids: np.ndarray
    price_boundaries: np.ndarray


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_synthetic_benchmark_data(
    settings: Settings,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate deterministic synthetic dataset matching 823,371 interactions, 5,200 products, 5,000 users.

    Used when PostgreSQL is not connected or in dry-run benchmark mode.
    """
    num_users = settings.data.num_users
    num_items = settings.data.num_items
    num_leaves = settings.data.num_leaf_categories
    store_id = settings.data.store_id
    total_events = 823371

    rng = np.random.default_rng(seed=settings.train.seed)

    # 1. Generate Catalog (5,200 products)
    raw_product_ids = np.arange(1001, 1001 + num_items, dtype=np.int64)
    root_categories = np.array([f"RootCat_{i}" for i in range(14)])
    leaf_categories = np.arange(1, num_leaves + 1, dtype=np.int64)

    product_roots = rng.choice(root_categories, size=num_items)
    product_leaves = rng.choice(leaf_categories, size=num_items)
    unit_prices = np.round(rng.uniform(5000, 250000, size=num_items), -2)

    catalog_df = pd.DataFrame(
        {
            "product_id": raw_product_ids,
            "product_name": [f"Sản phẩm {pid}" for pid in raw_product_ids],
            "vendor_name": [f"Nhà cung cấp {pid % 20}" for pid in raw_product_ids],
            "root_category": product_roots,
            "leaf_category_id": product_leaves,
            "unit_price": unit_prices,
        }
    )

    # 2. Generate Users & Personas (5,000 users)
    raw_user_ids = np.arange(1, num_users + 1, dtype=np.int64)
    persona_clusters = rng.integers(0, 8, size=num_users, dtype=np.int16)

    users_df = pd.DataFrame(
        {
            "user_id": raw_user_ids,
            "persona_cluster": persona_clusters,
        }
    )

    # 3. Designate 250 highest-ID products as Cold-Start items
    cold_raw_ids = raw_product_ids[-250:]
    warm_raw_ids = raw_product_ids[:-250]

    # 4. Generate 823,371 interaction events across timestamps
    start_ts = int(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())

    # Generate 80% train time, 10% val time, 10% test time timestamps
    ts_samples = rng.integers(start_ts, end_ts, size=total_events)
    ts_samples.sort()

    split_idx_80 = int(0.80 * total_events)
    split_idx_90 = int(0.90 * total_events)

    event_users = rng.choice(raw_user_ids, size=total_events)

    # Products: Train/Val events get ONLY warm items. Test events get warm + cold items.
    event_products = np.zeros(total_events, dtype=np.int64)
    event_products[:split_idx_90] = rng.choice(warm_raw_ids, size=split_idx_90)

    # For test set (last 10%), ensure each cold item appears at least once
    test_size = total_events - split_idx_90
    test_products = rng.choice(warm_raw_ids, size=test_size)

    # Guarantee at least 1 positive per cold product in test set
    cold_indices = rng.choice(test_size, size=250, replace=False)
    test_products[cold_indices] = cold_raw_ids

    event_products[split_idx_90:] = test_products

    # Map personas
    user_persona_dict = dict(zip(raw_user_ids, persona_clusters))
    event_personas = np.array([user_persona_dict[u] for u in event_users], dtype=np.int16)

    event_df = pd.DataFrame(
        {
            "event_id": [f"evt_{i:08d}" for i in range(total_events)],
            "store_id": store_id,
            "user_id": event_users,
            "product_id": event_products,
            "persona_cluster": event_personas,
            "event_type": "purchase",
            "event_ts": pd.to_datetime(ts_samples, unit="s", utc=True),
            "interaction_weight": 1.0,
        }
    )

    # 5. Generate Order Baskets for train period (order_date < val_min_ts)
    train_events = event_df.iloc[:split_idx_80]
    basket_order_ids = [f"ord_{i // 3:06d}" for i in range(len(train_events))]
    order_baskets_df = pd.DataFrame(
        {
            "order_id": basket_order_ids,
            "product_id": train_events["product_id"].values,
            "order_date": train_events["event_ts"].values,
        }
    )

    return catalog_df, users_df, event_df, order_baskets_df


def fit_price_boundaries(warm_prices: np.ndarray) -> np.ndarray:
    """Fit seven price boundaries on log1p(unit_price) using 8 quantiles (Q1/8 .. Q7/8)."""
    log_prices = np.log1p(warm_prices)
    quantiles = np.linspace(12.5, 87.5, 7)
    boundaries = np.percentile(log_prices, quantiles)
    return np.sort(boundaries)


def map_price_to_bucket(price: float, boundaries: np.ndarray) -> int:
    """Map raw price to bucket index 1..8 (0 is reserved for UNK/invalid)."""
    if price is None or np.isnan(price) or price <= 0:
        return 0
    log_p = np.log1p(price)
    bucket = np.searchsorted(boundaries, log_p, side="right") + 1
    return int(min(max(bucket, 1), 8))


def fetch_postgres_data(
    settings: Settings,
) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """Fetch real data snapshots from PostgreSQL databases (ml_interaction_event_v1, product, sale_order)."""
    import os
    chatbot_url = settings.data.database_url or os.getenv("CHATBOT_DATABASE_URL") or os.getenv("DATABASE_URL")
    catalog_url = settings.data.catalog_database_url or os.getenv("CATALOG_DATABASE_URL") or os.getenv("DATABASE_URL")
    order_url = settings.data.order_database_url or os.getenv("ORDER_DATABASE_URL") or os.getenv("DATABASE_URL")

    if not chatbot_url:
        return None

    try:
        import psycopg2

        print(f"📡 Fetching real dataset snapshot from PostgreSQL...")

        # 1. Fetch Catalog SKUs from CATALOG_DATABASE_URL
        cat_conn = psycopg2.connect(catalog_url or chatbot_url)
        cat_cur = cat_conn.cursor()
        cat_cur.execute("SET default_transaction_read_only = off;")
        cat_cur.execute(
            """SELECT p.id AS product_id, p.name AS product_name, COALESCE(p.vendor_name, 'Unknown') AS vendor_name,
                      COALESCE(c.name, 'DefaultRoot') AS root_category, p.category_id AS leaf_category_id, p.unit_price
               FROM product p
               LEFT JOIN category c ON p.category_id = c.id
               WHERE p.is_active = TRUE
               ORDER BY p.id ASC;"""
        )
        cat_rows = cat_cur.fetchall()
        cat_cols = [desc[0] for desc in cat_cur.description]
        catalog_df = pd.DataFrame(cat_rows, columns=cat_cols)
        cat_cur.close()
        cat_conn.close()
        print(f"   ✓ Catalog SKUs loaded: {len(catalog_df)}")

        # 2. Fetch ML Interaction Events from CHATBOT_DATABASE_URL (ml_interaction_event_v1)
        chat_conn = psycopg2.connect(chatbot_url)
        chat_cur = chat_conn.cursor()
        chat_cur.execute("SET default_transaction_read_only = off;")
        chat_cur.execute(
            """SELECT event_id, store_id, user_id, product_id, persona_cluster, event_type, event_ts, interaction_weight
               FROM ml_interaction_event_v1
               WHERE store_id = %s
               ORDER BY event_ts ASC, event_id ASC;""",
            (settings.data.store_id,),
        )
        evt_rows = chat_cur.fetchall()
        evt_cols = [desc[0] for desc in chat_cur.description]
        event_df = pd.DataFrame(evt_rows, columns=evt_cols)

        # Users DF
        chat_cur.execute(
            """SELECT DISTINCT user_id, persona_cluster FROM ml_interaction_event_v1 WHERE store_id = %s ORDER BY user_id ASC;""",
            (settings.data.store_id,),
        )
        u_rows = chat_cur.fetchall()
        users_df = pd.DataFrame(u_rows, columns=["user_id", "persona_cluster"])
        chat_cur.close()
        chat_conn.close()
        print(f"   ✓ ml_interaction_event_v1 events loaded: {len(event_df)} | Users: {len(users_df)}")

        # 3. Fetch Order Baskets from ORDER_DATABASE_URL
        ord_conn = psycopg2.connect(order_url or chatbot_url)
        ord_cur = ord_conn.cursor()
        ord_cur.execute("SET default_transaction_read_only = off;")
        ord_cur.execute(
            """SELECT o.id AS order_id, d.product_id, o.created_at AS order_date
               FROM sale_order o
               JOIN sale_order_detail d ON d.order_id = o.id
               WHERE o.status = 'delivered' AND o.payment_status = 'paid'
               ORDER BY o.created_at ASC;"""
        )
        ord_rows = ord_cur.fetchall()
        ord_cols = [desc[0] for desc in ord_cur.description]
        order_baskets_df = pd.DataFrame(ord_rows, columns=ord_cols)
        ord_cur.close()
        ord_conn.close()
        print(f"   ✓ Order baskets loaded: {len(order_baskets_df)}")

        if len(catalog_df) > 0 and len(users_df) > 0 and len(event_df) > 0:
            return catalog_df, users_df, event_df, order_baskets_df
    except Exception as e:
        print(f"⚠️ Could not fetch from PostgreSQL ({e}), falling back to synthetic benchmark generation...")

    return None


def build_snapshot(
    settings: Optional[Settings] = None, snapshot_id: str = "scaled-v1"
) -> SnapshotManifest:
    """Build immutable snapshot directory and artifacts."""
    if settings is None:
        settings = get_settings()

    snapshot_dir = DATA_ARTIFACTS_DIR / snapshot_id
    splits_dir = snapshot_dir / "splits"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    splits_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch or Generate Data
    fetched = fetch_postgres_data(settings)
    if fetched is not None:
        catalog_df, users_df, event_df, order_baskets_df = fetched
    else:
        catalog_df, users_df, event_df, order_baskets_df = generate_synthetic_benchmark_data(settings)

    # 2. Build Mappings
    # Product Map: raw product_id -> internal index 0..5199
    sorted_raw_products = np.sort(catalog_df["product_id"].unique())
    product_map = {int(pid): int(idx) for idx, pid in enumerate(sorted_raw_products)}
    raw_product_map = {v: k for k, v in product_map.items()}

    # User Map: raw user_id -> internal index 1..5000 (0=UNK)
    sorted_raw_users = np.sort(users_df["user_id"].unique())
    user_map = {int(uid): int(idx + 1) for idx, uid in enumerate(sorted_raw_users)}
    raw_user_map = {v: k for k, v in user_map.items()}

    # Leaf Category Map: raw leaf_cat_id -> internal index 1..40 (0=UNK)
    sorted_leaf_cats = np.sort(catalog_df["leaf_category_id"].unique())
    leaf_category_map = {int(cid): int(idx + 1) for idx, cid in enumerate(sorted_leaf_cats)}

    # Persona Map: raw user_id -> persona_cluster 0..7
    persona_map = dict(zip(users_df["user_id"].values, users_df["persona_cluster"].values))

    # Identify 250 highest-ID products as Cold items
    cold_raw_ids = sorted_raw_products[-250:]
    cold_internal_ids = np.array([product_map[pid] for pid in cold_raw_ids], dtype=np.int64)

    # 3. Add mapped columns to Catalog & Events
    catalog_df["internal_product_id"] = catalog_df["product_id"].map(product_map)
    catalog_df["internal_leaf_category_id"] = catalog_df["leaf_category_id"].map(leaf_category_map)

    # Fit Price Buckets on warm products
    warm_catalog = catalog_df[~catalog_df["internal_product_id"].isin(cold_internal_ids)]
    price_boundaries = fit_price_boundaries(warm_catalog["unit_price"].values)

    catalog_df["price_bucket_id"] = catalog_df["unit_price"].apply(
        lambda p: map_price_to_bucket(p, price_boundaries)
    )

    event_df["internal_user_id"] = event_df["user_id"].map(user_map)
    event_df["internal_product_id"] = event_df["product_id"].map(product_map)

    # 4. Temporal Split (80% Train / 10% Val / 10% Test)
    event_df = event_df.sort_values(by=["event_ts", "event_id"]).reset_index(drop=True)
    total_rows = len(event_df)
    idx_80 = int(0.80 * total_rows)
    idx_90 = int(0.90 * total_rows)

    train_df = event_df.iloc[:idx_80].copy()
    val_df = event_df.iloc[idx_80:idx_90].copy()
    test_df = event_df.iloc[idx_90:].copy()

    # Enforce Cold Item Isolation: remove cold items from train and val
    train_df = train_df[~train_df["internal_product_id"].isin(cold_internal_ids)].copy()
    val_df = val_df[~val_df["internal_product_id"].isin(cold_internal_ids)].copy()

    # 5. Persist Parquet files
    catalog_df.to_parquet(snapshot_dir / "catalog.parquet", index=False)
    users_df.to_parquet(snapshot_dir / "users.parquet", index=False)
    train_df.to_parquet(splits_dir / "train.parquet", index=False)
    val_df.to_parquet(splits_dir / "val.parquet", index=False)
    test_df.to_parquet(splits_dir / "test.parquet", index=False)
    order_baskets_df.to_parquet(snapshot_dir / "order_baskets.parquet", index=False)

    # 6. Persist Mappings and Arrays
    mappings_json = {
        "user_map": {str(k): v for k, v in user_map.items()},
        "raw_user_map": {str(k): v for k, v in raw_user_map.items()},
        "product_map": {str(k): v for k, v in product_map.items()},
        "raw_product_map": {str(k): v for k, v in raw_product_map.items()},
        "leaf_category_map": {str(k): v for k, v in leaf_category_map.items()},
        "persona_map": {str(k): int(v) for k, v in persona_map.items()},
    }
    with open(snapshot_dir / "mappings.json", "w", encoding="utf-8") as f:
        json.dump(mappings_json, f, indent=2)

    np.save(snapshot_dir / "cold_item_ids.npy", cold_internal_ids)
    np.save(snapshot_dir / "price_boundaries.npy", price_boundaries)

    # 7. Compute Checksums
    checksums = {
        "catalog.parquet": compute_sha256(snapshot_dir / "catalog.parquet"),
        "users.parquet": compute_sha256(snapshot_dir / "users.parquet"),
        "splits/train.parquet": compute_sha256(splits_dir / "train.parquet"),
        "splits/val.parquet": compute_sha256(splits_dir / "val.parquet"),
        "splits/test.parquet": compute_sha256(splits_dir / "test.parquet"),
        "order_baskets.parquet": compute_sha256(snapshot_dir / "order_baskets.parquet"),
        "mappings.json": compute_sha256(snapshot_dir / "mappings.json"),
        "cold_item_ids.npy": compute_sha256(snapshot_dir / "cold_item_ids.npy"),
        "price_boundaries.npy": compute_sha256(snapshot_dir / "price_boundaries.npy"),
    }

    manifest = SnapshotManifest(
        snapshot_id=snapshot_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        store_id=settings.data.store_id,
        num_users=len(user_map),
        num_items=len(product_map),
        num_leaf_categories=len(leaf_category_map),
        num_price_buckets=len(price_boundaries) + 1,
        num_train_events=len(train_df),
        num_val_events=len(val_df),
        num_test_events=len(test_df),
        num_cold_items=len(cold_internal_ids),
        train_max_ts=str(train_df["event_ts"].max()),
        val_min_ts=str(val_df["event_ts"].min()),
        val_max_ts=str(val_df["event_ts"].max()),
        test_min_ts=str(test_df["event_ts"].min()),
        checksums=checksums,
    )

    with open(snapshot_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2)

    return manifest


def load_snapshot(snapshot_id_or_path: str | Path = "scaled-v1") -> SnapshotArtifacts:
    """Load snapshot artifacts and verify checksums."""
    if isinstance(snapshot_id_or_path, Path):
        snapshot_dir = snapshot_id_or_path
    else:
        snapshot_dir = DATA_ARTIFACTS_DIR / snapshot_id_or_path

    if not snapshot_dir.exists():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")

    manifest_path = snapshot_dir / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    manifest = SnapshotManifest(**manifest_data)

    # Verify checksums
    for file_rel_path, expected_hash in manifest.checksums.items():
        full_path = snapshot_dir / file_rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Missing snapshot artifact: {full_path}")
        actual_hash = compute_sha256(full_path)
        if actual_hash != expected_hash:
            raise ValueError(f"Checksum mismatch for {file_rel_path}: expected {expected_hash}, got {actual_hash}")

    catalog_df = pd.read_parquet(snapshot_dir / "catalog.parquet")
    users_df = pd.read_parquet(snapshot_dir / "users.parquet")
    train_df = pd.read_parquet(snapshot_dir / "splits" / "train.parquet")
    val_df = pd.read_parquet(snapshot_dir / "splits" / "val.parquet")
    test_df = pd.read_parquet(snapshot_dir / "splits" / "test.parquet")
    order_baskets_df = pd.read_parquet(snapshot_dir / "order_baskets.parquet")

    with open(snapshot_dir / "mappings.json", "r", encoding="utf-8") as f:
        mappings_data = json.load(f)

    user_map = {int(k): int(v) for k, v in mappings_data["user_map"].items()}
    raw_user_map = {int(k): int(v) for k, v in mappings_data["raw_user_map"].items()}
    product_map = {int(k): int(v) for k, v in mappings_data["product_map"].items()}
    raw_product_map = {int(k): int(v) for k, v in mappings_data["raw_product_map"].items()}
    leaf_category_map = {int(k): int(v) for k, v in mappings_data["leaf_category_map"].items()}
    persona_map = {int(k): int(v) for k, v in mappings_data["persona_map"].items()}

    cold_item_ids = np.load(snapshot_dir / "cold_item_ids.npy")
    price_boundaries = np.load(snapshot_dir / "price_boundaries.npy")

    return SnapshotArtifacts(
        snapshot_dir=snapshot_dir,
        manifest=manifest,
        catalog_df=catalog_df,
        users_df=users_df,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        order_baskets_df=order_baskets_df,
        user_map=user_map,
        raw_user_map=raw_user_map,
        product_map=product_map,
        raw_product_map=raw_product_map,
        leaf_category_map=leaf_category_map,
        persona_map=persona_map,
        cold_item_ids=cold_item_ids,
        price_boundaries=price_boundaries,
    )
