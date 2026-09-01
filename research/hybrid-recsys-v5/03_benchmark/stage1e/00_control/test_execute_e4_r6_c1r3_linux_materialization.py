from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import execute_e4_r6_c1r3_linux_materialization as runner


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_key_is_rejected(self) -> None:
        with self.assertRaises(runner.StrictJsonError):
            runner.strict_json_bytes(b'{"a":1,"a":2}')

    def test_case_colliding_key_is_rejected(self) -> None:
        with self.assertRaises(runner.StrictJsonError):
            runner.strict_json_bytes(b'{"a":1,"A":2}')

    def test_nonfinite_number_is_rejected(self) -> None:
        with self.assertRaises(runner.StrictJsonError):
            runner.strict_json_bytes(b'{"a":NaN}')


class PacketPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[5]
        cls.plan = runner.load_execution_plan(cls.repo_root)

    def test_only_image_and_m0_m1_commands_are_selected(self) -> None:
        ids = [row["id"] for row in self.plan]
        self.assertEqual(ids, list(runner.EXPECTED_COMMAND_IDS))
        self.assertEqual(len(ids), 17)
        self.assertFalse(any(value.startswith("B") for value in ids))

    def test_all_packet_argv_hashes_replay(self) -> None:
        for row in self.plan:
            self.assertEqual(row["argv_sha256"], runner.argv_hash(row["argv"]))

    def test_mutated_argv_is_rejected(self) -> None:
        row = dict(self.plan[0])
        row["argv"] = [*row["argv"], "unexpected"]
        with self.assertRaisesRegex(RuntimeError, "ARGV_HASH_MISMATCH"):
            runner.validate_packet_command(row)

    def test_live_packet_validator_replays_current_72_checks(self) -> None:
        value = runner.run_packet_validator(self.repo_root)
        self.assertEqual(value["diagnostics"]["passed_count"], 72)
        self.assertEqual(value["diagnostics"]["check_count"], 72)
        self.assertEqual(value["diagnostics"]["source_replay"]["files"], 265)


class OrchestrationTests(unittest.TestCase):
    def test_roots_are_created_only_after_I02_passes(self) -> None:
        commands = [{"id": value} for value in runner.EXPECTED_COMMAND_IDS]
        events: list[str] = []

        def execute(row: dict[str, object]) -> None:
            events.append(str(row["id"]))

        runner.orchestrate_commands(commands, execute, lambda: events.append("ROOTS"))
        self.assertEqual(events[2], "I02_PROBE_EXACT_CPYTHON_IDENTITY")
        self.assertEqual(events[3], "ROOTS")

    def test_failure_before_I02_never_creates_roots(self) -> None:
        commands = [{"id": value} for value in runner.EXPECTED_COMMAND_IDS]
        events: list[str] = []

        def execute(row: dict[str, object]) -> None:
            identifier = str(row["id"])
            events.append(identifier)
            if identifier == "I01_INSPECT_LOCAL_IMAGE_IDENTITY":
                raise RuntimeError("synthetic failure")

        with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
            runner.orchestrate_commands(commands, execute, lambda: events.append("ROOTS"))
        self.assertNotIn("ROOTS", events)
        self.assertEqual(events, list(runner.EXPECTED_COMMAND_IDS[:2]))

    def test_first_lane_failure_stops_all_following_commands(self) -> None:
        commands = [{"id": value} for value in runner.EXPECTED_COMMAND_IDS]
        events: list[str] = []

        def execute(row: dict[str, object]) -> None:
            identifier = str(row["id"])
            events.append(identifier)
            if identifier == "M01_SAFE_EXTRACT_CONVERT_AND_RECONCILE":
                raise RuntimeError("lane failure")

        with self.assertRaisesRegex(RuntimeError, "lane failure"):
            runner.orchestrate_commands(commands, execute, lambda: events.append("ROOTS"))
        self.assertNotIn("E00_DOWNLOAD_LINUX_WHEEL_CLOSURE", events)


class EvidenceTests(unittest.TestCase):
    def test_append_jsonl_is_append_only_and_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "journal.jsonl"
            runner.append_jsonl(path, {"sequence": 1})
            runner.append_jsonl(path, {"sequence": 2})
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(rows, [{"sequence": 1}, {"sequence": 2}])

    def test_dataset_final_receipt_rejects_scientific_execution(self) -> None:
        receipt = {
            "schema_version": "stage1e-r6-c1r3-dataset-materialization-1.0",
            "attempt": "attempt-004-linux",
            "archive_sha256": runner.ML100K_SHA256,
            "rows": 100000,
            "users": 943,
            "items": 1682,
            "scientific_execution_performed": True,
            "test_opened": False,
            "verdict": "PASS_R6_M0_MATERIALIZED_NOT_BENCHMARKED",
        }
        with self.assertRaisesRegex(RuntimeError, "DATASET_FINAL_RECEIPT_INVALID"):
            runner.validate_dataset_final_receipt(receipt)

    def test_environment_final_receipt_rejects_evaluation(self) -> None:
        receipt = {
            "schema_version": "stage1e-r6-c1r3-environment-materialization-1.0",
            "attempt": "attempt-004-linux",
            "python": "3.11.9",
            "recbole": "1.2.1",
            "torch": "2.2.2+cpu",
            "torch_cuda": None,
            "cuda_available": False,
            "source_python_files": 150,
            "source_python_bytes": 1378341,
            "dataset_constructed": False,
            "training": False,
            "evaluation": True,
            "test_opened": False,
            "verdict": "PASS_R6_M1_ENVIRONMENT_MATERIALIZED_NOT_BENCHMARKED",
        }
        with self.assertRaisesRegex(RuntimeError, "ENVIRONMENT_FINAL_RECEIPT_INVALID"):
            runner.validate_environment_final_receipt(receipt)

    def test_confirmation_is_exact(self) -> None:
        runner.require_confirmation(runner.CONFIRMATION_TOKEN)
        with self.assertRaisesRegex(RuntimeError, "EXECUTION_CONFIRMATION_MISMATCH"):
            runner.require_confirmation(runner.CONFIRMATION_TOKEN + "_MUTATED")


