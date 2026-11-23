"""Stage 7: descriptive analyses of the opened TEST. Selects nothing.

1. Rebuilds the TEST cohort and the MostPop baseline from the raw split files, with code independent
   of stage 6, and prints both next to the stored values.
2. Splits the stored per-user metrics into user groups: users whose generator persona was assigned a
   co-purchase transition versus the rest, and users whose TEST positives are reachable by a rule
   versus the rest.

Writes ``test/results_groups.json``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import common
import numpy as np

from hybrid_recsys.data.io import load_canonical_snapshot
from hybrid_recsys.data.pair_rules import load_pair_rule_table
from hybrid_recsys.hashing import sha256_file

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


def jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def raw_rebuild(config, snapshot):
    users = {int(raw): index for index, raw in enumerate(snapshot.raw_user_ids)}
    items = {int(raw): index for index, raw in enumerate(snapshot.raw_item_ids)}
    train = list(jsonl(config.snapshot_root / "train.jsonl"))
    catalog = {e["item_id"] for e in train}
    history = defaultdict(set)
    for e in train + list(jsonl(config.snapshot_root / "val.jsonl")):
        if e["item_id"] in catalog:
            history[e["user_id"]].add(e["item_id"])
    targets = defaultdict(set)
    for e in jsonl(config.sealed_test):
        item = items[e["raw_item_id"]]
        if e["event_type"] == "purchase" and e["event_origin"] == "organic" and item in catalog:
            targets[users[e["raw_user_id"]]].add(item)
    cases = {u: t - history[u] for u, t in targets.items() if t - history[u]}
    counts = Counter(
        e["item_id"]
        for e in train
        if e["event_type"] == "purchase" and e["event_origin"] == "organic"
    )
    order = sorted(catalog, key=lambda i: (-counts[i], i))
    ndcg = hr = 0.0
    for user, positives in cases.items():
        ranked = [i for i in order if i not in history[user]][:10]
        hits = [1 if i in positives else 0 for i in ranked]
        dcg = sum(h / math.log2(rank + 2) for rank, h in enumerate(hits))
        ideal = sum(1 / math.log2(rank + 2) for rank in range(min(10, len(positives))))
        ndcg += dcg / ideal
        hr += 1 if any(hits) else 0
    summary = {
        "eligible_users": len(cases),
        "novel_positive_events": sum(map(len, cases.values())),
        "distinct_target_items": len(set().union(*cases.values())),
        "MostPop NDCG@10": ndcg / len(cases),
        "MostPop HR@10": hr / len(cases),
    }
    return summary, cases, history


def transition_users(raw_users, seed: int, count: int) -> set[int]:
    """Users the data generator assigns a co-purchase transition: the first ``count`` by hash order."""
    key = lambda u: (int.from_bytes(hashlib.sha256(f"{seed}:{u}".encode()).digest()[:4], "big"), u)
    return set(sorted(raw_users, key=key)[:count])


def main() -> None:
    parser = common.parser(__doc__.splitlines()[0])
    parser.add_argument("--transition-seed", type=int, default=42)
    parser.add_argument("--transition-users", type=int, default=2500)
    args = parser.parse_args()
    config = common.load_config(args.config)
    report = json.loads((config.test_root / "test_results.json").read_text(encoding="utf-8"))
    inputs = common.inputs(config)
    snapshot = load_canonical_snapshot(config.snapshot_root, required_splits=("train", "val"))
    rebuilt, cases, history = raw_rebuild(config, snapshot)
    print("raw rebuild", rebuilt)
    print(
        "stored     ",
        report["cohort"],
        {m: report["methods"]["MostPop"][m]["mean"] for m in ("NDCG@10", "HR@10")},
    )

    stored = np.load(config.test_root / "per_user_metrics.npz")
    users = [int(u) for u in stored["user_ids"]]
    if set(users) != set(cases):
        raise SystemExit("stored users differ from the raw rebuild")
    assigned = transition_users(
        [int(raw) for raw in snapshot.raw_user_ids], args.transition_seed, args.transition_users
    )
    transition = np.array([int(snapshot.raw_user_ids[u]) in assigned for u in users])

    table = load_pair_rule_table(
        config.rules_root, expected_manifest_sha256=sha256_file(config.rules_root / "manifest.json")
    )
    candidates = tuple(inputs.validation_protocol.candidate_item_ids)
    item_map = inputs.item_id_map
    covered = np.zeros(len(users), dtype=bool)
    for position, user in enumerate(users):
        values = np.asarray(table.score(frozenset(item_map[i] for i in history[user]), candidates))
        scored = {candidates[index] for index in np.flatnonzero(values > 0)}
        covered[position] = bool(scored & {item_map[i] for i in cases[user]})
    table.close()

    def group_means(mask):
        result = {}
        for method in METHODS:
            names = (
                [f"{method} s{s}" for s in config.seeds]
                if f"{method} s{config.seeds[0]}|NDCG@10" in stored
                else [method]
            )
            result[method] = {
                m: float(np.mean([stored[f"{n}|{m}"][mask].mean() for n in names]))
                for m in common.METRICS
            }
        return result

    groups = {
        "transition_assigned": transition,
        "non_assigned": ~transition,
        "rule_covered": covered,
        "not_rule_covered": ~covered,
        "all": np.ones(len(users), dtype=bool),
    }
    output = {
        "stage": "descriptive split of the opened TEST",
        "raw_rebuild": rebuilt,
        "sizes": {name: int(mask.sum()) for name, mask in groups.items()},
        "means": {name: group_means(mask) for name, mask in groups.items()},
    }
    (config.test_root / "results_groups.json").write_text(
        json.dumps(output, indent=1), encoding="utf-8"
    )
    print(output["sizes"])
    for name in groups:
        print(name)
        for method in (
            "ItemKNN",
            "ItemKNN H1",
            "ItemKNN H2",
            "Rule-only",
            "Deep-only",
            "W&D",
            "Hybrid",
        ):
            row = output["means"][name][method]
            print(f"  {method:12s} {row['NDCG@10']:.4f} {row['HR@10']:.4f} {row['GAUC']:.4f}")


if __name__ == "__main__":
    main()
