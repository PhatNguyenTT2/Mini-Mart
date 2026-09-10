from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import traceback
from typing import Any


ATTEMPT_ID = "ais-r8-p3-public-validation-attempt-002"
EXPECTED_OUTPUT_ROOT = "E:/UIT/cv/materialized-experiments/hybrid-recsys-v5/ai-service-v2/r8/public-data-protocol-validation/attempt-002"


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


def load_base_executor(path: pathlib.Path) -> Any:
    module_spec = importlib.util.spec_from_file_location("ais_r8_p3_base_executor", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("unable to load immutable base executor")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def main() -> int:
    if "--packet" not in sys.argv:
        raise ValueError("--packet is required")
    packet_path = pathlib.Path(sys.argv[sys.argv.index("--packet") + 1]).resolve()
    packet = read_json(packet_path)
    repo_root = pathlib.Path(packet["repository_root"]).resolve()
    wrapper_binding = packet["input_bindings"]["executor_wrapper"]
    wrapper_path = (repo_root / wrapper_binding["path"]).resolve()
    if wrapper_path != pathlib.Path(__file__).resolve():
        raise ValueError("executor-wrapper path binding mismatch")
    if sha256(wrapper_path) != wrapper_binding["sha256"]:
        raise ValueError("executor-wrapper SHA-256 mismatch")

    base_binding = packet["input_bindings"]["executor"]
    base_path = (repo_root / base_binding["path"]).resolve()
    if sha256(base_path) != base_binding["sha256"]:
        raise ValueError("immutable base-executor SHA-256 mismatch")
    base = load_base_executor(base_path)

    original_static_preflight = base.static_preflight
    original_build_docker_argv = base.build_docker_argv

    def validate_packet_attempt002(payload: dict[str, Any]) -> None:
        if payload.get("schema_version") != base.PACKET_SCHEMA:
            raise ValueError("unexpected packet schema")
        if payload.get("stage_id") != "AIS-R8-P3":
            raise ValueError("unexpected stage")
        if payload.get("namespace") != "PUBLIC_DATA_PROTOCOL_VALIDATION":
            raise ValueError("unexpected namespace")
        if payload.get("attempt_id") != ATTEMPT_ID:
            raise ValueError("unexpected attempt identity")
        if payload.get("execution_authorized") is not False:
            raise ValueError("immutable packet must remain pre-confirmation")
        runtime = payload["runtime"]
        if runtime["output_root"] != EXPECTED_OUTPUT_ROOT:
            raise ValueError("unexpected attempt-002 output root")
        if runtime["container_name"] != "ais-r8-p3-public-validation-attempt-002":
            raise ValueError("unexpected attempt-002 container name")
        if runtime["network"] != "none" or runtime["automatic_retry"] is not False:
            raise ValueError("network or retry policy drift")
        if runtime["project_v5_test_access"] is not False:
            raise ValueError("v5 TEST access is prohibited")

    def static_preflight_attempt002(
        current_packet_path: pathlib.Path,
        payload: dict[str, Any],
    ) -> tuple[pathlib.Path, dict[str, pathlib.Path], list[dict[str, Any]]]:
        resolved_root, paths, checks = original_static_preflight(current_packet_path, payload)
        p4 = base.load_json(paths["p4_receipt"])
        if p4.get("verdict") != "PUBLIC_DATA_PROTOCOL_VALIDATION_FAIL":
            raise ValueError("P4 remediation authority is not a fail receipt")
        spec = base.load_json(paths["spec"])
        if spec.get("attempt_id") != ATTEMPT_ID:
            raise ValueError("spec attempt identity mismatch")
        if spec["protocol"].get("seen_item_masking") is not True:
            raise ValueError("seen-item masking drift")
        if spec["protocol"].get("repeatable") is not False:
            raise ValueError("protocol repeatable must be false")
        if spec["common_config"].get("repeatable") is not False:
            raise ValueError("runtime repeatable must be false")
        if any("repeatable" in row["model_config"] for row in spec["runs"]):
            raise ValueError("model-specific repeatable override prohibited")
        return resolved_root, paths, checks

    def build_docker_argv_attempt002(
        payload: dict[str, Any],
        paths: dict[str, pathlib.Path],
        output_root: pathlib.Path,
    ) -> list[str]:
        argv = original_build_docker_argv(payload, paths, output_root)
        base_runner_hash = payload["input_bindings"]["base_runner"]["sha256"]
        wrapper_hash = payload["input_bindings"]["runner"]["sha256"]
        for index, value in enumerate(argv):
            if value.startswith("AIS_R8_EXPECTED_RUNNER_SHA256="):
                argv[index] = f"AIS_R8_EXPECTED_RUNNER_SHA256={base_runner_hash}"
                break
        insertion = argv.index("--workdir")
        additions = [
            "--env",
            f"AIS_R8_EXPECTED_WRAPPER_SHA256={wrapper_hash}",
            "--env",
            f"AIS_R8_EXPECTED_BASE_RUNNER_SHA256={base_runner_hash}",
            "--mount",
            f"type=bind,src={paths['base_runner']},dst=/stage1e/packet/base_runner.py,readonly",
        ]
        return argv[:insertion] + additions + argv[insertion:]

    base.validate_packet = validate_packet_attempt002
    base.static_preflight = static_preflight_attempt002
    base.build_docker_argv = build_docker_argv_attempt002
    return int(base.main())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
