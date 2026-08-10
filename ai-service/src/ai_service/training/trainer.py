"""Fail-fast optimization lifecycle for the hybrid model."""

from __future__ import annotations

import ctypes
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import torch
from torch import nn
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import ModelVariant, SplitName
from ai_service.data.dataset import PurchaseBatch, PurchaseBatchIterator, TrainingBatch
from ai_service.data.history import build_user_profile_vectors
from ai_service.data.snapshot import Snapshot
from ai_service.errors import ModelTrainingError
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.objectives import multi_positive_sampled_softmax


class ValidationEvaluator(Protocol):
    def evaluate(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        *,
        split: SplitName,
        k: int,
        variant: ModelVariant,
        device: torch.device,
    ) -> Any: ...


@dataclass(frozen=True)
class EpochMetrics:
    epoch: int
    global_step: int
    train_loss: float
    purchase_loss: float
    view_loss: float
    wide_loss: float
    val_gauc: float
    val_hr_at_k: float
    val_ndcg_at_k: float
    val_deep_gauc: float
    val_deep_ndcg_at_k: float
    val_wide_gauc: float
    val_wide_ndcg_at_k: float
    checkpoint_guardrails_passed: bool
    learning_rate: float
    sampled_pair_accuracy: float
    all_negative_win_rate: float
    margin_p10: float
    margin_p50: float
    margin_p90: float
    gradient_norm: float
    user_tower_gradient_norm: float
    item_tower_gradient_norm: float
    wide_gradient_norm: float
    positive_logit_p10: float
    positive_logit_p50: float
    positive_logit_p90: float
    negative_logit_p10: float
    negative_logit_p50: float
    negative_logit_p90: float
    rule_present_rate: float
    elapsed_seconds: float
    peak_ram_bytes: int
    peak_vram_bytes: int
    gpu_utilization_median: float
    data_wait_ratio: float
    is_best: bool
    early_peak_warning: bool


@dataclass(frozen=True)
class TrainResult:
    run_id: str
    best_epoch: int
    best_gauc: float
    best_ndcg_at_k: float
    history: tuple[EpochMetrics, ...]
    checkpoint_path: Path
    stop_reason: str


def _settings_sha256(settings: Settings) -> str:
    return settings.training_signature_sha256()


def _peak_resident_bytes() -> int:
    if platform.system() == "Windows":

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        succeeded = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        )
        return int(counters.PeakWorkingSetSize) if succeeded else 0
    try:
        import resource  # noqa: PLC0415

        getrusage = cast(Any, getattr(resource, "getrusage"))  # noqa: B009
        usage_self = cast(Any, getattr(resource, "RUSAGE_SELF"))  # noqa: B009
        value = int(getrusage(usage_self).ru_maxrss)
        return value if sys.platform == "darwin" else value * 1_024
    except (ImportError, OSError):
        return 0


def _module_gradient_norm(module: nn.Module) -> float:
    squares = [
        parameter.grad.detach().float().pow(2).sum()
        for parameter in module.parameters()
        if parameter.grad is not None
    ]
    return float(torch.sqrt(torch.stack(squares).sum()).cpu()) if squares else 0.0


