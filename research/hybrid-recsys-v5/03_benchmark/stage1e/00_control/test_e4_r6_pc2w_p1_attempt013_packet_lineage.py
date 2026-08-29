#!/usr/bin/env python3
"""Public-seam tests for the pure Attempt-013 packet-lineage predicate."""

from __future__ import annotations

from dataclasses import replace
import unittest

from e4_r6_pc2w_p1_attempt013_packet_lineage import (
    DeltaEntry,
    OriginBinding,
    PacketBlobFact,
    PacketLineageError,
    PacketLineageObservation,
    PacketLineageSpec,
    validate_packet_lineage,
)


CONTROL = "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
R0 = "ce6377c351625ed7e029f2883520583ca97fc2b8"
R1 = "294422ca8557e4b55ae3863d853289e2232011b2"
R2A = "b" * 40
R2 = "c" * 40


def packet_path(index: int) -> str:
    return f"{CONTROL}lineage_fixture_{index:02d}.json"


def blob(path: str, marker: str = "a") -> PacketBlobFact:
    return PacketBlobFact(path=path, raw_bytes=100, raw_sha256=marker * 64)


def unchanged(path: str, origin_commit: str, marker: str = "a") -> OriginBinding:
    return OriginBinding(
        path=path,
        origin_commit=origin_commit,
        origin_raw_bytes=100,
        origin_raw_sha256=marker * 64,
        final_raw_bytes=100,
        final_raw_sha256=marker * 64,
    )


