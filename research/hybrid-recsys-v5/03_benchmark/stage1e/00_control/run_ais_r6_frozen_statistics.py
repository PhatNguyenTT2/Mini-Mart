"""Run the frozen AIS-R6 paired bootstrap and multiplicity analysis once."""

# ruff: noqa: I001

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np


SCRIPT_PATH = Path(__file__).resolve()
for candidate_root in SCRIPT_PATH.parents:
    candidate_source = candidate_root / "ai-service-v2" / "src"
    if candidate_source.is_dir():
        sys.path.insert(0, str(candidate_source))
        break
else:  # pragma: no cover - fail closed on a malformed checkout
    raise RuntimeError("cannot locate the ai-service-v2 source tree")

from ai_service_v2.evaluation.evaluator import (  # type: ignore[import-untyped]
    per_user_metrics_sha256,
)
from ai_service_v2.hashing import (  # type: ignore[import-untyped]
    canonical_json_bytes,
    load_strict_json,
    sha256_file,
)
from ai_service_v2.statistics import (  # type: ignore[import-untyped]
    hierarchical_paired_bootstrap,
    holm_adjust,
)


METRICS = ("NDCG@10", "HR@10", "GAUC")
EXPECTED_PACKET_SCHEMA = "ais-r6-frozen-statistics-execution-packet/1.0"
EXPECTED_RUNTIME_SCHEMA = "ais-r6-test-application-runtime-receipt/1.0"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _raw_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _inventory(root: Path) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    total_bytes = 0
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        raw_hash = sha256_file(path)
        total_bytes += size
        digest.update(f"{relative}\t{size}\t{raw_hash}\n".encode())
    return len(files), total_bytes, digest.hexdigest()


def _find_runtime_row(runtime: Mapping[str, Any], run_id: str) -> Mapping[str, Any]:
    matches = [row for row in runtime["run_results"] if row["run_id"] == run_id]
    _require(len(matches) == 1, f"runtime row cardinality mismatch: {run_id}")
    return cast(Mapping[str, Any], matches[0])


def _load_metric_vectors(
    test_root: Path,
    runtime: Mapping[str, Any],
    input_row: Mapping[str, Any],
) -> tuple[tuple[int, ...], dict[str, np.ndarray]]:
    run_id = str(input_row["run_id"])
    runtime_row = _find_runtime_row(runtime, run_id)
    _require(runtime_row["model_id"] == input_row["model_id"], f"model mismatch: {run_id}")
    _require(runtime_row["seed"] == input_row["seed"], f"seed mismatch: {run_id}")
    _require(
        runtime_row["per_user_metrics_sha256"] == input_row["per_user_metrics_sha256"],
        f"packet/runtime per-user hash mismatch: {run_id}",
    )
    relative_path = Path(str(input_row["relative_path"]))
    _require(not relative_path.is_absolute(), f"absolute metric path forbidden: {run_id}")
    path = test_root / relative_path
    payload = load_strict_json(path)
    _require(payload["schema_version"] == "per-user-metrics/1.0", f"schema mismatch: {run_id}")
    rows = payload["metrics"]
    _require(len(rows) == 4_970, f"eligible-user count mismatch: {run_id}")
    user_ids = tuple(int(row["user_id"]) for row in rows)
    _require(len(set(user_ids)) == len(user_ids), f"duplicate user ID: {run_id}")
    vectors = {
        metric: np.asarray([row[metric] for row in rows], dtype=np.float64)
        for metric in METRICS
    }
    _require(all(np.isfinite(vector).all() for vector in vectors.values()), f"nonfinite: {run_id}")
    canonical_vectors = {metric: tuple(vector.tolist()) for metric, vector in vectors.items()}
    observed_hash = per_user_metrics_sha256(user_ids, canonical_vectors, cutoff=10)
    _require(observed_hash == input_row["per_user_metrics_sha256"], f"hash mismatch: {run_id}")
    return user_ids, vectors