class Trainer:
    def __init__(
        self,
        model: HybridTwoTowerModel,
        *,
        settings: Settings,
        run_dir: Path,
        device: str | torch.device | None = None,
    ) -> None:
        self.settings = settings
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = model.to(self.device)
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.optimizer = AdamW(
            self.model.parameters(),
            lr=settings.train.learning_rate,
            weight_decay=settings.train.weight_decay,
        )
        self.scheduler: LambdaLR | None = None
        self.loss_function = nn.BCEWithLogitsLoss(reduction="none")

    def _build_scheduler(self, steps_per_epoch: int) -> LambdaLR:
        total_steps = max(1, steps_per_epoch * self.settings.train.max_epochs)
        warmup_steps = int(total_steps * self.settings.train.warmup_fraction)
        minimum_factor = (
            self.settings.train.minimum_learning_rate / self.settings.train.learning_rate
        )

        def multiplier(step: int) -> float:
            if warmup_steps and step < warmup_steps:
                return max((step + 1) / warmup_steps, minimum_factor)
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
            progress = min(max(progress, 0.0), 1.0)
            cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
            return minimum_factor + (1.0 - minimum_factor) * cosine

        return LambdaLR(self.optimizer, multiplier)

    def _append_history(self, metrics: EpochMetrics) -> None:
        path = self.run_dir / "training" / "history.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as destination:
            destination.write(json.dumps(asdict(metrics), sort_keys=True) + "\n")
            destination.flush()
            os.fsync(destination.fileno())

    @torch.no_grad()
    def _refresh_model_hard_cache(
        self,
        train_loader: object,
        snapshot: Snapshot,
        item_vectors: torch.Tensor,
    ) -> None:
        if not isinstance(train_loader, PurchaseBatchIterator):
            return
        index = train_loader.index
        profiles = build_user_profile_vectors(
            self.model,
            snapshot,
            item_vectors,
            snapshot.train_df,
            max_history_items=self.settings.train.max_history_items,
            device=self.device,
        )
        if not self.settings.train.use_history_profiles:
            profiles.zero_()
        personas = np.full(
            snapshot.manifest.num_users + 1,
            self.settings.data.num_personas,
            dtype=np.int64,
        )
        for internal_user, raw_user in snapshot.raw_user_map.items():
            personas[int(internal_user)] = int(
                snapshot.persona_map.get(raw_user, self.settings.data.num_personas)
            )
        cache_width = min(64, snapshot.manifest.num_items - len(snapshot.cold_item_ids))
        cache = np.zeros((snapshot.manifest.num_users + 1, cache_width), dtype=np.int32)
        cold = np.zeros(snapshot.manifest.num_items, dtype=np.bool_)
        cold[np.asarray(snapshot.cold_item_ids, dtype=np.int64)] = True
        for offset in range(1, snapshot.manifest.num_users + 1, 512):
            users = np.arange(
                offset,
                min(offset + 512, snapshot.manifest.num_users + 1),
                dtype=np.int64,
            )
            user_tensor = torch.from_numpy(users).to(self.device)
            profile_batch = profiles[user_tensor]
            user_vectors = self.model.encode_user(
                user_tensor,
                torch.from_numpy(personas[users]).to(self.device),
                history_vector=profile_batch,
                history_present=torch.linalg.vector_norm(profile_batch, dim=-1) > 0,
            )
            scores = torch.matmul(user_vectors, item_vectors.T) / self.model._temperature
            invalid = index.known_history[users] | cold[None, :]
            scores.masked_fill_(torch.from_numpy(invalid).to(self.device), -torch.inf)
            if bool(torch.isneginf(scores).all(dim=1).any()):
                raise ModelTrainingError("model-hard negative pool is exhausted")
            cache[users] = torch.topk(scores, k=cache_width, dim=1).indices.cpu().numpy()
        train_loader.sampler.update_model_hard_cache(cache)

    def fit(
        self,
        train_loader: Any,
        snapshot: Snapshot,
        embeddings: np.ndarray,
        val_evaluator: ValidationEvaluator | None,
        lineage: dict[str, str],
        *,
        resume_from: Path | None = None,
    ) -> TrainResult:
        if val_evaluator is None:
            raise ModelTrainingError("validation evaluator is mandatory")
        required_lineage = {"snapshot", "embedding", "rules"}
        if set(lineage) != required_lineage:
            raise ModelTrainingError("training lineage must contain snapshot, embedding, and rules")
        if embeddings is None or embeddings.shape != (
            snapshot.manifest.num_items,
            self.settings.model.sbert_dim,
        ):
            raise ModelTrainingError("SBERT artifact is missing or has the wrong shape")
        if not np.isfinite(embeddings).all():
            raise ModelTrainingError("SBERT artifact contains NaN or Inf")

        catalog = snapshot.catalog_df.sort_values("internal_product_id", kind="stable")
        sbert_catalog = torch.from_numpy(np.array(embeddings, dtype=np.float32, copy=True)).to(
            self.device
        )
        category_catalog = torch.from_numpy(
            catalog.internal_leaf_category_id.to_numpy(np.int64)
        ).to(self.device)
        price_catalog = torch.from_numpy(catalog.price_bucket_id.to_numpy(np.int64)).to(self.device)
        cold_catalog = torch.zeros(
            snapshot.manifest.num_items, dtype=torch.bool, device=self.device
        )
        if snapshot.cold_item_ids:
            cold_catalog[
                torch.tensor(snapshot.cold_item_ids, dtype=torch.int64, device=self.device)
            ] = True
        persona_by_internal = np.full(
            snapshot.manifest.num_users + 1,
            self.settings.data.num_personas,
            dtype=np.int64,
        )
        for internal_user, raw_user in snapshot.raw_user_map.items():
            persona_by_internal[int(internal_user)] = int(
                snapshot.persona_map.get(raw_user, self.settings.data.num_personas)
            )
        best_gauc = float("-inf")
        best_ndcg = float("-inf")
        best_epoch = 0
        no_improvement = 0
        history: list[EpochMetrics] = []
        pareto_frontier: list[tuple[float, float, float, Path]] = []
        best_path = self.run_dir / "checkpoints" / "best.pt"
        config_sha = _settings_sha256(self.settings)
        run_id = self.run_dir.name
        amp_enabled = self.device.type == "cuda"
        scaler = GradScaler("cuda", enabled=amp_enabled)
        self.scheduler = self._build_scheduler(len(train_loader))
        global_step = 0
        stop_reason = "max_epochs"
        started_training = time.perf_counter()
        start_epoch = 1
        if resume_from is not None:
            if resume_from.resolve() != (self.run_dir / "checkpoints" / "last.pt").resolve():
                raise ModelTrainingError("resume must use this run's last.pt checkpoint")
            state = CheckpointManager.load(
                resume_from,
                model=self.model,
                optimizer=self.optimizer,
                scheduler=self.scheduler,
                scaler=scaler,
                expected_lineage=lineage,
                expected_training_signature=config_sha,
                expected_model_schema_version=MODEL_SCHEMA_VERSION,
                restore_rng=True,
            )
            start_epoch = int(state["epoch"]) + 1
            history_path = self.run_dir / "training" / "history.jsonl"
            if not history_path.is_file():
                raise ModelTrainingError("resume checkpoint has no durable training history")
            history = [
                EpochMetrics(**json.loads(line))
                for line in history_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if not history or history[-1].epoch != int(state["epoch"]):
                raise ModelTrainingError("resume history and checkpoint epochs differ")
            best_rows = [row for row in history if row.is_best]
            if not best_rows:
                # Runs created before diagnostic/release checkpoint separation
                # may have no guardrail-qualified best.  The loaded last.pt is
                # still an exact resumable model and becomes the bootstrap best.
                best_row = history[-1]
                CheckpointManager.save(
                    best_path,
                    model=self.model,
                    optimizer=self.optimizer,
                    scheduler=self.scheduler,
                    epoch=best_row.epoch,
                    metrics={
                        "val_gauc": best_row.val_gauc,
                        "val_ndcg_at_k": best_row.val_ndcg_at_k,
                        "train_loss": best_row.train_loss,
                    },
                    lineage=lineage,
                    training_signature_sha256=config_sha,
                    model_schema_version=MODEL_SCHEMA_VERSION,
                    run_id=run_id,
                    scaler=scaler,
                )
            else:
                if not best_path.is_file():
                    raise ModelTrainingError("resume history references a missing best checkpoint")
                best_row = best_rows[-1]
            best_epoch = best_row.epoch
            best_gauc = best_row.val_gauc
            best_ndcg = best_row.val_ndcg_at_k
            no_improvement = history[-1].epoch - best_epoch
            global_step = history[-1].global_step
            started_training -= history[-1].elapsed_seconds
            if start_epoch > self.settings.train.max_epochs:
                stop_reason = "already_complete"
            for row in history:
                pareto_path = self.run_dir / "checkpoints" / "pareto" / f"epoch-{row.epoch:03d}.pt"
                if row.checkpoint_guardrails_passed and pareto_path.is_file():
                    pareto_frontier.append(
                        (row.val_ndcg_at_k, row.val_gauc, row.val_hr_at_k, pareto_path)
                    )
        if amp_enabled:
            torch.cuda.reset_peak_memory_stats(self.device)

        for epoch in range(start_epoch, self.settings.train.max_epochs + 1):
            self.model.train()
            if hasattr(train_loader, "set_epoch"):
                train_loader.set_epoch(epoch)
            dataset = getattr(train_loader, "dataset", None)
            if dataset is not None and hasattr(dataset, "set_epoch"):
                dataset.set_epoch(epoch)
            weighted_loss_sum = 0.0
            sample_count = 0
            purchase_loss_sum = 0.0
            purchase_weight = 0.0
            view_loss_sum = 0.0
            view_weight = 0.0
            pair_correct = 0.0
            all_negative_wins = 0
            candidate_pairs = 0
            margins: list[np.ndarray] = []
            positive_logits: list[np.ndarray] = []
            negative_logits: list[np.ndarray] = []
            present_count = 0
            candidate_count = 0
            epoch_gradient_norm = 0.0
            user_gradient_norm = 0.0
            item_gradient_norm = 0.0
            wide_gradient_norm = 0.0
            data_wait_seconds = 0.0
            epoch_started = time.perf_counter()
            previous_batch_finished = epoch_started
            gpu_utilization: list[float] = []
            for batch in train_loader:
                data_wait_seconds += time.perf_counter() - previous_batch_finished
                self.optimizer.zero_grad(set_to_none=True)
                if isinstance(batch, PurchaseBatch):
                    if self.settings.train.objective != "sampled_softmax":
                        raise ModelTrainingError(
                            "purchase batches require the sampled_softmax objective"
                        )
                    users = batch.user_idx.to(self.device)
                    personas = batch.persona_idx.to(self.device)
                    positive_ids = batch.positive_item_idx.to(self.device)
                    negative_ids = batch.explicit_negative_idx.to(self.device)
                    history_ids = batch.history_item_idx.to(self.device)
                    history_mask = batch.history_mask.to(self.device)
                    history_age_days = batch.history_age_days.to(self.device)
                    positive_mask = batch.positive_mask.to(self.device)
                    denominator_mask = batch.denominator_mask.to(self.device)
                    confidence = batch.confidence.to(self.device)
                    with autocast(device_type=self.device.type, enabled=amp_enabled):
                        positive_vectors = self.model.encode_items(
                            sbert_catalog[positive_ids],
                            category_catalog[positive_ids],
                            price_catalog[positive_ids],
                            item_idx=positive_ids,
                            is_cold=cold_catalog[positive_ids],
                        )
                        negative_vectors = self.model.encode_items(
                            sbert_catalog[negative_ids],
                            category_catalog[negative_ids],
                            price_catalog[negative_ids],
                            item_idx=negative_ids,
                            is_cold=cold_catalog[negative_ids],
                        )
                        safe_history_ids = history_ids.clamp_min(0)
                        history_item_vectors = self.model.encode_items(
                            sbert_catalog[safe_history_ids],
                            category_catalog[safe_history_ids],
                            price_catalog[safe_history_ids],
                            item_idx=safe_history_ids,
                            is_cold=cold_catalog[safe_history_ids],
                        )
                        if self.settings.train.use_history_profiles:
                            history_vector, history_present = self.model.encode_history(
                                history_item_vectors,
                                history_mask,
                                history_age_days,
                            )
                        else:
                            history_vector = torch.zeros(
                                (len(users), self.settings.model.item_emb_dim),
                                dtype=history_item_vectors.dtype,
                                device=self.device,
                            )
                            history_present = torch.zeros(
                                len(users), dtype=torch.bool, device=self.device
                            )
                        user_vectors = self.model.encode_user(
                            users,
                            personas,
                            history_vector=history_vector,
                            history_present=history_present,
                        )
                        objective = multi_positive_sampled_softmax(
                            user_vectors,
                            positive_vectors,
                            negative_vectors,
                            positive_mask=positive_mask,
                            denominator_mask=denominator_mask,
                            confidence=confidence,
                            temperature=self.model._temperature,
                        )
                        purchase_objective_loss = objective.loss
                        auxiliary_view_loss = torch.zeros((), device=self.device)
                        if self.settings.train.view_auxiliary_weight > 0 and len(
                            train_loader.index.view_only_pairs
                        ):
                            view_pairs = train_loader.index.view_only_pairs
                            auxiliary_rng = np.random.default_rng(
                                np.random.SeedSequence(
                                    [self.settings.train.seed, epoch, global_step, 17]
                                )
                            )
                            selected_views = auxiliary_rng.choice(
                                len(view_pairs),
                                size=len(users),
                                replace=len(view_pairs) < len(users),
                            )
                            view_users_np = view_pairs[selected_views, 0]
                            view_items_np = view_pairs[selected_views, 1]
                            view_negatives_np = train_loader.sampler.sample(
                                view_users_np,
                                view_items_np,
                                epoch=epoch,
                                batch_index=global_step + 1_000_000,
                            )
                            view_users = torch.from_numpy(view_users_np).to(self.device)
                            view_items = torch.from_numpy(view_items_np).to(self.device)
                            view_negatives = torch.from_numpy(view_negatives_np).to(self.device)
                            view_positive_vectors = self.model.encode_items(
                                sbert_catalog[view_items],
                                category_catalog[view_items],
                                price_catalog[view_items],
                                item_idx=view_items,
                                is_cold=cold_catalog[view_items],
                            )
                            view_negative_vectors = self.model.encode_items(
                                sbert_catalog[view_negatives],
                                category_catalog[view_negatives],
                                price_catalog[view_negatives],
                                item_idx=view_negatives,
                                is_cold=cold_catalog[view_negatives],
                            )
                            view_user_vectors = self.model.encode_user(
                                view_users,
                                torch.from_numpy(persona_by_internal[view_users_np]).to(
                                    self.device
                                ),
                            )
                            view_positive_mask = train_loader.index.known_history[
                                view_users_np[:, None], view_items_np[None, :]
                            ]
                            view_denominator_mask = ~view_positive_mask
                            view_denominator_mask |= view_positive_mask
                            view_objective = multi_positive_sampled_softmax(
                                view_user_vectors,
                                view_positive_vectors,
                                view_negative_vectors,
                                positive_mask=torch.from_numpy(view_positive_mask).to(self.device),
                                denominator_mask=torch.from_numpy(view_denominator_mask).to(
                                    self.device
                                ),
                                confidence=torch.ones(len(view_users), device=self.device),
                                temperature=self.model._temperature,
                            )
                            auxiliary_view_loss = view_objective.loss
                        loss = purchase_objective_loss + (
                            self.settings.train.view_auxiliary_weight * auxiliary_view_loss
                        )
                    with torch.no_grad():
                        in_batch = (
                            torch.matmul(user_vectors, positive_vectors.T) / self.model._temperature
                        )
                        explicit = (
                            torch.einsum("bd,brd->br", user_vectors, negative_vectors)
                            / self.model._temperature
                        )
                        target_scores = in_batch.diagonal()
                        in_batch_valid = denominator_mask & ~positive_mask
                        valid_scores = torch.cat(
                            (
                                in_batch.masked_fill(~in_batch_valid, -torch.inf),
                                explicit,
                            ),
                            dim=1,
                        )
                        valid = torch.isfinite(valid_scores)
                        comparisons = target_scores[:, None] > valid_scores
                        pair_correct += float(comparisons[valid].sum().cpu())
                        candidate_pairs += int(valid.sum().cpu())
                        all_negative_wins += int(
                            torch.where(valid, comparisons, torch.ones_like(comparisons))
                            .all(dim=1)
                            .sum()
                            .cpu()
                        )
                        if sum(len(values) for values in margins) < 8_192:
                            margins.append(
                                (target_scores - valid_scores.max(dim=1).values)
                                .float()
                                .cpu()
                                .numpy()
                            )
                            positive_logits.append(target_scores.float().cpu().numpy())
                            negative_logits.append(valid_scores[valid].float().cpu().numpy())
                    count = len(users)
                    purchase_loss_sum += float(purchase_objective_loss.detach()) * count
                    purchase_weight += float(count)
                    if self.settings.train.view_auxiliary_weight > 0:
                        view_loss_sum += float(auxiliary_view_loss.detach()) * count
                        view_weight += float(count)
                elif isinstance(batch, TrainingBatch):
                    if self.settings.train.objective not in {"legacy_bce", "purchase_bce"}:
                        raise ModelTrainingError(
                            "legacy candidate batches require the legacy_bce objective"
                        )
                    candidate_ids = batch.candidate_item_idx.to(self.device)
                    users = batch.user_idx.to(self.device)
                    personas = batch.persona_idx.to(self.device)
                    wide = batch.wide_values.to(self.device)
                    present = batch.rule_present.to(self.device)
                    labels = batch.labels.to(self.device)
                    sample_weight = batch.sample_weight.to(self.device)
                    with autocast(device_type=self.device.type, enabled=amp_enabled):
                        logits = self.model(
                            users,
                            personas,
                            sbert_catalog[candidate_ids],
                            category_catalog[candidate_ids],
                            price_catalog[candidate_ids],
                            wide,
                            present,
                            ModelVariant.HYBRID,
                            item_idx=candidate_ids,
                            is_cold=cold_catalog[candidate_ids],
                        )
                        if not bool(torch.isfinite(logits).all()):
                            raise ModelTrainingError("training logits contain NaN or Inf")
                        per_candidate = self.loss_function(logits, labels)
                        per_sample = per_candidate.mean(dim=1)
                        loss = (per_sample * sample_weight).sum() / sample_weight.sum()
                    with torch.no_grad():
                        positive = logits[:, :1]
                        negatives = logits[:, 1:]
                        comparisons = positive > negatives
                        pair_correct += float(comparisons.sum().cpu())
                        candidate_pairs += int(comparisons.numel())
                        all_negative_wins += int(comparisons.all(dim=1).sum().cpu())
                        if sum(len(values) for values in margins) < 8_192:
                            margins.append(
                                (positive[:, 0] - negatives.max(dim=1).values).cpu().numpy()
                            )
                            positive_logits.append(positive[:, 0].float().cpu().numpy())
                            negative_logits.append(negatives.float().cpu().numpy().reshape(-1))
                        present_count += int(present.sum().cpu())
                        candidate_count += int(present.numel())
                        purchase_rows = batch.is_purchase.to(self.device)
                        view_rows = ~purchase_rows
                        if bool(purchase_rows.any()):
                            weights = sample_weight[purchase_rows]
                            purchase_loss_sum += float(
                                (per_sample[purchase_rows] * weights).sum().cpu()
                            )
                            purchase_weight += float(weights.sum().cpu())
                        if bool(view_rows.any()):
                            weights = sample_weight[view_rows]
                            view_loss_sum += float((per_sample[view_rows] * weights).sum().cpu())
                            view_weight += float(weights.sum().cpu())
                    count = len(users)
                else:
                    raise ModelTrainingError(
                        f"unsupported training batch type: {type(batch).__name__}"
                    )
                if not bool(torch.isfinite(loss)):
                    raise ModelTrainingError("training loss contains NaN or Inf")
                scaler.scale(loss).backward()  # type: ignore[no-untyped-call]
                scaler.unscale_(self.optimizer)
                user_gradient_norm = max(
                    user_gradient_norm, _module_gradient_norm(self.model.user_tower)
                )
                item_gradient_norm = max(
                    item_gradient_norm, _module_gradient_norm(self.model.item_tower)
                )
                wide_gradient_norm = max(
                    wide_gradient_norm, _module_gradient_norm(self.model.wide_layer)
                )
                gradient_norm = nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.settings.train.max_grad_norm
                )
                if not bool(torch.isfinite(gradient_norm)):
                    raise ModelTrainingError("gradient norm contains NaN or Inf")
                scaler.step(self.optimizer)
                scaler.update()
                self.scheduler.step()
                global_step += 1
                weighted_loss_sum += float(loss.detach()) * count
                sample_count += count
                epoch_gradient_norm = max(epoch_gradient_norm, float(gradient_norm))
                if amp_enabled:
                    try:
                        gpu_utilization.append(float(torch.cuda.utilization(self.device)))
                    except (RuntimeError, OSError, ImportError):
                        pass
                previous_batch_finished = time.perf_counter()
            if sample_count == 0:
                raise ModelTrainingError("training loader produced no samples")
            train_loss = weighted_loss_sum / sample_count
            if hasattr(val_evaluator, "evaluate_variants"):
                variants = cast(Any, val_evaluator).evaluate_variants(
                    self.model,
                    snapshot,
                    split=SplitName.VAL,
                    k=self.settings.eval.k,
                    variants=(
                        ModelVariant.HYBRID,
                        ModelVariant.DEEP_ONLY,
                        ModelVariant.WIDE_ONLY,
                    ),
                    device=self.device,
                )
                report = variants[ModelVariant.HYBRID].report
                deep_report = variants[ModelVariant.DEEP_ONLY].report
                wide_report = variants[ModelVariant.WIDE_ONLY].report
            else:
                validation = val_evaluator.evaluate(
                    self.model,
                    snapshot,
                    split=SplitName.VAL,
                    k=self.settings.eval.k,
                    variant=ModelVariant.HYBRID,
                    device=self.device,
                )
                report = getattr(validation, "report", validation)
                deep_report = report
                wide_report = report
            val_gauc = float(report.gauc)
            val_ndcg = float(report.ndcg_at_k)
            if not np.isfinite(val_gauc) or not np.isfinite(val_ndcg):
                raise ModelTrainingError("validation metrics are not finite")
            ndcg_improved = val_ndcg > best_ndcg + self.settings.train.min_delta
            ndcg_tied = abs(val_ndcg - best_ndcg) <= self.settings.train.min_delta
            guardrails_passed = (
                val_gauc >= float(deep_report.gauc) + self.settings.eval.gauc_guardrail_delta
                and val_ndcg
                >= max(float(deep_report.ndcg_at_k), float(wide_report.ndcg_at_k))
                + self.settings.eval.ndcg_guardrail_delta
            )
            # Ablations must retain their best validation checkpoint even when
            # they intentionally fail release guardrails.  Release eligibility
            # remains a separate measured field and is enforced downstream.
            is_best = ndcg_improved or (ndcg_tied and val_gauc > best_gauc)
            if is_best:
                best_gauc = val_gauc
                best_ndcg = val_ndcg
                best_epoch = epoch
                no_improvement = 0
                CheckpointManager.save(
                    best_path,
                    model=self.model,
                    optimizer=self.optimizer,
                    scheduler=self.scheduler,
                    epoch=epoch,
                    metrics={
                        "val_gauc": val_gauc,
                        "val_ndcg_at_k": val_ndcg,
                        "train_loss": train_loss,
                    },
                    lineage=lineage,
                    training_signature_sha256=config_sha,
                    model_schema_version=MODEL_SCHEMA_VERSION,
                    run_id=run_id,
                    scaler=scaler,
                )
            else:
                no_improvement += 1
            point = (val_ndcg, val_gauc, float(report.hr_at_k))
            dominated = any(
                existing[0] >= point[0]
                and existing[1] >= point[1]
                and existing[2] >= point[2]
                and (existing[0] > point[0] or existing[1] > point[1] or existing[2] > point[2])
                for existing in pareto_frontier
            )
            if guardrails_passed and not dominated:
                retained: list[tuple[float, float, float, Path]] = []
                for existing in pareto_frontier:
                    is_dominated = (
                        point[0] >= existing[0]
                        and point[1] >= existing[1]
                        and point[2] >= existing[2]
                        and (
                            point[0] > existing[0]
                            or point[1] > existing[1]
                            or point[2] > existing[2]
                        )
                    )
                    if is_dominated:
                        existing[3].unlink(missing_ok=True)
                        existing[3].with_suffix(".pt.manifest.json").unlink(missing_ok=True)
                    else:
                        retained.append(existing)
                pareto_path = self.run_dir / "checkpoints" / "pareto" / f"epoch-{epoch:03d}.pt"
                CheckpointManager.save(
                    pareto_path,
                    model=self.model,
                    optimizer=self.optimizer,
                    scheduler=self.scheduler,
                    scaler=scaler,
                    epoch=epoch,
                    metrics={
                        "val_gauc": val_gauc,
                        "val_ndcg_at_k": val_ndcg,
                        "train_loss": train_loss,
                    },
                    lineage=lineage,
                    training_signature_sha256=config_sha,
                    model_schema_version=MODEL_SCHEMA_VERSION,
                    run_id=run_id,
                )
                pareto_frontier = [*retained, (*point, pareto_path)]
                pareto_frontier.sort(key=lambda value: value[:3], reverse=True)
                for discarded in pareto_frontier[3:]:
                    discarded[3].unlink(missing_ok=True)
                    discarded[3].with_suffix(".pt.manifest.json").unlink(missing_ok=True)
                pareto_frontier = pareto_frontier[:3]
            margin_values = np.concatenate(margins) if margins else np.asarray([0.0])
            positive_values = (
                np.concatenate(positive_logits) if positive_logits else np.asarray([0.0])
            )
            negative_values = (
                np.concatenate(negative_logits) if negative_logits else np.asarray([0.0])
            )
            epoch_duration = max(time.perf_counter() - epoch_started, np.finfo(float).eps)
            metrics = EpochMetrics(
                epoch=epoch,
                global_step=global_step,
                train_loss=train_loss,
                purchase_loss=purchase_loss_sum / max(1, purchase_weight),
                view_loss=view_loss_sum / max(1, view_weight),
                wide_loss=0.0,
                val_gauc=val_gauc,
                val_hr_at_k=float(report.hr_at_k),
                val_ndcg_at_k=val_ndcg,
                val_deep_gauc=float(deep_report.gauc),
                val_deep_ndcg_at_k=float(deep_report.ndcg_at_k),
                val_wide_gauc=float(wide_report.gauc),
                val_wide_ndcg_at_k=float(wide_report.ndcg_at_k),
                checkpoint_guardrails_passed=guardrails_passed,
                learning_rate=float(self.optimizer.param_groups[0]["lr"]),
                sampled_pair_accuracy=pair_correct / max(1, candidate_pairs),
                all_negative_win_rate=all_negative_wins / sample_count,
                margin_p10=float(np.quantile(margin_values, 0.1)),
                margin_p50=float(np.quantile(margin_values, 0.5)),
                margin_p90=float(np.quantile(margin_values, 0.9)),
                gradient_norm=epoch_gradient_norm,
                user_tower_gradient_norm=user_gradient_norm,
                item_tower_gradient_norm=item_gradient_norm,
                wide_gradient_norm=wide_gradient_norm,
                positive_logit_p10=float(np.quantile(positive_values, 0.1)),
                positive_logit_p50=float(np.quantile(positive_values, 0.5)),
                positive_logit_p90=float(np.quantile(positive_values, 0.9)),
                negative_logit_p10=float(np.quantile(negative_values, 0.1)),
                negative_logit_p50=float(np.quantile(negative_values, 0.5)),
                negative_logit_p90=float(np.quantile(negative_values, 0.9)),
                rule_present_rate=present_count / max(1, candidate_count),
                elapsed_seconds=time.perf_counter() - started_training,
                peak_ram_bytes=_peak_resident_bytes(),
                peak_vram_bytes=(
                    int(torch.cuda.max_memory_allocated(self.device)) if amp_enabled else 0
                ),
                gpu_utilization_median=(
                    float(np.median(gpu_utilization)) if gpu_utilization else 0.0
                ),
                data_wait_ratio=data_wait_seconds / epoch_duration,
                is_best=is_best,
                early_peak_warning=best_epoch <= 2 and epoch >= 2,
            )
            history.append(metrics)
            self._append_history(metrics)
            CheckpointManager.save(
                self.run_dir / "checkpoints" / "last.pt",
                model=self.model,
                optimizer=self.optimizer,
                scheduler=self.scheduler,
                epoch=epoch,
                metrics={
                    "val_gauc": val_gauc,
                    "val_ndcg_at_k": val_ndcg,
                    "train_loss": train_loss,
                },
                lineage=lineage,
                training_signature_sha256=config_sha,
                model_schema_version=MODEL_SCHEMA_VERSION,
                run_id=run_id,
                scaler=scaler,
            )
            if (
                isinstance(train_loader, PurchaseBatchIterator)
                and epoch < self.settings.train.max_epochs
            ):
                self.model.eval()
                refreshed_items = self.model.encode_items(
                    sbert_catalog,
                    category_catalog,
                    price_catalog,
                    item_idx=torch.arange(
                        snapshot.manifest.num_items,
                        dtype=torch.int64,
                        device=self.device,
                    ),
                    is_cold=cold_catalog,
                )
                self._refresh_model_hard_cache(train_loader, snapshot, refreshed_items)
            if no_improvement >= self.settings.train.early_stopping_patience:
                stop_reason = "early_stopping"
                break
        if not best_path.exists():
            raise ModelTrainingError("training did not produce a best checkpoint")
        summary_path = self.run_dir / "training" / "summary.json"
        summary_temporary = summary_path.with_suffix(".json.tmp")
        summary_temporary.write_text(
            json.dumps(
                {
                    "best_epoch": best_epoch,
                    "best_val_ndcg_at_k": best_ndcg,
                    "best_val_gauc": best_gauc,
                    "epochs_completed": len(history),
                    "stop_reason": stop_reason,
                    "pareto_checkpoints": [str(value[3]) for value in pareto_frontier],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(summary_temporary, summary_path)
        CheckpointManager.load(
            best_path,
            model=self.model,
            expected_lineage=lineage,
            expected_training_signature=config_sha,
            expected_model_schema_version=MODEL_SCHEMA_VERSION,
        )
        return TrainResult(
            run_id,
            best_epoch,
            best_gauc,
            best_ndcg,
            tuple(history),
            best_path,
            stop_reason,
        )
