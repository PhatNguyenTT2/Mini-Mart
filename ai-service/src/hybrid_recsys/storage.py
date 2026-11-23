"""Bounded, write-once file storage for score artifacts and manifests."""

from __future__ import annotations

import io
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from hybrid_recsys.errors import IntegrityError
from hybrid_recsys.hashing import canonical_json_bytes

MIB = 1024 * 1024
SCORE_BOUND_BYTES = 128 * MIB
DOCUMENT_BOUND_BYTES = 8 * MIB
NPY_HEADER_BOUND_BYTES = 256


def numpy_payload_bytes(array: np.ndarray[Any, Any]) -> bytes:
    """Serialize one score chunk in memory and enforce the size cap before touching disk."""
    stream = io.BytesIO()
    np.save(stream, array, allow_pickle=False)
    data = stream.getvalue()
    if len(data) > SCORE_BOUND_BYTES:
        raise IntegrityError("score chunk exceeds the size cap")
    return data


def score_output_bound_bytes(*, user_count: int, candidate_count: int, chunk_size: int) -> int:
    """Upper bound of all float32 score chunks plus one manifest; reject oversized outputs early."""
    if any(
        type(value) is not int or value < 1 for value in (user_count, candidate_count, chunk_size)
    ):
        raise IntegrityError("score output dimensions must be positive integers")
    chunks = (user_count + chunk_size - 1) // chunk_size
    bound = user_count * candidate_count * 4 + chunks * NPY_HEADER_BOUND_BYTES
    bound += DOCUMENT_BOUND_BYTES
    if bound > SCORE_BOUND_BYTES:
        raise IntegrityError("score output exceeds the aggregate size cap")
    return bound


def validate_payload_destination(path: Path) -> None:
    """Reject destinations that already exist or resolve through a symlink."""
    absolute = path.absolute()
    if absolute.exists() and not absolute.is_dir():
        raise IntegrityError(f"destination already exists: {path}")
    for parent in (absolute, *absolute.parents):
        if parent.is_symlink():
            raise IntegrityError(f"destination resolves through a symlink: {parent}")


def write_exclusive_payload(path: Path, data: bytes) -> None:
    """Create ``path`` exclusively, write ``data`` durably and verify it by reading back."""
    if len(data) > SCORE_BOUND_BYTES:
        raise IntegrityError("payload exceeds the size cap")
    validate_payload_destination(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        if stream.write(data) != len(data):
            raise IntegrityError("partial write")
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != data:
        raise IntegrityError("readback mismatch")


def write_exclusive_document(path: Path, document: Mapping[str, Any]) -> None:
    """Write canonical JSON (with a trailing newline) through ``write_exclusive_payload``."""
    data = canonical_json_bytes(document) + b"\n"
    if len(data) > DOCUMENT_BOUND_BYTES:
        raise IntegrityError("document exceeds the size cap")
    write_exclusive_payload(path, data)
