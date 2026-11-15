"""Additive byte/predicate verification; never a workload or scientific authority."""

from __future__ import annotations

import io
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

from ai_service_v2.errors import IntegrityError
from ai_service_v2.hashing import (
    canonical_json_bytes,
    canonical_json_sha256,
    sha256_bytes,
    sha256_file,
)
from ai_service_v2.training.cost_reference_metadata_01 import (
    MetadataBoundary,
    canonical_document,
    relative_path,
    validate_inventory,
)
from ai_service_v2.training.cost_runtime_custody import read_canonical_json, reject_reparse_path

BASELINE = "cfe2f2f84060679d2cd6a45036634eefb651ca8d"
LOCAL = "research/hybrid-recsys-v5/06_venue_readiness/07_local_v5_validation"
CONTROL = LOCAL + "/00_control/cost_optimization_01"
ROUTE = CONTROL + "/optimization_closure_03"
AUTHORITY_HASHES = {
    "deep": "c15b97a4272a832ca6f5391992d4116371c9b20b33bca49bc2e285225ce4f64c",
    "components": "35a07fa56dd589b493a6726e70a7f37e97248648905ee1b1af45d6c34fad503b",
}
SOURCE_ADDITIONS = (
    "ai-service-v2/tools/run_cost_optimization_closure_03.py",
    "ai-service-v2/src/ai_service_v2/training/cost_optimization_closure_03.py",
    "ai-service-v2/tests/test_cost_closure_03_route.py",
    "ai-service-v2/tests/cost_closure_03_public_subprocess_fixture.py",
)
VERIFIER_SOURCES = (
    "ai-service-v2/src/ai_service_v2/training/cost_closure_postmeasurement_03.py",
    "ai-service-v2/tools/verify_cost_optimization_closure_03.py",
    "ai-service-v2/tests/test_cost_closure03_postmeasurement.py",
)
PREPARATION = {
    "accepted_result_rows": 0,
    "scientific_evidence_created": False,
    "validation_execution_authorized": False,
    "test_release_authorized": False,
    "c4_state": "BLOCKED",
    "test_access_state": "LOCKED_NOT_ACCESSED",
}

OVERHEADS = ("startup", "custody", "restore_segment", "cleanup")
LENGTHS = {
    "deep_candidate_epochs_ns": 4,
    "mostpop_ns": 1,
    "itemknn_ns": 3,
    "rule_ns": 3,
    "hybrid_ns": 12,
}


def equal(actual: Any, expected: Any, code: str) -> None:
    if canonical_json_bytes({"value": actual}) != canonical_json_bytes({"value": expected}):
        raise IntegrityError(code)


def safe_relative(value: Any) -> str:
    name = relative_path(value)
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    if any(
        part.endswith((".", " "))
        or part.split(".")[0].casefold() in reserved
        or any(ord(char) < 32 for char in part)
        for part in name.split("/")
    ):
        raise IntegrityError("POSTMEASUREMENT_PATH_ALIAS")
    return name


