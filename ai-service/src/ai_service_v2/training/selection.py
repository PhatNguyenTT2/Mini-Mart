"""Frozen validation-selection contracts for MP2 confirmatory execution."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ai_service_v2.errors import ContractError, IntegrityError

BASE_SEEDS = (42, 2027, 31415)
EXTENDED_PRIMARY_SEEDS = (42, 2027, 31415, 2718, 1618)
EPOCH_METHODS = frozenset({"BPR-MF", "LightGCN", "SASRec", "UniSRec", "Deep-only"})
NON_EPOCH_METHODS = frozenset({"Random", "MostPop", "ItemKNN", "Rule-only", "Hybrid"})
STOCHASTIC_CONFIGURATION_METHODS = frozenset(
    {"Random", "BPR-MF", "LightGCN", "SASRec", "UniSRec", "Deep-only", "Hybrid"}
)
DETERMINISTIC_CONFIGURATION_METHODS = frozenset({"MostPop", "ItemKNN", "Rule-only"})
MANDATORY_BASELINES = frozenset({"ItemKNN", "BPR-MF", "LightGCN", "SASRec", "UniSRec"})
RULE_SUPPORT_FRACTIONS = frozenset({0.0005, 0.001, 0.002})
HYBRID_LAMBDAS = frozenset({0.25, 0.5, 1.0, 2.0})
_OUTCOME_STATUSES = frozenset({"PASS", "FAIL", "INCOMPLETE"})
_EXCLUDED_CONFIGURATION_FIELDS = frozenset(
    {
        "run_seed",
        "selected_epoch",
        "checkpoint_hash",
        "checkpoint_sha256",
        "artifact_path",
        "validation_metric_value",
        "validation_ndcg_at_10",
        "test_value",
    }
)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _nonempty(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} must be a non-empty string")
    return unicodedata.normalize("NFC", value)


def _metric(value: object, name: str = "validation_ndcg_at_10") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0 or parsed > 1.0:
        raise ContractError(f"{name} must be finite and within [0, 1]")
    return parsed


def _decimal_text(value: float | Decimal) -> str:
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except InvalidOperation as error:
        raise IntegrityError("configuration decimal is invalid") from error
    if not parsed.is_finite():
        raise IntegrityError("configuration decimal must be finite")
    if parsed.is_zero():
        return "0"
    text = format(parsed, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _canonical_mapping_items(value: Mapping[object, object]) -> list[tuple[str, object]]:
    normalized: dict[str, object] = {}
    folded: dict[str, str] = {}
    for raw_key, item in value.items():
        if not isinstance(raw_key, str) or not raw_key:
            raise IntegrityError("configuration mapping keys must be non-empty strings")
        key = unicodedata.normalize("NFC", raw_key)
        if key in normalized:
            raise IntegrityError(f"duplicate normalized configuration key: {key}")
        casefolded = key.casefold()
        if casefolded in folded:
            raise IntegrityError(f"case-colliding configuration keys: {folded[casefolded]} / {key}")
        if key in _EXCLUDED_CONFIGURATION_FIELDS:
            raise ContractError(f"configuration payload contains excluded field: {key}")
        normalized[key] = item
        folded[casefolded] = key
    return sorted(normalized.items(), key=lambda row: row[0].encode("utf-8"))


def _encode_configuration_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (float, Decimal)):
        return _decimal_text(value)
    if isinstance(value, str):
        return json.dumps(
            unicodedata.normalize("NFC", value),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    if isinstance(value, Mapping):
        return (
            "{"
            + ",".join(
                json.dumps(key, ensure_ascii=False, separators=(",", ":"))
                + ":"
                + _encode_configuration_value(item)
                for key, item in _canonical_mapping_items(value)
            )
            + "}"
        )
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode_configuration_value(item) for item in value) + "]"
    raise IntegrityError(f"unsupported configuration value type: {type(value).__name__}")


def canonical_configuration_payload(
    *,
    method_id: str,
    resolved_training_and_scoring_parameters: Mapping[str, object],
    resolved_source_native_defaults_that_affect_scores: Mapping[str, object],
    feature_contract_revision: str,
    adapter_revision: str,
) -> bytes:
    """Serialize exactly the P2-authorized configuration identity fields."""

    document: dict[str, object] = {
        "method_id": _nonempty(method_id, "method_id"),
        "resolved_training_and_scoring_parameters": dict(resolved_training_and_scoring_parameters),
        "resolved_source_native_defaults_that_affect_scores": dict(
            resolved_source_native_defaults_that_affect_scores
        ),
        "feature_contract_revision": _nonempty(
            feature_contract_revision, "feature_contract_revision"
        ),
        "adapter_revision": _nonempty(adapter_revision, "adapter_revision"),
    }
    return _encode_configuration_value(document).encode("utf-8")


@dataclass(frozen=True)
class CanonicalConfigurationBinding:
    path: Path
    payload_bytes: int
    sha256: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "canonical_config_payload_path": self.path.as_posix(),
            "canonical_config_payload_bytes": self.payload_bytes,
            "canonical_config_sha256": self.sha256,
        }


def write_canonical_configuration(
    path: Path,
    *,
    method_id: str,
    resolved_training_and_scoring_parameters: Mapping[str, object],
    resolved_source_native_defaults_that_affect_scores: Mapping[str, object],
    feature_contract_revision: str,
    adapter_revision: str,
) -> CanonicalConfigurationBinding:
    """Write one no-newline canonical payload into an unused namespace."""

    if path.exists():
        raise IntegrityError(f"canonical configuration payload already exists: {path}")
    if not path.parent.is_dir():
        raise IntegrityError("canonical configuration parent directory does not exist")
    payload = canonical_configuration_payload(
        method_id=method_id,
        resolved_training_and_scoring_parameters=resolved_training_and_scoring_parameters,
        resolved_source_native_defaults_that_affect_scores=(
            resolved_source_native_defaults_that_affect_scores
        ),
        feature_contract_revision=feature_contract_revision,
        adapter_revision=adapter_revision,
    )
    try:
        path.write_bytes(payload)
    except OSError as error:
        raise IntegrityError(f"cannot write canonical configuration payload: {path}") from error
    return CanonicalConfigurationBinding(
        path=path,
        payload_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


@dataclass(frozen=True)
class EpochCheckpointCandidate:
    epoch: int
    validation_ndcg_at_10: float
    checkpoint_sha256: str
    validation_score_artifact_sha256: str

    def __post_init__(self) -> None:
        if isinstance(self.epoch, bool) or not isinstance(self.epoch, int) or self.epoch < 1:
            raise ContractError("checkpoint epoch must be a positive integer")
        object.__setattr__(
            self,
            "validation_ndcg_at_10",
            _metric(self.validation_ndcg_at_10),
        )
        if not _is_sha256(self.checkpoint_sha256):
            raise ContractError("checkpoint SHA-256 is invalid")
        if not _is_sha256(self.validation_score_artifact_sha256):
            raise ContractError("validation score artifact SHA-256 is invalid")


def select_epoch_checkpoint(
    candidates: Sequence[EpochCheckpointCandidate],
) -> EpochCheckpointCandidate:
    """Select max validation NDCG, earliest epoch, then checkpoint hash."""

    if not candidates:
        raise ContractError("checkpoint selection requires at least one candidate")
    identities = {(row.epoch, row.checkpoint_sha256) for row in candidates}
    if len(identities) != len(candidates):
        raise ContractError("checkpoint selection contains a duplicate candidate")
    return min(
        candidates,
        key=lambda row: (
            -row.validation_ndcg_at_10,
            row.epoch,
            row.checkpoint_sha256,
        ),
    )


@dataclass(frozen=True)
class SeedValidationOutcome:
    seed: int
    status: str
    validation_ndcg_at_10: float | None = None
    selected_epoch: int | None = None
    checkpoint_sha256: str | None = None
    validation_score_artifact_sha256: str | None = None
    failure_receipt_sha256: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ContractError("validation seed must be a non-negative integer")
        if self.status not in _OUTCOME_STATUSES:
            raise ContractError("validation outcome status is invalid")
        if self.status == "PASS":
            if self.validation_ndcg_at_10 is None:
                raise ContractError("PASS validation outcome requires NDCG@10")
            object.__setattr__(
                self,
                "validation_ndcg_at_10",
                _metric(self.validation_ndcg_at_10),
            )
            if not _is_sha256(self.validation_score_artifact_sha256):
                raise ContractError("PASS validation outcome requires a score artifact hash")
            if self.failure_receipt_sha256 is not None:
                raise ContractError("PASS validation outcome cannot carry a failure receipt")
            return
        if any(
            value is not None
            for value in (
                self.validation_ndcg_at_10,
                self.selected_epoch,
                self.checkpoint_sha256,
                self.validation_score_artifact_sha256,
            )
        ):
            raise ContractError("failed or incomplete seed cannot carry selected results")
        if not _is_sha256(self.failure_receipt_sha256):
            raise ContractError("failed or incomplete seed requires a failure receipt hash")


def _validate_outcome_for_method(method_id: str, outcome: SeedValidationOutcome) -> None:
    if outcome.status != "PASS":
        return
    if method_id in EPOCH_METHODS:
        if (
            isinstance(outcome.selected_epoch, bool)
            or not isinstance(outcome.selected_epoch, int)
            or outcome.selected_epoch < 1
            or not _is_sha256(outcome.checkpoint_sha256)
        ):
            raise ContractError("epoch method outcome requires selected epoch and checkpoint")
        return
    if method_id not in NON_EPOCH_METHODS:
        raise ContractError(f"unknown method checkpoint policy: {method_id}")
    if outcome.selected_epoch is not None or outcome.checkpoint_sha256 is not None:
        raise ContractError("non-epoch method outcome must mark checkpoint not applicable")


@dataclass(frozen=True)
class ConfigurationQualification:
    dataset_id: str
    method_id: str
    canonical_config_sha256: str
    status: str
    validation_statistic: float | None
    required_seeds: tuple[int, ...]
    completed_seeds: tuple[int, ...]
    method_specific_tie_break_value: float | None

    @property
    def eligible(self) -> bool:
        return self.status == "ELIGIBLE"

    def to_mapping(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "method_id": self.method_id,
            "canonical_config_sha256": self.canonical_config_sha256,
            "status": self.status,
            "validation_statistic": self.validation_statistic,
            "required_seeds": list(self.required_seeds),
            "completed_seeds": list(self.completed_seeds),
            "method_specific_tie_break_value": self.method_specific_tie_break_value,
            "failed_seed_policy": "CONFIGURATION_INELIGIBLE_NO_IMPUTATION",
        }


def _tie_break_value(method_id: str, value: float | None) -> float | None:
    if method_id == "Rule-only":
        if value not in RULE_SUPPORT_FRACTIONS:
            raise ContractError("Rule-only tie-break value is outside the support grid")
        return float(value)
    if method_id == "Hybrid":
        if value not in HYBRID_LAMBDAS:
            raise ContractError("Hybrid tie-break value is outside the lambda grid")
        return float(value)
    if value is not None:
        raise ContractError("method does not define a method-specific tie-break")
    return None


def qualify_configuration(
    *,
    dataset_id: str,
    method_id: str,
    canonical_config_sha256: str,
    outcomes: Sequence[SeedValidationOutcome],
    method_specific_tie_break_value: float | None = None,
) -> ConfigurationQualification:
    """Apply complete-seed eligibility without imputation or replacement."""

    dataset = _nonempty(dataset_id, "dataset_id")
    method = _nonempty(method_id, "method_id")
    if not _is_sha256(canonical_config_sha256):
        raise ContractError("canonical configuration SHA-256 is invalid")
    tie_break = _tie_break_value(method, method_specific_tie_break_value)
    required: tuple[int, ...]
    if method in STOCHASTIC_CONFIGURATION_METHODS:
        required = BASE_SEEDS
    elif method in DETERMINISTIC_CONFIGURATION_METHODS:
        required = (42,)
    else:
        raise ContractError(f"unknown configuration seed policy: {method}")
    observed = [row.seed for row in outcomes]
    if len(observed) != len(set(observed)):
        raise ContractError("configuration contains duplicate seed outcomes")
    if any(seed not in required for seed in observed):
        raise ContractError("configuration selection cannot use replacement or extended seeds")
    by_seed = {row.seed: row for row in outcomes}
    for row in outcomes:
        _validate_outcome_for_method(method, row)
    completed = tuple(
        seed
        for seed in required
        if by_seed.get(seed, None) is not None and by_seed[seed].status == "PASS"
    )
    if set(by_seed) != set(required) or completed != required:
        return ConfigurationQualification(
            dataset_id=dataset,
            method_id=method,
            canonical_config_sha256=canonical_config_sha256,
            status="CONFIGURATION_INELIGIBLE_NO_IMPUTATION",
            validation_statistic=None,
            required_seeds=required,
            completed_seeds=completed,
            method_specific_tie_break_value=tie_break,
        )
    values = [by_seed[seed].validation_ndcg_at_10 for seed in required]
    if any(value is None for value in values):
        raise IntegrityError("completed validation outcome lost its metric")
    statistic = math.fsum(float(value) for value in values if value is not None) / len(values)
    return ConfigurationQualification(
        dataset_id=dataset,
        method_id=method,
        canonical_config_sha256=canonical_config_sha256,
        status="ELIGIBLE",
        validation_statistic=statistic,
        required_seeds=required,
        completed_seeds=completed,
        method_specific_tie_break_value=tie_break,
    )


@dataclass(frozen=True)
class ConfigurationSelection:
    dataset_id: str
    method_id: str
    status: str
    selected_config_sha256: str | None
    validation_statistic: float | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "method_id": self.method_id,
            "status": self.status,
            "selected_config_sha256": self.selected_config_sha256,
            "validation_statistic": self.validation_statistic,
            "selection_metric": "VALIDATION_NDCG_AT_10",
        }


def select_configuration(
    candidates: Sequence[ConfigurationQualification],
) -> ConfigurationSelection:
    if not candidates:
        raise ContractError("configuration selection requires candidates")
    dataset_ids = {row.dataset_id for row in candidates}
    method_ids = {row.method_id for row in candidates}
    hashes = {row.canonical_config_sha256 for row in candidates}
    if len(dataset_ids) != 1 or len(method_ids) != 1 or len(hashes) != len(candidates):
        raise ContractError(
            "configuration candidates must have one dataset/method and unique hashes"
        )
    dataset = next(iter(dataset_ids))
    method = next(iter(method_ids))
    eligible = [row for row in candidates if row.eligible]
    if not eligible:
        return ConfigurationSelection(
            dataset_id=dataset,
            method_id=method,
            status="INCOMPLETE_NO_ELIGIBLE_CONFIGURATION",
            selected_config_sha256=None,
            validation_statistic=None,
        )

    def selection_key(row: ConfigurationQualification) -> tuple[float, float, str]:
        if row.validation_statistic is None:
            raise IntegrityError("eligible configuration has no validation statistic")
        method_key = 0.0
        if method == "Rule-only":
            if row.method_specific_tie_break_value is None:
                raise IntegrityError("Rule-only candidate lost its support tie-break")
            method_key = -row.method_specific_tie_break_value
        elif method == "Hybrid":
            if row.method_specific_tie_break_value is None:
                raise IntegrityError("Hybrid candidate lost its lambda tie-break")
            method_key = row.method_specific_tie_break_value
        return (-row.validation_statistic, method_key, row.canonical_config_sha256)

    selected = min(eligible, key=selection_key)
    return ConfigurationSelection(
        dataset_id=dataset,
        method_id=method,
        status="SELECTED",
        selected_config_sha256=selected.canonical_config_sha256,
        validation_statistic=selected.validation_statistic,
    )


@dataclass(frozen=True)
class StrongestBaselineSelection:
    dataset_id: str
    status: str
    method_id: str | None
    canonical_config_sha256: str | None
    validation_statistic: float | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "status": self.status,
            "method_id": self.method_id,
            "canonical_config_sha256": self.canonical_config_sha256,
            "validation_statistic": self.validation_statistic,
            "tie_break": "METHOD_ID_ASCENDING",
        }


def select_strongest_baseline(
    selections: Sequence[ConfigurationSelection],
) -> StrongestBaselineSelection:
    if not selections:
        raise ContractError("strongest baseline selection requires method selections")
    datasets = {row.dataset_id for row in selections}
    methods = {row.method_id for row in selections}
    if len(datasets) != 1 or len(methods) != len(selections):
        raise ContractError("baseline selections must have one dataset and unique methods")
    dataset = next(iter(datasets))
    if methods != MANDATORY_BASELINES or any(row.status != "SELECTED" for row in selections):
        return StrongestBaselineSelection(
            dataset_id=dataset,
            status="INCOMPLETE_MANDATORY_BASELINE_SELECTION",
            method_id=None,
            canonical_config_sha256=None,
            validation_statistic=None,
        )
    selected = min(
        selections,
        key=lambda row: (
            -float(row.validation_statistic) if row.validation_statistic is not None else math.inf,
            row.method_id,
        ),
    )
    if selected.selected_config_sha256 is None or selected.validation_statistic is None:
        raise IntegrityError("selected baseline lost its configuration binding")
    return StrongestBaselineSelection(
        dataset_id=dataset,
        status="SELECTED",
        method_id=selected.method_id,
        canonical_config_sha256=selected.selected_config_sha256,
        validation_statistic=selected.validation_statistic,
    )


def selected_surface_binding(
    *,
    dataset_id: str,
    method_id: str,
    canonical_config_sha256: str,
    outcome: SeedValidationOutcome,
) -> dict[str, object]:
    """Emit exactly the P2 selected-surface binding fields."""

    method = _nonempty(method_id, "method_id")
    if outcome.status != "PASS":
        raise ContractError("selected surface requires a PASS seed outcome")
    if not _is_sha256(canonical_config_sha256):
        raise ContractError("selected surface configuration hash is invalid")
    _validate_outcome_for_method(method, outcome)
    if outcome.validation_score_artifact_sha256 is None:
        raise IntegrityError("selected surface lost its score artifact hash")
    return {
        "dataset_id": _nonempty(dataset_id, "dataset_id"),
        "method_id": method,
        "canonical_config_sha256": canonical_config_sha256,
        "seed": outcome.seed,
        "selected_epoch_or_not_applicable": (
            outcome.selected_epoch if outcome.selected_epoch is not None else "NOT_APPLICABLE"
        ),
        "checkpoint_sha256_or_not_applicable": (
            outcome.checkpoint_sha256 if outcome.checkpoint_sha256 is not None else "NOT_APPLICABLE"
        ),
        "validation_score_artifact_sha256": outcome.validation_score_artifact_sha256,
    }


def comparison_seed_status(
    left: Sequence[SeedValidationOutcome],
    right: Sequence[SeedValidationOutcome],
    *,
    required_seeds: tuple[int, ...],
) -> str:
    """Fail closed when either paired method lacks a required completed seed."""

    if not required_seeds or len(set(required_seeds)) != len(required_seeds):
        raise ContractError("comparison required seeds must be unique and non-empty")
    if any(
        isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in required_seeds
    ):
        raise ContractError("comparison required seeds are invalid")

    def complete(rows: Sequence[SeedValidationOutcome]) -> bool:
        seeds = [row.seed for row in rows]
        if len(seeds) != len(set(seeds)) or set(seeds) != set(required_seeds):
            return False
        return all(row.status == "PASS" for row in rows)

    if complete(left) and complete(right):
        return "COMPLETE_PAIRED_SEEDS"
    return "COMPARISON_INCOMPLETE_NO_IMPUTATION_NO_REPLACEMENT"


__all__ = [
    "BASE_SEEDS",
    "EPOCH_METHODS",
    "EXTENDED_PRIMARY_SEEDS",
    "MANDATORY_BASELINES",
    "NON_EPOCH_METHODS",
    "CanonicalConfigurationBinding",
    "ConfigurationQualification",
    "ConfigurationSelection",
    "EpochCheckpointCandidate",
    "SeedValidationOutcome",
    "StrongestBaselineSelection",
    "canonical_configuration_payload",
    "comparison_seed_status",
    "qualify_configuration",
    "select_configuration",
    "select_epoch_checkpoint",
    "select_strongest_baseline",
    "selected_surface_binding",
    "write_canonical_configuration",
]
