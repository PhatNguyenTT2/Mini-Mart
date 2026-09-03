"""Strict replay boundary for Hybrid Deep/Wide/component score artifacts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ai_service_v2.contracts import ModelDescriptor
from ai_service_v2.data.rules import load_rule_table
from ai_service_v2.errors import ContractError, IntegrityError
from ai_service_v2.evaluation.artifacts import (
    MaterializedScores,
    load_materialized_scores,
    load_score_matrix,
)
from ai_service_v2.hashing import canonical_json_sha256, load_strict_json, sha256_file
from ai_service_v2.models.registry import ModelRunSpec, descriptor_for_spec
from ai_service_v2.protocol import PreparedProtocol, protocol_manifest_sha256
from ai_service_v2.training import CheckpointManifest, load_run, load_run_command


@dataclass(frozen=True)
class HybridScoreComponents:
    """A verified component wrapper and its three score artifacts."""

    root: Path
    manifest: dict[str, Any]
    components: dict[str, MaterializedScores]


_FIELDS = {
    "schema_version",
    "run_id",
    "model_id",
    "protocol_manifest_sha256",
    "candidate_order_sha256",
    "model_spec",
    "model_spec_sha256",
    "descriptor",
    "descriptor_sha256",
    "model_artifact_sha256",
    "checkpoint_manifest_sha256",
    "checkpoint_sha256",
    "feature_content_sha256",
    "rule_artifact_sha256",
    "fusion_normalization",
    "wide_weight",
    "components",
}
_MODEL_ARTIFACT_FIELDS = {
    "schema_version",
    "model_kind",
    "model_id",
    "model_spec_sha256",
    "descriptor",
    "checkpoint_directory",
    "checkpoint_sha256",
    "rule_artifact_file",
    "rule_artifact_sha256",
    "feature_content_sha256",
    "fusion_normalization",
}
_COMPONENT_NAMES = ("deep", "wide", "hybrid")


def _sha(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise IntegrityError(f"Hybrid component field is not a SHA-256: {name}")
    return value


def _load_spec(run_root: Path, document: dict[str, Any]) -> ModelRunSpec:
    config = load_strict_json(run_root / "config.json")
    if document.get("model_spec") != config:
        raise IntegrityError("Hybrid component model spec does not match the run config")
    try:
        spec = ModelRunSpec.from_mapping(config)
    except ContractError as error:
        raise IntegrityError("Hybrid component run config is invalid") from error
    if spec.model_kind != "hybrid":
        raise IntegrityError("Hybrid component wrapper requires a Hybrid model spec")
    if _sha(document.get("model_spec_sha256"), "model_spec_sha256") != canonical_json_sha256(
        spec.to_mapping()
    ):
        raise IntegrityError("Hybrid component model spec hash does not match the run config")
    return spec


def _load_descriptor(
    document: dict[str, Any], spec: ModelRunSpec, model_artifact: dict[str, Any]
) -> ModelDescriptor:
    raw_descriptor = document.get("descriptor")
    if not isinstance(raw_descriptor, dict):
        raise IntegrityError("Hybrid component descriptor must be an object")
    try:
        descriptor = ModelDescriptor.from_mapping(raw_descriptor)
    except ContractError as error:
        raise IntegrityError("Hybrid component descriptor is invalid") from error
    if descriptor != descriptor_for_spec(spec):
        raise IntegrityError("Hybrid component descriptor cannot be replayed from the model spec")
    if model_artifact.get("descriptor") != descriptor.to_mapping():
        raise IntegrityError("Hybrid component descriptor does not match the model artifact")
    if _sha(document.get("descriptor_sha256"), "descriptor_sha256") != canonical_json_sha256(
        descriptor.to_mapping()
    ):
        raise IntegrityError("Hybrid component descriptor hash does not match its mapping")
    return descriptor


def _load_model_artifact(run_root: Path, document: dict[str, Any]) -> dict[str, Any]:
    path = run_root / "model_artifact.json"
    if _sha(document.get("model_artifact_sha256"), "model_artifact_sha256") != sha256_file(path):
        raise IntegrityError("Hybrid component model artifact hash does not match")
    artifact = load_strict_json(path)
    if (
        set(artifact) != _MODEL_ARTIFACT_FIELDS
        or artifact.get("schema_version") != "model-artifact/1.1"
    ):
        raise IntegrityError("Hybrid component model artifact fields do not match schema")
    return artifact


def _replay_checkpoint_and_rules(
    run_root: Path,
    document: dict[str, Any],
    model_artifact: dict[str, Any],
    descriptor: ModelDescriptor,
    spec: ModelRunSpec,
    *,
    run: Any,
) -> None:
    checkpoint_root = run_root / "checkpoint"
    checkpoint_manifest_path = checkpoint_root / "manifest.json"
    if _sha(
        document.get("checkpoint_manifest_sha256"), "checkpoint_manifest_sha256"
    ) != sha256_file(checkpoint_manifest_path):
        raise IntegrityError("Hybrid component checkpoint manifest hash does not match")
    checkpoint = CheckpointManifest.from_mapping(load_strict_json(checkpoint_manifest_path))
    try:
        checkpoint_files = {path.name for path in checkpoint_root.iterdir() if path.is_file()}
    except OSError as error:
        raise IntegrityError("cannot inspect Hybrid checkpoint root") from error
    if checkpoint_files != {"manifest.json", "checkpoint.npz"}:
        raise IntegrityError("Hybrid checkpoint contains an unexpected or missing file")
    checkpoint_sha256 = _sha(document.get("checkpoint_sha256"), "checkpoint_sha256")
    if (
        checkpoint_sha256 != checkpoint.checkpoint_sha256
        or checkpoint_sha256 != model_artifact.get("checkpoint_sha256")
        or checkpoint_sha256 != run.manifest.checkpoint_sha256
        or checkpoint_sha256 != sha256_file(checkpoint_root / "checkpoint.npz")
    ):
        raise IntegrityError("Hybrid component checkpoint payload binding does not match")
    if (
        checkpoint.run_id != run.manifest.run_id
        or checkpoint.model_id != run.manifest.model_id
        or checkpoint.seed != run.manifest.seed
        or checkpoint.checkpoint_rule != run.manifest.checkpoint_rule
        or checkpoint.descriptor != descriptor.to_mapping()
    ):
        raise IntegrityError("Hybrid checkpoint identity does not match the run")

    feature_sha256 = _sha(document.get("feature_content_sha256"), "feature_content_sha256")
    if feature_sha256 != checkpoint.feature_content_sha256 or feature_sha256 != model_artifact.get(
        "feature_content_sha256"
    ):
        raise IntegrityError("Hybrid component feature binding does not match")

    rule_path = run_root / "rule_artifact.json"
    rule_sha256 = _sha(document.get("rule_artifact_sha256"), "rule_artifact_sha256")
    if (
        model_artifact.get("rule_artifact_file") != "rule_artifact.json"
        or rule_sha256 != model_artifact.get("rule_artifact_sha256")
        or rule_sha256 != sha256_file(rule_path)
    ):
        raise IntegrityError("Hybrid component rule artifact binding does not match")
    if load_rule_table(rule_path).min_support != spec.rule_min_support:
        raise IntegrityError("Hybrid component rule support does not match the model spec")


def _load_children(
    root: Path,
    document: dict[str, Any],
    *,
    run_id: str,
    model_id: str,
    protocol: PreparedProtocol,
) -> dict[str, MaterializedScores]:
    rows = document.get("components")
    if not isinstance(rows, dict) or set(rows) != set(_COMPONENT_NAMES):
        raise IntegrityError("Hybrid component rows must contain exactly deep, wide, and hybrid")
    expected_model_ids = {
        "deep": f"{model_id}::deep",
        "wide": f"{model_id}::wide",
        "hybrid": model_id,
    }
    loaded: dict[str, MaterializedScores] = {}
    for name in _COMPONENT_NAMES:
        row = rows[name]
        if not isinstance(row, dict) or set(row) != {
            "model_id",
            "relative_root",
            "manifest_sha256",
        }:
            raise IntegrityError(f"Hybrid component row fields are invalid: {name}")
        if row["relative_root"] != name or row["model_id"] != expected_model_ids[name]:
            raise IntegrityError(f"Hybrid component row identity is invalid: {name}")
        child_root = root / name
        if _sha(row["manifest_sha256"], f"{name}.manifest_sha256") != sha256_file(
            child_root / "manifest.json"
        ):
            raise IntegrityError(f"Hybrid child manifest hash does not match: {name}")
        child = load_materialized_scores(child_root)
        if (
            child.manifest.run_id != run_id
            or child.manifest.model_id != expected_model_ids[name]
            or child.manifest.protocol_manifest_sha256 != protocol_manifest_sha256(protocol)
            or child.manifest.candidate_order_sha256 != protocol.manifest.candidate_order_sha256
        ):
            raise IntegrityError(f"Hybrid child score identity does not match: {name}")
        loaded[name] = child
    reference = loaded["hybrid"].manifest
    for name in ("deep", "wide"):
        manifest = loaded[name].manifest
        if (
            manifest.num_users != reference.num_users
            or manifest.num_candidates != reference.num_candidates
            or manifest.user_order_sha256 != reference.user_order_sha256
            or manifest.score_shape != reference.score_shape
            or manifest.score_dtype != reference.score_dtype
            or not manifest.finite
        ):
            raise IntegrityError(f"Hybrid child score surface differs from Hybrid: {name}")
    return loaded


def load_hybrid_score_components(
    root: Path,
    *,
    run_root: Path,
    protocol: PreparedProtocol,
) -> HybridScoreComponents:
    """Strict-load and replay every identity and fusion binding in a component bundle."""

    document = load_strict_json(root / "component_manifest.json")
    if set(document) != _FIELDS or document.get("schema_version") != "hybrid-score-components/1.1":
        raise IntegrityError("Hybrid component manifest fields do not match schema")
    try:
        actual_entries = {path.name for path in root.iterdir()}
    except OSError as error:
        raise IntegrityError("cannot inspect Hybrid component root") from error
    if actual_entries != {"component_manifest.json", *_COMPONENT_NAMES}:
        raise IntegrityError("Hybrid component root contains an unexpected or missing entry")

    run = load_run(run_root)
    load_run_command(run)
    if run.manifest.status != "PASS":
        raise IntegrityError("Hybrid components require a PASS run")
    protocol_sha256 = protocol_manifest_sha256(protocol)
    if (
        document.get("run_id") != run.manifest.run_id
        or document.get("model_id") != run.manifest.model_id
        or document.get("protocol_manifest_sha256") != protocol_sha256
        or document.get("candidate_order_sha256") != protocol.manifest.candidate_order_sha256
        or run.manifest.protocol_manifest_sha256 != protocol_sha256
    ):
        raise IntegrityError("Hybrid component run or protocol identity does not match")
    if protocol.manifest.split != "val" or protocol.manifest.test_set_opened:
        raise IntegrityError("Hybrid components may replay only against sealed validation")

    model_artifact = _load_model_artifact(run_root, document)
    spec = _load_spec(run_root, document)
    descriptor = _load_descriptor(document, spec, model_artifact)
    if (
        model_artifact.get("model_kind") != "hybrid"
        or model_artifact.get("model_id") != run.manifest.model_id
        or model_artifact.get("model_spec_sha256") != document["model_spec_sha256"]
        or model_artifact.get("checkpoint_directory") != "checkpoint"
    ):
        raise IntegrityError("Hybrid model artifact identity does not match the wrapper")

    normalization = document.get("fusion_normalization")
    weight = document.get("wide_weight")
    if (
        normalization != spec.fusion_normalization
        or normalization != model_artifact.get("fusion_normalization")
        or isinstance(weight, bool)
        or not isinstance(weight, (int, float))
        or not math.isfinite(float(weight))
        or float(weight) != spec.wide_weight
    ):
        raise IntegrityError("Hybrid fusion declaration does not match the model spec")

    _replay_checkpoint_and_rules(
        run_root,
        document,
        model_artifact,
        descriptor,
        spec,
        run=run,
    )
    components = _load_children(
        root,
        document,
        run_id=run.manifest.run_id,
        model_id=run.manifest.model_id,
        protocol=protocol,
    )
    deep = load_score_matrix(components["deep"])
    wide = load_score_matrix(components["wide"])
    hybrid = load_score_matrix(components["hybrid"])
    if not np.allclose(hybrid, deep + float(weight) * wide, rtol=1e-6, atol=1e-6):
        raise IntegrityError("Hybrid scores do not replay from the bound Deep/Wide fusion")

    reference = load_strict_json(run_root / "component_score_artifact_ref.json")
    if (
        set(reference) != {"schema_version", "root", "manifest_sha256"}
        or reference.get("schema_version") != "hybrid-score-components-ref/1.0"
    ):
        raise IntegrityError("Hybrid component reference fields do not match schema")
    try:
        referenced_root = Path(reference["root"]).resolve()
    except (TypeError, OSError) as error:
        raise IntegrityError("Hybrid component reference root is invalid") from error
    if referenced_root != root.resolve() or _sha(
        reference.get("manifest_sha256"), "reference.manifest_sha256"
    ) != sha256_file(root / "component_manifest.json"):
        raise IntegrityError("Hybrid component reference does not match the wrapper")
    return HybridScoreComponents(root=root, manifest=document, components=components)


__all__ = ["HybridScoreComponents", "load_hybrid_score_components"]
