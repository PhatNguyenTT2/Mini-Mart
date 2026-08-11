"""Train-only Apriori mining and sparse CSR rule access."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import torch

from ai_service.config import Settings
from ai_service.contracts import (
    RULE_COVERAGE_SEMANTICS_VERSION,
    RuleCoverageEvidence,
    RuleManifest,
)
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ArtifactIntegrityError, DataIntegrityError


class RuleStore:
    """Directed association-rule features backed by one sparse CSR index."""

    def __init__(
        self,
        num_items: int,
        rule_pairs: Sequence[tuple[int, int, float] | tuple[int, int, float, float, float, int]],
        *,
        min_lift: float = 1.0,
        q99_log_lift: float | None = None,
    ) -> None:
        records: list[tuple[int, int, float, float, float, int]] = []
        for rule in rule_pairs:
            if len(rule) == 3:
                row, column, lift = rule
                support, confidence, count = 0.0, 0.0, 1
            else:
                row, column, lift, support, confidence, count = rule
            record = (
                int(row),
                int(column),
                float(lift),
                float(support),
                float(confidence),
                int(count),
            )
            if record[2] >= min_lift:
                records.append(record)
        filtered = sorted(records)
        if any(
            row < 0 or column < 0 or row >= num_items or column >= num_items
            for row, column, *_ in filtered
        ):
            raise DataIntegrityError("rule index is outside catalog bounds")
        if any(
            not np.isfinite([lift, support, confidence]).all()
            or lift < 0
            or not 0 <= support <= 1
            or not 0 <= confidence <= 1
            or count < 1
            for _, _, lift, support, confidence, count in filtered
        ):
            raise DataIntegrityError("rule statistics are outside valid bounds")
        coordinates = [(row, column) for row, column, *_ in filtered]
        if len(coordinates) != len(set(coordinates)):
            raise DataIntegrityError("rule coordinates must be unique")
        log_values = np.log1p([lift for _, _, lift, *_ in filtered]).astype(np.float32)
        scale = float(q99_log_lift or (np.quantile(log_values, 0.99) if log_values.size else 1.0))
        if not np.isfinite(scale) or scale <= 0:
            scale = 1.0
        normalized = np.clip(log_values / scale, 0.0, 1.0).astype(np.float32)
        counts = np.zeros(num_items, dtype=np.int64)
        for row, *_ in filtered:
            counts[row] += 1
        crow = np.concatenate(([0], np.cumsum(counts))).astype(np.int64)
        self.num_items = num_items
        self.q99_log_lift = scale
        self.crow_indices = torch.from_numpy(crow).contiguous()
        # ``torch.from_numpy(np.asarray([]))`` has stride ``(0,)``.  PyTorch
        # 2.11 rejects that representation for an otherwise valid empty CSR
        # matrix, so construct the two variable-length arrays directly.
        self.col_indices = torch.tensor([column for _, column, *_ in filtered], dtype=torch.int64)
        self.values = torch.tensor(normalized.tolist(), dtype=torch.float32)
        self.features = torch.tensor(
            [
                [np.log1p(lift), confidence, np.log1p(count)]
                for _, _, lift, _, confidence, count in filtered
            ],
            dtype=torch.float32,
        ).reshape(-1, 3)
        self.raw_lifts = torch.tensor([lift for _, _, lift, *_ in filtered], dtype=torch.float32)
        self.supports = torch.tensor(
            [support for _, _, _, support, _, _ in filtered], dtype=torch.float32
        )
        self.confidences = torch.tensor(
            [confidence for _, _, _, _, confidence, _ in filtered], dtype=torch.float32
        )
        self.counts = torch.tensor([count for _, _, _, _, _, count in filtered], dtype=torch.int64)
        with torch.sparse.check_sparse_tensor_invariants():  # type: ignore[no-untyped-call]
            self.csr = torch.sparse_csr_tensor(
                self.crow_indices,
                self.col_indices,
                self.values,
                size=(num_items, num_items),
                dtype=torch.float32,
            )

    def lookup(self, context_item_idx: int, candidate_item_idx: int) -> float:
        if context_item_idx < 0:
            return 0.0
        start = int(self.crow_indices[context_item_idx])
        end = int(self.crow_indices[context_item_idx + 1])
        columns = self.col_indices[start:end].numpy()
        position = int(np.searchsorted(columns, candidate_item_idx))
        if position >= len(columns) or int(columns[position]) != candidate_item_idx:
            return 0.0
        return float(self.values[start + position])

    def batch_lookup(
        self, context_indices: np.ndarray, candidate_indices: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        if candidate_indices.ndim != 2 or len(context_indices) != len(candidate_indices):
            raise DataIntegrityError("rule lookup shapes must be [B] and [B,C]")
        output = np.zeros((*candidate_indices.shape, 3), dtype=np.float32)
        present = np.zeros(candidate_indices.shape, dtype=np.bool_)
        for batch_index, context in enumerate(context_indices.astype(np.int64)):
            if context < 0:
                continue
            start = int(self.crow_indices[context])
            end = int(self.crow_indices[context + 1])
            row_columns = self.col_indices[start:end].numpy()
            row_values = self.features[start:end].numpy()
            positions = np.searchsorted(row_columns, candidate_indices[batch_index])
            valid = positions < len(row_columns)
            matched = np.zeros_like(valid)
            matched[valid] = row_columns[positions[valid]] == candidate_indices[batch_index, valid]
            present[batch_index] = matched
            output[batch_index, matched] = row_values[positions[matched]]
        return output, present

    def batch_raw_lift(
        self, context_indices: np.ndarray, candidate_indices: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        if candidate_indices.ndim != 2 or len(context_indices) != len(candidate_indices):
            raise DataIntegrityError("rule lookup shapes must be [B] and [B,C]")
        lifts = np.zeros(candidate_indices.shape, dtype=np.float32)
        present = np.zeros(candidate_indices.shape, dtype=np.bool_)
        for batch_index, context in enumerate(context_indices.astype(np.int64)):
            if context < 0:
                continue
            start = int(self.crow_indices[context])
            end = int(self.crow_indices[context + 1])
            columns = self.col_indices[start:end].numpy()
            positions = np.searchsorted(columns, candidate_indices[batch_index])
            valid = positions < len(columns)
            matched = np.zeros_like(valid)
            matched[valid] = columns[positions[valid]] == candidate_indices[batch_index, valid]
            present[batch_index] = matched
            matched_positions = positions[matched]
            lifts[batch_index, matched] = self.raw_lifts[start:end].numpy()[matched_positions]
        return lifts, present


def _build_rule_coverage(
    snapshot: Snapshot,
    rules: Sequence[tuple[int, int, float, float, float, int]],
) -> RuleCoverageEvidence:
    """Derive organic/trap rule coverage from immutable snapshot evidence."""
    events = np.concatenate(
        [
            snapshot.train_df.internal_product_id.to_numpy(np.int64),
            snapshot.val_df.internal_product_id.to_numpy(np.int64),
            snapshot.test_df.internal_product_id.to_numpy(np.int64),
        ]
    )
    origin_frames = []
    for frame in (snapshot.train_df, snapshot.val_df, snapshot.test_df):
        if "event_origin" in frame:
            origin_frames.append(frame.event_origin.astype(str).to_numpy())
        else:
            origin_frames.append(np.full(len(frame), "organic", dtype=object))
    origins = np.concatenate(origin_frames)
    fixture_items = set(int(value) for value in events[origins == "semantic_trap"])
    organic_rules = [
        rule
        for rule in rules
        if int(rule[0]) not in fixture_items and int(rule[1]) not in fixture_items
    ]
    trap_rules = [rule for rule in rules if rule not in organic_rules]
    organic_items = {int(value) for rule in organic_rules for value in rule[:2]}
    train = snapshot.train_df
    organic_train = train[train.event_type.astype(str) == "purchase"]
    if "event_origin" in organic_train:
        organic_train = organic_train[organic_train.event_origin.astype(str) == "organic"]
    latest = organic_train.sort_values(["event_ts", "event_id"], kind="stable").drop_duplicates(
        "internal_user_id", keep="last"
    )
    organic_val = snapshot.val_df[snapshot.val_df.event_type.astype(str) == "purchase"]
    if "event_origin" in organic_val:
        organic_val = organic_val[organic_val.event_origin.astype(str) == "organic"]
    seen = organic_train.groupby("internal_user_id").internal_product_id.apply(set).to_dict()
    eligible = {
        int(str(user)): group.internal_product_id.astype(int)
        .isin(set(seen.get(int(str(user)), set())))
        .eq(False)
        .any()
        for user, group in organic_val.groupby("internal_user_id")
    }
    eligible_users = {user for user, is_eligible in eligible.items() if is_eligible}
    rule_sources = {int(rule[0]) for rule in organic_rules}
    latest_eligible = latest[latest.internal_user_id.isin(eligible_users)]
    covered = int(latest_eligible.internal_product_id.astype(int).isin(rule_sources).sum())
    total_directed = len(rules)
    non_trap_directed = len(organic_rules)
    trap_directed = len(trap_rules)
    warm_count = max(1, snapshot.manifest.num_items - len(snapshot.cold_item_ids))
    return RuleCoverageEvidence(
        total_directed_rules=total_directed,
        non_trap_directed_rules=non_trap_directed,
        trap_anchored_directed_rules=trap_directed,
        trap_anchored_rule_fraction=trap_directed / max(1, total_directed),
        distinct_organic_rule_items=len(organic_items),
        eligible_val_context_users=len(eligible_users),
        val_context_users_with_rule=covered,
        val_context_rule_coverage=covered / max(1, len(eligible_users)),
        full_catalog_organic_pair_coverage=non_trap_directed
        / max(1, warm_count * (warm_count - 1)),
    )


@dataclass(frozen=True)
class RuleArtifact:
    store: RuleStore
    manifest: RuleManifest
    artifact_dir: Path

    def require_training_capability(self, settings: Settings | None = None) -> RuleStore:
        if not getattr(self.manifest, "has_full_statistics", False):
            raise ArtifactIntegrityError(
                "rule artifact missing full statistics required for training"
            )
        if settings is not None and settings.data.rule_feature_schema_version == "3.0.0":
            coverage = self.manifest.coverage
            if (
                self.manifest.feature_schema_version != "3.0.0"
                or self.manifest.coverage_semantics_version != RULE_COVERAGE_SEMANTICS_VERSION
                or coverage is None
            ):
                raise ArtifactIntegrityError(
                    "rule artifact missing organic coverage evidence required for training"
                )
            if coverage.non_trap_directed_rules < settings.data.minimum_non_trap_directed_rules:
                raise ArtifactIntegrityError("non-trap rule coverage is below training threshold")
            if (
                coverage.distinct_organic_rule_items
                < settings.data.minimum_distinct_organic_rule_items
            ):
                raise ArtifactIntegrityError(
                    "distinct organic rule coverage is below training threshold"
                )
            if coverage.val_context_rule_coverage < settings.data.minimum_val_context_rule_coverage:
                raise ArtifactIntegrityError(
                    "VAL context rule coverage is below training threshold"
                )
            if (
                coverage.trap_anchored_rule_fraction
                > settings.data.maximum_trap_anchored_rule_fraction
            ):
                raise ArtifactIntegrityError(
                    "trap-anchored rule fraction exceeds training threshold"
                )
        return self.store


class AprioriRuleMiner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def mine(self, snapshot: Snapshot, artifact_id: str | None = None) -> RuleArtifact:
        orders = snapshot.order_baskets_df
        cold = set(snapshot.cold_item_ids)
        if cold & set(orders.internal_product_id.astype(int)):
            raise DataIntegrityError("cold item exists in train rule universe")
        baskets = orders.groupby("order_id").internal_product_id.apply(
            lambda values: tuple(sorted(set(int(value) for value in values)))
        )
        item_counts: Counter[int] = Counter()
        pair_counts: Counter[tuple[int, int]] = Counter()
        for basket in baskets:
            item_counts.update(basket)
            for left, right in combinations(basket, 2):
                pair_counts[(left, right)] += 1
                pair_counts[(right, left)] += 1
        basket_count = len(baskets)
        rules: list[tuple[int, int, float, float, float, int]] = []
        for (left, right), count in pair_counts.items():
            if count < self.settings.data.min_rule_count:
                continue
            lift = count * basket_count / (item_counts[left] * item_counts[right])
            if lift >= self.settings.data.min_rule_lift:
                rules.append(
                    (
                        left,
                        right,
                        float(lift),
                        count / basket_count,
                        count / item_counts[left],
                        count,
                    )
                )
        store = RuleStore(
            snapshot.manifest.num_items,
            rules,
            min_lift=self.settings.data.min_rule_lift,
        )
        payload = b"".join(
            (
                store.crow_indices.numpy().tobytes(),
                store.col_indices.numpy().tobytes(),
                store.values.numpy().tobytes(),
                store.features.numpy().tobytes(),
                store.raw_lifts.numpy().tobytes(),
                store.supports.numpy().tobytes(),
                store.confidences.numpy().tobytes(),
                store.counts.numpy().tobytes(),
            )
        )
        checksum = hashlib.sha256(payload).hexdigest()
        coverage = None
        feature_schema_version = self.settings.data.rule_feature_schema_version
        if feature_schema_version == "3.0.0":
            coverage = _build_rule_coverage(snapshot, rules)
        identity = hashlib.sha256(
            json.dumps(
                {
                    "artifact_kind": "rule-v3-organic-coverage"
                    if feature_schema_version == "3.0.0"
                    else "rule-v2-fullstats",
                    "snapshot_sha256": snapshot.manifest.content_sha256,
                    "content_sha256": checksum,
                    "feature_schema_version": feature_schema_version,
                    "has_full_statistics": True,
                    "min_count": self.settings.data.min_rule_count,
                    "min_lift": self.settings.data.min_rule_lift,
                    "coverage_semantics_version": RULE_COVERAGE_SEMANTICS_VERSION
                    if coverage is not None
                    else None,
                    "coverage": coverage.model_dump(mode="json") if coverage is not None else None,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        artifact_id = artifact_id or (
            f"{snapshot.manifest.artifact_id}-rules-v3-{identity[:12]}"
            if feature_schema_version == "3.0.0"
            else f"{snapshot.manifest.artifact_id}-rules-v2-{identity[:12]}"
        )
        manifest = RuleManifest(
            artifact_id=artifact_id,
            content_sha256=checksum,
            parent_sha256={"snapshot": snapshot.manifest.content_sha256},
            snapshot_sha256=snapshot.manifest.content_sha256,
            num_directed_rules=int(store.values.numel()),
            train_basket_count=basket_count,
            min_count=self.settings.data.min_rule_count,
            min_lift=self.settings.data.min_rule_lift,
            q99_log_lift=store.q99_log_lift,
            feature_schema_version=feature_schema_version,
            has_full_statistics=True,
            coverage_semantics_version=RULE_COVERAGE_SEMANTICS_VERSION
            if coverage is not None
            else None,
            coverage=coverage,
        )
        destination = self.settings.data.artifact_root.resolve() / "rules" / artifact_id
        if destination.exists():
            raise ArtifactIntegrityError(f"immutable rule artifact exists: {destination}")
        root = destination.parent
        root.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{artifact_id}-", dir=root))
        try:
            np.savez_compressed(
                temporary / "rules.npz",
                crow_indices=store.crow_indices.numpy(),
                col_indices=store.col_indices.numpy(),
                values=store.values.numpy(),
                features=store.features.numpy(),
                raw_lifts=store.raw_lifts.numpy(),
                supports=store.supports.numpy(),
                confidences=store.confidences.numpy(),
                counts=store.counts.numpy(),
            )
            for filename in ("rules.npz",):
                with (temporary / filename).open("r+b") as handle:
                    os.fsync(handle.fileno())
            manifest_path = temporary / "manifest.json"
            with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(manifest.model_dump(mode="json"), handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            # Validate the complete temporary artifact before exposing it.
            load_rule_artifact(temporary, snapshot.manifest.num_items)
            if destination.exists():
                raise ArtifactIntegrityError(f"immutable rule artifact exists: {destination}")
            os.replace(temporary, destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return RuleArtifact(store=store, manifest=manifest, artifact_dir=destination)


def load_rule_artifact(path: Path, num_items: int) -> RuleArtifact:
    try:
        manifest = RuleManifest.model_validate_json(
            (path / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("rule manifest cannot be loaded") from error
    if set(manifest.parent_sha256) != {"snapshot"}:
        raise ArtifactIntegrityError("rule manifest lineage is incomplete")
    if manifest.parent_sha256.get("snapshot") != manifest.snapshot_sha256:
        raise ArtifactIntegrityError("rule manifest snapshot lineage mismatch")
    if manifest.num_directed_rules < 0 or manifest.train_basket_count < 0:
        raise ArtifactIntegrityError("rule manifest counts are invalid")
    if manifest.feature_schema_version == "3.0.0":
        coverage = manifest.coverage
        if coverage is None or coverage.total_directed_rules != manifest.num_directed_rules:
            raise ArtifactIntegrityError("v3 rule coverage evidence is missing or inconsistent")
        if coverage.trap_anchored_directed_rules + coverage.non_trap_directed_rules != (
            manifest.num_directed_rules
        ):
            raise ArtifactIntegrityError("v3 rule coverage rule counts are inconsistent")
    if not np.isfinite(manifest.q99_log_lift) or manifest.q99_log_lift <= 0:
        raise ArtifactIntegrityError("rule q99_log_lift is invalid")
    try:
        arrays = np.load(path / "rules.npz", allow_pickle=False)
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError("rule arrays cannot be loaded") from error
    with arrays:
        base_arrays = {"crow_indices", "col_indices", "values"}
        full_arrays = {
            "crow_indices",
            "col_indices",
            "values",
            "features",
            "raw_lifts",
            "supports",
            "confidences",
            "counts",
        }
        payload_has_full_statistics = set(arrays.files) == full_arrays
        expected = full_arrays if manifest.has_full_statistics else base_arrays
        if set(arrays.files) != expected and not (
            not manifest.has_full_statistics and payload_has_full_statistics
        ):
            raise ArtifactIntegrityError("rule artifact arrays do not match manifest capability")
        if arrays["crow_indices"].dtype != np.int64 or arrays["col_indices"].dtype != np.int64:
            raise ArtifactIntegrityError("rule CSR index arrays have invalid dtype")
        if arrays["values"].dtype != np.float32 or not np.isfinite(arrays["values"]).all():
            raise ArtifactIntegrityError("rule CSR values are invalid")
        if len(arrays["crow_indices"]) != num_items + 1:
            raise ArtifactIntegrityError("rule CSR row pointer length mismatch")
        if (
            arrays["crow_indices"][0] != 0
            or np.any(np.diff(arrays["crow_indices"]) < 0)
            or arrays["crow_indices"][-1] != manifest.num_directed_rules
        ):
            raise ArtifactIntegrityError("rule CSR row pointers are invalid")
        nnz = manifest.num_directed_rules
        if (
            len(arrays["col_indices"]) != nnz
            or np.any(arrays["col_indices"] < 0)
            or np.any(arrays["col_indices"] >= num_items)
        ):
            raise ArtifactIntegrityError("rule CSR columns or length are invalid")
        if manifest.has_full_statistics or payload_has_full_statistics:
            for name in ("features", "raw_lifts", "supports", "confidences"):
                values = arrays[name]
                if (
                    values.dtype != np.float32
                    or len(values) != nnz
                    or (name == "features" and values.shape != (nnz, 3))
                    or not np.isfinite(values).all()
                ):
                    raise ArtifactIntegrityError(f"rule statistics are invalid: {name}")
            if (
                np.any(arrays["raw_lifts"] < 0)
                or np.any(arrays["supports"] < 0)
                or np.any(arrays["supports"] > 1)
                or np.any(arrays["confidences"] < 0)
                or np.any(arrays["confidences"] > 1)
            ):
                raise ArtifactIntegrityError("rule statistics are outside valid ranges")
            if (
                arrays["counts"].dtype != np.int64
                or len(arrays["counts"]) != nnz
                or np.any(arrays["counts"] < 1)
            ):
                raise ArtifactIntegrityError("rule counts are invalid")
        base_names = ("crow_indices", "col_indices", "values")
        full_names = (
            "crow_indices",
            "col_indices",
            "values",
            "features",
            "raw_lifts",
            "supports",
            "confidences",
            "counts",
        )
        payload = b"".join(
            arrays[name].tobytes()
            for name in (full_names if manifest.has_full_statistics else base_names)
        )
        payload_hash = hashlib.sha256(payload).hexdigest()
        legacy_full_hash = hashlib.sha256(
            b"".join(arrays[name].tobytes() for name in full_names)
        ).hexdigest()
        if payload_hash != manifest.content_sha256 and not (
            not manifest.has_full_statistics
            and payload_has_full_statistics
            and legacy_full_hash == manifest.content_sha256
        ):
            raise ArtifactIntegrityError("rule artifact checksum mismatch")
        rows = np.repeat(np.arange(num_items), np.diff(arrays["crow_indices"]))
        lifts = np.expm1(arrays["values"] * manifest.q99_log_lift)
        try:
            if manifest.has_full_statistics or payload_has_full_statistics:
                pairs = list(
                    zip(
                        rows.tolist(),
                        arrays["col_indices"].tolist(),
                        arrays["raw_lifts"].tolist(),
                        arrays["supports"].tolist(),
                        arrays["confidences"].tolist(),
                        arrays["counts"].tolist(),
                        strict=True,
                    )
                )
            else:
                pairs = list(
                    zip(rows.tolist(), arrays["col_indices"].tolist(), lifts.tolist(), strict=True)
                )
        except ValueError as error:
            raise ArtifactIntegrityError("rule CSR arrays have inconsistent lengths") from error
    try:
        store = RuleStore(num_items, pairs, q99_log_lift=manifest.q99_log_lift)
    except (DataIntegrityError, ValueError) as error:
        raise ArtifactIntegrityError("rule artifact statistics are inconsistent") from error
    return RuleArtifact(store=store, manifest=manifest, artifact_dir=path)
