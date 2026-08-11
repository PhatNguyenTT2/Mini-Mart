from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ai_service.artifact_io import (
    canonical_json_sha256,
    immutable_write_json,
    require_child_path,
)
from ai_service.contracts import (
    ColdParityReport,
    EvaluationReport,
    ModelVariant,
    SplitName,
)
from ai_service.data.rules import RuleStore
from ai_service.errors import ArtifactIntegrityError
from ai_service.evaluation.baselines import BaselineComparisonReport
from ai_service.evaluation.gates import SingleSeedGateInputs, evaluate_single_seed
from ai_service.evaluation.report import (
    load_evaluation_artifacts,
    publish_evaluation_artifacts,
)
from ai_service.evaluation.semantic_traps import SemanticTrapReport
from ai_service.export.bundle import BundlePublisher, verify_bundle
from tests.support.v5_factories import make_settings, make_victory_matrix


def _typed_metrics(users: int = 3) -> dict[str, np.ndarray]:
    one_d = np.full(users, 0.5, dtype=np.float64)
    values: dict[str, np.ndarray] = {"user_ids": np.arange(1, users + 1, dtype=np.int64)}
    for name in (
        "hybrid_hr",
        "hybrid_ndcg",
        "hybrid_gauc",
        "deep_hr",
        "deep_ndcg",
        "deep_gauc",
        "persona_hr",
        "persona_ndcg",
        "persona_gauc",
        "apriori_hr",
        "apriori_ndcg",
        "apriori_gauc",
        "sbert_hr",
        "sbert_ndcg",
        "sbert_gauc",
        "item_cf_hr",
        "item_cf_ndcg",
        "item_cf_gauc",
        "noisy_hybrid_hr",
        "noisy_hybrid_ndcg",
        "noisy_hybrid_gauc",
    ):
        values[name] = one_d.copy()
    values["random_hr"] = np.full((10, users), 0.5)
    values["random_ndcg"] = np.full((10, users), 0.5)
    values["random_gauc"] = np.full((10, users), 0.5)
    return values


def _evaluation(variant: ModelVariant, hr: float, ndcg: float, gauc: float) -> object:
    values = np.full(32, gauc, dtype=np.float64)
    return SimpleNamespace(
        report=EvaluationReport(
            run_id="fixture",
            split=SplitName.VAL,
            variant=variant,
            num_total_users=32,
            num_eligible_users=32,
            num_users_without_novel_purchase=0,
            num_catalog_items=64,
            hr_at_k=hr,
            ndcg_at_k=ndcg,
            gauc=gauc,
            k=10,
        ),
        user_ids=np.arange(32),
        per_user_hr=np.full(32, hr),
        per_user_ndcg=np.full(32, ndcg),
        per_user_gauc=values,
        top_k_by_user={},
    )


