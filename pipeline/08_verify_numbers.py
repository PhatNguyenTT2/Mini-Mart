"""Stage 8: independent verification and descriptive numbers for the opened TEST. Selects nothing.

Re-scores every model from its frozen checkpoint, recomputes NDCG@10, HR@10 and GAUC with a ranking
and metric implementation written here (independent of the evaluator used in stage 6), and reports
the largest per-user difference against ``test/per_user_metrics.npz``. Also reports rule coverage,
seed spread and an exploratory transition-group bootstrap (Holm-adjusted). Writes
``test/results_final.json``.
"""

from __future__ import annotations

import hashlib
import json
import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import common
import numpy as np
from fast_paths import FastEvaluator, batched_scores, wd_batched_scores
from scipy.stats import rankdata
from scoring import RuleScores, load_deep, load_wide_deep, reference_test_rows

from hybrid_recsys.statistics.bootstrap import holm_adjust
from hybrid_recsys.training.inputs import build_test_protocol


class HandMetrics:
    """Own ranking (score desc, raw id asc) and metrics, kept apart from the evaluator."""

    def __init__(self, evaluator):
        self.raw, self.seen, self.positive = evaluator.raw, evaluator.seen, evaluator.positive

    def one(self, position, scores):
        values = np.asarray(scores, dtype=np.float64)
        keep = np.ones(len(values), dtype=bool)
        keep[self.seen[position]] = False
        candidates = np.flatnonzero(keep)
        top = candidates[np.lexsort((self.raw[candidates], -values[candidates]))[:10]]
        positives = set(self.positive[position].tolist())
        hits = [1 if int(item) in positives else 0 for item in top]
        dcg = sum(hit / np.log2(rank + 2) for rank, hit in enumerate(hits))
        ideal = sum(1 / np.log2(rank + 2) for rank in range(min(10, len(positives))))
        is_positive = np.isin(candidates, self.positive[position])
        ranks = rankdata(values[candidates])
        count = int(is_positive.sum())
        auc = (ranks[is_positive].sum() - count * (count + 1) / 2) / (
            count * (len(candidates) - count)
        )
        return dcg / ideal, float(any(hits)), auc, top


def transition_mask(snapshot, users, seed=42, count=2500):
    raw = [int(value) for value in snapshot.raw_user_ids]
    key = lambda u: (int.from_bytes(hashlib.sha256(f"{seed}:{u}".encode()).digest()[:4], "big"), u)
    assigned = set(sorted(raw, key=key)[:count])
    return np.array([raw[u] in assigned for u in users])


