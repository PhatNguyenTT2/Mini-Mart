from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError, ProtocolError, ScoreError
from ai_service_v2.protocol import build_protocol, load_protocol, save_protocol


def test_validation_protocol_uses_train_history(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    assert protocol.eligible_user_ids == (0, 1)
    assert protocol.case_for(0).history_item_ids == frozenset({0, 1})
    assert protocol.case_for(0).positive_item_ids == frozenset({2})
    assert protocol.manifest.test_set_opened is False
    assert protocol.candidate_item_ids == (0, 1, 2, 3, 4)


def test_test_protocol_is_sealed_by_default(snapshot: Snapshot) -> None:
    with pytest.raises(ProtocolError, match="TEST is sealed"):
        build_protocol(snapshot, split="test", cutoff=5)
    protocol = build_protocol(snapshot, split="test", allow_test=True, cutoff=5)
    assert protocol.manifest.test_set_opened is True
    assert protocol.eligible_user_ids == (0, 1)


def test_mask_is_copy_and_rejects_bad_scores(snapshot: Snapshot) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    original = np.arange(5, dtype=float)
    masked = protocol.mask_scores(0, original)
    assert np.array_equal(original, np.arange(5, dtype=float))
    assert np.isneginf(masked[0]) and np.isneginf(masked[1])
    with pytest.raises(ScoreError, match="non-finite"):
        protocol.mask_scores(0, np.array([0.0, np.nan, 1.0, 2.0, 3.0]))
    with pytest.raises(ScoreError, match="shape"):
        protocol.mask_scores(0, np.ones(4))


def test_snapshot_does_not_silently_sort_events(snapshot: Snapshot) -> None:
    from ai_service_v2.data.snapshot import Snapshot
    from ai_service_v2.errors import ContractError

    events = dict(snapshot.events_by_split)
    events["train"] = tuple(reversed(events["train"]))
    with pytest.raises(ContractError, match="timestamp ordered"):
        Snapshot.from_fixture(
            snapshot.manifest,
            events,
            snapshot.item_records,
            raw_item_ids=snapshot.raw_item_ids,
        )


def test_protocol_round_trip_replays_against_snapshot(snapshot: Snapshot, tmp_path: Path) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    path = save_protocol(protocol, tmp_path / "protocol")
    restored = load_protocol(path, snapshot=snapshot)
    assert restored.manifest == protocol.manifest
    assert restored.cases == protocol.cases


def test_protocol_replay_rejects_mutated_case(snapshot: Snapshot, tmp_path: Path) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    path = save_protocol(protocol, tmp_path / "protocol")
    document = path.read_text(encoding="utf-8").replace(
        '"positive_item_ids":[2]', '"positive_item_ids":[3]'
    )
    path.write_text(document, encoding="utf-8")
    with pytest.raises(IntegrityError, match="protocol"):
        load_protocol(path, snapshot=snapshot)
