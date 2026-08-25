#!/usr/bin/env python3
"""Synthetic regression loop for Attempt-008; never probes Docker or the host."""

from __future__ import annotations

import unittest

import e4_r6_pc2w_p1_attempt008_probe_contract as contract


class Attempt008ProbeContractTests(unittest.TestCase):
    def test_accepts_observed_docker_cli_build_time_families(self) -> None:
        cases = {
            "Wed Oct  8 12:18:19 2025": "DOCKER_CLI_HUMAN",
            "2025-10-08T12:18:19.000000000+00:00": "RFC3339_UTC",
            "2025-10-08T12:18:19.0000000Z": "RFC3339_UTC",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(contract.classify_docker_build_time(raw), expected)

    def test_process_unavailable_has_stable_failure_locator(self) -> None:
        unavailable = {
            "Available": False,
            "Count": 0,
            "Rows": [],
            "ErrorCode": "PROBE_EXCEPTION",
            "ErrorTypeHash": "a" * 64,
        }
        with self.assertRaises(ValueError) as caught:
            contract.validate_process_identity(unavailable)
        self.assertEqual(
            getattr(caught.exception, "code", None),
            "PROCESS_ENVELOPE_UNAVAILABLE",
        )
        self.assertEqual(caught.exception.stage, "D01")
        self.assertEqual(
            caught.exception.safe_details,
            {
                "probe_error_code": "PROBE_EXCEPTION",
                "probe_error_type_hash": "a" * 64,
            },
        )

    def test_rejects_non_utc_or_unrecognized_build_times_with_locator(self) -> None:
        for raw in ("2025-10-08T12:18:19+07:00", "not-a-time"):
            with self.subTest(raw=raw):
                with self.assertRaises(contract.IdentityContractError) as caught:
                    contract.classify_docker_build_time(raw)
                self.assertEqual(
                    caught.exception.code,
                    "DOCKER_BUILD_TIME_FORMAT_UNSUPPORTED",
                )
                self.assertEqual(caught.exception.field, "BuildTime")

    def test_tcp_unavailable_has_stable_failure_locator(self) -> None:
        unavailable = {
            "Available": False,
            "Count": 0,
            "Rows": [],
            "ErrorCode": "PROBE_EXCEPTION",
            "ErrorTypeHash": "b" * 64,
        }
        with self.assertRaises(contract.IdentityContractError) as caught:
            contract.validate_tcp_identity(unavailable, {"Rows": []})
        self.assertEqual(caught.exception.code, "TCP_ENVELOPE_UNAVAILABLE")
        self.assertEqual(caught.exception.stage, "D02")

    def test_desktop_file_failure_maps_to_stable_locator(self) -> None:
        invalid = {
            "PathHash": "1" * 64,
            "RawBytes": 1,
            "FileSha256": "2" * 64,
            "FileVersion": "1.0.0",
            "ProductVersion": "1.0.0",
            "AuthenticodeStatus": "NotSigned",
            "SignerSubjectHash": "3" * 64,
        }
        with self.assertRaises(contract.IdentityContractError) as caught:
            contract.validate_desktop_file_identity(invalid)
        self.assertEqual(caught.exception.code, "DESKTOP_FILE_SIGNATURE_INVALID")
        self.assertEqual(caught.exception.stage, "D06")

    def test_conflicting_api_version_aliases_fail_closed(self) -> None:
        version = {
            "Client": {
                "ApiVersion": "1.51",
                "APIVersion": "1.52",
                "BuildTime": "Wed Oct  8 12:18:19 2025",
            },
            "Server": {
                "ApiVersion": "1.52",
                "BuildTime": "2025-10-08T12:18:19.000000000+00:00",
            },
        }
        with self.assertRaises(contract.IdentityContractError) as caught:
            contract.sanitize_docker_identity(version, {}, [])
        self.assertEqual(caught.exception.code, "DOCKER_API_VERSION_ALIAS_CONFLICT")
        self.assertEqual(caught.exception.stage, "DOCKER_CLIENT")

    def test_canonical_process_fixture_still_passes(self) -> None:
        def row(name: str, pid: int) -> dict[str, object]:
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

        fixture = {
            "Available": True,
            "Count": 2,
            "Rows": [
                row("com.docker.backend", 20),
                row("docker desktop", 10),
            ],
            "ErrorCode": "NONE",
            "ErrorTypeHash": None,
        }
        self.assertIs(contract.validate_process_identity(fixture), fixture)

    def test_mixed_docker_version_fixture_is_sanitized_without_raw_secret_paths(self) -> None:
        version = {
            "Client": {
                "Version": "29.0.0",
                "APIVersion": "1.52",
                "DefaultAPIVersion": "1.52",
                "GitCommit": "client-commit",
                "GoVersion": "go1.25.3",
                "Os": "windows",
                "Arch": "amd64",
                "BuildTime": "Wed Oct  8 12:18:19 2025",
                "Context": "desktop-linux",
            },
            "Server": {
                "Version": "29.0.0",
                "ApiVersion": "1.52",
                "MinAPIVersion": "1.24",
                "GitCommit": "server-commit",
                "GoVersion": "go1.25.3",
                "Os": "linux",
                "Arch": "amd64",
                "KernelVersion": "6.6.87.2-microsoft-standard-WSL2",
                "BuildTime": "2025-10-08T12:18:19.000000000+00:00",
                "Experimental": False,
            },
        }
        info = {
            "ServerVersion": "29.0.0",
            "OperatingSystem": "Docker Desktop",
            "OSType": "linux",
            "Architecture": "amd64",
            "KernelVersion": "6.6.87.2-microsoft-standard-WSL2",
            "Driver": "overlayfs",
            "CgroupDriver": "cgroupfs",
            "CgroupVersion": "2",
            "DockerRootDir": "/var/lib/docker",
            "DefaultRuntime": "runc",
            "ID": "daemon-id",
            "NCPU": 8,
            "MemTotal": 8589934592,
            "Containers": 0,
            "ContainersRunning": 0,
            "ContainersPaused": 0,
            "ContainersStopped": 0,
            "Images": 0,
            "LiveRestoreEnabled": False,
            "ExperimentalBuild": False,
            "ContainerdCommit": {"ID": "containerd-commit"},
            "Runtimes": {"runc": {}},
            "SecurityOptions": ["name=seccomp,profile=builtin"],
        }
        context = [
            {
                "Name": "desktop-linux",
                "Metadata": {"Description": "Docker Desktop"},
                "Endpoints": {
                    "docker": {
                        "Host": "npipe:////./pipe/dockerdesktoplinuxengine",
                        "SkipTLSVerify": False,
                    }
                },
                "TLSMaterial": {},
                "Storage": {},
            }
        ]
        sanitized, cross = contract.sanitize_docker_identity(version, info, context)
        self.assertEqual(sanitized["client"]["BuildTimeFormat"], "DOCKER_CLI_HUMAN")
        self.assertEqual(sanitized["server"]["BuildTimeFormat"], "RFC3339_UTC")
        self.assertEqual(sanitized["client"]["ApiVersion"], "1.52")
        self.assertTrue(all(cross.values()))
        self.assertNotIn("/var/lib/docker", str(sanitized))
        self.assertNotIn("daemon-id", str(sanitized))


if __name__ == "__main__":
    unittest.main()
