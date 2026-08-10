"""Statistical suitability audit independent from structural snapshot validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_service.contracts import DataQualityReport
from ai_service.data.snapshot import Snapshot


def filter_event_origin(frame: pd.DataFrame, *origins: str) -> pd.DataFrame:
    """Return selected benchmark cohorts; legacy snapshots are treated as organic."""
    if "event_origin" not in frame.columns:
        return frame
    accepted = origins or ("organic",)
    return frame[frame.event_origin.isin(accepted)]


def _gini(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=np.float64)
    if not len(values) or float(values.sum()) == 0.0:
        return 0.0
    ordered = np.sort(values)
    indices = np.arange(1, len(ordered) + 1, dtype=np.float64)
    return float(
        (2.0 * np.sum(indices * ordered) / (len(ordered) * ordered.sum()))
        - (len(ordered) + 1) / len(ordered)
    )


def _distribution(frame: pd.DataFrame, num_items: int) -> np.ndarray:
    counts = (
        frame.internal_product_id.value_counts()
        .reindex(range(num_items), fill_value=0)
        .to_numpy(np.float64)
    )
    return counts / max(float(counts.sum()), 1.0)


def _jensen_shannon(left: np.ndarray, right: np.ndarray) -> float:
    middle = 0.5 * (left + right)

    def divergence(source: np.ndarray) -> float:
        mask = source > 0
        return float(np.sum(source[mask] * np.log2(source[mask] / middle[mask])))

    return float(np.sqrt(max(0.0, 0.5 * divergence(left) + 0.5 * divergence(right))))


def _novel_users(history: pd.DataFrame, target: pd.DataFrame) -> int:
    seen = set(
        map(
            tuple,
            filter_event_origin(history)[["internal_user_id", "internal_product_id"]]
            .drop_duplicates()
            .to_numpy(),
        )
    )
    purchases = filter_event_origin(target)
    purchases = purchases[purchases.event_type == "purchase"]
    novel = {
        (int(user), int(item))
        for user, item in purchases[["internal_user_id", "internal_product_id"]].to_numpy()
        if (int(user), int(item)) not in seen
    }
    return len({user for user, _ in novel})


class DataQualityAuditor:
    """Deep module producing one deterministic training-suitability report."""

    def audit(self, snapshot: Snapshot) -> DataQualityReport:
        frames = {
            "train": snapshot.train_df,
            "val": snapshot.val_df,
            "test": snapshot.test_df,
        }
        all_events = pd.concat(tuple(frames.values()), ignore_index=True)
        organic_train = filter_event_origin(snapshot.train_df)
        pair_columns = ["internal_user_id", "internal_product_id"]
        unique_pairs = all_events[pair_columns].drop_duplicates()
        views = set(
            map(
                tuple,
                organic_train.loc[organic_train.event_type == "view", pair_columns]
                .drop_duplicates()
                .to_numpy(),
            )
        )
        purchases = set(
            map(
                tuple,
                organic_train.loc[organic_train.event_type == "purchase", pair_columns]
                .drop_duplicates()
                .to_numpy(),
            )
        )

        prior_view_fraction: float | None = None
        view_to_purchase_lift: float | None = None
        if "session_id" in organic_train.columns:
            ordered = organic_train.sort_values(["event_ts", "event_id"], kind="stable")
            viewed: set[tuple[int, str, int]] = set()
            purchase_count = 0
            purchase_after_view = 0
            for user, session, item, event_type in ordered[
                ["internal_user_id", "session_id", "internal_product_id", "event_type"]
            ].itertuples(index=False, name=None):
                key = (int(user), str(session), int(item))
                if event_type == "view":
                    viewed.add(key)
                elif event_type == "purchase":
                    purchase_count += 1
                    purchase_after_view += int(key in viewed)
            prior_view_fraction = purchase_after_view / purchase_count if purchase_count else 0.0
            converted_rate = len(views & purchases) / max(1, len(views))
            random_purchase_rate = len(purchases) / max(
                1,
                snapshot.manifest.num_users * snapshot.manifest.num_items,
            )
            view_to_purchase_lift = converted_rate / max(
                random_purchase_rate,
                np.finfo(np.float64).eps,
            )

        per_user = organic_train.groupby("internal_user_id").internal_product_id.nunique()
        quantiles = {
            str(label): float(value)
            for label, value in per_user.quantile([0.0, 0.1, 0.5, 0.9, 0.99, 1.0]).items()
        }
        popularity = organic_train.internal_product_id.value_counts().to_numpy(np.float64)
        popularity = np.sort(popularity)[::-1]
        total_popularity = max(float(popularity.sum()), 1.0)
        distributions = {
            name: _distribution(filter_event_origin(frame), snapshot.manifest.num_items)
            for name, frame in frames.items()
        }
        fixture_counts: dict[str, int] = {}
        legacy_origin = "event_origin" not in all_events.columns
        if not legacy_origin:
            fixture_counts = {
                str(name): int(count)
                for name, count in all_events.loc[
                    all_events.event_origin != "organic", "event_origin"
                ]
                .value_counts()
                .items()
            }

        ordered_train = organic_train.sort_values(
            ["internal_user_id", "event_ts", "event_id"], kind="stable"
        )
        purchases_with_context = 0
        purchase_targets = 0
        last_purchase: dict[int, pd.Timestamp] = {}
        for user, event_type, event_ts in ordered_train[
            ["internal_user_id", "event_type", "event_ts"]
        ].itertuples(index=False, name=None):
            user_id = int(user)
            if event_type == "purchase":
                timestamp = pd.Timestamp(event_ts)
                purchase_targets += 1
                purchases_with_context += int(
                    user_id in last_purchase and last_purchase[user_id] < timestamp
                )
                previous = last_purchase.get(user_id)
                if previous is None or timestamp > previous:
                    last_purchase[user_id] = timestamp
        context_coverage = purchases_with_context / max(1, purchase_targets)

        novel_users = {
            "val": _novel_users(snapshot.train_df, snapshot.val_df),
            "test": _novel_users(
                pd.concat((snapshot.train_df, snapshot.val_df), ignore_index=True),
                snapshot.test_df,
            ),
        }
        failures: list[str] = []
        if prior_view_fraction is None:
            failures.append("session_contract_missing")
        elif prior_view_fraction < 0.8:
            failures.append("purchase_prior_view_fraction_below_0.8")
        if view_to_purchase_lift is not None and view_to_purchase_lift < 2.0:
            failures.append("view_to_purchase_lift_below_2.0")
        required_users = int(np.ceil(snapshot.manifest.num_users * 0.9))
        for split, eligible in novel_users.items():
            if eligible < required_users:
                failures.append(f"organic_{split}_novel_user_coverage_below_0.9")

        return DataQualityReport(
            total_events=len(all_events),
            split_counts={name: len(frame) for name, frame in frames.items()},
            unique_user_item_pairs=len(unique_pairs),
            repeat_event_rate=1.0 - len(unique_pairs) / max(1, len(all_events)),
            view_pairs=len(views),
            purchase_pairs=len(purchases),
            view_only_pairs=len(views - purchases),
            converted_pairs=len(views & purchases),
            purchase_with_prior_view_fraction=prior_view_fraction,
            view_to_purchase_lift=view_to_purchase_lift,
            per_user_unique_item_quantiles=quantiles,
            popularity_gini=_gini(popularity),
            popularity_top_shares={
                "top_1": float(popularity[:1].sum() / total_popularity),
                "top_10": float(popularity[:10].sum() / total_popularity),
                "top_100": float(popularity[:100].sum() / total_popularity),
            },
            product_distribution_js={
                "train_val": _jensen_shannon(distributions["train"], distributions["val"]),
                "val_test": _jensen_shannon(distributions["val"], distributions["test"]),
                "train_test": _jensen_shannon(distributions["train"], distributions["test"]),
            },
            organic_novel_purchase_users=novel_users,
            strict_context_coverage=context_coverage,
            fixture_event_counts=fixture_counts,
            legacy_origin_defaulted=legacy_origin,
            training_suitability_passed=not failures,
            gate_failures=tuple(failures),
        )
