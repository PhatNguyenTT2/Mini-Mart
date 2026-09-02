"""Validation-only suitability checks for a canonical research snapshot."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.hashing import canonical_json_sha256
from ai_service_v2.protocol import build_protocol


@dataclass(frozen=True)
class DatasetSuitabilityReport:
    dataset_id: str
    dataset_manifest_sha256: str
    dataset_sha256: str
    dataset_classification: str
    observed_behavior: bool
    split_event_counts: dict[str, int]
    event_origin_counts: dict[str, int]
    distinct_user_item_cells: int
    distinct_cell_density: float
    event_frequency_density: float
    validation_eligible_users: int
    validation_users_without_novel_organic_truth: int
    organic_training_baskets: int
    semantic_training_baskets: int
    empty_text_items: int
    duplicate_normalized_text_items: int
    checks: dict[str, bool]
    blocking_findings: tuple[str, ...]
    verdict: str
    test_set_opened: bool = False

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "dataset-suitability/1.0",
            "dataset_id": self.dataset_id,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "dataset_sha256": self.dataset_sha256,
            "dataset_classification": self.dataset_classification,
            "observed_behavior": self.observed_behavior,
            "split_event_counts": dict(sorted(self.split_event_counts.items())),
            "event_origin_counts": dict(sorted(self.event_origin_counts.items())),
            "distinct_user_item_cells": self.distinct_user_item_cells,
            "distinct_cell_density": self.distinct_cell_density,
            "event_frequency_density": self.event_frequency_density,
            "validation_eligible_users": self.validation_eligible_users,
            "validation_users_without_novel_organic_truth": (
                self.validation_users_without_novel_organic_truth
            ),
            "organic_training_baskets": self.organic_training_baskets,
            "semantic_training_baskets": self.semantic_training_baskets,
            "empty_text_items": self.empty_text_items,
            "duplicate_normalized_text_items": self.duplicate_normalized_text_items,
            "checks": dict(sorted(self.checks.items())),
            "blocking_findings": list(self.blocking_findings),
            "verdict": self.verdict,
            "test_set_opened": self.test_set_opened,
            "accepted_result_rows": 0,
        }


def _provenance_admitted(status: str, *, fixture: bool) -> bool:
    return status == "VERIFIED" or (fixture and status == "TEST_ONLY")


def _license_admitted(status: str, *, fixture: bool) -> bool:
    return status in {
        "APPROVED_PRIVATE_RESEARCH",
        "APPROVED_RESEARCH_AND_REDISTRIBUTION",
        "OPEN_LICENSE_VERIFIED",
    } or (fixture and status == "TEST_ONLY")


def _language_admitted(status: str, *, fixture: bool) -> bool:
    return status == "AUDITED" or (fixture and status == "TEST_ONLY")


def assess_snapshot_suitability(snapshot: Snapshot) -> DatasetSuitabilityReport:
    """Assess lineage and task support without preparing or evaluating TEST."""

    manifest = snapshot.manifest
    all_events = tuple(
        event for split in ("train", "val", "test") for event in snapshot.events_by_split[split]
    )
    distinct_cells = len({(event.user_id, event.item_id) for event in all_events})
    possible_cells = manifest.num_users * manifest.num_items
    split_counts = {
        split: len(snapshot.events_by_split[split]) for split in ("train", "val", "test")
    }
    origin_counts = Counter(event.event_origin for event in all_events)
    validation = build_protocol(
        snapshot,
        split="val",
        cutoff=min(10, manifest.num_items),
    )
    normalized_text = [record.text.strip().casefold() for record in snapshot.item_records.values()]
    nonempty_text = [text for text in normalized_text if text]
    duplicate_text = len(nonempty_text) - len(set(nonempty_text))
    fixture = manifest.source_locator.startswith("fixture-")
    checks = {
        "source_bundle_bound": (
            manifest.schema_version == "dataset-manifest/1.1"
            and manifest.source_bundle_sha256 is not None
            and bool(manifest.source_artifact_hashes)
        ),
        "all_temporal_splits_nonempty": all(count > 0 for count in split_counts.values()),
        "validation_has_novel_organic_truth": bool(validation.eligible_user_ids),
        "organic_training_baskets_present": any(
            basket.origin == "organic" for basket in snapshot.training_baskets
        ),
        "cold_item_cohort_present": bool(snapshot.cold_item_ids),
        "catalog_text_complete": not any(not text for text in normalized_text),
        "catalog_provenance_admitted": _provenance_admitted(
            manifest.provenance_status, fixture=fixture
        ),
        "catalog_license_admitted": _license_admitted(manifest.license_status, fixture=fixture),
        "catalog_language_admitted": _language_admitted(manifest.language_status, fixture=fixture),
    }
    blockers = tuple(name for name, passed in sorted(checks.items()) if not passed)
    return DatasetSuitabilityReport(
        dataset_id=manifest.dataset_id,
        dataset_manifest_sha256=canonical_json_sha256(manifest.to_mapping()),
        dataset_sha256=manifest.dataset_sha256,
        dataset_classification=manifest.behavior_nature,
        observed_behavior=manifest.observed_behavior,
        split_event_counts=split_counts,
        event_origin_counts=dict(origin_counts),
        distinct_user_item_cells=distinct_cells,
        distinct_cell_density=distinct_cells / possible_cells,
        event_frequency_density=manifest.num_interactions / possible_cells,
        validation_eligible_users=len(validation.eligible_user_ids),
        validation_users_without_novel_organic_truth=(
            manifest.num_users - len(validation.eligible_user_ids)
        ),
        organic_training_baskets=sum(
            basket.origin == "organic" for basket in snapshot.training_baskets
        ),
        semantic_training_baskets=sum(
            basket.origin == "semantic_trap" for basket in snapshot.training_baskets
        ),
        empty_text_items=sum(not text for text in normalized_text),
        duplicate_normalized_text_items=duplicate_text,
        checks=checks,
        blocking_findings=blockers,
        verdict=(
            "PASS_CONTROLLED_INTERNAL_DATASET_SUITABILITY"
            if not blockers
            else "INCOMPLETE_DATASET_SUITABILITY"
        ),
    )


__all__ = ["DatasetSuitabilityReport", "assess_snapshot_suitability"]
