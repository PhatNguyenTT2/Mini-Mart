"""Low-cardinality Prometheus metrics for the serving path."""

from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("ai_recommend_requests_total", "Recommendation requests", ["status"])
INFERENCE_SECONDS = Histogram(
    "ai_inference_seconds",
    "ONNX inference duration",
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1),
)
CANDIDATE_COUNT = Histogram(
    "ai_candidate_count", "Candidates per request", buckets=(1, 8, 16, 32, 64, 128, 256)
)
READY = Gauge("ai_model_ready", "Whether a verified model bundle is loaded")
