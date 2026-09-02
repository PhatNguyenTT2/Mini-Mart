"""Clean, reference-bound research runner for the recommender benchmark."""

__version__ = "0.1.0"

from ai_service_v2.contracts import (
    DatasetManifest,
    EvaluationReceipt,
    ModelDescriptor,
    ProtocolManifest,
    RunManifest,
    ScoreArtifactManifest,
)

__all__ = [
    "DatasetManifest",
    "EvaluationReceipt",
    "ModelDescriptor",
    "ProtocolManifest",
    "RunManifest",
    "ScoreArtifactManifest",
    "__version__",
]
