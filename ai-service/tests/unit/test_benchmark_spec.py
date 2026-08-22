from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_service.errors import ArtifactIntegrityError

EXPECTED_V5_SPEC_SHA256 = "1ace202aaa8f54204ead66ceabe809b3c51795e097dd71c505f07b8367c80bd2"
SPEC_PATH = (
    Path(__file__).parents[3]
    / "backend"
    / "docs"
    / "chatbot"
    / "seed-product"
    / "benchmark-spec-v5.json"
)


def test_load_benchmark_spec_matches_node_v5_golden_hash() -> None:
    from ai_service.data.benchmark_spec import load_benchmark_spec

    spec = load_benchmark_spec(SPEC_PATH, expected_sha256=EXPECTED_V5_SPEC_SHA256)

    assert spec.sha256 == EXPECTED_V5_SPEC_SHA256
    assert spec.canonical_bytes.startswith(b'{"conversion_affinity_weight":0.1,')
    assert spec.validation_users_per_trap == 100
    assert spec.test_users_per_trap == 100
    assert tuple(trap.trap_id for trap in spec.semantic_traps) == tuple(range(1, 11))


def test_load_benchmark_spec_normalizes_integral_float_like_json_stringify(tmp_path: Path) -> None:
    from ai_service.data.benchmark_spec import load_benchmark_spec

    document = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    document["minimum_semantic_lift"] = 10.0
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert (
        load_benchmark_spec(path, expected_sha256=EXPECTED_V5_SPEC_SHA256).sha256
        == EXPECTED_V5_SPEC_SHA256
    )


def test_load_benchmark_spec_rejects_hash_and_non_finite_values(tmp_path: Path) -> None:
    from ai_service.data.benchmark_spec import load_benchmark_spec

    document = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    document["minimum_semantic_lift"] = float("inf")
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(document, allow_nan=True), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="finite"):
        load_benchmark_spec(path, expected_sha256=EXPECTED_V5_SPEC_SHA256)

    path.write_text(SPEC_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="checksum"):
        load_benchmark_spec(path, expected_sha256="0" * 64)