def _load_and_validate_inputs(
    packet_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[int, dict[str, np.ndarray]]]]:
    packet = load_strict_json(packet_path)
    _require(packet["schema_version"] == EXPECTED_PACKET_SCHEMA, "packet schema mismatch")
    _require(
        packet["verdict"] == "FROZEN_PENDING_EXACT_COMMAND_CONFIRMATION",
        "packet is not frozen",
    )
    identity = packet["runtime_identity"]
    _require(SCRIPT_PATH.as_posix() == identity["runner_path"], "runner path mismatch")
    _require(sha256_file(SCRIPT_PATH) == identity["runner_raw_sha256"], "runner hash mismatch")
    _require(Path(sys.executable).resolve() == Path(identity["python_executable"]).resolve(),
             "Python executable mismatch")
    _require(
        sha256_file(Path(sys.executable)) == identity["python_executable_sha256"],
        "Python executable hash mismatch",
    )
    for source in identity["implementation_sources"]:
        source_path = Path(source["path"])
        _require(sha256_file(source_path) == source["raw_sha256"],
                 f"implementation hash mismatch: {source_path}")

    test_root = Path(packet["input_binding"]["test_root"])
    output_root = Path(packet["output_contract"]["statistics_root"])
    _require(test_root.is_dir(), "TEST root is missing")
    _require(not output_root.exists(), "statistics root must be absent")
    _require(output_root.parent == test_root, "statistics root must be a direct TEST-root child")
    observed_inventory = _inventory(test_root)
    expected_inventory = (
        packet["input_binding"]["test_root_file_count"],
        packet["input_binding"]["test_root_total_bytes"],
        packet["input_binding"]["test_root_inventory_sha256"],
    )
    _require(observed_inventory == expected_inventory, "TEST-root inventory mismatch")

    runtime_path = Path(packet["input_binding"]["runtime_receipt_path"])
    _require(
        sha256_file(runtime_path) == packet["input_binding"]["runtime_receipt_raw_sha256"],
        "runtime receipt raw hash mismatch",
    )
    runtime = load_strict_json(runtime_path)
    _require(runtime["schema_version"] == EXPECTED_RUNTIME_SCHEMA, "runtime receipt schema mismatch")
    _require(
        runtime["runtime_verdict"]
        == "PASS_13_OF_13_TEST_APPLICATIONS_READY_FOR_FROZEN_STATISTICS_PACKET",
        "runtime verdict mismatch",
    )
    _require(
        runtime["artifact_replay"]["test_root_inventory_sha256"]
        == expected_inventory[2],
        "runtime inventory binding mismatch",
    )

    loaded: dict[str, dict[int, dict[str, np.ndarray]]] = {}
    common_user_ids: tuple[int, ...] | None = None
    for input_row in packet["input_binding"]["per_user_inputs"]:
        user_ids, vectors = _load_metric_vectors(test_root, runtime, input_row)
        if common_user_ids is None:
            common_user_ids = user_ids
        _require(user_ids == common_user_ids, f"user-order mismatch: {input_row['run_id']}")
        group = str(input_row["group"])
        seed = int(input_row["seed"])
        _require(seed not in loaded.setdefault(group, {}), f"duplicate group/seed: {group}/{seed}")
        loaded[group][seed] = vectors
    _require(common_user_ids is not None and len(common_user_ids) == 4_970, "empty inputs")
    return packet, runtime, loaded


def _matrix(
    loaded: Mapping[str, Mapping[int, Mapping[str, np.ndarray]]],
    group: str,
    metric: str,
    seeds: Sequence[int],
    policy: str,
) -> np.ndarray:
    rows = loaded[group]
    if policy == "MATCH_SEEDS":
        _require(set(rows) == set(seeds), f"seed set mismatch: {group}")
        return np.stack([rows[seed][metric] for seed in seeds])
    _require(policy == "BROADCAST_DETERMINISTIC", f"unknown seed policy: {policy}")
    _require(len(rows) == 1, f"deterministic comparator cardinality mismatch: {group}")
    vector = next(iter(rows.values()))[metric]
    return np.repeat(vector[np.newaxis, :], len(seeds), axis=0)


