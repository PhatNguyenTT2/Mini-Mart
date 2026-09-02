"""Train-only pairwise association features for the proposed candidate."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError, IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, load_strict_json, sha256_bytes


@dataclass(frozen=True)
class AprioriRuleTable:
    """A small, deterministic one-step association-rule table.

    This is an internal rule-feature implementation for the proposed model,
    not an official reproduction of a particular Apriori repository.  It is
    fitted exclusively from TRAIN purchase baskets and therefore can be tested
    for leakage independently of the model.
    """

    pair_confidence: dict[tuple[int, int], float]
    context_counts: dict[int, int]
    basket_count: int
    min_support: int

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "apriori-rules/1.0",
            "basket_count": self.basket_count,
            "min_support": self.min_support,
            "context_counts": [
                {"item_id": item_id, "count": count}
                for item_id, count in sorted(self.context_counts.items())
            ],
            "pair_confidence": [
                {
                    "context_item_id": left,
                    "candidate_item_id": right,
                    "confidence": confidence,
                }
                for (left, right), confidence in sorted(self.pair_confidence.items())
            ],
        }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> AprioriRuleTable:
        required = {
            "schema_version",
            "basket_count",
            "min_support",
            "context_counts",
            "pair_confidence",
        }
        if set(value) != required or value["schema_version"] != "apriori-rules/1.0":
            raise IntegrityError("rule artifact fields do not match schema")
        basket_count = value["basket_count"]
        min_support = value["min_support"]
        if any(
            isinstance(number, bool) or not isinstance(number, int) or number < 1
            for number in (basket_count, min_support)
        ):
            raise IntegrityError("rule artifact counts are invalid")
        context_rows = value["context_counts"]
        pair_rows = value["pair_confidence"]
        if not isinstance(context_rows, list) or not isinstance(pair_rows, list):
            raise IntegrityError("rule artifact rows must be lists")
        contexts: dict[int, int] = {}
        for row in context_rows:
            if not isinstance(row, dict) or set(row) != {"item_id", "count"}:
                raise IntegrityError("rule context row fields are invalid")
            item_id, count = row["item_id"], row["count"]
            if (
                isinstance(item_id, bool)
                or not isinstance(item_id, int)
                or item_id < 0
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 1
                or item_id in contexts
            ):
                raise IntegrityError("rule context row is invalid")
            contexts[item_id] = count
        pairs: dict[tuple[int, int], float] = {}
        for row in pair_rows:
            if not isinstance(row, dict) or set(row) != {
                "context_item_id",
                "candidate_item_id",
                "confidence",
            }:
                raise IntegrityError("rule pair row fields are invalid")
            left = row["context_item_id"]
            right = row["candidate_item_id"]
            confidence = row["confidence"]
            if (
                isinstance(left, bool)
                or not isinstance(left, int)
                or left < 0
                or isinstance(right, bool)
                or not isinstance(right, int)
                or right < 0
                or left == right
                or isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not math.isfinite(float(confidence))
                or confidence < 0
                or confidence > 1
                or (left, right) in pairs
            ):
                raise IntegrityError("rule pair row is invalid")
            pairs[(left, right)] = float(confidence)
        return cls(pairs, contexts, basket_count, min_support)

    def content_sha256(self) -> str:
        return sha256_bytes(canonical_json_bytes(self.to_mapping()))

    @classmethod
    def fit(cls, snapshot: Snapshot, *, min_support: int = 1) -> AprioriRuleTable:
        if min_support < 1:
            raise ContractError("min_support must be positive")
        baskets = [
            set(basket.item_ids)
            for basket in snapshot.training_baskets
            if basket.origin == "organic"
        ]
        if not baskets:
            train_purchases = [
                event
                for event in snapshot.events_by_split["train"]
                if event.event_type == "purchase"
            ]
            if train_purchases and any(event.basket_id is None for event in train_purchases):
                raise ContractError("TRAIN purchase events require basket_id for rule fitting")
            raise ContractError("cannot fit rules without organic TRAIN purchase baskets")

        item_counts: Counter[int] = Counter()
        pair_counts: Counter[tuple[int, int]] = Counter()
        for items in baskets:
            for item in items:
                item_counts[item] += 1
            for left in items:
                for right in items:
                    if left != right:
                        pair_counts[(left, right)] += 1
        confidence = {
            pair: count / item_counts[pair[0]]
            for pair, count in pair_counts.items()
            if count >= min_support
        }
        return cls(
            pair_confidence=confidence,
            context_counts=dict(item_counts),
            basket_count=len(baskets),
            min_support=min_support,
        )

    def score(self, history_items: set[int], candidate_item: int) -> float:
        return float(
            sum(
                self.pair_confidence.get((context, candidate_item), 0.0)
                for context in history_items
            )
        )


def save_rule_table(table: AprioriRuleTable, path: Path) -> Path:
    """Write a train-derived rule artifact exactly once."""

    if path.exists():
        raise IntegrityError(f"rule artifact already exists: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(table.to_mapping()) + b"\n")
    except OSError as error:
        raise IntegrityError(f"could not write rule artifact: {path}") from error
    return path


def load_rule_table(path: Path) -> AprioriRuleTable:
    return AprioriRuleTable.from_mapping(load_strict_json(path))


__all__ = ["AprioriRuleTable", "load_rule_table", "save_rule_table"]
