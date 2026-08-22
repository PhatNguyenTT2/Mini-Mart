from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ai_service.errors import ArtifactIntegrityError


def _document() -> dict[str, object]:
    cases = []
    for split, timestamp in (("val", "2026-06-20T00:00:00Z"), ("test", "2026-07-11T00:00:00Z")):
        for trap_id in range(1, 11):
            cases.append(
                {
                    "trap_id": trap_id,
                    "user_id": trap_id,
                    "anchor_product_id": 1000 + trap_id,
                    "target_product_id": 2000 + trap_id,
                    "split": split,
                    "anchor_event_id": f"anchor-{split}-{trap_id}",
                    "target_event_id": f"target-{split}-{trap_id}",
                    "anchor_event_ts": "2026-01-01T00:00:00Z",
                    "target_event_ts": timestamp,
                }
            )
    return {
        "schema_version": "1.0.0",
        "benchmark_run_id": "benchmark-v5",
        "benchmark_spec_sha256": "a" * 64,
        "cases": cases,
    }


def test_typed_semantic_cohort_loader_rejects_legacy_raw_events(tmp_path: Path) -> None:
    from ai_service.data.semantic_cohort import load_semantic_cohort

    path = tmp_path / "semantic-cohort.json"
    path.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="typed document"):
        load_semantic_cohort(tmp_path, expected_sha256="a" * 64)


def test_typed_semantic_cohort_loader_hashes_and_filters_cases(tmp_path: Path) -> None:
    from ai_service.data.semantic_cohort import (
        canonical_semantic_cohort_bytes,
        cases_for_split,
        load_semantic_cohort,
    )

    document = _document()
    payload = canonical_semantic_cohort_bytes(document)
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    (tmp_path / "semantic-cohort.json").write_bytes(payload)

    cohort = load_semantic_cohort(tmp_path, expected_sha256=expected_sha256)

    assert len(cohort.cases) == 20
    assert len(cases_for_split(cohort, "val")) == 10
    assert cases_for_split(cohort, "val")[0].target_event_id == "target-val-1"


def test_typed_semantic_cohort_rejects_duplicate_direction_and_hash_tampering(tmp_path: Path) -> None:
    from ai_service.data.semantic_cohort import canonical_semantic_cohort_bytes, load_semantic_cohort

    document = _document()
    document["cases"] = [*document["cases"], document["cases"][0]]  # type: ignore[index]
    path = tmp_path / "semantic-cohort.json"
    payload = canonical_semantic_cohort_bytes(document)
    path.write_bytes(payload)

    with pytest.raises(ArtifactIntegrityError, match="duplicate"):
        load_semantic_cohort(tmp_path, expected_sha256=hashlib.sha256(payload).hexdigest())

    path.write_bytes(canonical_semantic_cohort_bytes(_document()) + b" ")
    with pytest.raises(ArtifactIntegrityError, match="canonical"):
        load_semantic_cohort(tmp_path, expected_sha256="f" * 64)
