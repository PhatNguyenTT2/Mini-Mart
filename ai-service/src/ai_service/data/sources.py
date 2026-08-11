"""Raw dataset adapters. Production and synthetic behavior are explicit choices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import psycopg

from ai_service.config import Settings
from ai_service.contracts import DataSourceKind
from ai_service.errors import SourceReadError


@dataclass(frozen=True)
class RawDataset:
    events_df: pd.DataFrame
    products_df: pd.DataFrame
    orders_df: pd.DataFrame
    cold_product_ids: tuple[int, ...]
    source_kind: DataSourceKind
    benchmark_run_id: str
    store_id: int


class DatasetSource(Protocol):
    def load(self, store_id: int, benchmark_run_id: str | None = None) -> RawDataset: ...


def _frame(
    cursor: psycopg.Cursor[tuple[object, ...]], query: str, params: tuple[object, ...]
) -> pd.DataFrame:
    cursor.execute(query, params)
    columns = [column.name for column in cursor.description or ()]
    return pd.DataFrame(cursor.fetchall(), columns=columns)


def _connect_read_only(url: str, settings: Settings) -> psycopg.Connection[tuple[object, ...]]:
    hostname = (urlparse(url).hostname or "").lower()
    local = hostname in {"localhost", "127.0.0.1", "::1"}
    if local:
        connection = psycopg.connect(url)
    else:
        certificate = settings.data.database_ssl_root_cert
        if certificate is None or not certificate.resolve().is_file():
            raise SourceReadError(
                "SUPABASE_DB_CA_PATH must reference the Supabase CA for verified PostgreSQL TLS"
            )
        connection = psycopg.connect(
            url,
            sslmode="verify-full",
            sslrootcert=str(certificate.resolve()),
        )
    connection.read_only = True
    return connection


class PostgresDatasetSource:
    """Read a ready benchmark run from the three owned PostgreSQL databases."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def load(self, store_id: int, benchmark_run_id: str | None = None) -> RawDataset:
        data = self.settings.data
        if (
            not data.chatbot_database_url
            or not data.catalog_database_url
            or not data.order_database_url
        ):
            raise SourceReadError("all three PostgreSQL URLs are required")
        try:
            with _connect_read_only(
                data.chatbot_database_url.get_secret_value(), self.settings
            ) as chat_conn:
                with chat_conn.cursor() as cursor:
                    if benchmark_run_id is None:
                        cursor.execute(
                            """
                            SELECT benchmark_run_id
                            FROM ml_benchmark_run_v1
                            WHERE store_id=%s AND status='ready' AND published_at IS NOT NULL
                            ORDER BY published_at DESC
                            LIMIT 1
                            """,
                            (store_id,),
                        )
                        row = cursor.fetchone()
                        if row is None:
                            raise SourceReadError("no ready benchmark run exists")
                        benchmark_run_id = str(row[0])
                    else:
                        cursor.execute(
                            """
                            SELECT benchmark_run_id
                            FROM ml_benchmark_run_v1
                            WHERE store_id=%s AND benchmark_run_id=%s
                              AND status='ready' AND published_at IS NOT NULL
                            """,
                            (store_id, benchmark_run_id),
                        )
                        if cursor.fetchone() is None:
                            raise SourceReadError(
                                f"specified benchmark run {benchmark_run_id} is not ready "
                                "or published"
                            )
                    events = _frame(
                        cursor,
                        """
                        SELECT event_id, store_id, user_id, product_id, persona_cluster,
                               event_type, event_ts, interaction_weight, session_id,
                               event_origin, cohort_id, benchmark_run_id
                        FROM ml_interaction_event_v1
                        WHERE store_id=%s AND benchmark_run_id=%s
                        ORDER BY event_ts, event_id
                        """,
                        (store_id, benchmark_run_id),
                    )
                    cursor.execute(
                        """
                        SELECT product_id
                        FROM ml_benchmark_item_partition_v1
                        WHERE store_id=%s AND benchmark_run_id=%s AND partition='cold'
                        ORDER BY product_id
                        """,
                        (store_id, benchmark_run_id),
                    )
                    cold_ids = tuple(int(str(row[0])) for row in cursor.fetchall())

            with _connect_read_only(
                data.catalog_database_url.get_secret_value(), self.settings
            ) as catalog_conn:
                with catalog_conn.cursor() as cursor:
                    products = _frame(
                        cursor,
                        """
                        SELECT p.id AS product_id, p.name, p.unit_price,
                               p.category_id AS leaf_category_id,
                               leaf.name AS leaf_category_name,
                               root.name AS root_category_name,
                               COALESCE(p.vendor, '') AS vendor,
                               COALESCE(leaf.description, '') AS description
                        FROM product p
                        JOIN category leaf ON leaf.id=p.category_id
                        LEFT JOIN category root ON root.id=leaf.parent_id
                        WHERE p.is_active=true
                        ORDER BY p.id
                        """,
                        (),
                    )

            with _connect_read_only(
                data.order_database_url.get_secret_value(), self.settings
            ) as order_conn:
                with order_conn.cursor() as cursor:
                    orders = _frame(
                        cursor,
                        """
                        SELECT o.id AS order_id, o.customer_id AS user_id, d.product_id,
                               d.quantity, o.order_date AS order_ts
                        FROM sale_order o
                        JOIN sale_order_detail d ON d.order_id=o.id
                        WHERE o.store_id=%s AND o.benchmark_run_id=%s
                          AND o.status='delivered' AND o.payment_status='paid'
                        ORDER BY o.order_date, o.id, d.product_id
                        """,
                        (store_id, benchmark_run_id),
                    )
        except SourceReadError:
            raise
        except Exception as error:
            raise SourceReadError(f"failed to read PostgreSQL benchmark: {error}") from error

        return RawDataset(
            events_df=events,
            products_df=products,
            orders_df=orders,
            cold_product_ids=cold_ids,
            source_kind=DataSourceKind.POSTGRES,
            benchmark_run_id=benchmark_run_id,
            store_id=store_id,
        )


