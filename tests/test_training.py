from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hybrid_recsys.data.io import load_canonical_snapshot
from hybrid_recsys.data.snapshot import Snapshot
from hybrid_recsys.errors import IntegrityError
from hybrid_recsys.training.deep import build_train_examples
from hybrid_recsys.training.inputs import build_test_protocol, load_pipeline_inputs

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "fixture-retail-v1"


def _write_features(snapshot: Snapshot, root: Path) -> None:
    train_items = sorted({event.item_id for event in snapshot.events_by_split["train"]})
    raw = np.asarray([snapshot.raw_item_ids[item] for item in train_items], dtype=np.int64)
    root.mkdir(parents=True, exist_ok=True)
    np.save(root / "raw_item_ids.npy", raw)
    np.save(root / "text_embeddings.npy", np.ones((len(raw), 384), dtype=np.float32))
    np.save(root / "category_ids.npy", np.zeros(len(raw), dtype=np.int64))


def test_pipeline_inputs_use_train_catalog_and_never_open_test(tmp_path: Path) -> None:
    full = load_canonical_snapshot(FIXTURE_ROOT)
    _write_features(full, tmp_path / "features")
    inputs = load_pipeline_inputs(FIXTURE_ROOT, tmp_path / "features")
    assert set(inputs.snapshot.events_by_split) == {"train", "val"}
    assert not inputs.validation_protocol.manifest.test_set_opened
    train_items = {event.item_id for event in full.events_by_split["train"]}
    assert set(inputs.item_id_map) == train_items
    assert sorted(inputs.item_id_map.values()) == list(range(len(train_items)))
    for user in inputs.validation_protocol.eligible_user_ids:
        case = inputs.validation_protocol.case_for(user)
        assert not case.positive_item_ids & case.history_item_ids


def test_pipeline_inputs_reject_features_outside_train_catalog(tmp_path: Path) -> None:
    full = load_canonical_snapshot(FIXTURE_ROOT)
    _write_features(full, tmp_path / "features")
    raw = np.load(tmp_path / "features" / "raw_item_ids.npy")
    np.save(tmp_path / "features" / "raw_item_ids.npy", raw[:-1])
    with pytest.raises(IntegrityError):
        load_pipeline_inputs(FIXTURE_ROOT, tmp_path / "features")


def test_test_protocol_uses_train_and_validation_history(tmp_path: Path) -> None:
    full = load_canonical_snapshot(FIXTURE_ROOT)
    _write_features(full, tmp_path / "features")
    inputs = load_pipeline_inputs(FIXTURE_ROOT, tmp_path / "features")
    test = build_test_protocol(full, inputs.validation_protocol, inputs.item_id_map)
    assert test.manifest.test_set_opened
    assert test.candidate_item_ids == inputs.validation_protocol.candidate_item_ids
    for user in test.eligible_user_ids:
        history = {
            inputs.item_id_map[e.item_id]
            for split in ("train", "val")
            for e in full.events_by_split[split]
            if e.user_id == user and e.item_id in inputs.item_id_map
        }
        case = test.case_for(user)
        assert set(case.history_item_ids) == history
        assert not case.positive_item_ids & history


def test_train_examples_use_strict_prefix_and_whole_basket(snapshot: Snapshot) -> None:
    examples = build_train_examples(snapshot)
    first = [e for e in examples if e.user_id == 0]
    assert first[0].history_item_ids == ()
    assert set(first[0].target_basket_item_ids) == {0, 1}
    for example in examples:
        assert example.positive_item_id not in example.history_item_ids
        assert example.positive_item_id in example.target_basket_item_ids