def main() -> None:
    args = common.parser(__doc__.splitlines()[0]).parse_args()
    config = common.load_config(args.config)
    seeds, device = config.seeds, common.device(config)
    freeze = json.loads(config.freeze_file.read_text(encoding="utf-8"))
    stored = np.load(config.test_root / "per_user_metrics.npz")
    report = json.loads((config.test_root / "test_results.json").read_text(encoding="utf-8"))
    groups = json.loads((config.test_root / "results_groups.json").read_text(encoding="utf-8"))
    inputs = common.inputs(config)
    snapshot = common.snapshot_with_test(config)
    test = build_test_protocol(snapshot, inputs.validation_protocol, inputs.item_id_map)
    evaluator = FastEvaluator(test)
    hand, users = HandMetrics(evaluator), evaluator.user_ids
    num_items = len(test.candidate_item_ids)
    if tuple(stored["user_ids"].tolist()) != tuple(users):
        raise SystemExit("stored user order differs")

    worst = {}

    def compare(name, rows):
        got = np.zeros((len(users), 3))
        tops = []
        for position, scores in rows:
            ndcg, hr, auc, top = hand.one(position, scores)
            got[position] = ndcg, hr, auc
            tops.append(top)
        worst[name] = {
            m: float(np.abs(got[:, i] - stored[f"{name}|{m}"]).max())
            for i, m in enumerate(common.METRICS)
        }
        print(name, worst[name], flush=True)
        return tops

    rules = RuleScores(config, evaluator, tuple(test.candidate_item_ids))
    shares, tie_shares = [], []
    for position, values in enumerate(rules.raw):
        mask = rules.masks[position]
        shares.append(float((values[mask] > 0).mean()))
        positive = np.zeros(num_items, dtype=bool)
        positive[evaluator.positive[position]] = True
        negative = mask & ~positive
        tie_shares.append(
            int((values[positive] == 0).sum())
            * int((values[negative] == 0).sum())
            / (int(positive.sum()) * int(negative.sum()))
        )
    compare("Rule-only", enumerate(rules.raw))
    nonzero = [values > 0 for values in rules.raw]

    lambda_value, lr_wide = freeze["selected"]["lambda"], freeze["selected"]["wd_lr_wide"]
    hybrid_rule_items = []
    for seed in seeds:
        model = load_deep(config, inputs, seed, device)
        scores = {p: s.copy() for p, s in batched_scores(model, users, evaluator.histories)}
        compare(f"Deep-only s{seed}", scores.items())
        tops = compare(
            f"Hybrid s{seed}",
            (
                (p, common.zscore(s, rules.masks[p]) + lambda_value * rules.z[p])
                for p, s in scores.items()
            ),
        )
        hybrid_rule_items.append(
            float(np.mean([nonzero[p][top].sum() for p, top in enumerate(tops)]))
        )
        del model, scores
        wide = load_wide_deep(config, inputs, seed, lr_wide, device)
        compare(f"W&D s{seed}", wd_batched_scores(wide, users, evaluator.histories))
        del wide
        compare(
            f"BPR-MF s{seed}", reference_test_rows(config, "BPR", seed, inputs, users, num_items)
        )
        compare(
            f"LightGCN s{seed}",
            reference_test_rows(config, "LightGCN", seed, inputs, users, num_items),
        )

    def matrix(name, metric):
        if f"{name} s{seeds[0]}|{metric}" in stored:
            return np.stack([stored[f"{name} s{s}|{metric}"] for s in seeds])
        return np.stack([stored[f"{name}|{metric}"]] * len(seeds))

    transition = transition_mask(snapshot, users)
    assigned, others = np.flatnonzero(transition), np.flatnonzero(~transition)
    replicates = config.bootstrap_replicates
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([*config.bootstrap_seed, 2])))
    schedule = [
        (
            rng.integers(0, len(assigned), len(assigned)),
            rng.integers(0, len(others), len(others)),
            rng.integers(0, len(seeds), len(seeds)),
        )
        for _ in range(replicates)
    ]
    exploratory = {}
    for versus in ("Rule-only", "ItemKNN"):
        for metric in ("NDCG@10", "HR@10"):
            delta = matrix("Hybrid", metric) - matrix(versus, metric)
            a, n = delta[:, assigned], delta[:, others]
            draws = {"assigned": np.empty(replicates), "non_assigned": np.empty(replicates)}
            for index, (ua, un, s) in enumerate(schedule):
                draws["assigned"][index] = a[np.ix_(s, ua)].mean()
                draws["non_assigned"][index] = n[np.ix_(s, un)].mean()
            draws["interaction"] = draws["non_assigned"] - draws["assigned"]
            observed = {"assigned": float(a.mean()), "non_assigned": float(n.mean())}
            observed["interaction"] = observed["non_assigned"] - observed["assigned"]
            for part, effects in draws.items():
                low, high = np.quantile(effects, [0.025, 0.975])
                extreme = int(
                    np.count_nonzero(np.abs(effects - observed[part]) >= abs(observed[part]))
                )
                exploratory[f"{versus}|{metric}|{part}"] = {
                    "difference": observed[part],
                    "ci95": [float(low), float(high)],
                    "raw_p": min(1.0, (1 + extreme) / (replicates + 1)),
                }
    for key, value in holm_adjust({k: v["raw_p"] for k, v in exploratory.items()}).items():
        exploratory[key]["holm_p"] = value

    final = {
        "stage": "verification and descriptive numbers on the opened TEST; nothing selected",
        "verification_max_abs_diff": worst,
        "verification_worst": {m: max(row[m] for row in worst.values()) for m in common.METRICS},
        "seed_sd": {
            name: {m: float(np.std(row[m]["seed_means"], ddof=1)) for m in common.METRICS}
            for name, row in report["methods"].items()
        },
        "primary_by_seed": (matrix("Hybrid", "NDCG@10") - matrix("ItemKNN", "NDCG@10"))
        .mean(axis=1)
        .tolist(),
        "exploratory": exploratory,
        "coverage": {
            "median_scored_share": float(np.median(shares)),
            "iqr_scored_share": [
                float(np.quantile(shares, 0.25)),
                float(np.quantile(shares, 0.75)),
            ],
            "hybrid_top10_rule_items_by_seed": hybrid_rule_items,
            "mean_tied_pair_share": float(np.mean(tie_shares)),
            "users_with_antecedent": rules.users_with_antecedent,
        },
        "groups": groups["means"],
        "group_sizes": groups["sizes"],
    }
    (config.test_root / "results_final.json").write_text(
        json.dumps(final, indent=1), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: final[k] for k in ("verification_worst", "primary_by_seed", "coverage")}, indent=1
        )
    )


if __name__ == "__main__":
    main()
