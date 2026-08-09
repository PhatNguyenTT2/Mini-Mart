"""Training Engine for Hybrid Two-Tower Wide & Deep Model."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Any
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from ai_service.config import Settings, RUN_ARTIFACTS_DIR
from ai_service.errors import ModelTrainingError
from ai_service.contracts import RunManifestV2, ModelVariant
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.data.snapshot import Snapshot
from ai_service.evaluation.full_catalog import FullCatalogEvaluator, EvaluationReport


@dataclass
class EpochMetrics:
    epoch: int
    train_loss: float
    val_gauc: float
    val_hr10: float
    val_ndcg10: float
    is_best: bool


@dataclass
class TrainResult:
    best_epoch: int
    best_gauc: float
    metrics_history: List[EpochMetrics]
    checkpoint_path: Path


class Trainer:
    """Trainer engine with mandatory ValidationEvaluator and early stopping."""

    def __init__(
        self,
        model: HybridTwoTowerModel,
        settings: Optional[Settings] = None,
        run_dir: Optional[Path] = None,
    ):
        if settings is None:
            settings = Settings()

        self.settings = settings
        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

        self.model = model.to(self.device)
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=settings.train.lr,
            weight_decay=settings.train.weight_decay,
        )
        self.criterion = nn.BCEWithLogitsLoss(reduction="none")

        if run_dir is None:
            run_dir = RUN_ARTIFACTS_DIR / "main"
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)

        self.best_gauc = -1.0
        self.best_epoch = 0
        self.metrics_history: List[EpochMetrics] = []

    def fit(
        self,
        train_loader: DataLoader,
        snapshot: Snapshot,
        val_evaluator: Optional[FullCatalogEvaluator] = None,
    ) -> TrainResult:
        """Run model optimization epochs."""
        if val_evaluator is None:
            val_evaluator = FullCatalogEvaluator(self.settings)

        # Precompute catalog features on device for fast training batch lookup
        catalog_df = snapshot.catalog_df.sort_values(by="internal_product_id").reset_index(drop=True)
        cat_tensor = torch.tensor(catalog_df["internal_leaf_category_id"].values, dtype=torch.long, device=self.device)
        price_tensor = torch.tensor(catalog_df["price_bucket_id"].values, dtype=torch.long, device=self.device)

        sbert_path = snapshot.snapshot_dir / "sbert_embeddings.npy"
        if sbert_path.exists():
            sbert_np = np.load(sbert_path)
        else:
            sbert_np = np.zeros((len(catalog_df), 768), dtype=np.float32)
        sbert_tensor = torch.tensor(sbert_np, dtype=torch.float32, device=self.device)

        patience = self.settings.train.early_stopping_patience
        no_improve = 0

        for epoch in range(1, self.settings.train.max_epochs + 1):
            self.model.train()
            if hasattr(train_loader.dataset, "set_epoch"):
                train_loader.dataset.set_epoch(epoch)

            total_loss = 0.0
            total_batches = 0

            for batch in train_loader:
                user_idx = batch.user_idx.to(self.device)
                persona_idx = batch.persona_idx.to(self.device)
                cand_idx = batch.candidate_item_idx.to(self.device)
                ctx_present = batch.context_present.to(self.device)
                log_lift = batch.log_lift.to(self.device)
                labels = batch.labels.to(self.device)
                sample_weight = batch.sample_weight.to(self.device)

                # Batch lookup candidate features [B, 5, 768]
                cand_sbert = sbert_tensor[cand_idx]
                cand_cat = cat_tensor[cand_idx]
                cand_price = price_tensor[cand_idx]

                self.optimizer.zero_grad()

                logits = self.model(
                    user_idx=user_idx,
                    persona_idx=persona_idx,
                    candidate_sbert=cand_sbert,
                    candidate_cat=cand_cat,
                    candidate_price=cand_price,
                    log_lift=log_lift,
                    context_present=ctx_present,
                    include_wide=True,
                )

                raw_loss = self.criterion(logits, labels)
                weighted_loss = (raw_loss * sample_weight.unsqueeze(-1)).mean()

                weighted_loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=self.settings.train.max_grad_norm)
                self.optimizer.step()

                total_loss += weighted_loss.item()
                total_batches += 1

            avg_train_loss = total_loss / max(total_batches, 1)

            # Mandatory real Full-Catalog Validation Evaluation
            val_report = val_evaluator.evaluate(
                model=self.model,
                snapshot=snapshot,
                split="val",
                k=self.settings.eval.k,
                variant=ModelVariant.HYBRID,
                device=self.device,
            )

            val_gauc = val_report.gauc
            is_best = val_gauc > (self.best_gauc + self.settings.train.min_delta)

            if is_best:
                self.best_gauc = val_gauc
                self.best_epoch = epoch
                no_improve = 0
                torch.save(self.model.state_dict(), self.run_dir / "best.pt")
            else:
                no_improve += 1

            self.metrics_history.append(
                EpochMetrics(
                    epoch=epoch,
                    train_loss=avg_train_loss,
                    val_gauc=val_gauc,
                    val_hr10=val_report.hr10,
                    val_ndcg10=val_report.ndcg10,
                    is_best=is_best,
                )
            )

            if no_improve >= patience:
                break

        # Save last checkpoint
        torch.save(self.model.state_dict(), self.run_dir / "last.pt")

        # Reload best checkpoint weights into model memory before returning
        best_ckpt = self.run_dir / "best.pt"
        if best_ckpt.exists():
            self.model.load_state_dict(torch.load(best_ckpt, map_location=self.device))

        return TrainResult(
            best_epoch=self.best_epoch,
            best_gauc=self.best_gauc,
            metrics_history=self.metrics_history,
            checkpoint_path=best_ckpt,
        )
