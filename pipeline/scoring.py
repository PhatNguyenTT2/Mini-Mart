"""Scorers shared by validation and TEST scoring: ItemKNN, RecBole baselines and rule tables."""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
import scipy.sparse as sp
from common import PipelineConfig, zscore

from hybrid_recsys.data.pair_rules import load_pair_rule_table
from hybrid_recsys.hashing import sha256_file

RECBOLE_DATASET = "pipeline"


def organic_pairs(snapshot: Any, item_id_map: Any, splits: Iterable[str]) -> set[tuple[int, int]]:
    """Unique (user, item) organic purchases in ``splits``, mapped to the candidate catalog."""
    return {
        (int(e.user_id), int(item_id_map[e.item_id]))
        for split in splits
        for e in snapshot.events_by_split[split]
        if e.event_type == "purchase" and e.event_origin == "organic" and e.item_id in item_id_map
    }


def mostpop_counts(snapshot: Any, item_id_map: Any, num_items: int) -> Any:
    counts = np.zeros(num_items, dtype=np.float32)
    for event in snapshot.events_by_split["train"]:
        if event.event_type == "purchase" and event.event_origin == "organic":
            if event.item_id in item_id_map:
                counts[item_id_map[event.item_id]] += 1
    return counts


class ItemKnn:
    """TRAIN-fitted item-item cosine similarity (RecBole implementation), scored from any history."""

    def __init__(self, snapshot: Any, item_id_map: Any, num_items: int, user_ids: Any, k: int):
        from recbole.model.general_recommender.itemknn import ComputeSimilarity  # type: ignore

        self.snapshot, self.map, self.user_ids = snapshot, item_id_map, np.asarray(user_ids)
        self.num_users, self.num_items = snapshot.manifest.num_users, num_items
        pairs = sorted(organic_pairs(snapshot, item_id_map, ("train",)))
        order = list(dict.fromkeys(item for _, item in pairs))
        known = set(order)
        order += [item for item in range(num_items) if item not in known]
        self.to_native = np.empty(num_items, dtype=np.int64)
        self.to_native[np.asarray(order)] = np.arange(1, num_items + 1)
        _, similarity = ComputeSimilarity(
            self.native(pairs), topk=k, shrink=0.0, method="item"
        ).compute_similarity()
        self.similarity = similarity.tocsr().astype(np.float32)

    def native(self, pairs: Iterable[tuple[int, int]]) -> Any:
        ordered = sorted(pairs)
        rows = np.asarray([u for u, _ in ordered])
        columns = self.to_native[np.asarray([i for _, i in ordered])]
        return sp.csr_matrix(
            (np.ones(len(ordered), dtype=np.float32), (rows, columns)),
            shape=(self.num_users, self.num_items + 1),
            dtype=np.float32,
        )

    def full_history(self) -> set[tuple[int, int]]:
        """Every TRAIN+VAL interaction, the same history the Hybrid model sees at TEST time."""
        return {
            (int(e.user_id), int(self.map[e.item_id]))
            for split in ("train", "val")
            for e in self.snapshot.events_by_split[split]
            if e.item_id in self.map
        }

    def rows(self, pairs: Iterable[tuple[int, int]]) -> Iterator[tuple[int, Any]]:
        matrix = self.native(pairs)
        for start in range(0, len(self.user_ids), 512):
            part = np.asarray(
                matrix[self.user_ids[start : start + 512]].dot(self.similarity).todense(),
                dtype=np.float32,
            )
            for offset, values in enumerate(part[:, self.to_native]):
                yield start + offset, values


class RuleScores:
    """Raw rule scores, z-scored rule scores and seen-item masks for every evaluated user."""

    def __init__(self, config: PipelineConfig, evaluator: Any, candidates: tuple[int, ...]):
        table = load_pair_rule_table(
            config.rules_root,
            expected_manifest_sha256=sha256_file(config.rules_root / "manifest.json"),
        )
        num_items = len(candidates)
        self.masks, self.z, self.raw = [], [], []
        self.users_with_antecedent = 0
        try:
            for position, history in enumerate(evaluator.histories):
                mask = np.ones(num_items, dtype=bool)
                mask[evaluator.seen[position]] = False
                values = np.asarray(table.score(frozenset(history), candidates), dtype=np.float32)
                self.masks.append(mask)
                self.raw.append(values)
                self.z.append(zscore(values, mask))
                self.users_with_antecedent += int(table.has_antecedent(frozenset(history)))
        finally:
            table.close()


