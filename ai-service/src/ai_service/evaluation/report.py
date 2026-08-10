"""Lineage-backed JSON and Markdown evaluation reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ai_service.errors import ArtifactIntegrityError

SHA256_HEX_LENGTH = 64


def write_evaluation_report(
    output_dir: Path,
    *,
    payload: dict[str, Any],
    lineage: dict[str, str],
) -> tuple[Path, Path]:
    required = {"snapshot", "embedding", "rules", "checkpoint"}
    if set(lineage) != required or any(
        len(value) != SHA256_HEX_LENGTH for value in lineage.values()
    ):
        raise ArtifactIntegrityError("evaluation report requires complete SHA-256 lineage")
    output_dir.mkdir(parents=True, exist_ok=False)
    document = {"schema_version": "3.0.0", "lineage": lineage, "results": payload}
    json_bytes = json.dumps(document, indent=2, sort_keys=True).encode("utf-8")
    json_path = output_dir / "report.json"
    json_path.write_bytes(json_bytes)
    checksum = hashlib.sha256(json_bytes).hexdigest()
    markdown_path = output_dir / "report.md"
    markdown_path.write_text(
        "# AI Service Evaluation\n\n"
        f"- Report SHA-256: `{checksum}`\n"
        f"- Snapshot: `{lineage['snapshot']}`\n"
        f"- Checkpoint: `{lineage['checkpoint']}`\n",
        encoding="utf-8",
    )
    return json_path, markdown_path
