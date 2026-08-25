#!/usr/bin/env python3
"""Offline regression tests for Attempt-009 runtime compatibility."""

from __future__ import annotations

import os
import unittest

import e4_r6_pc2w_p1_attempt009_runtime_compatibility as compat


def client() -> dict[str, object]:
    return {
        "Version": "29.5.3",
        "ApiVersion": "1.54",
        "DefaultAPIVersion": "1.54",
        "GitCommit": "client-commit",
        "GoVersion": "go1.26.4",
        "Os": "windows",
        "Arch": "amd64",
        "BuildTime": "Wed Jun  3 18:03:06 2026",
        "Context": "desktop-linux",
    }


def engine_details() -> dict[str, object]:
    return {
        "ApiVersion": "1.54",
        "MinAPIVersion": "1.44",
        "GitCommit": "engine-commit",
        "GoVersion": "go1.26.4",
        "Os": "linux",
        "Arch": "amd64",
        "KernelVersion": "6.6.87.2-microsoft-standard-WSL2",
        "BuildTime": "2026-06-03T18:03:06.000000000+00:00",
        "Experimental": "false",
    }


def modern_version() -> dict[str, object]:
    return {
        "Client": client(),
        "Server": {
            "Platform": {"Name": "Docker Desktop 4.78.0"},
            "Version": "29.5.3",
            "APIVersion": "1.54",
            "MinAPIVersion": "1.44",
            "Os": "linux",
            "Arch": "amd64",
            "Experimental": False,
            "Components": [
                {
                    "Name": "Engine",
                    "Version": "29.5.3",
                    "Details": engine_details(),
                },
                {"Name": "containerd", "Version": "v2.2.0", "Details": {}},
            ],
        },
    }