def validate_control_links(
    stage: str, authority_bytes: bytes, inventory_bytes: bytes, outcome_bytes: bytes
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if stage not in AUTHORITY_HASHES:
        raise IntegrityError("POSTMEASUREMENT_STAGE")
    authority = canonical_document(authority_bytes)
    inventory = canonical_document(inventory_bytes)
    outcome = canonical_document(outcome_bytes)
    equal(
        authority["schema_version"],
        "mp2-cost-optimization-closure-03-authority/1.0",
        "POSTMEASUREMENT_AUTHORITY_SCHEMA",
    )
    equal(authority["stage"], stage, "POSTMEASUREMENT_STAGE")
    if set(inventory) != {"schema_version", "stage", "artifacts"} or set(outcome) != {
        "schema_version",
        "stage",
        "state",
        "allocation_consumed_seconds",
        "authority_sha256",
        "inventory_sha256",
        "public_replay",
    }:
        raise IntegrityError("POSTMEASUREMENT_CONTROL_SCHEMA")
    equal(
        inventory["schema_version"],
        "mp2-cost-closure03-inventory/1.0",
        "POSTMEASUREMENT_INVENTORY_SCHEMA",
    )
    equal(
        outcome["schema_version"],
        "mp2-cost-closure03-outcome/1.0",
        "POSTMEASUREMENT_OUTCOME_SCHEMA",
    )
    equal([inventory["stage"], outcome["stage"]], [stage, stage], "POSTMEASUREMENT_STAGE")
    equal(outcome["state"], "ENGINEERING_PASS_NON_AUTHORIZING", "POSTMEASUREMENT_OUTCOME")
    equal(
        outcome["allocation_consumed_seconds"],
        8400 if stage == "deep" else 2400,
        "POSTMEASUREMENT_ALLOCATION",
    )
    equal(
        outcome["authority_sha256"], sha256_bytes(authority_bytes), "POSTMEASUREMENT_CONTROL_LINK"
    )
    equal(
        outcome["inventory_sha256"], sha256_bytes(inventory_bytes), "POSTMEASUREMENT_CONTROL_LINK"
    )
    rows = validate_inventory(inventory["artifacts"])
    for row in rows.values():
        safe_relative(row["path"])
    return authority, rows


def git_bytes(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=input_bytes,
        capture_output=True,
        check=True,
        timeout=60,
    ).stdout


def frozen_blobs(repository: Path, commit: str, paths: list[str]) -> dict[str, bytes]:
    for name in paths:
        safe_relative(name)
    requests = "".join(f"{commit}:{name}\n" for name in paths).encode()
    stream = io.BytesIO(git_bytes(repository, "cat-file", "--batch", input_bytes=requests))
    blobs = {}
    for name in paths:
        header = stream.readline().decode("ascii").split()
        if len(header) != 3 or header[1] != "blob" or not header[2].isdigit():
            raise IntegrityError("POSTMEASUREMENT_GIT_BLOB_MISSING")
        data = stream.read(int(header[2]))
        if len(data) != int(header[2]) or stream.read(1) != b"\n":
            raise IntegrityError("POSTMEASUREMENT_GIT_BLOB_TRUNCATED")
        blobs[name] = data
    if stream.read():
        raise IntegrityError("POSTMEASUREMENT_GIT_EXTRA_BLOB")
    return blobs


def verify_metadata(repository: Path, cache: Path) -> dict[str, Any]:
    """Authenticate fixed control/source bytes before any current-stage payload read."""
    control_names = [
        f"{ROUTE}/{stage}/{name}"
        for stage in AUTHORITY_HASHES
        for name in (
            "authority.json",
            "inventory.json",
            "outcome.json",
            "budget.json",
            "metadata_roster.json",
            "authority_only_gate.json",
        )
    ]
    control_names += [
        f"{CONTROL}/optimization_closure_02/{name}"
        for name in ("authority.json", "inventory.json", "outcome.json")
    ]
    control_names += [
        f"{CONTROL}/reference_epoch_01/{name}"
        for name in ("outcome.json", "inventory.json", "partial_forecast_metadata_only_01.json")
    ]
    control_names += [f"{CONTROL}/profile_reference_03_wddm_policy.json"]
    frozen_controls = frozen_blobs(repository, BASELINE, control_names)
    historical_sources = (
        git_bytes(
            repository,
            "ls-tree",
            "-r",
            "--name-only",
            "8972c0d6bc0479834e2852a9fbada58fef84123a",
            "ai-service-v2/src",
            "ai-service-v2/tools",
            "ai-service-v2/tests",
        )
        .decode()
        .splitlines()
    )
    source_names = sorted(
        {p for p in historical_sources if p.endswith(".py")} | set(SOURCE_ADDITIONS)
    )
    allowed = {repository / name: "CONTROL_BYTES_ONLY" for name in control_names}
    allowed.update({repository / name: "GIT_DECLARED_SOURCE" for name in source_names})
    boundary = MetadataBoundary(allowed, (repository, cache))
    stages = {}
    with boundary.enforce():
        documents = {}
        for name in control_names:
            data = (repository / name).read_bytes()
            equal(
                sha256_bytes(data),
                sha256_bytes(frozen_controls[name]),
                "POSTMEASUREMENT_FROZEN_CONTROL_DRIFT",
            )
            documents[name] = canonical_document(data)
        for stage, expected_hash in AUTHORITY_HASHES.items():
            prefix = f"{ROUTE}/{stage}"
            authority_data = frozen_controls[f"{prefix}/authority.json"]
            equal(sha256_bytes(authority_data), expected_hash, "POSTMEASUREMENT_AUTHORITY_HASH")
            authority, inventory = validate_control_links(
                stage,
                authority_data,
                frozen_controls[f"{prefix}/inventory.json"],
                frozen_controls[f"{prefix}/outcome.json"],
            )
            equal(authority["fixture"], False, "POSTMEASUREMENT_FIXTURE_AUTHORITY")
            equal(
                authority["namespace"],
                str(cache / f"cost-opt-01-optimization-closure-03-{stage}"),
                "POSTMEASUREMENT_NAMESPACE",
            )
            for key in ("scientific_evidence_created", "test_access_state"):
                equal(authority[key], PREPARATION[key], "POSTMEASUREMENT_AUTHORITY_SCOPE")
            rows = authority["source_bindings"]
            equal(
                [row["path"] for row in rows], source_names, "POSTMEASUREMENT_FROZEN_SOURCE_ROSTER"
            )
            blobs = frozen_blobs(repository, authority["source_commit"], source_names)
            for row in rows:
                data = blobs[row["path"]]
                equal(
                    {"bytes": len(data), "sha256": sha256_bytes(data)},
                    {"bytes": row["bytes"], "sha256": row["sha256"]},
                    "POSTMEASUREMENT_FROZEN_BLOB_DRIFT",
                )
                # The admitted delta permits test-only remediation, never measured code changes.
                if not row["path"].startswith("ai-service-v2/tests/"):
                    equal(
                        sha256_bytes((repository / row["path"]).read_bytes()),
                        sha256_bytes(data),
                        "POSTMEASUREMENT_CURRENT_SOURCE_DRIFT",
                    )
            stages[stage] = {
                "authority": authority,
                "inventory": inventory,
                "authority_sha256": expected_hash,
                "outcome": documents[f"{prefix}/outcome.json"],
            }
        reference = documents[
            f"{CONTROL}/reference_epoch_01/partial_forecast_metadata_only_01.json"
        ]
        equal(
            [reference["base_subtotal_seconds"], reference["maximum_subtotal_seconds"]],
            [12583, 15101],
            "POSTMEASUREMENT_REFERENCE_SUBTOTAL",
        )
        reference_outcome = documents[f"{CONTROL}/reference_epoch_01/outcome.json"]
        reference_inventory = frozen_controls[f"{CONTROL}/reference_epoch_01/inventory.json"]
        equal(
            reference_outcome["inventory_sha256"],
            sha256_bytes(reference_inventory),
            "POSTMEASUREMENT_REFERENCE_LINK",
        )
        predecessor = documents[f"{CONTROL}/optimization_closure_02/outcome.json"]
        equal(
            predecessor["inventory_sha256"],
            sha256_bytes(frozen_controls[f"{CONTROL}/optimization_closure_02/inventory.json"]),
            "POSTMEASUREMENT_PREDECESSOR_LINK",
        )
    return {
        "stages": stages,
        "source_names": source_names,
        "policy": documents[f"{CONTROL}/profile_reference_03_wddm_policy.json"],
        "reference": reference,
        "predecessor": predecessor,
        "metadata_gate": {
            "state": "PASS_CONTROL_SOURCE_ONLY_NON_AUTHORIZING",
            "baseline_commit": BASELINE,
            "control_bindings": [
                {"path": name, "bytes": len(data), "sha256": sha256_bytes(data)}
                for name, data in frozen_controls.items()
            ],
            **boundary.report(),
        },
    }


def positive(value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise IntegrityError("POSTMEASUREMENT_NONCANONICAL_TIMER")
    return int(value)


def verify_inventory_bytes(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Only the already bound current-stage roster may authorize byte reads."""
    declared = validate_inventory(rows)
    names = [safe_relative(row["path"]) for row in declared.values()]
    actual = []
    reject_reparse_path(root)
    if not root.is_dir():
        raise IntegrityError("POSTMEASUREMENT_NAMESPACE_MISSING")
    for path in root.rglob("*"):
        reject_reparse_path(path)
        if path.is_file():
            actual.append(path.relative_to(root).as_posix())
    equal(sorted(actual), sorted(names), "POSTMEASUREMENT_INVENTORY_ROSTER")
    boundary = MetadataBoundary(
        {root / name: "CURRENT_STAGE_BOUND_BYTES" for name in names}, (root,)
    )
    with boundary.enforce():
        for row in rows:
            path = root / row["path"]
            equal(
                {"bytes": path.stat().st_size, "sha256": sha256_file(path)},
                {"bytes": row["bytes"], "sha256": row["sha256"]},
                "POSTMEASUREMENT_INVENTORY_BYTES",
            )
    return {
        **boundary.report(),
        "read_scope": "CURRENT_STAGE_BOUND_BYTES_ONLY",
        "payload_bytes_certified": True,
        "artifact_count": len(rows),
    }


def validate_handshake(
    expected: dict[str, Any], response: dict[str, Any], release: dict[str, Any], response_hash: str
) -> None:
    equal(
        response,
        {"identity": expected, "identity_sha256": canonical_json_sha256(expected)},
        "POSTMEASUREMENT_WORKER_IDENTITY",
    )
    equal(
        release,
        {"identity_sha256": canonical_json_sha256(expected), "response_sha256": response_hash},
        "POSTMEASUREMENT_WORKER_RELEASE",
    )


def reject_live_workload() -> None:
    import psutil  # type: ignore[import-untyped]

    for process in psutil.process_iter(["pid", "cmdline"]):
        if process.info["pid"] == os.getpid():
            continue
        command = process.info["cmdline"] or []
        if any("run_cost_" in str(arg).casefold() for arg in command) and any(
            arg in {"--worker", "--supervisor"} for arg in command
        ):
            raise IntegrityError("POSTMEASUREMENT_OWNED_OR_FOREIGN_WORKLOAD")


def require_process_exited(identity: dict[str, Any]) -> None:
    import psutil

    from ai_service_v2.training.cost_profile_process_03 import validate_identity

    validate_identity(identity)
    try:
        current = psutil.Process(identity["pid"])
        creation = int(current.create_time() * 10_000_000)
    except psutil.NoSuchProcess:
        return
    except psutil.AccessDenied as error:
        raise IntegrityError("POSTMEASUREMENT_PROCESS_OWNERSHIP_UNRESOLVED") from error
    if creation == identity["creation_time_100ns"]:
        raise IntegrityError("POSTMEASUREMENT_OWNED_PROCESS_ALIVE")


def verify_stage_predicates(
    root: Path, stage: str, bound: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    from ai_service_v2.training.cost_evaluator_engineering_03 import replay_cuda
    from ai_service_v2.training.cost_profile_process_03 import replay_admission
    from ai_service_v2.training.cost_profile_wddm import validate_window
    from ai_service_v2.training.cost_runtime_custody import EngineeringJournal

    authority, authority_hash = bound["authority"], bound["authority_sha256"]
    guard = read_canonical_json(root / "invocation_guard.json")
    completion = read_canonical_json(root / "completion.json")
    guard_hash = sha256_file(root / "invocation_guard.json")
    if set(guard) != {
        "schema_version",
        "stage",
        "authority_sha256",
        "namespace",
        "command",
        "execution_head",
        "invocation_id",
        "automatic_retry",
        "claim_monotonic_ns",
    }:
        raise IntegrityError("POSTMEASUREMENT_GUARD_SCHEMA")
    equal(
        guard["schema_version"],
        "mp2-cost-closure03-invocation-guard/1.0",
        "POSTMEASUREMENT_GUARD_SCHEMA",
    )
    for key, value in {
        "stage": stage,
        "authority_sha256": authority_hash,
        "namespace": str(root),
        "command": authority["command"],
        "automatic_retry": False,
    }.items():
        equal(guard[key], value, "POSTMEASUREMENT_GUARD_BINDING")
    equal(str(uuid.UUID(guard["invocation_id"])), guard["invocation_id"], "POSTMEASUREMENT_TOKEN")
    positive(guard["claim_monotonic_ns"])
    expected_head = (
        "dc293a21393214ba68518ad999d7f979d2caf499"
        if stage == "deep"
        else "d1639b427fd45c85976dc8a0b85e8bf4e5eb3517"
    )
    equal(guard["execution_head"], expected_head, "POSTMEASUREMENT_EXECUTION_HEAD")
    if set(completion) != {
        "schema_version",
        "stage",
        "state",
        "authority_sha256",
        "guard_sha256",
        "execution_head",
        "elapsed_ns",
        "custody_ns",
        "measurement_sha256",
        "inventory",
    }:
        raise IntegrityError("POSTMEASUREMENT_COMPLETION_SCHEMA")
    for key, value in {
        "schema_version": "mp2-cost-closure03-completion/1.0",
        "stage": stage,
        "state": "COMPLETE_NON_AUTHORIZING",
        "authority_sha256": authority_hash,
        "guard_sha256": guard_hash,
        "execution_head": expected_head,
        "measurement_sha256": sha256_file(root / "measurement.json"),
    }.items():
        equal(completion[key], value, "POSTMEASUREMENT_COMPLETION_LINK")
    if positive(completion["elapsed_ns"]) >= authority["cap_ns"]:
        raise IntegrityError("POSTMEASUREMENT_DEADLINE")
    positive(completion["custody_ns"])
    equal(
        completion["inventory"],
        [row for row in bound["inventory"].values() if row["path"] != "completion.json"],
        "POSTMEASUREMENT_COMPLETION_INVENTORY",
    )
    if any(
        "failure" in row["path"].casefold() or "hard_timeout" in row["path"].casefold()
        for row in bound["inventory"].values()
    ):
        raise IntegrityError("POSTMEASUREMENT_FAILURE_COEXISTS")

    # Construct no journal: its normal constructor can create/repair the evidence root.
    class ReadOnlyJournal(EngineeringJournal):
        def __init__(self) -> None:
            self.root = root / "journal"
            self.binding_sha256 = authority_hash
            self.authorization_state = "NON_AUTHORIZING"

    journal = ReadOnlyJournal()
    equal(
        journal.replay("optimization-closure-03-" + stage)["state"],
        "COMPLETE_NON_AUTHORIZING",
        "POSTMEASUREMENT_JOURNAL",
    )
    admission = read_canonical_json(root / "launcher_admission.json")
    if set(admission) != {"authority_sha256", "window"}:
        raise IntegrityError("POSTMEASUREMENT_ADMISSION_FIELDS")
    equal(admission["authority_sha256"], authority_hash, "POSTMEASUREMENT_ADMISSION_AUTHORITY")
    validate_window(admission["window"], policy, now_ns=guard["claim_monotonic_ns"])
    supervisor = replay_admission(
        root, "supervisor", authority_hash, guard_hash, authority["supervisor_command"]
    )
    require_process_exited(supervisor["runtime_identity"])
    require_process_exited(
        read_canonical_json(root / "children/supervisor/spawned_identity.json")["spawned"]
    )
    phases = ("deep-initial", "deep-resume") if stage == "deep" else ("components",)
    for phase in phases:
        identity_root, worker_root = root / phase, root / "workers" / phase
        descriptor = read_canonical_json(identity_root / "children/worker/spawned_identity.json")
        equal(
            descriptor["parent"],
            supervisor["runtime_identity"],
            "POSTMEASUREMENT_FOREIGN_WORKER_PARENT",
        )
        worker_admission = replay_admission(
            identity_root, "worker", authority_hash, guard_hash, authority["worker_commands"][phase]
        )
        require_process_exited(descriptor["spawned"])
        require_process_exited(worker_admission["runtime_identity"])
        expected = {
            "schema_version": "mp2-cost-closure03-worker-identity/1.0",
            "stage": stage,
            "role": "worker",
            "phase": phase,
            "authority_sha256": authority_hash,
            "source_commit": authority["source_commit"],
            "namespace": os.path.normcase(os.path.abspath(root)),
            "invocation_id": guard["invocation_id"],
            "guard_sha256": guard_hash,
            "command_sha256": canonical_json_sha256(
                {"command": authority["worker_commands"][phase]}
            ),
        }
        equal(
            read_canonical_json(identity_root / "expected_identity.json"),
            expected,
            "POSTMEASUREMENT_PARENT_EXPECTED_IDENTITY",
        )
        validate_handshake(
            expected,
            read_canonical_json(identity_root / "identity_response.json"),
            read_canonical_json(identity_root / "identity_release.json"),
            sha256_file(identity_root / "identity_response.json"),
        )
        window = read_canonical_json(identity_root / "worker_admission.json")
        if set(window) != {"authority_sha256", "guard_sha256", "window"}:
            raise IntegrityError("POSTMEASUREMENT_WORKER_ADMISSION_FIELDS")
        equal(
            [window["authority_sha256"], window["guard_sha256"]],
            [authority_hash, guard_hash],
            "POSTMEASUREMENT_WORKER_ADMISSION_BINDING",
        )
        validate_window(window["window"], policy)
        replay_cuda(worker_root, authority_hash, authority["gpu_uuid"])
        equal(
            read_canonical_json(worker_root / "authority_snapshot.json"),
            authority,
            "POSTMEASUREMENT_WORKER_AUTHORITY",
        )
        equal(
            read_canonical_json(worker_root / "invocation_guard.json"),
            guard,
            "POSTMEASUREMENT_WORKER_GUARD",
        )
    return {
        "state": "PASS_NON_AUTHORIZING",
        "stage": stage,
        "elapsed_ns": completion["elapsed_ns"],
        "custody_ns": completion["custody_ns"],
        "worker_phases": list(phases),
        "worker_terminal_custody_scope": "SUPERVISOR_COMPLETION_AFTER_FROZEN_RETURN_CODE_CHECK",
        "individual_child_outcome_receipts_present": False,
        "worker_recheck_freshness_scope": "WINDOW_INTERNAL_CHRONOLOGY_ONLY_NO_PERSISTED_NOW",
    }


def replay_scores_and_continuation(
    roots: dict[str, Path], stages: dict[str, Any]
) -> dict[str, Any]:
    from ai_service_v2.evaluation.artifacts import load_materialized_scores
    from ai_service_v2.protocol import load_protocol
    from ai_service_v2.training.cost_closure_validation_02 import validate_partition
    from ai_service_v2.training.cost_numerical_receipts_02 import validate_numerical_receipt
    from ai_service_v2.training.cost_optimization_closure_03 import (
        verify_continuation_metadata,
        verify_stage_measurement,
    )
    from ai_service_v2.training.cost_reference_runtime_01 import replay_pair

    deep = roots["deep"]
    initial = read_canonical_json(deep / "workers/deep-initial/measurement.json")
    resumed = read_canonical_json(deep / "workers/deep-resume/measurement.json")
    components = read_canonical_json(roots["components"] / "workers/components/measurement.json")
    numerical_root = deep / "workers/deep-initial/numerical"
    numerical = read_canonical_json(numerical_root / "receipt.json")
    validate_numerical_receipt(numerical_root, numerical, require_physical=True)
    equal(numerical["candidate_pass"], True, "POSTMEASUREMENT_NUMERICAL_DRIFT")
    for phase in ("deep-initial", "deep-resume"):
        gate = read_canonical_json(deep / "workers" / phase / "qualification_gate.json")
        equal(
            gate,
            {
                "authority_sha256": stages["deep"]["authority_sha256"],
                "guard_sha256": sha256_file(deep / "invocation_guard.json"),
                "receipt_sha256": sha256_file(numerical_root / "receipt.json"),
                "runtime_identity": "LEGACY_TRAINING_COST_EVALUATOR",
            },
            "POSTMEASUREMENT_QUALIFICATION_LINK",
        )
    equal(
        read_canonical_json(deep / "workers/deep-resume/continuation_gate.json"),
        verify_continuation_metadata(deep, stages["deep"]["authority"]),
        "POSTMEASUREMENT_CONTINUATION_COMPANION",
    )
    for stage, root in roots.items():
        equal(
            read_canonical_json(root / "measurement.json")["verification"],
            verify_stage_measurement(root, stage),
            "POSTMEASUREMENT_STAGE_MEASUREMENT",
        )

    protocols = {}
    for stage, phases in (
        ("deep", ("deep-initial", "deep-resume")),
        ("components", ("components",)),
    ):
        for phase in phases:
            worker = roots[stage] / "workers" / phase
            fingerprint = read_canonical_json(worker / "input_fingerprints.json")
            measurement = read_canonical_json(worker / "measurement.json")
            equal(
                measurement["input_fingerprints_sha256"]
                if stage == "deep"
                else sha256_file(worker / "input_fingerprints.json"),
                sha256_file(worker / "input_fingerprints.json"),
                "POSTMEASUREMENT_INPUT_LINK",
            )
            equal(
                [fingerprint["protocol_sha256"], fingerprint["protocol_bytes"]],
                [sha256_file(worker / "protocol.json"), (worker / "protocol.json").stat().st_size],
                "POSTMEASUREMENT_PROTOCOL_PAYLOAD",
            )
            equal(
                fingerprint["source_commit"],
                stages[stage]["authority"]["source_commit"],
                "POSTMEASUREMENT_INPUT_SOURCE",
            )
            equal(
                fingerprint["authority_sha256"],
                stages[stage]["authority_sha256"],
                "POSTMEASUREMENT_INPUT_AUTHORITY",
            )
            equal(
                fingerprint["guard_sha256"],
                sha256_file(roots[stage] / "invocation_guard.json"),
                "POSTMEASUREMENT_INPUT_GUARD",
            )
            protocols[stage] = load_protocol(worker / "protocol.json")
            if (
                protocols[stage].manifest.split != "val"
                or protocols[stage].manifest.test_set_opened
            ):
                raise IntegrityError("POSTMEASUREMENT_TEST_ACCESS")
    fingerprints = [
        read_canonical_json(roots[s] / "workers" / p / "input_fingerprints.json")
        for s, p in (
            ("deep", "deep-initial"),
            ("deep", "deep-resume"),
            ("components", "components"),
        )
    ]
    for key in (
        "protocol_sha256",
        "protocol_bytes",
        "id_map_sha256",
        "configuration_sha256",
        "runtime_sha256",
        "dtype",
        "history_policy",
    ):
        equal(
            [f[key] for f in fingerprints],
            [fingerprints[0][key]] * 3,
            "POSTMEASUREMENT_INPUT_CONTINUATION",
        )
    cases: list[tuple[str, Path, dict[str, Any]]] = []
    segments = initial["deep_segments"] + resumed["deep_segments"]
    equal(
        segments[0]["epochs"][0]["semantic"],
        segments[1]["epochs"][0]["semantic"],
        "POSTMEASUREMENT_LEGACY_CANDIDATE_PARITY",
    )
    for segment in segments:
        for row in segment["epochs"]:
            case = deep / "workloads/deep" / segment["segment"] / f"epoch-{row['epoch']}"
            equal(row, read_canonical_json(case / "measurement.json"), "POSTMEASUREMENT_EPOCH_LINK")
            manifest = read_canonical_json(case / "checkpoint/manifest.json")
            equal(
                row["checkpoint_manifest_sha256"],
                sha256_file(case / "checkpoint/manifest.json"),
                "POSTMEASUREMENT_CHECKPOINT_MANIFEST",
            )
            equal(
                manifest["payload_sha256"],
                sha256_file(case / "checkpoint/checkpoint.pt"),
                "POSTMEASUREMENT_CHECKPOINT_BYTES",
            )
            equal(
                manifest["authorities"],
                segment["authority_bindings"],
                "POSTMEASUREMENT_CHECKPOINT_AUTHORITIES",
            )
            equal(manifest["completed_epoch"], row["epoch"], "POSTMEASUREMENT_CHECKPOINT_CURSOR")
            cases.append(("deep", case, row))
    c = roots["components"] / "workloads"
    component_cases = [(c / "mostpop", components["mostpop"])]
    component_cases += [
        (c / f"itemknn-c{i}", row) for i, row in zip((1, 3, 5), components["itemknn"], strict=True)
    ]
    component_cases += [(c / f"rule-c{i}", row) for i, row in enumerate(components["rule"], 1)]
    component_cases += [
        (c / f"hybrid-rule-{i}-lambda-{weight}", row)
        for (i, weight), row in zip(
            [(i, w) for i in (1, 2, 3) for w in (0.25, 0.5, 1.0, 2.0)],
            components["hybrid"],
            strict=True,
        )
    ]
    equal(len(component_cases), 19, "POSTMEASUREMENT_COMPONENT_ROSTER")
    for case, row in component_cases:
        validate_partition(row, deep=False)
        name = "itemknn.json" if row["method_id"] == "ItemKNN" else "measurement.json"
        equal(row, read_canonical_json(case / name), "POSTMEASUREMENT_COMPONENT_LINK")
        if row["method_id"] == "ItemKNN":
            checkpoint = read_canonical_json(case / "checkpoint/manifest.json")
            equal(
                row["checkpoint_manifest_sha256"],
                sha256_file(case / "checkpoint/manifest.json"),
                "POSTMEASUREMENT_ITEMKNN_CHECKPOINT_MANIFEST",
            )
            equal(
                checkpoint["checkpoint_sha256"],
                sha256_file(case / "checkpoint/checkpoint.pt"),
                "POSTMEASUREMENT_ITEMKNN_CHECKPOINT_BYTES",
            )
            equal(
                [
                    checkpoint["method_id"],
                    checkpoint["epoch"],
                    checkpoint["seed"],
                    checkpoint["model_device_identity"]["canonical"],
                    checkpoint["optimizer_state_sha256"],
                    row["fit_count"],
                    row["trainer_created"],
                    row["optimizer_created"],
                ],
                ["ItemKNN", None, 42, "cpu", None, 1, False, False],
                "POSTMEASUREMENT_ITEMKNN_FIT_DEVICE",
            )
        equal(
            [
                row["seed"],
                row["score_exports"],
                row["training_epochs"],
                row["score_dtype"],
                row["chunk_size"],
                row["legacy_parity"],
            ],
            [42, 1, 0, "float32", 128, "EXACT"],
            "POSTMEASUREMENT_COMPONENT_SEMANTICS",
        )
        cases.append(("components", case, row))
    for stage, case, row in cases:
        equal(
            row["score_manifest_sha256"],
            sha256_file(case / "scores/manifest.json"),
            "POSTMEASUREMENT_SCORE_MANIFEST",
        )
        artifact = load_materialized_scores(case / "scores")
        equal(artifact.manifest.score_dtype, "float32", "POSTMEASUREMENT_SCORE_DTYPE")
        equal(
            row["semantic"]["score_chunks_sha256"]
            if stage == "deep"
            else row["score_chunks_sha256"],
            canonical_json_sha256({"chunks": [chunk.to_mapping() for chunk in artifact.chunks]}),
            "POSTMEASUREMENT_SCORE_CHUNKS",
        )
        if any(chunk.user_count > 128 for chunk in artifact.chunks):
            raise IntegrityError("POSTMEASUREMENT_SCORE_CHUNK")
        replay_pair(protocols[stage], artifact, case / "cost", case / "legacy")
    predecessor = stages["components"]["authority"]
    equal(predecessor["deep_namespace"], str(deep), "POSTMEASUREMENT_DEEP_NAMESPACE")
    outcome_bytes = canonical_json_bytes(stages["deep"]["outcome"]) + b"\n"
    equal(
        predecessor["deep_predecessor_outcome"],
        {
            "path": str(
                Path(stages["deep"]["authority"]["budget_binding"]["path"]).parent / "outcome.json"
            ),
            "bytes": len(outcome_bytes),
            "sha256": sha256_bytes(outcome_bytes),
        },
        "POSTMEASUREMENT_STAGE_PREDECESSOR",
    )
    for row in predecessor["deep_predecessor_bindings"]:
        path = deep / safe_relative(row["path"])
        equal(
            {"bytes": path.stat().st_size, "sha256": sha256_file(path)},
            {"bytes": row["bytes"], "sha256": row["sha256"]},
            "POSTMEASUREMENT_STAGE_PREDECESSOR_BYTES",
        )
    return {
        "training_epochs": 5,
        "score_exports": len(cases),
        "parity_artifacts": len(cases),
        "numerical_predicates": sum(len(rows) for rows in numerical["comparisons"].values()),
        "continuation": "EXACT_PERSISTED_SEMANTICS_CHECKPOINT_BYTES_NOT_RESTORED",
    }


def verify_postmeasurement(repository: Path, cache: Path) -> dict[str, Any]:
    metadata = verify_metadata(repository, cache)
    roots = {
        stage: cache / f"cost-opt-01-optimization-closure-03-{stage}" for stage in AUTHORITY_HASHES
    }
    allowed = {
        repository / name: "GIT_DECLARED_SOURCE"
        for name in (*metadata["source_names"], *VERIFIER_SOURCES)
    }
    byte_reports = {}
    for stage, root in roots.items():
        rows = list(metadata["stages"][stage]["inventory"].values())
        byte_reports[stage] = verify_inventory_bytes(root, rows)
        allowed.update({root / row["path"]: "CURRENT_STAGE_BOUND_BYTES" for row in rows})
    boundary = MetadataBoundary(allowed, (repository, cache))
    with boundary.enforce():
        import torch

        if torch.cuda.is_initialized():  # type: ignore[no-untyped-call]
            raise IntegrityError("POSTMEASUREMENT_CUDA_NOT_COLD")
        reject_live_workload()
        from ai_service_v2.training.cuda_telemetry_smoke import SmokePaths, SmokeRuntime

        interpreter = Path(metadata["stages"]["deep"]["authority"]["command"][0])
        runtime = SmokeRuntime(
            SmokePaths(repository=repository, interpreter=interpreter)
        ).runtime_bindings()
        for bound in metadata["stages"].values():
            equal(
                runtime, bound["authority"]["dependency_runtime"], "POSTMEASUREMENT_RUNTIME_DRIFT"
            )
        predicates = {
            stage: verify_stage_predicates(
                root, stage, metadata["stages"][stage], metadata["policy"]
            )
            for stage, root in roots.items()
        }
        scores = replay_scores_and_continuation(roots, metadata["stages"])
        reject_live_workload()
        if torch.cuda.is_initialized():  # type: ignore[no-untyped-call]
            raise IntegrityError("POSTMEASUREMENT_CUDA_NOT_COLD")
    return {
        "schema_version": "mp2-cost-closure03-postmeasurement-verification/1.0",
        "state": "VERIFIED_BYTES_PREDICATES_NON_AUTHORIZING",
        **PREPARATION,
        "metadata_gate": metadata["metadata_gate"],
        "byte_verification": byte_reports,
        "stage_predicates": predicates,
        "scores": scores,
        "dependency_runtime": runtime,
        "cuda_context_before_after": [False, False],
        "owned_workload_remaining": False,
        "predicate_ledger": {
            **boundary.report(),
            "read_scope": "CLOSURE03_BOUND_BYTES_PREDICATES",
            "payload_bytes_certified": True,
        },
        "predecessor_classification": "CAPACITY_BOUNDARY_TIMEOUT_CONTROL_BYTES_ONLY",
        "historical_numerical_root_cause": "UNRESOLVED",
    }


def project_seconds(nanoseconds: Any) -> int:
    return (5 * positive(nanoseconds) + 3_999_999_999) // 4_000_000_000


def forecast_from_bound_measurements(repository: Path, cache: Path) -> dict[str, Any]:
    metadata = verify_metadata(repository, cache)
    roots = {
        stage: cache / f"cost-opt-01-optimization-closure-03-{stage}" for stage in AUTHORITY_HASHES
    }
    allowed = {}
    byte_reports = {}
    for stage, root in roots.items():
        rows = list(metadata["stages"][stage]["inventory"].values())
        byte_reports[stage] = verify_inventory_bytes(root, rows)
        allowed.update({root / row["path"]: "CURRENT_STAGE_BOUND_MEASUREMENT" for row in rows})
    boundary = MetadataBoundary(allowed, (repository, cache))
    with boundary.enforce():
        initial = read_canonical_json(roots["deep"] / "workers/deep-initial/measurement.json")
        resume = read_canonical_json(roots["deep"] / "workers/deep-resume/measurement.json")
        component = read_canonical_json(roots["components"] / "workers/components/measurement.json")
        segments = initial["deep_segments"][1:] + resume["deep_segments"]
        if (
            resume["copy_ns"] is not None
            or initial["copy_ns"] is None
            or component["copy_ns"] is None
        ):
            raise IntegrityError("POSTMEASUREMENT_COPY_EXECUTION_SCOPE")
        common = [
            positive(worker["cuda_setup_ns"])
            + positive(worker["input_ns"])
            + (positive(worker["copy_ns"]) if worker["copy_ns"] is not None else 0)
            for worker in (initial, resume, component)
        ]
        common[2] += positive(component["rule_table_load_ns"])
        measurements = {
            "deep_candidate_epochs_ns": [
                row["candidate_epoch_ns"] for segment in segments for row in segment["epochs"]
            ],
            "deep_setup_ns": max(positive(segment["setup_ns"]) for segment in segments),
            "deep_finalization_ns": max(
                positive(segment["finalization_ns"]) for segment in segments
            ),
            "common_input_ns": max(common),
            "mostpop_ns": [component["mostpop"]["candidate_surface_ns"]],
            "itemknn_ns": [row["candidate_surface_ns"] for row in component["itemknn"]],
            "rule_ns": [row["candidate_surface_ns"] for row in component["rule"]],
            "hybrid_ns": [row["candidate_surface_ns"] for row in component["hybrid"]],
        }
        result = project_forecast(
            measurements, reference_base_seconds=12583, reference_maximum_seconds=15101
        )
    return {
        **result,
        "observation_authority": "SEALED_CLOSURE03_BYTES_SUBTOTAL_ONLY",
        "measurements": measurements,
        "stage_authority_sha256": AUTHORITY_HASHES,
        "metadata_gate": metadata["metadata_gate"],
        "measurement_ledger": {**boundary.report(), "read_scope": "CLOSURE03_BOUND_MEASUREMENTS"},
        "measurement_byte_reports": byte_reports,
        "blockers": [
            {
                "component": name,
                "reason": "NO_AUTHENTICATED_EXCLUSIVE_INTERVAL_AND_DAG_COUNT_COVERAGE",
            }
            for name in OVERHEADS
        ],
        "compute_accounting_ceiling_is_not_invocation_or_eta": True,
    }


def require_freeze_ready(verification: dict[str, Any], forecast: dict[str, Any]) -> None:
    if verification.get("state") != "VERIFIED_BYTES_PREDICATES_NON_AUTHORIZING":
        raise IntegrityError("POSTMEASUREMENT_VERIFICATION_REQUIRED")
    if verification.get("owned_workload_remaining") is not False:
        raise IntegrityError("POSTMEASUREMENT_OWNED_WORKLOAD")
    if forecast.get("remaining_gaps") or forecast.get("full_envelope_seconds") is None:
        raise IntegrityError("POSTMEASUREMENT_COVERAGE_DELTA_REQUIRED")
    if (
        forecast.get("observation_authority") != "COMPLETE_AUTHENTICATED_MEASUREMENT_COVERAGE"
        or positive(forecast["full_envelope_seconds"]) > 259200
    ):
        raise IntegrityError("POSTMEASUREMENT_BUDGET_INFEASIBLE_OR_UNAUTHENTICATED")


def project_forecast(
    measurements: dict[str, Any],
    *,
    reference_base_seconds: int,
    reference_maximum_seconds: int,
    overhead_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project bound observations; raw inputs alone cannot qualify a freeze."""
    base, maximum = positive(reference_base_seconds), positive(reference_maximum_seconds)
    if maximum < base or set(measurements) != set(LENGTHS) | {
        "deep_setup_ns",
        "deep_finalization_ns",
        "common_input_ns",
    }:
        raise IntegrityError("POSTMEASUREMENT_FORECAST_ROSTER")
    for name, count in LENGTHS.items():
        values = measurements[name]
        if not isinstance(values, list) or len(values) != count:
            raise IntegrityError("POSTMEASUREMENT_FORECAST_ROSTER")
        for value in values:
            positive(value)
    for name in ("deep_setup_ns", "deep_finalization_ns", "common_input_ns"):
        positive(measurements[name])
    common = measurements["common_input_ns"]
    epoch_seconds = project_seconds(max(measurements["deep_candidate_epochs_ns"]))
    deep_per_run = 16 * epoch_seconds + project_seconds(
        measurements["deep_setup_ns"] + measurements["deep_finalization_ns"] + common
    )
    components = {
        "Deep-only": 5 * deep_per_run,
        "MostPop": project_seconds(measurements["mostpop_ns"][0] + common),
        "ItemKNN": sum(project_seconds(value + common) for value in measurements["itemknn_ns"]),
        "Rule-only": sum(project_seconds(value + common) for value in measurements["rule_ns"]),
        "Hybrid": 14 * project_seconds(max(measurements["hybrid_ns"]) + common),
    }
    coverage = {} if overhead_coverage is None else overhead_coverage
    if not isinstance(coverage, dict) or set(coverage) - set(OVERHEADS):
        raise IntegrityError("POSTMEASUREMENT_OVERHEAD_ROSTER")
    for row in coverage.values():
        if not isinstance(row, dict) or set(row) != {"wall_ns", "count", "scope"}:
            raise IntegrityError("POSTMEASUREMENT_OVERHEAD_SCHEMA")
        if row["scope"] != "VERIFIED_EXCLUSIVE_INTERVAL":
            raise IntegrityError("POSTMEASUREMENT_OVERHEAD_UNQUALIFIED")
        positive(row["wall_ns"])
        positive(row["count"])
    gaps = [name for name in OVERHEADS if name not in coverage]
    overhead = sum(project_seconds(row["wall_ns"]) * row["count"] for row in coverage.values())
    validation_base = base + sum(components.values()) + overhead
    validation_maximum = maximum + sum(components.values()) + overhead
    envelope = (6 * (validation_maximum + 38100 + 10800) + 4) // 5 if not gaps else None
    return {
        "schema_version": "mp2-cost-closure03-forecast-72h/1.0",
        "state": "PARTIAL_FORECAST_NON_AUTHORIZING"
        if gaps
        else (
            "DISCLOSED_EXCEPTION_WITHIN_72H_NON_AUTHORIZING"
            if envelope is not None and envelope <= 259200
            else "BUDGET_INFEASIBLE_NON_AUTHORIZING"
        ),
        "observation_authority": "RAW_INPUTS_ONLY_REQUIRES_POSTMEASUREMENT_BINDINGS",
        "profiling_cap_seconds": 38100,
        "test_analysis_seconds": 10800,
        "maximum_envelope_seconds": 259200,
        "maximum_validation_seconds": 167100,
        "historical_validation_target_ceiling_seconds": [33900, 51900],
        "deep_projected_epoch_seconds": epoch_seconds,
        "deep_projected_per_run_seconds": deep_per_run,
        "reference_subtotal_seconds": [base, maximum],
        "training_run_range": [15, 17],
        "component_surface_counts": {"MostPop": 1, "ItemKNN": 3, "Rule-only": 3, "Hybrid": 14},
        "projected_component_seconds": components,
        "projected_validation_base_seconds": validation_base,
        "projected_validation_maximum_seconds": validation_maximum,
        "known_subtotal_excludes_remaining_gaps": bool(gaps),
        "overhead_coverage": coverage,
        "remaining_gaps": gaps,
        "full_envelope_seconds": envelope,
        "credits_seconds": {"cache": 0, "shared_setup": 0, "early_stopping": 0, "parallelism": 0},
        "legacy_audit_included": False,
        "qualification_included": False,
        "later_epoch_scaling": "UNPROVEN_POINT_ESTIMATE_SHARED_HOST",
        "scientific_evidence_created": False,
        "validation_execution_authorized": False,
        "test_access_state": "LOCKED_NOT_ACCESSED",
    }
