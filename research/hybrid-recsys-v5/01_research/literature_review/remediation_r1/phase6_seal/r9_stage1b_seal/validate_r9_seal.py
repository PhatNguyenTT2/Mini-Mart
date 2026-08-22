#!/usr/bin/env python3
"""Read-only deterministic validator for the Stage 1B R1 R9 seal bundle."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
BASE = Path("research/hybrid-recsys-v5/01_research/literature_review/remediation_r1")
CONTROL = BASE / "00_control"
R7 = BASE / "phase4_freeze/r7_packet_r1"
R8 = BASE / "phase5_audit/r8_independent_audit"
OUT = BASE / "phase6_seal/r9_stage1b_seal"

R9_INPUT = CONTROL / "r9_input_manifest.json"
R7_HANDOFF = R7 / "r7_handoff.json"
R7_MANIFEST = R7 / "stage1b_r1_audit_packet_manifest.json"
R7_ROOT = R7 / "stage1b_r1_root_hash.json"
R8_HANDOFF = R8 / "r8_handoff.json"
R8_FINDINGS = R8 / "r8_findings.json"
R8_RECEIPT = R8 / "r8_validation_receipt.json"
SCHOLAR = CONTROL / "scholar_tension_adjudication_r1.json"
V0_FINDINGS = Path("research/hybrid-recsys-v5/01_research/literature_review/audit/audit_findings.json")
V0_VERDICT = Path("research/hybrid-recsys-v5/01_research/literature_review/audit/audit_verdict.json")

SEAL_MANIFEST = OUT / "stage1b_r1_seal_manifest.json"
STAGE2_HANDOFF = OUT / "stage2_literature_handoff.json"
REPORT = OUT / "r9_seal_report.md"
RECEIPT = OUT / "r9_validation_receipt.json"
R9_HANDOFF = OUT / "r9_handoff.json"
VALIDATOR = OUT / "validate_r9_seal.py"

EXPECTED_OUTPUTS = {
    SEAL_MANIFEST.name,
    STAGE2_HANDOFF.name,
    REPORT.name,
    RECEIPT.name,
    R9_HANDOFF.name,
    VALIDATOR.name,
}
EXPECTED_ROOT = "f0f2d56e42ce0f181f83182ddffe1060bf8994f50ababd4b0dbe563a942370dd"
EXPECTED_R9_INPUT_SHA = "fb3584574bba7f52f34eda4b6f82a72d4c5fe100a7436c39a166cce7ce568f13"
EXPECTED_R8_HANDOFF_SHA = "82cef8251e37702dc60b7a724f81f771b5bde61cf72e90b2f5ffae08e14f7800"
EXPECTED_SCHOLAR_SHA = "a9a9ccc008f119bd4e4923fbb580529390a4f6653c8d973c1487e70133a2df62"
EXPECTED_V0_FINDINGS_SHA = "52a754ee42ff8d00a6f10ec1f17429fcbfa0b83afa27dc9756656ee921b86520"
EXPECTED_V0_VERDICT_SHA = "d4d33b02e157c0fec44327951c0cf8e7dbcbb55561b2a432bdf497959ed8cf47"
EXPECTED_CLOSURES = {
    "ST1B-META-001",
    "ST1B-META-002",
    "ST1B-META-003",
    "ST1B-SCOPE-001",
    "ST1B-SYNTH-001",
    "ST1B-LOCATOR-001",
    "ST1B-ARS-001",
    "ST1B-RIGHTS-001",
}
EXPECTED_AUTHORIZED = [
    "L2-CLAIM-GRAPH-ZERO-EDGE-005",
    "L2-CLAIM-ITEMCF-BPR-001",
    "L2-CLAIM-NCF-DEEPFM-002",
    "L2-CLAIM-OBJECTIVE-006",
    "L2-CLAIM-RECENT-TOWER-CONTROLS-007",
    "L2-CLAIM-TWO-STAGE-003",
    "L2-CLAIM-WIDE-DEEP-004",
    "L3-APR-001",
    "L3-BTBR-005",
    "L3-HYB-006",
    "L3-NBR-004",
    "L3-PROTO-007",
    "L3-RULE-002",
    "L3-SEQ-003",
    "L4-CC-01",
    "L4-CC-02",
    "L4-CC-03",
    "L4-CC-04",
    "L4-CC-05",
    "L4-CC-06",
    "L4-CC-07",
    "L4-CC-08",
]
EXPECTED_PROHIBITED = [
    "C-L5-EXT-01",
    "C-L5-EXT-02",
    "C-L5-EXT-03",
    "C-L5-EXT-04",
    "C-L5-EXT-05",
    "C-L5-RIGHTS-01",
    "C-L5-SCOPE-01",
    "C-L5-VN-01",
    "C-L5-VN-02",
    "L1-CC-001",
    "L1-CC-002",
    "L1-CC-003",
    "L1-CC-004",
    "L1-CC-005",
    "L1-CC-006",
    "L1-CC-007",
    "L1-CC-008",
    "L1-CC-009",
    "L1-CC-010",
    "L1-CC-011",
    "L2-CLAIM-HARMONIZED-EVAL-008",
    "L3-GAP-008",
]


def absolute(path: Path | str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def load_json(path: Path | str) -> Any:
    return json.loads(absolute(path).read_text(encoding="utf-8"))


def sha256_file(path: Path | str) -> str:
    return hashlib.sha256(absolute(path).read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def normalized_repo_path(raw: str) -> bool:
    return (
        bool(raw)
        and "\\" not in raw
        and "://" not in raw
        and not Path(raw).is_absolute()
        and PurePosixPath(raw).as_posix() == raw
        and not raw.startswith("../")
        and "/../" not in raw
    )


def input_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        manifest["seal_contract"],
        *manifest["r8_control_bindings"],
        *manifest["frozen_r7_seal_base"],
        *manifest["frozen_r8_outputs"],
        manifest["scholar_adjudication"],
    ]


def pointer_map(r7_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["path"]: row for row in r7_manifest["members"]}


def recursively_contains_forbidden_preimage_surface(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if any(token in lowered for token in ("timestamp", "generated_at", "frozen_at", "path")):
                return True
            if key in {"seal_sha256", "r9_handoff_sha256", "output_sha256", "self_hash"}:
                return True
            if recursively_contains_forbidden_preimage_surface(child):
                return True
    elif isinstance(value, list):
        return any(recursively_contains_forbidden_preimage_surface(child) for child in value)
    elif isinstance(value, str):
        lowered = value.lower()
        if "research/" in lowered or "\\" in value or re.search(r"[a-z]:/", lowered):
            return True
        if re.search(r"\d{4}-\d{2}-\d{2}(?:t|$)", lowered):
            return True
    return False


def run_validation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, function: Callable[[], Any]) -> None:
        try:
            detail = function()
            checks.append({"name": name, "status": "PASS", "detail": detail})
        except Exception as exc:  # fail-closed aggregation
            checks.append({"name": name, "status": "FAIL", "detail": str(exc)})

    r9_input = load_json(R9_INPUT)
    r7_handoff = load_json(R7_HANDOFF)
    r7_manifest = load_json(R7_MANIFEST)
    r7_root = load_json(R7_ROOT)
    r8_handoff = load_json(R8_HANDOFF)
    r8_findings = load_json(R8_FINDINGS)
    r8_receipt = load_json(R8_RECEIPT)
    scholar = load_json(SCHOLAR)
    seal = load_json(SEAL_MANIFEST)
    stage2 = load_json(STAGE2_HANDOFF)
    handoff = load_json(R9_HANDOFF)
    receipt = load_json(RECEIPT)
    report = absolute(REPORT).read_text(encoding="utf-8")

    check("output_roster_exact_six", lambda: (
        require({p.name for p in absolute(OUT).iterdir() if p.is_file()} == EXPECTED_OUTPUTS, "output roster mismatch"),
        {"outputs": 6, "extra": [], "missing": []},
    )[-1])
    check("r9_input_manifest_sha256_exact", lambda: (
        require(sha256_file(R9_INPUT) == EXPECTED_R9_INPUT_SHA, "R9 input manifest SHA mismatch"),
        EXPECTED_R9_INPUT_SHA,
    )[-1])

    def direct_inputs() -> dict[str, Any]:
        rows = input_rows(r9_input)
        require(len(rows) == 13, "direct input count")
        for row in rows:
            require(normalized_repo_path(row["path"]), f"noncanonical path: {row['path']}")
            require(absolute(row["path"]).stat().st_size == row["bytes"], f"byte mismatch: {row['path']}")
            require(sha256_file(row["path"]) == row["sha256"], f"SHA mismatch: {row['path']}")
        return {"matched": 13, "declared": 13}

    check("direct_input_byte_sha_bindings_13_of_13", direct_inputs)
    check("runtime_lock_exact", lambda: (
        require(r9_input["runtime_lock"] == {"model": "gpt-5.6-sol", "reasoning": "high", "execution_mode": "dedicated_worktree_task"}, "runtime lock"),
        r9_input["runtime_lock"],
    )[-1])
    check("r7_handoff_gate_29_of_29", lambda: (
        require(r7_handoff["verdict"] == "PASS_READY_FOR_INDEPENDENT_AUDIT", "R7 verdict"),
        require(r7_handoff["validator_final_gate"] == "PASS_29_OF_29", "R7 check count"),
        {"verdict": r7_handoff["verdict"], "checks": 29},
    )[-1])
    check("r7_packet_member_count_193", lambda: (
        require(len(r7_manifest["members"]) == 193 == r7_handoff["packet_member_count"] == r7_root["member_count"], "R7 member count"),
        193,
    )[-1])

    def replay_r7_members() -> dict[str, Any]:
        for row in r7_manifest["members"]:
            require(absolute(row["path"]).stat().st_size == row["bytes"], f"R7 byte mismatch: {row['path']}")
            require(sha256_file(row["path"]) == row["sha256"], f"R7 SHA mismatch: {row['path']}")
        return {"replayed": 193, "mismatches": 0}

    check("r7_packet_byte_sha_replay_193_of_193", replay_r7_members)

    def replay_root() -> dict[str, Any]:
        rows = r7_manifest["members"]
        paths = [row["path"] for row in rows]
        require(paths == sorted(paths) and len(paths) == len(set(paths)), "R7 paths not sorted/unique")
        tuples = [[row["path"], row["bytes"], row["sha256"], row["role"]] for row in rows]
        preimage = json.dumps(tuples, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(preimage).hexdigest()
        require(len(preimage) == 43928, "R7 preimage bytes")
        require(digest == EXPECTED_ROOT == r7_root["canonical_root_sha256"] == r7_handoff["canonical_root_sha256"], "R7 root")
        return {"preimage_bytes": 43928, "sha256": digest}

    check("r7_canonical_root_replay", replay_root)
    check("r8_handoff_sha256_exact", lambda: (
        require(sha256_file(R8_HANDOFF) == EXPECTED_R8_HANDOFF_SHA, "R8 handoff SHA"),
        EXPECTED_R8_HANDOFF_SHA,
    )[-1])
    check("r8_gate_60_of_60", lambda: (
        require(r8_handoff["verdict"] == "PASS_READY_TO_SEAL", "R8 verdict"),
        require(r8_handoff["final_validation"] == "PASS_60_OF_60", "R8 handoff check count"),
        require(r8_receipt["checks_passed"] == 60 == r8_receipt["checks_run"] and r8_receipt["checks_failed"] == 0, "R8 receipt"),
        {"verdict": r8_handoff["verdict"], "checks": 60},
    )[-1])
    check("r8_zero_critical_major_minor", lambda: (
        require(r8_handoff["severity_counts"] == {"Critical": 0, "Major": 0, "Minor": 0, "Observation": 5}, "R8 severity"),
        r8_handoff["severity_counts"],
    )[-1])
    check("r8_observations_preserved_five", lambda: (
        require(len(r8_findings["findings"]) == 5 and all(row["severity"] == "Observation" for row in r8_findings["findings"]), "R8 observations"),
        [row["finding_id"] for row in r8_findings["findings"]],
    )[-1])
    check("scholar_adjudication_sha256_exact", lambda: (
        require(sha256_file(SCHOLAR) == EXPECTED_SCHOLAR_SHA, "scholar SHA"),
        EXPECTED_SCHOLAR_SHA,
    )[-1])
    check("scholar_adjudication_11_1_0_0", lambda: (
        require(scholar["counts"] == {"pairs": 12, "confirmed": 11, "disputed": 1, "pending": 0, "reclassified": 1, "flagged_unresolved": 0}, "scholar counts"),
        scholar["counts"],
    )[-1])
    check("t002_effective_reclassification", lambda: (
        require(next(row for row in scholar["decisions"] if row["pair_id"] == "T-002")["effective_pair_assessment"] == "no_material_conflict", "T-002 assessment"),
        require(next(row for row in scholar["decisions"] if row["pair_id"] == "T-002")["effective_resolution_status"] == "not_applicable", "T-002 resolution"),
        "no_material_conflict/not_applicable",
    )[-1])
    check("v0_findings_immutable_sha256", lambda: (
        require(sha256_file(V0_FINDINGS) == EXPECTED_V0_FINDINGS_SHA, "v0 findings SHA"),
        EXPECTED_V0_FINDINGS_SHA,
    )[-1])
    check("v0_verdict_fail_immutable_sha256", lambda: (
        require(sha256_file(V0_VERDICT) == EXPECTED_V0_VERDICT_SHA, "v0 verdict SHA"),
        require(load_json(V0_VERDICT)["verdict"] == "FAIL", "v0 verdict history"),
        EXPECTED_V0_VERDICT_SHA,
    )[-1])
    check("v0_original_findings_exact_eight", lambda: (
        require({row["id"] for row in load_json(V0_FINDINGS)["findings"]} == EXPECTED_CLOSURES, "v0 finding roster"),
        sorted(EXPECTED_CLOSURES),
    )[-1])

    members = pointer_map(r7_manifest)

    def closure_accounting() -> dict[str, Any]:
        closures = seal["original_audit_closures"]
        require(len(closures) == 8, "closure count")
        require({row["finding_id"] for row in closures} == EXPECTED_CLOSURES, "closure roster")
        for closure in closures:
            require(closure["status"] == "CLOSED_FOR_STAGE1B_R1", f"closure status: {closure['finding_id']}")
            require(closure["closure_basis"], f"empty closure basis: {closure['finding_id']}")
            require(closure["evidence"], f"empty evidence: {closure['finding_id']}")
            for evidence in closure["evidence"]:
                require(evidence["path"] in members, f"closure evidence not in R7 packet: {evidence['path']}")
                require(members[evidence["path"]]["sha256"] == evidence["sha256"], f"closure evidence SHA: {evidence['path']}")
        return {"closed": 8, "required": 8, "unaccounted": []}

    check("original_audit_closure_accounting_8_of_8", closure_accounting)
    check("v0_fail_supersession_boundary", lambda: (
        require(seal["history"]["v0_verdict"] == "FAIL", "v0 history"),
        require(seal["history"]["supersession_scope"] == "remediation R1 supersedes v0 only for Stage 1B completion", "supersession scope"),
        require(seal["history"]["v0_mutated"] is False, "v0 mutation flag"),
        seal["history"],
    )[-1])

    claim_path = stage2["claim_authority"]["path"]
    claim_map = load_json(claim_path)
    check("stage2_claim_authority_r7_bound", lambda: (
        require(claim_path in members, "claim authority absent from R7 packet"),
        require(stage2["claim_authority"]["sha256"] == members[claim_path]["sha256"], "claim authority SHA"),
        stage2["claim_authority"],
    )[-1])
    check("stage2_authorized_claims_exact_22", lambda: (
        require([row["claim_id"] for row in stage2["authorized_claims"]] == EXPECTED_AUTHORIZED, "authorized claim roster"),
        require([row["claim_id"] for row in claim_map["claims"] if row["r5_disposition"] == "citation_ready_candidate"] == EXPECTED_AUTHORIZED, "frozen authorized roster"),
        22,
    )[-1])
    check("stage2_planning_only_prohibited_exact_22", lambda: (
        require([row["claim_id"] for row in stage2["prohibited_claims"]] == EXPECTED_PROHIBITED, "prohibited claim roster"),
        require([row["claim_id"] for row in claim_map["claims"] if row["r5_disposition"] == "planning_only"] == EXPECTED_PROHIBITED, "frozen prohibited roster"),
        22,
    )[-1])
    check("stage2_claim_partition_44_disjoint", lambda: (
        require(set(EXPECTED_AUTHORIZED).isdisjoint(EXPECTED_PROHIBITED), "claim sets overlap"),
        require(set(EXPECTED_AUTHORIZED) | set(EXPECTED_PROHIBITED) == {row["claim_id"] for row in claim_map["claims"]}, "claim union"),
        44,
    )[-1])
    check("stage2_claim_pointers_exact", lambda: (
        require(all(row["pointer"] == f"/claims/{next(i for i, claim in enumerate(claim_map['claims']) if claim['claim_id'] == row['claim_id'])}" for row in stage2["authorized_claims"] + stage2["prohibited_claims"]), "claim pointer mismatch"),
        44,
    )[-1])

    def authority_artifacts() -> dict[str, Any]:
        rows = stage2["authority_artifacts"]
        required_roles = {
            "scholarly_corpus",
            "operational_resource_separation",
            "source_quality",
            "source_family_dependence",
            "claim_intent",
            "claim_source_map",
            "counter_evidence",
            "theme_denominators",
            "tension_overlay",
            "scholar_tension_packet",
            "bounded_synthesis",
            "locator_registry",
            "core_source_acquisition",
            "claim_acquisition",
            "rights_access",
        }
        require({row["role"] for row in rows} == required_roles, "authority role roster")
        for row in rows:
            require(row["path"] in members, f"authority path absent: {row['path']}")
            require(row["sha256"] == members[row["path"]]["sha256"], f"authority SHA: {row['path']}")
        return {"artifacts": len(rows), "roles": sorted(required_roles)}

    check("stage2_authority_artifacts_r7_bound", authority_artifacts)

    def citation_pairs() -> dict[str, Any]:
        synthesis_row = next(row for row in stage2["authority_artifacts"] if row["role"] == "bounded_synthesis")
        text = absolute(synthesis_row["path"]).read_text(encoding="utf-8")
        pairs = re.findall(r"<!--ref:([^>]+)--><!--anchor:([^>]+)-->", text)
        require(len(pairs) == 33, "visible citation/locator pair count")
        require(all(anchor and anchor != "none" and not anchor.startswith("page:") for _, anchor in pairs), "non-none non-page locator boundary")
        require(stage2["verified_citation_locator_pairs"]["count"] == 33, "handoff citation pair count")
        return {"pairs": 33, "non_none": 33, "page_anchors": 0}

    check("verified_citation_non_none_locator_pairs_33_of_33", citation_pairs)
    check("stage2_introduction_related_work_priority_only", lambda: (
        require(stage2["drafting_targets"] == ["Introduction", "Related Work"], "drafting targets"),
        require(stage2["drafting_action_in_r9"] == "NOT_PERFORMED", "R9 drafted prose"),
        stage2["drafting_targets"],
    )[-1])
    check("stage2_bounded_literature_authorization", lambda: (
        require(stage2["authorization"] == "BOUNDED_STAGE2_LITERATURE_DRAFTING", "Stage 2 authorization"),
        require(stage2["authorization_excludes"] == ["fabricated_citations", "fabricated_results", "benchmark_claims", "planning_only_claims"], "authorization exclusions"),
        stage2["authorization"],
    )[-1])
    check("h1_h4_not_run", lambda: (
        require(stage2["experiment_boundary"]["h1_h4"] == "NOT_RUN", "Stage2 H1-H4"),
        require(r8_handoff["phase_boundary"]["h1_h4"] == "NOT_RUN", "R8 H1-H4"),
        "NOT_RUN",
    )[-1])
    check("benchmark_training_evaluation_not_run", lambda: (
        require(stage2["experiment_boundary"]["benchmark_training_evaluation"] == "NOT_RUN", "Stage2 benchmark"),
        require(r8_handoff["phase_boundary"]["benchmark_training_evaluation"] == "NOT_RUN", "R8 benchmark"),
        "NOT_RUN",
    )[-1])
    check("empirical_cross_dataset_claims_forbidden", lambda: (
        require(stage2["experiment_boundary"]["forbidden_factual_claims"] == ["H1-H4 results", "benchmark comparison", "empirical superiority", "cross-dataset compatibility", "training results", "evaluation results"], "forbidden factual claims"),
        stage2["experiment_boundary"]["forbidden_factual_claims"],
    )[-1])

    check("seal_preimage_forbidden_surfaces_absent", lambda: (
        require(not recursively_contains_forbidden_preimage_surface(seal["seal_preimage"]), "forbidden seal-preimage surface"),
        seal["preimage_policy"],
    )[-1])
    check("seal_preimage_sha256_replay", lambda: (
        require(hashlib.sha256(canonical_bytes(seal["seal_preimage"])).hexdigest() == seal["seal_sha256"], "seal SHA replay"),
        seal["seal_sha256"],
    )[-1])
    check("seal_required_bindings_exact", lambda: (
        require(seal["seal_preimage"]["input_manifest_sha256"] == EXPECTED_R9_INPUT_SHA, "preimage input manifest"),
        require(seal["seal_preimage"]["r7"]["canonical_root_sha256"] == EXPECTED_ROOT, "preimage R7 root"),
        require(seal["seal_preimage"]["r8"]["handoff_sha256"] == EXPECTED_R8_HANDOFF_SHA, "preimage R8 handoff"),
        require(seal["seal_preimage"]["scholar"]["adjudication_sha256"] == EXPECTED_SCHOLAR_SHA, "preimage scholar"),
        "exact",
    )[-1])
    check("seal_verdict_pass_stage1b_sealed", lambda: (
        require(seal["verdict"] == "PASS_STAGE1B_SEALED" == stage2["stage1b_seal_verdict"] == handoff["verdict"], "seal verdict"),
        "PASS_STAGE1B_SEALED",
    )[-1])
    check("deterministic_vs_semantic_boundary", lambda: (
        require(seal["authority_boundary"]["deterministic_integrity"] != seal["authority_boundary"]["semantic_judgment"], "authority separation"),
        require(seal["authority_boundary"]["does_not_prove"] == ["scientific correctness", "novelty", "superiority", "external validity", "benchmark success"], "non-proof boundary"),
        seal["authority_boundary"],
    )[-1])

    def handoff_hashes() -> dict[str, Any]:
        for row in handoff["artifact_sha256"]:
            require(row["path"] != str(R9_HANDOFF).replace("\\", "/"), "handoff self-hash")
            require(row["path"] != str(RECEIPT).replace("\\", "/"), "receipt cycle in handoff")
            require(sha256_file(row["path"]) == row["sha256"], f"handoff artifact SHA: {row['path']}")
        return {"bound": len(handoff["artifact_sha256"]), "self_hash": False}

    check("r9_handoff_nonself_hashes_exact", handoff_hashes)

    def receipt_hashes() -> dict[str, Any]:
        require(receipt["result"] == "PASS" and receipt["verdict"] == "PASS_STAGE1B_SEALED", "receipt verdict")
        require(receipt["checks_run"] == 40 and receipt["checks_passed"] == 40 and receipt["checks_failed"] == 0, "receipt check counts")
        require(receipt["seal_sha256"] == seal["seal_sha256"], "receipt seal SHA")
        for row in receipt["artifact_sha256"]:
            require(row["path"] != str(RECEIPT).replace("\\", "/"), "receipt self-hash")
            require(sha256_file(row["path"]) == row["sha256"], f"receipt artifact SHA: {row['path']}")
        require(any(row["path"] == str(R9_HANDOFF).replace("\\", "/") for row in receipt["artifact_sha256"]), "receipt does not bind handoff")
        return {"bound": len(receipt["artifact_sha256"]), "self_hash": False}

    check("r9_receipt_nonself_hashes_exact", receipt_hashes)
    check("r9_report_required_summary", lambda: (
        require("PASS_STAGE1B_SEALED" in report, "report verdict"),
        require("29/29" in report and "60/60" in report and "193/193" in report, "report validator summary"),
        require(seal["seal_sha256"] in report, "report seal SHA"),
        require("22 authorized" in report and "22 prohibited" in report, "report claim counts"),
        "complete",
    )[-1])

    failures = [row for row in checks if row["status"] == "FAIL"]
    result = {
        "schema_version": "stage1b-r1-r9-final-validation-1.0",
        "validation_mode": "read_only_final",
        "result": "PASS" if not failures else "FAIL",
        "verdict": "PASS_STAGE1B_SEALED" if not failures else "REVISE",
        "checks_run": len(checks),
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "check_names": [row["name"] for row in checks],
        "failures": failures,
        "recomputed": {
            "direct_inputs": 13,
            "r7_validation": "PASS_29_OF_29",
            "r8_validation": "PASS_60_OF_60",
            "packet_members": 193,
            "canonical_root_sha256": EXPECTED_ROOT,
            "closures": 8,
            "authorized_claims": 22,
            "prohibited_claims": 22,
            "verified_citation_locator_pairs": 33,
            "seal_sha256": seal["seal_sha256"],
            "r9_handoff_sha256": sha256_file(R9_HANDOFF),
        },
        "authority": "This deterministic PASS seals the bounded Stage 1B R1 artifact chain and Stage 2 literature handoff only; it is not proof of scientific correctness, novelty, superiority, external validity, or benchmark success.",
    }
    return result


def main() -> int:
    result = run_validation()
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