def _shared_hierarchical_samples(
    deltas: np.ndarray,
    *,
    samples: int,
    seed: int,
) -> np.ndarray:
    _require(deltas.ndim == 3, "delta bank must be [hypothesis, seed, user]")
    hypothesis_count, seed_count, user_count = deltas.shape
    rng = np.random.Generator(np.random.PCG64(seed))
    means = np.empty((hypothesis_count, samples), dtype=np.float64)
    denominator = float(seed_count * user_count)
    for sample_index in range(samples):
        selected_seeds = [int(rng.integers(0, seed_count)) for _ in range(seed_count)]
        totals = np.zeros(hypothesis_count, dtype=np.float64)
        for selected_seed in selected_seeds:
            selected_users = rng.integers(0, user_count, size=user_count)
            totals += deltas[:, selected_seed, selected_users].sum(axis=1, dtype=np.float64)
        means[:, sample_index] = totals / denominator
    return means


def _decision(lower: float, upper: float) -> str:
    if lower > 0.0:
        return "POSITIVE_INTERNAL_CONTROLLED_EFFECT"
    if upper < 0.0:
        return "NEGATIVE_INTERNAL_CONTROLLED_EFFECT"
    return "NULL_OR_INCONCLUSIVE"


def _execute(
    packet: Mapping[str, Any],
    loaded: Mapping[str, Mapping[int, Mapping[str, np.ndarray]]],
    packet_path: Path,
) -> dict[str, Any]:
    freeze = packet["statistics_freeze"]
    seeds = tuple(int(seed) for seed in freeze["candidate_seeds"])
    hypotheses: list[dict[str, Any]] = []
    delta_rows: list[np.ndarray] = []
    for comparison in freeze["comparisons"]:
        for metric in freeze["metrics"]:
            candidate = _matrix(
                loaded,
                comparison["candidate_group"],
                metric,
                seeds,
                "MATCH_SEEDS",
            )
            comparator = _matrix(
                loaded,
                comparison["comparator_group"],
                metric,
                seeds,
                comparison["comparator_seed_policy"],
            )
            hypotheses.append(
                {
                    "hypothesis_id": f"{comparison['comparison_id']}::{metric}",
                    "comparison_id": comparison["comparison_id"],
                    "role": comparison["role"],
                    "metric": metric,
                    "candidate_group": comparison["candidate_group"],
                    "comparator_group": comparison["comparator_group"],
                    "comparator_seed_policy": comparison["comparator_seed_policy"],
                }
            )
            delta_rows.append(candidate - comparator)
    delta_bank = np.stack(delta_rows)
    replicate_count = int(freeze["bootstrap"]["replicates"])
    bootstrap_seed = int(freeze["bootstrap"]["seed"])
    samples = _shared_hierarchical_samples(
        delta_bank,
        samples=replicate_count,
        seed=bootstrap_seed,
    )
    results: list[dict[str, Any]] = []
    for index, hypothesis in enumerate(hypotheses):
        observed = float(delta_bank[index].mean())
        lower, upper = np.quantile(samples[index], [0.025, 0.975], method="linear")
        centered = np.abs(samples[index] - observed)
        extreme = int(np.count_nonzero(centered >= abs(observed)))
        raw_p_value = float((extreme + 1) / (replicate_count + 1))
        results.append(
            {
                **hypothesis,
                "mean_delta": observed,
                "ci_lower": float(lower),
                "ci_upper": float(upper),
                "confidence_level": 0.95,
                "bootstrap_replicates": replicate_count,
                "bootstrap_seed": bootstrap_seed,
                "raw_two_sided_centered_bootstrap_p_value": raw_p_value,
                "interval_decision": _decision(float(lower), float(upper)),
            }
        )

    primary = next(
        result
        for result in results
        if result["comparison_id"] == freeze["primary_comparison_id"]
        and result["metric"] == freeze["primary_metric"]
    )
    exploratory = {
        result["hypothesis_id"]: result["raw_two_sided_centered_bootstrap_p_value"]
        for result in results
        if result["role"] == "EXPLORATORY"
    }
    _require(len(exploratory) == 12, "exploratory family must contain exactly 12 hypotheses")
    adjusted = holm_adjust(exploratory)
    alpha = float(freeze["multiplicity"]["alpha"])
    holm_rows = [
        {
            "hypothesis_id": name,
            "raw_p_value": exploratory[name],
            "holm_adjusted_p_value": adjusted[name],
            "reject_at_alpha_0_05": adjusted[name] <= alpha,
        }
        for name in exploratory
    ]
    bootstrap_report = {
        "schema_version": "ais-r6-bootstrap-report/1.0",
        "method": "hierarchical_paired_bootstrap",
        "seed_axis": list(seeds),
        "user_count": 4_970,
        "shared_resampling_schedule_across_hypotheses": True,
        "pre_average_seed_vectors": False,
        "results": results,
        "primary_result": primary,
        "construct_validity_scope": "INTERNAL_CONTROLLED_GENERATED_BEHAVIOR_ONLY",
    }
    holm_report = {
        "schema_version": "ais-r6-holm-report/1.0",
        "method": "Holm step-down adjustment",
        "family_definition": freeze["multiplicity"]["family_definition"],
        "hypothesis_count": len(holm_rows),
        "alpha": alpha,
        "post_test_amendment": True,
        "rows": holm_rows,
    }
    bootstrap_bytes = canonical_json_bytes(bootstrap_report) + b"\n"
    holm_bytes = canonical_json_bytes(holm_report) + b"\n"
    statistics_receipt = {
        "schema_version": "ais-r6-statistics-runtime-receipt/1.0",
        "packet_raw_sha256": sha256_file(packet_path),
        "runner_raw_sha256": sha256_file(SCRIPT_PATH),
        "bootstrap_report_raw_sha256": _raw_sha256(bootstrap_bytes),
        "holm_report_raw_sha256": _raw_sha256(holm_bytes),
        "primary_result": primary,
        "output_file_count": 3,
        "bootstrap_status": "PASS",
        "holm_status": "PASS_POST_TEST_EXPLORATORY_AMENDMENT",
        "accepted_result_rows": 0,
        "paper_numbers_authorized": False,
        "next_gate": "FRESH_AIS_R7_E5_INDEPENDENT_AUDIT",
        "verdict": "PASS_READY_FOR_FRESH_INDEPENDENT_AUDIT",
    }
    receipt_bytes = canonical_json_bytes(statistics_receipt) + b"\n"
    output_root = Path(packet["output_contract"]["statistics_root"])
    output_root.mkdir()
    (output_root / "bootstrap_report.json").write_bytes(bootstrap_bytes)
    (output_root / "holm_report.json").write_bytes(holm_bytes)
    (output_root / "statistics_receipt.json").write_bytes(receipt_bytes)
    return statistics_receipt


