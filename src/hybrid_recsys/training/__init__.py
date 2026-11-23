"""Inputs, example construction and training loops used by the research pipeline."""

from hybrid_recsys.training.inputs import (
    FeatureIdentity,
    PipelineInputs,
    build_test_protocol,
    load_pipeline_inputs,
)

__all__ = [
    "FeatureIdentity",
    "PipelineInputs",
    "build_test_protocol",
    "load_pipeline_inputs",
]
