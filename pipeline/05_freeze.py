"""Stage 5: freeze the configuration on VALIDATION before TEST is opened.

Selects the Hybrid lambda (mean NDCG@10 over seeds) and the Wide&Deep wide learning rate (first
seed), checks the cohort gates, hashes every checkpoint that TEST scoring will load, and writes
``<work_root>/freeze.json``. Refuses to overwrite an existing freeze. Reads no TEST event.
"""

from __future__ import annotations

import json
from pathlib import Path

import common
import numpy as np

from hybrid_recsys.hashing import sha256_file

HERE = Path(__file__).resolve().parent


def load(root: Path, unit: str) -> dict:
    path = root / unit / "result.json"
    if not path.exists():
        raise SystemExit(f"missing validation unit {unit}")
    with np.load(root / unit / "per_user_metrics.npz") as stored:
        if not (np.isfinite(stored["ndcg"]).all() and np.isfinite(stored["hr"]).all()):
            raise SystemExit(f"non-finite per-user metric in {unit}")
    return json.loads(path.read_text(encoding="utf-8"))


def summary(root: Path, units: list[str]) -> dict:
    rows = [load(root, u) for u in units]
    return {
        **{m: float(np.mean([r["metrics"][m] for r in rows])) for m in common.METRICS},
        "per_seed_ndcg": [r["metrics"]["NDCG@10"] for r in rows],
        "best_epochs": [r.get("best_epoch") for r in rows],
    }


def main() -> None:
    args = common.parser(__doc__.splitlines()[0]).parse_args()
    config = common.load_config(args.config)
    root, seeds = config.validation_root, config.seeds
    if config.freeze_file.exists():
        raise SystemExit(f"{config.freeze_file} already exists; a freeze is written once")
    means = {
        v: float(np.mean([load(root, f"hybrid-l{v}-s{s}")["metrics"]["NDCG@10"] for s in seeds]))
        for v in config.lambda_grid
    }
    lambda_value = max(config.lambda_grid, key=lambda v: (means[v], -v))
    wd_scores = {
        lr: load(root, f"wd-lr{lr}-s{seeds[0]}")["metrics"]["NDCG@10"] for lr in config.wd_lr_grid
    }
    wd_lr = max(config.wd_lr_grid, key=lambda lr: (wd_scores[lr], -lr))

    protocol = common.inputs(config).validation_protocol
    positives = [protocol.case_for(user).positive_item_ids for user in protocol.eligible_user_ids]
    counts = {
        "eligible_users": len(positives),
        "novel_positive_events": sum(map(len, positives)),
        "distinct_target_items": len(set().union(*positives)),
    }
    cohort_pass = all(
        counts[name.removesuffix("_min")] >= limit for name, limit in config.cohort_gates.items()
    )
    freeze = {
        "stage": "validation_freeze",
        "test_rows_used": 0,
        "selected": {"lambda": lambda_value, "wd_lr_wide": wd_lr},
        "selection_values": {
            "hybrid_mean_ndcg": {str(k): v for k, v in means.items()},
            "wd_ndcg_first_seed": {str(k): v for k, v in wd_scores.items()},
        },
        "validation": {
            "MostPop": summary(root, ["mostpop"]),
            "ItemKNN": summary(root, [f"itemknn-k{config.itemknn_k}"]),
            "Rule-only": summary(root, ["rule"]),
            "BPR-MF": summary(root, [f"bpr-s{s}" for s in seeds]),
            "LightGCN": summary(root, [f"lightgcn-s{s}" for s in seeds]),
            "Deep-only": summary(root, [f"deep-s{s}" for s in seeds]),
            "W&D": summary(root, [f"wd-lr{wd_lr}-s{s}" for s in seeds]),
            "Hybrid": summary(root, [f"hybrid-l{lambda_value}-s{s}" for s in seeds]),
        },
        "checkpoints": {
            unit: sha256_file(root / unit / "best.pt")
            for unit in [
                f"{name}-s{s}"
                for name in ("deep", "bpr", "lightgcn", f"wd-lr{wd_lr}")
                for s in seeds
            ]
        },
        "code": {
            name: sha256_file(HERE / name) for name in sorted(p.name for p in HERE.glob("*.py"))
        },
        "candidate_order_sha256": protocol.manifest.candidate_order_sha256,
        "cohort": {"counts": counts, "gates": config.cohort_gates, "pass": cohort_pass},
    }
    config.freeze_file.parent.mkdir(parents=True, exist_ok=True)
    config.freeze_file.write_text(json.dumps(freeze, indent=1), encoding="utf-8")
    print(
        json.dumps(
            {k: freeze[k] for k in ("selected", "selection_values", "cohort", "validation")},
            indent=1,
        )
    )
    if not cohort_pass:
        raise SystemExit("cohort gates failed; TEST must not be opened")


if __name__ == "__main__":
    main()
