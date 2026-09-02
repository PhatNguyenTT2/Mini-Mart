"""Immutable, chunked score artifacts at the model/evaluator seam."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from ai_service_v2.contracts import ScoreArtifactManifest
from ai_service_v2.errors import IntegrityError, ScoreError
from ai_service_v2.evaluation.evaluator import ScoreProvider
from ai_service_v2.hashing import canonical_json_bytes, loads_strict_json, sha256_bytes
from ai_service_v2.protocol import PreparedProtocol


@dataclass(frozen=True)
class ScoreChunk:
    name: str
    first_user_index: int
    user_count: int
    sha256: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "first_user_index": self.first_user_index,
            "user_count": self.user_count,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class MaterializedScores:
    root: Path
    manifest: ScoreArtifactManifest
    chunks: tuple[ScoreChunk, ...]


class MatrixScoreProvider:
    """Score provider backed by a verified matrix in protocol user order."""

    def __init__(
        self,
        materialized: MaterializedScores,
        user_ids: tuple[int, ...],
        candidate_item_ids: tuple[int, ...],
    ) -> None:
        if materialized.manifest.num_users != len(user_ids):
            raise ScoreError("score matrix user count does not match provider IDs")
        if materialized.manifest.num_candidates != len(candidate_item_ids):
            raise ScoreError("score matrix candidate count does not match provider IDs")
        if materialized.manifest.user_order_sha256 != _ordered_ids_hash(user_ids):
            raise IntegrityError("score matrix user order hash does not match provider IDs")
        matrix = load_score_matrix(materialized)
        self._user_to_row = {user_id: index for index, user_id in enumerate(user_ids)}
        self._candidate_item_ids = candidate_item_ids
        self._matrix = matrix

    def __call__(self, user_id: int, candidate_item_ids: tuple[int, ...]) -> np.ndarray:
        if candidate_item_ids != self._candidate_item_ids:
            raise ScoreError("provider candidate order differs from frozen protocol")
        try:
            row = self._matrix[self._user_to_row[user_id]]
        except KeyError as error:
            raise ScoreError(f"unknown score-artifact user: {user_id}") from error
        return cast(np.ndarray, row.copy())


def _ensure_new_root(root: Path) -> None:
    if root.exists():
        raise IntegrityError(f"score artifact root already exists: {root}")
    try:
        root.mkdir(parents=True)
    except OSError as error:
        raise IntegrityError(f"cannot create score artifact root: {root}") from error


def _ordered_ids_hash(ids: tuple[int, ...]) -> str:
    return sha256_bytes(canonical_json_bytes({"ids": list(ids)}))


def materialize_scores(
    protocol: PreparedProtocol,
    scorer: ScoreProvider,
    *,
    root: Path,
    run_id: str,
    model_id: str,
    chunk_size: int = 128,
) -> MaterializedScores:
    """Write scores in immutable chunks and emit a hash-bound manifest.

    The scorer is called only in frozen user and candidate order.  No metric is
    computed here; this module only validates and records the score surface.
    """

    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    _ensure_new_root(root)
    users = protocol.eligible_user_ids
    candidates = protocol.candidate_item_ids
    chunks: list[ScoreChunk] = []
    for chunk_index, first in enumerate(range(0, len(users), chunk_size)):
        selected_users = users[first : first + chunk_size]
        matrix = np.empty((len(selected_users), len(candidates)), dtype=np.float32)
        for row_index, user_id in enumerate(selected_users):
            values = np.asarray(scorer(user_id, candidates), dtype=np.float32)
            if values.shape != (len(candidates),):
                raise ScoreError("scorer returned a vector with the wrong shape")
            if not np.isfinite(values).all():
                raise ScoreError("scorer returned non-finite values")
            matrix[row_index] = values
        name = f"scores-{chunk_index:05d}.npy"
        path = root / name
        try:
            with path.open("wb") as stream:
                np.save(stream, matrix, allow_pickle=False)
            payload = path.read_bytes()
        except OSError as error:
            raise IntegrityError(f"could not write score chunk: {path}") from error
        chunks.append(
            ScoreChunk(
                name=name,
                first_user_index=first,
                user_count=len(selected_users),
                sha256=sha256_bytes(payload),
            )
        )

    user_hash = _ordered_ids_hash(users)
    candidate_hash = protocol.manifest.candidate_order_sha256
    artifact_manifest = ScoreArtifactManifest(
        run_id=run_id,
        model_id=model_id,
        num_users=len(users),
        num_candidates=len(candidates),
        user_order_sha256=user_hash,
        candidate_order_sha256=candidate_hash,
        score_dtype="float32",
        score_shape=(len(users), len(candidates)),
        finite=True,
        chunks=tuple(chunk.name for chunk in chunks),
        protocol_manifest_sha256=_protocol_manifest_hash(protocol),
    )
    document = {
        "schema_version": "score-artifact/1.0",
        "manifest": artifact_manifest.to_mapping(),
        "chunks": [chunk.to_mapping() for chunk in chunks],
    }
    try:
        (root / "manifest.json").write_bytes(canonical_json_bytes(document) + b"\n")
    except OSError as error:
        raise IntegrityError(f"could not write score manifest: {root / 'manifest.json'}") from error
    return MaterializedScores(root=root, manifest=artifact_manifest, chunks=tuple(chunks))


def load_score_matrix(materialized: MaterializedScores) -> np.ndarray:
    """Reload and verify all chunks in their recorded order."""

    matrices: list[np.ndarray] = []
    expected_first = 0
    for chunk in materialized.chunks:
        if chunk.first_user_index != expected_first:
            raise IntegrityError("score chunks have a gap or overlap in user order")
        path = materialized.root / chunk.name
        try:
            payload = path.read_bytes()
            matrix = np.load(path, allow_pickle=False)
        except (OSError, ValueError) as error:
            raise IntegrityError(f"could not read score chunk: {path}") from error
        if sha256_bytes(payload) != chunk.sha256:
            raise IntegrityError(f"score chunk hash mismatch: {path}")
        if matrix.dtype != np.float32 or matrix.ndim != 2 or not np.isfinite(matrix).all():
            raise ScoreError(f"score chunk is invalid: {path}")
        if matrix.shape[0] != chunk.user_count:
            raise ScoreError(f"score chunk user dimension mismatch: {path}")
        if matrix.shape[1] != materialized.manifest.num_candidates:
            raise ScoreError(f"score chunk candidate dimension mismatch: {path}")
        matrices.append(matrix)
        expected_first += chunk.user_count
    if not matrices:
        raise IntegrityError("score artifact has no chunks")
    combined = np.concatenate(matrices, axis=0)
    if combined.shape != materialized.manifest.score_shape:
        raise ScoreError("combined score matrix shape does not match manifest")
    return combined


def load_materialized_scores(root: Path) -> MaterializedScores:
    """Load the wrapper manifest and validate its chunk declarations."""

    manifest_path = root / "manifest.json"
    try:
        document = loads_strict_json(manifest_path.read_bytes(), source=str(manifest_path))
    except (OSError, ValueError) as error:
        raise IntegrityError(f"could not read score manifest: {manifest_path}") from error
    if not isinstance(document, dict) or set(document) != {"schema_version", "manifest", "chunks"}:
        raise IntegrityError("score manifest wrapper has invalid fields")
    if document["schema_version"] != "score-artifact/1.0":
        raise IntegrityError("unsupported score artifact schema")
    if not isinstance(document["manifest"], dict) or not isinstance(document["chunks"], list):
        raise IntegrityError("score manifest wrapper has invalid values")
    artifact_manifest = ScoreArtifactManifest.from_mapping(document["manifest"])
    chunks: list[ScoreChunk] = []
    seen_names: set[str] = set()
    for value in document["chunks"]:
        if not isinstance(value, dict) or set(value) != {
            "name",
            "first_user_index",
            "user_count",
            "sha256",
        }:
            raise IntegrityError("score chunk manifest has invalid fields")
        name = value["name"]
        first = value["first_user_index"]
        count = value["user_count"]
        digest = value["sha256"]
        if (
            not isinstance(name, str)
            or not name
            or Path(name).name != name
            or not isinstance(first, int)
            or not isinstance(count, int)
            or first < 0
            or count < 1
            or not isinstance(digest, str)
            or not _is_sha256(digest)
        ):
            raise IntegrityError("score chunk manifest value is invalid")
        if name in seen_names:
            raise IntegrityError("score chunk manifest contains duplicate names")
        seen_names.add(name)
        chunks.append(ScoreChunk(name, first, count, digest))
    if tuple(chunk.name for chunk in chunks) != artifact_manifest.chunks:
        raise IntegrityError("score chunk order does not match artifact manifest")
    expected_first = 0
    for chunk in chunks:
        if chunk.first_user_index != expected_first:
            raise IntegrityError("score chunks are not contiguous in user order")
        expected_first += chunk.user_count
    if expected_first != artifact_manifest.num_users:
        raise IntegrityError("score chunk user counts do not match manifest")
    try:
        actual_entries = {path.name for path in root.iterdir()}
    except OSError as error:
        raise IntegrityError(f"cannot inspect score artifact root: {root}") from error
    if actual_entries != {"manifest.json", *seen_names}:
        raise IntegrityError("score artifact contains an unexpected or missing file")
    return MaterializedScores(root=root, manifest=artifact_manifest, chunks=tuple(chunks))


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _protocol_manifest_hash(protocol: PreparedProtocol) -> str:
    from ai_service_v2.hashing import canonical_json_sha256

    return canonical_json_sha256(protocol.manifest.to_mapping())


__all__ = [
    "MaterializedScores",
    "MatrixScoreProvider",
    "ScoreChunk",
    "load_materialized_scores",
    "load_score_matrix",
    "materialize_scores",
]
