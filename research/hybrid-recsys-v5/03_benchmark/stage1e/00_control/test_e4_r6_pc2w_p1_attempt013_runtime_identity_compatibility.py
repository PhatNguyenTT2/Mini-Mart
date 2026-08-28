#!/usr/bin/env python3
"""Offline RED-to-GREEN regressions for Attempt-013 identity seams."""

from __future__ import annotations

import copy
import json
import unittest
from typing import Any

import e4_r6_pc2w_p1_attempt008_probe_contract as parser008
import e4_r6_pc2w_p1_attempt008_safe_probe_envelopes as probes008
import e4_r6_pc2w_p1_attempt009_runtime_compatibility as compat009

try:
    import e4_r6_pc2w_p1_attempt013_runtime_identity_compatibility as compat013
except ModuleNotFoundError:
    compat013 = None


ATTEMPT013_SCHEMA = (
    "stage1e-e4-r6-pc2w-p1-attempt013-runtime-identity-compatibility-1.0"
)


def self_row(
    name: str, pid: int, *, resolution: str = "UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT"
) -> dict[str, Any]:
    resolved = resolution == "RESOLVED"
    return {
        "Name": name,
        "ProcessId": pid,
        "ParentProcessId": 4,
        "ParentResolution": resolution,
        "ParentNameHash": "1" * 64 if resolved else None,
        "ParentExecutablePathHash": "2" * 64 if resolved else None,
        "ExecutablePathHash": "3" * 64,
        "ExecutableFileSha256": "4" * 64,
        "FileVersion": "1.0.0",
        "AuthenticodeStatus": "Valid",
        "SignerSubjectHash": "5" * 64,
        "CreationTimeUtc": "2026-08-29T01:02:03.0000000Z",
        "CommandLineHash": "6" * 64,
    }


def process_envelope() -> dict[str, Any]:
    rows = [
        self_row("com.docker.backend", 20),
        self_row("docker desktop", 10, resolution="RESOLVED"),
    ]
    rows.sort(key=lambda row: (row["Name"], row["ProcessId"]))
    return {
        "SchemaVersion": ATTEMPT013_SCHEMA,
        "Available": True,
        "Count": len(rows),
        "Rows": rows,
        "ErrorCode": "NONE",
        "FailureStep": "NONE",
        "FailureTarget": None,
        "ErrorTypeHash": None,
    }


def tcp_envelope(*, pid: int = 20, name: str = "com.docker.backend") -> dict[str, Any]:
    return {
        "SchemaVersion": ATTEMPT013_SCHEMA,
        "Available": True,
        "Count": 1,
        "Rows": [{
            "ProcessName": name,
            "ProcessId": pid,
            "State": "Listen",
            "LocalAddressHash": "7" * 64,
            "LocalPort": 2375,
            "RemoteAddressHash": "8" * 64,
            "RemotePort": 0,
        }],
        "ErrorCode": "NONE",
        "FailureStep": "NONE",
        "FailureTarget": None,
        "ErrorTypeHash": None,
    }


def version_fixture(
    root_build: str = "Wed Jun  3 18:03:06 2026",
    engine_build: str = "2026-06-03T18:03:06Z",
) -> dict[str, Any]:
    common = {
        "ApiVersion": "1.54",
        "MinAPIVersion": "1.44",
        "GitCommit": "commit",
        "GoVersion": "go1.26.4",
        "Os": "linux",
        "Arch": "amd64",
        "KernelVersion": "kernel",
    }
    details = {**common, "BuildTime": engine_build, "Experimental": "false"}
    return {
        "Client": {},
        "Server": {
            "Version": "29.5.3",
            **common,
            "BuildTime": root_build,
            "Experimental": False,
            "Components": [{
                "Name": "Engine",
                "Version": "29.5.3",
                "Details": details,
            }],
        },
    }


