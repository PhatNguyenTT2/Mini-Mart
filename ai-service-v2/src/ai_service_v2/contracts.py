"""Small, strict, serializable contracts for the research runner."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from ai_service_v2.errors import ContractError

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SPLITS = {"train", "val", "test"}
_RUN_STATUSES = {"RUNNING", "PASS", "FAIL", "INCOMPLETE"}


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be an object")
    return value


def _required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ContractError(f"missing required field: {key}")
    return data[key]


def _string(data: dict[str, Any], key: str, *, nonempty: bool = True) -> str:
    value = _required(data, key)
    if not isinstance(value, str) or (nonempty and not value):
        raise ContractError(f"{key} must be a non-empty string")
    return value


def _sha(data: dict[str, Any], key: str) -> str:
    value = _string(data, key)
    if not _SHA256.fullmatch(value):
        raise ContractError(f"{key} must be a lowercase SHA-256")
    return value


def _optional_sha(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ContractError(f"{key} must be null or a lowercase SHA-256")
    return value


def _integer(data: dict[str, Any], key: str, *, minimum: int = 0) -> int:
    value = _required(data, key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContractError(f"{key} must be an integer >= {minimum}")
    return int(value)


def _list_of_ints(data: dict[str, Any], key: str) -> tuple[int, ...]:
    value = _required(data, key)
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in value
    ):
        raise ContractError(f"{key} must be a list of integers")
    return tuple(value)


def _string_map(data: dict[str, Any], key: str) -> dict[str, str]:
    value = _mapping(_required(data, key), key)
    result: dict[str, str] = {}
    for map_key, map_value in value.items():
        if not isinstance(map_key, str) or not isinstance(map_value, str):
            raise ContractError(f"{key} must map strings to strings")
        result[map_key] = map_value
    return result


def _reject_unknown(data: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ContractError(f"unknown contract fields: {', '.join(unknown)}")


def _require_nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} must be a non-empty string")
    return value


def _require_sha(value: Any, name: str) -> str:
    parsed = _require_nonempty(value, name)
    if not _SHA256.fullmatch(parsed):
        raise ContractError(f"{name} must be a lowercase SHA-256")
    return parsed


def _require_nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(f"{name} must be an integer >= 0")
    return int(value)


def _require_positive_int(value: Any, name: str) -> int:
    parsed = _require_nonnegative_int(value, name)
    if parsed < 1:
        raise ContractError(f"{name} must be an integer >= 1")
    return parsed


@dataclass(frozen=True)
class DatasetManifest:
    schema_version: str
    dataset_id: str
    source_kind: str
    source_locator: str
    dataset_sha256: str
    num_users: int
    num_items: int
    num_interactions: int
    num_cold_items: int
    raw_user_map_sha256: str
    raw_item_map_sha256: str
    split_hashes: dict[str, str]
    item_feature_hashes: dict[str, str]
    cold_item_ids: tuple[int, ...]
    event_schema: tuple[str, ...]
    id_convention: str
    basket_field: str | None
    provenance_status: str
    license_status: str
    source_bundle_sha256: str | None = None
    source_artifact_hashes: dict[str, str] = field(default_factory=dict)
    num_baskets: int = 0
    basket_sha256: str | None = None
    behavior_nature: str = "UNSPECIFIED"
    observed_behavior: bool = False
    language_status: str = "UNSPECIFIED"

    _FIELDS: ClassVar[set[str]] = {
        "schema_version",
        "dataset_id",
        "source_kind",
        "source_locator",
        "dataset_sha256",
        "num_users",
        "num_items",
        "num_interactions",
        "num_cold_items",
        "raw_user_map_sha256",
        "raw_item_map_sha256",
        "split_hashes",
        "item_feature_hashes",
        "cold_item_ids",
        "event_schema",
        "id_convention",
        "basket_field",
        "provenance_status",
        "license_status",
        "source_bundle_sha256",
        "source_artifact_hashes",
        "num_baskets",
        "basket_sha256",
        "behavior_nature",
        "observed_behavior",
        "language_status",
    }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> DatasetManifest:
        _reject_unknown(value, cls._FIELDS)
        schema_version = _string(value, "schema_version")
        extended = schema_version == "dataset-manifest/1.1"
        if schema_version not in {"dataset-manifest/1.0", "dataset-manifest/1.1"}:
            raise ContractError(f"unsupported dataset manifest schema: {schema_version}")
        event_schema_value = _required(value, "event_schema")
        if (
            not isinstance(event_schema_value, list)
            or not event_schema_value
            or any(not isinstance(item, str) or not item for item in event_schema_value)
        ):
            raise ContractError("event_schema must be a non-empty list of strings")
        split_hashes = _string_map(value, "split_hashes")
        if set(split_hashes) != _SPLITS:
            raise ContractError("split_hashes must contain exactly train, val, test")
        source_bundle_sha256 = _optional_sha(value, "source_bundle_sha256")
        basket_sha256 = _optional_sha(value, "basket_sha256")
        source_artifact_hashes = (
            _string_map(value, "source_artifact_hashes")
            if "source_artifact_hashes" in value
            else {}
        )
        if any(not _SHA256.fullmatch(item) for item in source_artifact_hashes.values()):
            raise ContractError("source_artifact_hashes values must be lowercase SHA-256")
        observed_behavior = value.get("observed_behavior", False)
        if not isinstance(observed_behavior, bool):
            raise ContractError("observed_behavior must be boolean")
        if extended:
            required_extended = {
                "source_bundle_sha256",
                "source_artifact_hashes",
                "num_baskets",
                "basket_sha256",
                "behavior_nature",
                "observed_behavior",
                "language_status",
            }
            missing_extended = sorted(required_extended - set(value))
            if missing_extended:
                raise ContractError(
                    "missing dataset-manifest/1.1 fields: " + ", ".join(missing_extended)
                )
            if source_bundle_sha256 is None or basket_sha256 is None:
                raise ContractError("dataset-manifest/1.1 requires source and basket hashes")
            if not source_artifact_hashes:
                raise ContractError("dataset-manifest/1.1 requires source artifact hashes")
        manifest = cls(
            schema_version=schema_version,
            dataset_id=_string(value, "dataset_id"),
            source_kind=_string(value, "source_kind"),
            source_locator=_string(value, "source_locator"),
            dataset_sha256=_sha(value, "dataset_sha256"),
            num_users=_integer(value, "num_users", minimum=1),
            num_items=_integer(value, "num_items", minimum=1),
            num_interactions=_integer(value, "num_interactions", minimum=1),
            num_cold_items=_integer(value, "num_cold_items"),
            raw_user_map_sha256=_sha(value, "raw_user_map_sha256"),
            raw_item_map_sha256=_sha(value, "raw_item_map_sha256"),
            split_hashes=split_hashes,
            item_feature_hashes=_string_map(value, "item_feature_hashes"),
            cold_item_ids=_list_of_ints(value, "cold_item_ids"),
            event_schema=tuple(event_schema_value),
            id_convention=_string(value, "id_convention"),
            basket_field=(
                None if value.get("basket_field") is None else _string(value, "basket_field")
            ),
            provenance_status=_string(value, "provenance_status"),
            license_status=_string(value, "license_status"),
            source_bundle_sha256=source_bundle_sha256,
            source_artifact_hashes=source_artifact_hashes,
            num_baskets=(_integer(value, "num_baskets") if "num_baskets" in value else 0),
            basket_sha256=basket_sha256,
            behavior_nature=(
                _string(value, "behavior_nature") if "behavior_nature" in value else "UNSPECIFIED"
            ),
            observed_behavior=observed_behavior,
            language_status=(
                _string(value, "language_status") if "language_status" in value else "UNSPECIFIED"
            ),
        )
        if manifest.num_cold_items != len(manifest.cold_item_ids):
            raise ContractError("num_cold_items does not match cold_item_ids")
        if len(set(manifest.cold_item_ids)) != len(manifest.cold_item_ids):
            raise ContractError("cold_item_ids must be unique")
        if any(item < 0 or item >= manifest.num_items for item in manifest.cold_item_ids):
            raise ContractError("cold_item_ids must be valid internal item IDs")
        return manifest

    def to_mapping(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": self.schema_version,
            "dataset_id": self.dataset_id,
            "source_kind": self.source_kind,
            "source_locator": self.source_locator,
            "dataset_sha256": self.dataset_sha256,
            "num_users": self.num_users,
            "num_items": self.num_items,
            "num_interactions": self.num_interactions,
            "num_cold_items": self.num_cold_items,
            "raw_user_map_sha256": self.raw_user_map_sha256,
            "raw_item_map_sha256": self.raw_item_map_sha256,
            "split_hashes": dict(sorted(self.split_hashes.items())),
            "item_feature_hashes": dict(sorted(self.item_feature_hashes.items())),
            "cold_item_ids": list(self.cold_item_ids),
            "event_schema": list(self.event_schema),
            "id_convention": self.id_convention,
            "basket_field": self.basket_field,
            "provenance_status": self.provenance_status,
            "license_status": self.license_status,
        }
        if self.schema_version == "dataset-manifest/1.1":
            value.update(
                {
                    "source_bundle_sha256": self.source_bundle_sha256,
                    "source_artifact_hashes": dict(sorted(self.source_artifact_hashes.items())),
                    "num_baskets": self.num_baskets,
                    "basket_sha256": self.basket_sha256,
                    "behavior_nature": self.behavior_nature,
                    "observed_behavior": self.observed_behavior,
                    "language_status": self.language_status,
                }
            )
        return value


@dataclass(frozen=True)
class ProtocolManifest:
    protocol_id: str
    dataset_id: str
    dataset_manifest_sha256: str
    split: str
    split_hash: str
    candidate_item_ids: tuple[int, ...]
    candidate_order_sha256: str
    eligible_user_rule: str
    positive_rule: str
    seen_masking: str
    cutoff: int
    tie_break: str
    metric_version: str
    test_set_opened: bool

    _FIELDS: ClassVar[set[str]] = {
        "protocol_id",
        "dataset_id",
        "dataset_manifest_sha256",
        "split",
        "split_hash",
        "candidate_item_ids",
        "candidate_order_sha256",
        "eligible_user_rule",
        "positive_rule",
        "seen_masking",
        "cutoff",
        "tie_break",
        "metric_version",
        "test_set_opened",
    }

    def __post_init__(self) -> None:
        _require_nonempty(self.protocol_id, "protocol_id")
        _require_nonempty(self.dataset_id, "dataset_id")
        _require_sha(self.dataset_manifest_sha256, "dataset_manifest_sha256")
        if self.split not in _SPLITS:
            raise ContractError(f"unsupported split: {self.split}")
        _require_sha(self.split_hash, "split_hash")
        if not self.candidate_item_ids or len(set(self.candidate_item_ids)) != len(
            self.candidate_item_ids
        ):
            raise ContractError("candidate_item_ids must be non-empty and unique")
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in self.candidate_item_ids
        ):
            raise ContractError("candidate_item_ids must contain non-negative integers")
        _require_sha(self.candidate_order_sha256, "candidate_order_sha256")
        for name, value in (
            ("eligible_user_rule", self.eligible_user_rule),
            ("positive_rule", self.positive_rule),
            ("seen_masking", self.seen_masking),
            ("tie_break", self.tie_break),
            ("metric_version", self.metric_version),
        ):
            _require_nonempty(value, name)
        if isinstance(self.cutoff, bool) or not isinstance(self.cutoff, int):
            raise ContractError("cutoff must be an integer >= 1")
        if self.cutoff < 1 or self.cutoff > len(self.candidate_item_ids):
            raise ContractError("cutoff cannot exceed candidate catalog")
        if not isinstance(self.test_set_opened, bool):
            raise ContractError("test_set_opened must be boolean")
        if self.split == "test" and not self.test_set_opened:
            raise ContractError("test protocol cannot be prepared while test_set_opened=false")

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ProtocolManifest:
        _reject_unknown(value, cls._FIELDS)
        split = _string(value, "split")
        candidates = _list_of_ints(value, "candidate_item_ids")
        opened = _required(value, "test_set_opened")
        return cls(
            protocol_id=_string(value, "protocol_id"),
            dataset_id=_string(value, "dataset_id"),
            dataset_manifest_sha256=_sha(value, "dataset_manifest_sha256"),
            split=split,
            split_hash=_sha(value, "split_hash"),
            candidate_item_ids=candidates,
            candidate_order_sha256=_sha(value, "candidate_order_sha256"),
            eligible_user_rule=_string(value, "eligible_user_rule"),
            positive_rule=_string(value, "positive_rule"),
            seen_masking=_string(value, "seen_masking"),
            cutoff=_integer(value, "cutoff", minimum=1),
            tie_break=_string(value, "tie_break"),
            metric_version=_string(value, "metric_version"),
            test_set_opened=opened,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "dataset_id": self.dataset_id,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "split": self.split,
            "split_hash": self.split_hash,
            "candidate_item_ids": list(self.candidate_item_ids),
            "candidate_order_sha256": self.candidate_order_sha256,
            "eligible_user_rule": self.eligible_user_rule,
            "positive_rule": self.positive_rule,
            "seen_masking": self.seen_masking,
            "cutoff": self.cutoff,
            "tie_break": self.tie_break,
            "metric_version": self.metric_version,
            "test_set_opened": self.test_set_opened,
        }


@dataclass(frozen=True)
class ModelDescriptor:
    model_id: str
    family: str
    implementation_provenance: str
    repository_url: str | None
    repository_commit: str | None
    objective: str
    negative_sampler: str
    input_features: tuple[str, ...]
    config_sha256: str
    adapter_revision: str

    def __post_init__(self) -> None:
        if not self.model_id or not self.family or not self.implementation_provenance:
            raise ContractError("model identity fields must be non-empty")
        if not self.objective or not self.negative_sampler or not self.adapter_revision:
            raise ContractError("model training fields must be non-empty")
        if not _SHA256.fullmatch(self.config_sha256):
            raise ContractError("config_sha256 must be a lowercase SHA-256")
        if (self.repository_url is None) != (self.repository_commit is None):
            raise ContractError("repository URL and commit must be supplied together")
        if self.repository_commit is not None and not re.fullmatch(
            r"[0-9a-f]{40}", self.repository_commit
        ):
            raise ContractError("repository_commit must be a full lowercase commit SHA")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "family": self.family,
            "implementation_provenance": self.implementation_provenance,
            "repository_url": self.repository_url,
            "repository_commit": self.repository_commit,
            "objective": self.objective,
            "negative_sampler": self.negative_sampler,
            "input_features": list(self.input_features),
            "config_sha256": self.config_sha256,
            "adapter_revision": self.adapter_revision,
        }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ModelDescriptor:
        allowed = {
            "model_id",
            "family",
            "implementation_provenance",
            "repository_url",
            "repository_commit",
            "objective",
            "negative_sampler",
            "input_features",
            "config_sha256",
            "adapter_revision",
        }
        _reject_unknown(value, allowed)
        features = _required(value, "input_features")
        if not isinstance(features, list) or any(not isinstance(item, str) for item in features):
            raise ContractError("input_features must be a list of strings")
        for key in ("repository_url", "repository_commit"):
            if value.get(key) is not None and not isinstance(value[key], str):
                raise ContractError(f"{key} must be a string or null")
        return cls(
            model_id=_string(value, "model_id"),
            family=_string(value, "family"),
            implementation_provenance=_string(value, "implementation_provenance"),
            repository_url=value.get("repository_url"),
            repository_commit=value.get("repository_commit"),
            objective=_string(value, "objective"),
            negative_sampler=_string(value, "negative_sampler"),
            input_features=tuple(features),
            config_sha256=_sha(value, "config_sha256"),
            adapter_revision=_string(value, "adapter_revision"),
        )


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    model_id: str
    dataset_manifest_sha256: str
    protocol_manifest_sha256: str
    seed: int
    environment_lock_sha256: str
    checkpoint_rule: str
    checkpoint_sha256: str | None
    command_sha256: str
    status: str

    def __post_init__(self) -> None:
        _require_nonempty(self.run_id, "run_id")
        _require_nonempty(self.model_id, "model_id")
        _require_nonnegative_int(self.seed, "seed")
        for name, value in (
            ("dataset_manifest_sha256", self.dataset_manifest_sha256),
            ("protocol_manifest_sha256", self.protocol_manifest_sha256),
            ("environment_lock_sha256", self.environment_lock_sha256),
            ("command_sha256", self.command_sha256),
        ):
            _require_sha(value, name)
        if self.checkpoint_sha256 is not None:
            _require_sha(self.checkpoint_sha256, "checkpoint_sha256")
        _require_nonempty(self.checkpoint_rule, "checkpoint_rule")
        if self.status not in _RUN_STATUSES:
            raise ContractError(f"unsupported run status: {self.status}")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "protocol_manifest_sha256": self.protocol_manifest_sha256,
            "seed": self.seed,
            "environment_lock_sha256": self.environment_lock_sha256,
            "checkpoint_rule": self.checkpoint_rule,
            "checkpoint_sha256": self.checkpoint_sha256,
            "command_sha256": self.command_sha256,
            "status": self.status,
        }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> RunManifest:
        allowed = {
            "run_id",
            "model_id",
            "dataset_manifest_sha256",
            "protocol_manifest_sha256",
            "seed",
            "environment_lock_sha256",
            "checkpoint_rule",
            "checkpoint_sha256",
            "command_sha256",
            "status",
        }
        _reject_unknown(value, allowed)
        return cls(
            run_id=_string(value, "run_id"),
            model_id=_string(value, "model_id"),
            dataset_manifest_sha256=_sha(value, "dataset_manifest_sha256"),
            protocol_manifest_sha256=_sha(value, "protocol_manifest_sha256"),
            seed=_integer(value, "seed"),
            environment_lock_sha256=_sha(value, "environment_lock_sha256"),
            checkpoint_rule=_string(value, "checkpoint_rule"),
            checkpoint_sha256=_optional_sha(value, "checkpoint_sha256"),
            command_sha256=_sha(value, "command_sha256"),
            status=_string(value, "status"),
        )


@dataclass(frozen=True)
class ScoreArtifactManifest:
    run_id: str
    model_id: str
    num_users: int
    num_candidates: int
    user_order_sha256: str
    candidate_order_sha256: str
    score_dtype: str
    score_shape: tuple[int, int]
    finite: bool
    chunks: tuple[str, ...]
    protocol_manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(self.run_id, "run_id")
        _require_nonempty(self.model_id, "model_id")
        _require_positive_int(self.num_users, "num_users")
        _require_positive_int(self.num_candidates, "num_candidates")
        if self.score_shape != (self.num_users, self.num_candidates):
            raise ContractError("score_shape must match declared dimensions")
        for name, value in (
            ("user_order_sha256", self.user_order_sha256),
            ("candidate_order_sha256", self.candidate_order_sha256),
        ):
            _require_sha(value, name)
        if self.protocol_manifest_sha256 is not None:
            _require_sha(self.protocol_manifest_sha256, "protocol_manifest_sha256")
        _require_nonempty(self.score_dtype, "score_dtype")
        if not isinstance(self.finite, bool):
            raise ContractError("finite must be boolean")
        if not self.finite:
            raise ContractError("non-finite score artifacts cannot be admitted")
        if not self.chunks or any(not isinstance(name, str) or not name for name in self.chunks):
            raise ContractError("score artifact must list at least one chunk")

    def to_mapping(self) -> dict[str, Any]:
        document = {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "num_users": self.num_users,
            "num_candidates": self.num_candidates,
            "user_order_sha256": self.user_order_sha256,
            "candidate_order_sha256": self.candidate_order_sha256,
            "score_dtype": self.score_dtype,
            "score_shape": list(self.score_shape),
            "finite": self.finite,
            "chunks": list(self.chunks),
        }
        if self.protocol_manifest_sha256 is not None:
            document["protocol_manifest_sha256"] = self.protocol_manifest_sha256
        return document

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ScoreArtifactManifest:
        allowed = {
            "run_id",
            "model_id",
            "num_users",
            "num_candidates",
            "user_order_sha256",
            "candidate_order_sha256",
            "score_dtype",
            "score_shape",
            "finite",
            "chunks",
            "protocol_manifest_sha256",
        }
        _reject_unknown(value, allowed)
        shape = _required(value, "score_shape")
        chunks = _required(value, "chunks")
        finite = _required(value, "finite")
        if (
            not isinstance(shape, list)
            or len(shape) != 2
            or any(isinstance(item, bool) or not isinstance(item, int) for item in shape)
        ):
            raise ContractError("score_shape must be a two-element integer list")
        if not isinstance(chunks, list) or any(
            not isinstance(item, str) or not item for item in chunks
        ):
            raise ContractError("chunks must be a non-empty list of strings")
        if not isinstance(finite, bool):
            raise ContractError("finite must be boolean")
        protocol_hash = value.get("protocol_manifest_sha256")
        if protocol_hash is not None and not isinstance(protocol_hash, str):
            raise ContractError("protocol_manifest_sha256 must be a string or null")
        return cls(
            run_id=_string(value, "run_id"),
            model_id=_string(value, "model_id"),
            num_users=_integer(value, "num_users", minimum=1),
            num_candidates=_integer(value, "num_candidates", minimum=1),
            user_order_sha256=_sha(value, "user_order_sha256"),
            candidate_order_sha256=_sha(value, "candidate_order_sha256"),
            score_dtype=_string(value, "score_dtype"),
            score_shape=(shape[0], shape[1]),
            finite=finite,
            chunks=tuple(chunks),
            protocol_manifest_sha256=protocol_hash,
        )


@dataclass(frozen=True)
class EvaluationReceipt:
    run_id: str
    model_id: str
    protocol_id: str
    protocol_manifest_sha256: str
    candidate_order_sha256: str
    evaluator_version: str
    evaluator_implementation_sha256: str
    per_user_metrics_sha256: str
    num_total_users: int
    num_eligible_users: int
    candidate_count: int
    cutoff: int
    aggregate_metrics: dict[str, float | None]
    denominator_by_metric: dict[str, int]
    verdict: str

    def __post_init__(self) -> None:
        _require_nonempty(self.run_id, "run_id")
        _require_nonempty(self.model_id, "model_id")
        _require_nonempty(self.protocol_id, "protocol_id")
        _require_sha(self.protocol_manifest_sha256, "protocol_manifest_sha256")
        _require_sha(self.candidate_order_sha256, "candidate_order_sha256")
        _require_nonempty(self.evaluator_version, "evaluator_version")
        _require_sha(self.evaluator_implementation_sha256, "evaluator_implementation_sha256")
        _require_positive_int(self.num_total_users, "num_total_users")
        _require_positive_int(self.num_eligible_users, "num_eligible_users")
        if self.num_eligible_users > self.num_total_users:
            raise ContractError("eligible users cannot exceed total users")
        _require_positive_int(self.candidate_count, "candidate_count")
        _require_positive_int(self.cutoff, "cutoff")
        if self.cutoff > self.candidate_count:
            raise ContractError("invalid candidate count or cutoff")
        _require_sha(self.per_user_metrics_sha256, "per_user_metrics_sha256")
        expected_metrics = {f"HR@{self.cutoff}", f"NDCG@{self.cutoff}", "GAUC"}
        if set(self.aggregate_metrics) != expected_metrics:
            raise ContractError("evaluation metrics must be HR, NDCG, and GAUC at the cutoff")
        if set(self.aggregate_metrics) != set(self.denominator_by_metric):
            raise ContractError("aggregate metrics and denominators must have identical keys")
        for metric, value in self.aggregate_metrics.items():
            denominator = self.denominator_by_metric[metric]
            if isinstance(denominator, bool) or not isinstance(denominator, int):
                raise ContractError(f"denominator for {metric} must be an integer")
            if denominator < 0 or denominator > self.num_eligible_users:
                raise ContractError(f"invalid denominator for {metric}")
            if value is None:
                if denominator != 0:
                    raise ContractError(f"undefined metric {metric} must have zero denominator")
            elif isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ContractError(f"aggregate metric {metric} must be a number or null")
            elif not math.isfinite(float(value)):
                raise ContractError(f"aggregate metric {metric} must be finite")
            elif not 0.0 <= float(value) <= 1.0:
                raise ContractError(f"aggregate metric {metric} must be inside [0, 1]")
            elif denominator == 0:
                raise ContractError(f"defined metric {metric} must have a positive denominator")
        if self.verdict not in {"PASS", "FAIL", "INCOMPLETE"}:
            raise ContractError(f"unsupported evaluation verdict: {self.verdict}")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "protocol_id": self.protocol_id,
            "protocol_manifest_sha256": self.protocol_manifest_sha256,
            "candidate_order_sha256": self.candidate_order_sha256,
            "evaluator_version": self.evaluator_version,
            "evaluator_implementation_sha256": self.evaluator_implementation_sha256,
            "per_user_metrics_sha256": self.per_user_metrics_sha256,
            "num_total_users": self.num_total_users,
            "num_eligible_users": self.num_eligible_users,
            "candidate_count": self.candidate_count,
            "cutoff": self.cutoff,
            "aggregate_metrics": dict(sorted(self.aggregate_metrics.items())),
            "denominator_by_metric": dict(sorted(self.denominator_by_metric.items())),
            "verdict": self.verdict,
        }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> EvaluationReceipt:
        allowed = {
            "run_id",
            "model_id",
            "protocol_id",
            "protocol_manifest_sha256",
            "candidate_order_sha256",
            "evaluator_version",
            "evaluator_implementation_sha256",
            "per_user_metrics_sha256",
            "num_total_users",
            "num_eligible_users",
            "candidate_count",
            "cutoff",
            "aggregate_metrics",
            "denominator_by_metric",
            "verdict",
        }
        _reject_unknown(value, allowed)
        aggregates = _mapping(_required(value, "aggregate_metrics"), "aggregate_metrics")
        denominators = _mapping(_required(value, "denominator_by_metric"), "denominator_by_metric")
        if any(not isinstance(key, str) for key in aggregates):
            raise ContractError("aggregate_metrics keys must be strings")
        if any(
            item is not None and (isinstance(item, bool) or not isinstance(item, (int, float)))
            for item in aggregates.values()
        ):
            raise ContractError("aggregate_metrics must map strings to numbers or null")
        if any(
            not isinstance(key, str) or isinstance(item, bool) or not isinstance(item, int)
            for key, item in denominators.items()
        ):
            raise ContractError("denominator_by_metric must map strings to integers")
        return cls(
            run_id=_string(value, "run_id"),
            model_id=_string(value, "model_id"),
            protocol_id=_string(value, "protocol_id"),
            protocol_manifest_sha256=_sha(value, "protocol_manifest_sha256"),
            candidate_order_sha256=_sha(value, "candidate_order_sha256"),
            evaluator_version=_string(value, "evaluator_version"),
            evaluator_implementation_sha256=_sha(value, "evaluator_implementation_sha256"),
            per_user_metrics_sha256=_sha(value, "per_user_metrics_sha256"),
            num_total_users=_integer(value, "num_total_users", minimum=1),
            num_eligible_users=_integer(value, "num_eligible_users", minimum=1),
            candidate_count=_integer(value, "candidate_count", minimum=1),
            cutoff=_integer(value, "cutoff", minimum=1),
            aggregate_metrics={
                key: None if item is None else float(item) for key, item in aggregates.items()
            },
            denominator_by_metric=dict(denominators),
            verdict=_string(value, "verdict"),
        )


__all__ = [
    "DatasetManifest",
    "EvaluationReceipt",
    "ModelDescriptor",
    "ProtocolManifest",
    "RunManifest",
    "ScoreArtifactManifest",
]
