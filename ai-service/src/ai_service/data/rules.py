"""Train-only Apriori mining and sparse CSR rule access."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import torch

from ai_service.config import Settings
from ai_service.contracts import RuleManifest
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


@dataclass(frozen=True)
class RuleArtifact:
    store: RuleStore
    manifest: RuleManifest
    artifact_dir: Path


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
        artifact_id = artifact_id or f"{snapshot.manifest.artifact_id}-rules-{checksum[:12]}"
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
        )
        destination = self.settings.data.artifact_root.resolve() / "rules" / artifact_id
        if destination.exists():
            raise ArtifactIntegrityError(f"immutable rule artifact exists: {destination}")
        destination.mkdir(parents=True)
        np.savez_compressed(
            destination / "rules.npz",
            crow_indices=store.crow_indices.numpy(),
            col_indices=store.col_indices.numpy(),
            values=store.values.numpy(),
            features=store.features.numpy(),
            raw_lifts=store.raw_lifts.numpy(),
            supports=store.supports.numpy(),
            confidences=store.confidences.numpy(),
            counts=store.counts.numpy(),
        )
        (destination / "manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
        )
        return RuleArtifact(store=store, manifest=manifest, artifact_dir=destination)


def load_rule_artifact(path: Path, num_items: int) -> RuleArtifact:
    manifest = RuleManifest.model_validate_json(
        (path / "manifest.json").read_text(encoding="utf-8")
    )
    arrays = np.load(path / "rules.npz")
    statistic_names = ("features", "raw_lifts", "supports", "confidences", "counts")
    names = ("crow_indices", "col_indices", "values") + (
        statistic_names if all(name in arrays for name in statistic_names) else ()
    )
    payload = b"".join(arrays[name].tobytes() for name in names)
    if hashlib.sha256(payload).hexdigest() != manifest.content_sha256:
        raise ArtifactIntegrityError("rule artifact checksum mismatch")
    rows = np.repeat(np.arange(num_items), np.diff(arrays["crow_indices"]))
    lifts = np.expm1(arrays["values"] * manifest.q99_log_lift)
    if "features" in arrays:
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
    store = RuleStore(num_items, pairs, q99_log_lift=manifest.q99_log_lift)
    return RuleArtifact(store=store, manifest=manifest, artifact_dir=path)
