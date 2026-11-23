"""Stage 4: train every method and score it on VALIDATION. Never reads TEST.

Each unit writes ``<work_root>/validation/<unit>/result.json`` (metrics, history) and
``per_user_metrics.npz``; a unit that already has ``result.json`` is skipped, so a run can resume.

Methods: MostPop, ItemKNN, Deep (two-tower), Rule-only, Hybrid (lambda grid), Wide&Deep (wide
learning-rate grid on the first seed, then the remaining seeds), BPR-MF and LightGCN (RecBole).
"""

from __future__ import annotations

import json
import os
import time
import traceback

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import common
import numpy as np
import torch
from fast_paths import FastEvaluator, batched_scores, promote_to_fast, wd_batched_scores
from scoring import ItemKnn, RuleScores, mostpop_counts, organic_pairs, recbole_config, recbole_rows

from hybrid_recsys.models.confirmatory import (
    ConfirmatoryTwoTowerConfig,
    build_confirmatory_two_tower,
)
from hybrid_recsys.models.wd_original import WideDeepOriginal, sampled_bce
from hybrid_recsys.training.deep import build_train_examples, train_deep_epoch
from hybrid_recsys.training.runtime import deterministic, recbole_epoch_trainer

DEEP_CONFIG = ConfirmatoryTwoTowerConfig(128, 256, 4)


class Run:
    def __init__(self, config: common.PipelineConfig, smoke: bool):
        self.config, self.smoke = config, smoke
        self.device = common.device(config)
        self.root = config.validation_root.parent / ("validation_smoke" if smoke else "validation")
        self.root.mkdir(parents=True, exist_ok=True)
        self.started = time.perf_counter()
        self.inputs = common.inputs(config)
        self.protocol = self.inputs.validation_protocol
        self.evaluator = FastEvaluator(self.protocol)
        self.examples = list(build_train_examples(self.inputs.snapshot, self.inputs.item_id_map))
        if smoke:
            self.examples = self.examples[:4096]
        self.num_users = self.inputs.snapshot.manifest.num_users
        self.num_items = len(self.protocol.candidate_item_ids)
        self.deep_epochs = 2 if smoke else config.deep_epochs
        self.log(f"users={self.num_users} items={self.num_items} examples={len(self.examples)}")

    def log(self, text: str) -> None:
        print(f"[{time.perf_counter() - self.started:9.1f}s] {text}", flush=True)

    def done(self, unit: str):
        path = self.root / unit / "result.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def finish(self, unit: str, rows, **payload):
        folder = self.root / unit
        folder.mkdir(exist_ok=True)
        np.savez_compressed(
            folder / "per_user_metrics.npz",
            user_ids=np.asarray(self.evaluator.user_ids),
            ndcg=np.asarray([r.ndcg for r in rows]),
            hr=np.asarray([r.hit_rate for r in rows]),
            gauc=np.asarray([np.nan if r.gauc is None else r.gauc for r in rows]),
        )
        (folder / "result.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
        summary = {k: payload[k] for k in ("metrics", "best_epoch", "epochs_run") if k in payload}
        self.log(f"{unit}: {summary}")
        return payload

    def shuffled(self, seed: int, epoch: int):
        order = np.random.default_rng(seed * 1000 + epoch).permutation(len(self.examples))
        return [self.examples[i] for i in order.tolist()]

    def release(self) -> None:
        if self.device.type == "cuda":
            torch.cuda.empty_cache()


def mostpop(run: Run) -> None:
    if run.done("mostpop"):
        return
    counts = mostpop_counts(run.inputs.snapshot, run.inputs.item_id_map, run.num_items)
    rows, metrics = run.evaluator.evaluate((p, counts) for p in range(len(run.evaluator.user_ids)))
    run.finish("mostpop", rows, metrics=metrics)


def itemknn(run: Run) -> None:
    unit = f"itemknn-k{run.config.itemknn_k}"
    if run.done(unit):
        return
    knn = ItemKnn(
        run.inputs.snapshot,
        run.inputs.item_id_map,
        run.num_items,
        run.evaluator.user_ids,
        run.config.itemknn_k,
    )
    rows, metrics = run.evaluator.evaluate(
        knn.rows(organic_pairs(run.inputs.snapshot, run.inputs.item_id_map, ("train",)))
    )
    run.finish(unit, rows, metrics=metrics, k=run.config.itemknn_k)


def build_deep(run: Run, seed: int):
    deterministic(seed)
    model = build_confirmatory_two_tower(
        num_users=run.num_users, features=run.inputs.features, config=DEEP_CONFIG, seed=seed
    ).to(run.device)
    promote_to_fast(model)
    return model


def deep(run: Run) -> None:
    for seed in run.config.seeds:
        unit = f"deep-s{seed}"
        if run.done(unit):
            continue
        model = build_deep(run, seed)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.00001)
        folder = run.root / unit
        folder.mkdir(exist_ok=True)
        best, best_epoch, best_rows, history = -np.inf, None, None, []
        for epoch in range(1, run.deep_epochs + 1):
            trained = train_deep_epoch(
                model, optimizer, run.shuffled(seed, epoch), epoch=epoch, device=run.device
            )
            rows, metrics = run.evaluator.evaluate(
                batched_scores(model, run.evaluator.user_ids, run.evaluator.histories)
            )
            history.append(
                {"epoch": epoch, "loss": trained["mean_pairwise_loss"], "metrics": metrics}
            )
            if metrics["NDCG@10"] > best:
                best, best_epoch, best_rows = metrics["NDCG@10"], epoch, rows
                torch.save({k: v.cpu() for k, v in model.state_dict().items()}, folder / "best.pt")
        run.finish(
            unit,
            best_rows,
            metrics=history[best_epoch - 1]["metrics"],
            best_epoch=best_epoch,
            seed=seed,
            history=history,
        )
        del model, optimizer
        run.release()


