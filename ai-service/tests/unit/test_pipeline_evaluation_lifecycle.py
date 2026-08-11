from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_service.config import Settings
from ai_service.contracts import SplitName, TrainingVariant
from ai_service.errors import ArtifactIntegrityError, ConfigurationError
from ai_service.training import pipeline


def _loaded(
    *,
    seed: int = 42,
    signature: str = "a" * 64,
    lineage: dict[str, str] | None = None,
) -> SimpleNamespace:
    lineage = lineage or {"snapshot": "b" * 64, "embedding": "c" * 64, "rules": "d" * 64}
    settings = SimpleNamespace(
        train=SimpleNamespace(seed=seed),
        comparison_signature_sha256=lambda: signature,
    )
    snapshot = SimpleNamespace(manifest=SimpleNamespace(content_sha256=lineage["snapshot"]))
    embedding = SimpleNamespace(manifest=SimpleNamespace(content_sha256=lineage["embedding"]))
    rules = SimpleNamespace(manifest=SimpleNamespace(content_sha256=lineage["rules"]))
    state = SimpleNamespace(checkpoint_path="checkpoint")
    lifecycle = SimpleNamespace(document={"git_commit": "0" * 40})
    return SimpleNamespace(
        settings=settings,
        snapshot=snapshot,
        embedding=embedding,
        rules=rules,
        state=state,
        lifecycle=lifecycle,
    )


def _base_settings(tmp_path: Path) -> Settings:
    settings = Settings()
    settings.data.artifact_root = tmp_path
    return settings


def test_pair_evaluation_rejects_seed_signature_and_lineage_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _base_settings(tmp_path)
    hybrid = _loaded()
    for deep, message in (
        (_loaded(seed=2027), "matching seeds"),
        (_loaded(signature="e" * 64), "matching comparison signatures"),
        (
            _loaded(lineage={"snapshot": "f" * 64, "embedding": "c" * 64, "rules": "d" * 64}),
            "matching artifact lineage",
        ),
    ):
        monkeypatch.setattr(
            pipeline,
            "_load_run_context",
            lambda *_args, _hybrid=hybrid, _deep=deep, **_kwargs: (
                _hybrid if _kwargs.get("expected_variant") is TrainingVariant.HYBRID else _deep
            ),
        )
        with pytest.raises(ArtifactIntegrityError, match=message):
            pipeline._evaluate_pair(
                base,
                hybrid_run_id="hybrid",
                deep_run_id="deep",
                split=SplitName.VAL,
                device=base.data.artifact_root,  # type: ignore[arg-type]
            )


def test_test_pair_requires_valid_aggregate_validation_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _base_settings(tmp_path)
    hybrid = _loaded()
    deep = _loaded()
    # The pair context is enough to reach the TEST precondition before model
    # evaluation; no synthetic model or full catalog is needed here.
    monkeypatch.setattr(
        pipeline,
        "_load_run_context",
        lambda *_args, **kwargs: (
            hybrid if kwargs.get("expected_variant") is TrainingVariant.HYBRID else deep
        ),
    )
    with pytest.raises(ArtifactIntegrityError, match="aggregate validation gate"):
        pipeline._evaluate_pair(
            base,
            hybrid_run_id="hybrid",
            deep_run_id="deep",
            split=SplitName.TEST,
            device=SimpleNamespace(type="cpu"),  # type: ignore[arg-type]
        )


def test_pair_cli_rejects_missing_ids_before_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings()
    monkeypatch.setattr(pipeline, "_configure", lambda _args: settings)
    monkeypatch.setattr(pipeline, "_seed_everything", lambda _seed: None)
    with pytest.raises(ConfigurationError, match=r"requires .*hybrid-run-id"):
        pipeline.execute_command(
            Namespace(
                command="evaluate",
                split="val",
                hybrid_run_id=None,
                deep_run_id=None,
                device="cpu",
            )
        )
