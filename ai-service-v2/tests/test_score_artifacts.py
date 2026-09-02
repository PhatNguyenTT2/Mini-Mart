from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ai_service_v2.data.snapshot import Snapshot
from ai_service_v2.errors import IntegrityError, ScoreError
from ai_service_v2.evaluation.artifacts import (
    MatrixScoreProvider,
    load_materialized_scores,
    load_score_matrix,
    materialize_scores,
)
from ai_service_v2.protocol import build_protocol


def test_scores_are_chunked_and_reloaded_with_hashes(snapshot: Snapshot, tmp_path: Path) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)

    def scorer(user_id: int, candidates: tuple[int, ...]) -> np.ndarray:
        return np.asarray([user_id + item / 10.0 for item in candidates])

    materialized = materialize_scores(
        protocol,
        scorer,
        root=tmp_path / "scores",
        run_id="score-run",
        model_id="score-model",
        chunk_size=1,
    )
    assert len(materialized.chunks) == 2
    matrix = load_score_matrix(materialized)
    assert matrix.shape == (2, 5)
    assert matrix.dtype == np.float32
    reloaded = load_materialized_scores(tmp_path / "scores")
    provider = MatrixScoreProvider(
        reloaded, protocol.eligible_user_ids, protocol.candidate_item_ids
    )
    assert np.array_equal(provider(0, protocol.candidate_item_ids), matrix[0])


def test_score_root_is_immutable(snapshot: Snapshot, tmp_path: Path) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    root = tmp_path / "scores"
    root.mkdir()
    with pytest.raises(IntegrityError, match="already exists"):
        materialize_scores(
            protocol,
            lambda user_id, candidates: np.ones(len(candidates)),
            root=root,
            run_id="run",
            model_id="model",
        )


def test_score_artifact_rejects_wrong_shape_and_nonfinite(
    snapshot: Snapshot, tmp_path: Path
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    with pytest.raises(ScoreError, match="wrong shape"):
        materialize_scores(
            protocol,
            lambda user_id, candidates: np.ones(2),
            root=tmp_path / "wrong-shape",
            run_id="run",
            model_id="model",
        )
    with pytest.raises(ScoreError, match="non-finite"):
        materialize_scores(
            protocol,
            lambda user_id, candidates: np.full(len(candidates), np.nan),
            root=tmp_path / "nonfinite",
            run_id="run",
            model_id="model",
        )


def test_score_loader_rejects_extra_file(snapshot: Snapshot, tmp_path: Path) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    root = tmp_path / "scores"
    materialize_scores(
        protocol,
        lambda user_id, candidates: np.zeros(len(candidates)),
        root=root,
        run_id="run",
        model_id="model",
    )
    (root / "unexpected.txt").write_text("x", encoding="utf-8")
    with pytest.raises(IntegrityError, match="unexpected"):
        load_materialized_scores(root)


@pytest.mark.parametrize(("chunk_index", "first_user_index"), ((0, 1), (1, 0)))
def test_score_loader_rejects_chunk_gap_or_overlap(
    snapshot: Snapshot, tmp_path: Path, chunk_index: int, first_user_index: int
) -> None:
    protocol = build_protocol(snapshot, split="val", cutoff=5)
    root = tmp_path / "scores"
    materialize_scores(
        protocol,
        lambda user_id, candidates: np.zeros(len(candidates)),
        root=root,
        run_id="run",
        model_id="model",
        chunk_size=1,
    )
    manifest_path = root / "manifest.json"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["chunks"][chunk_index]["first_user_index"] = first_user_index
    manifest_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(IntegrityError, match=r"contiguous|gap|overlap"):
        load_materialized_scores(root)
