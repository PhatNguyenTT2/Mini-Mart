"""Typed failures exposed by the ai_service module interfaces."""


class AIServiceError(RuntimeError):
    """Base error for failures callers may handle."""


class ConfigurationError(AIServiceError):
    """Configuration is absent, invalid, or unsafe for the current environment."""


class SourceReadError(AIServiceError):
    """A configured source cannot produce the required immutable input."""


class DataIntegrityError(AIServiceError):
    """Input data violates temporal, catalog, or cold-partition invariants."""


class ArtifactIntegrityError(AIServiceError):
    """An artifact is missing, corrupt, or belongs to another lineage."""


class NegativeSamplingError(AIServiceError):
    """A valid negative candidate set cannot be sampled."""


class ModelTrainingError(AIServiceError):
    """Training cannot safely continue."""


class CatastrophicTrainingError(ModelTrainingError):
    """Training encountered non-finite logits/loss or GAUC collapsed below random."""


class TrainingInterruptedError(ModelTrainingError):
    """A resumable interruption, such as a configured wall-time limit."""


class TrainingGateError(AIServiceError):
    """A validation or checkpoint gate failed."""


class VictoryGateError(AIServiceError):
    """Evaluation failed to satisfy the required victory matrix criteria."""


class ExportValidationError(AIServiceError):
    """ONNX export, parity, or latency verification failed."""


class ServingUnavailableError(AIServiceError):
    """The immutable serving bundle is not ready."""