class MinimalPreRuntimeGateTests(unittest.TestCase):
    def test_independent_audit_is_post_runtime_not_a_precondition(self) -> None:
        repo_root = Path(__file__).resolve().parents[5]
        contract = runner.strict_load(repo_root / runner.CONTRACT_RELATIVE)
        gate = runner.validate_minimal_pre_runtime_gate_contract(contract)

        self.assertTrue(gate["central_static_receipt_required_before_runtime"])
        self.assertFalse(gate["fresh_independent_audit_required_before_runtime"])
        self.assertEqual(gate["fresh_independent_audit_timing"], "POST_RUNTIME")


class StoppedStateEvidenceTests(unittest.TestCase):
    @staticmethod
    def result(exit_code: int, process_success: bool) -> dict[str, object]:
        return {
            "exit_code": exit_code,
            "process_success": process_success,
            "launch_error": None,
            "timed_out": False,
        }

    @staticmethod
    def exact_daemon_absence() -> tuple[bytes, bytes]:
        return (
            b"null\r\n",
            (
                b"failed to connect to the docker API at "
                b"npipe:////./pipe/dockerDesktopLinuxEngine; "
                b"The system cannot find the file specified.\r\n"
            ),
        )

    @staticmethod
    def quiet_tasklist() -> bytes:
        return (
            b'"System Idle Process","0","Services","0","8 K"\r\n'
            b'"python.exe","123","Console","1","10 K"\r\n'
        )

    def validate(
        self,
        *,
        daemon_stdout: bytes | None = None,
        daemon_stderr: bytes | None = None,
        wsl_stdout: bytes = b"",
        tasklist_stdout: bytes | None = None,
    ) -> dict[str, object]:
        exact_stdout, exact_stderr = self.exact_daemon_absence()
        return runner.validate_stopped_snapshot(
            self.result(1, False),
            exact_stdout if daemon_stdout is None else daemon_stdout,
            exact_stderr if daemon_stderr is None else daemon_stderr,
            self.result(0, True),
            wsl_stdout,
            b"",
            self.result(0, True),
            self.quiet_tasklist() if tasklist_stdout is None else tasklist_stdout,
            b"",
        )

    def test_exact_composite_stopped_evidence_passes(self) -> None:
        evidence = self.validate()
        self.assertTrue(evidence["passed"])
        self.assertTrue(evidence["docker_server_endpoint_absent"])
        self.assertEqual(evidence["wsl_running_distros"], [])
        self.assertEqual(evidence["docker_processes"], [])

    def test_ambiguous_desktop_status_text_cannot_prove_stopped(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "DOCKER_SERVER_ABSENCE_SIGNATURE_MISMATCH"):
            self.validate(
                daemon_stdout=b"",
                daemon_stderr=b"Could not retrieve status. Is Docker Desktop running?",
            )

    def test_access_denied_daemon_probe_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "DOCKER_SERVER_PROBE_ACCESS_DENIED"):
            self.validate(daemon_stdout=b"", daemon_stderr=b"Access is denied.")

    def test_running_wsl_distro_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "WSL_DISTRO_STILL_RUNNING"):
            self.validate(wsl_stdout="docker-desktop\r\n".encode("utf-16-le"))

    def test_exact_docker_process_is_rejected(self) -> None:
        tasklist = (
            self.quiet_tasklist()
            + b'"Docker Desktop.exe","456","Console","1","100 K"\r\n'
        )
        with self.assertRaisesRegex(RuntimeError, "DOCKER_PROCESS_STILL_RUNNING"):
            self.validate(tasklist_stdout=tasklist)

    def test_non_csv_tasklist_success_cannot_prove_stopped(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "TASKLIST_CSV_INVALID"):
            self.validate(tasklist_stdout=b"No task inventory is available.\r\n")


class FinalResultPublicationTests(unittest.TestCase):
    @staticmethod
    def passing_document() -> dict[str, object]:
        return {
            "passed": True,
            "error_type": None,
            "error": None,
            "verdict": "PASS_R6_C1R3_LINUX_M0_M1_MATERIALIZED_NOT_BENCHMARKED",
        }

    def test_atomic_publication_writes_parseable_authoritative_result(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "runner_result.json"
            document = self.passing_document()
            self.assertTrue(runner.persist_final_result(path, document))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), document)
            self.assertFalse(path.with_name(path.name + ".partial").exists())

    def test_publication_failure_mutates_emitted_document_fail_closed(self) -> None:
        def fail_writer(path: Path, value: dict[str, object]) -> None:
            raise OSError("synthetic publication failure")

        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "runner_result.json"
            document = self.passing_document()
            self.assertFalse(runner.persist_final_result(path, document, fail_writer))
            self.assertFalse(document["passed"])
            self.assertEqual(
                document["verdict"],
                "HANDOFF_INCOMPLETE_R6_C1R3_LINUX_ATTEMPT004_CLOSED",
            )
            self.assertEqual(document["error_type"], "RunnerResultWriteError")
            self.assertIn("synthetic publication failure", str(document["error"]))
            self.assertIn("synthetic publication failure", str(document["runner_result_write_error"]))
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
