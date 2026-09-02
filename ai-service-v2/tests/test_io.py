from __future__ import annotations

from pathlib import Path

import pytest

from ai_service_v2.data.io import load_canonical_snapshot
from ai_service_v2.errors import IntegrityError

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "fixture-retail-v1"


def test_canonical_fixture_loader_verifies_all_bindings() -> None:
    snapshot = load_canonical_snapshot(FIXTURE_ROOT)
    assert snapshot.manifest.dataset_id == "fixture-retail-v1"
    assert len(snapshot.events_by_split["train"]) == 6
    assert snapshot.raw_item_ids == (100, 50, 75, 25, 10)


def test_canonical_fixture_loader_fails_on_payload_mutation(tmp_path: Path) -> None:
    copied = tmp_path / "fixture"
    copied.mkdir()
    for source in FIXTURE_ROOT.iterdir():
        (copied / source.name).write_bytes(source.read_bytes())
    events = copied / "val.jsonl"
    events.write_text(
        events.read_text(encoding="utf-8").replace('"item_id":2', '"item_id":4'),
        encoding="utf-8",
    )
    with pytest.raises(IntegrityError, match="payload hash"):
        load_canonical_snapshot(copied)
