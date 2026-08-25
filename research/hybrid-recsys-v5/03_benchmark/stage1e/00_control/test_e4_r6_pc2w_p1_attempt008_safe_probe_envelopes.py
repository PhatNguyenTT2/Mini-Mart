#!/usr/bin/env python3
"""Synthetic tests for Attempt-008 R2 safe envelopes; no host probes."""

from __future__ import annotations

import unittest

import e4_r6_pc2w_p1_attempt008_probe_contract as parser
import e4_r6_pc2w_p1_attempt008_safe_probe_envelopes as probes


def process_row(name: str, pid: int) -> dict[str, object]:
    return {
        "Name": name,
        "ProcessId": pid,
        "ParentProcessId": 1,
        "ParentNameHash": "1" * 64,
        "ParentExecutablePathHash": "2" * 64,
        "ExecutablePathHash": "3" * 64,
        "ExecutableFileSha256": "4" * 64,
        "FileVersion": "1.0.0",
        "AuthenticodeStatus": "Valid",
        "SignerSubjectHash": "5" * 64,
        "CreationTimeUtc": "2026-08-25T01:02:03.0000000Z",
        "CommandLineHash": "6" * 64,
    }


def process_envelope() -> dict[str, object]:
    return {
        "SchemaVersion": probes.PROBE_SCHEMA,
        "Available": True,
        "Count": 2,
        "Rows": [
            process_row("com.docker.backend", 20),
            process_row("docker desktop", 10),
        ],
        "ErrorCode": "NONE",
        "FailureStep": "NONE",
        "FailureTarget": None,
        "ErrorTypeHash": None,
    }