def test_single_seed_gate_emits_complete_matrix() -> None:
    hybrid = _evaluation(ModelVariant.HYBRID, 0.90, 0.80, 0.80)
    random = tuple(_evaluation(ModelVariant.RANDOM, 0.01, 0.01, 0.50) for _ in range(10))
    comparison = BaselineComparisonReport(
        persona_only=_evaluation(ModelVariant.PERSONA_ONLY, 0.25, 0.30, 0.55),
        apriori_only=_evaluation(ModelVariant.ITEM_CF, 0.30, 0.40, 0.60),
        sbert_centroid=_evaluation(ModelVariant.SBERT_CENTROID, 0.40, 0.45, 0.65),
        item_cf=_evaluation(ModelVariant.ITEM_CF, 0.50, 0.35, 0.70),
        deep_only=_evaluation(ModelVariant.DEEP_ONLY, 0.60, 0.50, 0.72),
        hybrid=hybrid,
        noisy_hybrid=_evaluation(ModelVariant.NOISY_HYBRID, 0.70, 0.55, 0.75),
        random_seed_results=random,
    )
    cold = ColdParityReport(
        max_abs_wide_logit=0.0,
        max_abs_hybrid_minus_deep=0.0,
        cold_only_order_equality=True,
        deep_cold_hr_at_k=0.1,
        deep_cold_ndcg_at_k=0.1,
        hybrid_cold_hr_at_k=0.1,
        hybrid_cold_ndcg_at_k=0.1,
        passed=True,
    )
    traps = SemanticTrapReport(passed=10, total=10, all_passed=True, results=())
    matrix = evaluate_single_seed(
        SingleSeedGateInputs(
            comparison=comparison,
            cold_parity=cold,
            semantic_traps=traps,
            seed=42,
            split=SplitName.VAL,
            comparison_signature="a" * 64,
        ),
        bootstrap_samples=32,
    )
    assert matrix.all_passed
    assert len(matrix.gates) == 7
    assert (
        matrix.sha256
        == hashlib.sha256(
            json.dumps(
                {k: v for k, v in matrix.model_dump(mode="json").items() if k != "sha256"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )


@pytest.mark.parametrize(
    ("competitor", "metric_index", "gate_name"),
    [
        ("item_cf", 2, "gauc_domination"),
        ("persona_only", 0, "hr_domination"),
        ("sbert_centroid", 1, "ndcg_domination"),
    ],
)
def test_single_seed_gate_rejects_each_metric_strongest_competitor(
    competitor: str,
    metric_index: int,
    gate_name: str,
) -> None:
    baseline_values = {
        name: [0.20, 0.20, 0.60]
        for name in (
            "persona_only",
            "apriori_only",
            "sbert_centroid",
            "item_cf",
            "deep_only",
            "noisy_hybrid",
        )
    }
    baseline_values[competitor][metric_index] = 0.90
    variants = {
        "persona_only": ModelVariant.PERSONA_ONLY,
        "apriori_only": ModelVariant.WIDE_ONLY,
        "sbert_centroid": ModelVariant.SBERT_CENTROID,
        "item_cf": ModelVariant.ITEM_CF,
        "deep_only": ModelVariant.DEEP_ONLY,
        "noisy_hybrid": ModelVariant.NOISY_HYBRID,
    }
    comparison = BaselineComparisonReport(
        hybrid=_evaluation(ModelVariant.HYBRID, 0.80, 0.70, 0.76),
        random_seed_results=tuple(
            _evaluation(ModelVariant.RANDOM, 0.01, 0.01, 0.50) for _ in range(10)
        ),
        **{name: _evaluation(variants[name], *values) for name, values in baseline_values.items()},
    )
    matrix = evaluate_single_seed(
        SingleSeedGateInputs(
            comparison=comparison,
            cold_parity=ColdParityReport(
                max_abs_wide_logit=0.0,
                max_abs_hybrid_minus_deep=0.0,
                cold_only_order_equality=True,
                deep_cold_hr_at_k=0.1,
                deep_cold_ndcg_at_k=0.1,
                hybrid_cold_hr_at_k=0.1,
                hybrid_cold_ndcg_at_k=0.1,
                passed=True,
            ),
            semantic_traps=SemanticTrapReport(passed=10, total=10, all_passed=True, results=()),
            seed=42,
            split=SplitName.VAL,
            comparison_signature="b" * 64,
        ),
        bootstrap_samples=32,
    )
    assert {gate.name: gate for gate in matrix.gates}[gate_name].passed is False
    assert matrix.all_passed is False


def test_evaluation_artifact_set_is_atomic_and_hash_checked(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    metrics = {
        "user_ids": np.arange(1, 4, dtype=np.int64),
        **{
            name: np.full(3, 0.8, dtype=np.float64)
            for name in (
                "hybrid_hr",
                "hybrid_ndcg",
                "hybrid_gauc",
                "deep_hr",
                "deep_ndcg",
                "deep_gauc",
                "persona_hr",
                "persona_ndcg",
                "persona_gauc",
                "apriori_hr",
                "apriori_ndcg",
                "apriori_gauc",
                "sbert_hr",
                "sbert_ndcg",
                "sbert_gauc",
                "item_cf_hr",
                "item_cf_ndcg",
                "item_cf_gauc",
                "noisy_hybrid_hr",
                "noisy_hybrid_ndcg",
                "noisy_hybrid_gauc",
            )
        },
        "random_hr": np.full((10, 3), 0.5),
        "random_ndcg": np.full((10, 3), 0.5),
        "random_gauc": np.full((10, 3), 0.5),
    }
    artifact = publish_evaluation_artifacts(
        run_dir=tmp_path / "run",
        split=SplitName.VAL,
        hybrid_run_id="hybrid-42",
        deep_run_id="deep-42",
        hybrid_checkpoint_sha256="d" * 64,
        deep_checkpoint_sha256="e" * 64,
        lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        metrics=metrics,
        results={"passed": True},
        victory_matrix=matrix,
    )
    loaded = load_evaluation_artifacts(
        tmp_path / "run",
        expected_split=SplitName.VAL,
        expected_hybrid_run_id="hybrid-42",
        expected_deep_run_id="deep-42",
        expected_comparison_signature=settings.comparison_signature_sha256(),
        expected_lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
    )
    assert loaded.manifest == artifact.manifest
    with pytest.raises(ArtifactIntegrityError):
        publish_evaluation_artifacts(
            run_dir=tmp_path / "run",
            split=SplitName.VAL,
            hybrid_run_id="hybrid-42",
            deep_run_id="deep-42",
            hybrid_checkpoint_sha256="d" * 64,
            deep_checkpoint_sha256="e" * 64,
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            comparison_signature_sha256=settings.comparison_signature_sha256(),
            metrics=metrics,
            results={"passed": True},
            victory_matrix=matrix,
        )


def test_artifact_io_immutable_and_path_guard(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    immutable_write_json(path, {"value": 1})
    assert canonical_json_sha256({"value": 1})
    with pytest.raises(ArtifactIntegrityError):
        immutable_write_json(path, {"value": 2})
    with pytest.raises(ArtifactIntegrityError):
        require_child_path(tmp_path, tmp_path / ".." / "escape")
    assert RuleStore(4, []).features.shape == (0, 3)


def test_bundle_preflight_rejects_missing_matrix_and_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(ArtifactIntegrityError, match="bundle directory"):
        verify_bundle(tmp_path / "missing")
    with pytest.raises(ArtifactIntegrityError, match="non-placeholder"):
        BundlePublisher(SimpleNamespace()).publish(
            bundle_id="bundle",
            run_id="run",
            snapshot=SimpleNamespace(),
            rule_store=SimpleNamespace(),
            ranker_path=tmp_path / "ranker.onnx",
            item_vectors=np.zeros((1, 1), dtype=np.float32),
            user_profile_vectors=np.zeros((1, 1), dtype=np.float32),
            embedding_sha256="b" * 64,
            rule_sha256="c" * 64,
            checkpoint_sha256="a" * 64,
            comparison_signature_sha256="d" * 64,
            parity=SimpleNamespace(),
            victory_matrix_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "unsorted_users",
        "random_shape",
        "nan_metric",
    ],
)
def test_evaluation_metric_schema_rejects_malformed_payloads(tmp_path: Path, mutation: str) -> None:
    settings = make_settings(tmp_path)
    metrics = _typed_metrics()
    if mutation == "missing":
        del metrics["deep_hr"]
    elif mutation == "extra":
        metrics["unexpected"] = np.ones(3)
    elif mutation == "unsorted_users":
        metrics["user_ids"] = np.asarray([1, 1, 2], dtype=np.int64)
    elif mutation == "random_shape":
        metrics["random_hr"] = np.ones((9, 3))
    elif mutation == "nan_metric":
        metrics["hybrid_hr"][0] = np.nan
    matrix = make_victory_matrix(
        split=SplitName.VAL,
        seed=42,
        comparison_signature=settings.comparison_signature_sha256(),
    )
    with pytest.raises(ArtifactIntegrityError, match=r"metric|evaluation"):
        publish_evaluation_artifacts(
            run_dir=tmp_path / "run",
            split=SplitName.VAL,
            hybrid_run_id="hybrid-42",
            deep_run_id="deep-42",
            hybrid_checkpoint_sha256="d" * 64,
            deep_checkpoint_sha256="e" * 64,
            lineage={"snapshot": "a" * 64, "embedding": "b" * 64, "rules": "c" * 64},
            comparison_signature_sha256=settings.comparison_signature_sha256(),
            metrics=metrics,
            results={},
            victory_matrix=matrix,
        )
