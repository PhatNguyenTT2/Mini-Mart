from __future__ import annotations

from pathlib import Path

import pytest

from ai_service_v2.adapters.v5_source import materialize_v5_source_bundle
from ai_service_v2.cli import main
from ai_service_v2.data.rules import AprioriRuleTable
from ai_service_v2.data.suitability import assess_snapshot_suitability
from ai_service_v2.errors import IntegrityError
from ai_service_v2.protocol import build_protocol
from tests.source_bundle_fixture import build_v5_source_bundle


def test_source_bundle_materializes_raw_mappings_origins_and_baskets(tmp_path: Path) -> None:
    source = build_v5_source_bundle(tmp_path / "source")
    output = tmp_path / "canonical"

    snapshot = materialize_v5_source_bundle(source, output)

    assert snapshot.raw_user_ids == (10, 20, 30, 40)
    assert snapshot.raw_item_ids == (10, 25, 50, 75, 100)
    assert snapshot.events_by_split["val"][0].raw_event_id == "event-006"
    assert snapshot.events_by_split["val"][0].event_origin == "organic"
    assert [basket.origin for basket in snapshot.training_baskets] == [
        "organic",
        "semantic_trap",
    ]
    assert snapshot.manifest.behavior_nature == "CONTROLLED_GENERATED_BEHAVIOR"
    assert snapshot.manifest.observed_behavior is False
    assert snapshot.manifest.source_artifact_hashes["generator_spec_source"] == "5" * 64
    assert (
        snapshot.manifest.source_artifact_hashes["generator_spec_source"]
        != snapshot.manifest.source_artifact_hashes["benchmark_spec.json"]
    )
    assert snapshot.manifest.source_artifact_hashes["catalog_audit"] == "3" * 64
    assert {path.name for path in output.iterdir()} == {
        "manifest.json",
        "users.jsonl",
        "items.jsonl",
        "baskets.jsonl",
        "train.jsonl",
        "val.jsonl",
        "test.jsonl",
    }


def test_source_bundle_rejects_a_hash_mutation(tmp_path: Path) -> None:
    source = build_v5_source_bundle(tmp_path / "source")
    with (source / "users.jsonl").open("ab") as stream:
        stream.write(b" ")

    with pytest.raises(IntegrityError, match="source file hash"):
        materialize_v5_source_bundle(source, tmp_path / "canonical")


def test_protocol_uses_only_novel_organic_purchase_truth(tmp_path: Path) -> None:
    snapshot = materialize_v5_source_bundle(
        build_v5_source_bundle(tmp_path / "source"), tmp_path / "canonical"
    )

    protocol = build_protocol(snapshot, split="val", cutoff=5)

    assert protocol.eligible_user_ids == (0,)
    assert protocol.case_for(0).positive_item_ids == frozenset({3})
    assert protocol.manifest.positive_rule == "organic_purchase_events_minus_all_history_items"


def test_apriori_uses_only_organic_training_baskets(tmp_path: Path) -> None:
    snapshot = materialize_v5_source_bundle(
        build_v5_source_bundle(tmp_path / "source"), tmp_path / "canonical"
    )

    rules = AprioriRuleTable.fit(snapshot)

    assert rules.basket_count == 1
    assert rules.pair_confidence == {(2, 4): 1.0, (4, 2): 1.0}
    assert (1, 3) not in rules.pair_confidence


def test_cli_materializes_an_admitted_v5_source_bundle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = build_v5_source_bundle(tmp_path / "source")
    output = tmp_path / "canonical"

    assert main(["materialize-v5-source", str(source), str(output)]) == 0
    assert '"status": "PASS"' in capsys.readouterr().out
    assert (output / "manifest.json").is_file()
    assert main(["assess-snapshot", str(output)]) == 0
    assert "PASS_CONTROLLED_INTERNAL_DATASET_SUITABILITY" in capsys.readouterr().out


def test_suitability_report_is_validation_only_and_classifies_generated_data(
    tmp_path: Path,
) -> None:
    snapshot = materialize_v5_source_bundle(
        build_v5_source_bundle(tmp_path / "source"), tmp_path / "canonical"
    )

    report = assess_snapshot_suitability(snapshot)

    assert report.verdict == "PASS_CONTROLLED_INTERNAL_DATASET_SUITABILITY"
    assert report.dataset_classification == "CONTROLLED_GENERATED_BEHAVIOR"
    assert report.distinct_user_item_cells == 8
    assert report.distinct_cell_density == pytest.approx(0.4)
    assert report.validation_eligible_users == 1
    assert report.organic_training_baskets == 1
    assert report.test_set_opened is False


def test_pending_post_export_language_audit_blocks_dataset_admission(tmp_path: Path) -> None:
    snapshot = materialize_v5_source_bundle(
        build_v5_source_bundle(tmp_path / "source", language_status="PENDING_POST_EXPORT_AUDIT"),
        tmp_path / "canonical",
    )

    report = assess_snapshot_suitability(snapshot)

    assert report.verdict == "INCOMPLETE_DATASET_SUITABILITY"
    assert report.checks["catalog_language_admitted"] is False
    assert "catalog_language_admitted" in report.blocking_findings

    protocol_path = tmp_path / "protocol.json"
    assert (
        main(
            [
                "build-protocol",
                str(tmp_path / "canonical"),
                str(protocol_path),
                "--cutoff",
                "5",
            ]
        )
        == 0
    )
    run_root = tmp_path / "blocked-run"
    assert (
        main(
            [
                "train",
                str(tmp_path / "canonical"),
                str(protocol_path),
                str(run_root),
            ]
        )
        == 2
    )
    assert not run_root.exists()