def info() -> dict[str, object]:
    return {
        "ServerVersion": "29.5.3",
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


def context() -> list[dict[str, object]]:
    return [
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


class Attempt009RuntimeCompatibilityTests(unittest.TestCase):
    def test_child_environment_removes_codex_and_powershell7_module_shadowing(self) -> None:
        parent = {
            "PATH": os.environ.get("PATH", ""),
            "PSModulePath": (
                r"C:\Users\ACER\Documents\PowerShell\Modules;"
                r"C:\Users\ACER\.cache\codex-runtimes\runtime\powershell\Modules;"
                r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules"
            ),
        }
        child = compat.windows_powershell_child_environment(parent)
        module_path = child["PSModulePath"].casefold()
        self.assertNotIn("codex-runtimes", module_path)
        self.assertNotIn(r"documents\powershell\modules", module_path)
        self.assertIn(r"windowspowershell\v1.0\modules", module_path)
        self.assertEqual(child["PATH"], parent["PATH"])

    def test_probe_wrappers_import_exact_windows_powershell_manifests_first(self) -> None:
        wrapped = compat.wrap_process_identity_probe("ORIGINAL_PROCESS_PROBE")
        self.assertLess(wrapped.index("Import-Module"), wrapped.index("ORIGINAL_PROCESS_PROBE"))
        self.assertIn("Microsoft.PowerShell.Utility.psd1", wrapped)
        self.assertIn("Microsoft.PowerShell.Security.psd1", wrapped)
        self.assertIn("CimCmdlets.psd1", wrapped)
        tcp = compat.wrap_tcp_identity_probe("ORIGINAL_TCP_PROBE")
        self.assertIn("NetTCPIP.psd1", tcp)

    def test_preflight_is_observation_only_and_has_closed_envelope(self) -> None:
        query = compat.POWERSHELL_MODULE_PREFLIGHT_QUERY
        self.assertIn(compat.PREFLIGHT_SCHEMA, query)
        self.assertIn("FailureStep", query)
        for forbidden in (
            "Start-Process", "Stop-Process", "Start-Service", "Stop-Service",
            "Restart-Service", "Set-ItemProperty", "Remove-Item", "Install-Module",
            "Invoke-WebRequest", "Invoke-RestMethod",
        ):
            self.assertNotIn(forbidden, query)

    def test_preflight_success_requires_all_exact_command_bindings(self) -> None:
        rows = [
            {
                "Command": name,
                "Module": module,
                "CommandType": command_type,
                "ModuleVersion": version,
                "ModulePathHash": char * 64,
                "ManifestSha256": digit * 64,
            }
            for name, module, command_type, version, char, digit in (
                ("Get-CimInstance", "CimCmdlets", "Cmdlet", "1.0.0.0", "a", "1"),
                ("Get-NetTCPConnection", "MSFT_NetTCPConnection", "Function", "1.0.0.0", "b", "2"),
                ("Get-FileHash", "Microsoft.PowerShell.Utility", "Function", "3.1.0.0", "c", "3"),
                ("Get-AuthenticodeSignature", "Microsoft.PowerShell.Security", "Cmdlet", "3.0.0.0", "d", "4"),
                ("ConvertTo-Json", "Microsoft.PowerShell.Utility", "Cmdlet", "3.1.0.0", "e", "5"),
            )
        ]
        envelope = {
            "SchemaVersion": compat.PREFLIGHT_SCHEMA,
            "Available": True,
            "PowerShellMajor": 5,
            "LanguageMode": "FullLanguage",
            "Count": 5,
            "Rows": rows,
            "ErrorCode": "NONE",
            "FailureStep": "NONE",
            "ErrorTypeHash": None,
        }
        validated = compat.validate_powershell_module_preflight(envelope)
        self.assertEqual(validated["Count"], 5)

    def test_docker29_component_details_supplement_missing_root_fields(self) -> None:
        sanitized, cross = compat.sanitize_docker_identity(
            modern_version(), info(), context()
        )
        self.assertTrue(all(cross.values()))
        self.assertEqual(
            sanitized["server"]["IdentitySourceProfile"],
            "ROOT_WITH_ENGINE_COMPONENT_SUPPLEMENT",
        )
        self.assertEqual(
            sanitized["server"]["IdentityFieldSources"]["GitCommit"],
            "ENGINE_COMPONENT_DETAILS",
        )
        self.assertEqual(sanitized["server"]["Experimental"], False)

    def test_docker29_root_and_component_conflict_fails_closed(self) -> None:
        version = modern_version()
        version["Server"]["GitCommit"] = "conflicting-root-commit"
        with self.assertRaises(compat.IdentityContractError) as caught:
            compat.sanitize_docker_identity(version, info(), context())
        self.assertEqual(caught.exception.code, "DOCKER_SERVER_FIELD_CONFLICT")
        self.assertEqual(caught.exception.field, "GitCommit")

        invalid_boolean = modern_version()
        del invalid_boolean["Server"]["Experimental"]
        invalid_boolean["Server"]["Components"][0]["Details"]["Experimental"] = "False"
        with self.assertRaises(compat.IdentityContractError) as boolean_caught:
            compat.sanitize_docker_identity(invalid_boolean, info(), context())
        self.assertEqual(
            boolean_caught.exception.code,
            "DOCKER_SERVER_EXPERIMENTAL_INVALID",
        )
        self.assertEqual(boolean_caught.exception.field, "Experimental")

    def test_missing_server_field_in_root_and_engine_component_has_locator(self) -> None:
        version = modern_version()
        del version["Server"]["Components"][0]["Details"]["BuildTime"]
        with self.assertRaises(compat.IdentityContractError) as caught:
            compat.sanitize_docker_identity(version, info(), context())
        self.assertEqual(caught.exception.code, "DOCKER_SERVER_FIELD_MISSING")
        self.assertEqual(caught.exception.field, "BuildTime")

    def test_duplicate_engine_components_fail_closed(self) -> None:
        version = modern_version()
        version["Server"]["Components"].append(
            {"Name": "Engine", "Version": "29.5.3", "Details": engine_details()}
        )
        with self.assertRaises(compat.IdentityContractError) as caught:
            compat.sanitize_docker_identity(version, info(), context())
        self.assertEqual(caught.exception.code, "DOCKER_ENGINE_COMPONENT_AMBIGUOUS")

    def test_complete_legacy_root_does_not_require_components(self) -> None:
        version = modern_version()
        server = version["Server"]
        details = server["Components"][0]["Details"]
        for field in (
            "GitCommit", "GoVersion", "KernelVersion", "BuildTime"
        ):
            server[field] = details[field]
        del server["Components"]
        sanitized, cross = compat.sanitize_docker_identity(version, info(), context())
        self.assertTrue(all(cross.values()))
        self.assertEqual(sanitized["server"]["IdentitySourceProfile"], "ROOT_ONLY")


if __name__ == "__main__":
    unittest.main()