def hybrid(run: Run) -> None:
    rules = RuleScores(run.config, run.evaluator, tuple(run.protocol.candidate_item_ids))
    if not run.done("rule"):
        rows, metrics = run.evaluator.evaluate(enumerate(rules.raw))
        run.finish("rule", rows, metrics=metrics)
    for seed in run.config.seeds:
        pending = [v for v in run.config.lambda_grid if not run.done(f"hybrid-l{v}-s{seed}")]
        if not pending:
            continue
        model = build_deep(run, seed)
        model.load_state_dict(
            torch.load(run.root / f"deep-s{seed}/best.pt", map_location=run.device)
        )
        z_deep = {
            p: common.zscore(s, rules.masks[p])
            for p, s in batched_scores(model, run.evaluator.user_ids, run.evaluator.histories)
        }
        for value in pending:
            rows, metrics = run.evaluator.evaluate(
                (p, z_deep[p] + value * rules.z[p]) for p in range(len(rules.z))
            )
            run.finish(
                f"hybrid-l{value}-s{seed}", rows, metrics=metrics, lambda_value=value, seed=seed
            )
        del model
        run.release()


def wd_unit(run: Run, seed: int, lr_wide: float):
    unit = f"wd-lr{lr_wide}-s{seed}"
    done = run.done(unit)
    if done:
        return done
    deterministic(seed)
    features = run.inputs.features
    model = WideDeepOriginal(run.num_users, features.text_embeddings, features.category_ids).to(
        run.device
    )
    optimizer = model.optimizer(lr_wide)
    folder = run.root / unit
    folder.mkdir(exist_ok=True)
    best, best_epoch, best_rows, history, stalled = -np.inf, None, None, [], 0
    for epoch in range(1, (2 if run.smoke else run.config.wd_max_epochs) + 1):
        order = run.shuffled(seed, epoch)
        model.train()
        total, count = 0.0, 0
        for group_start in range(0, len(order), 1024):
            group = order[group_start : group_start + 1024]
            optimizer.zero_grad(set_to_none=True)
            for micro_start in range(0, len(group), 256):
                loss, pairs = sampled_bce(
                    model,
                    group[micro_start : micro_start + 256],
                    negative_seed=epoch * 1_000_000 + group_start + micro_start,
                    device=run.device,
                )
                if not bool(torch.isfinite(loss)):
                    raise RuntimeError("non-finite W&D loss")
                (loss / (len(group) * 5)).backward()
                total += float(loss.detach())
                count += pairs
            optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        rows, metrics = run.evaluator.evaluate(
            wd_batched_scores(model, run.evaluator.user_ids, run.evaluator.histories)
        )
        history.append({"epoch": epoch, "loss": total / count, "metrics": metrics})
        if metrics["NDCG@10"] > best:
            best, best_epoch, best_rows, stalled = metrics["NDCG@10"], epoch, rows, 0
            torch.save({k: v.cpu() for k, v in model.state_dict().items()}, folder / "best.pt")
        else:
            stalled += 1
            if stalled >= run.config.wd_patience:
                break
    result = run.finish(
        unit,
        best_rows,
        metrics=history[best_epoch - 1]["metrics"],
        best_epoch=best_epoch,
        seed=seed,
        lr_wide=lr_wide,
        epochs_run=len(history),
        history=history,
    )
    del model, optimizer
    run.release()
    return result


