"""Small smoke controls and later proposed model implementations."""

from ai_service_v2.models.baselines import MostPopScorer, RandomScorer
from ai_service_v2.models.proposed import (
    HybridScorer,
    ItemFeatureMatrix,
    RuleOnlyScorer,
    TrainedTwoTower,
    TrainingReport,
    TwoTowerConfig,
    item_text_hash_features,
    train_two_tower,
)
from ai_service_v2.models.registry import (
    MODEL_KINDS,
    LocalModelBundle,
    ModelRunSpec,
    default_spec,
    descriptor_for_spec,
    train_local_model,
)

__all__ = [
    "MODEL_KINDS",
    "HybridScorer",
    "ItemFeatureMatrix",
    "LocalModelBundle",
    "ModelRunSpec",
    "MostPopScorer",
    "RandomScorer",
    "RuleOnlyScorer",
    "TrainedTwoTower",
    "TrainingReport",
    "TwoTowerConfig",
    "default_spec",
    "descriptor_for_spec",
    "item_text_hash_features",
    "train_local_model",
    "train_two_tower",
]
