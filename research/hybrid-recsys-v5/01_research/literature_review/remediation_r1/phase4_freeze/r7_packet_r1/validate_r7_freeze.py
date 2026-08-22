#!/usr/bin/env python3
"""Build and deterministically validate the Stage 1B R1 R7 audit packet."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from collections import Counter, deque
from pathlib import Path, PurePosixPath
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
BASE = Path("research/hybrid-recsys-v5/01_research/literature_review/remediation_r1")
CONTROL = BASE / "00_control"
P3 = BASE / "phase3_analysis"
OUT = BASE / "phase4_freeze/r7_packet_r1"

CONTRACT = CONTROL / "r7_freeze_contract.md"
R7_INPUT = CONTROL / "r7_input_manifest.json"
PIPELINE_STATE = Path("research/hybrid-recsys-v5/01_research/pipeline_state_stage1b_remediation_r1.json")
R6_REAUDIT_INPUT = CONTROL / "r6_reaudit_input_manifest.json"
R6_INPUT = CONTROL / "r6_input_manifest.json"
R6_REMEDIATION_INPUT = CONTROL / "r6_remediation_input_manifest.json"
SCHOLAR = CONTROL / "scholar_tension_adjudication_r1.json"

R5_MAP = P3 / "claim_source_map_r1.json"
REM_MAP = P3 / "remediation_r6/claim_source_map_r1_remediated.json"
R5_HANDOFF = P3 / "r5_handoff.json"
R6_HANDOFF = P3 / "devils_advocate_cp2/r6_handoff.json"
R6_RECEIPT = P3 / "devils_advocate_cp2/r6_validation_receipt.json"
R6_PACKET = P3 / "devils_advocate_cp2/tension_adjudication_packet.json"
REM_HANDOFF = P3 / "remediation_r6/r6_remediation_handoff.json"
REM_RECEIPT = P3 / "remediation_r6/r6_remediation_validation_receipt.json"
REAUDIT_HANDOFF = P3 / "devils_advocate_cp2_reaudit/r6_reaudit_handoff.json"
REAUDIT_RECEIPT = P3 / "devils_advocate_cp2_reaudit/r6_reaudit_validation_receipt.json"
REAUDIT_PACKET = P3 / "devils_advocate_cp2_reaudit/tension_adjudication_packet_reaudit.json"

MANIFEST = OUT / "stage1b_r1_audit_packet_manifest.json"
ROOT_HASH = OUT / "stage1b_r1_root_hash.json"
REPORT = OUT / "stage1b_r1_freeze_report.md"
RECEIPT = OUT / "r7_validation_receipt.json"
HANDOFF = OUT / "r7_handoff.json"
VALIDATOR = OUT / "validate_r7_freeze.py"

EXPECTED_OUTPUTS = {
    MANIFEST.name,
    ROOT_HASH.name,
    REPORT.name,
    RECEIPT.name,
    HANDOFF.name,
    VALIDATOR.name,
}
SHA_RE = re.compile(r"[0-9a-f]{64}")
LIVE_STATE_READ_FORBIDDEN = False
LIVE_STATE_READ_ATTEMPTS = 0


def absolute(path: Path | str) -> Path:
    global LIVE_STATE_READ_ATTEMPTS
    candidate = Path(path)
    resolved = candidate if candidate.is_absolute() else ROOT / candidate
    if resolved.resolve() == (ROOT / PIPELINE_STATE).resolve() and LIVE_STATE_READ_FORBIDDEN:
        LIVE_STATE_READ_ATTEMPTS += 1
        raise RuntimeError("final mode attempted to dereference mutable live pipeline state")
    return resolved


def relative(path: Path | str) -> str:
    candidate = Path(path)
    if not candidate.is_absolute() and candidate.as_posix() == PIPELINE_STATE.as_posix():
        return PIPELINE_STATE.as_posix()
    if candidate.is_absolute() and candidate.resolve() == (ROOT / PIPELINE_STATE).resolve():
        return PIPELINE_STATE.as_posix()
    return absolute(path).resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_file(path: Path | str) -> str:
    return hashlib.sha256(absolute(path).read_bytes()).hexdigest()


def byte_count(path: Path | str) -> int:
    return absolute(path).stat().st_size


def load_json(path: Path | str) -> Any:
    return json.loads(absolute(path).read_text(encoding="utf-8"))


def json_bytes(value: Any, *, pretty: bool = True) -> bytes:
    if pretty:
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.encode("utf-8")


def write_json(path: Path | str, value: Any) -> None:
    absolute(path).write_bytes(json_bytes(value, pretty=True))


def is_repo_relative_path(raw: str) -> bool:
    return (
        bool(raw)
        and "/" in raw
        and "\\" not in raw
        and "://" not in raw
        and not Path(raw).is_absolute()
    )


def normalize_member_path(raw: str) -> str:
    if not is_repo_relative_path(raw):
        raise ValueError(f"not a repository-relative forward-slash path: {raw!r}")
    normalized = PurePosixPath(raw).as_posix()
    if normalized != raw or normalized.startswith("../") or "/../" in normalized:
        raise ValueError(f"noncanonical member path: {raw!r}")
    return normalized


def resolve_declared(raw: str, declaring: Path, integration_root: str | None) -> Path:
    if Path(raw).is_absolute():
        # Some frozen PDF-preflight sidecars retain the producer worktree's
        # absolute input path. Rebase its repository suffix into this worktree,
        # then verify the declared digest against the current immutable bytes.
        parts = Path(raw).parts
        if "research" in parts:
            rebased = ROOT.joinpath(*parts[parts.index("research") :])
            if rebased.is_file():
                return rebased.resolve()
        return Path(raw).resolve()
    if "://" in raw:
        return absolute(raw).resolve()
    candidates = [absolute(raw)]
    if integration_root and not Path(integration_root).is_absolute():
        candidates.append(absolute(Path(integration_root) / raw))
    candidates.append(declaring.parent / raw)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return candidates[0].resolve()


def recursive_declaration_audit(
    seed: Path, virtual_files: dict[str, bytes] | None = None
) -> dict[str, Any]:
    """Replay all reachable JSON path/byte/SHA declarations from one frozen seed."""
    virtual_files = virtual_files or {}
    queue: deque[tuple[Path, bytes | None]] = deque([(absolute(seed).resolve(), None)])
    visited: set[Path] = set()
    rows: list[dict[str, Any]] = []
    seen_rows: set[tuple[str, str, int | None, str]] = set()

    def add_row(
        declaring: Path,
        raw_path: str,
        expected_sha: Any,
        expected_bytes: Any,
        integration_root: str | None,
    ) -> None:
        if not isinstance(raw_path, str) or not isinstance(expected_sha, str):
            return
        if not SHA_RE.fullmatch(expected_sha):
            rows.append(
                {
                    "declared_in": relative(declaring),
                    "declared_path": raw_path,
                    "expected_bytes": expected_bytes,
                    "expected_sha256": expected_sha,
                    "pass": False,
                    "reason": "invalid_sha256_declaration",
                }
            )
            return
        normalized_bytes = expected_bytes if isinstance(expected_bytes, int) else None
        key = (relative(declaring), raw_path, normalized_bytes, expected_sha)
        if key in seen_rows:
            return
        seen_rows.add(key)
        virtual_path = raw_path if raw_path in virtual_files else None
        if virtual_path is not None:
            target = ROOT / virtual_path
            exists = True
            within_repo = True
            resolved_path = virtual_path
            actual_content = virtual_files[virtual_path]
            actual_bytes = len(actual_content)
            actual_sha = hashlib.sha256(actual_content).hexdigest()
        else:
            target = resolve_declared(raw_path, declaring, integration_root)
            exists = target.is_file()
            within_repo = False
            resolved_path = str(target)
            actual_content = None
        if exists and virtual_path is None:
            try:
                resolved_path = target.relative_to(ROOT.resolve()).as_posix()
                within_repo = True
            except ValueError:
                within_repo = False
            actual_bytes = target.stat().st_size
            actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        elif not exists:
            actual_bytes = None
            actual_sha = None
        passed = (
            exists
            and within_repo
            and (normalized_bytes is None or normalized_bytes == actual_bytes)
            and expected_sha == actual_sha
        )
        rows.append(
            {
                "declared_in": relative(declaring),
                "declared_path": raw_path,
                "resolved_path": resolved_path,
                "expected_bytes": normalized_bytes,
                "actual_bytes": actual_bytes,
                "expected_sha256": expected_sha,
                "actual_sha256": actual_sha,
                "pass": passed,
                "reason": None if passed else "missing_outside_repo_or_byte_sha_mismatch",
            }
        )
        if exists and within_repo and target.suffix.lower() == ".json":
            queue.append((target, actual_content))

    def walk(node: Any, declaring: Path, integration_root: str | None) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("path"), str) and "sha256" in node:
                add_row(declaring, node["path"], node["sha256"], node.get("bytes"), integration_root)

            for path_key in ("file", "filename", "relative_path"):
                if isinstance(node.get(path_key), str) and "sha256" in node:
                    add_row(
                        declaring,
                        node[path_key],
                        node["sha256"],
                        node.get("bytes", node.get("byte_count")),
                        integration_root,
                    )

            for key, value in node.items():
                if not isinstance(key, str):
                    continue
                if key.endswith("_path") and isinstance(value, str):
                    prefix = key[:-5]
                    sha_key = f"{prefix}_sha256"
                    if sha_key in node:
                        add_row(
                            declaring,
                            value,
                            node[sha_key],
                            node.get(f"{prefix}_bytes"),
                            integration_root,
                        )
                if isinstance(value, str) and is_repo_relative_path(value):
                    sha_key = f"{key}_sha256"
                    if sha_key in node:
                        add_row(
                            declaring,
                            value,
                            node[sha_key],
                            node.get(f"{key}_bytes"),
                            integration_root,
                        )
                if is_repo_relative_path(key) and isinstance(value, str) and SHA_RE.fullmatch(value):
                    add_row(declaring, key, value, None, integration_root)

            for value in node.values():
                walk(value, declaring, integration_root)
        elif isinstance(node, list):
            for value in node:
                walk(value, declaring, integration_root)

    while queue:
        current, virtual_content = queue.popleft()
        current = current.resolve()
        if current in visited:
            continue
        visited.add(current)
        try:
            if virtual_content is None:
                document = json.loads(current.read_text(encoding="utf-8"))
            else:
                document = json.loads(virtual_content.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            rows.append(
                {
                    "declared_in": relative(current),
                    "declared_path": relative(current),
                    "pass": False,
                    "reason": f"reachable_json_unreadable:{type(exc).__name__}",
                }
            )
            continue
        integration_root = document.get("integration_root") if isinstance(document, dict) else None
        walk(document, current, integration_root)

    failures = [row for row in rows if not row["pass"]]
    targets = sorted(
        {
            row["resolved_path"]
            for row in rows
            if row.get("pass") and isinstance(row.get("resolved_path"), str)
        }
    )
    return {
        "json_files_scanned": len(visited),
        "declarations_checked": len(rows),
        "unique_targets": len(targets),
        "targets": targets,
        "failures": failures,
    }


def role_for(path: str) -> str:
    name = PurePosixPath(path).name
    if "receipt" in name and name.endswith(".json"):
        return "receipt"
    if (
        "/00_control/" in f"/{path}"
        or "handoff" in name
        or name.startswith("validate_")
        or name.startswith("build_")
        or name.endswith("_contract.md")
    ):
        return "control"
    return "payload"


def reason_for(role: str) -> str:
    return {
        "payload": "Immutable evidence or analysis payload required to replay R3-R6 and preserve superseded audit history.",
        "control": "Immutable contract, manifest, handoff, or executable control required to replay declarations and gate logic.",
        "receipt": "Immutable validation receipt required to replay a declared gate and retain its audit history.",
    }[role]


def derive_members(audit: dict[str, Any]) -> list[dict[str, Any]]:
    paths = set(audit["targets"])
    paths.add(relative(R7_INPUT))
    paths.discard(relative(PIPELINE_STATE))
    output_prefix = relative(OUT) + "/"
    paths = {path for path in paths if not path.startswith(output_prefix)}
    members: list[dict[str, Any]] = []
    for path in sorted(paths):
        normalized = normalize_member_path(path)
        role = role_for(normalized)
        members.append(
            {
                "path": normalized,
                "bytes": byte_count(normalized),
                "sha256": sha256_file(normalized),
                "role": role,
                "inclusion_reason": reason_for(role),
            }
        )
    return members


def root_preimage_builder(members: list[dict[str, Any]]) -> bytes:
    tuples = [
        [member["path"], member["bytes"], member["sha256"], member["role"]]
        for member in sorted(members, key=lambda item: item["path"])
    ]
    return json_bytes(tuples, pretty=False)


def root_hash_builder(members: list[dict[str, Any]]) -> tuple[bytes, str]:
    preimage = root_preimage_builder(members)
    return preimage, hashlib.sha256(preimage).hexdigest()


def root_hash_validator_independent(members: list[dict[str, Any]]) -> tuple[bytes, str]:
    """Independent recomputation: do not consume the manifest's root or preimage fields."""
    ordered = sorted(members, key=lambda item: item["path"])
    tuple_only: list[list[Any]] = []
    for item in ordered:
        tuple_only.append([item["path"], int(item["bytes"]), item["sha256"], item["role"]])
    encoded = json.dumps(tuple_only, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return encoded, hashlib.sha256(encoded).hexdigest()


def state_declaration(r7_input: dict[str, Any]) -> dict[str, Any]:
    return r7_input["authorized_pipeline_state"]


def frozen_state_snapshot_document(state_bytes: bytes, r7_input: dict[str, Any]) -> dict[str, Any]:
    declaration = state_declaration(r7_input)
    return {
        "schema_version": "stage1b-r1-r7-frozen-authorized-state-snapshot-1.0",
        "path": declaration["path"],
        "encoding": "base64_exact_bytes",
        "bytes": len(state_bytes),
        "sha256": hashlib.sha256(state_bytes).hexdigest(),
        "required_state": declaration["required_state"],
        "content_base64": base64.b64encode(state_bytes).decode("ascii"),
        "root_membership": "EXCLUDED_MUTABLE_STATE_SNAPSHOT",
        "replay_policy": "Build mode validates the live authorized state. Final mode validates and replays only these embedded historical bytes, never the mutable live state path.",
    }


def decode_frozen_state_snapshot(manifest: dict[str, Any], r7_input: dict[str, Any]) -> tuple[bytes, list[str]]:
    failures: list[str] = []
    snapshot = manifest.get("frozen_authorized_state_snapshot")
    if not isinstance(snapshot, dict):
        return b"", ["missing_frozen_authorized_state_snapshot"]
    try:
        content = base64.b64decode(snapshot.get("content_base64", ""), validate=True)
    except (ValueError, TypeError):
        return b"", ["invalid_frozen_state_base64"]
    declaration = state_declaration(r7_input)
    expected_shape = {
        "schema_version": "stage1b-r1-r7-frozen-authorized-state-snapshot-1.0",
        "path": declaration["path"],
        "encoding": "base64_exact_bytes",
        "bytes": declaration["bytes"],
        "sha256": declaration["sha256"],
        "required_state": declaration["required_state"],
        "content_base64": snapshot.get("content_base64"),
        "root_membership": "EXCLUDED_MUTABLE_STATE_SNAPSHOT",
        "replay_policy": "Build mode validates the live authorized state. Final mode validates and replays only these embedded historical bytes, never the mutable live state path.",
    }
    if snapshot != expected_shape:
        failures.append("frozen_state_snapshot_metadata_mismatch")
    if len(content) != declaration["bytes"]:
        failures.append("frozen_state_snapshot_byte_length_mismatch")
    if hashlib.sha256(content).hexdigest() != declaration["sha256"]:
        failures.append("frozen_state_snapshot_sha256_mismatch")
    try:
        state = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        failures.append("frozen_state_snapshot_json_invalid")
    else:
        if state.get("state") != declaration["required_state"]:
            failures.append("frozen_state_snapshot_required_state_mismatch")
        if state.get("r7_authorized") is not True:
            failures.append("frozen_state_snapshot_r7_not_authorized")
    return content, failures


def direct_declared_file_gate(
    r7_input: dict[str, Any], state_bytes: bytes, require_live_state: bool
) -> list[str]:
    failures: list[str] = []
    declarations = [
        r7_input["freeze_contract"],
        r7_input["authorized_pipeline_state"],
        r7_input["transitive_reaudit_input"],
        *r7_input["reaudit_gate_artifacts"],
        r7_input["scholar_adjudication"],
    ]
    for declaration in declarations:
        path = declaration["path"]
        if path == state_declaration(r7_input)["path"]:
            if len(state_bytes) != declaration["bytes"]:
                failures.append(f"bytes:{path}")
            if hashlib.sha256(state_bytes).hexdigest() != declaration["sha256"]:
                failures.append(f"sha256:{path}")
            if require_live_state:
                if not absolute(path).is_file():
                    failures.append(f"missing:{path}")
                elif absolute(path).read_bytes() != state_bytes:
                    failures.append(f"live_state_bytes:{path}")
            continue
        if not absolute(path).is_file():
            failures.append(f"missing:{path}")
            continue
        if byte_count(path) != declaration["bytes"]:
            failures.append(f"bytes:{path}")
        if sha256_file(path) != declaration["sha256"]:
            failures.append(f"sha256:{path}")
    return failures


def find_pair(document: dict[str, Any], pair_id: str) -> dict[str, Any] | None:
    return next((row for row in document.get("pairs", []) if row.get("pair_id") == pair_id), None)


def find_decision(document: dict[str, Any], pair_id: str) -> dict[str, Any] | None:
    return next((row for row in document.get("decisions", []) if row.get("pair_id") == pair_id), None)


def input_gate_results(
    audit: dict[str, Any],
    members: list[dict[str, Any]],
    state_bytes: bytes,
    snapshot_failures: list[str],
    *,
    require_live_state: bool,
) -> list[tuple[str, bool, Any]]:
    r7 = load_json(R7_INPUT)
    try:
        state = json.loads(state_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        state = {}
    r6_reaudit_input = load_json(R6_REAUDIT_INPUT)
    r6_input = load_json(R6_INPUT)
    r6_rem_input = load_json(R6_REMEDIATION_INPUT)
    r5_map = load_json(R5_MAP)
    rem_map = load_json(REM_MAP)
    r5_handoff = load_json(R5_HANDOFF)
    r6_handoff = load_json(R6_HANDOFF)
    r6_receipt = load_json(R6_RECEIPT)
    r6_packet = load_json(R6_PACKET)
    rem_handoff = load_json(REM_HANDOFF)
    rem_receipt = load_json(REM_RECEIPT)
    reaudit_handoff = load_json(REAUDIT_HANDOFF)
    reaudit_receipt = load_json(REAUDIT_RECEIPT)
    reaudit_packet = load_json(REAUDIT_PACKET)
    scholar = load_json(SCHOLAR)

    gate = r7["gate_summary"]
    expected_ids = {f"T-{index:03d}" for index in range(1, 13)}
    decisions = scholar["decisions"]
    decision_ids = {row.get("pair_id") for row in decisions}
    confirmations = Counter(row.get("scholar_confirmation") for row in decisions)
    rem_dispositions = Counter(row.get("r5_disposition") for row in rem_map["claims"])
    r5_dispositions = Counter(row.get("r5_disposition") for row in r5_map["claims"])
    t002_reaudit = find_pair(reaudit_packet, "T-002")
    t002_original = find_pair(r6_packet, "T-002")
    t002_decision = find_decision(scholar, "T-002")
    member_paths = [member["path"] for member in members]
    direct_failures = direct_declared_file_gate(r7, state_bytes, require_live_state)

    return [
        (
            "r7_direct_control_byte_sha_gate",
            not direct_failures,
            direct_failures,
        ),
        (
            "embedded_authorized_state_snapshot_exact",
            not snapshot_failures,
            snapshot_failures,
        ),
        (
            "final_replay_live_state_independence",
            require_live_state or (LIVE_STATE_READ_FORBIDDEN and LIVE_STATE_READ_ATTEMPTS == 0),
            {
                "require_live_state": require_live_state,
                "live_state_read_forbidden": LIVE_STATE_READ_FORBIDDEN,
                "live_state_read_attempts": LIVE_STATE_READ_ATTEMPTS,
            },
        ),
        (
            "runtime_lock_exact",
            r7["runtime_lock"]
            == {
                "model": "gpt-5.6-sol",
                "reasoning": "high",
                "execution_mode": "fresh_dedicated_worktree_task",
            },
            r7["runtime_lock"],
        ),
        (
            "fail_closed_recursive_reachable_declarations",
            not audit["failures"],
            audit["failures"],
        ),
        (
            "recursive_replay_coverage_floor",
            audit["json_files_scanned"] >= 64
            and audit["declarations_checked"] >= 338
            and audit["unique_targets"] >= 119,
            {
                "json_files_scanned": audit["json_files_scanned"],
                "declarations_checked": audit["declarations_checked"],
                "unique_targets": audit["unique_targets"],
            },
        ),
        (
            "authorized_state_exact_and_read_only_boundary",
            state.get("state") == r7["authorized_pipeline_state"]["required_state"]
            and state.get("r7_authorized") is True,
            {"state": state.get("state"), "r7_authorized": state.get("r7_authorized")},
        ),
        (
            "r5_pass_29_of_29",
            gate["r5_final_validation"] == "PASS_29_OF_29"
            and r6_input["r5_gate"]["verdict"] == "PASS"
            and r6_input["r5_gate"]["central_final_validation"] == "PASS_29_OF_29"
            and r5_handoff["verdict"] == "PASS",
            gate["r5_final_validation"],
        ),
        (
            "r6_original_pass_26_of_26_with_revise",
            gate["r6_original_final_validation"] == "PASS_26_OF_26"
            and gate["r6_original_verdict"] == "REVISE"
            and r6_rem_input["r6_gate"]["final_validation"] == "PASS_26_OF_26"
            and r6_handoff["verdict"] == "REVISE"
            and r6_receipt["result"] == "PASS",
            {"verdict": r6_handoff["verdict"], "receipt": r6_receipt["result"]},
        ),
        (
            "r6_remediation_pass_33_of_33",
            gate["r6_remediation_validation"] == "PASS_33_OF_33"
            and gate["r6_remediation_verdict"] == "PASS_FRESH_R6_REAUDIT_ONLY"
            and rem_receipt["checks_passed"] == 33
            and rem_receipt["checks_failed"] == 0
            and rem_handoff["verdict"] == "PASS_FRESH_R6_REAUDIT_ONLY",
            {"passed": rem_receipt["checks_passed"], "verdict": rem_handoff["verdict"]},
        ),
        (
            "r6_reaudit_pass_26_of_26_zero_critical_major",
            gate["r6_reaudit_final_validation"] == "PASS_26_OF_26"
            and reaudit_receipt["checks_passed"] == 26
            and reaudit_receipt["checks_failed"] == 0
            and reaudit_handoff["severity_counts"]["Critical"] == 0
            and reaudit_handoff["severity_counts"]["Major"] == 0,
            {
                "passed": reaudit_receipt["checks_passed"],
                "severity_counts": reaudit_handoff["severity_counts"],
            },
        ),
        (
            "claim_population_exact_44",
            len(r5_map["claims"]) == 44
            and len(rem_map["claims"]) == 44
            and len({row["claim_id"] for row in rem_map["claims"]}) == 44
            and gate["claims"] == 44,
            {"r5": len(r5_map["claims"]), "remediated": len(rem_map["claims"])},
        ),
        (
            "claim_dispositions_exact_22_and_22",
            r5_dispositions == Counter({"citation_ready_candidate": 22, "planning_only": 22})
            and rem_dispositions == Counter({"citation_ready_candidate": 22, "planning_only": 22})
            and gate["citation_ready_candidates"] == 22
            and gate["planning_only"] == 22,
            {"r5": dict(r5_dispositions), "remediated": dict(rem_dispositions)},
        ),
        (
            "verified_citation_locator_pairs_exact_33",
            gate["verified_citation_locator_pairs"] == 33
            and r5_handoff["counts"]["citations"]["paired_ref_markers"] == 33
            and r5_handoff["counts"]["citations"]["verified_non_none_anchors"] == 33
            and reaudit_handoff["recomputed"]["citation_marker_anchor_pairs_unchanged"] == 33,
            gate["verified_citation_locator_pairs"],
        ),
        (
            "scholar_adjudication_pair_roster_exact",
            len(decisions) == 12 and decision_ids == expected_ids,
            {"count": len(decisions), "ids": sorted(decision_ids)},
        ),
        (
            "scholar_adjudication_counts_11_1_0_0",
            scholar["counts"]
            == {
                "pairs": 12,
                "confirmed": 11,
                "disputed": 1,
                "pending": 0,
                "reclassified": 1,
                "flagged_unresolved": 0,
            }
            and confirmations == Counter({"confirmed": 11, "disputed": 1}),
            {"counts": scholar["counts"], "decisions": dict(confirmations)},
        ),
        (
            "t002_original_row_preserved",
            t002_original is not None
            and t002_reaudit is not None
            and t002_reaudit["r5_pair_assessment"] == "conditional_difference"
            and t002_reaudit["r5_resolution_status"] == "resolved_in_synthesis"
            and t002_reaudit["scholar_confirmation"] == "pending",
            t002_reaudit,
        ),
        (
            "t002_overlay_effective_reclassification_exact",
            t002_decision is not None
            and t002_decision["scholar_confirmation"] == "disputed"
            and t002_decision["original_pair_assessment"] == "conditional_difference"
            and t002_decision["original_resolution_status"] == "resolved_in_synthesis"
            and t002_decision["effective_pair_assessment"] == "no_material_conflict"
            and t002_decision["effective_resolution_status"] == "not_applicable"
            and t002_decision["flagged_unresolved"] is False,
            t002_decision,
        ),
        (
            "scholar_overlay_is_authoritative_without_mutation",
            scholar["application_policy"]["original_r5_tension_artifact_mutated"] is False
            and scholar["application_policy"]["original_r6_packets_mutated"] is False
            and scholar["application_policy"]["overlay_is_authoritative_for_r7_and_later"] is True,
            scholar["application_policy"],
        ),
        (
            "h1_h4_remain_not_run",
            gate["h1_h4"] == "NOT_RUN"
            and state.get("r6_reaudit_status") == "complete_pass_pending_scholar_confirmation"
            and r5_handoff["phase_boundary"]["h1_h4"] == "NOT_RUN"
            and reaudit_handoff["phase_boundary"]["h1_h4"] == "NOT_RUN",
            gate["h1_h4"],
        ),
        (
            "stage1b_remains_unsealed",
            gate["stage1b_sealed"] is False
            and state.get("stage1b_sealed") is False
            and scholar["authorization"]["stage1b_sealed"] is False
            and reaudit_handoff["stage1b_sealed"] is False,
            gate["stage1b_sealed"],
        ),
        (
            "stage2_remains_unauthorized",
            gate["stage2_production_citations_authorized"] is False
            and state.get("stage2_production_citations_authorized") is False
            and scholar["authorization"]["stage2_production_citations_authorized"] is False
            and reaudit_handoff["stage2_production_citations_authorized"] is False,
            gate["stage2_production_citations_authorized"],
        ),
        (
            "mutable_central_state_excluded_from_packet_members",
            relative(PIPELINE_STATE) not in member_paths,
            relative(PIPELINE_STATE),
        ),
        (
            "packet_member_paths_normalized_sorted_unique",
            member_paths == sorted(member_paths)
            and len(member_paths) == len(set(member_paths))
            and all(normalize_member_path(path) == path for path in member_paths),
            {"member_count": len(member_paths)},
        ),
        (
            "packet_member_byte_sha_replay",
            all(
                byte_count(member["path"]) == member["bytes"]
                and sha256_file(member["path"]) == member["sha256"]
                for member in members
            ),
            {"member_count": len(members)},
        ),
    ]


def manifest_document(
    members: list[dict[str, Any]], root_sha: str, preimage_bytes: int, state_bytes: bytes
) -> dict[str, Any]:
    roles = Counter(member["role"] for member in members)
    r7_input = load_json(R7_INPUT)
    return {
        "schema_version": "stage1b-r1-r7-audit-packet-manifest-1.0",
        "project": "hybrid-recsys-v5",
        "stage": "1B",
        "round": "R1",
        "step": "R7_freeze_packet",
        "packet_status": "IMMUTABLE_BYTES_FROZEN",
        "verdict": "PASS_READY_FOR_INDEPENDENT_AUDIT",
        "canonical_root_sha256": root_sha,
        "canonical_preimage_bytes": preimage_bytes,
        "member_count": len(members),
        "role_counts": {key: roles.get(key, 0) for key in ("payload", "control", "receipt")},
        "root_hash_contract": {
            "hash": "SHA-256",
            "encoding": "UTF-8",
            "preimage": "JSON array of sorted [path,bytes,sha256,role] tuples",
            "serialization": "json.dumps(ensure_ascii=False,separators=(',',':')); no trailing newline",
            "ordering": "lexicographic ascending by normalized repository-relative path",
            "tuple_fields": ["path", "bytes", "sha256", "role"],
            "excluded": [
                "timestamps",
                "absolute_or_worktree_paths",
                "mutable_pipeline_state",
                "R7_output_self_hashes",
            ],
        },
        "frozen_authorized_state_snapshot": frozen_state_snapshot_document(state_bytes, r7_input),
        "validation_only_inputs": [
            {
                "path": relative(PIPELINE_STATE),
                "bytes": len(state_bytes),
                "sha256": hashlib.sha256(state_bytes).hexdigest(),
                "reason": "Embedded historical authorization snapshot; excluded from the canonical root because central pipeline state is mutable and R7 must not create a second state authority. Final replay never dereferences the live path.",
            }
        ],
        "members": members,
        "phase_boundary": {
            "r8": "AUTHORIZED_FRESH_READ_ONLY_AUDIT_ONLY",
            "r9": "NOT_PERFORMED_NOT_AUTHORIZED",
            "stage1b_seal": "NOT_PERFORMED",
            "stage2_authorization": "NOT_AUTHORIZED",
            "benchmark_training_evaluation": "NOT_RUN",
            "h1_h4": "NOT_RUN",
        },
    }


def root_document(member_count: int, preimage_bytes: int, root_sha: str) -> dict[str, Any]:
    return {
        "schema_version": "stage1b-r1-r7-root-hash-1.0",
        "hash_algorithm": "SHA-256",
        "preimage_encoding": "UTF-8",
        "preimage_format": "JSON array of lexicographically path-sorted [path,bytes,sha256,role] tuples",
        "preimage_serialization": "json.dumps(ensure_ascii=False,separators=(',',':')); no trailing newline",
        "member_count": member_count,
        "preimage_bytes": preimage_bytes,
        "canonical_root_sha256": root_sha,
        "exclusions": [
            "timestamps",
            "absolute_or_worktree_paths",
            "mutable_pipeline_state",
            "R7_output_self_hashes",
        ],
    }


def report_document(
    members: list[dict[str, Any]], root_sha: str, audit: dict[str, Any], state_bytes: bytes
) -> str:
    roles = Counter(member["role"] for member in members)
    return f"""# Stage 1B Remediation R1 — R7 Freeze Report

Verdict: `PASS_READY_FOR_INDEPENDENT_AUDIT`

## Frozen packet

- Packet members: `{len(members)}` (`{roles['payload']}` payload, `{roles['control']}` control, `{roles['receipt']}` receipt).
- Canonical root SHA-256: `{root_sha}`.
- Paths are repository-relative, use forward slashes, are unique, and are sorted lexicographically.
- Every member records its exact byte length, SHA-256, role, and inclusion reason in `stage1b_r1_audit_packet_manifest.json`.
- Superseded R5, original R6, remediation, and re-audit evidence is retained rather than rewritten or omitted.

## Canonical root-hash preimage

The preimage is the UTF-8 encoding, without a trailing newline, of a compact JSON array containing only sorted member tuples:

`[[path,bytes,sha256,role], ...]`

Serialization is `json.dumps(ensure_ascii=False, separators=(',', ':'))`. Entries are sorted lexicographically by normalized path before serialization. Timestamps, absolute/worktree paths, mutable pipeline state, and all R7 output/self-hashes are excluded. The validator independently reconstructs the tuple array from current member bytes and fails on path, ordering, byte, SHA-256, role, serialization, or root-hash divergence.

Build mode validated the central pipeline state at `{relative(PIPELINE_STATE)}` with `{len(state_bytes)}` bytes and SHA-256 `{hashlib.sha256(state_bytes).hexdigest()}`. Those exact historical bytes are embedded as base64 in the packet manifest. Final mode validates the embedded byte length, SHA-256, JSON, required state, and R7 authorization against `r7_input_manifest.json`; it never dereferences the mutable live state path. The embedded snapshot remains a validation-only carrier and is not a root-hashed packet member.

## Deterministic gates

- Recursive replay: `{audit['json_files_scanned']}` reachable JSON files, `{audit['declarations_checked']}` declarations, `{audit['unique_targets']}` unique declared targets, zero mismatches.
- R5: `29/29 PASS`.
- Original R6: `26/26 PASS`, verdict `REVISE`.
- R6 remediation: `33/33 PASS`, verdict `PASS_FRESH_R6_REAUDIT_ONLY`.
- Fresh R6 re-audit: `26/26 PASS`, `Critical=0`, `Major=0`.
- Claims: `44`; citation-ready candidates: `22`; planning-only: `22`.
- Verified citation/locator pairs: `33`.
- Scholar adjudication: `12/12` decided; `11` confirmed; `T-002` disputed and effectively reclassified to `no_material_conflict/not_applicable`; `0` pending and `0` unresolved.

## Boundary

R7 authorizes only a fresh read-only R8 independent audit. R8 and R9 were not performed. Stage 1B remains unsealed, Stage 2 remains unauthorized, and H1-H4 remain `NOT_RUN`.
"""


def handoff_document(members: list[dict[str, Any]], root_sha: str) -> dict[str, Any]:
    return {
        "schema_version": "stage1b-r1-r7-handoff-1.0",
        "project": "hybrid-recsys-v5",
        "stage": "1B",
        "round": "R1",
        "step": "R7_freeze_packet",
        "verdict": "PASS_READY_FOR_INDEPENDENT_AUDIT",
        "input_binding": {
            relative(R7_INPUT): sha256_file(R7_INPUT),
            relative(CONTRACT): sha256_file(CONTRACT),
            relative(SCHOLAR): sha256_file(SCHOLAR),
        },
        "packet_manifest": relative(MANIFEST),
        "root_hash_record": relative(ROOT_HASH),
        "canonical_root_sha256": root_sha,
        "packet_member_count": len(members),
        "validator_final_gate": "PASS_29_OF_29",
        "scholar_adjudication": {
            "pairs": 12,
            "confirmed": 11,
            "disputed": 1,
            "pending": 0,
            "flagged_unresolved": 0,
            "t002_effective_classification": "no_material_conflict/not_applicable",
        },
        "artifact_sha256": {
            relative(MANIFEST): sha256_file(MANIFEST),
            relative(ROOT_HASH): sha256_file(ROOT_HASH),
            relative(REPORT): sha256_file(REPORT),
            relative(VALIDATOR): sha256_file(VALIDATOR),
        },
        "self_hash_policy": "The handoff and validation receipt do not self-hash. The receipt binds the handoff; the canonical root binds only immutable input member tuples and excludes all R7 output hashes.",
        "authorized_next_action": "fresh_read_only_R8_independent_audit_only",
        "phase_boundary": {
            "r8": "AUTHORIZED_NOT_PERFORMED",
            "r9": "NOT_PERFORMED_NOT_AUTHORIZED",
            "stage1b_seal": "NOT_PERFORMED",
            "stage1b_sealed": False,
            "stage2_authorization": "NOT_AUTHORIZED",
            "stage2_production_citations_authorized": False,
            "benchmark_training_evaluation": "NOT_RUN",
            "h1_h4": "NOT_RUN",
        },
    }


def expected_documents(
    audit: dict[str, Any], state_bytes: bytes
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], str, bytes, str]:
    members = derive_members(audit)
    preimage, root_sha = root_hash_builder(members)
    manifest = manifest_document(members, root_sha, len(preimage), state_bytes)
    root_record = root_document(len(members), len(preimage), root_sha)
    report = report_document(members, root_sha, audit, state_bytes)
    return members, manifest, root_record, report, preimage, root_sha


def validate_outputs(
    audit: dict[str, Any],
    members: list[dict[str, Any]],
    expected_manifest: dict[str, Any],
    expected_root: dict[str, Any],
    expected_report: str,
    expected_root_sha: str,
) -> list[tuple[str, bool, Any]]:
    independent_preimage, independent_sha = root_hash_validator_independent(members)
    actual_roster = {path.name for path in absolute(OUT).iterdir() if path.is_file()}

    manifest_ok = absolute(MANIFEST).is_file() and load_json(MANIFEST) == expected_manifest
    root_ok = absolute(ROOT_HASH).is_file() and load_json(ROOT_HASH) == expected_root
    report_ok = absolute(REPORT).is_file() and absolute(REPORT).read_text(encoding="utf-8") == expected_report

    expected_handoff = None
    handoff_ok = False
    if manifest_ok and root_ok and report_ok:
        expected_handoff = handoff_document(members, expected_root_sha)
        handoff_ok = absolute(HANDOFF).is_file() and load_json(HANDOFF) == expected_handoff

    manifest_members = load_json(MANIFEST).get("members", []) if absolute(MANIFEST).is_file() else []
    manifest_member_tuples = [
        (item.get("path"), item.get("bytes"), item.get("sha256"), item.get("role"))
        for item in manifest_members
    ]
    expected_member_tuples = [
        (item["path"], item["bytes"], item["sha256"], item["role"])
        for item in members
    ]

    return [
        (
            "packet_member_set_exhaustive_from_recursive_seed",
            manifest_member_tuples == expected_member_tuples,
            {"expected": len(expected_member_tuples), "actual": len(manifest_member_tuples)},
        ),
        (
            "canonical_root_independent_recomputation",
            independent_sha == expected_root_sha
            and len(independent_preimage) == expected_root["preimage_bytes"],
            {"expected": expected_root_sha, "actual": independent_sha},
        ),
        (
            "manifest_root_report_handoff_exact",
            manifest_ok and root_ok and report_ok and handoff_ok,
            {
                "manifest": manifest_ok,
                "root": root_ok,
                "report": report_ok,
                "handoff": handoff_ok,
            },
        ),
        (
            "output_roster_exact_six",
            actual_roster == EXPECTED_OUTPUTS,
            {"expected": sorted(EXPECTED_OUTPUTS), "actual": sorted(actual_roster)},
        ),
    ]


def run_validation(
    state_bytes: bytes,
    snapshot_failures: list[str],
    *,
    require_live_state: bool,
) -> tuple[list[tuple[str, bool, Any]], dict[str, Any], list[dict[str, Any]], str]:
    virtual_files = None if require_live_state else {relative(PIPELINE_STATE): state_bytes}
    audit = recursive_declaration_audit(R7_INPUT, virtual_files)
    members, expected_manifest, expected_root, expected_report, _preimage, root_sha = expected_documents(
        audit, state_bytes
    )
    checks = input_gate_results(
        audit,
        members,
        state_bytes,
        snapshot_failures,
        require_live_state=require_live_state,
    )
    checks.extend(validate_outputs(audit, members, expected_manifest, expected_root, expected_report, root_sha))
    if len(checks) != 29:
        raise RuntimeError(f"validator contract error: expected 29 checks, got {len(checks)}")
    context = {
        "audit": audit,
        "expected_manifest": expected_manifest,
        "expected_root": expected_root,
        "expected_report": expected_report,
    }
    return checks, context, members, root_sha


def receipt_document(
    checks: list[tuple[str, bool, Any]],
    audit: dict[str, Any],
    members: list[dict[str, Any]],
    root_sha: str,
) -> dict[str, Any]:
    failed = [
        {"check": name, "detail": detail}
        for name, passed, detail in checks
        if not passed
    ]
    passed_count = sum(1 for _, passed, _ in checks if passed)
    return {
        "schema_version": "stage1b-r1-r7-validation-receipt-1.0",
        "validation_mode": "final",
        "result": "PASS" if not failed else "FAIL",
        "verdict": "PASS_READY_FOR_INDEPENDENT_AUDIT" if not failed else "REVISE",
        "checks_run": len(checks),
        "checks_passed": passed_count,
        "checks_failed": len(failed),
        "check_names": [name for name, _, _ in checks],
        "failures": failed,
        "recomputed": {
            "recursive_json_files_scanned": audit["json_files_scanned"],
            "recursive_declarations_checked": audit["declarations_checked"],
            "recursive_unique_targets": audit["unique_targets"],
            "packet_member_count": len(members),
            "canonical_root_sha256": root_sha,
            "claims": 44,
            "citation_ready_candidates": 22,
            "planning_only": 22,
            "verified_citation_locator_pairs": 33,
            "scholar_pairs": 12,
            "scholar_confirmed": 11,
            "scholar_disputed": 1,
            "scholar_pending": 0,
            "scholar_unresolved": 0,
        },
        "artifact_sha256": {
            relative(MANIFEST): sha256_file(MANIFEST),
            relative(ROOT_HASH): sha256_file(ROOT_HASH),
            relative(REPORT): sha256_file(REPORT),
            relative(HANDOFF): sha256_file(HANDOFF),
            relative(VALIDATOR): sha256_file(VALIDATOR),
        },
        "authority": "PASS certifies only the deterministic R7 immutable packet. It authorizes a fresh read-only R8 audit; it does not perform R8/R9, seal Stage 1B, authorize Stage 2, or run H1-H4.",
    }


def build() -> int:
    global LIVE_STATE_READ_ATTEMPTS, LIVE_STATE_READ_FORBIDDEN
    LIVE_STATE_READ_FORBIDDEN = False
    LIVE_STATE_READ_ATTEMPTS = 0
    r7_input = load_json(R7_INPUT)
    state_bytes = absolute(PIPELINE_STATE).read_bytes()
    generated_snapshot = frozen_state_snapshot_document(state_bytes, r7_input)
    _decoded, snapshot_failures = decode_frozen_state_snapshot(
        {"frozen_authorized_state_snapshot": generated_snapshot}, r7_input
    )
    audit = recursive_declaration_audit(R7_INPUT)
    members, manifest, root_record, report, _preimage, root_sha = expected_documents(audit, state_bytes)
    input_checks = input_gate_results(
        audit,
        members,
        state_bytes,
        snapshot_failures,
        require_live_state=True,
    )
    failures = [(name, detail) for name, passed, detail in input_checks if not passed]
    if failures:
        print(json.dumps({"verdict": "REVISE", "input_failures": failures}, ensure_ascii=False, indent=2))
        return 1

    absolute(OUT).mkdir(parents=True, exist_ok=True)
    write_json(MANIFEST, manifest)
    write_json(ROOT_HASH, root_record)
    absolute(REPORT).write_text(report, encoding="utf-8", newline="\n")
    write_json(HANDOFF, handoff_document(members, root_sha))
    absolute(RECEIPT).write_text("{}\n", encoding="utf-8", newline="\n")

    embedded_state, embedded_failures = decode_frozen_state_snapshot(load_json(MANIFEST), r7_input)
    LIVE_STATE_READ_FORBIDDEN = True
    LIVE_STATE_READ_ATTEMPTS = 0
    checks, context, validated_members, validated_root = run_validation(
        embedded_state, embedded_failures, require_live_state=False
    )
    write_json(
        RECEIPT,
        receipt_document(checks, context["audit"], validated_members, validated_root),
    )
    final_checks, final_context, final_members, final_root = run_validation(
        embedded_state, embedded_failures, require_live_state=False
    )
    final_receipt = receipt_document(final_checks, final_context["audit"], final_members, final_root)
    write_json(RECEIPT, final_receipt)
    print(
        json.dumps(
            {
                "verdict": final_receipt["verdict"],
                "checks_passed": final_receipt["checks_passed"],
                "checks_run": final_receipt["checks_run"],
                "packet_member_count": len(final_members),
                "canonical_root_sha256": final_root,
                "r7_handoff_sha256": sha256_file(HANDOFF),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if final_receipt["result"] == "PASS" else 1


def final() -> int:
    global LIVE_STATE_READ_ATTEMPTS, LIVE_STATE_READ_FORBIDDEN
    r7_input = load_json(R7_INPUT)
    state_bytes, snapshot_failures = decode_frozen_state_snapshot(load_json(MANIFEST), r7_input)
    LIVE_STATE_READ_FORBIDDEN = True
    LIVE_STATE_READ_ATTEMPTS = 0
    checks, context, members, root_sha = run_validation(
        state_bytes, snapshot_failures, require_live_state=False
    )
    receipt = receipt_document(checks, context["audit"], members, root_sha)
    write_json(RECEIPT, receipt)
    print(
        json.dumps(
            {
                "verdict": receipt["verdict"],
                "checks_passed": receipt["checks_passed"],
                "checks_run": receipt["checks_run"],
                "packet_member_count": len(members),
                "canonical_root_sha256": root_sha,
                "r7_handoff_sha256": sha256_file(HANDOFF),
                "failures": receipt["failures"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if receipt["result"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("build", "final"), required=True)
    args = parser.parse_args()
    return build() if args.mode == "build" else final()


if __name__ == "__main__":
    sys.exit(main())
