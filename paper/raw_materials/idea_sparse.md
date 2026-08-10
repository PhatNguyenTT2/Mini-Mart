# Research Idea: Hybrid Cascade Ranking Recommender System: Wide (Apriori) + Deep (Two-Tower with SBERT)

## Problem Statement
E-commerce systems face information overload, cold-start issues, and the memorization-vs-generalization tradeoff in product recommendation. Furthermore, highly sparse implicit datasets often render traditional behavioral algorithms (like CF) ineffective.

## Core Contribution
A hybrid cascade ranking architecture combining:
1. **Wide Branch (Memorization):** Utilizes 10,820 Apriori co-purchase rules (lift map). To solve the scale mismatch problem (raw lift ranges from 1.01 to 1926.0), we introduce a `log1p` normalization step followed by a Wide MLP (`Linear(1,16) -> ReLU -> Linear(16,1)`).
2. **Deep Branch (Generalization):** A Two-Tower Network using frozen Vietnamese SBERT embeddings (768-dim) for semantic understanding, combined with categorical features (Price Bucket, Category ID).
3. **Evaluation Protocol:** Strict adherence to Full-Catalog Ranking across 1,380 SKUs to eliminate the "Illusion of Accuracy" caused by Sampled Metrics.
4. **ONNX Runtime Serving:** Sub-millisecond inference (<1ms) on a microservices architecture.

## Methodology
- Cascade 2-stage pipeline: Candidate Retrieval -> Re-ranking
- Item Tower: Frozen SBERT -> 768-dim semantic vectors
- User Tower: Persona cluster encoding + interaction history
- Wide Score: Wide_MLP(log1p(Apriori_Lift))
- Deep Score: Dot(u(x), v(y)) / (||u(x)|| * ||v(y)|| * τ)
- Joint Score: Logits = Score_Deep + Score_Wide
- Training: Hard Negative Sampling (1:4 ratio), BCE Loss
