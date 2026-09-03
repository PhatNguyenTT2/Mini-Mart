"""Model-independent ranking evaluation."""

from ai_service_v2.evaluation.artifacts import (
    MaterializedScores,
    MatrixScoreProvider,
    ScoreChunk,
    load_materialized_scores,
    load_score_matrix,
    materialize_scores,
)
from ai_service_v2.evaluation.components import (
    HybridScoreComponents,
    load_hybrid_score_components,
)
from ai_service_v2.evaluation.evaluator import (
    EvaluationResult,
    FullCatalogEvaluator,
    evaluator_implementation_sha256,
    evaluator_source_hashes,
)
from ai_service_v2.evaluation.metrics import UserMetrics, ranking_metrics, user_auc
from ai_service_v2.evaluation.persistence import (
    PersistedEvaluation,
    load_evaluation,
    save_evaluation,
)

__all__ = [
    "EvaluationResult",
    "FullCatalogEvaluator",
    "HybridScoreComponents",
    "MaterializedScores",
    "MatrixScoreProvider",
    "PersistedEvaluation",
    "ScoreChunk",
    "UserMetrics",
    "evaluator_implementation_sha256",
    "evaluator_source_hashes",
    "load_evaluation",
    "load_hybrid_score_components",
    "load_materialized_scores",
    "load_score_matrix",
    "materialize_scores",
    "ranking_metrics",
    "save_evaluation",
    "user_auc",
]
