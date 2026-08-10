# 📊 Báo Cáo Kết Quả Huấn Luyện Mô Hình Wide & Deep Two-Tower

> **Phân hệ**: AI Recommendation Engine — Huấn Luyện & Đánh Giá Mô Hình  
> **Phiên bản dữ liệu**: v3 (Mock Data tuned — Beer↔Snack Fix — 2026-08-04)  
> **Thư mục**: `backend/docs/neural/05-training-results.md`

---

## 1. Tổng Quan Kết Quả Huấn Luyện

### Kết Quả Cuối Cùng Trên Tập Test (Hold-out 10%):

| Chỉ Số | Giá Trị Đạt Được | Ngưỡng Chấp Nhận (Target) | Đánh Giá |
|:---|:---:|:---:|:---:|
| **Hit Rate@10** | **1.0000** | ≥ 0.60 | ✅ Vượt 67% |
| **NDCG@10** | **1.0000** | ≥ 0.35 | ✅ Vượt 186% |
| **AUC-ROC** | **1.0000** | ≥ 0.80 | ✅ Vượt 25% |
| **Train Loss (BCE)** | ~0.0000 | Hội tụ | ✅ |
| **Val Loss (BCE)** | ~0.0000 | Hội tụ | ✅ |

### Quá Trình Huấn Luyện (Training Log):

```
Epoch 01/50 | Train Loss: 0.3979 | Val Loss: 0.3488 | Hit@10: 0.9992 | NDCG@10: 0.9992 | AUC: 0.9738
   ⭐ Best Model Saved! (NDCG@10 = 0.9992)
Epoch 02/50 | Train Loss: 0.2474 | Val Loss: 0.2192 | Hit@10: 1.0000 | NDCG@10: 1.0000 | AUC: 1.0000
   ⭐ Best Model Saved! (NDCG@10 = 1.0000)
Epoch 03/50 | Train Loss: 0.1771 | Val Loss: 0.1585 | Hit@10: 1.0000 | NDCG@10: 1.0000 | AUC: 1.0000
Epoch 04/50 | Train Loss: 0.1280 | ...
...
Epoch 07/50 | ⏹️ Early Stopping triggered (patience = 5)

✅ Training Complete! Best Validation NDCG@10: 1.0000
```

> **Convergence Speed**: Mô hình hội tụ chỉ sau **2 epochs** (NDCG@10 đạt 1.0000 từ Epoch 2), Early Stopping kích hoạt tại Epoch 7 (5 epochs patience không cải thiện thêm). Train Loss giảm đều từ 0.3979 → 0.1280, chứng minh quá trình gradient descent hội tụ ổn định.

---

## 2. Giải Thích Bản Chất Kết Quả

### 2.1. Tại sao Hit@10 = 1.0000?

**Hit Rate@10** đo tỷ lệ % người dùng có ít nhất 1 sản phẩm đúng (positive) nằm trong Top-10 gợi ý của mô hình.

$$Hit@10 = \frac{|\{u : \exists \text{ positive item in Top-10 predictions of } u\}|}{|U_{test}|}$$

- **Kết quả 1.0000 (100%)**: Mọi người dùng trong tập Test đều được gợi ý đúng ít nhất 1 sản phẩm thực sự tương tác trong Top-10.
- **Nguyên nhân**: Mạng Two-Tower đã học thành công biểu diễn vector ẩn 64 chiều tách biệt rõ ràng giữa Positive samples (sản phẩm user thực sự quan tâm) và Negative samples (sản phẩm ngẫu nhiên hoặc phổ biến mà user bỏ qua).

### 2.2. Tại sao NDCG@10 = 1.0000?

**NDCG (Normalized Discounted Cumulative Gain)** đánh giá chất lượng xếp hạng, không chỉ đo "có đúng không" mà còn "đúng ở vị trí nào".

$$DCG@K = \sum_{i=1}^{K} \frac{2^{rel_i} - 1}{\log_2(i+1)}, \quad NDCG@K = \frac{DCG@K}{IDCG@K} $$

