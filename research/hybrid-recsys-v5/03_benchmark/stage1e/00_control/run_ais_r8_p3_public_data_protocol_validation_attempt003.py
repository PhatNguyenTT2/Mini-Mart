from __future__ import annotations

import gc
import hashlib
import importlib.util
import json
import os
import pathlib
import traceback
from datetime import datetime, timezone
from typing import Any


ATTEMPT_ID = "ais-r8-p3-public-validation-attempt-003"
BASE_RUNNER = pathlib.Path("/stage1e/packet/base_runner.py")


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
    folded: dict[str, str] = {}
    for key, value in pairs:
        normalized = key.casefold()
        if key in result or (normalized in folded and folded[normalized] != key):
            raise ValueError(f"duplicate or case-colliding JSON key: {key}")
        folded[normalized] = key
        result[key] = value
    return result


def read_json(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM prohibited: {path}")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    if not isinstance(value, dict):
        raise ValueError(f"top-level JSON object required: {path}")
    return value


def write_json(path: pathlib.Path, payload: dict[str, Any], *, replace: bool = False) -> None:
    temporary = path.with_name(path.name + ".partial")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with temporary.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    if path.exists() and not replace:
        temporary.unlink()
        raise FileExistsError(path)
    os.replace(temporary, path)


def user_item_sets(dataset: Any) -> list[set[int]]:
    result = [set() for _ in range(int(dataset.user_num))]
    users = dataset.inter_feat[dataset.uid_field].detach().cpu().tolist()
    items = dataset.inter_feat[dataset.iid_field].detach().cpu().tolist()
    for user, item in zip(users, items):
        result[int(user)].add(int(item))
    return result


def assert_history_masking(spec: dict[str, Any]) -> dict[str, Any]:
    import torch
    from recbole.config import Config
    from recbole.data import create_dataset, data_preparation
    from recbole.utils import init_seed

    if spec.get("attempt_id") != ATTEMPT_ID:
        raise ValueError("attempt identity drift")
    if spec["protocol"].get("seen_item_masking") is not True:
        raise ValueError("seen-item masking must remain enabled")
    if spec["protocol"].get("repeatable") is not False:
        raise ValueError("protocol repeatable must be false")
    if spec["common_config"].get("repeatable") is not False:
        raise ValueError("runtime repeatable must be false")
    if any("repeatable" in row["model_config"] for row in spec["runs"]):
        raise ValueError("model-specific repeatable override prohibited")

    row = next(item for item in spec["runs"] if item["run_id"] == "recbole-bpr-seed-42")
    requested = dict(spec["common_config"])
    requested.update(row["model_config"])
    requested["seed"] = row["seed"]
    requested["checkpoint_dir"] = "/tmp/ais-r8-mask-probe-checkpoints"
    config = Config(model=row["model"], dataset=spec["dataset"]["name"], config_dict=requested)
    if config["repeatable"] is not False:
        raise ValueError("resolved RecBole repeatable flag is not false")
    init_seed(config["seed"], config["reproducibility"])
    dataset = create_dataset(config)
    train, valid, test = data_preparation(config, dataset)

    valid_protocol_sampler = getattr(valid, "_sampler", None)
    test_protocol_sampler = getattr(test, "_sampler", None)
    if type(valid_protocol_sampler).__name__ != "Sampler" or type(test_protocol_sampler).__name__ != "Sampler":
        raise ValueError("phase-aware RecBole _sampler was not selected")
    if getattr(valid_protocol_sampler, "phase", None) != "valid":
        raise ValueError("validation RecBole sampler phase mismatch")
    if getattr(test_protocol_sampler, "phase", None) != "test":
        raise ValueError("test RecBole sampler phase mismatch")
    if type(valid).__name__ != "FullSortEvalDataLoader" or type(test).__name__ != "FullSortEvalDataLoader":
        raise ValueError("full-sort evaluator dataloader was not selected")

    train_sets = user_item_sets(train._dataset)
    valid_sets = user_item_sets(valid._dataset)
    validation_pairs = 0
    test_pairs = 0
    for user_tensor in valid.uid_list:
        user = int(user_tensor.item())
        actual = {int(item) for item in valid.uid2history_item[user].tolist()}
        expected = train_sets[user]
        if actual != expected:
            raise ValueError(f"validation history mask mismatch for internal user {user}")
        validation_pairs += len(actual)
    for user_tensor in test.uid_list:
        user = int(user_tensor.item())
        actual = {int(item) for item in test.uid2history_item[user].tolist()}
        expected = train_sets[user] | valid_sets[user]
        if actual != expected:
            raise ValueError(f"test history mask mismatch for internal user {user}")
        test_pairs += len(actual)

    interaction, history_index, positive_u, positive_i = next(iter(valid))
    if history_index is None or history_index[0].numel() == 0:
        raise ValueError("validation full-sort batch does not expose history indices")
    fixture_scores = torch.zeros(
        (len(interaction), int(valid._dataset.item_num)), dtype=torch.float32
    )
    fixture_scores[:, 0] = -torch.inf
    fixture_scores[history_index] = -torch.inf
    if not torch.isneginf(fixture_scores[history_index]).all().item():
        raise ValueError("history-index score masking fixture failed")
    if torch.isneginf(fixture_scores[positive_u, positive_i]).any().item():
        raise ValueError("history-index fixture masks a held-out positive")

    receipt = {
        "schema_version": "ais-r8-p3-attempt003-masking-semantics/1.0",
        "status": "PASS_BEFORE_TRAINING",
        "checked_at": now(),
        "attempt_id": ATTEMPT_ID,
        "resolved_repeatable": False,
        "validation_protocol_sampler": type(valid_protocol_sampler).__name__,
        "test_protocol_sampler": type(test_protocol_sampler).__name__,
        "validation_protocol_sampler_phase": valid_protocol_sampler.phase,
        "test_protocol_sampler_phase": test_protocol_sampler.phase,
        "validation_torch_sampler": type(valid.sampler).__name__,
        "test_torch_sampler": type(test.sampler).__name__,
        "validation_dataloader": type(valid).__name__,
        "test_dataloader": type(test).__name__,
        "validation_users_checked": len(valid.uid_list),
        "test_users_checked": len(test.uid_list),
        "validation_masked_user_item_pairs": validation_pairs,
        "test_masked_user_item_pairs": test_pairs,
        "validation_history_semantics": "TRAIN interactions only",
        "test_history_semantics": "TRAIN plus validation interactions",
        "mask_application_fixture": "PASS",
        "mask_application_fixture_history_pairs": int(history_index[0].numel()),
        "mask_application_fixture_positive_pairs": int(positive_u.numel()),
        "candidate_padding_excluded_by_trainer": True,
        "training_performed_by_probe": False,
        "evaluation_performed_by_probe": False,
        "project_v5_test_access": False,
    }
    del fixture_scores, train, valid, test, dataset
    gc.collect()
    return receipt


def load_base_runner() -> Any:
    module_spec = importlib.util.spec_from_file_location("ais_r8_p3_base_runner", BASE_RUNNER)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("unable to load immutable base runner")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def main() -> int:
    wrapper_path = pathlib.Path(__file__).resolve()
    spec_path = pathlib.Path(os.environ["AIS_R8_SPEC_PATH"])
    output_root = pathlib.Path(os.environ["AIS_R8_OUTPUT_ROOT"])
    wrapper_hash = sha256(wrapper_path)
    base_hash = sha256(BASE_RUNNER)
    if wrapper_hash != os.environ["AIS_R8_EXPECTED_WRAPPER_SHA256"]:
        raise ValueError("attempt-003 wrapper hash mismatch")
    if base_hash != os.environ["AIS_R8_EXPECTED_BASE_RUNNER_SHA256"]:
        raise ValueError("immutable base-runner hash mismatch")
    if sha256(spec_path) != os.environ["AIS_R8_EXPECTED_SPEC_SHA256"]:
        raise ValueError("spec hash mismatch")
    if sorted(path.name for path in output_root.iterdir()) != ["host_preflight.json"]:
        raise ValueError("attempt-003 output root is not fresh")

    spec = read_json(spec_path)
    masking_receipt = assert_history_masking(spec)
    masking_receipt["spec_sha256"] = sha256(spec_path)
    masking_receipt["wrapper_sha256"] = wrapper_hash
    masking_receipt["base_runner_sha256"] = base_hash
    masking_receipt["masking_source_bindings"] = spec["masking_source_bindings"]
    print("AIS_R8_MASKING_PREFLIGHT_PASS", flush=True)

    os.environ["AIS_R8_EXPECTED_RUNNER_SHA256"] = base_hash
    base_runner = load_base_runner()
    result = int(base_runner.main())
    if result != 0:
        raise RuntimeError(f"immutable base runner returned {result}")

    masking_path = output_root / "masking_semantics_receipt.json"
    write_json(masking_path, masking_receipt)
    manifest_path = output_root / "run_manifest.json"
    manifest = read_json(manifest_path)
    manifest["attempt003_wrapper_sha256"] = wrapper_hash
    manifest["base_runner_sha256"] = base_hash
    manifest["masking_semantics_receipt"] = {
        "path": masking_path.relative_to(output_root).as_posix(),
        "bytes": masking_path.stat().st_size,
        "sha256": sha256(masking_path),
        "status": masking_receipt["status"],
    }
    manifest["key_artifacts"].append(manifest["masking_semantics_receipt"])
    write_json(manifest_path, manifest, replace=True)
    print("AIS_R8_MASKING_RECEIPT_WRITTEN", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        output = os.environ.get("AIS_R8_OUTPUT_ROOT")
        if output and pathlib.Path(output).is_dir():
            failure = pathlib.Path(output) / "failure_receipt.json"
            if not failure.exists():
                try:
                    write_json(
                        failure,
                        {
                            "schema_version": "ais-r8-p3-attempt003-failure/1.0",
                            "status": "FAILED_NO_RETRY",
                            "created_at": now(),
                            "error_type": type(error).__name__,
                            "error": str(error),
                            "traceback": traceback.format_exc(),
                            "automatic_retry": False,
                            "project_v5_test_opened": False,
                        },
                    )
                except Exception:
                    pass
        traceback.print_exc()
        raise