class FrozenAttempt012SeamEvidenceTests(unittest.TestCase):
    def test_old_process_validator_rejects_the_adjudicated_parent_union(self) -> None:
        value = process_envelope()
        value["SchemaVersion"] = probes008.PROBE_SCHEMA
        with self.assertRaises(parser008.IdentityContractError) as caught:
            probes008.validate_process_probe_envelope(value)
        self.assertEqual(caught.exception.code, "PROCESS_ROW_FIELDS_INVALID")

    def test_old_tcp_path_fails_when_parent_lookup_erases_process_identity(self) -> None:
        value = tcp_envelope()
        value["SchemaVersion"] = probes008.PROBE_SCHEMA
        with self.assertRaises(parser008.IdentityContractError) as caught:
            probes008.validate_tcp_probe_envelope(value, None)
        self.assertEqual(
            caught.exception.code, "TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE"
        )

    def test_old_build_time_raw_equality_rejects_same_zero_fraction_civil_second(self) -> None:
        with self.assertRaises(parser008.IdentityContractError) as caught:
            compat009.canonicalize_docker_server(version_fixture())
        self.assertEqual(caught.exception.code, "DOCKER_SERVER_FIELD_CONFLICT")
        self.assertEqual(caught.exception.field, "BuildTime")


class Attempt013ProcessAndTcpContractTests(unittest.TestCase):
    def require_new(self) -> Any:
        if compat013 is None:
            self.fail("ATTEMPT013_IMPLEMENTATION_MODULE_ABSENT")
        return compat013

    def test_unresolved_parent_retains_complete_direct_self_identity(self) -> None:
        module = self.require_new()
        result = module.validate_process_probe_envelope(process_envelope())
        backend = result["Rows"][0]
        self.assertEqual(
            backend["ParentResolution"],
            "UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT",
        )
        self.assertEqual(backend["ExecutableFileSha256"], "4" * 64)

    def test_unresolved_parent_does_not_legalize_incomplete_self_identity(self) -> None:
        module = self.require_new()
        value = process_envelope()
        value["Rows"][0]["ExecutableFileSha256"] = None
        with self.assertRaises(module.IdentityContractError) as caught:
            module.validate_process_probe_envelope(value)
        self.assertEqual(caught.exception.code, "PROCESS_SELF_HASH_INVALID")

    def test_parent_union_enum_and_nullability_are_closed(self) -> None:
        module = self.require_new()
        for mutation, code in (
            ({"ParentResolution": "UNKNOWN"}, "PROCESS_PARENT_RESOLUTION_INVALID"),
            ({"ParentNameHash": "1" * 64}, "PROCESS_PARENT_NULLABILITY_INVALID"),
            ({
                "ParentResolution": "RESOLVED",
                "ParentNameHash": None,
                "ParentExecutablePathHash": None,
            }, "PROCESS_PARENT_HASH_INVALID"),
        ):
            with self.subTest(code=code):
                value = process_envelope()
                value["Rows"][0].update(mutation)
                with self.assertRaises(module.IdentityContractError) as caught:
                    module.validate_process_probe_envelope(value)
                self.assertEqual(caught.exception.code, code)

    def test_required_self_identity_names_remain_mandatory(self) -> None:
        module = self.require_new()
        value = process_envelope()
        value["Rows"] = [value["Rows"][0]]
        value["Count"] = 1
        with self.assertRaises(module.IdentityContractError) as caught:
            module.validate_process_probe_envelope(value)
        self.assertEqual(caught.exception.code, "PROCESS_REQUIRED_IDENTITIES_MISSING")

    def test_tcp_owner_binds_to_self_identity_with_unresolved_parent(self) -> None:
        module = self.require_new()
        processes = module.validate_process_probe_envelope(process_envelope())
        result = module.validate_tcp_probe_envelope(tcp_envelope(), processes)
        self.assertEqual(result["Rows"][0]["ProcessId"], 20)

    def test_tcp_dependency_and_unbound_owner_remain_fail_closed(self) -> None:
        module = self.require_new()
        with self.assertRaises(module.IdentityContractError) as dependency:
            module.validate_tcp_probe_envelope(tcp_envelope(), None)
        self.assertEqual(
            dependency.exception.code,
            "TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE",
        )
        processes = module.validate_process_probe_envelope(process_envelope())
        with self.assertRaises(module.IdentityContractError) as unbound:
            module.validate_tcp_probe_envelope(tcp_envelope(pid=999), processes)
        self.assertEqual(unbound.exception.code, "TCP_OWNER_AMBIGUOUS")

    def test_process_query_is_single_snapshot_observation_only(self) -> None:
        module = self.require_new()
        query = module.PROCESS_IDENTITY_QUERY_V3
        self.assertEqual(query.count("Get-CimInstance"), 1)
        self.assertIn("UNRESOLVED_NOT_IN_ENUMERATED_SNAPSHOT", query)
        for forbidden in (
            "Start-Process", "Stop-Process", "Start-Service", "Stop-Service",
            "Restart-Service", "Invoke-WebRequest", "Invoke-RestMethod",
        ):
            self.assertNotIn(forbidden, query)


