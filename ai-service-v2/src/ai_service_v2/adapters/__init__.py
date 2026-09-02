"""Adapters at the reference-training and score-export seam."""

from ai_service_v2.adapters.base import CheckpointRef, ModelAdapter, RunSpec
from ai_service_v2.adapters.v5_family_view import materialize_v5_family_view
from ai_service_v2.adapters.v5_source import materialize_v5_source_bundle

__all__ = [
    "CheckpointRef",
    "ModelAdapter",
    "RunSpec",
    "materialize_v5_family_view",
    "materialize_v5_source_bundle",
]