def _synthetic_preferred_category(user_ids: np.ndarray, num_categories: int) -> np.ndarray:
    """Map one-based user IDs to one-based deterministic preferred categories."""
    if num_categories <= 0:
        raise SourceReadError("synthetic category count must be positive")
    return ((np.asarray(user_ids, dtype=np.int64) - 1) % num_categories) + 1


def _sample_preference_items(
    *,
    user_ids: np.ndarray,
    warm_item_ids: np.ndarray,
    item_category_ids: np.ndarray,
    seen_by_user: dict[int, set[int]],
    rng: np.random.Generator,
    novel: bool,
    preference_probability: float = 0.85,
) -> np.ndarray:
    """Sample deterministic preference/noise items, optionally excluding history."""
    warm = np.asarray(warm_item_ids, dtype=np.int64)
    categories = np.asarray(item_category_ids, dtype=np.int64)
    if warm.ndim != 1 or categories.shape != warm.shape or warm.size == 0:
        raise SourceReadError("synthetic warm catalog/category arrays are invalid")
    if not 0.0 <= preference_probability <= 1.0:
        raise SourceReadError("synthetic preference probability must be within [0,1]")
    category_by_item = {
        int(item): int(category) for item, category in zip(warm, categories, strict=True)
    }
    items_by_category: dict[int, np.ndarray] = {}
    for category in sorted(set(category_by_item.values())):
        items_by_category[category] = np.asarray(
            [item for item in warm if category_by_item[int(item)] == category], dtype=np.int64
        )
    preferred = _synthetic_preferred_category(user_ids, max(items_by_category))
    sampled = np.empty(len(user_ids), dtype=np.int64)
    for index, raw_user in enumerate(np.asarray(user_ids, dtype=np.int64)):
        user = int(raw_user)
        preferred_pool = items_by_category.get(int(preferred[index]), warm)
        pool = preferred_pool if rng.random() < preference_probability else warm
        seen = seen_by_user.setdefault(user, set())
        if novel:
            available = np.asarray([item for item in pool if int(item) not in seen], dtype=np.int64)
            if available.size == 0:
                available = np.asarray(
                    [item for item in warm if int(item) not in seen], dtype=np.int64
                )
            if available.size == 0:
                raise SourceReadError(f"synthetic user {user} has no novel warm item")
        else:
            available = pool
        chosen = int(available[int(rng.integers(0, len(available)))])
        sampled[index] = chosen
        seen.add(chosen)
    return sampled


