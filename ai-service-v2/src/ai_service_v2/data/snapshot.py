"""In-memory representation of a verified, immutable benchmark snapshot."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ai_service_v2.contracts import DatasetManifest
from ai_service_v2.errors import ContractError
from ai_service_v2.hashing import assert_canonical_json_file, canonical_json_sha256


@dataclass(frozen=True)
class Interaction:
    """One canonical event after raw IDs have been mapped to dense IDs."""

    event_id: int
    user_id: int
    item_id: int
    timestamp: int
    event_type: str
    basket_id: str | None = None
    raw_event_id: str | None = None
    event_origin: str = "organic"
    session_id: str | None = None
    cohort_id: str | None = None

    def __post_init__(self) -> None:
        if self.event_id < 0 or self.user_id < 0 or self.item_id < 0:
            raise ContractError("event, user, and item IDs must be non-negative")
        if self.timestamp < 0:
            raise ContractError("timestamp must be a non-negative epoch value")
        if not self.event_type:
            raise ContractError("event_type must be non-empty")
        if self.raw_event_id is not None and not self.raw_event_id:
            raise ContractError("raw_event_id must be non-empty when present")
        if self.event_origin not in {"organic", "semantic_trap", "cold_start"}:
            raise ContractError(f"unsupported event_origin: {self.event_origin}")


@dataclass(frozen=True)
class TrainingBasket:
    """One source-bound training basket used by the association-rule lane."""

    basket_id: str
    user_id: int
    timestamp: int
    item_ids: tuple[int, ...]
    origin: str

    def __post_init__(self) -> None:
        if not self.basket_id:
            raise ContractError("basket_id must be non-empty")
        if self.user_id < 0 or self.timestamp < 0:
            raise ContractError("basket user and timestamp must be non-negative")
        if len(self.item_ids) < 2 or len(set(self.item_ids)) != len(self.item_ids):
            raise ContractError("training basket must contain at least two unique items")
        if any(item_id < 0 for item_id in self.item_ids):
            raise ContractError("training basket item IDs must be non-negative")
        if self.origin not in {"organic", "semantic_trap"}:
            raise ContractError(f"unsupported training basket origin: {self.origin}")


@dataclass(frozen=True)
class ItemRecord:
    """Content fields available to content-aware models."""

    item_id: int
    raw_item_id: int
    text: str
    category: str
    price: float | None

    def __post_init__(self) -> None:
        if self.item_id < 0:
            raise ContractError("item_id must be non-negative")
        if not self.category:
            raise ContractError("category must be non-empty")
        if self.price is not None and self.price < 0:
            raise ContractError("price must be non-negative when present")


@dataclass(frozen=True)
class Snapshot:
    """Verified snapshot used by every adapter and evaluator.

    The object is deliberately independent of pandas, a database connection,
    Docker, and model code.  Adapters may materialize it from any storage
    format, but once constructed all downstream modules see this same shape.
    Internal item IDs are dense ``0..num_items-1``; raw IDs remain explicit.
    """

    manifest: DatasetManifest
    users: tuple[int, ...]
    items: tuple[int, ...]
    raw_user_ids: tuple[int, ...]
    raw_item_ids: tuple[int, ...]
    events_by_split: Mapping[str, tuple[Interaction, ...]]
    item_records: Mapping[int, ItemRecord]
    training_baskets: tuple[TrainingBasket, ...]

    def __post_init__(self) -> None:
        expected_users = tuple(range(self.manifest.num_users))
        expected_items = tuple(range(self.manifest.num_items))
        if self.users != expected_users:
            raise ContractError("users must be dense internal IDs in ascending order")
        if self.items != expected_items:
            raise ContractError("items must be dense internal IDs in ascending order")
        if len(self.raw_user_ids) != self.manifest.num_users:
            raise ContractError("raw_user_ids length does not match num_users")
        if len(set(self.raw_user_ids)) != len(self.raw_user_ids):
            raise ContractError("raw_user_ids must be unique")
        if len(self.raw_item_ids) != self.manifest.num_items:
            raise ContractError("raw_item_ids length does not match num_items")
        if len(set(self.raw_item_ids)) != len(self.raw_item_ids):
            raise ContractError("raw_item_ids must be unique")
        loaded_splits = tuple(self.events_by_split)
        if loaded_splits not in {
            ("train",),
            ("train", "val"),
            ("train", "val", "test"),
        }:
            raise ContractError("events_by_split must be a canonical temporal prefix")
        if set(self.item_records) != set(self.items):
            raise ContractError("item_records must cover every internal item")
        total = 0
        global_event_ids: set[int] = set()
        global_raw_event_ids: set[str] = set()
        for split, events in self.events_by_split.items():
            previous_timestamp = -1
            for event in events:
                if event.event_id in global_event_ids:
                    raise ContractError(f"duplicate event_id across splits: {event.event_id}")
                global_event_ids.add(event.event_id)
                if event.raw_event_id is not None:
                    if event.raw_event_id in global_raw_event_ids:
                        raise ContractError(
                            f"duplicate raw_event_id across splits: {event.raw_event_id}"
                        )
                    global_raw_event_ids.add(event.raw_event_id)
                if event.user_id not in self.users or event.item_id not in self.items:
                    raise ContractError(f"event references an unknown ID in {split}")
                if event.timestamp < previous_timestamp:
                    raise ContractError(f"events must be timestamp ordered in {split}")
                previous_timestamp = event.timestamp
            total += len(events)
        if "test" in self.events_by_split:
            if total != self.manifest.num_interactions:
                raise ContractError("event counts do not match manifest")
        elif total >= self.manifest.num_interactions:
            raise ContractError("partial snapshot event count is inconsistent with manifest")
        if any(record.item_id not in self.items for record in self.item_records.values()):
            raise ContractError("item record references an unknown item")
        basket_ids: set[str] = set()
        previous_basket_timestamp = -1
        for basket in self.training_baskets:
            if basket.basket_id in basket_ids:
                raise ContractError(f"duplicate training basket: {basket.basket_id}")
            basket_ids.add(basket.basket_id)
            if basket.user_id not in self.users or any(
                item_id not in self.items for item_id in basket.item_ids
            ):
                raise ContractError("training basket references an unknown ID")
            if basket.timestamp < previous_basket_timestamp:
                raise ContractError("training baskets must be timestamp ordered")
            previous_basket_timestamp = basket.timestamp
        if (
            self.manifest.schema_version == "dataset-manifest/1.1"
            and len(self.training_baskets) != self.manifest.num_baskets
        ):
            raise ContractError("training basket count does not match manifest")

    @property
    def cold_item_ids(self) -> frozenset[int]:
        return frozenset(self.manifest.cold_item_ids)

    def history_events(self, split: str) -> tuple[Interaction, ...]:
        if split == "val":
            if "val" not in self.events_by_split:
                raise ContractError("validation split is not loaded")
            return self.events_by_split["train"]
        if split == "test":
            if "test" not in self.events_by_split:
                raise ContractError("TEST split is not loaded")
            return self.events_by_split["train"] + self.events_by_split["val"]
        raise ValueError("history is defined only for val or test")

    def target_events(self, split: str) -> tuple[Interaction, ...]:
        if split not in {"val", "test"}:
            raise ValueError("target is defined only for val or test")
        if split not in self.events_by_split:
            raise ContractError(f"{split} split is not loaded")
        return self.events_by_split[split]

    def events_for_user(self, events: Iterable[Interaction]) -> dict[int, tuple[Interaction, ...]]:
        grouped: dict[int, list[Interaction]] = {user: [] for user in self.users}
        for event in events:
            grouped[event.user_id].append(event)
        return {user: tuple(rows) for user, rows in grouped.items()}

    @classmethod
    def from_fixture(
        cls,
        manifest: DatasetManifest,
        events_by_split: Mapping[str, Iterable[Interaction]],
        item_records: Mapping[int, ItemRecord],
        *,
        raw_user_ids: tuple[int, ...] | None = None,
        raw_item_ids: tuple[int, ...] | None = None,
        training_baskets: Iterable[TrainingBasket] | None = None,
    ) -> Snapshot:
        """Construct a snapshot for deterministic tests and local smoke runs."""

        # Preserve caller order so the constructor can reject unsorted input;
        # silently sorting a source would hide a lineage/data-quality defect.
        frozen_events = {split: tuple(events) for split, events in events_by_split.items()}
        frozen_baskets: tuple[TrainingBasket, ...]
        if training_baskets is None:
            grouped: dict[str, list[Interaction]] = {}
            for event in frozen_events.get("train", ()):
                if event.event_type == "purchase" and event.basket_id is not None:
                    grouped.setdefault(event.basket_id, []).append(event)
            derived: list[TrainingBasket] = []
            for basket_id, rows in grouped.items():
                origins = {row.event_origin for row in rows}
                users = {row.user_id for row in rows}
                if len(origins) != 1 or len(users) != 1:
                    raise ContractError("derived training basket has mixed user or origin")
                derived.append(
                    TrainingBasket(
                        basket_id=basket_id,
                        user_id=rows[0].user_id,
                        timestamp=max(row.timestamp for row in rows),
                        item_ids=tuple(sorted({row.item_id for row in rows})),
                        origin=rows[0].event_origin,
                    )
                )
            frozen_baskets = tuple(sorted(derived, key=lambda row: (row.timestamp, row.basket_id)))
        else:
            frozen_baskets = tuple(training_baskets)
        return cls(
            manifest=manifest,
            users=tuple(range(manifest.num_users)),
            items=tuple(range(manifest.num_items)),
            raw_user_ids=raw_user_ids or tuple(range(manifest.num_users)),
            raw_item_ids=raw_item_ids or tuple(range(manifest.num_items)),
            events_by_split=frozen_events,
            item_records=dict(item_records),
            training_baskets=frozen_baskets,
        )


def load_dataset_manifest(path: str) -> DatasetManifest:
    """Load a strict manifest without silently repairing its bytes."""

    parsed = assert_canonical_json_file(Path(path), canonical_json_sha256_from_file(Path(path)))
    return DatasetManifest.from_mapping(parsed)


def canonical_json_sha256_from_file(path: Path) -> str:
    """Return the canonical hash for a strict JSON object on disk."""

    from ai_service_v2.hashing import load_strict_json

    parsed = load_strict_json(path)
    return canonical_json_sha256(parsed)


__all__ = [
    "Interaction",
    "ItemRecord",
    "Snapshot",
    "TrainingBasket",
    "load_dataset_manifest",
]