def wide_deep(run: Run) -> None:
    first, *rest = run.config.seeds
    grid = run.config.wd_lr_grid
    results = [wd_unit(run, first, lr) for lr in grid]
    selected = max(range(len(grid)), key=lambda i: (results[i]["metrics"]["NDCG@10"], -i))
    for seed in rest:
        wd_unit(run, seed, grid[selected])


def reference(run: Run, method: str) -> None:
    from recbole.data import create_dataset, data_preparation  # type: ignore
    from recbole.utils import init_seed  # type: ignore

    for seed in run.config.seeds:
        unit = f"{method.lower()}-s{seed}"
        if run.done(unit):
            continue
        folder = run.root / unit
        folder.mkdir(exist_ok=True)
        pairs = sorted(organic_pairs(run.inputs.snapshot, run.inputs.item_id_map, ("train",)))
        torch.use_deterministic_algorithms(False)
        config, model_class = recbole_config(
            run.config, method, seed, pairs, run.num_users, run.num_items, folder / "native"
        )
        init_seed(seed, True)
        dataset = create_dataset(config)
        train_data, valid_data, test_data = data_preparation(config, dataset)
        if len(valid_data) or len(test_data):
            raise RuntimeError("RecBole split kept non-TRAIN rows")
        model = model_class(config, train_data.dataset).to(config["device"])
        trainer = recbole_epoch_trainer(config, model)
        best, best_epoch, best_rows, history, patience = None, None, None, [], 0
        for epoch_index in range(2 if run.smoke else run.config.reference_max_epochs):
            loss = trainer._train_epoch(train_data, epoch_index, show_progress=False)
            rows, metrics = run.evaluator.evaluate(
                recbole_rows(
                    model, method, dataset, run.evaluator.user_ids, run.num_items, config["device"]
                )
            )
            model.train()
            total = sum(loss) if isinstance(loss, tuple) else loss
            if not np.isfinite(float(total)):
                raise RuntimeError("non-finite baseline loss")
            history.append({"epoch": epoch_index + 1, "loss": float(total), "metrics": metrics})
            if best is None or metrics["NDCG@10"] > best:
                best, best_epoch, best_rows, patience = metrics["NDCG@10"], epoch_index + 1, rows, 0
                torch.save({k: v.cpu() for k, v in model.state_dict().items()}, folder / "best.pt")
            else:
                patience += 1
            if patience >= run.config.reference_patience:
                break
        run.finish(
            unit,
            best_rows,
            method=method,
            seed=seed,
            metrics=history[best_epoch - 1]["metrics"],
            best_epoch=best_epoch,
            epochs_run=len(history),
            history=history,
        )
        del model
        run.release()


PHASES = {
    "mostpop": mostpop,
    "itemknn": itemknn,
    "deep": deep,
    "hybrid": hybrid,
    "wd": wide_deep,
    "bpr": lambda run: reference(run, "BPR"),
    "lightgcn": lambda run: reference(run, "LightGCN"),
}


def main() -> None:
    parser = common.parser(__doc__.splitlines()[0])
    parser.add_argument("--smoke", action="store_true", help="2 epochs on 4,096 examples")
    parser.add_argument("--phases", default=",".join(PHASES))
    args = parser.parse_args()
    run = Run(common.load_config(args.config), args.smoke)
    for name in args.phases.split(","):
        run.log(f"phase {name}")
        try:
            PHASES[name](run)
        except Exception:
            run.log(f"phase {name} FAILED\n{traceback.format_exc()}")
            raise
    run.log("complete")


if __name__ == "__main__":
    main()
