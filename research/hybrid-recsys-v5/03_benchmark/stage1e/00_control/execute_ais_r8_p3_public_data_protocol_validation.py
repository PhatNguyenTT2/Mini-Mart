from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


PACKET_SCHEMA = "ais-r8-p3-public-data-protocol-validation-execution-packet/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        normalized = key.casefold()
        if normalized in folded and folded[normalized] != key:
            raise ValueError(f"case-colliding JSON keys: {folded[normalized]} and {key}")
        folded[normalized] = key
        result[key] = value
    return result


def load_json(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"UTF-8 BOM is prohibited: {path}")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_object)
    if not isinstance(value, dict):
        raise ValueError(f"top-level JSON object required: {path}")
    return value


def atomic_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with temporary.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def resolve_repo_path(repo_root: pathlib.Path, relative: str) -> pathlib.Path:
    target = (repo_root / relative).resolve()
    try:
        target.relative_to(repo_root)
    except ValueError as error:
        raise ValueError(f"repository path escapes root: {relative}") from error
    return target


def verify_file(path: pathlib.Path, expected_sha256: str, expected_bytes: int | None) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required regular file missing: {path}")
    actual_bytes = path.stat().st_size
    if expected_bytes is not None and actual_bytes != expected_bytes:
        raise ValueError(f"file byte count mismatch: {path}")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(f"file SHA-256 mismatch: {path}")
    return {"path": str(path), "bytes": actual_bytes, "sha256": actual_sha256}


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema_version") != PACKET_SCHEMA:
        raise ValueError("unexpected packet schema")
    if packet.get("stage_id") != "AIS-R8-P3":
        raise ValueError("unexpected stage")
    if packet.get("namespace") != "PUBLIC_DATA_PROTOCOL_VALIDATION":
        raise ValueError("unexpected namespace")
    if packet.get("attempt_id") != "ais-r8-p3-public-validation-attempt-001":
        raise ValueError("unexpected attempt identity")
    if packet.get("execution_authorized") is not False:
        raise ValueError("immutable packet must remain pre-confirmation")
    if packet["runtime"]["network"] != "none":
        raise ValueError("network must be disabled")
    if packet["runtime"]["automatic_retry"] is not False:
        raise ValueError("automatic retry is prohibited")
    if packet["runtime"]["project_v5_test_access"] is not False:
        raise ValueError("v5 TEST access is prohibited")


