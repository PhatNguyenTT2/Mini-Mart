from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hybrid_recsys.adapters.instacart import load_instacart_runtime_view
from hybrid_recsys.errors import IntegrityError
from hybrid_recsys.evaluation.evaluator import FullCatalogEvaluator
from hybrid_recsys.hashing import canonical_json_bytes, load_strict_json, sha256_file

from .instacart_runtime_fixture import build_instacart_runtime_fixture


def test_instacart_runtime_view_keeps_test_locked_and_maps_validation_lazily(
    tmp_path: Path,
) -> None:
    root = tmp_path / "instacart-runtime"
    locked_test_path, manifest_sha256 = build_instacart_runtime_fixture(root)

    view = load_instacart_runtime_view(
        root,
        expected_manifest_sha256=manifest_sha256,
        cutoff=3,
    )

    assert not locked_test_path.exists()
    assert view.test_access_state == "LOCKED_NOT_ACCESSED"
    assert view.raw_user_ids == (10, 20, 30)
    assert view.raw_item_ids == (2, 4, 7)
    assert [
        (batch.user_ids.tolist(), batch.item_ids.tolist())
        for batch in view.iter_train_pairs(batch_size=2)
    ] == [([0, 0], [0, 1]), ([1, 2], [1, 2])]
    assert [
        (record.item_id, record.raw_item_id, record.text, record.category, record.price)
        for record in view.iter_item_records()
    ] == [
        (0, 2, "product 2", "department_id=1|aisle_id=2", None),
        (1, 4, "product 4", "department_id=1|aisle_id=2", None),
        (2, 7, "product 7", "department_id=1|aisle_id=2", None),
    ]
    assert [
        (basket.user_id, basket.order_number, basket.raw_order_id, basket.item_ids)
        for basket in view.iter_train_baskets()
    ] == [
        (0, 1, 101, (0, 1)),
        (1, 1, 201, (1,)),
        (2, 1, 301, (2,)),
    ]

    protocol = view.validation_protocol
    assert protocol.num_total_users == 3
    assert protocol.eligible_user_ids == (0, 1)
    assert protocol.candidate_item_ids == (0, 1, 2)
    assert protocol.raw_item_ids == (2, 4, 7)
    assert protocol.case_for(0).history_item_ids == frozenset({0, 1})
    assert protocol.case_for(0).positive_item_ids == frozenset({2})
    assert protocol.case_for(1).history_item_ids == frozenset({1})
    assert protocol.case_for(1).positive_item_ids == frozenset({0})

    evaluator = FullCatalogEvaluator(protocol)

    def scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        positive = next(iter(protocol.case_for(user_id).positive_item_ids))
        return np.asarray([1.0 if item_id == positive else 0.0 for item_id in candidates])

    result = evaluator.evaluate(scorer, run_id="fixture-run", model_id="fixture-model")
    assert result.receipt.aggregate_metrics["NDCG@3"] == 1.0


def test_instacart_runtime_view_rejects_opened_test_boundary(tmp_path: Path) -> None:
    root = tmp_path / "instacart-runtime"
    build_instacart_runtime_fixture(root)
    manifest_path = root / "runtime_materialization_manifest.json"
    document = load_strict_json(manifest_path)
    document["test_boundary"]["content_parsed"] = True
    manifest_path.write_bytes(canonical_json_bytes(document) + b"\n")

    with pytest.raises(IntegrityError, match="TEST boundary"):
        load_instacart_runtime_view(
            root,
            expected_manifest_sha256=sha256_file(manifest_path),
            cutoff=3,
        )


def test_instacart_train_baskets_reject_prior_source_drift(tmp_path: Path) -> None:
    root = tmp_path / "instacart-runtime"
    _, manifest_sha256 = build_instacart_runtime_fixture(root)
    view = load_instacart_runtime_view(
        root,
        expected_manifest_sha256=manifest_sha256,
        cutoff=3,
    )
    with (root / "source" / "order_products__prior.csv").open(
        "a", encoding="utf-8", newline=""
    ) as stream:
        stream.write("\n")

    with pytest.raises(IntegrityError, match="source binding"):
        list(view.iter_train_baskets())
