"""Data Source Adapters for PostgreSQL and Synthetic generation."""

from dataclasses import dataclass
from typing import Optional, Protocol, Tuple, Dict, Any
import numpy as np
import pandas as pd
import psycopg2

from ai_service.config import Settings
from ai_service.errors import SourceReadError


@dataclass
class RawDataset:
    events_df: pd.DataFrame
    products_df: pd.DataFrame
    orders_df: pd.DataFrame
    source_kind: str


class DatasetSource(Protocol):
    """Protocol interface for loading raw dataset DataFrames."""

    def load(self, store_id: int) -> RawDataset:
        ...


class PostgresDatasetSource:
    """PostgreSQL production Data Source Adapter."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def load(self, store_id: int) -> RawDataset:
        db_url_secret = self.settings.data.database_url
        if db_url_secret is None:
            raise SourceReadError("CHATBOT_DATABASE_URL is not set in environment or config")

        db_url = db_url_secret.get_secret_value()
        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            # Enforce read-only session mode
            cursor.execute("SET TRANSACTION READ ONLY;")

            # 1. Fetch interaction events
            events_query = """
                SELECT event_id, store_id, user_id, product_id, persona_cluster, event_type, event_ts, interaction_weight
                FROM ml_interaction_event_v1
                WHERE store_id = %s
                ORDER BY event_ts ASC, event_id ASC;
            """
            events_df = pd.read_sql_query(events_query, conn, params=(store_id,))

            # 2. Fetch catalog products
            catalog_db_url_secret = self.settings.data.catalog_database_url or db_url_secret
            catalog_conn = psycopg2.connect(catalog_db_url_secret.get_secret_value())
            cat_cursor = catalog_conn.cursor()
            cat_cursor.execute("SET TRANSACTION READ ONLY;")

            products_query = """
                SELECT p.id as product_id, p.name, p.unit_price, p.leaf_category_id
                FROM product p
                WHERE p.is_active = true
                ORDER BY p.id ASC;
            """
            products_df = pd.read_sql_query(products_query, catalog_conn)

            # 3. Fetch completed orders for Apriori mining
            order_db_url_secret = self.settings.data.order_database_url or db_url_secret
            order_conn = psycopg2.connect(order_db_url_secret.get_secret_value())
            order_cursor = order_conn.cursor()
            order_cursor.execute("SET TRANSACTION READ ONLY;")

            orders_query = """
                SELECT o.id as order_id, o.user_id, d.product_id, d.quantity, o.created_at
                FROM sale_order o
                JOIN sale_order_detail d ON o.id = d.order_id
                WHERE o.store_id = %s AND o.status = 'delivered'
                ORDER BY o.id ASC;
            """
            orders_df = pd.read_sql_query(orders_query, order_conn, params=(store_id,))

            cursor.close()
            conn.close()
            cat_cursor.close()
            catalog_conn.close()
            order_cursor.close()
            order_conn.close()

            return RawDataset(
                events_df=events_df,
                products_df=products_df,
                orders_df=orders_df,
                source_kind="postgres",
            )

        except Exception as err:
            raise SourceReadError(f"Failed to read dataset from PostgreSQL: {err}") from err


class SyntheticDatasetSource:
    """Synthetic Benchmark Data Source Adapter for testing and standalone CLI runs."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def load(self, store_id: int) -> RawDataset:
        num_users = self.settings.data.num_users
        num_items = self.settings.data.num_items
        num_cold = self.settings.data.num_cold_items
        num_warm = num_items - num_cold

        rng = np.random.default_rng(seed=42)

        # 1. Synthetic Catalog Products
        product_ids = np.arange(1001, 1001 + num_items, dtype=np.int64)
        leaf_categories = rng.integers(1, 41, size=num_items)
        unit_prices = np.round(rng.uniform(10.0, 500.0, size=num_items), 2)
        products_df = pd.DataFrame({
            "product_id": product_ids,
            "name": [f"Product_{pid}" for pid in product_ids],
            "unit_price": unit_prices,
            "leaf_category_id": leaf_categories,
        })

        # 2. Synthetic Events (823,371 rows)
        num_events = 823371
        warm_pids = product_ids[:num_warm]
        cold_pids = product_ids[num_warm:]

        user_ids = rng.integers(1, num_users + 1, size=num_events)
        persona_clusters = (user_ids % 8).astype(np.int16)
        
        # 80% train time, 10% val time, 10% test time
        base_ts = pd.Timestamp("2026-01-01 00:00:00+00:00")
        train_val_events = int(0.90 * num_events)
        test_events = num_events - train_val_events

        # Warm items assigned across train/val/test
        warm_event_pids = rng.choice(warm_pids, size=train_val_events)
        # Cold items assigned only in test time
        cold_event_pids = rng.choice(cold_pids, size=test_events)

        event_pids = np.concatenate([warm_event_pids, cold_event_pids])
        
        # Sorted timestamps
        ts_offsets = np.sort(rng.integers(0, 180 * 86400, size=num_events))
        timestamps = [base_ts + pd.Timedelta(seconds=int(sec)) for sec in ts_offsets]

        event_types = rng.choice(["view", "order"], size=num_events, p=[0.67, 0.33])
        weights = np.where(event_types == "order", 1.0, 0.5).astype(np.float32)

        events_df = pd.DataFrame({
            "event_id": [f"evt_{i}" for i in range(num_events)],
            "store_id": store_id,
            "user_id": user_ids,
            "product_id": event_pids,
            "persona_cluster": persona_clusters,
            "event_type": event_types,
            "event_ts": timestamps,
            "interaction_weight": weights,
        })

        # 3. Synthetic Orders (30,045 baskets)
        num_baskets = 30045
        order_rows = []
        for o_id in range(1, num_baskets + 1):
            u_id = rng.integers(1, num_users + 1)
            b_size = rng.integers(2, 6)
            b_items = rng.choice(warm_pids, size=b_size, replace=False)
            for p_id in b_items:
                order_rows.append({
                    "order_id": o_id,
                    "user_id": u_id,
                    "product_id": p_id,
                    "quantity": rng.integers(1, 4),
                    "created_at": base_ts + pd.Timedelta(days=int(o_id % 120)),
                })
        orders_df = pd.DataFrame(order_rows)

        return RawDataset(
            events_df=events_df,
            products_df=products_df,
            orders_df=orders_df,
            source_kind="synthetic",
        )