def docker_server_probe(docker: pathlib.Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            str(docker),
            "version",
            "--format",
            "{{json .Server}}",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Docker daemon is not ready: {detail}")
    server = json.loads(result.stdout)
    if server.get("Os") != "linux" or server.get("Arch") != "amd64":
        raise RuntimeError("Docker server must be linux/amd64")
    return server


def verify_image(docker: pathlib.Path, image_reference: str) -> dict[str, Any]:
    result = subprocess.run(
        [str(docker), "image", "inspect", image_reference],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("pinned image is not locally available; pulling is prohibited")
    payload = json.loads(result.stdout)
    if not isinstance(payload, list) or len(payload) != 1:
        raise RuntimeError("unexpected Docker image-inspect response")
    image = payload[0]
    repo_digests = image.get("RepoDigests") or []
    expected_digest = image_reference.split("@", 1)[1]
    if not any(str(value).endswith("@" + expected_digest) for value in repo_digests):
        raise RuntimeError("local image does not expose the pinned repository digest")
    return {
        "id": image.get("Id"),
        "repo_digests": repo_digests,
        "architecture": image.get("Architecture"),
        "os": image.get("Os"),
    }


def assert_container_absent(docker: pathlib.Path, name: str) -> None:
    result = subprocess.run(
        [
            str(docker),
            "ps",
            "-a",
            "--filter",
            f"name=^/{name}$",
            "--format",
            "{{.ID}}",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("unable to query container-name state")
    if result.stdout.strip():
        raise RuntimeError("reserved container name already exists; automatic deletion is prohibited")


def assert_safe_output_root(output_root: pathlib.Path, repo_root: pathlib.Path, minimum_free_bytes: int) -> None:
    resolved = output_root.resolve(strict=False)
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise ValueError("runtime output root must remain outside the repository")
    if resolved.exists():
        raise FileExistsError("fresh attempt root already exists")
    existing = resolved.parent
    while not existing.exists():
        if existing.parent == existing:
            raise ValueError("no existing output ancestor found")
        existing = existing.parent
    if existing.is_symlink():
        raise ValueError("output ancestor may not be a symlink")
    if shutil.disk_usage(existing).free < minimum_free_bytes:
        raise RuntimeError("insufficient free disk capacity")


def build_docker_argv(
    packet: dict[str, Any],
    paths: dict[str, pathlib.Path],
    output_root: pathlib.Path,
) -> list[str]:
    runtime = packet["runtime"]
    runner_sha = packet["input_bindings"]["runner"]["sha256"]
    spec_sha = packet["input_bindings"]["spec"]["sha256"]
    environment_receipt_sha = packet["input_bindings"]["environment_receipt"]["sha256"]
    return [
        str(paths["docker"]),
        "run",
        "--rm",
        "--pull=never",
        "--name",
        runtime["container_name"],
        "--platform",
        "linux/amd64",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=536870912,mode=1777",
        "--user",
        "10001:10001",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--cpus",
        "2",
        "--memory",
        "4g",
        "--stop-timeout",
        "10",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "PYTHONNOUSERSITE=1",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "OMP_NUM_THREADS=2",
        "--env",
        "MKL_NUM_THREADS=2",
        "--env",
        "AIS_R8_SPEC_PATH=/stage1e/packet/spec.json",
        "--env",
        "AIS_R8_OUTPUT_ROOT=/stage1e/run",
        "--env",
        f"AIS_R8_EXPECTED_SPEC_SHA256={spec_sha}",
        "--env",
        f"AIS_R8_EXPECTED_RUNNER_SHA256={runner_sha}",
        "--env",
        "AIS_R8_TORCH_THREADS=2",
        "--env",
        f"AIS_R8_IMAGE_REFERENCE={runtime['image_reference']}",
        "--env",
        f"AIS_R8_SOURCE_ENVIRONMENT_RECEIPT_SHA256={environment_receipt_sha}",
        "--mount",
        f"type=bind,src={paths['environment_root']},dst=/stage1e/env,readonly",
        "--mount",
        f"type=bind,src={paths['dataset_root']},dst=/stage1e/data,readonly",
        "--mount",
        f"type=bind,src={paths['spec']},dst=/stage1e/packet/spec.json,readonly",
        "--mount",
        f"type=bind,src={paths['runner']},dst=/stage1e/packet/runner.py,readonly",
        "--mount",
        f"type=bind,src={output_root},dst=/stage1e/run",
        "--workdir",
        "/stage1e/run",
        runtime["image_reference"],
        "/stage1e/env/venv/bin/python",
        "-B",
        "/stage1e/packet/runner.py",
    ]


def static_preflight(packet_path: pathlib.Path, packet: dict[str, Any]) -> tuple[pathlib.Path, dict[str, pathlib.Path], list[dict[str, Any]]]:
    validate_packet(packet)
    repo_root = pathlib.Path(packet["repository_root"]).resolve()
    if not repo_root.is_dir():
        raise ValueError("repository root is missing")
    paths: dict[str, pathlib.Path] = {
        "packet": packet_path.resolve(),
        "executor": pathlib.Path(__file__).resolve(),
        "docker": pathlib.Path(packet["runtime"]["docker_executable"]).resolve(),
        "host_python": pathlib.Path(packet["runtime"]["host_python_executable"]).resolve(),
        "environment_root": resolve_repo_path(repo_root, packet["runtime"]["environment_root"]),
        "dataset_root": resolve_repo_path(repo_root, packet["runtime"]["dataset_root"]),
    }
    for name, binding in packet["input_bindings"].items():
        if name == "packet":
            continue
        if name == "executor":
            paths[name] = pathlib.Path(__file__).resolve()
        else:
            paths[name] = resolve_repo_path(repo_root, binding["path"])

    checks: list[dict[str, Any]] = []
    for name, binding in packet["input_bindings"].items():
        if name == "packet":
            continue
        if name not in paths:
            raise ValueError(f"unmapped input binding: {name}")
        checks.append(
            verify_file(paths[name], binding["sha256"], binding.get("bytes"))
        )
    checks.append(
        verify_file(
            paths["docker"],
            packet["runtime"]["docker_executable_sha256"],
            packet["runtime"]["docker_executable_bytes"],
        )
    )
    checks.append(
        verify_file(
            paths["host_python"],
            packet["runtime"]["host_python_executable_sha256"],
            packet["runtime"]["host_python_executable_bytes"],
        )
    )
    if pathlib.Path(sys.executable).resolve() != paths["host_python"]:
        raise ValueError("executor is not running under the pinned host Python")
    amendment = load_json(paths["amendment"])
    if amendment.get("verdict") != "PUBLIC_DATA_PROTOCOL_VALIDATION_DESIGN_FROZEN":
        raise ValueError("R8-P2 amendment is not admitted")
    spec = load_json(paths["spec"])
    if spec.get("schema_version") != "ais-r8-p3-public-data-protocol-validation-spec/1.0":
        raise ValueError("R8-P3 spec is not admitted")
    return repo_root, paths, checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--confirmed-packet-sha")
    parser.add_argument("--static-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_path = pathlib.Path(args.packet).resolve()
    packet = load_json(packet_path)
    packet_sha = sha256_file(packet_path)
    repo_root, paths, file_checks = static_preflight(packet_path, packet)
    if args.static_only:
        print(
            json.dumps(
                {
                    "status": "STATIC_PREFLIGHT_PASS",
                    "packet_sha256": packet_sha,
                    "verified_file_count": len(file_checks),
                    "execution_performed": False,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.confirmed_packet_sha != packet_sha:
        raise ValueError("fresh packet-bound confirmation SHA is missing or incorrect")
    output_root = pathlib.Path(packet["runtime"]["output_root"])
    assert_safe_output_root(
        output_root,
        repo_root,
        int(packet["runtime"]["minimum_free_bytes"]),
    )
    server = docker_server_probe(paths["docker"])
    image = verify_image(paths["docker"], packet["runtime"]["image_reference"])
    assert_container_absent(paths["docker"], packet["runtime"]["container_name"])

    output_root.mkdir(parents=True, exist_ok=False)
    docker_argv = build_docker_argv(packet, paths, output_root)
    atomic_json(
        output_root / "host_preflight.json",
        {
            "schema_version": "ais-r8-p3-host-preflight/1.0",
            "created_at": utc_now(),
            "status": "PASS_EXECUTION_STARTING",
            "packet_sha256": packet_sha,
            "confirmed_packet_sha256": args.confirmed_packet_sha,
            "verified_files": file_checks,
            "docker_server": server,
            "docker_image": image,
            "docker_argv": docker_argv,
            "docker_argv_sha256": canonical_hash(docker_argv),
            "output_root_absent_before_creation": True,
            "network": "none",
            "automatic_retry": False,
            "project_v5_test_access": False,
        },
    )
    print("AIS_R8_P3_RUNTIME_START", flush=True)
    process = subprocess.run(
        docker_argv,
        cwd=repo_root,
        stdin=subprocess.DEVNULL,
        timeout=int(packet["runtime"]["overall_timeout_seconds"]),
        check=False,
    )
    if process.returncode != 0:
        failure_path = output_root / "host_failure_receipt.json"
        if not failure_path.exists():
            atomic_json(
                failure_path,
                {
                    "schema_version": "ais-r8-p3-host-runtime-failure/1.0",
                    "created_at": utc_now(),
                    "status": "FAILED_NO_RETRY",
                    "docker_return_code": process.returncode,
                    "docker_argv_sha256": canonical_hash(docker_argv),
                    "automatic_retry_performed": False,
                    "project_v5_test_opened": False,
                },
            )
        raise RuntimeError(f"Docker runtime failed with exit code {process.returncode}")
    manifest = load_json(output_root / "run_manifest.json")
    if manifest.get("status") != "COMPLETED_UNAUDITED":
        raise RuntimeError("runtime returned without a completed un-audited manifest")
    print("AIS_R8_P3_RUNTIME_COMPLETED_UNAUDITED", flush=True)
    print(json.dumps({"run_manifest": str(output_root / "run_manifest.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
