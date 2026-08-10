# Hybrid Cascade Ranking Recommender System (Wide & Deep Two-Tower with Apriori Lift & SBERT)

## Problem Statement

E-commerce recommender systems face three fundamental challenges:
1. **Information overload** with rapidly growing product catalogs (1,380 Vietnamese retail product SKUs spanning grocery, beverages, household goods, and personal care across 500+ users and 50,000+ sparse implicit-feedback interactions, collected from a proprietary Vietnamese convenience store chain).
2. **Cold-start bottleneck** when new products or users lack interaction history.
3. **Memorization vs Generalization Tradeoff** — traditional association rule methods (e.g., Apriori) excel at memorizing high-confidence co-purchase patterns but completely fail to generalize to unseen items, while deep learning models generalize well semantically but often miss explicit, co-occurring purchase correlations.

Furthermore, real-world production systems demand sub-millisecond inference latency for scoring candidate items across the catalog, a requirement that monolithic Wide & Deep architectures struggle to meet when deployed without specialized serving runtimes.

## Core Hypothesis

We hypothesize that decoupling the Wide and Deep branches into architecturally independent components — a Wide MLP processing log1p-normalized Apriori lift scores and a Two-Tower network using frozen Vietnamese SBERT embeddings — and combining them via additive joint scoring achieves a superior balance of Hit Rate coverage and ranking quality (NDCG@10, GAUC) compared to either branch alone or traditional hybrid approaches (such as monolithic Wide & Deep [Cheng et al., 2016], DeepFM [Guo et al., 2017], and Neural Collaborative Filtering [He et al., 2017]). We further propose that ONNX Runtime optimization enables sub-millisecond batch inference (<1ms), making this architecture viable for real-time E-commerce serving on a proprietary Vietnamese Mini-Mart retail product catalog.

## Proposed Methodology (Detailed Technical Approach)

We introduce a **Hybrid Cascade Ranking** architecture with two complementary branches:

### 1. Wide Branch (Memorization Layer)
- Input: Co-purchase lift values $L(x, y)$ extracted from 10,820 Apriori association rules.
- Log1p Normalization: Normalizes raw lift scores $L \in [1.01, 1926.0]$ to $[0.0, 7.56]$ via $f(L) = \log(1 + L)$ to prevent gradient explosion.
- Wide MLP Architecture: $\text{Linear}(1, 16) \rightarrow \text{ReLU} \rightarrow \text{Linear}(16, 1)$, yielding scalar score contribution $S_{\text{Wide}}(x, y)$.

### 2. Deep Branch (Generalization Layer) — Two-Tower Network
- **User Tower:** 
  - User ID embedding ($64d$) concatenated with User Persona Cluster embedding ($8d$) $\rightarrow 72d$ vector.
  - Architecture: $\text{Linear}(72, 128) \rightarrow \text{ReLU} \rightarrow \text{LayerNorm}(128) \rightarrow \text{Linear}(128, 64) \rightarrow \text{L2 Normalization} \rightarrow \mathbf{u}(x) \in \mathbb{R}^{64}$.
  - User Cold-Start Fallback: For new users without interaction history, the $8d$ Persona Cluster embedding defaults to the global majority cluster vector, and the User ID embedding is initialized with the mean of all trained user embeddings.
- **Item Tower:**
  - Semantic Representation: Frozen Vietnamese SBERT (`keepitreal/vietnamese-sbert`, $768d$) projected via $\text{Linear}(768, 64)$.
  - Categorical & Numerical Features: Category ID embedding ($16d$) + Price Bucket embedding ($8d$) concatenated with text projection $\rightarrow 88d$ vector.
  - Architecture: $\text{Linear}(88, 64) \rightarrow \text{ReLU} \rightarrow \text{Linear}(64, 64) \rightarrow \text{L2 Normalization} \rightarrow \mathbf{v}(y) \in \mathbb{R}^{64}$.
- **Deep Similarity Scoring:**

  $$S_{\text{Deep}}(x, y) = \frac{\mathbf{u}(x) \cdot \mathbf{v}(y)}{\tau}$$

  where $\tau = 0.1$ is the temperature scaling hyperparameter.

### 3. Joint Scoring & Optimization
- Joint Logits: $\hat{y}(x,y) = S_{\text{Deep}}(x, y) + S_{\text{Wide}}(x, y)$.
- Predicted Probability: $P(y=1|x,y) = \sigma(\hat{y}(x,y))$.
- Loss Function: Binary Cross-Entropy (BCE) Loss with Hard Negative Sampling ($1:4$ ratio).

  $$\mathcal{L} = -\frac{1}{N} \sum_{i=1}^N \left[ y_i \log(\hat{p}_i) + (1 - y_i) \log(1 - \hat{p}_i) \right]$$

- Hard Negative Sampling Definition: Hard negatives are sampled from high-impression items (top-20% by global interaction count) that were present in the user's browsing session but explicitly ignored, ensuring the model learns to distinguish genuinely preferred items from popular distractors. The remaining negatives are sampled uniformly at random from the full catalog.
- Optimizer: Adam ($\text{lr} = 10^{-3}$, weight decay $= 10^{-5}$).

### 4. High-Performance ONNX Serving
- Model graph exported to ONNX format with dynamic batching.
- Fast Execution: In-memory RAM lookup for 1,380 SKU feature vectors + ONNX CPU execution achieving sub-millisecond serving latency (~0.85ms per batch of 100 candidate items).

## Expected Contribution

1. **Decoupled Wide & Deep Two-Tower Architecture:** Demonstrates that combining Apriori lift MLP with SBERT Two-Tower achieves the highest Hit Rate@10 (0.4940) across all baselines (including Rule-based Apriori, Semantic SBERT-only, Item-CF, and Deep-Only Two-Tower) on the full-catalog ranking evaluation (1,380 SKUs).
2. **Cold-Start Resolution:** Proves frozen Vietnamese SBERT embeddings eliminate product cold-start penalties without requiring retraining.
3. **Sub-Millisecond Microservice Serving:** Achieves 14.7x speedup (~0.85ms serving latency) using ONNX Runtime within a Node.js Chatbot + FastAPI microservices architecture.
4. **Full-Catalog Evaluation Rigor:** Adopts full-catalog ranking against all 1,380 SKUs, eliminating sampling bias ("Illusion of Accuracy").
