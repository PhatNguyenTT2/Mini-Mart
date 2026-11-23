"""Stage 6: score the sealed TEST split once with the frozen configuration.

``--dry-run`` checks the whole scoring path on the VALIDATION split and prints no metric.
``--open`` scores TEST. It requires ``freeze.json``, the sealed TEST file whose hash matches the
custody receipt, and ``open_authorized.json`` (written by a person after reviewing the freeze). It
refuses to run when ``<work_root>/test`` already exists: TEST is opened exactly once.

Writes ``test/per_user_metrics.npz`` and ``test/test_results.json`` (means, seed means, paired
bootstrap contrasts of Hybrid against every comparator, Holm-adjusted p-values).
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import common
import numpy as np
from fast_paths import FastEvaluator, batched_scores
from scoring import (
    ItemKnn,
    RuleScores,
    load_deep,
    load_wide_deep,
    mostpop_counts,
    organic_pairs,
    reference_test_rows,
)

from hybrid_recsys.hashing import sha256_file
from hybrid_recsys.statistics.bootstrap import holm_adjust
from hybrid_recsys.training.inputs import build_test_protocol

METHODS = (
    "MostPop",
    "ItemKNN",
    "ItemKNN H1",
    "ItemKNN H2",
    "BPR-MF",
    "LightGCN",
    "Rule-only",
    "Deep-only",
    "W&D",
    "Hybrid",
)
COMPARATORS = ("ItemKNN", "W&D", "Deep-only", "Rule-only", "ItemKNN H1", "ItemKNN H2")
PRIMARY = "ItemKNN|NDCG@10"


def score_all(config, inputs, snapshot, protocol, freeze):
    """Per-user metrics of every method (and seed) on ``protocol``."""
    device = common.device(config)
    evaluator = FastEvaluator(protocol)
    users, num_items = evaluator.user_ids, len(protocol.candidate_item_ids)
    results = {}

    def keep(name, rows):
        results[name] = common.per_user(evaluator.evaluate(rows)[0])

    counts = mostpop_counts(snapshot, inputs.item_id_map, num_items)
    keep("MostPop", ((p, counts) for p in range(len(users))))
    knn = ItemKnn(snapshot, inputs.item_id_map, num_items, users, config.itemknn_k)
    keep("ItemKNN", knn.rows(organic_pairs(snapshot, inputs.item_id_map, ("train",))))
    if "test" in snapshot.events_by_split:
        keep("ItemKNN H1", knn.rows(knn.full_history()))
        keep("ItemKNN H2", knn.rows(organic_pairs(snapshot, inputs.item_id_map, ("train", "val"))))
    rules = RuleScores(config, evaluator, tuple(protocol.candidate_item_ids))
    keep("Rule-only", enumerate(rules.raw))
    lambda_value, lr_wide = freeze["selected"]["lambda"], freeze["selected"]["wd_lr_wide"]
    for seed in config.seeds:
        model = load_deep(config, inputs, seed, device)
        scores = {p: s.copy() for p, s in batched_scores(model, users, evaluator.histories)}
        keep(f"Deep-only s{seed}", scores.items())
        keep(
            f"Hybrid s{seed}",
            (
                (p, common.zscore(s, rules.masks[p]) + lambda_value * rules.z[p])
                for p, s in scores.items()
            ),
        )
        del model, scores
        wide = load_wide_deep(config, inputs, seed, lr_wide, device)
        keep(
            f"W&D s{seed}",
            ((p, wide.score_user(users[p], evaluator.histories[p])) for p in range(len(users))),
        )
        del wide
        keep(f"BPR-MF s{seed}", reference_test_rows(config, "BPR", seed, inputs, users, num_items))
        keep(
            f"LightGCN s{seed}",
            reference_test_rows(config, "LightGCN", seed, inputs, users, num_items),
        )
    return evaluator, results


def seed_matrix(results, name, metric, seeds):
    if f"{name} s{seeds[0]}" in results:
        return np.stack([results[f"{name} s{s}"][metric] for s in seeds])
    return np.stack([results[name][metric]] * len(seeds))


def bootstrap(config, candidate, comparator):
    """Crossed paired bootstrap over users and seeds, one schedule shared by every contrast."""
    delta = candidate - comparator
    seeds, users = delta.shape
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(list(config.bootstrap_seed))))
    effects = np.empty(config.bootstrap_replicates)
    for index in range(config.bootstrap_replicates):
        effects[index] = delta[
            np.ix_(rng.integers(0, seeds, size=seeds), rng.integers(0, users, size=users))
        ].mean()
    observed = float(delta.mean())
    extreme = int(np.count_nonzero(np.abs(effects - observed) >= abs(observed)))
    low, high = np.quantile(effects, [0.025, 0.975])
    return {
        "difference": observed,
        "ci95": [float(low), float(high)],
        "raw_p": min(1.0, (1 + extreme) / (config.bootstrap_replicates + 1)),
    }


def analyze(config, results, protocol, evaluator):
    seeds = config.seeds
    report = {"methods": {}, "contrasts": {}, "users": len(evaluator.user_ids)}
    for name in METHODS:
        report["methods"][name] = {
            m: {
                "mean": float(seed_matrix(results, name, m, seeds).mean()),
                "seed_means": seed_matrix(results, name, m, seeds).mean(axis=1).tolist(),
            }
            for m in common.METRICS
        }
    for versus in COMPARATORS:
        for metric in common.METRICS:
            report["contrasts"][f"{versus}|{metric}"] = bootstrap(
                config,
                seed_matrix(results, "Hybrid", metric, seeds),
                seed_matrix(results, versus, metric, seeds),
            )
    family = {
        k: r["raw_p"]
        for k, r in report["contrasts"].items()
        if k != PRIMARY and not k.startswith("ItemKNN H")
    }
    for key, value in holm_adjust(family).items():
        report["contrasts"][key]["holm_p"] = value
    positives = [protocol.case_for(user).positive_item_ids for user in evaluator.user_ids]
    report["cohort"] = {
        "eligible_users": len(positives),
        "novel_positive_events": sum(map(len, positives)),
        "distinct_target_items": len(set().union(*positives)),
    }
    return report


def main() -> None:
    parser = common.parser(__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--open", action="store_true")
    args = parser.parse_args()
    config = common.load_config(args.config)
    freeze = json.loads(config.freeze_file.read_text(encoding="utf-8"))
    inputs = common.inputs(config)
    if not args.open:
        evaluator, results = score_all(
            config, inputs, inputs.snapshot, inputs.validation_protocol, freeze
        )
        finite = all(np.isfinite(rows["NDCG@10"]).all() for rows in results.values())
        print(
            f"dry run ok: {len(results)} score sets, {len(evaluator.user_ids)} users, finite {finite}"
        )
        return
    if not config.open_authorization.exists():
        raise SystemExit(f"TEST is sealed: {config.open_authorization} is missing")
    receipt = json.loads((config.custody_root / "custody_receipt.json").read_text(encoding="utf-8"))
    if sha256_file(config.sealed_test) != receipt["test_source_sha256"]:
        raise SystemExit("sealed TEST hash differs from the custody receipt")
    if config.test_root.exists():
        raise SystemExit("TEST was already opened; it opens only once")
    config.test_root.mkdir(parents=True)
    snapshot = common.snapshot_with_test(config)
    protocol = build_test_protocol(snapshot, inputs.validation_protocol, inputs.item_id_map)
    evaluator, results = score_all(config, inputs, snapshot, protocol, freeze)
    report = analyze(config, results, protocol, evaluator)
    np.savez_compressed(
        config.test_root / "per_user_metrics.npz",
        user_ids=np.asarray(evaluator.user_ids),
        **{
            f"{name}|{metric}": values
            for name, rows in results.items()
            for metric, values in rows.items()
        },
    )
    (config.test_root / "test_results.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8"
    )
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
