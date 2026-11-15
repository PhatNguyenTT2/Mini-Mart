from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ai_service_v2.data.rules import AprioriRuleTable, load_rule_table, save_rule_table
from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import ContractError


def test_rules_are_fit_from_train_only(snapshot: Snapshot) -> None:
    rules = AprioriRuleTable.fit(snapshot)
    assert rules.basket_count == 3
    assert rules.score({0}, 1) > 0
    # Item 4 occurs only in TEST and must not appear as a learned context pair.
    assert rules.score({4}, 0) == 0.0


def test_rule_fit_fails_closed_without_basket_ids(snapshot: Snapshot) -> None:
    events = dict(snapshot.events_by_split)
    events["train"] = tuple(replace(event, basket_id=None) for event in events["train"])
    with pytest.raises(ContractError, match="basket_id"):
        AprioriRuleTable.fit(
            Snapshot.from_fixture(
                snapshot.manifest,
                events,
                snapshot.item_records,
                raw_item_ids=snapshot.raw_item_ids,
            )
        )


def test_rule_artifact_round_trip_preserves_train_derived_table(
    snapshot: Snapshot, tmp_path: Path
) -> None:
    table = AprioriRuleTable.fit(snapshot)
    path = save_rule_table(table, tmp_path / "rules.json")
    loaded = load_rule_table(path)

    assert loaded == table
    assert loaded.content_sha256() == table.content_sha256()
