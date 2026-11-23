from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hybrid_recsys.contracts import ProtocolManifest
from hybrid_recsys.data.pair_rules import (
    load_pair_rule_table,
    materialize_pair_rules,
    rule_aligned_user_ids,
)
from hybrid_recsys.errors import IntegrityError
from hybrid_recsys.protocol import PreparedProtocol, UserEvaluationCase

from .training_view_fixture import FixtureTrainingView


def _protocol(candidate_hash: str) -> PreparedProtocol:
    manifest = ProtocolManifest(
        protocol_id="pair-rule-fixture:val",
        dataset_id="pair-rule-fixture",
        dataset_manifest_sha256="a" * 64,
        split="val",
        split_hash="b" * 64,
        candidate_item_ids=(0, 1, 2, 3),
        candidate_order_sha256=candidate_hash,
        eligible_user_rule="fixture",
        positive_rule="fixture",
        seen_masking="fixture",
        cutoff=3,
        tie_break="descending_score_then_ascending_raw_product_id",
        metric_version="ranking-v1",
        test_set_opened=False,
    )
    return PreparedProtocol(
        manifest=manifest,
        raw_item_ids=(2, 4, 7, 9),
        cases={
            0: UserEvaluationCase(0, frozenset({0, 1}), frozenset({3})),
            1: UserEvaluationCase(1, frozenset({2}), frozenset({1})),
            2: UserEvaluationCase(2, frozenset(), frozenset({0})),
        },
        num_total_users=3,
    )


def test_pair_rules_are_fractional_train_only_and_disk_backed(tmp_path: Path) -> None:
    rules = materialize_pair_rules(
        FixtureTrainingView(),
        root=tmp_path / "rules",
        min_support_fraction=0.0005,
        max_pairs_in_memory=1,
    )
    assert rules.basket_count == 4
    assert rules.min_support_count == 1
    assert rules.pair_count == 4
    assert rules.antecedent_ids == (0, 1, 2, 3)
    assert rules.score(frozenset({0, 1}), (0, 1, 2, 3)).tolist() == [
        0.0,
        0.0,
        1.0,
        1.0,
    ]
    assert not (rules.root / ".pair-counts.sqlite3").exists()


def test_pair_rule_artifact_replays_and_detects_drift(tmp_path: Path) -> None:
    rules = materialize_pair_rules(
        FixtureTrainingView(),
        root=tmp_path / "rules",
        min_support_fraction=0.001,
    )
    loaded = load_pair_rule_table(
        rules.root,
        expected_manifest_sha256=rules.manifest_sha256,
    )
    assert np.array_equal(loaded.candidate_ids, rules.candidate_ids)
    with (rules.root / "confidences.npy").open("ab") as stream:
        stream.write(b"drift")
    with pytest.raises(IntegrityError, match="artifact mismatch"):
        load_pair_rule_table(
            rules.root,
            expected_manifest_sha256=rules.manifest_sha256,
        )


def test_rule_aligned_cohort_uses_train_history_only(tmp_path: Path) -> None:
    rules = materialize_pair_rules(
        FixtureTrainingView(),
        root=tmp_path / "rules",
        min_support_fraction=0.002,
    )
    assert rule_aligned_user_ids(_protocol(rules.candidate_order_sha256), rules) == (0, 1)


def test_pair_rule_materialization_rejects_open_test_boundary(tmp_path: Path) -> None:
    class OpenTestView(FixtureTrainingView):
        @property
        def test_access_state(self) -> str:
            return "OPENED"

    with pytest.raises(IntegrityError, match="locked TEST"):
        materialize_pair_rules(
            OpenTestView(),
            root=tmp_path / "rules",
            min_support_fraction=0.0005,
        )
