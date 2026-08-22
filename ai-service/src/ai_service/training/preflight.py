"""Shared, fail-closed preparation seam for R3 readiness and training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch
from pydantic import BaseModel

from ai_service.config import Settings
from ai_service.contracts import (
    ArtifactLineageV5,
    DataProbeReport,
    DataQualityReport,
    RuleManifest,
)
from ai_service.data.dataset import (
    PurchaseBatchIterator,
    PurchaseTrainingIndex,
    build_purchase_training_index,
)
from ai_service.data.features import EmbeddingArtifact, load_embedding_artifact
from ai_service.data.quality import DataQualityAuditor
from ai_service.data.rule_readiness import TrainingRuleReadiness, assess_training_rule_readiness
from ai_service.data.rules import RuleArtifact, load_rule_artifact
from ai_service.data.sampling import MixedNegativeSampler
from ai_service.data.snapshot import Snapshot, load_snapshot
from ai_service.data.sources import check_production_connections
from ai_service.errors import ArtifactIntegrityError
from ai_service.evaluation.probes import run_data_probes
from ai_service.lineage import require_v5_lineage, resolve_artifact_lineage


def _find_feature(root: Path, snapshot_sha256: str) -> Path:
    matches = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if document.get("snapshot_sha256") == snapshot_sha256:
            matches.append(manifest_path.parent)
    if len(matches) != 1:
        raise ArtifactIntegrityError(
            f"R3 preflight expected one feature artifact, found {len(matches)}"
        )
    return matches[0]


def _find_rule(settings: Settings, snapshot_sha256: str) -> Path:
    root = settings.data.artifact_root.resolve() / "rules"
    matches: list[Path] = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        try:
            manifest = RuleManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (
            manifest.snapshot_sha256 == snapshot_sha256
            and manifest.has_full_statistics
            and manifest.feature_schema_version == settings.data.rule_feature_schema_version
            and manifest.min_count == settings.data.min_rule_count
            and abs(manifest.min_lift - settings.data.min_rule_lift) <= 1e-12
        ):
            matches.append(manifest_path.parent)
    if len(matches) != 1:
        raise ArtifactIntegrityError(
            f"R3 preflight expected one rule artifact, found {len(matches)}"
        )
    return matches[0]


@dataclass(frozen=True)
class PreparedTrainingInputs:
    snapshot: Snapshot
    embedding: EmbeddingArtifact
    rules: RuleArtifact
    lineage: ArtifactLineageV5
    purchase_index: PurchaseTrainingIndex
    sampler: MixedNegativeSampler
    train_loader: PurchaseBatchIterator
    rule_readiness: TrainingRuleReadiness


class R3PreflightReceipt(BaseModel):
    schema_version: Literal["5.2.0"] = "5.2.0"
    passed: Literal[True] = True
    snapshot_id: str
    lineage: ArtifactLineageV5
    audit: DataQualityReport
    probes: DataProbeReport
    rule_readiness: TrainingRuleReadiness


def _load_base_inputs(
    settings: Settings,
) -> tuple[Snapshot, EmbeddingArtifact, RuleArtifact, ArtifactLineageV5]:
    """Load and validate immutable parents without creating a run directory."""
    snapshot = load_snapshot(settings.data.snapshot_id, settings)
    embedding_path = _find_feature(
        settings.data.artifact_root.resolve() / "features",
        snapshot_sha256=snapshot.manifest.content_sha256,
    )
    embedding = load_embedding_artifact(embedding_path)
    rule_path = _find_rule(settings, snapshot.manifest.content_sha256)
    rules = load_rule_artifact(rule_path, snapshot.manifest.num_items)
    rules.require_training_capability(settings)
    lineage = resolve_artifact_lineage(
        snapshot.manifest,
        embedding.manifest,
        rules.manifest,
        require_v5=True,
    )
    lineage = require_v5_lineage(lineage)
    return snapshot, embedding, rules, lineage


def prepare_training_inputs(settings: Settings) -> PreparedTrainingInputs:
    """Prepare the exact inputs shared by preflight and the training seam."""
    snapshot, embedding, rules, lineage = _load_base_inputs(settings)
    purchase_index = build_purchase_training_index(
        snapshot,
        max_history_items=settings.train.max_history_items,
    )
    sampler = MixedNegativeSampler(
        purchase_index,
        snapshot,
        embedding.vectors,
        ratio=settings.train.explicit_negative_ratio,
        seed=settings.train.seed,
        rule_store=rules.store,
        rule_hard_negative_count=settings.train.rule_hard_negative_count,
    )
    loader = PurchaseBatchIterator(
        purchase_index,
        sampler,
        rules.store,
        batch_size=settings.train.batch_size,
        seed=settings.train.seed,
    )
    readiness = assess_training_rule_readiness(
        loader,
        minimum_rows_with_any_rule=settings.data.minimum_training_rows_with_any_rule,
        minimum_training_target_rule_rate=settings.data.minimum_training_target_rule_rate,
    )
    if not readiness.passed:
        raise ArtifactIntegrityError(
            "R3 preflight rule readiness failed: " + "; ".join(readiness.failure_reasons)
        )
    return PreparedTrainingInputs(
        snapshot=snapshot,
        embedding=embedding,
        rules=rules,
        lineage=lineage,
        purchase_index=purchase_index,
        sampler=sampler,
        train_loader=loader,
        rule_readiness=readiness,
    )


def run_r3_preflight(
    settings: Settings,
    *,
    device: torch.device,
    prepared_inputs: PreparedTrainingInputs | None = None,
) -> R3PreflightReceipt:
    """Run all read-only R3 gates against one prepared training input set."""
    if settings.serving.environment.lower() == "production":
        check_production_connections(settings)
    prepared = prepared_inputs or prepare_training_inputs(settings)
    audit = DataQualityAuditor().audit(prepared.snapshot)
    if not audit.training_suitability_passed:
        raise ArtifactIntegrityError(
            "R3 preflight data audit failed: " + "; ".join(audit.gate_failures)
        )
    probes = run_data_probes(
        settings,
        prepared.snapshot,
        prepared.embedding.vectors,
        prepared.rules,
    )
    probe_model = probes
    if not probe_model.passed:
        raise ArtifactIntegrityError("R3 preflight probe parity/sanity failed")
    # Device is deliberately consumed so the CLI cannot silently omit it; all
    # R3 data checks themselves remain CPU-safe.
    _ = device
    return R3PreflightReceipt(
        snapshot_id=prepared.snapshot.manifest.artifact_id,
        lineage=prepared.lineage,
        audit=audit,
        probes=probe_model,
        rule_readiness=prepared.rule_readiness,
    )


__all__ = [
    "PreparedTrainingInputs",
    "R3PreflightReceipt",
    "prepare_training_inputs",
    "run_r3_preflight",
]