def _build_synthetic_orders(
    *,
    user_ids: np.ndarray,
    warm_item_ids: np.ndarray,
    item_category_ids: np.ndarray,
    order_count: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Build exact-count, category-coherent train-period baskets."""
    if order_count <= 0 or len(warm_item_ids) < 2:
        raise SourceReadError("synthetic order generation needs at least two warm items")
    category_by_item = {
        int(item): int(category)
        for item, category in zip(warm_item_ids, item_category_ids, strict=True)
    }
    items_by_category = {
        category: np.asarray(
            [item for item in warm_item_ids if category_by_item[int(item)] == category],
            dtype=np.int64,
        )
        for category in sorted(set(category_by_item.values()))
    }
    order_rows: list[dict[str, object]] = []
    order_base = pd.Timestamp("2026-01-01", tz="UTC")
    for order_id in range(1, order_count + 1):
        basket_size = int(rng.integers(2, min(5, len(warm_item_ids)) + 1))
        category = int(rng.choice(np.asarray(sorted(items_by_category), dtype=np.int64)))
        preferred_pool = items_by_category[category]
        if len(preferred_pool) >= basket_size:
            basket = rng.choice(preferred_pool, size=basket_size, replace=False)
        else:
            basket = rng.choice(warm_item_ids, size=basket_size, replace=False)
        for product_id in basket:
            order_rows.append(
                {
                    "order_id": order_id,
                    "user_id": int(user_ids[(order_id - 1) % len(user_ids)]),
                    "product_id": int(product_id),
                    "quantity": int(rng.integers(1, 4)),
                    "order_ts": order_base + pd.Timedelta(seconds=order_id * 500),
                }
            )
    return pd.DataFrame(order_rows)


class SyntheticDatasetSource:
    """Deterministic local adapter used only when explicitly selected."""

    def __init__(self, settings: Settings, *, num_events: int | None = None):
        self.settings = settings
        self.num_events = num_events or settings.data.expected_event_count

    def load(self, store_id: int, benchmark_run_id: str | None = None) -> RawDataset:
        data = self.settings.data
        rng = np.random.default_rng(self.settings.train.seed)
        product_ids = np.arange(1_001, 1_001 + data.num_items, dtype=np.int64)
        cold_ids = (
            tuple(int(value) for value in product_ids[-data.num_cold_items :])
            if data.num_cold_items
            else ()
        )
        warm_ids = product_ids[: data.num_items - data.num_cold_items]
        run_id = benchmark_run_id or f"synthetic-{self.settings.train.seed}"

        products = pd.DataFrame(
            {
                "product_id": product_ids,
                "name": [f"Product {value}" for value in product_ids],
                "unit_price": rng.uniform(10, 500, data.num_items).round(2),
                "leaf_category_id": (np.arange(data.num_items) % data.num_leaf_categories) + 1,
                "leaf_category_name": [
                    f"Leaf {idx % data.num_leaf_categories + 1}" for idx in range(data.num_items)
                ],
                "root_category_name": [f"Root {idx % 14 + 1}" for idx in range(data.num_items)],
                "vendor": [f"Vendor {idx % 25 + 1}" for idx in range(data.num_items)],
                "description": [""] * data.num_items,
            }
        )

        train_count = data.expected_train_count
        val_count = data.expected_val_count
        test_count = data.expected_test_count
        if train_count + val_count + test_count != self.num_events:
            raise SourceReadError("synthetic split counts do not match requested event count")
        if test_count < len(cold_ids):
            raise SourceReadError("synthetic test split is too small for cold ground truth")

        if len(warm_ids) < 2 or train_count < len(warm_ids):
            raise SourceReadError("synthetic train split cannot cover the warm catalog")
        item_categories = products.loc[
            products.product_id.isin(warm_ids), ["product_id", "leaf_category_id"]
        ].sort_values("product_id", kind="stable")
        warm_ids = item_categories.product_id.to_numpy(np.int64)
        warm_categories = item_categories.leaf_category_id.to_numpy(np.int64)
        train_users = (np.arange(train_count, dtype=np.int64) % data.num_users) + 1
        seen_by_user: dict[int, set[int]] = {user: set() for user in range(1, data.num_users + 1)}
        coverage_users = (np.arange(len(warm_ids), dtype=np.int64) % data.num_users) + 1
        train_items = np.empty(train_count, dtype=np.int64)
        train_items[: len(warm_ids)] = warm_ids
        for item, user in zip(train_items[: len(warm_ids)], coverage_users, strict=True):
            seen_by_user[int(user)].add(int(item))
        if train_count > len(warm_ids):
            train_items[len(warm_ids) :] = _sample_preference_items(
                user_ids=train_users[len(warm_ids) :],
                warm_item_ids=warm_ids,
                item_category_ids=warm_categories,
                seen_by_user=seen_by_user,
                rng=rng,
                novel=False,
            )
        val_users = (np.arange(val_count, dtype=np.int64) % data.num_users) + 1
        val_items = _sample_preference_items(
            user_ids=val_users,
            warm_item_ids=warm_ids,
            item_category_ids=warm_categories,
            seen_by_user=seen_by_user,
            rng=rng,
            novel=True,
        )
        if test_count <= len(cold_ids):
            raise SourceReadError("synthetic test split needs warm and cold ground truth")
        test_users = (np.arange(test_count, dtype=np.int64) % data.num_users) + 1
        test_items = np.empty(test_count, dtype=np.int64)
        test_items[: len(cold_ids)] = np.asarray(cold_ids, dtype=np.int64)
        test_items[len(cold_ids) :] = _sample_preference_items(
            user_ids=test_users[len(cold_ids) :],
            warm_item_ids=warm_ids,
            item_category_ids=warm_categories,
            seen_by_user=seen_by_user,
            rng=rng,
            novel=True,
        )
        all_items = np.concatenate((train_items, val_items, test_items))

        train_ts = pd.date_range(
            "2026-01-01T00:00:00Z", "2026-06-19T23:59:59Z", periods=train_count
        )
        val_ts = pd.date_range("2026-06-20T00:00:00Z", "2026-07-10T23:59:59Z", periods=val_count)
        test_ts = pd.date_range("2026-07-11T00:00:00Z", "2026-08-01T00:00:00Z", periods=test_count)
        train_event_types = np.full(train_count, "purchase", dtype=object)
        if train_count > data.num_users:
            train_event_types[data.num_users :] = rng.choice(
                ["view", "purchase"],
                p=[0.30, 0.70],
                size=train_count - data.num_users,
            )
        event_types = np.concatenate(
            (train_event_types, np.full(val_count + test_count, "purchase", dtype=object))
        )
        if self.num_events < data.num_users:
            raise SourceReadError("synthetic event count cannot cover every configured user")
        users = np.concatenate((train_users, val_users, test_users))
        session_ids = np.concatenate(
            tuple(
                np.asarray([f"{run_id}:session:{split}:{index // 2:09d}" for index in range(count)])
                for split, count in (
                    ("train", train_count),
                    ("val", val_count),
                    ("test", test_count),
                )
            )
        )
        events = pd.DataFrame(
            {
                "event_id": [f"{run_id}:{idx:09d}" for idx in range(self.num_events)],
                "store_id": store_id,
                "user_id": users,
                "product_id": all_items,
                "persona_cluster": (users - 1) % data.num_personas,
                "event_type": event_types,
                "event_ts": np.concatenate((train_ts, val_ts, test_ts)),
                "interaction_weight": np.where(event_types == "purchase", 1.0, 0.5),
                "session_id": session_ids,
                "event_origin": np.where(
                    np.isin(all_items, np.asarray(cold_ids, dtype=np.int64)),
                    "cold_start",
                    "organic",
                ),
                "cohort_id": None,
                "benchmark_run_id": run_id,
            }
        )

        order_rows = _build_synthetic_orders(
            user_ids=np.arange(1, data.num_users + 1, dtype=np.int64),
            warm_item_ids=warm_ids,
            item_category_ids=warm_categories,
            order_count=data.expected_order_count,
            rng=rng,
        )
        return RawDataset(
            events_df=events,
            products_df=products,
            orders_df=order_rows,
            cold_product_ids=cold_ids,
            source_kind=DataSourceKind.SYNTHETIC,
            benchmark_run_id=run_id,
            store_id=store_id,
        )
