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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import numpy as np
import torch
from torch import nn
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR

from ai_service.config import MODEL_SCHEMA_VERSION, Settings
from ai_service.contracts import (
    CheckpointAction,
    EvaluationReport,
    ModelVariant,
    SplitName,
    TerminalAction,
    TrainingVariant,
)
from ai_service.data.dataset import PurchaseBatch, TrainingBatch
from ai_service.data.rule_readiness import RuleCoverageAccumulator
from ai_service.data.snapshot import Snapshot
from ai_service.errors import (
    CatastrophicTrainingError,
    DataIntegrityError,
    DiagnosticQualityError,
    ModelTrainingError,
    TrainingInterruptedError,
)
from ai_service.evaluation.full_catalog import (
    PreparedEvaluationSplit,
    TrainingValidationPass,
    prepare_split,
)
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.checkpoint import CheckpointManager
from ai_service.training.diagnostic_stop import DiagnosticStopReport, publish_diagnostic_stop
from ai_service.training.objectives import multi_positive_sampled_softmax
from ai_service.training.stopping import EarlyStoppingController, StoppingDecision


class ValidationEvaluator(Protocol):
    def evaluate_training_epoch(
        self,
        model: HybridTwoTowerModel,
        snapshot: Snapshot,
        *,
        prepared_split: PreparedEvaluationSplit,
        k: int,
        device: torch.device,
    ) -> TrainingValidationPass: ...


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
    in_batch_rule_present_rate: float
    explicit_rule_present_rate: float
    rows_with_any_rule_rate: float
    wide_to_deep_logit_rms_ratio: float
    hybrid_deep_top_k_change_rate: float
    elapsed_seconds: float
    peak_ram_bytes: int
    peak_vram_bytes: int
    gpu_utilization_median: float
    data_wait_ratio: float
    is_best: bool
    early_peak_warning: bool
    deep_logit_rms: float = 0.0
    wide_logit_rms: float = 0.0
    hybrid_logit_rms: float = 0.0
    strict_target_rule_rate: float = 0.0
    other_positive_rule_rate: float = 0.0
    valid_negative_rule_rate: float = 0.0
    explicit_negative_rule_rate: float = 0.0
    negative_only_row_rate: float = 0.0
    rule_loss: float = 0.0
    model_hard_cache_updated: bool = False
    terminal_action: TerminalAction = TerminalAction.CONTINUE
    stopping_reason: str = ""


@dataclass(frozen=True)
class TrainResult:
    run_id: str
    best_epoch: int
    best_gauc: float
    best_ndcg_at_k: float
    best_hr_at_k: float
    history: tuple[EpochMetrics, ...]
    checkpoint_path: Path
    stop_reason: str
    terminal_action: TerminalAction = TerminalAction.COMPLETED
    terminal_reason: str = ""


@dataclass(frozen=True)
class _TrainingEpochPass:
    """Small, typed seam for the batch-training diagnostics produced per epoch."""

    epoch: int
    global_step: int
    train_loss: float
    purchase_loss: float
    view_loss: float
    sampled_pair_accuracy: float
    all_negative_win_rate: float
    margin_p10: float
    margin_p50: float
    margin_p90: float
    gradient_norm: float
    user_gradient_norm: float
    item_gradient_norm: float
    wide_gradient_norm: float
    positive_logit_p10: float
    positive_logit_p50: float
    positive_logit_p90: float
    negative_logit_p10: float
    negative_logit_p50: float
    negative_logit_p90: float
    in_batch_rule_present_rate: float
    explicit_rule_present_rate: float
    rows_with_any_rule_rate: float
    strict_target_rule_rate: float
    other_positive_rule_rate: float
    valid_negative_rule_rate: float
    explicit_negative_rule_rate: float
    negative_only_row_rate: float
    rule_loss: float
    learning_rate: float
    elapsed_seconds: float
    epoch_duration_seconds: float
    peak_ram_bytes: int
    peak_vram_bytes: int
    gpu_utilization_median: float
    data_wait_ratio: float


@dataclass(frozen=True)
class _ResumeState:
    start_epoch: int
    global_step: int
    history: tuple[EpochMetrics, ...]
    elapsed_seconds: float


@dataclass(frozen=True)
class _TrainingRuntime:
    catalog: _PreparedCatalog
    scaler: GradScaler
    stopping: EarlyStoppingController
    started_at: datetime
    started_training: float
    deep_wide_baseline: tuple[torch.Tensor, ...]


@dataclass(frozen=True)
class _PreparedCatalog:
    sbert: torch.Tensor
    category: torch.Tensor
    price: torch.Tensor
    cold: torch.Tensor
    persona_by_internal: np.ndarray