def recbole_config(
    config: PipelineConfig,
    method: str,
    seed: int,
    train_pairs: list[tuple[int, int]],
    num_users: int,
    num_items: int,
    checkpoint_dir: Path,
) -> Any:
    """Write the RecBole atomic files once and build a TRAIN-only RecBole config."""
    from recbole.config import Config  # type: ignore
    from recbole.model.general_recommender.bpr import BPR  # type: ignore
    from recbole.model.general_recommender.lightgcn import LightGCN  # type: ignore

    folder = config.work_root / "recbole" / RECBOLE_DATASET
    if not (folder / f"{RECBOLE_DATASET}.inter").exists():
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / f"{RECBOLE_DATASET}.inter").open(
            "w", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write("user_id:token\titem_id:token\n")
            stream.writelines(f"{u}\t{i}\n" for u, i in train_pairs)
        (folder / f"{RECBOLE_DATASET}.user").write_text(
            "user_id:token\n" + "".join(f"{u}\n" for u in range(num_users)), encoding="utf-8"
        )
        (folder / f"{RECBOLE_DATASET}.item").write_text(
            "item_id:token\n" + "".join(f"{i}\n" for i in range(num_items)), encoding="utf-8"
        )
    parameters = config.bpr if method == "BPR" else config.lightgcn
    native: dict[str, Any] = {
        "dataset": RECBOLE_DATASET,
        "data_path": str(folder.parent.resolve()),
        "field_separator": "\t",
        "USER_ID_FIELD": "user_id",
        "ITEM_ID_FIELD": "item_id",
        "load_col": {"inter": ["user_id", "item_id"], "user": ["user_id"], "item": ["item_id"]},
        "seed": seed,
        "reproducibility": True,
        "show_progress": False,
        "save_dataset": False,
        "save_dataloaders": False,
        "log_wandb": False,
        "epochs": config.reference_max_epochs,
        "stopping_step": config.reference_patience,
        "eval_step": 1,
        "learning_rate": parameters["learning_rate"],
        "valid_metric": "NDCG@10",
        "valid_metric_bigger": True,
        "topk": [10],
        "train_neg_sample_args": {
            "distribution": "uniform",
            "sample_num": 1,
            "alpha": 1.0,
            "dynamic": False,
            "candidate_num": 0,
        },
        "embedding_size": parameters["embedding_size"],
        "checkpoint_dir": str(checkpoint_dir.resolve()),
        "eval_args": {
            "split": {"RS": [1.0, 0.0, 0.0]},
            "order": "RO",
            "group_by": "user",
            "mode": "full",
        },
        "shuffle": True,
    }
    if method == "BPR":
        native["weight_decay"] = 0.00001
        model_class = BPR
    else:
        native["n_layers"] = parameters["n_layers"]
        native["reg_weight"] = 0.00001
        model_class = LightGCN
    argv, sys.argv = sys.argv, [sys.argv[0]]
    try:
        return Config(model=model_class, dataset=RECBOLE_DATASET, config_dict=native), model_class
    finally:
        sys.argv = argv


def recbole_rows(model: Any, method: str, dataset: Any, user_ids: Any, num_items: int, device: Any):
    """Full-catalog scores from a RecBole model, in the pipeline's user and item order."""
    import torch

    known_users = dataset.field2token_id["user_id"]
    known_items = dataset.field2token_id["item_id"]
    native_users = torch.as_tensor([int(known_users[str(u)]) for u in user_ids], device=device)
    native_items = torch.as_tensor(
        [int(known_items[str(i)]) for i in range(num_items)], device=device
    )
    model.eval()
    with torch.no_grad():
        if method == "BPR":
            users, items = model.user_embedding.weight, model.item_embedding.weight
        else:
            users, items = model.forward()
        chosen = items[native_items]
        for start in range(0, len(native_users), 1024):
            values = (users[native_users[start : start + 1024]] @ chosen.T).cpu().numpy()
            for offset, row in enumerate(values.astype(np.float32)):
                yield start + offset, row


def load_deep(config: PipelineConfig, inputs: Any, seed: int, device: Any) -> Any:
    """The validation-selected Deep checkpoint for ``seed``, promoted to the batched scorer."""
    import torch
    from fast_paths import promote_to_fast

    from hybrid_recsys.models.confirmatory import (
        ConfirmatoryTwoTowerConfig,
        build_confirmatory_two_tower,
    )
    from hybrid_recsys.training.runtime import deterministic

    deterministic(seed)
    model = build_confirmatory_two_tower(
        num_users=inputs.snapshot.manifest.num_users,
        features=inputs.features,
        config=ConfirmatoryTwoTowerConfig(128, 256, 4),
        seed=seed,
    ).to(device)
    model.load_state_dict(
        torch.load(config.validation_root / f"deep-s{seed}/best.pt", map_location=device)
    )
    return promote_to_fast(model)


def load_wide_deep(
    config: PipelineConfig, inputs: Any, seed: int, lr_wide: float, device: Any
) -> Any:
    import torch

    from hybrid_recsys.models.wd_original import WideDeepOriginal

    features = inputs.features
    model = WideDeepOriginal(
        inputs.snapshot.manifest.num_users, features.text_embeddings, features.category_ids
    ).to(device)
    model.load_state_dict(
        torch.load(config.validation_root / f"wd-lr{lr_wide}-s{seed}/best.pt", map_location=device)
    )
    return model


def reference_test_rows(
    config: PipelineConfig, method: str, seed: int, inputs: Any, user_ids: Any, num_items: int
) -> Iterator[tuple[int, Any]]:
    """Rebuild a trained RecBole model from its validation checkpoint and score ``user_ids``."""
    import torch
    from recbole.data import create_dataset, data_preparation  # type: ignore
    from recbole.utils import init_seed  # type: ignore

    folder = config.validation_root / f"{method.lower()}-s{seed}"
    pairs = sorted(organic_pairs(inputs.snapshot, inputs.item_id_map, ("train",)))
    torch.use_deterministic_algorithms(False)
    recbole, model_class = recbole_config(
        config,
        method,
        seed,
        pairs,
        inputs.snapshot.manifest.num_users,
        num_items,
        folder / "native",
    )
    init_seed(seed, True)
    dataset = create_dataset(recbole)
    train_data, _, _ = data_preparation(recbole, dataset)
    model = model_class(recbole, train_data.dataset).to(recbole["device"])
    model.load_state_dict(torch.load(folder / "best.pt", map_location=recbole["device"]))
    yield from recbole_rows(model, method, dataset, user_ids, num_items, recbole["device"])