class PacketLineageTests(unittest.TestCase):
    def assert_lineage_error(
        self,
        code: str,
        spec: PacketLineageSpec,
        observation: PacketLineageObservation,
    ) -> None:
        with self.assertRaises(PacketLineageError) as raised:
            validate_packet_lineage(spec, observation)
        self.assertEqual(raised.exception.code, code)

    def r2_case(self) -> tuple[PacketLineageSpec, PacketLineageObservation]:
        roster = tuple(packet_path(index) for index in range(13))
        frozen = tuple(unchanged(path, R0) for path in roster[:4])
        support = tuple(
            unchanged(path, R1 if index < 6 else R2A)
            for index, path in enumerate(roster[4:9], start=4)
        )
        delta = tuple(DeltaEntry("M", path) for path in roster[9:])
        return (
            PacketLineageSpec(
                aggregate_roster=roster,
                frozen_r0_bindings=frozen,
                support_bindings=support,
                sealing_parent=R2A,
                expected_sealing_delta=delta,
            ),
            PacketLineageObservation(
                packet_commit=R2,
                packet_parents=(R2A,),
                observed_sealing_delta=delta,
                final_packet_blobs=tuple(blob(path) for path in roster),
                packet_is_ancestor_of_execution_head=True,
            ),
        )

    def test_r1_lineage_accepts_roster_independent_of_six_addition_seal(self) -> None:
        roster = tuple(packet_path(index) for index in range(10))
        frozen = tuple(unchanged(path, R0) for path in roster[:4])
        delta = tuple(DeltaEntry("A", path) for path in roster[4:])
        evidence = validate_packet_lineage(
            PacketLineageSpec(
                aggregate_roster=roster,
                frozen_r0_bindings=frozen,
                support_bindings=(),
                sealing_parent=R0,
                expected_sealing_delta=delta,
            ),
            PacketLineageObservation(
                packet_commit=R1,
                packet_parents=(R0,),
                observed_sealing_delta=delta,
                final_packet_blobs=tuple(blob(path) for path in roster),
                packet_is_ancestor_of_execution_head=True,
            ),
        )
        self.assertTrue(evidence.predicate_passed)

    def test_r2_lineage_accepts_thirteen_blob_roster_and_four_modification_seal(self) -> None:
        spec, observation = self.r2_case()
        evidence = validate_packet_lineage(spec, observation)
        self.assertEqual(evidence.aggregate_roster_count, 13)
        self.assertEqual(evidence.sealing_delta_count, 4)

    def test_rejects_incomplete_roster_partition(self) -> None:
        spec, observation = self.r2_case()
        incomplete = replace(spec, support_bindings=spec.support_bindings[:-1])
        with self.assertRaises(PacketLineageError) as raised:
            validate_packet_lineage(incomplete, observation)
        self.assertEqual(raised.exception.code, "ROSTER_PARTITION_MISMATCH")

    def test_rejects_missing_final_packet_blob(self) -> None:
        spec, observation = self.r2_case()
        incomplete = replace(
            observation, final_packet_blobs=observation.final_packet_blobs[:-1]
        )
        self.assert_lineage_error("FINAL_BLOB_ROSTER_MISMATCH", spec, incomplete)

    def test_rejects_wrong_parent(self) -> None:
        spec, observation = self.r2_case()
        wrong = replace(observation, packet_parents=(R1,))
        self.assert_lineage_error("PACKET_PARENT_MISMATCH", spec, wrong)

    def test_rejects_multiple_parents(self) -> None:
        spec, observation = self.r2_case()
        merge = replace(observation, packet_parents=(R2A, R1))
        self.assert_lineage_error("PACKET_PARENT_MISMATCH", spec, merge)

    def test_rejects_missing_sealing_path(self) -> None:
        spec, observation = self.r2_case()
        missing = replace(
            observation,
            observed_sealing_delta=observation.observed_sealing_delta[:-1],
        )
        self.assert_lineage_error("SEALING_DELTA_MISMATCH", spec, missing)

    def test_rejects_extra_sealing_path(self) -> None:
        spec, observation = self.r2_case()
        extra = replace(
            observation,
            observed_sealing_delta=(
                *observation.observed_sealing_delta,
                DeltaEntry("M", f"{CONTROL}unexpected_seal.json"),
            ),
        )
        self.assert_lineage_error("SEALING_DELTA_MISMATCH", spec, extra)

    def test_rejects_wrong_sealing_status(self) -> None:
        spec, observation = self.r2_case()
        wrong = replace(
            observation,
            observed_sealing_delta=(
                DeltaEntry("A", observation.observed_sealing_delta[0].path),
                *observation.observed_sealing_delta[1:],
            ),
        )
        self.assert_lineage_error("SEALING_DELTA_MISMATCH", spec, wrong)

    def test_rejects_rename_or_copy_status(self) -> None:
        spec, observation = self.r2_case()
        renamed = replace(
            observation,
            observed_sealing_delta=(
                DeltaEntry("R100", observation.observed_sealing_delta[0].path),
                *observation.observed_sealing_delta[1:],
            ),
        )
        self.assert_lineage_error("INVALID_DELTA_STATUS", spec, renamed)

    def test_rejects_casefold_duplicate_roster_path(self) -> None:
        spec, observation = self.r2_case()
        duplicate = spec.aggregate_roster[-1][:-4] + "JSON"
        invalid = replace(spec, aggregate_roster=(*spec.aggregate_roster, duplicate))
        self.assert_lineage_error("DUPLICATE_PACKET_PATH", invalid, observation)

    def test_rejects_path_outside_control_root(self) -> None:
        spec, observation = self.r2_case()
        invalid = replace(
            spec, aggregate_roster=("research/outside.json", *spec.aggregate_roster[1:])
        )
        self.assert_lineage_error("INVALID_PACKET_PATH", invalid, observation)

    def test_rejects_frozen_origin_blob_drift(self) -> None:
        spec, observation = self.r2_case()
        drifted = replace(spec.frozen_r0_bindings[0], final_raw_bytes=101)
        invalid = replace(
            spec, frozen_r0_bindings=(drifted, *spec.frozen_r0_bindings[1:])
        )
        self.assert_lineage_error("ORIGIN_BLOB_DRIFT", invalid, observation)

    def test_rejects_final_blob_disagreeing_with_frozen_binding(self) -> None:
        spec, observation = self.r2_case()
        rebound = replace(
            spec.frozen_r0_bindings[0],
            origin_raw_sha256="b" * 64,
            final_raw_sha256="b" * 64,
        )
        invalid = replace(
            spec, frozen_r0_bindings=(rebound, *spec.frozen_r0_bindings[1:])
        )
        self.assert_lineage_error("FINAL_BLOB_BINDING_MISMATCH", invalid, observation)

    def test_rejects_support_origin_blob_drift(self) -> None:
        spec, observation = self.r2_case()
        drifted = replace(spec.support_bindings[0], final_raw_sha256="b" * 64)
        invalid = replace(
            spec, support_bindings=(drifted, *spec.support_bindings[1:])
        )
        self.assert_lineage_error("ORIGIN_BLOB_DRIFT", invalid, observation)

    def test_rejects_overlapping_roster_partitions(self) -> None:
        spec, observation = self.r2_case()
        overlap = replace(
            spec.support_bindings[0], path=spec.frozen_r0_bindings[0].path
        )
        invalid = replace(spec, support_bindings=(overlap, *spec.support_bindings[1:]))
        self.assert_lineage_error("ROSTER_PARTITION_MISMATCH", invalid, observation)

    def test_rejects_packet_not_ancestor_of_execution_head(self) -> None:
        spec, observation = self.r2_case()
        invalid = replace(observation, packet_is_ancestor_of_execution_head=False)
        self.assert_lineage_error(
            "PACKET_NOT_ANCESTOR_OF_EXECUTION_HEAD", spec, invalid
        )

    def test_rejects_aggregate_roster_manipulation_with_unchanged_seal(self) -> None:
        spec, observation = self.r2_case()
        added_path = f"{CONTROL}aggregate_only_extra.json"
        invalid_spec = replace(
            spec, aggregate_roster=(*spec.aggregate_roster, added_path)
        )
        invalid_observation = replace(
            observation,
            final_packet_blobs=(*observation.final_packet_blobs, blob(added_path)),
        )
        self.assert_lineage_error(
            "ROSTER_PARTITION_MISMATCH", invalid_spec, invalid_observation
        )

    def test_rejects_duplicate_final_blob_fact(self) -> None:
        spec, observation = self.r2_case()
        duplicate = replace(
            observation,
            final_packet_blobs=(
                *observation.final_packet_blobs,
                observation.final_packet_blobs[-1],
            ),
        )
        self.assert_lineage_error("DUPLICATE_PACKET_PATH", spec, duplicate)


if __name__ == "__main__":
    unittest.main()