@dataclass(frozen=True)
class _ValidationEpochPass:
    """Typed validation seam shared by checkpointing and hard-negative refresh."""

    hybrid_report: EvaluationReport
    deep_report: EvaluationReport
    wide_report: EvaluationReport
    deep_logit_rms: float
    wide_logit_rms: float
    hybrid_logit_rms: float
    hybrid_deep_top_k_change_rate: float
    model_hard_cache_updated: bool


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
        training_variant: TrainingVariant | None = None,
        device: str | torch.device | None = None,
    ) -> None:
        self.settings = settings
        self.training_variant = training_variant or settings.train.training_variant
        if self.training_variant is not settings.train.training_variant:
            raise ModelTrainingError(
                "requested training variant differs from resolved configuration"
            )
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = model.to(self.device)
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        if self.training_variant is TrainingVariant.DEEP_ONLY:
            deep_params = [
                p for name, p in self.model.named_parameters() if not name.startswith("wide_layer.")
            ]
            self.optimizer = AdamW(
                deep_params,
                lr=settings.train.learning_rate,
                weight_decay=settings.train.weight_decay,
            )
            optimizer_ids = {
                id(parameter)
                for group in self.optimizer.param_groups
                for parameter in group["params"]
            }
            expected_ids = {
                id(parameter)
                for name, parameter in self.model.named_parameters()
                if parameter.requires_grad and not name.startswith("wide_layer.")
            }
            if optimizer_ids != expected_ids:
                raise ModelTrainingError("Deep-only optimizer contains an invalid parameter set")
        else:
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

    def _prepare_catalog(self, snapshot: Snapshot, embeddings: np.ndarray) -> _PreparedCatalog:
        """Encode immutable catalog features once per training run."""
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
        return _PreparedCatalog(
            sbert=sbert_catalog,
            category=category_catalog,
            price=price_catalog,
            cold=cold_catalog,
            persona_by_internal=persona_by_internal,
        )

    def _assert_parameters_finite(self, *, stage: str) -> None:
        """Fail with the exact parameter name as soon as a model becomes invalid."""
        for name, parameter in self.model.named_parameters():
            if not bool(torch.isfinite(parameter).all()):
                raise CatastrophicTrainingError(f"parameter contains NaN or Inf {stage}: {name}")

    def _assert_deep_wide_invariant(self, baseline: list[torch.Tensor]) -> None:
        """Deep-only runs must never update or backpropagate through Wide."""
        for parameter, before in zip(self.model.wide_layer.parameters(), baseline, strict=True):
            if parameter.grad is not None and bool(torch.any(parameter.grad != 0)):
                raise CatastrophicTrainingError("Deep-only training produced Wide gradients")
            if not torch.equal(parameter.detach(), before):
                raise CatastrophicTrainingError("Deep-only training changed Wide parameters")

    def _restore_resume_state(
        self,
        resume_from: Path,
        *,
        best_path: Path,
        lineage: dict[str, str],
        config_sha: str,
        stopping: EarlyStoppingController,
        scaler: Any,
    ) -> _ResumeState:
        """Restore a durable ``last.pt`` without replaying stopping history."""
        expected_last = self.run_dir / "checkpoints" / "last.pt"
        if resume_from.resolve() != expected_last.resolve():
            raise ModelTrainingError("resume must use this run's last.pt checkpoint")
        state = CheckpointManager.load(
            resume_from,
            model=self.model,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            scaler=scaler,
            expected_lineage=lineage,
            expected_training_signature=config_sha,
            expected_comparison_signature=self.settings.comparison_signature_sha256(),
            expected_training_variant=self.training_variant,
            expected_model_schema_version=MODEL_SCHEMA_VERSION,
            expected_checkpoint_kind="last",
            expected_run_id=self.run_dir.name,
            require_resume_state=True,
            restore_rng=True,
        )
        stopping_state = state.get("stopping_state")
        if not stopping_state:
            raise ModelTrainingError("resume checkpoint has no stopping state")
        stopping.load_state_dict(stopping_state)
        if stopping.selected_epoch > 0 and not best_path.is_file():
            raise ModelTrainingError("resume stopping state references a missing best checkpoint")
        history_path = self.run_dir / "training" / "history.jsonl"
        if not history_path.is_file():
            raise ModelTrainingError("resume checkpoint has no durable training history")
        history: list[EpochMetrics] = []
        expected_epoch = int(state["epoch"])
        for line in history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                history_document = json.loads(line)
                history_document["terminal_action"] = TerminalAction(
                    history_document["terminal_action"]
                )
                history.append(EpochMetrics(**history_document))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                raise ModelTrainingError(
                    "resume history contains an invalid epoch record"
                ) from error
        if not history or history[-1].epoch != expected_epoch:
            raise ModelTrainingError("resume history and checkpoint epochs differ")
        epochs = [item.epoch for item in history]
        if epochs != list(range(1, expected_epoch + 1)):
            raise ModelTrainingError("resume history epochs are not contiguous")
        return _ResumeState(
            start_epoch=expected_epoch + 1,
            global_step=history[-1].global_step,
            history=tuple(history),
            elapsed_seconds=history[-1].elapsed_seconds,
        )

    def _train_epoch(
        self,
        *,
        epoch: int,
        global_step: int,
        train_loader: Any,
        runtime: _TrainingRuntime,
    ) -> _TrainingEpochPass:
        """Run one complete batch-training epoch and return immutable diagnostics."""
        self.model.train()
        if hasattr(train_loader, "set_epoch"):
            train_loader.set_epoch(epoch)
        dataset = getattr(train_loader, "dataset", None)
        if dataset is not None and hasattr(dataset, "set_epoch"):
            dataset.set_epoch(epoch)

        catalog = runtime.catalog
        sbert_catalog = catalog.sbert
        category_catalog = catalog.category
        price_catalog = catalog.price
        cold_catalog = catalog.cold
        persona_by_internal = catalog.persona_by_internal
        stopping = runtime.stopping
        scaler = runtime.scaler
        amp_enabled = self.device.type == "cuda"
        amp_dtype = torch.bfloat16 if amp_enabled else torch.float32
        if self.scheduler is None:
            raise ModelTrainingError("training scheduler is not initialized")

        weighted_loss_sum = 0.0
        sample_count = 0
        purchase_loss_sum = 0.0
        purchase_weight = 0.0
        view_loss_sum = 0.0
        view_weight = 0.0
        rule_loss_sum = 0.0
        pair_correct = 0.0
        all_negative_wins = 0
        candidate_pairs = 0
        margins: list[np.ndarray] = []
        positive_logits: list[np.ndarray] = []
        negative_logits: list[np.ndarray] = []
        rule_coverage = RuleCoverageAccumulator()
        epoch_gradient_norm = 0.0
        user_gradient_norm = 0.0
        item_gradient_norm = 0.0
        wide_gradient_norm = 0.0
        data_wait_seconds = 0.0
        epoch_started = time.perf_counter()
        previous_batch_finished = epoch_started
        gpu_utilization: list[float] = []
        for batch in train_loader:
            wall_decision = stopping.check_wall_time(
                start_time=runtime.started_at,
                current_time=datetime.now(UTC),
            )
            if wall_decision is not None:
                raise TrainingInterruptedError(wall_decision.reason)
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
                try:
                    rule_coverage.observe_purchase_batch(batch)
                except DataIntegrityError as error:
                    raise ModelTrainingError(str(error)) from error
                confidence = batch.confidence.to(self.device)
                with autocast(
                    device_type=self.device.type,
                    enabled=amp_enabled,
                    dtype=amp_dtype,
                ):
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
                    if self.training_variant is TrainingVariant.HYBRID:
                        in_batch_wide_values = batch.in_batch_wide_values.to(self.device)
                        in_batch_rule_present = batch.in_batch_rule_present.to(self.device)
                        explicit_wide_values = batch.explicit_wide_values.to(self.device)
                        explicit_rule_present = batch.explicit_rule_present.to(self.device)
                        in_batch_wide_logits = self.model.wide_layer(
                            in_batch_wide_values, in_batch_rule_present
                        )
                        explicit_wide_logits = self.model.wide_layer(
                            explicit_wide_values, explicit_rule_present
                        )
                    else:
                        in_batch_wide_logits = torch.zeros(
                            (len(users), len(users)), dtype=torch.float32, device=self.device
                        )
                        explicit_wide_logits = torch.zeros(
                            (len(users), batch.explicit_negative_idx.shape[1]),
                            dtype=torch.float32,
                            device=self.device,
                        )
                    objective = multi_positive_sampled_softmax(
                        user_vectors,
                        positive_vectors,
                        negative_vectors,
                        positive_mask=positive_mask,
                        denominator_mask=denominator_mask,
                        confidence=confidence,
                        temperature=self.model._temperature,
                        in_batch_wide_logits=in_batch_wide_logits,
                        explicit_wide_logits=explicit_wide_logits,
                        rule_positive_mask=(
                            in_batch_rule_present
                            if self.training_variant is TrainingVariant.HYBRID
                            else None
                        ),
                        rule_negative_mask=(
                            explicit_rule_present
                            if self.training_variant is TrainingVariant.HYBRID
                            else None
                        ),
                        rule_weight=(
                            self.settings.train.rule_auxiliary_weight
                            if self.training_variant is TrainingVariant.HYBRID
                            else 0.0
                        ),
                    )
                    purchase_objective_loss = objective.loss
                    rule_loss_sum += float(objective.rule_loss.detach().cpu()) * len(users)
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
                            torch.from_numpy(persona_by_internal[view_users_np]).to(self.device),
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
                            in_batch_wide_logits=torch.zeros(
                                (len(view_users), len(view_users)), device=self.device
                            ),
                            explicit_wide_logits=torch.zeros(
                                (len(view_users), view_negatives.shape[1]), device=self.device
                            ),
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
                    if not bool(torch.isfinite(in_batch).all()):
                        raise CatastrophicTrainingError(
                            "sampled-softmax in-batch logits contain NaN or Inf"
                        )
                    if not bool(torch.isfinite(explicit).all()):
                        raise CatastrophicTrainingError(
                            "sampled-softmax explicit logits contain NaN or Inf"
                        )
                    target_scores = in_batch.diagonal()
                    in_batch_valid = denominator_mask & ~positive_mask
                    valid_scores = torch.cat(
                        (in_batch.masked_fill(~in_batch_valid, -torch.inf), explicit), dim=1
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
                            (target_scores - valid_scores.max(dim=1).values).float().cpu().numpy()
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
                with autocast(
                    device_type=self.device.type,
                    enabled=amp_enabled,
                    dtype=amp_dtype,
                ):
                    logits = self.model(
                        users,
                        personas,
                        sbert_catalog[candidate_ids],
                        category_catalog[candidate_ids],
                        price_catalog[candidate_ids],
                        wide,
                        present,
                        (
                            ModelVariant.HYBRID
                            if self.training_variant is TrainingVariant.HYBRID
                            else ModelVariant.DEEP_ONLY
                        ),
                        item_idx=candidate_ids,
                        is_cold=cold_catalog[candidate_ids],
                    )
                    if not bool(torch.isfinite(logits).all()):
                        raise CatastrophicTrainingError("training logits contain NaN or Inf")
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
                            (positive[:, 0] - negatives.max(dim=1).values).float().cpu().numpy()
                        )
                        positive_logits.append(positive[:, 0].float().cpu().numpy())
                        negative_logits.append(negatives.float().cpu().numpy().reshape(-1))
                    try:
                        rule_coverage.observe_legacy_mask(present)
                    except DataIntegrityError as error:
                        raise ModelTrainingError(str(error)) from error
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
                raise ModelTrainingError(f"unsupported training batch type: {type(batch).__name__}")
            if not bool(torch.isfinite(loss)):
                raise CatastrophicTrainingError("training loss contains NaN or Inf")
            scaler.scale(loss).backward()  # type: ignore[no-untyped-call]
            scaler.unscale_(self.optimizer)
            for name, parameter in self.model.named_parameters():
                if parameter.grad is not None and not bool(torch.isfinite(parameter.grad).all()):
                    raise CatastrophicTrainingError(f"gradient contains NaN or Inf: {name}")
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
                raise CatastrophicTrainingError("gradient norm contains NaN or Inf")
            scaler.step(self.optimizer)
            scaler.update()
            self._assert_parameters_finite(stage="after optimizer step")
            if self.training_variant is TrainingVariant.DEEP_ONLY:
                self._assert_deep_wide_invariant(list(runtime.deep_wide_baseline))
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
        try:
            rule_rates = rule_coverage.rates()
        except DataIntegrityError as error:
            raise ModelTrainingError(str(error)) from error
        if (
            epoch == 1
            and self.training_variant is TrainingVariant.HYBRID
            and wide_gradient_norm <= 0.0
        ):
            raise CatastrophicTrainingError("Hybrid epoch 1 produced no Wide gradient")
        margin_values = np.concatenate(margins) if margins else np.asarray([0.0])
        positive_values = np.concatenate(positive_logits) if positive_logits else np.asarray([0.0])
        negative_values = np.concatenate(negative_logits) if negative_logits else np.asarray([0.0])
        epoch_duration = max(time.perf_counter() - epoch_started, np.finfo(float).eps)
        return _TrainingEpochPass(
            epoch=epoch,
            global_step=global_step,
            train_loss=weighted_loss_sum / sample_count,
            purchase_loss=purchase_loss_sum / max(1, purchase_weight),
            view_loss=view_loss_sum / max(1, view_weight),
            sampled_pair_accuracy=pair_correct / max(1, candidate_pairs),
            all_negative_win_rate=all_negative_wins / sample_count,
            margin_p10=float(np.quantile(margin_values, 0.1)),
            margin_p50=float(np.quantile(margin_values, 0.5)),
            margin_p90=float(np.quantile(margin_values, 0.9)),
            gradient_norm=epoch_gradient_norm,
            user_gradient_norm=user_gradient_norm,
            item_gradient_norm=item_gradient_norm,
            wide_gradient_norm=wide_gradient_norm,
            positive_logit_p10=float(np.quantile(positive_values, 0.1)),
            positive_logit_p50=float(np.quantile(positive_values, 0.5)),
            positive_logit_p90=float(np.quantile(positive_values, 0.9)),
            negative_logit_p10=float(np.quantile(negative_values, 0.1)),
            negative_logit_p50=float(np.quantile(negative_values, 0.5)),
            negative_logit_p90=float(np.quantile(negative_values, 0.9)),
            in_batch_rule_present_rate=rule_rates.in_batch_rule_present_rate,
            explicit_rule_present_rate=rule_rates.explicit_rule_present_rate,
            rows_with_any_rule_rate=rule_rates.rows_with_any_rule_rate,
            strict_target_rule_rate=rule_rates.strict_target_rule_rate,
            other_positive_rule_rate=rule_rates.other_positive_rule_rate,
            valid_negative_rule_rate=rule_rates.valid_negative_rule_rate,
            explicit_negative_rule_rate=rule_rates.explicit_negative_rule_rate,
            negative_only_row_rate=rule_rates.negative_only_row_rate,
            rule_loss=rule_loss_sum / max(1, sample_count),
            learning_rate=float(self.optimizer.param_groups[0]["lr"]),
            elapsed_seconds=time.perf_counter() - runtime.started_training,
            epoch_duration_seconds=epoch_duration,
            peak_ram_bytes=_peak_resident_bytes(),
            peak_vram_bytes=(
                int(torch.cuda.max_memory_allocated(self.device)) if amp_enabled else 0
            ),
            gpu_utilization_median=float(np.median(gpu_utilization)) if gpu_utilization else 0.0,
            data_wait_ratio=data_wait_seconds / epoch_duration,
        )

    def _validate_epoch(
        self,
        val_evaluator: ValidationEvaluator,
        snapshot: Snapshot,
        prepared_split: PreparedEvaluationSplit,
        train_loader: Any,
    ) -> _ValidationEpochPass:
        """Run exactly one typed validation pass and return its gate metrics."""
        validation = val_evaluator.evaluate_training_epoch(
            self.model,
            snapshot,
            prepared_split=prepared_split,
            k=self.settings.eval.k,
            device=self.device,
        )
        try:
            hybrid_report = validation.variants[ModelVariant.HYBRID].report
            deep_report = validation.variants[ModelVariant.DEEP_ONLY].report
            wide_report = validation.variants[ModelVariant.WIDE_ONLY].report
        except (AttributeError, KeyError, TypeError) as error:
            raise ModelTrainingError("validation did not return all model variants") from error
        for variant_name, report in (
            ("hybrid", hybrid_report),
            ("deep", deep_report),
            ("wide", wide_report),
        ):
            values = (float(report.gauc), float(report.ndcg_at_k), float(report.hr_at_k))
            if not np.isfinite(values).all():
                raise CatastrophicTrainingError(
                    f"validation {variant_name} metrics contain NaN or Inf"
                )
        diagnostics = tuple(
            float(getattr(validation, name, 0.0))
            for name in ("deep_logit_rms", "wide_logit_rms", "hybrid_logit_rms")
        )
        if not np.isfinite(diagnostics).all():
            raise CatastrophicTrainingError("validation diagnostics contain NaN or Inf")
        model_hard_cache = getattr(validation, "model_hard_cache", None)
        if model_hard_cache is None:
            raise ModelTrainingError("validation did not produce a model-hard cache")
        sampler = getattr(train_loader, "sampler", None)
        if sampler is None or not hasattr(sampler, "update_model_hard_cache"):
            raise ModelTrainingError("training sampler cannot accept model-hard cache")
        sampler.update_model_hard_cache(model_hard_cache)
        top_k_change_rate = float(validation.hybrid_deep_top_k_change_rate)
        if not math.isfinite(top_k_change_rate) or not 0.0 <= top_k_change_rate <= 1.0:
            raise CatastrophicTrainingError("validation Hybrid/Deep top-k change rate is invalid")
        return _ValidationEpochPass(
            hybrid_report=hybrid_report,
            deep_report=deep_report,
            wide_report=wide_report,
            deep_logit_rms=diagnostics[0],
            wide_logit_rms=diagnostics[1],
            hybrid_logit_rms=diagnostics[2],
            hybrid_deep_top_k_change_rate=top_k_change_rate,
            model_hard_cache_updated=True,
        )

    def _build_epoch_metrics(
        self,
        *,
        training: _TrainingEpochPass,
        validation: _ValidationEpochPass,
        decision: StoppingDecision,
        stopping: EarlyStoppingController,
    ) -> EpochMetrics:
        """Build one immutable metrics row from typed training/validation passes."""
        val_gauc = float(validation.hybrid_report.gauc)
        val_ndcg = float(validation.hybrid_report.ndcg_at_k)
        val_hr = float(validation.hybrid_report.hr_at_k)
        wide_to_deep_ratio = validation.wide_logit_rms / max(
            validation.deep_logit_rms, np.finfo(float).eps
        )
        guardrails_passed = self.training_variant is TrainingVariant.DEEP_ONLY or (
            val_gauc
            >= float(validation.deep_report.gauc) + self.settings.eval.aggregate_gauc_min_delta
            and val_ndcg
            >= max(
                float(validation.deep_report.ndcg_at_k),
                float(validation.wide_report.ndcg_at_k),
            )
            + self.settings.eval.aggregate_ndcg_min_delta
            and val_hr
            >= max(
                float(validation.deep_report.hr_at_k),
                float(validation.wide_report.hr_at_k),
            )
            + self.settings.eval.aggregate_hr_min_delta
            and wide_to_deep_ratio >= self.settings.eval.minimum_wide_to_deep_rms_ratio
            and validation.hybrid_deep_top_k_change_rate
            >= self.settings.eval.minimum_hybrid_deep_top_k_change_rate
        )
        is_best = decision.checkpoint_action is not CheckpointAction.NONE
        terminal_action = decision.terminal_action
        stopping_reason = decision.reason
        if (
            terminal_action is TerminalAction.CONTINUE
            and training.epoch == self.settings.train.max_epochs
        ):
            terminal_action = TerminalAction.COMPLETED
            stopping_reason = "maximum epochs completed"
        metrics = EpochMetrics(
            epoch=training.epoch,
            global_step=training.global_step,
            train_loss=training.train_loss,
            purchase_loss=training.purchase_loss,
            view_loss=training.view_loss,
            wide_loss=0.0,
            val_gauc=val_gauc,
            val_hr_at_k=val_hr,
            val_ndcg_at_k=val_ndcg,
            val_deep_gauc=float(validation.deep_report.gauc),
            val_deep_ndcg_at_k=float(validation.deep_report.ndcg_at_k),
            val_wide_gauc=float(validation.wide_report.gauc),
            val_wide_ndcg_at_k=float(validation.wide_report.ndcg_at_k),
            checkpoint_guardrails_passed=guardrails_passed,
            learning_rate=training.learning_rate,
            sampled_pair_accuracy=training.sampled_pair_accuracy,
            all_negative_win_rate=training.all_negative_win_rate,
            margin_p10=training.margin_p10,
            margin_p50=training.margin_p50,
            margin_p90=training.margin_p90,
            gradient_norm=training.gradient_norm,
            user_tower_gradient_norm=training.user_gradient_norm,
            item_tower_gradient_norm=training.item_gradient_norm,
            wide_gradient_norm=training.wide_gradient_norm,
            positive_logit_p10=training.positive_logit_p10,
            positive_logit_p50=training.positive_logit_p50,
            positive_logit_p90=training.positive_logit_p90,
            negative_logit_p10=training.negative_logit_p10,
            negative_logit_p50=training.negative_logit_p50,
            negative_logit_p90=training.negative_logit_p90,
            in_batch_rule_present_rate=training.in_batch_rule_present_rate,
            explicit_rule_present_rate=training.explicit_rule_present_rate,
            rows_with_any_rule_rate=training.rows_with_any_rule_rate,
            strict_target_rule_rate=training.strict_target_rule_rate,
            other_positive_rule_rate=training.other_positive_rule_rate,
            valid_negative_rule_rate=training.valid_negative_rule_rate,
            explicit_negative_rule_rate=training.explicit_negative_rule_rate,
            negative_only_row_rate=training.negative_only_row_rate,
            rule_loss=training.rule_loss,
            wide_to_deep_logit_rms_ratio=wide_to_deep_ratio,
            hybrid_deep_top_k_change_rate=validation.hybrid_deep_top_k_change_rate,
            elapsed_seconds=training.elapsed_seconds,
            peak_ram_bytes=training.peak_ram_bytes,
            peak_vram_bytes=training.peak_vram_bytes,
            gpu_utilization_median=training.gpu_utilization_median,
            data_wait_ratio=training.data_wait_ratio,
            is_best=is_best,
            early_peak_warning=stopping.selected_epoch <= 2 and training.epoch >= 2,
            deep_logit_rms=validation.deep_logit_rms,
            wide_logit_rms=validation.wide_logit_rms,
            hybrid_logit_rms=validation.hybrid_logit_rms,
            model_hard_cache_updated=validation.model_hard_cache_updated,
            terminal_action=terminal_action,
            stopping_reason=stopping_reason,
        )
        numeric_values = asdict(metrics)
        for name, value in numeric_values.items():
            if isinstance(value, float) and not math.isfinite(value):
                raise CatastrophicTrainingError(f"epoch metric contains NaN or Inf: {name}")
        return metrics

    def _checkpoint_eligibility(
        self,
        *,
        epoch: int,
        validation: _ValidationEpochPass,
    ) -> tuple[bool, str]:
        if self.training_variant is TrainingVariant.DEEP_ONLY:
            return True, "deep-only control"
        if epoch < self.settings.train.diagnostic_warmup_epochs:
            return True, "diagnostic warmup"
        ratio = validation.wide_logit_rms / max(validation.deep_logit_rms, np.finfo(float).eps)
        hybrid = validation.hybrid_report
        deep = validation.deep_report
        wide = validation.wide_report
        reasons: list[str] = []
        if float(hybrid.gauc) < self.settings.eval.minimum_gauc:
            reasons.append("absolute GAUC floor")
        if float(hybrid.hr_at_k) < self.settings.eval.minimum_hr_at_k:
            reasons.append("absolute HR floor")
        if float(hybrid.ndcg_at_k) < self.settings.eval.minimum_ndcg_at_k:
            reasons.append("absolute NDCG floor")
        if float(hybrid.gauc) < float(deep.gauc) + self.settings.eval.aggregate_gauc_min_delta:
            reasons.append("Hybrid GAUC guardrail")
        if (
            float(hybrid.hr_at_k)
            < max(float(deep.hr_at_k), float(wide.hr_at_k))
            + self.settings.eval.aggregate_hr_min_delta
        ):
            reasons.append("Hybrid HR guardrail")
        if (
            float(hybrid.ndcg_at_k)
            < max(float(deep.ndcg_at_k), float(wide.ndcg_at_k))
            + self.settings.eval.aggregate_ndcg_min_delta
        ):
            reasons.append("Hybrid NDCG guardrail")
        if ratio < self.settings.eval.minimum_wide_to_deep_rms_ratio:
            reasons.append("Wide RMS ratio")
        if (
            validation.hybrid_deep_top_k_change_rate
            < self.settings.eval.minimum_hybrid_deep_top_k_change_rate
        ):
            reasons.append("top-k change rate")
        return not reasons, ", ".join(reasons)

    def _publish_epoch_checkpoints(
        self,
        *,
        metrics: EpochMetrics,
        decision: StoppingDecision,
        lineage: dict[str, str],
        config_sha: str,
        run_id: str,
        scaler: Any,
        stopping: EarlyStoppingController,
    ) -> None:
        """Publish selected ``best.pt`` and the durable current ``last.pt``."""
        checkpoint_metrics = {
            "val_gauc": metrics.val_gauc,
            "val_ndcg_at_k": metrics.val_ndcg_at_k,
            "val_hr_at_k": metrics.val_hr_at_k,
            "train_loss": metrics.train_loss,
        }

        def publish(path: Path, checkpoint_kind: Literal["best", "last"]) -> None:
            CheckpointManager.save(
                path,
                model=self.model,
                optimizer=self.optimizer,
                scheduler=self.scheduler,
                epoch=metrics.epoch,
                metrics=checkpoint_metrics,
                checkpoint_kind=checkpoint_kind,
                lineage=lineage,
                training_signature_sha256=config_sha,
                comparison_signature_sha256=self.settings.comparison_signature_sha256(),
                training_variant=self.training_variant,
                model_schema_version=MODEL_SCHEMA_VERSION,
                run_id=run_id,
                scaler=scaler,
                stopping_state=stopping.state_dict(),
            )

        if decision.checkpoint_action is not CheckpointAction.NONE:
            publish(self.run_dir / "checkpoints" / "best.pt", "best")
        publish(self.run_dir / "checkpoints" / "last.pt", "last")

    def _append_history(self, metrics: EpochMetrics) -> None:
        path = self.run_dir / "training" / "history.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as destination:
            destination.write(json.dumps(asdict(metrics), sort_keys=True) + "\n")
            destination.flush()
            os.fsync(destination.fileno())

    def _write_terminal_summary(
        self,
        *,
        action: TerminalAction,
        reason: str,
        epochs_completed: int,
    ) -> None:
        path = self.run_dir / "training" / "summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "epochs_completed": epochs_completed,
                    "terminal_action": action.value,
                    "terminal_reason": reason,
                    "stop_reason": reason,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def _write_training_summary(
        self,
        *,
        stopping: EarlyStoppingController,
        history: list[EpochMetrics],
        action: TerminalAction,
        reason: str,
    ) -> None:
        """Write the complete terminal summary atomically."""
        path = self.run_dir / "training" / "summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "best_epoch": stopping.selected_epoch,
                    "best_val_ndcg_at_k": stopping.selected_ndcg,
                    "best_val_gauc": stopping.selected_gauc,
                    "best_val_hr_at_k": stopping.selected_hr,
                    "epochs_completed": len(history),
                    "stop_reason": reason,
                    "terminal_reason": reason,
                    "terminal_action": action.value,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        with temporary.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

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
            raise CatastrophicTrainingError("SBERT artifact contains NaN or Inf")

        prepared_split = prepare_split(snapshot, SplitName.VAL)
        catalog = self._prepare_catalog(snapshot, embeddings)
        stopping = EarlyStoppingController(
            patience=self.settings.train.early_stopping_patience,
            min_delta=self.settings.train.min_delta,
            minimum_gauc=0.50,
            max_wall_minutes=self.settings.train.max_wall_minutes,
        )
        best_path = self.run_dir / "checkpoints" / "best.pt"
        config_sha = _settings_sha256(self.settings)
        run_id = self.run_dir.name
        amp_enabled = self.device.type == "cuda"
        scaler = GradScaler("cuda", enabled=amp_enabled)
        self.scheduler = self._build_scheduler(len(train_loader))
        global_step = 0
        history: list[EpochMetrics] = []
        start_epoch = 1
        started_training = time.perf_counter()
        started_at = datetime.now(UTC)
        best_observed_gauc = -float("inf")
        best_observed_hr = -float("inf")
        best_observed_ndcg = -float("inf")

        if resume_from is not None:
            resume_state = self._restore_resume_state(
                resume_from,
                best_path=best_path,
                lineage=lineage,
                config_sha=config_sha,
                stopping=stopping,
                scaler=scaler,
            )
            start_epoch = resume_state.start_epoch
            global_step = resume_state.global_step
            history = list(resume_state.history)
            started_training -= resume_state.elapsed_seconds
            started_at -= timedelta(seconds=resume_state.elapsed_seconds)

        deep_wide_baseline = tuple(
            parameter.detach().clone() for parameter in self.model.wide_layer.parameters()
        )
        runtime = _TrainingRuntime(
            catalog=catalog,
            scaler=scaler,
            stopping=stopping,
            started_at=started_at,
            started_training=started_training,
            deep_wide_baseline=deep_wide_baseline,
        )
        if amp_enabled:
            torch.cuda.reset_peak_memory_stats(self.device)
        self._assert_parameters_finite(stage="before training")

        terminal_action = TerminalAction.COMPLETED
        stop_reason = "maximum epochs completed"
        try:
            for epoch in range(start_epoch, self.settings.train.max_epochs + 1):
                training = self._train_epoch(
                    epoch=epoch,
                    global_step=global_step,
                    train_loader=train_loader,
                    runtime=runtime,
                )
                global_step = training.global_step
                validation = self._validate_epoch(
                    val_evaluator,
                    snapshot,
                    prepared_split,
                    train_loader,
                )
                val_gauc = float(validation.hybrid_report.gauc)
                val_ndcg = float(validation.hybrid_report.ndcg_at_k)
                val_hr = float(validation.hybrid_report.hr_at_k)
                best_observed_gauc = max(best_observed_gauc, val_gauc)
                best_observed_hr = max(best_observed_hr, val_hr)
                best_observed_ndcg = max(best_observed_ndcg, val_ndcg)
                if epoch >= self.settings.train.diagnostic_warmup_epochs and (
                    best_observed_gauc < self.settings.train.diagnostic_minimum_gauc
                    or best_observed_hr < self.settings.train.diagnostic_minimum_hr_at_k
                    or best_observed_ndcg < self.settings.train.diagnostic_minimum_ndcg_at_k
                ):
                    reason = (
                        "diagnostic warmup floor failed: "
                        f"best_gauc={best_observed_gauc:.6f}, "
                        f"best_hr={best_observed_hr:.6f}, "
                        f"best_ndcg={best_observed_ndcg:.6f}"
                    )
                    publish_diagnostic_stop(
                        self.run_dir,
                        DiagnosticStopReport(
                            run_id=run_id,
                            epoch=epoch,
                            reason=reason,
                            best_gauc=best_observed_gauc,
                            best_hr_at_k=best_observed_hr,
                            best_ndcg_at_k=best_observed_ndcg,
                            thresholds={
                                "gauc": self.settings.train.diagnostic_minimum_gauc,
                                "hr_at_k": self.settings.train.diagnostic_minimum_hr_at_k,
                                "ndcg_at_k": self.settings.train.diagnostic_minimum_ndcg_at_k,
                            },
                        ),
                    )
                    raise DiagnosticQualityError(reason)
                checkpoint_eligible, eligibility_reason = self._checkpoint_eligibility(
                    epoch=epoch,
                    validation=validation,
                )
                decision = stopping.evaluate(
                    epoch,
                    val_gauc,
                    val_ndcg,
                    val_hr,
                    start_time=started_at,
                    current_time=datetime.now(UTC),
                    checkpoint_eligible=checkpoint_eligible,
                    eligibility_reason=eligibility_reason,
                )
                if decision.terminal_action is TerminalAction.FAILED:
                    raise CatastrophicTrainingError(decision.reason)
                if decision.terminal_action is TerminalAction.INTERRUPTED:
                    raise TrainingInterruptedError(decision.reason)
                metrics = self._build_epoch_metrics(
                    training=training,
                    validation=validation,
                    decision=decision,
                    stopping=stopping,
                )
                self._publish_epoch_checkpoints(
                    metrics=metrics,
                    decision=decision,
                    lineage=lineage,
                    config_sha=config_sha,
                    run_id=run_id,
                    scaler=scaler,
                    stopping=stopping,
                )
                history.append(metrics)
                self._append_history(metrics)
                terminal_action = metrics.terminal_action
                stop_reason = metrics.stopping_reason
                if decision.terminal_action is TerminalAction.STOP_PLATEAU:
                    break
        except DiagnosticQualityError as error:
            reason = str(error) or type(error).__name__
            self._write_terminal_summary(
                action=TerminalAction.FAILED,
                reason=reason,
                epochs_completed=len(history),
            )
            raise
        except CatastrophicTrainingError as error:
            reason = str(error) or type(error).__name__
            self._write_terminal_summary(
                action=TerminalAction.FAILED,
                reason=reason,
                epochs_completed=len(history),
            )
            raise
        except TrainingInterruptedError as error:
            reason = str(error) or type(error).__name__
            self._write_terminal_summary(
                action=TerminalAction.INTERRUPTED,
                reason=reason,
                epochs_completed=len(history),
            )
            raise

        if start_epoch > self.settings.train.max_epochs and history:
            terminal_action = TerminalAction.COMPLETED
            stop_reason = "already_complete"
        if not best_path.exists():
            raise DiagnosticQualityError("training did not produce an eligible best checkpoint")
        self._write_training_summary(
            stopping=stopping,
            history=history,
            action=terminal_action,
            reason=stop_reason,
        )
        CheckpointManager.load(
            best_path,
            model=self.model,
            expected_lineage=lineage,
            expected_training_signature=config_sha,
            expected_comparison_signature=self.settings.comparison_signature_sha256(),
            expected_model_schema_version=MODEL_SCHEMA_VERSION,
            expected_checkpoint_kind="best",
        )
        return TrainResult(
            run_id=run_id,
            best_epoch=stopping.selected_epoch,
            best_gauc=stopping.selected_gauc,
            best_ndcg_at_k=stopping.selected_ndcg,
            best_hr_at_k=stopping.selected_hr,
            history=tuple(history),
            checkpoint_path=best_path,
            stop_reason=stop_reason,
            terminal_action=terminal_action,
            terminal_reason=stop_reason,
        )
