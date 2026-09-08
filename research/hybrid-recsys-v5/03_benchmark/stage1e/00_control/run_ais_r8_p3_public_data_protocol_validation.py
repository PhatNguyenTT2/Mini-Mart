from __future__ import annotations

import gc
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import pathlib
import platform
import statistics
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


EXPECTED_RUNS = (
    ("recbole-pop-seed-42", "Pop", 42),
    ("recbole-bpr-seed-42", "BPR", 42),
    ("recbole-bpr-seed-2027", "BPR", 2027),
    ("recbole-bpr-seed-31415", "BPR", 31415),
)
METRICS = ("ndcg@10", "recall@10", "mrr@10", "hit@10", "precision@10")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: set[str] = set()
    for key, value in pairs:
        if key in result or key.casefold() in folded:
            raise ValueError(f"duplicate or case-colliding JSON key: {key}")
        result[key] = value
        folded.add(key.casefold())
    return result


def read_json(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM prohibited: {path}")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON object required")
    return value


def serial(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): serial(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".partial")
    encoded = (json.dumps(serial(payload), indent=2, sort_keys=True) + "\n").encode()
    with temporary.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def canonical_hash(value: Any) -> str:
    raw = json.dumps(serial(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema_version") != "ais-r8-p3-public-data-protocol-validation-spec/1.0":
        raise ValueError("spec schema drift")
    observed = tuple((row["run_id"], row["model"], row["seed"]) for row in spec["runs"])
    if observed != EXPECTED_RUNS:
        raise ValueError("model or seed registry drift")
    if spec["dataset"]["feedback_filter"]["interval"] != "[4,inf)":
        raise ValueError("rating-filter drift")
    if spec["protocol"]["order"] != "TO" or spec["protocol"]["split"] != {"RS": [0.8, 0.1, 0.1]}:
        raise ValueError("split drift")
    if spec["protocol"]["primary_metric"] != "NDCG@10":
        raise ValueError("metric drift")
    if spec["execution"]["automatic_retry"] or spec["execution"]["project_v5_test_access"]:
        raise ValueError("prohibited execution policy")


def interaction_hash(dataset: Any) -> str:
    digest = hashlib.sha256()
    for field in (dataset.uid_field, dataset.iid_field, "rating", "timestamp"):
        tensor = dataset.inter_feat[field].detach().cpu().numpy()
        digest.update(field.encode())
        digest.update(str(tensor.dtype).encode())
        digest.update(str(tuple(tensor.shape)).encode())
        digest.update(tensor.tobytes())
    return digest.hexdigest()


def split_binding(dataset: Any, train: Any, valid: Any, test: Any) -> dict[str, Any]:
    def one(loader: Any) -> dict[str, Any]:
        item = {
            "interactions": len(loader._dataset.inter_feat),
            "sha256": interaction_hash(loader._dataset),
        }
        if hasattr(loader, "uid_list"):
            item["evaluated_users"] = len(loader.uid_list)
        return item

    result = {
        "schema_version": "ais-r8-p3-dataset-binding/1.0",
        "filtered_interactions": len(dataset.inter_feat),
        "users_excluding_padding": int(dataset.user_num) - 1,
        "items_excluding_padding": int(dataset.item_num) - 1,
        "filtered_interactions_sha256": interaction_hash(dataset),
        "splits": {"train": one(train), "validation": one(valid), "test": one(test)},
        "rating_filter": "[4,inf)",
        "order": "TO",
        "ratio": [0.8, 0.1, 0.1],
    }
    result["binding_hash"] = canonical_hash(result)
    return result


def normalized_metrics(values: dict[str, Any]) -> dict[str, float]:
    lowered = {str(key).lower(): float(serial(value)) for key, value in values.items()}
    if any(metric not in lowered for metric in METRICS):
        raise ValueError("required metric missing")
    result = {metric: lowered[metric] for metric in METRICS}
    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError("non-finite metric")
    return result


def run_one(spec: dict[str, Any], row: dict[str, Any], root: pathlib.Path) -> dict[str, Any]:
    import torch
    from recbole.config import Config
    from recbole.data import create_dataset, data_preparation
    from recbole.utils import get_model, get_trainer, init_logger, init_seed

    run_root = root / "runs" / row["run_id"]
    run_root.mkdir(parents=True, exist_ok=False)
    started = now()
    write_json(run_root / "state.json", {"status": "PREPARING", "test_opened": False})
    requested = dict(spec["common_config"])
    requested.update(row["model_config"])
    requested["seed"] = row["seed"]
    requested["checkpoint_dir"] = str(run_root / "saved")
    write_json(run_root / "requested_config.json", requested)

    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)
    config = Config(model=row["model"], dataset=spec["dataset"]["name"], config_dict=requested)
    init_seed(config["seed"], config["reproducibility"])
    init_logger(config)
    dataset = create_dataset(config)
    train, valid, test = data_preparation(config, dataset)
    binding = split_binding(dataset, train, valid, test)
    write_json(run_root / "dataset_binding.json", binding)

    init_seed(config["seed"], config["reproducibility"])
    model = get_model(config["model"])(config, train._dataset).to(config["device"])
    trainer = get_trainer(config["MODEL_TYPE"], config["model"])(config, model)
    write_json(run_root / "state.json", {"status": "TRAINING_VALIDATION", "test_opened": False})
    best_score, valid_result = trainer.fit(train, valid, saved=True, show_progress=False)
    write_json(run_root / "state.json", {"status": "EVALUATING_PUBLIC_TEST", "test_opened": True})
    test_result = trainer.evaluate(test, load_best_model=True, show_progress=False)

    checkpoint = pathlib.Path(trainer.saved_model_file)
    if not checkpoint.is_file():
        raise ValueError("checkpoint missing")
    result = {
        "schema_version": "ais-r8-p3-model-result/1.0",
        "status": "COMPLETED_UNAUDITED",
        "run_id": row["run_id"],
        "model": row["model"],
        "seed": row["seed"],
        "started_at": started,
        "finished_at": now(),
        "best_valid_score": float(serial(best_score)),
        "validation_metrics": normalized_metrics(valid_result),
        "test_metrics": normalized_metrics(test_result),
        "dataset_binding_hash": binding["binding_hash"],
        "checkpoint": {
            "path": checkpoint.relative_to(root).as_posix(),
            "bytes": checkpoint.stat().st_size,
            "sha256": sha256(checkpoint),
            "selection_rule": "maximum validation NDCG@10"
        },
        "public_test_opened": True,
        "project_v5_test_opened": False,
        "accepted_for_paper": False,
    }
    write_json(run_root / "result.json", result)
    write_json(run_root / "state.json", {"status": "COMPLETED_UNAUDITED", "test_opened": True})
    del trainer, model, train, valid, test, dataset
    gc.collect()
    return result


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {row["run_id"]: row for row in results}
    pop = lookup["recbole-pop-seed-42"]["test_metrics"]
    bpr = [lookup[f"recbole-bpr-seed-{seed}"] for seed in (42, 2027, 31415)]
    summary: dict[str, Any] = {}
    for metric in METRICS:
        values = [row["test_metrics"][metric] for row in bpr]
        deltas = [value - pop[metric] for value in values]
        summary[metric] = {
            "pop": pop[metric],
            "bpr_values": values,
            "bpr_mean": statistics.mean(values),
            "bpr_sample_sd": statistics.stdev(values),
            "bpr_min": min(values),
            "bpr_max": max(values),
            "bpr_minus_pop_deltas": deltas,
            "bpr_minus_pop_mean": statistics.mean(deltas),
        }
    return {
        "schema_version": "ais-r8-p3-aggregate-metrics/1.0",
        "status": "COMPLETED_UNAUDITED",
        "primary_metric": "ndcg@10",
        "seed_order": [42, 2027, 31415],
        "standard_deviation": "sample_n_minus_1",
        "inferential_test": None,
        "numeric_outcome_is_not_a_pass_gate": True,
        "metrics": summary,
        "accepted_for_paper": False,
    }


def main() -> int:
    spec_path = pathlib.Path(os.environ["AIS_R8_SPEC_PATH"])
    root = pathlib.Path(os.environ["AIS_R8_OUTPUT_ROOT"])
    runner_path = pathlib.Path(__file__).resolve()
    if sha256(spec_path) != os.environ["AIS_R8_EXPECTED_SPEC_SHA256"]:
        raise ValueError("spec hash mismatch")
    if sha256(runner_path) != os.environ["AIS_R8_EXPECTED_RUNNER_SHA256"]:
        raise ValueError("runner hash mismatch")
    if sorted(path.name for path in root.iterdir()) != ["host_preflight.json"]:
        raise ValueError("attempt root is not fresh")
    spec = read_json(spec_path)
    validate_spec(spec)
    atomic = pathlib.Path(spec["dataset"]["atomic_container_path"])
    if sha256(atomic) != spec["dataset"]["atomic_sha256"]:
        raise ValueError("dataset hash mismatch")

    import torch
    torch.set_num_threads(spec["execution"]["torch_threads"])
    torch.use_deterministic_algorithms(True)
    write_json(root / "state.json", {"status": "RUNNING", "completed": [], "test_opened": False})
    write_json(root / "environment.json", {
        "python": platform.python_version(),
        "executable": sys.executable,
        "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) for name in ("recbole", "torch", "numpy", "scipy", "pandas", "scikit-learn")},
        "cuda_available": torch.cuda.is_available(),
        "image": os.environ["AIS_R8_IMAGE_REFERENCE"],
        "network": "none",
    })

    results = []
    for row in spec["runs"]:
        print(f"AIS_R8_RUN_START {row['run_id']}", flush=True)
        results.append(run_one(spec, row, root))
        print(f"AIS_R8_RUN_COMPLETE {row['run_id']}", flush=True)
        write_json(root / "state.json", {"status": "RUNNING", "completed": [item["run_id"] for item in results], "test_opened": True})
    if len({item["dataset_binding_hash"] for item in results}) != 1:
        raise ValueError("split differs across runs")
    write_json(root / "aggregate_metrics.json", aggregate(results))
    write_json(root / "state.json", {"status": "COMPLETED_UNAUDITED", "completed": [item["run_id"] for item in results], "test_opened": True})
    key_files = [root / "host_preflight.json", root / "environment.json", root / "aggregate_metrics.json"]
    key_files.extend(root / "runs" / row["run_id"] / "result.json" for row in spec["runs"])
    write_json(root / "run_manifest.json", {
        "schema_version": "ais-r8-p3-run-manifest/1.0",
        "status": "COMPLETED_UNAUDITED",
        "namespace": "PUBLIC_DATA_PROTOCOL_VALIDATION",
        "attempt_id": spec["attempt_id"],
        "spec_sha256": sha256(spec_path),
        "runner_sha256": sha256(runner_path),
        "run_ids": [item["run_id"] for item in results],
        "key_artifacts": [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in key_files],
        "public_test_opened": True,
        "project_v5_test_opened": False,
        "accepted_result_rows": 0,
        "paper_use": "BLOCKED_PENDING_AIS_R8_P4_AND_P5",
    })
    print("AIS_R8_ALL_RUNS_COMPLETED_UNAUDITED", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        output = os.environ.get("AIS_R8_OUTPUT_ROOT")
        if output and pathlib.Path(output).is_dir():
            target = pathlib.Path(output) / "failure_receipt.json"
            if not target.exists():
                try:
                    write_json(target, {
                        "schema_version": "ais-r8-p3-failure/1.0",
                        "status": "FAILED_NO_RETRY",
                        "created_at": now(),
                        "error_type": type(error).__name__,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                        "automatic_retry": False,
                        "project_v5_test_opened": False,
                    })
                except Exception:
                    pass
        traceback.print_exc()
        raise
