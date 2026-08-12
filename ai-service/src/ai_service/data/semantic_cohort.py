"""Verified semantic-trap cohort loader for immutable snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ai_service.contracts import SplitName
from ai_service.errors import ArtifactIntegrityError


class SemanticCohortCase(BaseModel):
    trap_id: int = Field(ge=1, le=10)
    user_id: int = Field(gt=0)
    anchor_product_id: int
    target_product_id: int
    split: Literal["val", "test"]


def load_semantic_cohort(
    snapshot_dir: Path,
    *,
    split: SplitName = SplitName.VAL,
    allow_empty: bool = False,
) -> tuple[SemanticCohortCase, ...]:
    """Load only the snapshot-owned cohort; never invent a serving request."""
    path = snapshot_dir / "semantic-cohort.json"
    if not path.is_file():
        raise ArtifactIntegrityError("snapshot semantic cohort is missing")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("snapshot semantic cohort cannot be parsed") from error
    if not isinstance(document, list):
        raise ArtifactIntegrityError("snapshot semantic cohort must be a list")
    cases: list[SemanticCohortCase] = []
    seen: set[tuple[int, int, int, str]] = set()
    for row in document:
        if not isinstance(row, dict):
            raise ArtifactIntegrityError("snapshot semantic cohort row is invalid")
        event_id = str(row.get("event_id", ""))
        raw_split = "val" if ":val:" in event_id else "test" if ":test:" in event_id else None
        if raw_split != split.value:
            continue
        cohort_id = str(row.get("cohort_id", ""))
        try:
            trap_id = int(cohort_id.removeprefix("semantic-"))
            target_ids = row["target_product_ids"]
            if not isinstance(target_ids, list) or not target_ids:
                raise ValueError("target list is empty")
            user_id = int(row["user_id"])
            anchor_id = int(row["anchor_product_id"])
            targets = [int(value) for value in target_ids]
        except (KeyError, TypeError, ValueError) as error:
            raise ArtifactIntegrityError("semantic cohort target row is malformed") from error
        for target_id in targets:
            key = (trap_id, user_id, target_id, raw_split)
            if key in seen:
                raise ArtifactIntegrityError("semantic cohort contains duplicate target cases")
            seen.add(key)
            cases.append(
                SemanticCohortCase(
                    trap_id=trap_id,
                    user_id=user_id,
                    anchor_product_id=anchor_id,
                    target_product_id=target_id,
                    split=raw_split,
                )
            )
    if not cases and not allow_empty:
        raise ArtifactIntegrityError("semantic cohort has no cases for requested split")
    if cases and {case.trap_id for case in cases} != set(range(1, 11)):
        raise ArtifactIntegrityError("semantic cohort must contain all ten trap IDs")
    return tuple(cases)


__all__ = ["SemanticCohortCase", "load_semantic_cohort"]
