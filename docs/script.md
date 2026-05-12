# Cải tiến RAG Pipeline: Hiển thị đầy đủ kết quả Hybrid Ensemble

## Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|----------|:---:|---------|
| Batch endpoint (`catalog`) | ✅ Done | `POST /api/products/batch` |
| ApiClient + Timeout | ✅ Done | `AbortController` 500ms |
| Two-Tier Hydration | ✅ Done | Local KB → Catalog API |
| Dynamic Stock | ✅ Done | `qtyOnShelf > 0` |
| Type Consistency | ✅ Done | `Number(p.price)` |
| **Session topSource fix** | ✅ **Done** | Ghi đè `topSource = 'session'` cho sản phẩm boosted |

---

## Fix mới: Session "Blind Spot" Attribution

### Vấn đề
`applySessionBoost()` cộng thêm điểm `+0.10~0.15` nhưng **KHÔNG** cập nhật `topSource`. Feedback loop ghi nhầm credit cho `content`/`cf` thay vì `session`.

### Giải pháp (đã triển khai)
[rag.service.js](file:///e:/UIT/backend/microservices/services/chatbot/src/services/rag.service.js) — Ngay sau `applySessionBoost()`:

```javascript
if (sessionIntent.cluster !== 'exploring') {
    for (const r of hybridResults) {
        if (r.session_boosted) {
            r.topSource = 'session';
            if (!r.sources.includes('session')) r.sources.push('session');
        }
    }
}
```

> [!IMPORTANT]
> Fix này đảm bảo cả 4 thuật toán đều **visible** trong `recommendation_feedback.source`, phục vụ đúng mục tiêu bảo vệ đồ án.

---

## Kịch bản Demo — Dựa trên Seed Data thực tế

### Dữ liệu nền tảng (đã seed)

**mock-interactions.js** — 4 persona clusters:

| Cluster | User ID Range | Sản phẩm chính | CF Similarity cao |
|---------|:---:|------|------|
| Nội trợ Nấu lẩu | 1–150 | Bò(1), Nấm(2), Rau(3), Gia vị lẩu(4), Bún(5) | Bò↔Nấm > 0.5 |
| Sinh viên Ăn vặt | 151–300 | Mì(12), Xúc xích(11), Coca(19), Snack(20) | Mì↔Coca > 0.5 |
| Dân nhậu | 301–450 | Bia HK(17), Tiger(18), Khô gà(21), Đậu phộng(22) | Bia↔Khô gà > 0.5 |
| Random | 451–500 | Ngẫu nhiên | Noise |

**mock-orders.js** — 500 đơn hàng → Apriori co-purchase:

| Cluster (35%) | Sản phẩm hay mua kèm | Lift kỳ vọng |
|---------|------|:---:|
| LAU_BO | Bò(1) ↔ Nấm(2) ↔ Rau(3) ↔ Gia vị(4) ↔ Bún(5) | > 1.0 |
| BUA_SANG (35%) | Bánh mì(7) ↔ Sữa(8) ↔ Trứng(10) ↔ Xúc xích(11) | > 1.0 |
| GIAI_KHAT (15%) | Bia(17) ↔ Coca(19) ↔ Snack(20) ↔ Khô gà(21) | > 1.0 |

**session-context.service.js** — Session clusters:

| Cluster Key | Keywords trigger | Products boosted | Boost |
|-------------|-----------------|------------------|:---:|
| `lau_bo` | lẩu, bò, nấm, rau, nấu, gia vị, bún | 1,2,3,4,5,24,25,26,27,28 | +0.15 |
| `bua_sang` | sáng, bánh mì, sữa, trứng | 7,8,9,10,11 | +0.12 |
| `nhau` | bia, nhậu, khô, đậu phộng, mồi | 17,18,19,20,21,22 | +0.15 |
| `an_vat` | mì, snack, nước ngọt, ăn vặt | 12,11,19,20,7,8 | +0.12 |

---

### 🎬 ACT 1: Content-Based (α = 0.40) — RAG Semantic Search

**Mục đích:** Chứng minh AI hiểu ngữ nghĩa tự nhiên.

**Tài khoản:** Bất kỳ (có thể không đăng nhập).

**Câu hỏi:**
```
"Tôi muốn mua đồ ăn vặt"
```

**Luồng kỹ thuật:**
1. `embedding.client.js` → encode "đồ ăn vặt" thành vector 768d
2. `knowledge.repository.js` → pgvector cosine search → match Snack(20), Mì(12), Coca(19)
3. Keyword search → tsvector match "ăn vặt" 
4. RRF Fusion → Top 5 content results
5. Hybrid scoring: `α × 1.0 + β × 0 + γ × 0 + δ × 0.3 = 0.43` (content dominant)

**Kết quả kỳ vọng:**
| # | Sản phẩm | topSource | Lý do |
|---|----------|:---------:|-------|
| 1 | Snack Lays (20) | `content` | Semantic match "ăn vặt" |
| 2 | Mì Hảo Hảo (12) | `content` | Keyword match |
| 3 | Coca-Cola (19) | `content` | Associated context |

**Demo action:** Click vào Snack Lays → Mở Dashboard → Kiểm tra badge `[content]` trên Live Feed.

---

### 🎬 ACT 2: Apriori Cross-sell (γ = 0.25) — Association Rules

**Mục đích:** Chứng minh AI biết bán chéo sản phẩm thường mua kèm.

**Tài khoản:** Customer đăng nhập (bất kỳ Customer ID 1-50).

**Câu hỏi:**
```
"Cho tôi 1 thùng bia Heineken"
```

**Luồng kỹ thuật:**
1. Content search → match Bia Heineken(17), Tiger(18)
2. Apriori lookup (co_purchase_stats): Bia(17) có co-purchase cao với Khô gà(21), Snack(20), Coca(19)
3. Hybrid scoring: Khô gà(21) nhận `γ × confidence ≈ 0.25 × 0.6 = 0.15` từ Apriori
4. Khô gà lọt Top 5 dù user KHÔNG search keyword "khô gà"

**Kết quả kỳ vọng:**
| # | Sản phẩm | topSource | Lý do |
|---|----------|:---------:|-------|
| 1 | Bia Heineken (17) | `content` | Direct match |
| 2 | Bia Tiger (18) | `content` | Semantic similar |
| 3 | **Khô gà lá chanh (21)** | **`apriori`** | **Co-purchase rule: Bia ↔ Khô gà** |
| 4 | Snack Lays (20) | `apriori` | Co-purchase: Bia ↔ Snack |

**Demo action:** Chỉ cho GVHD sản phẩm Khô gà xuất hiện dù user hỏi về bia → Giải thích "Đây là thuật toán Apriori phát hiện Bia ↔ Khô gà có Lift > 1 từ 500 đơn hàng lịch sử."

---

### 🎬 ACT 3: Collaborative Filtering (β = 0.25) — Cá nhân hóa

**Mục đích:** Chứng minh AI nhớ thói quen mua hàng và cá nhân hóa gợi ý.

**Tài khoản:** 🔴 Quan trọng — đăng nhập bằng **Customer ID thuộc nhóm "Nội trợ Nấu lẩu" (ID 1-150)**. Ví dụ Customer ID = 5.

> [!NOTE]
> Customer ID 1-150 có lịch sử tương tác mạnh với nhóm sản phẩm Bò(1), Nấm(2), Rau(3), Gia vị(4) từ `mock-interactions.js`. CF engine sẽ gợi ý các sản phẩm tương tự mà customer **chưa** mua.

**Câu hỏi:**
```
"Gợi ý cho tôi vài món"
```

**Luồng kỹ thuật:**
1. Content search → match chung chung (Top 5 RRF)
2. CF engine: `cf.service.getRecommendations(userId=5, storeId=1)`
   - Query `user_product_interaction` → User 5 hay mua Bò(1), Nấm(2), Rau(3)
   - Query `item_similarity` → Bò↔Cà chua(24), Nấm↔Hành tây(25) có similarity > 0.5
   - Prediction score: Cà chua(24) = Σ sim × score / Σ |sim| → cao
3. Hybrid scoring: Cà chua(24) nhận `β × normalizedCF ≈ 0.25 × 0.8 = 0.20`
4. **Hydration:** Cà chua(24) là CF-only → Local KB fetch metadata → hiển thị OK

**Kết quả kỳ vọng:**
| # | Sản phẩm | topSource | Lý do |
|---|----------|:---------:|-------|
| 1-3 | (Content results) | `content` | RAG search |
| 4 | **Hành tây (25) hoặc Cà chua (24)** | **`cf`** | **CF: "User nấu lẩu thường mua thêm hành tây"** |

**Demo action:** Chỉ cho GVHD badge `[cf]` → Giải thích "Sản phẩm này xuất hiện vì thuật toán CF phát hiện 150 user có hành vi mua hàng tương tự đều mua kèm hành tây."

**Verify `cfHydration` metadata:**
```json
{
  "cfHydration": {
    "cfOnlyCount": 2,
    "localHits": 2,
    "apiFetched": 0,
    "latencyMs": 1
  }
}
```

---

### 🎬 ACT 4: Session Context Memory — Multi-turn Conversation

**Mục đích:** Trình diễn tính năng "Trí nhớ ngắn hạn" — AI thay đổi gợi ý dựa trên ngữ cảnh phiên chat.

**Tài khoản:** Customer bất kỳ (đăng nhập).

**Kịch bản 3 lượt (cùng 1 session chat):**

**Lượt 1:**
```
"Tôi muốn nấu lẩu Thái cuối tuần"
```
→ AI trả về: Gia vị lẩu Thái(4), Bò(1), Nấm(2)...
→ `sessionIntent = null` (chỉ 1 turn, chưa đủ data)

**Lượt 2:**
```
"Có rau gì ăn kèm không?"
```
→ AI trả về: Rau muống(3), Cải thìa(22)
→ Session extractProductSequence: [4, 1, 2, 3, 22]
→ `inferSessionIntent` → Cluster `lau_bo` (productHits: 4×2 = 8 points, keywordHits: "lẩu" "rau" "nấu" = 3)
→ Confidence > 0.4 → Cluster locked!

**Lượt 3 (Cú chốt):**
```
"Gợi ý thêm đồ nấu ăn nữa đi"
```
→ **KHÔNG CÓ KEYWORD CỤ THỂ** — nhưng Session Context nhận diện cluster `lau_bo`
→ Boost +0.15 cho products: Bún(5), Hành tây(25), Tỏi(26), Ớt(27), Chanh(28)
→ Những sản phẩm này **nhảy lên Top** dù Content score có thể thấp

**Kết quả kỳ vọng (Lượt 3):**
| # | Sản phẩm | topSource | session_boosted |
|---|----------|:---------:|:---:|
| 1 | Bún tươi (5) | **`session`** | ✅ |
| 2 | Hành tây (25) | **`session`** | ✅ |
| 3 | Chanh (28) | **`session`** | ✅ |
| 4 | (Other content) | `content` | ❌ |

**Demo action:** 
- Chỉ cho GVHD badge `[session]` trên Dashboard → "Thưa thầy cô, sản phẩm này xuất hiện vì AI nhớ ngữ cảnh 'nấu lẩu' từ 2 câu trước."
- Kiểm tra `metadata.steps.hybrid.sessionCluster = 'lau_bo'`

---

## Verification Plan

### Kiểm tra tự động (sau `docker compose up --build`)

1. **Feedback source distribution:**
```sql
SELECT source, COUNT(*) 
FROM recommendation_feedback 
WHERE store_id = 1 
GROUP BY source 
ORDER BY count DESC;
```
→ Phải thấy **4 giá trị**: `content`, `cf`, `apriori`, `session`

2. **CF Hydration hoạt động:**
```sql
SELECT * FROM recommendation_feedback 
WHERE source = 'cf' AND action = 'recommended' 
ORDER BY created_at DESC LIMIT 5;
```

3. **Session attribution hoạt động:**
```sql
SELECT * FROM recommendation_feedback 
WHERE source = 'session' 
ORDER BY created_at DESC LIMIT 5;
```
→ Trước fix: **0 rows**. Sau fix: **có data** sau khi chạy ACT 4.

### Kiểm tra thủ công
- Dashboard Live Feed hiển thị đủ 4 loại badge: `[content]` `[cf]` `[apriori]` `[session]`
- Tổng latency pipeline không tăng quá 50ms so với trước (nhờ local-first hydration)