class Attempt013BuildTimeContractTests(unittest.TestCase):
    def require_new(self) -> Any:
        if compat013 is None:
            self.fail("ATTEMPT013_IMPLEMENTATION_MODULE_ABSENT")
        return compat013

    def test_exact_raw_build_time_is_accepted_after_format_validation(self) -> None:
        module = self.require_new()
        raw = "2026-06-03T18:03:06Z"
        _, _, _, comparison = module.canonicalize_docker_server(
            version_fixture(raw, raw)
        )
        self.assertEqual(comparison["comparison_profile"], "EXACT_RAW")

    def test_human_and_rfc3339_zero_fraction_same_civil_second_are_equivalent(self) -> None:
        module = self.require_new()
        _, _, _, comparison = module.canonicalize_docker_server(version_fixture())
        self.assertEqual(
            comparison["comparison_profile"],
            "FORMAT_EQUIVALENT_CIVIL_SECOND",
        )
        self.assertTrue(comparison["civil_second_equal"])
        self.assertTrue(comparison["fraction_zero_or_absent"])

    def test_build_time_mismatch_and_nonzero_fraction_fail_closed(self) -> None:
        module = self.require_new()
        for engine in (
            "2026-06-03T18:03:07Z",
            "2026-06-03T18:03:06.000000001Z",
        ):
            with self.subTest(engine=engine):
                with self.assertRaises(module.IdentityContractError) as caught:
                    module.canonicalize_docker_server(version_fixture(engine_build=engine))
                self.assertEqual(caught.exception.code, "DOCKER_SERVER_FIELD_CONFLICT")
                self.assertEqual(caught.exception.field, "BuildTime")

    def test_invalid_weekday_duplicate_engine_and_api_alias_remain_closed(self) -> None:
        module = self.require_new()
        invalid_weekday = version_fixture(root_build="Thu Jun  3 18:03:06 2026")
        with self.assertRaises(module.IdentityContractError) as weekday:
            module.canonicalize_docker_server(invalid_weekday)
        self.assertEqual(weekday.exception.code, "DOCKER_BUILD_TIME_WEEKDAY_MISMATCH")
        duplicate = version_fixture()
        duplicate["Server"]["Components"].append(
            copy.deepcopy(duplicate["Server"]["Components"][0])
        )
        with self.assertRaises(module.IdentityContractError) as engine:
            module.canonicalize_docker_server(duplicate)
        self.assertEqual(engine.exception.code, "DOCKER_ENGINE_COMPONENT_AMBIGUOUS")
        alias = version_fixture()
        alias["Server"]["APIVersion"] = "9.99"
        with self.assertRaises(module.IdentityContractError) as api:
            module.canonicalize_docker_server(alias)
        self.assertEqual(api.exception.code, "DOCKER_API_VERSION_ALIAS_CONFLICT")

    def test_comparison_receipt_is_hashed_private_and_deterministic(self) -> None:
        module = self.require_new()
        first = module.canonicalize_docker_server(version_fixture())[3]
        second = module.canonicalize_docker_server(version_fixture())[3]
        self.assertEqual(module.canonical_json_bytes(first), module.canonical_json_bytes(second))
        rendered = json.dumps(first, sort_keys=True)
        self.assertNotIn("Wed Jun", rendered)
        self.assertNotIn("2026-06-03T", rendered)
        self.assertEqual(len(first["root_value_sha256"]), 64)
        self.assertEqual(len(first["engine_value_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
