from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from ai_service.contracts import RunStatus, SplitName, TrainingVariant
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError
from ai_service.evaluation.release import (
    _aggregate_gate,
    _load_finalist_run,
    _load_validation_release,
    _pair_finalists_by_seed,
    _validate_finalist_set,
    evaluate_three_seed,
)
from ai_service.training.run import RunLifecycle
from tests.support.v5_factories import make_metric_gate, make_settings, make_victory_matrix
from tests.unit.test_release_gate_contract import _make_fixture


def test_test_release_retry_recovers_after_seal_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    evaluate_three_seed(
        split=SplitName.VAL,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    original_transition = RunLifecycle.transition
    failed = False

    def fail_once(self: RunLifecycle, target: RunStatus, *, reason: str | None = None) -> None:
        nonlocal failed
        if target is RunStatus.SEALED and not failed:
            failed = True
            raise OSError("injected seal publication failure")
        original_transition(self, target, reason=reason)

    monkeypatch.setattr(RunLifecycle, "transition", fail_once)
    with pytest.raises(OSError, match="seal publication failure"):
        evaluate_three_seed(
            split=SplitName.TEST,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )
    monkeypatch.undo()

    recovered = evaluate_three_seed(
        split=SplitName.TEST,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )

    assert recovered.selected_run_id == "hybrid-s42"
    assert RunLifecycle.load(hybrids[0]).status is RunStatus.SEALED


def test_release_retry_rejects_divergent_existing_gate(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    evaluate_three_seed(
        split=SplitName.VAL,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    gate_path = (
        tmp_path / "releases" / settings.comparison_signature_sha256() / "validation-gate.json"
    )
    gate_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="existing release report"):
        evaluate_three_seed(
            split=SplitName.VAL,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("no-checkpoint", "no best checkpoint"),
        ("escape", "escapes its run directory"),
        ("pair", "pair IDs do not match"),
        ("lineage", "checkpoint lineage mismatch"),
        ("manifest", "manifest identity mismatch"),
    ],
)
def test_release_public_interface_rejects_finalist_corruption(
    tmp_path: Path, mutation: str, message: str
) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    target = hybrids[0]
    state_path = target / "pipeline-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if mutation == "no-checkpoint":
        state["checkpoint_path"] = None
    elif mutation == "escape":
        state["checkpoint_path"] = str(tmp_path / "outside" / "checkpoints" / "best.pt")
    elif mutation == "pair":
        state["paired_run_id"] = "wrong-deep"
    elif mutation == "lineage":
        run_manifest = target / "run-manifest.json"
        document = json.loads(run_manifest.read_text(encoding="utf-8"))
        document["lineage"]["rules"] = "f" * 64
        run_manifest.write_text(json.dumps(document), encoding="utf-8")
    else:
        checkpoint_manifest = target / "checkpoints" / "best.pt.manifest.json"
        document = json.loads(checkpoint_manifest.read_text(encoding="utf-8"))
        document["run_id"] = "wrong-run"
        checkpoint_manifest.write_text(json.dumps(document), encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises((ArtifactIntegrityError, DataIntegrityError), match=message):
        evaluate_three_seed(
            split=SplitName.VAL,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )


def test_release_public_interface_rejects_aggregate_gate_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    failed = tuple(
        make_metric_gate(name, passed=name != "aggregate_gauc_domination")
        for name in (
            "aggregate_gauc_domination",
            "aggregate_hr_domination",
            "aggregate_ndcg_domination",
            "aggregate_gauc_vs_deep",
            "aggregate_hr_vs_deep",
            "aggregate_ndcg_vs_deep",
        )
    )
    monkeypatch.setattr(
        "ai_service.evaluation.release._build_aggregate_gates", lambda *_args, **_kwargs: failed
    )

    with pytest.raises(DataIntegrityError, match="aggregate three-seed release gate failed"):
        evaluate_three_seed(
            split=SplitName.VAL,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )
    assert not (
        tmp_path / "releases" / settings.comparison_signature_sha256() / "validation-gate.json"
    ).exists()


def test_release_test_gate_locks_validation_selected_winner(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    validation = evaluate_three_seed(
        split=SplitName.VAL,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    gate_path = (
        tmp_path / "releases" / settings.comparison_signature_sha256() / "validation-gate.json"
    )
    document = json.loads(gate_path.read_text(encoding="utf-8"))
    document["selected_run_id"] = "hybrid-s2027"
    document["selected_seed"] = 2027
    without_sha = {key: value for key, value in document.items() if key != "artifact_sha256"}
    document["artifact_sha256"] = hashlib.sha256(
        json.dumps(without_sha, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    gate_path.write_text(json.dumps(document), encoding="utf-8")

    assert validation.selected_run_id == "hybrid-s42"
    with pytest.raises(ArtifactIntegrityError, match="selected run differs"):
        evaluate_three_seed(
            split=SplitName.TEST,
            hybrid_run_dirs=hybrids,
            deep_run_dirs=deeps,
            settings=settings,
        )


def test_release_finalist_load_wraps_state_and_manifest_corruption(tmp_path: Path) -> None:
    hybrids, _ = _make_fixture(tmp_path)
    state_path = hybrids[0] / "pipeline-state.json"
    state_path.write_text("{", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="pipeline state cannot be read"):
        _load_finalist_run(hybrids[0], TrainingVariant.HYBRID)

    hybrids, _ = _make_fixture(tmp_path / "manifest")
    manifest_path = hybrids[0] / "checkpoints" / "best.pt.manifest.json"
    manifest_path.write_text("{", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="checkpoint manifest cannot be read"):
        _load_finalist_run(hybrids[0], TrainingVariant.HYBRID)


def test_release_pair_and_validation_helpers_fail_closed(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    h_records = tuple(_load_finalist_run(path, TrainingVariant.HYBRID) for path in hybrids)
    d_records = tuple(_load_finalist_run(path, TrainingVariant.DEEP_ONLY) for path in deeps)
    with pytest.raises(DataIntegrityError, match="seeds must be exactly"):
        _pair_finalists_by_seed(h_records[:2], d_records, split=SplitName.VAL)
    with pytest.raises(ArtifactIntegrityError, match="lineage differs"):
        _pair_finalists_by_seed(
            (
                replace(h_records[0], lineage={**h_records[0].lineage, "rules": "f" * 64}),
                *h_records[1:],
            ),
            d_records,
            split=SplitName.VAL,
        )
    with pytest.raises(DataIntegrityError, match="exactly three"):
        _validate_finalist_set(h_records[:0], split=SplitName.VAL, comparison_signature="x" * 64)

    candidate = np.ones(4, dtype=np.float64)
    baseline = np.zeros(4, dtype=np.float64)
    gate = _aggregate_gate(
        "aggregate_gauc_domination",
        candidate,
        baseline,
        2.0,
        32,
        baseline_name="deep_only",
    )
    assert gate.passed is False
    assert gate.failure_reason is not None

    gate_path = tmp_path / "validation-gate.json"
    gate_path.write_text("{", encoding="utf-8")
    with pytest.raises((ArtifactIntegrityError, ValueError)):
        _load_validation_release(
            gate_path,
            expected_signature=settings.comparison_signature_sha256(),
            expected_hybrid_run_ids=tuple(path.name for path in hybrids),
            expected_deep_run_ids=tuple(path.name for path in deeps),
        )


def test_release_pair_rejects_cross_variant_signature_and_user_ids(tmp_path: Path) -> None:
    hybrids, deeps = _make_fixture(tmp_path)
    h_records = tuple(_load_finalist_run(path, TrainingVariant.HYBRID) for path in hybrids)
    d_records = tuple(_load_finalist_run(path, TrainingVariant.DEEP_ONLY) for path in deeps)
    mismatched_settings = make_settings(
        tmp_path / "other", variant=TrainingVariant.DEEP_ONLY, seed=42
    )
    mismatched_settings.eval.aggregate_hr_min_delta = 0.5
    with pytest.raises(ArtifactIntegrityError, match="comparison signature"):
        _pair_finalists_by_seed(
            h_records,
            tuple(
                replace(
                    record,
                    settings=mismatched_settings,
                )
                for record in d_records
            ),
            split=SplitName.VAL,
        )


def test_release_finalist_identity_branches(tmp_path: Path) -> None:
    hybrids, _ = _make_fixture(tmp_path)
    target = hybrids[0]
    manifest_path = target / "run-manifest.json"
    original = json.loads(manifest_path.read_text(encoding="utf-8"))
    failed = {**original, "status": "failed", "status_reason": "fixture failure"}
    manifest_path.write_text(json.dumps(failed), encoding="utf-8")
    with pytest.raises(DataIntegrityError, match="not evaluable"):
        _load_finalist_run(target, TrainingVariant.HYBRID)
    manifest_path.write_text(json.dumps(original), encoding="utf-8")

    state_path = target / "pipeline-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["run_id"] = "wrong-run"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="identity mismatch"):
        _load_finalist_run(target, TrainingVariant.HYBRID)
    state["run_id"] = target.name
    state_path.write_text(json.dumps(state), encoding="utf-8")

    state["checkpoint_path"] = str(target / "wrong.pt")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match=r"checkpoints/best\.pt"):
        _load_finalist_run(target, TrainingVariant.HYBRID)


def test_release_pair_and_validation_document_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    h_records = tuple(_load_finalist_run(path, TrainingVariant.HYBRID) for path in hybrids)
    d_records = tuple(_load_finalist_run(path, TrainingVariant.DEEP_ONLY) for path in deeps)
    pairs = _pair_finalists_by_seed(h_records, d_records, split=SplitName.VAL)

    with pytest.raises(DataIntegrityError, match="seeds must be exactly"):
        _pair_finalists_by_seed(
            (replace(h_records[0], seed=1), *h_records[1:]), d_records, split=SplitName.VAL
        )
    with pytest.raises(ArtifactIntegrityError, match="evaluation split"):
        _validate_finalist_set(
            (
                replace(
                    pairs[0],
                    evaluation=replace(
                        pairs[0].evaluation,
                        victory_matrix=make_victory_matrix(
                            split=SplitName.TEST,
                            seed=42,
                            comparison_signature=settings.comparison_signature_sha256(),
                        ),
                    ),
                ),
                *pairs[1:],
            ),
            split=SplitName.VAL,
            comparison_signature=settings.comparison_signature_sha256(),
        )
    mismatched_manifest = pairs[0].evaluation.manifest.model_copy(
        update={"comparison_signature_sha256": "f" * 64}
    )
    with pytest.raises(ArtifactIntegrityError, match="evaluation signature"):
        _validate_finalist_set(
            (
                replace(
                    pairs[0],
                    evaluation=replace(pairs[0].evaluation, manifest=mismatched_manifest),
                ),
                *pairs[1:],
            ),
            split=SplitName.VAL,
            comparison_signature=settings.comparison_signature_sha256(),
        )
    original_loader = __import__(
        "ai_service.evaluation.release", fromlist=["load_evaluation_artifacts"]
    ).load_evaluation_artifacts
    calls = 0

    def mismatched_loader(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        result = original_loader(*args, **kwargs)
        if calls == 2:
            metrics = dict(result.metrics)
            metrics["user_ids"] = np.asarray([1, 2, 3, 99], dtype=np.int64)
            return replace(result, metrics=metrics)
        return result

    monkeypatch.setattr(
        "ai_service.evaluation.release.load_evaluation_artifacts", mismatched_loader
    )
    with pytest.raises(DataIntegrityError, match="user IDs differ"):
        _pair_finalists_by_seed(
            h_records,
            d_records,
            split=SplitName.VAL,
        )


@pytest.mark.parametrize("mutation", ["hash", "split", "signature", "sets"])
def test_release_validation_gate_guards(tmp_path: Path, mutation: str) -> None:
    settings = make_settings(tmp_path)
    hybrids, deeps = _make_fixture(tmp_path)
    evaluate_three_seed(
        split=SplitName.VAL,
        hybrid_run_dirs=hybrids,
        deep_run_dirs=deeps,
        settings=settings,
    )
    gate_path = (
        tmp_path / "releases" / settings.comparison_signature_sha256() / "validation-gate.json"
    )
    document = json.loads(gate_path.read_text(encoding="utf-8"))
    if mutation == "hash":
        document["artifact_sha256"] = "0" * 64
    elif mutation == "split":
        document["split"] = "test"
    elif mutation == "signature":
        document["comparison_signature_sha256"] = "f" * 64
    else:
        document["deep_run_ids"] = ["wrong-a", "wrong-b", "wrong-c"]
    if mutation != "hash":
        without_sha = {key: value for key, value in document.items() if key != "artifact_sha256"}
        document["artifact_sha256"] = hashlib.sha256(
            json.dumps(without_sha, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    gate_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError):
        _load_validation_release(
            gate_path,
            expected_signature=settings.comparison_signature_sha256(),
            expected_hybrid_run_ids=tuple(path.name for path in hybrids),
            expected_deep_run_ids=tuple(path.name for path in deeps),
        )
