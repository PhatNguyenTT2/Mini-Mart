# Experimental Log

## Dataset & Evaluation Settings
- E-commerce Mini-Mart dataset
- Total products: 1,380 SKUs (Full-Catalog Evaluation)
- User interactions: 50,000+ rows (Sparsity ~7.2% - 10.0%)
- Train/Val/Test split: 80/10/10 (Hold-out Test Set of 6,188 interactions)
- Single Source of Truth: 10,820 Apriori rules exported to `lift_map.json`

## Hyperparameters
- Embedding dim: 768 (SBERT frozen)
- User Tower hidden: [72, 128, 64]
- Item Tower hidden: [88, 64, 64]
- Wide Branch: log1p + MLP [1, 16, 1]
- Batch size: 512
- Learning rate: 1e-3
- Optimizer: Adam
- Temperature τ: 0.1
- Negative sampling ratio: 1:4 (during training only)

## Performance Comparison (Full-Catalog Ranking on 1,380 SKUs)
| Model / Algorithm       | Architecture / Signals Used       | Hit Rate@10 | NDCG@10 | GAUC   |
|-------------------------|-----------------------------------|-------------|---------|--------|
| Rule-based Apriori      | Wide-Only (Rules)                 | 0.0700      | 0.0104  | 0.7575 |
| Semantic Content-Based  | Deep-Only Text (SBERT Centroid)   | 0.3260      | 0.0402  | 0.6869 |
| Item-Item CF            | Behavioral History (Co-occurrence)| 0.4720      | 0.0734  | 0.8488 |
| Random Base             | Untrained (Sanity Check)          | 0.1620      | 0.0191  | 0.5324 |
| Noisy 10% Hybrid        | Cross-Persona Noise Injection     | 0.4200      | 0.0558  | 0.8463 |
| Deep-Only Two-Tower     | SBERT + Categorical Features      | 0.4840      | 0.0782  | 0.8501 |
| **Proposed Hybrid**     | **Wide (Apriori) + Deep (SBERT)** | **0.4940**  | **0.0644**| **0.8507**|

*Note: The Trade-off analysis shows the Wide branch improves Hit Rate (+1.00%) for better coverage, while inducing a slight drop in NDCG (-0.0138).*

## Latency Analysis (100 candidates scoring)
| Runtime Architecture | Latency (ms) | Speedup |
|----------------------|--------------|---------|
| PyTorch (.pt)        | ~12.50       | 1x      |
| ONNX Runtime         | ~0.85        | ~14.7x  |