class Attempt008SafeProbeEnvelopeTests(unittest.TestCase):
    def test_probe_scripts_are_observation_only_and_do_not_persist_raw_errors(self) -> None:
        forbidden = (
            "Start-Process",
            "Stop-Process",
            "Restart-Service",
            "Start-Service",
            "Stop-Service",
            "Set-ItemProperty",
            "Remove-Item",
            "Invoke-WebRequest",
            "Invoke-RestMethod",
            "Exception.Message",
            "ErrorMessage",
        )
        scripts = (
            probes.PROCESS_IDENTITY_QUERY_V2,
            probes.TCP_IDENTITY_QUERY_V2,
            probes.DOCKER_DESKTOP_FILE_IDENTITY_QUERY_V2,
        )
        for script in scripts:
            with self.subTest(script_sha=parser.legacy.sha256_bytes(script.encode("utf-8"))):
                self.assertIn(probes.PROBE_SCHEMA, script)
                self.assertIn("ErrorTypeHash", script)
                self.assertIn("FailureStep", script)
                for token in forbidden:
                    self.assertNotIn(token, script)
        self.assertNotIn("ExecutablePath=", probes.PROCESS_IDENTITY_QUERY_V2)
        self.assertNotIn("CommandLine=", probes.PROCESS_IDENTITY_QUERY_V2)
        self.assertNotIn("LocalAddress=", probes.TCP_IDENTITY_QUERY_V2)
        self.assertNotIn("RemoteAddress=", probes.TCP_IDENTITY_QUERY_V2)

    def test_process_failure_emits_closed_safe_locator(self) -> None:
        value = {
            "SchemaVersion": probes.PROBE_SCHEMA,
            "Available": False,
            "Count": 0,
            "Rows": [],
            "ErrorCode": "PROBE_EXCEPTION",
            "FailureStep": "RESOLVE_PARENT",
            "FailureTarget": "com.docker.backend",
            "ErrorTypeHash": "a" * 64,
        }
        with self.assertRaises(parser.IdentityContractError) as caught:
            probes.validate_process_probe_envelope(value)
        self.assertEqual(caught.exception.code, "PROCESS_PROBE_RESOLVE_PARENT")
        self.assertEqual(
            caught.exception.safe_details,
            {
                "failure_step": "RESOLVE_PARENT",
                "failure_target": "com.docker.backend",
                "error_type_hash": "a" * 64,
            },
        )

    def test_process_unknown_failure_step_fails_closed(self) -> None:
        value = {
            "SchemaVersion": probes.PROBE_SCHEMA,
            "Available": False,
            "Count": 0,
            "Rows": [],
            "ErrorCode": "PROBE_EXCEPTION",
            "FailureStep": "RAW_DYNAMIC_MESSAGE",
            "FailureTarget": None,
            "ErrorTypeHash": "a" * 64,
        }
        with self.assertRaises(parser.IdentityContractError) as caught:
            probes.validate_process_probe_envelope(value)
        self.assertEqual(caught.exception.code, "PROCESS_PROBE_FAILURE_STEP_INVALID")

    def test_process_success_reuses_r1_strict_identity_validation(self) -> None:
        result = probes.validate_process_probe_envelope(process_envelope())
        self.assertEqual(result["Count"], 2)

    def test_tcp_dependency_failure_is_not_misreported_as_tcp_parser_failure(self) -> None:
        value = {
            "SchemaVersion": probes.PROBE_SCHEMA,
            "Available": True,
            "Count": 0,
            "Rows": [],
            "ErrorCode": "NONE",
            "FailureStep": "NONE",
            "FailureTarget": None,
            "ErrorTypeHash": None,
        }
        with self.assertRaises(parser.IdentityContractError) as caught:
            probes.validate_tcp_probe_envelope(value, None)
        self.assertEqual(
            caught.exception.code,
            "TCP_DEPENDENCY_PROCESS_IDENTITY_UNAVAILABLE",
        )

    def test_tcp_own_probe_failure_has_own_locator(self) -> None:
        value = {
            "SchemaVersion": probes.PROBE_SCHEMA,
            "Available": False,
            "Count": 0,
            "Rows": [],
            "ErrorCode": "PROBE_EXCEPTION",
            "FailureStep": "ENUMERATE_TCP_CONNECTIONS",
            "FailureTarget": None,
            "ErrorTypeHash": "b" * 64,
        }
        processes = probes.validate_process_probe_envelope(process_envelope())
        with self.assertRaises(parser.IdentityContractError) as caught:
            probes.validate_tcp_probe_envelope(value, processes)
        self.assertEqual(
            caught.exception.code,
            "TCP_PROBE_ENUMERATE_TCP_CONNECTIONS",
        )

    def test_empty_tcp_success_is_valid_when_process_dependency_is_valid(self) -> None:
        value = {
            "SchemaVersion": probes.PROBE_SCHEMA,
            "Available": True,
            "Count": 0,
            "Rows": [],
            "ErrorCode": "NONE",
            "FailureStep": "NONE",
            "FailureTarget": None,
            "ErrorTypeHash": None,
        }
        processes = probes.validate_process_probe_envelope(process_envelope())
        result = probes.validate_tcp_probe_envelope(value, processes)
        self.assertEqual(result["Count"], 0)

    def test_desktop_file_probe_failure_has_closed_step(self) -> None:
        value = {
            "SchemaVersion": probes.PROBE_SCHEMA,
            "Available": False,
            "Identity": None,
            "ErrorCode": "PROBE_EXCEPTION",
            "FailureStep": "READ_AUTHENTICODE",
            "ErrorTypeHash": "c" * 64,
        }
        with self.assertRaises(parser.IdentityContractError) as caught:
            probes.validate_desktop_file_probe_envelope(value)
        self.assertEqual(
            caught.exception.code,
            "DESKTOP_FILE_PROBE_READ_AUTHENTICODE",
        )

    def test_desktop_file_success_reuses_r1_strict_validation(self) -> None:
        value = {
            "SchemaVersion": probes.PROBE_SCHEMA,
            "Available": True,
            "Identity": {
                "PathHash": "1" * 64,
                "RawBytes": 100,
                "FileSha256": "2" * 64,
                "FileVersion": "1.0.0",
                "ProductVersion": "1.0.0",
                "AuthenticodeStatus": "Valid",
                "SignerSubjectHash": "3" * 64,
            },
            "ErrorCode": "NONE",
            "FailureStep": "NONE",
            "ErrorTypeHash": None,
        }
        result = probes.validate_desktop_file_probe_envelope(value)
        self.assertEqual(result["RawBytes"], 100)


if __name__ == "__main__":
    unittest.main()
