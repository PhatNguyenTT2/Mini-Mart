# 🔬 BÁO CÁO TỔNG QUAN QUÉT SÂU KIẾN TRÚC HỆ THỐNG (ARCHITECTURE DEEP SCAN REPORT)

> **Mục đích:** Phân tích toàn bộ luồng kiến trúc end-to-end từ Mạng Nơ-ron Two-Tower đến Microservices Serving (`ai-service` + `chatbot-service`) nhằm cung cấp bức tranh dữ liệu chuẩn xác cho việc thiết kế sơ đồ & biểu đồ (Phase 2.4).

---

## 1. Sơ Đồ Khối Luồng Dữ Liệu End-to-End (End-to-End Microservice Flow)

```
[User Request / Web Chatbot]
           │
           ▼
┌────────────────────────────────────────────────────────────────────────┐
│ backend/services/chatbot (Node.js Service)                              │
│                                                                        │
│ 1. RAG Candidate Retrieval (pgvector / SBERT text search)              │
│ 2. Apriori Cross-Sell Injection (_getAprioriCandidates via PostgreSQL) │
│ 3. AIClient (Circuit Breaker: CLOSED | OPEN | HALF_OPEN, SLA = 300ms)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP POST /recommend
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ ai-service (FastAPI AI Inference Microservice)                         │
│                                                                        │
│ 1. Singleton RAM Cache (1,380 SKUs features + 10,820 Apriori lifts)    │
│ 2. Batch Tensor Construction (User, Persona, Cat, Price, SBERT, Lift)  │
│ 3. ONNX Runtime CPU Engine (two_tower.onnx execution < 1ms)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         [Fallback Circuit Breaker]
                                    │
                                    ▼ (If ONNX fails/trips)
┌────────────────────────────────────────────────────────────────────────┐
│ Legacy White-box Ensemble (α/β/γ/δ Fallback Service)                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Chi Tiết Kiến Trúc Mạng Nơ-ron (Neural Two-Tower & Wide MLP)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PROPOSED HYBRID MODEL ARCHITECTURE                             │
├──────────────────────────────────────────────────────────────┬─────────────────────────────────┤
│ WIDE BRANCH (Memorization)                                   │ DEEP BRANCH (Generalization)    │
│                                                              │                                 │
│ Input: Co-purchase Lift L(x,y)                               │ USER TOWER:                     │
│    │                                                         │   User ID (64d)                 │
│    ▼                                                         │   Persona Cluster (8d)          │
│ log1p Normalization: log(1 + L)                              │      │                          │
│    │                                                         │      ▼                          │
│    ▼                                                         │   Linear(72,128) -> ReLU        │
│ Wide MLP: Linear(1,16) -> ReLU -> Linear(16,1)               │   -> LayerNorm -> Linear(128,64)│
│    │                                                         │      │                          │
│    ▼                                                         │      ▼                          │
│ Score_Wide                                                   │   L2 Norm -> Vector u(x) [64d]  │
│                                                              │                                 │
│                                                              │ ITEM TOWER:                     │
│                                                              │   Frozen SBERT Text (768d)      │
│                                                              │      │ Linear(768,128) -> ReLU │
│                                                              │      ▼                          │
│                                                              │   Text (64d) + Cat (16d)        │
│                                                              │            + Price (8d) = 88d   │
│                                                              │      │                          │
│                                                              │      ▼                          │
│                                                              │   Linear(88,64) -> ReLU         │
│                                                              │   -> Linear(64,64)               │
│                                                              │      │                          │
│                                                              │      ▼                          │
│                                                              │   L2 Norm -> Vector v(y) [64d]  │
│                                                              │                                 │
│                                                              │ Dot Product: u(x) · v(y)        │
│                                                              │ Temperature Scaling: / τ (0.1)  │
│                                                              │      │                          │
│                                                              │      ▼                          │
│                                                              │ Score_Deep                      │
├──────────────────────────────────────────────────────────────┴─────────────────────────────────┤
│ JOINT SCORING: Logits = Score_Deep + Score_Wide                                                 │
│ OUTPUT: Prob = Sigmoid(Logits)                                                                 │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Danh Mục 3 Hình Ảnh Biểu Đồ Cần Khởi Tạo (Phase 2.4 Specification)

| Tệp Hình Ảnh | Loại Hình Ảnh | Mô Tả Trực Quan Cần Thể Hiện | Mục Đích Trong Bài Báo IEEE |
|:---|:---|:---|:---|
| `architecture_overview.png` | System Architecture Diagram | • Luồng Wide Branch (Apriori → Log1p → Wide MLP)<br>• Luồng Deep Branch (User Tower + Item Tower với Frozen SBERT)<br>• Khối Dot Product + Temperature $\tau=0.1$<br>• Khối Joint Scoring (Sigmoid) | Minh họa chính cho Section 3 (Proposed Methodology) |
| `latency_comparison.png` | Speedup Bar Chart | • So sánh PyTorch Native (~12.5 ms) vs ONNX Runtime (~0.85 ms)<br>• Mũi tên highlight tốc độ tăng trưởng **~14.7x Speedup** | Minh họa cho Section 4.2 & 5.4 (Serving Efficiency) |
| `performance_ablation.png` | Grouped Bar Chart | • Trục X: 7 phương án (Apriori, Content, CF, Random, Noisy 10%, Deep-Only, Hybrid)<br>• Trục Y1 (Bar): Hit Rate@10<br>• Trục Y2 (Line): GAUC | Minh họa cho Section 5.3 (Full-Catalog Evaluation) |

---

## 4. Metadata Chuẩn Khởi Tạo `info.json`

Thư mục đích: `paper/raw_materials/figures/info.json`
```json
[
  {
    "name": "architecture_overview.png",
    "caption": "Overall architecture of the Proposed Hybrid Cascade Ranking System. The left branch illustrates the Wide component utilizing Apriori co-purchase rules with log1p transformation and Wide MLP, while the right branch details the Deep Two-Tower network incorporating frozen SBERT embeddings for generalized semantic matching."
  },
  {
    "name": "latency_comparison.png",
    "caption": "Inference latency comparison between the PyTorch native implementation and the optimized ONNX Runtime engine. Evaluation was performed by scoring a batch of 100 candidate items, demonstrating a 14.7x speedup."
  },
  {
    "name": "performance_ablation.png",
    "caption": "Performance comparison across baseline models and ablation variants using the full-catalog ranking evaluation protocol (1,380 SKUs)."
  }
]
```
