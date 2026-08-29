#!/usr/bin/env python3
"""Offline Revision 5 static validator; never imports or invokes an Attempt runner."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import e4_r6_pc2w_p1_attempt013_packet_lineage as packet_lineage
import e4_r6_pc2w_p1_attempt013_pre_runtime_authority as authority


PYTHON = Path(r"C:\Program Files\Python311\python.exe")
CONTROL = Path("research/hybrid-recsys-v5/03_benchmark/stage1e/00_control")
START = "3c7fede9dc0c1ba0925593e72ed515dccec84fcb"
R0 = "ce6377c351625ed7e029f2883520583ca97fc2b8"
R1 = "294422ca8557e4b55ae3863d853289e2232011b2"
CENTRAL_FAILURE = "0ebd1145171f9f1289adc7e2ff7a019a7aec9c2e"
PLAN = "2efdcd73bb7f7e2b298ee12cdb5b09171a865d69"
R2A = "1a9ca21c5c8b1b08fdec788fbbf23e88473c117f"
P1 = "d335cedbac6576c93251def1b02ef43d430bf7cb"
R2_REVISION4 = "d9b7c24065dc5def894d94dcb8eddafd4f89ac1f"
PRECOMMIT_PACKET_SENTINEL = "f" * 40

RUNTIME_HELPER = CONTROL / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
RUNTIME_CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility_contract.json"
RUNTIME_TEST = CONTROL / "test_e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility.py"
AUTHORITY_HELPER = CONTROL / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority.py"
AUTHORITY_CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt013_pre_runtime_authority_contract.json"
AUTHORITY_TEST = CONTROL / "test_e4_r6_pc2w_p1_attempt013_pre_runtime_gate.py"
LINEAGE_HELPER = CONTROL / "e4_r6_pc2w_p1_attempt013_packet_lineage.py"
LINEAGE_CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt013_packet_lineage_contract.json"
LINEAGE_TEST = CONTROL / "test_e4_r6_pc2w_p1_attempt013_packet_lineage.py"
CONTRACT = CONTROL / "e4_r6_pc2w_p1_attempt013_admission_observation_contract.json"
AUTHORIZATION = CONTROL / "e4_r6_pc2w_p1_attempt013_execution_authorization.json"
RUNNER = CONTROL / "execute_e4_r6_pc2w_p1_attempt013_admission_observation.py"
VALIDATOR = CONTROL / "validate_e4_r6_pc2w_p1_attempt013_static_packet.py"

FROZEN_R0_PATHS = (
    RUNTIME_CONTRACT,
    RUNTIME_TEST,
    AUTHORITY_CONTRACT,
    AUTHORITY_TEST,
)
R1_SUPPORT_PATHS = (RUNTIME_HELPER, AUTHORITY_HELPER)
R2A_SUPPORT_PATHS = (LINEAGE_HELPER, LINEAGE_CONTRACT, LINEAGE_TEST)
SUPPORT_PATHS = (*R1_SUPPORT_PATHS, *R2A_SUPPORT_PATHS)
SEALING_PATHS = (CONTRACT, AUTHORIZATION, RUNNER, VALIDATOR)
PACKET = (*FROZEN_R0_PATHS, *SUPPORT_PATHS, *SEALING_PATHS)
PACKET_ROSTER = tuple(path.as_posix() for path in PACKET)

R0_FILES = FROZEN_R0_PATHS
R1_FILES = (
    RUNTIME_HELPER,
    AUTHORITY_HELPER,
    CONTRACT,
    AUTHORIZATION,
    RUNNER,
    VALIDATOR,
)
R2A_FILES = R2A_SUPPORT_PATHS
P1_PLAN_FILE = CONTROL / "e4_r6_pc2w_p1_attempt013_revision2_precommit_status_remediation_plan.md"

OUTPUT = Path(
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ay/"
    "E4_R6PC2W_P1_attempt013_revision5_admission_observation"
)
CENTRAL_RECEIPT = CONTROL / (
    "rebaseline_v2_e4_r6_pc2w_p1_attempt013_revision5_"
    "central_static_validation_receipt.json"
)
AUDIT_RECEIPT = CONTROL / (
    "rebaseline_v2_e4_r6_pc2w_p1_attempt013_revision5_"
    "user_audit_waiver_receipt.json"
)
LINEAGE_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision2-"
    "packet-lineage-contract-1.0"
)
CONTRACT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision5-"
    "admission-observation-contract-1.0"
)
AUTHORIZATION_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision5-"
    "execution-authorization-1.0"
)
VALIDATOR_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision5-"
    "static-validation-result-1.0"
)
CENTRAL_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision5-"
    "central-static-validation-receipt-1.0"
)
CENTRAL_VERDICT = "PASS_PC2W_P1_ATTEMPT013_REVISION5_CENTRAL_STATIC_VALIDATION"
AUDIT_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-revision5-"
    "user-audit-waiver-receipt-1.0"
)
AUDIT_VERDICT = (
    "USER_OVERRIDE_PC2W_P1_ATTEMPT013_REVISION5_AUDIT_WAIVED_"
    "READY_FOR_EXACT_COMMAND"
)

ORIGIN_FACTS = {
    RUNTIME_CONTRACT: (
        R0, 4121,
        "ed7d4323e7287643e0372e11cc1a2e6f5b5af73f4ec20fc0d0758dd12e648784",
    ),
    RUNTIME_TEST: (
        R0, 11844,
        "36b0e95a7b87a98325da6debfb345cb5a1df96ec672e6f1f3bb35db6b79fc21b",
    ),
    AUTHORITY_CONTRACT: (
        R0, 4526,
        "1cb5d8130420ae543d9f63b4d4cd0b9d16c7571577a5ad506f0217b2ebd530f0",
    ),
    AUTHORITY_TEST: (
        R0, 7613,
        "9c372dcd8a4cb4f87dab444a55739966936a930f098999487fd86d6f65a8c437",
    ),
    RUNTIME_HELPER: (
        R1, 19773,
        "53474c597643fda346d72b251b5dd504a264621ad7daef48fc55663ee86b4614",
    ),
    AUTHORITY_HELPER: (
        R1, 9084,
        "abdaab61ffcf05e5d5fec8f7731f07804588d6dd06e69754e55b9f522e8eae9d",
    ),
    LINEAGE_HELPER: (
        R2A, 8142,
        "d7101a54bb7143df591fb6f32128bbf230c76a859cb21982ab179c0eb32afed5",
    ),
    LINEAGE_CONTRACT: (
        R2A, 2543,
        "520308aa361f100ecd9783ffb022e75f2895195d37f149e5bc34931ca7d6f8a0",
    ),
    LINEAGE_TEST: (
        R2A, 10118,
        "0d9fafa87cc586e92ba49b327b63dbe37208041d15e44fdf1552776cd781d58f",
    ),
}

ATTEMPT012_RECEIPTS = {
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/admission_observation.json"):
        (24292, "7295f026d57e497dfce68f768e4153b94e27436361c6e18ffe4818709ab72459"),
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/command_receipts.json"):
        (22369, "1b722165dfed8c8ba27832636fd7917f899786239d507e839cf9c7d1820d5098"),
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/execution_receipt.json"):
        (5189, "a35bcd4d70e0028a54eb6da3ace9a3da083dca15ae7100d8638e74a334c1973f"),
    Path("research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_au/E4_R6PC2W_P1_attempt012_admission_observation/handoff.json"):
        (1488, "1da3715ac0752fcc5e967791f4a0c8561b98128283088f87b1f0ed24c5fee6a4"),
}

CANDIDATE_SUITES = (
    (LINEAGE_TEST, 19, "attempt013_revision2_packet_lineage"),
    (RUNTIME_TEST, 15, "attempt013_runtime_identity_compatibility"),
    (AUTHORITY_TEST, 9, "attempt013_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt012_pre_runtime_gate.py", 12, "retained_attempt012_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py", 62, "retained_attempt011_pre_runtime_gate"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt010_command_interface.py", 10, "retained_attempt010_command_interface"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py", 9, "retained_attempt009_runtime_compatibility"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_probe_contract.py", 8, "retained_attempt008_probe_contract"),
    (CONTROL / "test_e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py", 9, "retained_attempt008_safe_envelopes"),
)
EXPECTED_RUNNER_REACHING = {
    RUNTIME_TEST,
    CONTROL / "test_e4_r6_pc2w_p1_attempt009_runtime_compatibility.py",
    CONTROL / "test_e4_r6_pc2w_p1_attempt008_probe_contract.py",
    CONTROL / "test_e4_r6_pc2w_p1_attempt008_safe_probe_envelopes.py",
}
EXPECTED_RUNNER_FREE = {
    LINEAGE_TEST,
    AUTHORITY_TEST,
    CONTROL / "test_e4_r6_pc2w_p1_attempt012_pre_runtime_gate.py",
    CONTROL / "test_e4_r6_pc2w_p1_attempt011_pre_runtime_gate.py",
    CONTROL / "test_e4_r6_pc2w_p1_attempt010_command_interface.py",
}
RUNNER_MODULE_PATTERN = re.compile(
    r"execute_e4_r6_pc2w_p1_attempt[0-9]+_admission_observation"
)
GIT_COMMAND_COUNT = 0


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    global GIT_COMMAND_COUNT
    GIT_COMMAND_COUNT += 1
    completed = subprocess.run(
        ["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, check=False,
    )
    require(completed.returncode == 0, "READ_ONLY_GIT_COMMAND_FAILED")
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8", errors="strict").strip()


def git_status_porcelain(repo: Path) -> str:
    raw = git(
        repo, "status", "--porcelain=v1", "--untracked-files=all", binary=True
    )
    assert isinstance(raw, bytes)
    return raw.decode("utf-8", errors="strict").rstrip("\r\n")


def git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    global GIT_COMMAND_COUNT
    GIT_COMMAND_COUNT += 1
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=False, check=False,
    )
    require(completed.returncode in {0, 1}, "READ_ONLY_GIT_ANCESTRY_FAILED")
    return completed.returncode == 0


def git_blob(repo: Path, revision: str, path: Path) -> bytes:
    raw = git(repo, "cat-file", "blob", f"{revision}:{path.as_posix()}", binary=True)
    assert isinstance(raw, bytes)
    return raw


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    folded: set[str] = set()
    for key, value in pairs:
        normalized = key.casefold()
        if key in result or normalized in folded:
            raise ValueError("duplicate JSON key")
        result[key] = value
        folded.add(normalized)
    return result


def strict_json(raw: bytes, path: Path) -> dict[str, Any]:
    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=strict_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON: {token}")
        ),
    )
    require(isinstance(value, dict), f"JSON_ROOT_NOT_OBJECT:{path.as_posix()}")
    return value


def normalized_checkout(path: Path) -> bytes:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    require(b"\r" not in raw, f"BARE_CR:{path.as_posix()}")
    return raw


def commit_row(repo: Path, revision: str) -> list[str]:
    return str(git(repo, "rev-list", "--parents", "-n", "1", revision)).split()


def commit_parent(repo: Path, revision: str) -> str:
    row = commit_row(repo, revision)
    require(len(row) == 2, f"COMMIT_NOT_SINGLE_PARENT:{revision}")
    return row[1].casefold()


def commit_delta(repo: Path, revision: str) -> list[str]:
    value = str(git(repo, "diff-tree", "--no-commit-id", "--name-status", "-r", revision))
    return value.splitlines() if value else []


def validate_commit_shape(repo: Path, precommit: bool) -> str:
    require(commit_parent(repo, R0) == START, "R0_PARENT_MISMATCH")
    require(
        sorted(commit_delta(repo, R0)) == sorted(f"A\t{path.as_posix()}" for path in R0_FILES),
        "R0_WRITE_SET_MISMATCH",
    )
    require(commit_parent(repo, R1) == R0, "R1_PARENT_MISMATCH")
    require(
        sorted(commit_delta(repo, R1)) == sorted(f"A\t{path.as_posix()}" for path in R1_FILES),
        "R1_WRITE_SET_MISMATCH",
    )
    require(commit_parent(repo, CENTRAL_FAILURE) == R1, "CENTRAL_FAILURE_PARENT_MISMATCH")
    require(commit_parent(repo, PLAN) == CENTRAL_FAILURE, "PLAN_PARENT_MISMATCH")
    require(commit_parent(repo, R2A) == PLAN, "R2A_PARENT_MISMATCH")
    require(
        sorted(commit_delta(repo, R2A)) == sorted(f"A\t{path.as_posix()}" for path in R2A_FILES),
        "R2A_WRITE_SET_MISMATCH",
    )
    require(commit_parent(repo, P1) == R2A, "P1_PARENT_MISMATCH")
    require(
        commit_delta(repo, P1) == [f"A\t{P1_PLAN_FILE.as_posix()}"],
        "P1_WRITE_SET_MISMATCH",
    )
    require(git_is_ancestor(repo, R1, R2A), "R1_NOT_ANCESTOR_OF_R2A")
    require(commit_parent(repo, R2_REVISION4) == P1, "REVISION4_PARENT_MISMATCH")
    require(
        sorted(commit_delta(repo, R2_REVISION4))
        == sorted(f"M\t{path.as_posix()}" for path in SEALING_PATHS),
        "REVISION4_WRITE_SET_MISMATCH",
    )
    head = str(git(repo, "rev-parse", "HEAD")).casefold()
    status = git_status_porcelain(repo)
    if precommit:
        require(head == R2_REVISION4, "PRECOMMIT_HEAD_NOT_REVISION4")
        expected = sorted(f" M {path.as_posix()}" for path in SEALING_PATHS)
        require(sorted(status.splitlines()) == expected, "PRECOMMIT_WRITE_SET_MISMATCH")
        return "WORKTREE_PRECOMMIT"
    require(commit_parent(repo, head) == R2_REVISION4, "REVISION5_PARENT_MISMATCH")
    require(
        sorted(commit_delta(repo, head)) == sorted(f"M\t{path.as_posix()}" for path in SEALING_PATHS),
        "REVISION5_WRITE_SET_MISMATCH",
    )
    require(status == "", "R2_WORKTREE_NOT_CLEAN")
    return head


def packet_bytes(repo: Path, revision: str, path: Path, precommit: bool) -> bytes:
    if precommit and path in SEALING_PATHS:
        return normalized_checkout(repo / path)
    lookup = R2_REVISION4 if precommit else revision
    return git_blob(repo, lookup, path)


def validate_packet(repo: Path, revision: str, precommit: bool) -> list[dict[str, Any]]:
    facts = []
    for path in PACKET:
        raw = packet_bytes(repo, revision, path, precommit)
        require(normalized_checkout(repo / path) == raw, f"PACKET_CHECKOUT_DRIFT:{path}")
        facts.append({
            "path": path.as_posix(),
            "git_blob_bytes": len(raw),
            "git_blob_sha256": sha256_bytes(raw),
            "source": "NORMALIZED_WORKTREE" if precommit and path in SEALING_PATHS else "RAW_GIT_BLOB",
        })
    require(len(facts) == 13, "PACKET_FACT_COUNT_MISMATCH")
    return facts


def origin_binding(
    repo: Path, revision: str, path: Path, precommit: bool
) -> packet_lineage.OriginBinding:
    origin_commit, expected_bytes, expected_sha256 = ORIGIN_FACTS[path]
    origin_raw = git_blob(repo, origin_commit, path)
    require(len(origin_raw) == expected_bytes, f"ORIGIN_BYTES_MISMATCH:{path}")
    require(sha256_bytes(origin_raw) == expected_sha256, f"ORIGIN_SHA_MISMATCH:{path}")
    final_raw = packet_bytes(repo, revision, path, precommit)
    return packet_lineage.OriginBinding(
        path=path.as_posix(), origin_commit=origin_commit,
        origin_raw_bytes=expected_bytes, origin_raw_sha256=expected_sha256,
        final_raw_bytes=len(final_raw), final_raw_sha256=sha256_bytes(final_raw),
    )


def parse_delta_rows(rows: list[str]) -> tuple[packet_lineage.DeltaEntry, ...]:
    parsed = []
    for row in rows:
        parts = row.split("\t")
        require(len(parts) == 2, "DELTA_ROW_NOT_EXACT_STATUS_PATH")
        parsed.append(packet_lineage.DeltaEntry(parts[0], parts[1]))
    return tuple(parsed)


def validate_lineage(
    repo: Path, revision: str, precommit: bool, packet_facts: list[dict[str, Any]]
) -> dict[str, Any]:
    frozen = tuple(origin_binding(repo, revision, path, precommit) for path in FROZEN_R0_PATHS)
    support = tuple(origin_binding(repo, revision, path, precommit) for path in SUPPORT_PATHS)
    expected_delta = tuple(
        packet_lineage.DeltaEntry("M", path.as_posix()) for path in SEALING_PATHS
    )
    if precommit:
        packet_commit = PRECOMMIT_PACKET_SENTINEL
        parents = (R2_REVISION4,)
        observed_delta = expected_delta
        ancestor = True
        ancestry_basis = "PRECOMMIT_EXACT_HEAD_AND_FOUR_MODIFICATION_SENTINEL"
    else:
        packet_commit = revision
        row = commit_row(repo, revision)
        parents = tuple(value.casefold() for value in row[1:])
        observed_delta = parse_delta_rows(commit_delta(repo, revision))
        ancestor = git_is_ancestor(repo, revision, str(git(repo, "rev-parse", "HEAD")))
        ancestry_basis = "READ_ONLY_GIT_MERGE_BASE_IS_ANCESTOR"
    spec = packet_lineage.PacketLineageSpec(
        aggregate_roster=PACKET_ROSTER,
        frozen_r0_bindings=frozen,
        support_bindings=support,
        sealing_parent=R2_REVISION4,
        expected_sealing_delta=expected_delta,
    )
    observation = packet_lineage.PacketLineageObservation(
        packet_commit=packet_commit,
        packet_parents=parents,
        observed_sealing_delta=observed_delta,
        final_packet_blobs=tuple(
            packet_lineage.PacketBlobFact(
                path=fact["path"], raw_bytes=fact["git_blob_bytes"],
                raw_sha256=fact["git_blob_sha256"],
            )
            for fact in packet_facts
        ),
        packet_is_ancestor_of_execution_head=ancestor,
    )
    evidence = packet_lineage.validate_packet_lineage(spec, observation)
    return {
        "public_seam": "e4_r6_pc2w_p1_attempt013_packet_lineage.validate_packet_lineage",
        "packet_commit": evidence.packet_commit,
        "sealing_parent": evidence.sealing_parent,
        "aggregate_roster_count": evidence.aggregate_roster_count,
        "frozen_r0_count": evidence.frozen_r0_count,
        "support_count": evidence.support_count,
        "sealing_delta_count": evidence.sealing_delta_count,
        "sealing_delta_statuses": ["M"],
        "ancestry_basis": ancestry_basis,
        "predicate_passed": evidence.predicate_passed,
    }


def validate_attempt012_receipts(repo: Path, revision: str, precommit: bool) -> list[dict[str, Any]]:
    lookup = R2_REVISION4 if precommit else revision
    facts = []
    for path, (expected_bytes, expected_sha256) in sorted(
        ATTEMPT012_RECEIPTS.items(), key=lambda item: item[0].as_posix()
    ):
        raw = git_blob(repo, lookup, path)
        require(len(raw) == expected_bytes, f"ATTEMPT012_RECEIPT_BYTES_MISMATCH:{path}")
        require(sha256_bytes(raw) == expected_sha256, f"ATTEMPT012_RECEIPT_HASH_MISMATCH:{path}")
        strict_json(raw, path)
        facts.append({
            "path": path.as_posix(), "git_blob_bytes": expected_bytes,
            "git_blob_sha256": expected_sha256,
            "authority": "HISTORICAL_FROZEN_NON_AUTHORITATIVE_FOR_REVISION2",
        })
    return facts


def validate_passport(document: dict[str, Any], label: str) -> None:
    passport = document.get("material_passport")
    require(isinstance(passport, dict), f"MATERIAL_PASSPORT_MISSING:{label}")
    require(passport.get("origin_skill") == "experiment-agent", f"PASSPORT_ORIGIN_SKILL:{label}")
    require(passport.get("verification_status") == "UNVERIFIED", f"PASSPORT_VERIFICATION:{label}")
    require("version_label" in passport, f"PASSPORT_VERSION_LABEL:{label}")
    require("upstream_dependencies" in passport, f"PASSPORT_UPSTREAM:{label}")
    require("repro_lock" in passport, f"PASSPORT_REPRO_LOCK:{label}")
    intake = passport.get("experiment_intake_declaration")
    require(
        isinstance(intake, dict)
        and intake.get("status") == "no_experiments_declared"
        and intake.get("declared_by") == "scholar",
        f"PASSPORT_EXPERIMENT_INTAKE:{label}",
    )
    require(passport.get("experiment_provenance") == [], f"PASSPORT_PROVENANCE:{label}")


def validate_documents(documents: dict[Path, dict[str, Any]]) -> None:
    runtime = documents[RUNTIME_CONTRACT]
    owner = documents[AUTHORITY_CONTRACT]
    lineage = documents[LINEAGE_CONTRACT]
    contract = documents[CONTRACT]
    authorization = documents[AUTHORIZATION]
    for path, document in documents.items():
        validate_passport(document, path.name)
    require(
        runtime.get("schema_version")
        == "stage1e-e4-r6-pc2w-p1-attempt013-runtime-identity-compatibility-contract-1.0",
        "RUNTIME_CONTRACT_SCHEMA_MISMATCH",
    )
    require(
        owner.get("schema_version")
        == "stage1e-e4-r6-pc2w-p1-attempt013-pre-runtime-authority-contract-1.0",
        "AUTHORITY_CONTRACT_SCHEMA_MISMATCH",
    )
    require(lineage.get("schema_version") == LINEAGE_SCHEMA, "LINEAGE_SCHEMA_MISMATCH")
    require(contract.get("schema_version") == CONTRACT_SCHEMA, "CONTRACT_SCHEMA_MISMATCH")
    require(authorization.get("schema_version") == AUTHORIZATION_SCHEMA, "AUTHORIZATION_SCHEMA_MISMATCH")

    seams = runtime.get("adjudicated_seams", {})
    require(
        seams.get("process_identity", {}).get("parent_resolution_closed_union")
        == ["RESOLVED", "UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT"],
        "PARENT_UNION_MISMATCH",
    )
    require(seams.get("process_identity", {}).get("direct_self_identity_required") is True, "DIRECT_SELF_NOT_REQUIRED")
    require(seams.get("tcp_ownership", {}).get("authority") == "VALIDATED_DIRECT_SELF_IDENTITY_INDEX", "TCP_AUTHORITY_MISMATCH")
    require(seams.get("tcp_ownership", {}).get("parent_completeness_dependency") is False, "TCP_PARENT_DEPENDENCY_RETAINED")
    require(
        seams.get("docker_build_time", {}).get("accepted_comparisons")
        == ["EXACT_RAW", "FORMAT_EQUIVALENT_CIVIL_SECOND"],
        "BUILDTIME_COMPARATOR_UNION_MISMATCH",
    )
    require(seams.get("docker_build_time", {}).get("nonzero_fraction_allowed") is False, "NONZERO_FRACTION_ALLOWED")

    packet_gate = contract.get("packet_entry_gate", {})
    require(
        packet_gate.get("packet_parent_checkpoint") == R2_REVISION4,
        "PACKET_PARENT_CONTRACT_MISMATCH",
    )
    require(packet_gate.get("aggregate_packet_files") == list(PACKET_ROSTER), "PACKET_ROSTER_MISMATCH")
    require(packet_gate.get("frozen_r0_files") == [path.as_posix() for path in FROZEN_R0_PATHS], "FROZEN_PARTITION_MISMATCH")
    require(packet_gate.get("unchanged_support_files") == [path.as_posix() for path in SUPPORT_PATHS], "SUPPORT_PARTITION_MISMATCH")
    require(packet_gate.get("final_sealing_commit_files") == [path.as_posix() for path in SEALING_PATHS], "SEALING_PARTITION_MISMATCH")
    require(packet_gate.get("aggregate_packet_file_count") == 13, "PACKET_COUNT_MISMATCH")
    require(packet_gate.get("final_sealing_commit_file_count") == 4, "SEAL_COUNT_MISMATCH")
    require(packet_gate.get("final_sealing_status") == "M", "SEAL_STATUS_MISMATCH")

    expected_runtime = {
        "path": RUNTIME_CONTRACT.as_posix(), "raw_git_blob_bytes": 4121,
        "raw_git_blob_sha256": ORIGIN_FACTS[RUNTIME_CONTRACT][2],
    }
    expected_authority = {
        "path": AUTHORITY_CONTRACT.as_posix(), "raw_git_blob_bytes": 4526,
        "raw_git_blob_sha256": ORIGIN_FACTS[AUTHORITY_CONTRACT][2],
    }
    expected_lineage = {
        "path": LINEAGE_CONTRACT.as_posix(), "raw_git_blob_bytes": 2543,
        "raw_git_blob_sha256": ORIGIN_FACTS[LINEAGE_CONTRACT][2],
        "schema_version": LINEAGE_SCHEMA,
        "public_seam": "e4_r6_pc2w_p1_attempt013_packet_lineage.validate_packet_lineage",
    }
    for document in (contract, authorization):
        runtime_binding = document.get("runtime_identity_compatibility_binding", {})
        authority_binding = document.get("pre_runtime_authority_binding", {})
        lineage_binding = document.get("packet_lineage_binding", {})
        require(all(runtime_binding.get(k) == v for k, v in expected_runtime.items()), "RUNTIME_BINDING_MISMATCH")
        require(all(authority_binding.get(k) == v for k, v in expected_authority.items()), "AUTHORITY_BINDING_MISMATCH")
        require(all(lineage_binding.get(k) == v for k, v in expected_lineage.items()), "LINEAGE_BINDING_MISMATCH")
        require(runtime_binding.get("restated_seam_values") is False, "SEAM_VALUES_RESTATED")
        require(authority_binding.get("restated_authority_values") is False, "AUTHORITY_VALUES_RESTATED")
        require(lineage_binding.get("restated_lineage_values") is False, "LINEAGE_VALUES_RESTATED")

    expected_receipts = {
        "central_path": CENTRAL_RECEIPT.as_posix(), "central_schema": CENTRAL_SCHEMA,
        "central_verdict": CENTRAL_VERDICT, "fresh_audit_path": AUDIT_RECEIPT.as_posix(),
        "fresh_audit_schema": AUDIT_SCHEMA, "fresh_audit_verdict": AUDIT_VERDICT,
        "fresh_audit_must_link_central_raw_sha256": True,
        "fresh_audit_requirement": "WAIVED_BY_CURRENT_USER",
        "fresh_audit_receipt_semantics": "USER_OVERRIDE_NOT_AN_INDEPENDENT_AUDIT",
        "user_override_confirmation": "CURRENT_USER_IF_FAILURE_AUDIT_AND_FIX_STANDING_AUTHORITY_2026_08_30",
        "attempt012_receipts_accepted": False,
        "attempt013_revision1_receipts_accepted": False,
        "attempt013_revision2_receipts_accepted": False,
        "attempt013_revision3_receipts_accepted": False,
        "attempt013_revision4_receipts_accepted": False,
    }
    require(contract.get("receipt_contract") == expected_receipts, "CONTRACT_RECEIPT_GATE_MISMATCH")
    require(authorization.get("receipt_contract") == expected_receipts, "AUTHORIZATION_RECEIPT_GATE_MISMATCH")
    expected_revision4_evidence = {
        "result_commit": "dd86eb11f58bfae46ee6f14f5eb1848b7aa2d1cf",
        "execution_receipt_sha256": (
            "905605a319d483fae429a8a6654c19d6fb18b8cc3f38a0606f6660516cdccc62"
        ),
        "verdict": (
            "FAIL_CLOSED_PC2W_P1_ATTEMPT013_REVISION4_CURRENT_HOST_NOT_ADMISSIBLE"
        ),
        "commands_recorded": 27,
        "docker_startup_succeeded": True,
        "closure_stable": True,
        "revision4_may_be_reinvoked": False,
    }
    authorization_evidence = authorization.get("revision4_runtime_failure_evidence", {})
    require(
        authorization_evidence == expected_revision4_evidence,
        "AUTHORIZATION_REVISION4_EVIDENCE_MISMATCH",
    )
    contract_evidence = contract.get("revision4_runtime_failure_evidence", {})
    require(
        all(contract_evidence.get(key) == value for key, value in expected_revision4_evidence.items()),
        "CONTRACT_REVISION4_EVIDENCE_MISMATCH",
    )
    require(
        contract_evidence.get("identity_failure_codes")
        == [
            "PROCESS_PROBE_READ_FILE_VERSION",
            "TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE",
        ],
        "REVISION4_IDENTITY_FAILURE_EVIDENCE_MISMATCH",
    )
    require(
        contract_evidence.get("docker_info_arch_alias_mismatch_observed") is True
        and contract_evidence.get("waiver_receipt_legacy_count_mismatch_observed") is True,
        "REVISION4_COMPATIBILITY_EVIDENCE_MISSING",
    )

    expected_budget = {
        "authorized": 1, "consumed": 0, "remaining": 1,
        "automatic_retry_count": 0, "fallback_count": 0,
    }
    require(owner.get("authority_contract", {}).get("attempt_budget") == expected_budget, "OWNER_BUDGET_MISMATCH")
    require(contract.get("attempt_budget") == expected_budget, "CONTRACT_BUDGET_MISMATCH")
    require(authorization.get("attempt_budget") == expected_budget, "AUTHORIZATION_BUDGET_MISMATCH")
    expected_exact_command = {
        "required_original_argv_prefix": [
            "PYTHON_EXECUTABLE", "-B", "RUNNER_PATH"
        ],
        "required_interpreter_flags": ["-B"],
        "required_interpreter_flag_count": 1,
        "machine_checked_by": (
            "e4_r6_pc2w_p1_attempt010_command_interface."
            "bind_exact_python_script_argv"
        ),
        "revision2_failure_error_sha256": (
            "4190f8dce17455e17eb3615e06ccbfd23249346e5bdcfec01a5aa085b47212b4"
        ),
        "revision2_failure_stable_code": "INTERPRETER_FLAGS_EXACT_MISMATCH",
        "revision2_may_be_reinvoked": False,
    }
    require(
        contract.get("exact_process_command_contract") == expected_exact_command,
        "CONTRACT_EXACT_COMMAND_GATE_MISMATCH",
    )
    require(
        authorization.get("exact_process_command_contract")
        == expected_exact_command,
        "AUTHORIZATION_EXACT_COMMAND_GATE_MISMATCH",
    )
    expected_adapter_contract = {
        "module_chain": [
            "ATTEMPT013", "ATTEMPT012", "ATTEMPT011", "ATTEMPT010",
            "ATTEMPT009",
        ],
        "original_json_io_owner": "ATTEMPT009",
        "load_reference": (
            "previous.previous.previous.previous._ORIGINAL_LOAD_JSON"
        ),
        "write_reference": (
            "previous.previous.previous.previous._ORIGINAL_WRITE_JSON"
        ),
        "forbidden_three_hop_reference": True,
        "revision3_failure_error_sha256": (
            "a76a4582be67134579d5f7224a7d76dbb4411750b3b517d0de5b4a88c3395c80"
        ),
        "revision3_may_be_reinvoked": False,
    }
    require(
        contract.get("adapter_ancestry_contract") == expected_adapter_contract,
        "CONTRACT_ADAPTER_ANCESTRY_GATE_MISMATCH",
    )
    require(
        authorization.get("adapter_ancestry_contract")
        == expected_adapter_contract,
        "AUTHORIZATION_ADAPTER_ANCESTRY_GATE_MISMATCH",
    )
    policy = owner.get("model_policy", {})
    expected_role = {
        "requested_model": "gpt-5.6-sol", "requested_reasoning_effort": "xhigh",
        "requested_service_tier": "default", "requested_display_tier": "Standard",
        "fast_or_priority_allowed": False,
    }
    for role in ("implementation_static", "locked_execution"):
        require(policy.get("roles", {}).get(role) == expected_role, f"MODEL_ROLE_MISMATCH:{role}")
    observation = authorization.get("implementation_model_observation", {})
    try:
        model_record = authority.validate_model_policy(
            policy, "locked_execution", observation
        )
    except authority.AuthorityError as exc:
        raise RuntimeError(
            f"PRODUCTION_MODEL_ATTESTATION_INVALID:{exc.code}"
        ) from exc
    require(model_record["actual"] == observation, "MODEL_ATTESTATION_PROJECTION_DRIFT")

    future = authorization.get("future_exact_confirmation", {})
    for key in (
        "standing_user_authorization",
        "auto_execution_activation_requires_central_pass",
        "current_user_audit_waiver",
        "audit_waiver_does_not_claim_independent_verification",
        "auto_execution_activation_requires_deterministic_exact_command_binding",
        "user_override_replaces_only_fresh_audit_gate",
    ):
        require(future.get(key) is True, f"STANDING_AUTHORIZATION_GATE_MISSING:{key}")
    require(
        future.get("auto_execution_activation_requires_fresh_audit_pass") is False,
        "AUDIT_WAIVER_NOT_BOUND",
    )
    require(
        future.get("confirmation_token")
        == "USER_CONFIRMED_EXACT_ATTEMPT013_REVISION5_PROCESS_COMMAND_WITH_DASH_B_AND_AUDIT_WAIVER",
        "REVISION5_CONFIRMATION_TOKEN_MISMATCH",
    )
    require(contract.get("output_contract", {}).get("output_root") == OUTPUT.as_posix(), "OUTPUT_ROOT_MISMATCH")
    require(contract.get("output_contract", {}).get("absent_before_execution") is True, "OUTPUT_ABSENCE_NOT_CONTRACTED")
    require(contract.get("scope_boundary", {}).get("runtime_execution_authorized_now") is True, "CONTRACT_RUNTIME_NOT_AUTHORIZED")
    require(authorization.get("user_decision", {}).get("runtime_execution_authorized_now") is True, "AUTH_RUNTIME_NOT_AUTHORIZED")
    require(authorization.get("user_decision", {}).get("automatic_retry_authorized") is False, "AUTOMATIC_RETRY_AUTHORIZED")
    for document in (contract, authorization):
        truth = document.get("truth_state", {})
        require(truth.get("RESULT_STATUS") == "NOT_RUN", "RESULT_STATUS_WIDENED")
        require(truth.get("TEST_SET_OPENED") == "NO", "TEST_SET_WIDENED")
        require(truth.get("ACCEPTED_RESULT_ROWS") == 0, "ACCEPTED_ROWS_WIDENED")
        require(truth.get("benchmark_admission_opened") is False, "BENCHMARK_OPENED")


def imported_modules(tree: ast.AST) -> set[str]:
    result = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    result.update(
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    )
    return result


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def validate_sources(repo: Path) -> dict[str, Any]:
    validator_tree = ast.parse((repo / VALIDATOR).read_text(encoding="utf-8"), filename=VALIDATOR.as_posix())
    direct_imports = imported_modules(validator_tree)
    require(
        not any(RUNNER_MODULE_PATTERN.fullmatch(name) for name in direct_imports),
        "STATIC_VALIDATOR_IMPORTS_RUNNER",
    )
    require("importlib" not in direct_imports and "runpy" not in direct_imports, "VALIDATOR_DYNAMIC_IMPORT_CAPABILITY")

    helper_source = (repo / LINEAGE_HELPER).read_text(encoding="utf-8")
    helper_tree = ast.parse(helper_source, filename=LINEAGE_HELPER.as_posix())
    helper_imports = imported_modules(helper_tree)
    allowed_helper_imports = {"__future__", "dataclasses", "pathlib", "re", "typing"}
    require(helper_imports <= allowed_helper_imports, "LINEAGE_HELPER_IMPORT_NOT_PURE")
    forbidden_calls = {"open", "exec", "eval", "compile", "__import__"}
    require(
        not any(
            isinstance(node, ast.Call) and dotted_name(node.func) in forbidden_calls
            for node in ast.walk(helper_tree)
        ),
        "LINEAGE_HELPER_FORBIDDEN_CALL",
    )
    require(
        not any(RUNNER_MODULE_PATTERN.fullmatch(name) for name in helper_imports),
        "LINEAGE_HELPER_RUNNER_IMPORT",
    )

    runner = (repo / RUNNER).read_text(encoding="utf-8")
    compatibility = (repo / RUNTIME_HELPER).read_text(encoding="utf-8")
    authority = (repo / AUTHORITY_HELPER).read_text(encoding="utf-8")
    main = runner[runner.index("def main() -> int:"):]
    handoff = main.index("binding = authority.prepare_legacy_handoff")
    exact = main.index("command_interface.bind_exact_python_script_argv", handoff)
    lineage_call = main.index("lineage_evidence = _validate_packet_lineage", exact)
    configure = main.index("configure_attempt013_runner()", lineage_call)
    root_rebind = main.index("legacy.EXPECTED_EXECUTION_ROOT = binding.execution_root", configure)
    legacy_main = main.index("return legacy.main()", root_rebind)
    require(handoff < exact < lineage_call < configure < root_rebind < legacy_main, "PRE_LEGACY_ORDER_INVALID")
    require("return packet_lineage.validate_packet_lineage(spec, observation)" in runner, "RUNNER_DOES_NOT_CALL_SHARED_LINEAGE_SEAM")
    require("legacy.git =" not in runner, "RUNNER_MONKEYPATCHES_GIT")
    configure_body = runner[runner.index("def configure_attempt013_runner() -> None:"):runner.index("def main() -> int:")]
    require("legacy.PACKET_PARENT = PACKET_PARENT" in configure_body, "RETAINED_PACKET_PARENT_NOT_CONFIGURED")
    require("legacy.PACKET_RELATIVES = PACKET_RELATIVES" in configure_body, "RETAINED_PACKET_RELATIVES_NOT_CONFIGURED")
    require("PACKET_RELATIVES = set(SEALING_PATHS)" in runner, "SEALING_AUTHORITY_NOT_SEPARATE")
    require("PACKET_RELATIVES = set(PACKET_PATHS)" not in runner, "AGGREGATE_CONFLATION_REINTRODUCED")
    require("legacy.probes_v2 = compatibility" in configure_body, "PROCESS_TCP_VALIDATOR_NOT_INSTALLED")
    require(
        "sanitize_docker_identity=_sanitize_docker_identity_revision5"
        in configure_body,
        "REVISION5_DOCKER_COMPARATOR_NOT_INSTALLED",
    )
    require(
        "PROCESS_IDENTITY_QUERY_REVISION5" in configure_body,
        "REVISION5_PROCESS_QUERY_NOT_INSTALLED",
    )
    require("compatibility.TCP_IDENTITY_QUERY_V3" in configure_body, "TCP_QUERY_NOT_INSTALLED")
    require("*sys.argv[1:]" not in runner, "ACTUAL_ARGV_TAIL_COPIED")
    require("output.exists()" in authority, "OUTPUT_ABSENCE_GATE_MISSING")
    require("(1, 0, 1)" in authority, "ONE_SHOT_BUDGET_GATE_MISSING")
    require(compatibility.count("Get-CimInstance") == 1, "PROCESS_QUERY_NOT_SINGLE_SNAPSHOT")
    require("UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT" in compatibility, "PARENT_UNION_MISSING")
    require("FORMAT_EQUIVALENT_CIVIL_SECOND" in compatibility, "BUILDTIME_EQUIVALENCE_MISSING")
    require("root_value_sha256" in compatibility and "engine_value_sha256" in compatibility, "BUILDTIME_HASH_RECEIPT_MISSING")
    require(
        "ABSENT_FROM_PE_METADATA_HASH_AND_SIGNATURE_BOUND" in runner
        and "$currentTarget -ne 'com.docker.build'" in runner,
        "REVISION5_FILE_VERSION_SENTINEL_NOT_CLOSED",
    )
    require(
        '"amd64": "amd64"' in runner
        and '"x86_64": "amd64"' in runner
        and '"arm64": "arm64"' in runner
        and '"aarch64": "arm64"' in runner,
        "REVISION5_ARCHITECTURE_ALIASES_MISSING",
    )
    require(
        'result["user_audit_waiver_receipt"] = result.pop(' in runner
        and 'gate_receipts["fresh_independent_audit_performed"] = False' in runner
        and 'result["fresh_independent_audit_performed"] = False' not in runner,
        "REVISION5_WAIVER_RECEIPT_COUNT_FIX_MISSING",
    )
    require("subprocess" not in compatibility and "subprocess" not in authority, "PURE_IDENTITY_SEAM_HOST_CAPABILITY")
    require(CENTRAL_SCHEMA in runner and AUDIT_SCHEMA in runner, "REVISION5_RECEIPT_SCHEMAS_NOT_BOUND")
    require(
        'command_interface.REQUIRED_INTERPRETER_FLAGS != ("-B",)' in runner,
        "REVISION5_DASH_B_RUNTIME_ASSERTION_MISSING",
    )
    require(
        '"required_original_argv_prefix": [' in runner
        and '"PYTHON_EXECUTABLE", "-B", "RUNNER_PATH"' in runner,
        "REVISION5_USER_VISIBLE_COMMAND_PREFIX_NOT_BOUND",
    )
    require(
        "previous.previous.previous.previous._ORIGINAL_LOAD_JSON(path)"
        in runner,
        "REVISION5_ORIGINAL_LOAD_OWNER_DEPTH_MISSING",
    )
    require(
        "previous.previous.previous.previous._ORIGINAL_WRITE_JSON("
        in runner,
        "REVISION5_ORIGINAL_WRITE_OWNER_DEPTH_MISSING",
    )
    runner_tree = ast.parse(runner, filename=RUNNER.as_posix())
    load_owner_refs = {
        dotted_name(node)
        for node in ast.walk(runner_tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "_ORIGINAL_LOAD_JSON"
    }
    write_owner_refs = {
        dotted_name(node)
        for node in ast.walk(runner_tree)
        if isinstance(node, ast.Attribute)
        and node.attr == "_ORIGINAL_WRITE_JSON"
    }
    require(
        load_owner_refs
        == {"previous.previous.previous.previous._ORIGINAL_LOAD_JSON"},
        "REVISION5_ORIGINAL_LOAD_OWNER_AST_MISMATCH",
    )
    require(
        write_owner_refs
        == {"previous.previous.previous.previous._ORIGINAL_WRITE_JSON"},
        "REVISION5_ORIGINAL_WRITE_OWNER_AST_MISMATCH",
    )
    return {
        "static_validator_direct_runner_imports": 0,
        "direct_only_counter_is_not_import_authority": True,
        "shared_packet_lineage_helper_called_before_legacy_main": True,
        "retained_packet_parent_is_revision4": True,
        "retained_packet_relatives_are_exact_four_seal_paths": True,
        "retained_packet_delta_check_not_bypassed": True,
        "public_pre_legacy_handoff_order_valid": True,
        "parent_union_and_direct_self_validator_installed": True,
        "tcp_direct_self_index_binding_installed": True,
        "build_time_field_comparator_installed": True,
        "single_process_snapshot_query": True,
    }


def local_imports(repo: Path, relative: Path, cache: dict[Path, tuple[set[Path], ast.AST]]) -> tuple[set[Path], ast.AST]:
    if relative in cache:
        return cache[relative]
    source = (repo / relative).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=relative.as_posix())
    dynamic_calls = {"__import__", "importlib.import_module", "runpy.run_module", "runpy.run_path"}
    require(
        not any(
            isinstance(node, ast.Call) and dotted_name(node.func) in dynamic_calls
            for node in ast.walk(tree)
        ),
        f"DYNAMIC_IMPORT_GRAPH_AMBIGUOUS:{relative.as_posix()}",
    )
    dependencies: set[Path] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            require(node.level == 0, f"RELATIVE_IMPORT_GRAPH_AMBIGUOUS:{relative.as_posix()}")
            if node.module:
                modules.append(node.module)
        for module in modules:
            candidate = CONTROL / (module.replace(".", "/") + ".py")
            if (repo / candidate).is_file():
                dependencies.add(candidate)
            elif module.startswith(("e4_", "execute_e4_", "test_e4_")):
                raise RuntimeError(f"LOCAL_IMPORT_UNRESOLVED:{module}")
    cache[relative] = (dependencies, tree)
    return cache[relative]


def import_closure(
    repo: Path, entry: Path, cache: dict[Path, tuple[set[Path], ast.AST]]
) -> tuple[set[Path], set[tuple[str, str]]]:
    visited: set[Path] = set()
    visiting: set[Path] = set()
    cycles: set[tuple[str, str]] = set()

    def visit(path: Path) -> None:
        if path in visited:
            return
        if path in visiting:
            return
        visiting.add(path)
        dependencies, _tree = local_imports(repo, path, cache)
        for dependency in sorted(dependencies, key=lambda item: item.as_posix()):
            if dependency in visiting:
                cycles.add((path.as_posix(), dependency.as_posix()))
            else:
                visit(dependency)
        visiting.remove(path)
        visited.add(path)

    visit(entry)
    return visited, cycles


def validate_import_graph(repo: Path) -> dict[str, Any]:
    cache: dict[Path, tuple[set[Path], ast.AST]] = {}
    entries = []
    reaching: set[Path] = set()
    runner_free: set[Path] = set()
    all_cycles: set[tuple[str, str]] = set()
    closures: dict[Path, set[Path]] = {}
    for path, _count, label in CANDIDATE_SUITES:
        closure, cycles = import_closure(repo, path, cache)
        closures[path] = closure
        all_cycles.update(cycles)
        runners = sorted(
            module.stem for module in closure
            if RUNNER_MODULE_PATTERN.fullmatch(module.stem)
        )
        if runners:
            reaching.add(path)
        else:
            runner_free.add(path)
        entries.append({
            "suite": label, "path": path.as_posix(),
            "local_transitive_closure_count": len(closure),
            "reachable_runner_modules": runners,
            "classification": "EXCLUDED_RUNNER_REACHING" if runners else "AUTHORITATIVE_RUNNER_FREE",
        })
    require(reaching == EXPECTED_RUNNER_REACHING, "RUNNER_REACHING_SUITE_SET_MISMATCH")
    require(runner_free == EXPECTED_RUNNER_FREE, "RUNNER_FREE_SUITE_SET_MISMATCH")
    for path in reaching:
        runners = {
            module.stem for module in closures[path]
            if RUNNER_MODULE_PATTERN.fullmatch(module.stem)
        }
        require(runners == {"execute_e4_r6_pc2w_p1_attempt007_admission_observation"}, f"RUNNER_REACHABILITY_TARGET_MISMATCH:{path}")
    forbidden_process_calls = {
        "subprocess.run", "subprocess.Popen", "subprocess.call",
        "subprocess.check_call", "subprocess.check_output", "os.system", "os.popen",
        "socket.socket", "urllib.request.urlopen", "requests.get", "requests.post",
    }
    for entry in runner_free:
        for module in closures[entry]:
            _deps, tree = local_imports(repo, module, cache)
            require(
                not any(
                    isinstance(node, ast.Call) and dotted_name(node.func) in forbidden_process_calls
                    for node in ast.walk(tree)
                ),
                f"RUNNER_FREE_CLOSURE_HAS_HOST_PROCESS_CALL:{entry.as_posix()}:{module.as_posix()}",
            )
    return {
        "resolution": "RECURSIVE_CYCLE_SAFE_REPOSITORY_LOCAL_AST_NO_IMPORT_EXECUTION",
        "candidate_suite_entrypoints": 9,
        "runner_reaching_candidate_entrypoints": 4,
        "runner_free_candidate_entrypoints": 5,
        "excluded_runner_reaching_suites": 4,
        "authoritative_executed_runner_free_suites": 5,
        "executed_child_runner_imports": 0,
        "runner_main_invocations": 0,
        "cycle_edges_resolved_deterministically": len(all_cycles),
        "entries": entries,
    }


def test_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def run_authoritative_tests(repo: Path, import_graph: dict[str, Any]) -> list[dict[str, Any]]:
    free_paths = {
        Path(entry["path"])
        for entry in import_graph["entries"]
        if entry["classification"] == "AUTHORITATIVE_RUNNER_FREE"
    }
    require(free_paths == EXPECTED_RUNNER_FREE, "AUTHORITATIVE_SUITE_SET_DRIFT")
    results = []
    for relative, expected_count, label in CANDIDATE_SUITES:
        if relative not in free_paths:
            continue
        require(test_count(repo / relative) == expected_count, f"TEST_COUNT_MISMATCH:{label}")
        source = (repo / relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative.as_posix())
        decorators = [
            ast.unparse(decorator)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for decorator in node.decorator_list
        ]
        require(
            not any(
                any(token in value for token in ("skip", "xfail", "expectedFailure"))
                for value in decorators
            ),
            f"SKIP_OR_XFAIL:{label}",
        )
        require("pytestmark" not in source and "pytest.mark.xfail" not in source, f"XFAIL_MARKER:{label}")
        completed = subprocess.run(
            [str(PYTHON.resolve()), "-B", str(repo / relative)],
            cwd=repo, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, check=False,
        )
        require(completed.returncode == 0, f"STATIC_TEST_FAILURE:{label}")
        results.append({
            "suite": label, "path": relative.as_posix(),
            "tests_passed": expected_count, "tests_total": expected_count,
            "python_dash_b": True, "transitive_ast_runner_reachable": False,
            "runtime_or_host_commands": 0,
        })
    require(len(results) == 5, "AUTHORITATIVE_SUITE_EXECUTION_COUNT_MISMATCH")
    require(sum(row["tests_total"] for row in results) == 112, "AUTHORITATIVE_TEST_TOTAL_MISMATCH")
    return results


def bytecode_inventory(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (len(raw), sha256_bytes(raw))
        for path in sorted(root.rglob("*.pyc"))
        for raw in [path.read_bytes()]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--precommit", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    require(Path(sys.executable).resolve() == PYTHON.resolve(), "VALIDATOR_PYTHON_MISMATCH")
    require(Path.cwd().resolve() == repo, "VALIDATOR_CWD_MISMATCH")
    require(Path(str(git(repo, "rev-parse", "--show-toplevel"))).resolve() == repo, "REPOSITORY_ROOT_MISMATCH")
    require((repo / VALIDATOR).resolve() == Path(__file__).resolve(), "VALIDATOR_PATH_MISMATCH")
    require(not (repo / OUTPUT).exists(), "ATTEMPT013_OUTPUT_ROOT_ALREADY_EXISTS")
    require(not (repo / CENTRAL_RECEIPT).exists(), "REVISION5_CENTRAL_RECEIPT_PREEXISTS")
    require(not (repo / AUDIT_RECEIPT).exists(), "REVISION5_USER_AUDIT_WAIVER_RECEIPT_PREEXISTS")

    revision = validate_commit_shape(repo, args.precommit)
    packet_facts = validate_packet(repo, revision, args.precommit)
    lineage_evidence = validate_lineage(repo, revision, args.precommit, packet_facts)
    historical_receipts = validate_attempt012_receipts(repo, revision, args.precommit)
    json_paths = (
        RUNTIME_CONTRACT, AUTHORITY_CONTRACT, LINEAGE_CONTRACT, CONTRACT, AUTHORIZATION,
    )
    documents = {
        path: strict_json(packet_bytes(repo, revision, path, args.precommit), path)
        for path in json_paths
    }
    validate_documents(documents)
    source_checks = validate_sources(repo)
    import_graph = validate_import_graph(repo)
    pyc_before = bytecode_inventory(repo / CONTROL)
    test_results = run_authoritative_tests(repo, import_graph)
    pyc_after = bytecode_inventory(repo / CONTROL)
    require(pyc_before == pyc_after, "PYTHON_BYTECODE_INVENTORY_CHANGED")
    require(not (repo / OUTPUT).exists(), "ATTEMPT013_OUTPUT_ROOT_CREATED")

    result = {
        "schema_version": VALIDATOR_SCHEMA,
        "material_passport": {
            "origin_skill": "experiment-agent",
            "origin_mode": "validate",
            "origin_date": "2026-08-29T00:00:00+07:00",
            "verification_status": "UNVERIFIED",
            "version_label": "stage1e_e4_r6_pc2w_p1_attempt013_revision5_static_validation_result_v1",
            "upstream_dependencies": [
                "stage1e_e4_r6_pc2w_p1_attempt013_revision2_packet_lineage_contract_v1",
                "stage1e_e4_r6_pc2w_p1_attempt013_revision5_admission_observation_contract_v1",
                "stage1e_e4_r6_pc2w_p1_attempt013_revision5_execution_authorization_v1",
            ],
            "repro_lock": None,
            "experiment_intake_declaration": {
                "status": "no_experiments_declared",
                "declared_at": "2026-08-29T00:00:00+07:00",
                "declared_by": "scholar",
            },
            "experiment_provenance": [],
        },
        "stage_id": "E4-R6-PC2W-P1-ATTEMPT013",
        "validation_mode": "PRECOMMIT_WORKTREE" if args.precommit else "COMMITTED_REPLAY",
        "validated_revision": revision,
        "lineage_topology": {
            "r0_commit": R0, "r0_parent": START,
            "r1_commit": R1, "r1_parent": R0,
            "central_failure_commit": CENTRAL_FAILURE, "central_failure_parent": R1,
            "plan_commit": PLAN, "plan_parent": CENTRAL_FAILURE,
            "r2a_commit": R2A, "r2a_parent": PLAN,
            "p1_commit": P1, "p1_parent": R2A,
            "revision4_packet_commit": R2_REVISION4,
            "revision4_packet_parent": P1,
            "revision5_packet_commit": None if args.precommit else revision,
            "revision5_packet_parent": R2_REVISION4,
        },
        "exact_write_sets": {
            "r0": [f"A\t{path.as_posix()}" for path in R0_FILES],
            "r1": [f"A\t{path.as_posix()}" for path in R1_FILES],
            "r2a": [f"A\t{path.as_posix()}" for path in R2A_FILES],
            "p1": [f"A\t{P1_PLAN_FILE.as_posix()}"],
            "revision4": [f"M\t{path.as_posix()}" for path in SEALING_PATHS],
            "revision5": [f"M\t{path.as_posix()}" for path in SEALING_PATHS],
        },
        "aggregate_packet_roster_count": 13,
        "packet_artifacts": packet_facts,
        "packet_lineage_evidence": lineage_evidence,
        "frozen_r0_artifacts_unchanged": 4,
        "r1_support_artifacts_unchanged": 2,
        "r2a_support_artifacts_unchanged": 3,
        "historical_attempt012_runtime_receipts": historical_receipts,
        "historical_attempt012_receipts_authoritative_for_revision5": False,
        "historical_revision4_runtime_result_authoritative_for_revision5_gate": False,
        "strict_json_files_passed": len(json_paths),
        "strict_json_files_total": len(json_paths),
        "source_checks": source_checks,
        "recursive_ast_import_graph": import_graph,
        "test_results": test_results,
        "authoritative_aggregate_tests_passed": 112,
        "authoritative_aggregate_tests_total": 112,
        "historical_runner_reaching_tests_observed_non_authoritative": 41,
        "new_or_modified_python_bytecode_files": 0,
        "command_inventory": {
            "python_dash_b_static_test_processes": 5,
            "full_user_visible_python_dash_b_runner_prefix_checked": True,
            "attempt009_original_json_io_owner_depth_checked": True,
            "read_only_git_commands": GIT_COMMAND_COUNT,
            "runner_imports_in_executed_child_closures": 0,
            "runner_invocations": 0,
            "docker_commands": 0,
            "wsl_commands": 0,
            "hyper_v_commands": 0,
            "powershell_host_probe_commands": 0,
            "network_operations": 0,
            "materialization_training_evaluation_benchmark_or_test_operations": 0,
            "automatic_retry_count": 0,
            "fallback_count": 0,
        },
        "attempt_budget": {
            "authorized": 1, "consumed": 0, "remaining": 1,
            "automatic_retry_count": 0, "fallback_count": 0,
        },
        "output_root_absent": True,
        "runtime_commands_executed": False,
        "RESULT_STATUS": "NOT_RUN",
        "TEST_SET_OPENED": "NO",
        "ACCEPTED_RESULT_ROWS": 0,
        "benchmark_admission_opened": False,
        "model_policy": {
            "requested_model": "gpt-5.6-sol",
            "requested_reasoning_effort": "xhigh",
            "requested_service_tier": "default",
            "requested_display_tier": "Standard",
            "actual_model": "gpt-5.6-sol",
            "actual_reasoning_effort": "xhigh",
            "actual_service_tier": "UNOBSERVABLE",
            "actual_speed": "UNOBSERVABLE",
            "fast_or_priority_observed": False,
        },
        "standing_user_authorization": {
            "activation_requires_central_pass": True,
            "activation_requires_fresh_audit_pass": False,
            "current_user_audit_waiver": True,
            "audit_waiver_is_not_independent_verification": True,
            "activation_requires_deterministic_exact_command_binding": True,
            "override_scope": "FRESH_AUDIT_GATE_ONLY",
            "active_now": False,
        },
        "central_and_user_audit_waiver_receipts_created": False,
        "next_gate": "CENTRAL_STATIC_VALIDATION_THEN_USER_AUDIT_WAIVER_RECEIPT",
        "verdict": "IMPLEMENTATION_PASS_READY_FOR_CENTRAL_STATIC_VALIDATION",
    }
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
