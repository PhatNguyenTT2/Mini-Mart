"""Fixed predecessor metadata reads, never a historical payload replay."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import canonical_json_bytes, loads_strict_json, sha256_bytes
from ai_service_v2.training.cost_runtime_custody import reject_reparse_path

SCOPE = "METADATA_CONTROL_SOURCE_ONLY"
BASELINE = "04934414c87ba8a49bccee76ae8366a68608f50b"
OLD_AUTHORITY_SHA256 = "e5aaf392cdc06198441900ff77c166e11450327c16867bcbaa11b2f029becfa1"
LOCAL = "research/hybrid-recsys-v5/06_venue_readiness/07_local_v5_validation"
CONTROL = LOCAL + "/00_control/cost_optimization_01"
OLD_AUTHORITY = CONTROL + "/reference_epoch_01/authority.json"
REFERENCE_CONTROLS = (
    "engineering_profile_reference_05_run.json",
    "profile_reference_05_run_outcome.json",
    "profile_reference_05_run_inventory.json",
    "profile_reference_03_wddm_policy.json",
    "profile_reference_03_wddm_probe_inventory.json",
    "profile_reference_03_wddm_probe_outcome.json",
    "profile_reference_04_run_inventory.json",
    "profile_reference_04_run_outcome.json",
)
REFERENCE_SOURCE_COMMIT = "eec560756146f9d96a6b6dbe61aa15750a6466bf"
REFERENCE_IMPLEMENTATION = (
    "ai-service-v2/tools/run_cost_profile_reference_05.py",
    "ai-service-v2/tools/manage_cost_profile_reference_05.py",
    "ai-service-v2/src/ai_service_v2/training/cost_profile_reference_05.py",
    "ai-service-v2/tests/test_cost_profile_reference_05.py",
    "ai-service-v2/tests/reference_05_subprocess_fixture.py",
    "ai-service-v2/tools/verify_cost_profile_reference_05.py",
    "ai-service-v2/tests/reference_05_history_view.py",
)
CASES = tuple(
    f"cost-opt-{method}-c{index}-s42" for method in ("bpr-mf", "lightgcn") for index in (1, 3, 5)
)
CASE_METADATA = (
    "cost_request.json",
    "cost_spec.json",
    "cost_native_configuration.json",
    "reference-training/selected-checkpoint/manifest.json",
)
SNAPSHOT = Path(
    "E:/UIT/cv/materialized-experiments/hybrid-recsys-v5/ai-service-v2/ais-r2b-v5.1-canonical/attempt-001"
)
FEATURES = Path(
    "E:/UIT/cv/materialized-experiments/hybrid-recsys-v5/mp2/p4/correction/g1/attempt-001/data/v5/package"
)
SEALED_GRAPHS = (
    (
        "cuda_telemetry_smoke_01",
        "cost-opt-01-cuda-telemetry-smoke-01",
        "engineering_authority.json",
        "CUDA_TELEMETRY_SMOKE_PASS_NON_AUTHORIZING",
        47,
    ),
    (
        "evaluator_engineering_02",
        "cost-opt-01-evaluator-engineering-02/run",
        "authority.json",
        "FAILED_TERMINAL_NO_RETRY",
        172,
    ),
    (
        "lightgcn_score_drift_diagnostic_02",
        "cost-opt-01-lightgcn-score-drift-diagnostic-02",
        "authority.json",
        "SCORE_DRIFT_UNRESOLVED_NON_AUTHORIZING",
        107,
    ),
    (
        "evaluator_engineering_03/cpu_corpus_delta_01",
        "cost-opt-01-evaluator-engineering-03/run",
        "authority.json",
        "EVALUATOR_ENGINEERING_03_CPU_CORPUS_PASS_NON_AUTHORIZING",
        147,
    ),
)
_ACTIVE: tuple[MetadataBoundary, ...] = ()
_ACTIVE_LOCK = threading.RLock()


def path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


class MetadataBoundary:
    """Audit Python file opens across transitive helpers within evidence roots."""

    def __init__(self, allowed: Mapping[Path, str], roots: tuple[Path, ...]) -> None:
        self.allowed: dict[str, tuple[Path, str]] = {}
        for path, scope in allowed.items():
            reject_reparse_path(path)
            key = path_key(path)
            if key in self.allowed:
                raise IntegrityError("METADATA_DUPLICATE_PATH")
            self.allowed[key] = (path, scope)
        self.roots = tuple(path_key(root) for root in roots)
        self.reads: dict[str, int] = {}
        self.denied = 0
        self.bytecode_prevented = 0

    def observe(self, path: str | bytes | os.PathLike[str], mode: Any, flags: int) -> None:
        key = path_key(Path(os.fsdecode(path)))
        protected = any(key == root or key.startswith(root + os.sep) for root in self.roots)
        if not protected and key not in self.allowed:
            dependency = any(
                key.startswith(path_key(Path(root)) + os.sep)
                for root in (sys.prefix, sys.base_prefix)
            )
            if dependency or Path(key).suffix.casefold() not in {
                ".json",
                ".pt",
                ".npy",
                ".npz",
                ".inter",
                ".pkl",
                ".pickle",
            }:
                return
            self.denied += 1
            raise IntegrityError("METADATA_READ_FORBIDDEN: " + key)
        if key.endswith(".pyc") and Path(key).parent.name == "__pycache__":
            source = Path(key).parent.parent / (Path(key).name.split(".")[0] + ".py")
            entry = self.allowed.get(path_key(source))
            if entry and entry[1] == "GIT_DECLARED_SOURCE":
                # Importlib treats a missing cache as a request to read source.
                self.bytecode_prevented += 1
                raise FileNotFoundError("metadata consumers require bound Python source")
        writing = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        if key not in self.allowed or writing:
            self.denied += 1
            raise IntegrityError("METADATA_READ_FORBIDDEN: " + key)
        reject_reparse_path(Path(os.fsdecode(path)))
        self.reads[key] = self.reads.get(key, 0) + 1

    @contextmanager
    def enforce(self) -> Iterator[MetadataBoundary]:
        global _ACTIVE
        with _ACTIVE_LOCK:
            _ACTIVE = (*_ACTIVE, self)
        try:
            yield self
        finally:
            with _ACTIVE_LOCK:
                position = _ACTIVE.index(self)
                _ACTIVE = _ACTIVE[:position] + _ACTIVE[position + 1 :]

    def report(self) -> dict[str, Any]:
        return {
            "read_scope": SCOPE,
            "read_ledger": [
                {"path": str(self.allowed[key][0]), "scope": self.allowed[key][1], "reads": count}
                for key, count in sorted(self.reads.items())
            ],
            "denied_reads": self.denied,
            "bytecode_reads_prevented": self.bytecode_prevented,
            "boundary": "PYTHON_AUDIT_OPEN_TRANSITIVE_EVIDENCE_ROOTS",
            "payload_bytes_certified": False,
        }


def _audit(event: str, args: tuple[Any, ...]) -> None:
    boundaries = _ACTIVE
    if not boundaries:
        return
    if event == "open" and not isinstance(args[0], int):
        for boundary in boundaries:
            boundary.observe(args[0], args[1], args[2])
    if event == "subprocess.Popen":
        executable = Path(str(args[0])).name.casefold()
        command = args[1]
        if args[0] is None and command == "lscpu" and os.name == "nt":
            raise FileNotFoundError("no platform probe subprocess in metadata consumers")
        windows_git = (
            args[0] is None
            and isinstance(command, str)
            and re.match(r"^git(?:\.exe)? ", command, re.IGNORECASE)
        )
        if executable not in {"git", "git.exe"} and not windows_git:
            raise IntegrityError("METADATA_SUBPROCESS_FORBIDDEN")


sys.addaudithook(_audit)


def canonical_document(data: bytes) -> dict[str, Any]:
    document = loads_strict_json(data)
    if not isinstance(document, dict) or data != canonical_json_bytes(document) + b"\n":
        raise IntegrityError("METADATA_NONCANONICAL_JSON")
    return document


def relative_path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or value.startswith("/")
    ):
        raise IntegrityError("METADATA_PATH_ALIAS_OR_TRAVERSAL")
    return value


def validate_inventory(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise IntegrityError("METADATA_INVENTORY_SCHEMA")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"path", "bytes", "sha256"}
            or type(row["bytes"]) is not int
            or row["bytes"] < 0
            or not isinstance(row["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
        ):
            raise IntegrityError("METADATA_INVENTORY_ROW")
        path = relative_path(row["path"])
        if path.casefold() in result:
            raise IntegrityError("METADATA_DUPLICATE_PATH")
        result[path.casefold()] = row
    return result


def git_blob(repository: Path, commit: str, relative: str) -> bytes:
    relative_path(relative)
    return subprocess.run(
        ["git", "-C", str(repository), "show", f"{commit}:{relative}"],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def fixed_predecessor_paths(repository: Path, historical: Path, cache: Path) -> tuple[Path, ...]:
    rows: list[Path] = []
    for sibling, names in (
        (
            "cuda_telemetry_smoke_01",
            ("engineering_authority.json", "budget.json", "outcome.json", "inventory.json"),
        ),
        (
            "evaluator_engineering_02",
            ("authority.json", "budget.json", "outcome.json", "inventory.json"),
        ),
        ("lightgcn_score_drift_diagnostic_01", ("authority.json", "budget.json")),
    ):
        rows.extend(historical / CONTROL / sibling / name for name in names)
    rows.extend(
        cache / "cost-opt-01-lightgcn-score-drift-diagnostic-01" / name
        for name in ("invocation_guard.json", "terminal_outcome.json", "inventory.json")
    )
    rows.extend(
        cache / "cost-opt-01-evaluator-engineering-02/run" / name
        for name in ("invocation_guard.json", "failure_receipt.json", "diagnostics/failure.json")
    )
    rows.append(
        cache / "cost-opt-01-evaluator-engineering-03-control/score_drift_reconciliation.json"
    )
    for sibling in (
        "lightgcn_score_drift_diagnostic_02",
        "evaluator_engineering_03/cpu_corpus_delta_01",
    ):
        rows.extend(
            repository / CONTROL / sibling / name
            for name in ("authority.json", "outcome.json", "inventory.json")
        )
    return tuple(rows)


def metadata_allowlist(repository: Path, historical: Path, cache: Path) -> dict[Path, str]:
    paths = fixed_predecessor_paths(repository, historical, cache)
    result = {path: "CONTROL_BYTES_ONLY" for path in paths}
    result[repository / OLD_AUTHORITY] = "GIT_BOUND_CONTROL_BYTES_ONLY"
    for name in REFERENCE_CONTROLS:
        result[repository / CONTROL / name] = "GIT_BOUND_CONTROL_BYTES_ONLY"
    reference = cache / "cost-opt-01-profile-reference-05/run"
    result[reference / "invocation_guard.json"] = "INVENTORY_BOUND_CONTROL_ONLY"
    result[reference / "_shared/reference-data/manifest.json"] = "MANIFEST_ONLY"
    for case in CASES:
        for name in CASE_METADATA:
            result[reference / "workloads" / case / name] = "INVENTORY_BOUND_METADATA_ONLY"
    for root in (SNAPSHOT, FEATURES):
        result[root / "manifest.json"] = "MANIFEST_ONLY"
    for _, namespace, _, _, _ in SEALED_GRAPHS:
        result[cache / namespace / "invocation_guard.json"] = "INVENTORY_BOUND_CONTROL_ONLY"
    for relative in (*reference_source_roster(repository), *REFERENCE_IMPLEMENTATION):
        result[historical / relative] = "HISTORICAL_SOURCE_BYTES_ONLY"
    return result


def reference_source_roster(repository: Path) -> tuple[str, ...]:
    data = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "ls-tree",
            "-r",
            "--name-only",
            REFERENCE_SOURCE_COMMIT,
            "ai-service-v2/src",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.decode("utf-8")
    return tuple(path for path in data.splitlines() if path.endswith(".py"))


def verify_predecessor_metadata(repository: Path, historical: Path, cache: Path) -> dict[str, Any]:
    """Follow fixed graph edges, not paths or payload rosters supplied by JSON."""
    boundary = MetadataBoundary(
        metadata_allowlist(repository, historical, cache),
        (repository, historical, cache, SNAPSHOT, FEATURES),
    )
    bindings = []
    with boundary.enforce():
        original = (repository / OLD_AUTHORITY).read_bytes()
        if (
            original != git_blob(repository, BASELINE, OLD_AUTHORITY)
            or sha256_bytes(original) != OLD_AUTHORITY_SHA256
        ):
            raise IntegrityError("METADATA_OLD_AUTHORITY_DRIFT")
        old = canonical_document(original)
        expected = fixed_predecessor_paths(repository, historical, cache)
        rows = old["predecessor_control_bindings"]
        if (
            not isinstance(rows, list)
            or len(rows) != len(expected)
            or [row.get("path") for row in rows] != [str(path) for path in expected]
        ):
            raise IntegrityError("METADATA_FIXED_PREDECESSOR_ROSTER")
        for path, row in zip(expected, rows, strict=True):
            if set(row) != {"path", "bytes", "sha256", "scope"}:
                raise IntegrityError("METADATA_CONTROL_ROW")
            data = path.read_bytes()
            if (
                type(row["bytes"]) is not int
                or len(data) != row["bytes"]
                or sha256_bytes(data) != row["sha256"]
            ):
                raise IntegrityError("METADATA_CONTROL_BYTES_DRIFT")
            if row["scope"] == "OPAQUE_GIT_BOUND_CONTROL_BYTES_ONLY":
                if data != git_blob(historical, BASELINE, path.relative_to(historical).as_posix()):
                    raise IntegrityError("METADATA_OPAQUE_GIT_DRIFT")
            else:
                canonical_document(data)
            if path.is_relative_to(repository) or path.is_relative_to(historical):
                root = repository if path.is_relative_to(repository) else historical
                if data != git_blob(root, BASELINE, path.relative_to(root).as_posix()):
                    raise IntegrityError("METADATA_CONTROL_GIT_DRIFT")
            bindings.append(row)
        for sibling, namespace, authority_name, state, count in SEALED_GRAPHS:
            root = (
                historical
                if sibling in {"cuda_telemetry_smoke_01", "evaluator_engineering_02"}
                else repository
            )
            control = root / CONTROL / sibling
            outcome = canonical_document((control / "outcome.json").read_bytes())
            inventory_bytes = (control / "inventory.json").read_bytes()
            inventory_key = (
                "artifact_bindings" if sibling == "evaluator_engineering_02" else "artifacts"
            )
            inventory = validate_inventory(canonical_document(inventory_bytes)[inventory_key])
            authority_hash = sha256_bytes((control / authority_name).read_bytes())
            if (
                outcome["state"] != state
                or type(outcome["artifact_count"]) is not int
                or outcome["artifact_count"] != count
                or len(inventory) != count
                or outcome["inventory_sha256"] != sha256_bytes(inventory_bytes)
                or outcome.get("authority_sha256", authority_hash) != authority_hash
            ):
                raise IntegrityError("METADATA_PREDECESSOR_GRAPH_LINK")
            guard_path = cache / namespace / "invocation_guard.json"
            data = guard_path.read_bytes()
            guard = canonical_document(data)
            row = inventory.get("invocation_guard.json")
            guard_authority_hash = (
                sha256_bytes(
                    canonical_json_bytes(
                        canonical_document((control / authority_name).read_bytes())
                    )
                )
                if sibling == "cuda_telemetry_smoke_01"
                else authority_hash
            )
            if (
                row is None
                or len(data) != row["bytes"]
                or sha256_bytes(data) != row["sha256"]
                or guard["authority_sha256"] != guard_authority_hash
                or outcome.get("guard_sha256", sha256_bytes(data)) != sha256_bytes(data)
            ):
                raise IntegrityError("METADATA_PREDECESSOR_GUARD_LINK")
            bindings.append(
                {**row, "path": str(guard_path), "scope": "INVENTORY_BOUND_CONTROL_ONLY"}
            )
        documents = {}
        for name in REFERENCE_CONTROLS:
            path = repository / CONTROL / name
            data = path.read_bytes()
            if data != git_blob(repository, BASELINE, path.relative_to(repository).as_posix()):
                raise IntegrityError("METADATA_REFERENCE_GIT_DRIFT")
            documents[name] = canonical_document(data)
            bindings.append(
                {
                    "path": str(path),
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                    "scope": "GIT_BOUND_CONTROL_BYTES_ONLY",
                }
            )
        outcome = documents["profile_reference_05_run_outcome.json"]
        reference_authority = documents["engineering_profile_reference_05_run.json"]
        if reference_authority["source_commit"] != REFERENCE_SOURCE_COMMIT:
            raise IntegrityError("METADATA_REFERENCE_SOURCE_IDENTITY")
        for key, roster in (
            ("implementation_bindings", REFERENCE_IMPLEMENTATION),
            ("dependency_bindings", reference_source_roster(repository)),
        ):
            rows = reference_authority[key]
            if [row.get("path") for row in rows] != list(roster):
                raise IntegrityError("METADATA_REFERENCE_SOURCE_ROSTER")
            validate_inventory(rows)
            for relative, row in zip(roster, rows, strict=True):
                path = historical / relative
                data = path.read_bytes()
                if (
                    data != git_blob(repository, REFERENCE_SOURCE_COMMIT, relative)
                    or len(data) != row["bytes"]
                    or sha256_bytes(data) != row["sha256"]
                ):
                    raise IntegrityError("METADATA_REFERENCE_SOURCE_DRIFT")
                bindings.append({**row, "path": str(path), "scope": "HISTORICAL_SOURCE_BYTES_ONLY"})
        for key, name in (
            ("predecessor_inventory_binding", "profile_reference_04_run_inventory.json"),
            ("predecessor_outcome_binding", "profile_reference_04_run_outcome.json"),
        ):
            declared = reference_authority[key]
            data = (repository / CONTROL / name).read_bytes()
            if (
                declared["path"] != CONTROL + "/" + name
                or type(declared["bytes"]) is not int
                or len(data) != declared["bytes"]
                or sha256_bytes(data) != declared["sha256"]
            ):
                raise IntegrityError("METADATA_REFERENCE_PREDECESSOR_LINK")
        inventory_path = repository / CONTROL / "profile_reference_05_run_inventory.json"
        authority_path = repository / CONTROL / "engineering_profile_reference_05_run.json"
        if (
            outcome["inventory_sha256"] != sha256_bytes(inventory_path.read_bytes())
            or outcome["authority_sha256"] != sha256_bytes(authority_path.read_bytes())
            or outcome["state"] != "PROFILE_STAGE_MEASURED_NON_AUTHORIZING"
            or type(outcome["artifact_count"]) is not int
            or outcome["artifact_count"] != 132
        ):
            raise IntegrityError("METADATA_REFERENCE_GRAPH_LINK")
        inventory = validate_inventory(
            documents["profile_reference_05_run_inventory.json"]["artifact_bindings"]
        )
        if len(inventory) != 132:
            raise IntegrityError("METADATA_REFERENCE_INVENTORY_COUNT")
        reference = cache / "cost-opt-01-profile-reference-05/run"
        for path, scope in metadata_allowlist(repository, historical, cache).items():
            if not path.is_relative_to(reference):
                continue
            key = path.relative_to(reference.parent).as_posix().casefold()
            if key not in inventory:
                raise IntegrityError("METADATA_MANIFEST_NOT_IN_INVENTORY")
            data = path.read_bytes()
            row = inventory[key]
            if len(data) != row["bytes"] or sha256_bytes(data) != row["sha256"]:
                raise IntegrityError("METADATA_MANIFEST_BYTES_DRIFT")
            document = canonical_document(data)
            if path == reference / "invocation_guard.json":
                if (
                    sha256_bytes(data) != outcome["invocation_guard_sha256"]
                    or document["authority_sha256"] != outcome["authority_sha256"]
                ):
                    raise IntegrityError("METADATA_REFERENCE_GUARD_LINK")
            bindings.append({**row, "path": str(path), "scope": scope})
        for path, row in zip(
            (SNAPSHOT / "manifest.json", FEATURES / "manifest.json"),
            old["dataset_binding"]["manifests"],
            strict=True,
        ):
            data = path.read_bytes()
            if (
                str(path) != row["path"]
                or len(data) != row["bytes"]
                or sha256_bytes(data) != row["sha256"]
            ):
                raise IntegrityError("METADATA_DATASET_MANIFEST_DRIFT")
            canonical_document(data)
            bindings.append({**row, "scope": "MANIFEST_ONLY"})
    unique: dict[str, dict[str, Any]] = {}
    for row in bindings:
        key = path_key(Path(row["path"]))
        if key in unique and any(
            row[field] != unique[key][field] for field in ("path", "bytes", "sha256")
        ):
            raise IntegrityError("METADATA_CONFLICTING_GRAPH_BINDING")
        unique[key] = row
    return {
        "schema_version": "mp2-cost-reference-metadata-roster/1.0",
        "state": "METADATA_BINDINGS_PASS_NON_AUTHORIZING",
        "baseline_commit": BASELINE,
        "bindings": list(unique.values()),
        "payload_inventory_replayed": False,
        **boundary.report(),
    }
