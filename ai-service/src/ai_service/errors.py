"""Custom exception hierarchy for ai_service module."""


class AIServiceError(Exception):
    """Base exception for all ai_service errors."""
    pass


class ConfigurationError(AIServiceError):
    """Raised when configuration parameters or environment variables are invalid."""
    pass


class SourceReadError(AIServiceError):
    """Raised when reading from PostgreSQL or synthetic data source fails."""
    pass


class DataIntegrityError(AIServiceError):
    """Raised when temporal invariants or cold-start isolation constraints are violated."""
    pass


class ModelTrainingError(AIServiceError):
    """Raised when model training, validation evaluation, or optimization fails."""
    pass


class ExportError(AIServiceError):
    """Raised when ONNX export or model bundle packaging fails."""
    pass


class InferenceError(AIServiceError):
    """Raised when ONNX runtime prediction fails during serving."""
    pass
