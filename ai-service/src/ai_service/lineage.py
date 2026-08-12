"""Strict lineage resolution for the active v5 benchmark campaign.

The pipeline used to rebuild the ``snapshot/embedding/rules`` mapping at each
call site.  This module is the single seam that turns the three immutable
manifests into the six-field v5 lineage required by R3/R4.
"""

from __future__ import annotations

from ai_service.contracts import (
    ArtifactLineage,
    ArtifactLineageV5,
    EmbeddingManifest,
    RuleManifest,
    SnapshotManifest,
)
from ai_service.errors import ArtifactIntegrityError


def resolve_artifact_lineage(
    snapshot_manifest: SnapshotManifest,
    embedding_manifest: EmbeddingManifest,
    rule_manifest: RuleManifest,
    *,
    require_v5: bool = True,
) -> ArtifactLineage | ArtifactLineageV5:
    """Resolve and validate one immutable artifact lineage.

    ``require_v5=False`` is retained only for schema-2 test/synthetic adapters;
    all schema-3 production callers must use the six-field result.
    """

    snapshot_sha = snapshot_manifest.content_sha256
    embedding_snapshot_sha = getattr(embedding_manifest, "snapshot_sha256", None)
    rule_snapshot_sha = getattr(rule_manifest, "snapshot_sha256", None)
    if embedding_snapshot_sha is not None and embedding_snapshot_sha != snapshot_sha:
        raise ArtifactIntegrityError("embedding does not belong to snapshot")
    if rule_snapshot_sha is not None and rule_snapshot_sha != snapshot_sha:
        raise ArtifactIntegrityError("rules do not belong to snapshot")
    metadata = (
        getattr(snapshot_manifest, "benchmark_spec_sha256", None),
        getattr(snapshot_manifest, "semantic_cohort_sha256", None),
        getattr(snapshot_manifest, "order_metadata_sha256", None),
    )
    if all(isinstance(value, str) for value in metadata):
        return ArtifactLineageV5(
            snapshot=snapshot_sha,
            embedding=embedding_manifest.content_sha256,
            rules=rule_manifest.content_sha256,
            benchmark_spec=metadata[0],
            semantic_cohort=metadata[1],
            order_metadata=metadata[2],
        )
    if require_v5:
        raise ArtifactIntegrityError("expanded lineage for v5 is missing benchmark metadata hashes")
    return ArtifactLineage(
        snapshot_sha256=snapshot_sha,
        embedding_sha256=embedding_manifest.content_sha256,
        rule_sha256=rule_manifest.content_sha256,
    )


def require_v5_lineage(value: ArtifactLineage | ArtifactLineageV5) -> ArtifactLineageV5:
    """Reject legacy three-field lineage at an active R3/R4 boundary."""
    if not isinstance(value, ArtifactLineageV5):
        raise ArtifactIntegrityError("active v5 path requires six-field artifact lineage")
    return value


__all__ = ["require_v5_lineage", "resolve_artifact_lineage"]