def _self_test() -> None:
    candidate = np.asarray([[0.2, 0.4], [0.6, 0.8]], dtype=np.float64)
    baseline = np.zeros_like(candidate)
    delta_bank = (candidate - baseline)[np.newaxis, :, :]
    samples = _shared_hierarchical_samples(delta_bank, samples=7, seed=19)[0]
    interval = hierarchical_paired_bootstrap(candidate, baseline, samples=7, seed=19)
    lower, upper = np.quantile(samples, [0.025, 0.975], method="linear")
    _require(math.isclose(float(delta_bank.mean()), interval.mean_delta), "self-test mean")
    _require(math.isclose(float(lower), interval.lower), "self-test lower")
    _require(math.isclose(float(upper), interval.upper), "self-test upper")
    _require(
        holm_adjust({"a": 0.01, "b": 0.04, "c": 0.2})
        == {"a": 0.03, "b": 0.08, "c": 0.2},
        "self-test Holm",
    )
    print("SELF_TEST=PASS")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.self_test:
        _self_test()
        return 0
    _require(args.packet is not None, "--packet is required")
    packet, _runtime, loaded = _load_and_validate_inputs(args.packet.resolve())
    packet_output = Path(packet["output_contract"]["statistics_root"]).resolve()
    _require(args.output_root is not None, "--output-root is required")
    _require(args.output_root.resolve() == packet_output, "output-root argument mismatch")
    if args.validate_only:
        print("STATISTICS_INPUT_VALIDATION=PASS")
        return 0
    receipt = _execute(packet, loaded, args.packet.resolve())
    print(canonical_json_bytes(receipt).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