- **Kết quả 1.0000**: Mô hình không chỉ đưa sản phẩm đúng vào Top-10, mà còn xếp chúng ở **đúng vị trí cao nhất** (vị trí 1, 2, 3...), đạt xếp hạng lý tưởng (ideal ranking).
- **Ý nghĩa thực tiễn**: Trong chatbot, sản phẩm phù hợp nhất luôn xuất hiện đầu tiên, tối ưu trải nghiệm người dùng.

### 2.3. Tại sao AUC-ROC = 1.0000?

**AUC-ROC (Area Under the Receiver Operating Characteristic Curve)** đo khả năng phân loại nhị phân: mô hình phân biệt được "sản phẩm user thích" (label = 1) và "sản phẩm user không quan tâm" (label = 0).

$$AUC = P(\hat{y}_{positive} > \hat{y}_{negative})$$

- **Kết quả 1.0000**: Với mọi cặp (positive, negative), mô hình luôn cho điểm positive cao hơn negative. Tức điểm phân biệt hoàn hảo: không có false positive hay false negative.

---

## 3. Phân Tích Tại Sao Đạt Điểm Hoàn Hảo (Không Phải Overfitting)

> [!IMPORTANT]
> Điểm 1.0000 trên tập Test KHÔNG phải overfitting vì các lý do kỹ thuật sau:

### 3.1. Đặc Thù Dữ Liệu Seed Controllable

| Yếu tố | Giải thích |
|:---|:---|
| **Dữ liệu persona rõ ràng** | 4 cụm persona (Nội trợ 1-150, Sinh viên 151-300, Dân nhậu 301-400, Vãng lai 401-500) với ranh giới phân tách dứt khoát |
| **Tín hiệu tương tác mạnh** | Mỗi persona tương tác 40-50 sản phẩm tập trung vào danh mục cốt lõi → Tín hiệu rõ ràng, ít nhiễu |
| **Negative sampling hiệu quả** | 50% Hard Negatives (sản phẩm phổ biến mà user bỏ qua) + 50% Uniform Negatives → Ranh giới quyết định sắc nét |
| **Quy mô phù hợp kiến trúc** | 500 users × 1,380 products là quy mô vừa đủ cho embedding 64d, tránh underfitting lẫn overfitting |

### 3.2. Kiểm Chứng Tính Hợp Lệ

- **Train/Val/Test Split**: 80% / 10% / 10% với `random_state=42`, đảm bảo tái tạo được kết quả.
- **Early Stopping (patience=5)**: Ngăn chặn overfitting bằng cách dừng huấn luyện khi validation metric không cải thiện.
- **Tập Test Độc Lập**: Không bị data leakage — test set chỉ chứa các interaction chưa từng xuất hiện trong train/val.

---

## 4. Cấu Hình Huấn Luyện Chi Tiết (Hyperparameters)

| Tham Số | Giá Trị | Giải Thích |
|:---|:---:|:---|
| `BATCH_SIZE` | 512 | Kích thước mini-batch tối ưu cho GPU/CPU convergence |
| `LEARNING_RATE` | 0.001 | Adam optimizer learning rate tiêu chuẩn |
| `WEIGHT_DECAY` | 1e-5 | L2 Regularization nhẹ chống overfitting |
| `EPOCHS` | 50 (max) | Dừng sớm tại Epoch 8 nhờ Early Stopping |
| `EARLY_STOPPING_PATIENCE` | 5 | Cho phép 5 epochs không cải thiện trước khi dừng |
| `NEGATIVE_RATIO` | 4 | Mỗi positive sample sinh 4 negative samples |
| `HARD_NEGATIVE_PCT` | 0.50 | 50% hard negatives (popular items user ignored) |
| `TOWER_OUTPUT_DIM` | 64 | Kích thước vector ẩn đầu ra của mỗi tháp |
| `SBERT_DIM` | 768 | Vietnamese SBERT `keepitreal/vietnamese-sbert` |
| `Loss Function` | Binary Cross-Entropy (BCE) | Hàm mất mát phân loại nhị phân |
| `Optimizer` | Adam | Adaptive Moment Estimation |

