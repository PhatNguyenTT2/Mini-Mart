from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError
from ai_service_v2.evaluation.evaluator import FullCatalogEvaluator
from ai_service_v2.evaluation.persistence import load_evaluation, save_evaluation
from ai_service_v2.hashing import canonical_json_bytes, load_strict_json
from ai_service_v2.protocol import build_protocol


def test_evaluation_bundle_round_trips_and_is_hash_bound(
    snapshot: Snapshot, tmp_path: Path
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)

    def scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        target = 2 if user_id == 0 else 3
        return np.asarray([10.0 if item == target else 0.0 for item in candidates])

    result = FullCatalogEvaluator(protocol).evaluate(
        scorer,
        run_id="run",
        model_id="model",
    )
    saved = save_evaluation(result, tmp_path / "evaluation")
    loaded = load_evaluation(saved.root)
    assert loaded.receipt == result.receipt
    assert loaded.user_ids == result.user_ids
    assert loaded.per_user_metrics == result.per_user_metrics


def test_evaluation_loader_rejects_mutated_per_user_value(
    snapshot: Snapshot, tmp_path: Path
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)

    def scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        del user_id
        return np.zeros(len(candidates), dtype=np.float64)

    result = FullCatalogEvaluator(protocol).evaluate(
        scorer,
        run_id="run",
        model_id="model",
    )
    root = save_evaluation(result, tmp_path / "evaluation").root
    path = root / "per_user_metrics.json"
    path.write_text(
        path.read_text(encoding="utf-8").replace('"HR@5":1.0', '"HR@5":0.0', 1),
        encoding="utf-8",
    )
    with pytest.raises(IntegrityError, match="hash"):
        load_evaluation(root)


def test_evaluation_loader_rejects_receipt_user_count_inconsistency(
    snapshot: Snapshot, tmp_path: Path
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)

    def scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        del user_id
        return np.zeros(len(candidates), dtype=np.float64)

    result = FullCatalogEvaluator(protocol).evaluate(
        scorer,
        run_id="run",
        model_id="model",
    )
    root = save_evaluation(result, tmp_path / "evaluation").root
    receipt_path = root / "evaluation_receipt.json"
    receipt_document = load_strict_json(receipt_path)
    receipt_document["receipt"]["num_eligible_users"] += 1
    receipt_path.write_bytes(canonical_json_bytes(receipt_document) + b"\n")

    with pytest.raises(IntegrityError, match="eligible user count"):
        load_evaluation(root)
