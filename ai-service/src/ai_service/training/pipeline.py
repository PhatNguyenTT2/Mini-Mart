"""End-to-End Pipeline Execution CLI Entrypoint."""

from pathlib import Path
import sys
from torch.utils.data import DataLoader

from ai_service.config import get_settings
from ai_service.data.sources import SyntheticDatasetSource, PostgresDatasetSource
from ai_service.data.snapshot import SnapshotBuilder, load_snapshot
from ai_service.data.features import precompute_embeddings
from ai_service.data.rules import AprioriRuleMiner
from ai_service.data.dataset import HybridImplicitDataset, collate_candidate_groups
from ai_service.models.two_tower_wide_deep import HybridTwoTowerModel
from ai_service.training.trainer import Trainer
from ai_service.evaluation.full_catalog import FullCatalogEvaluator
from ai_service.evaluation.baselines import run_seven_way_baselines
from ai_service.export.onnx import export_onnx_bundle


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    print("Starting AI Service Production Pipeline Execution (v2.0.0)...")
    settings = get_settings()

    # 1. Load Data Source (Attempt Postgres, fallback to Synthetic)
    print("Step 1: Loading Raw Data Source...")
    try:
        source = PostgresDatasetSource(settings)
        raw_data = source.load(settings.data.store_id)
        print("   [OK] Loaded data directly from PostgreSQL Supabase Cloud.")
    except Exception as err:
        print(f"   [INFO] PostgreSQL load unavailable ({err}). Using Synthetic Dataset Source.")
        source = SyntheticDatasetSource(settings)
        raw_data = source.load(settings.data.store_id)

    # 2. Build Snapshot with Temporal Split Invariant Verification
    print("Step 2: Building Dataset Snapshot (scaled-v1)...")
    builder = SnapshotBuilder(settings)
    snapshot = builder.build(raw_data, snapshot_id="scaled-v1")
    print(f"   [OK] Snapshot built successfully! Total events: {snapshot.manifest.num_events:,}")

    # 3. Precompute Text Embeddings & Mine Apriori Rules
    print("Step 3: Precomputing SBERT Embeddings & Apriori Rules...")
    precompute_embeddings(snapshot.catalog_df, snapshot.snapshot_dir)
    miner = AprioriRuleMiner(
        min_support_count=settings.data.min_rule_count,
        min_lift=settings.data.min_rule_lift,
    )
    rule_store = miner.mine(snapshot)
    print(f"   [OK] Precomputed SBERT embeddings & mined rules.")

    # 4. Initialize DataLoader & Train Hybrid Two-Tower Model
    print("Step 4: Training Hybrid Two-Tower Model...")
    train_dataset = HybridImplicitDataset(snapshot, rule_store, split="train")
    train_loader = DataLoader(
        train_dataset,
        batch_size=settings.train.batch_size,
        shuffle=True,
        collate_fn=collate_candidate_groups,
    )

    model = HybridTwoTowerModel(settings=settings)
    trainer = Trainer(model=model, settings=settings)
    val_evaluator = FullCatalogEvaluator(settings=settings)

    train_res = trainer.fit(train_loader, snapshot, val_evaluator=val_evaluator)
    print(f"   [OK] Model training finished! Best epoch: {train_res.best_epoch}, Best Val GAUC: {train_res.best_gauc:.4f}")

    # 5. Run 7-Way Baseline Evaluation Harness
    print("Step 5: Running 7-Way Baselines Evaluation...")
    baseline_report = run_seven_way_baselines(model, snapshot, split="test", k=settings.eval.k, settings=settings)
    print(f"   [OK] Evaluation complete! Test GAUC: {baseline_report.baselines['Proposed Hybrid (Ours)'].gauc:.4f}")

    # 6. Export ONNX Bundle
    print("Step 6: Exporting ONNX Bundle Artifacts...")
    bundle_manifest = export_onnx_bundle(model, settings=settings)
    print(f"   [OK] ONNX Bundle exported successfully (Checksum: {bundle_manifest.onnx_recommender_checksum})")

    print("\nAI Pipeline execution finished successfully 100%!")


if __name__ == "__main__":
    main()