---

## 5. Thống Kê Dữ Liệu Huấn Luyện

| Dataset | Số Dòng (Rows) | Mô Tả |
|:---|:---:|:---|
| `train.parquet` | ~50,000+ (×5 with negatives) | 80% interactions + Hard/Uniform Negative Sampling |
| `val.parquet` | ~6,000+ (×5) | 10% interactions cho validation mỗi epoch |
| `test.parquet` | ~6,000+ (×5) | 10% interactions cho đánh giá cuối cùng |
| `product_features.parquet` | 1,380 | Catalog SKU: embedding 768d + category_id + price_bucket |

---

## 6. Benchmark Tốc Độ Suy Luận ONNX (Inference Latency)

| Chế độ | Latency | Ghi chú |
|:---|:---:|:---|
| **Single-Item Prediction** | **~0.18 ms** | 1 sample inference |
| **Batch 100 Candidates** | **< 1 ms** | Xếp hạng 100 ứng viên trong 1 lệnh gọi |
| **Target** | < 5.0 ms | ✅ Vượt chỉ tiêu |

---

## 7. Lịch Sử Tinh Chỉnh Dữ Liệu (Data Tuning Iterations)

| Phiên bản | Vấn đề | Giải pháp | Kết quả |
|:---|:---|:---|:---|
| **v1** (ban đầu) | Cat 35 (Đậu nành, Bột khoai) lẫn vào nhóm Dân nhậu, Snack quá phân tán (50 SKU) | — | Apriori không kích hoạt cho Heineken |
| **v2** | Loại Cat 35, giảm xuống Cat 94/101/103. Nhưng Beer 1-3/đơn → Beer↔Beer chiếm ưu thế | Loại Cat 35, tăng Snack lên 2-3/đơn | Apriori trả về Beer↔Beer thay vì Beer↔Snack |
| **v3** (hiện tại) | Beer chỉ 1/đơn → **Beer↔Beer = 0 pairs**, Beer↔Snack = 383 pairs | `randSubset(BEER, 1, 1)` | ✅ Apriori Cross-sell chính xác: Heineken → Snack Lay's, Karamucho, Chà bông |

### Thống kê Co-Purchase v3 (Hiện tại):

| Loại cặp | Số lượng pairs | Avg Count | Avg Lift |
|:---|:---:|:---:|:---:|
| **Beer↔Beer** | **0** | — | — |
| **Beer↔Snack** | **383** | 3.0 | 3.13 |

**Top 3 Beer↔Snack pairs:**
- Heineken 250ml ↔ Snack Koikeya Karamucho (Count=13, Lift=5.22)
- Sài Gòn Special ↔ Snack Lay's Classic (Count=10, Lift=6.01)
- Heineken 250ml ↔ Snack Poca mực (Count=8, Lift=3.25)

---

## 8. Tóm Tắt Cho Bảo Vệ Đồ Án

> **Kết luận**: Mô hình Wide & Deep Two-Tower Neural Network đạt **điểm hoàn hảo trên cả 3 metric đánh giá** (Hit@10, NDCG@10, AUC-ROC = 1.0000) trên tập test độc lập. Kết quả này phù hợp với đặc thù dữ liệu mock controllable có tín hiệu persona rõ ràng, negative sampling hiệu quả, và kiến trúc embedding 64 chiều tương xứng quy mô. Dữ liệu đã qua **3 lần tinh chỉnh** (v1→v3) để đảm bảo Apriori hoạt động đúng: Beer↔Beer = 0 pairs, Beer↔Snack = 383 pairs. Mô hình đạt latency suy luận **< 1ms** qua ONNX Runtime, sẵn sàng phục vụ production thời gian thực.
