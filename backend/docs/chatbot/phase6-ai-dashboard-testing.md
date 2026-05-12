# Phase 6: AI Dashboard Verification & White-Box Testing

> **Mục tiêu**: Kiểm chứng toàn bộ hệ thống AI Recommendation hoạt động đúng end-to-end  
> **Phạm vi**: Backend algorithms + Dashboard widgets + Chatbot flows  
> **Ngày**: 2026-05-09

---

## Tổng Quan

Phase 6 không viết code mới. Mục tiêu là **kiểm chứng** rằng mọi thuật toán, pipeline, và tracking đã triển khai từ Phase 1→5 hoạt động chính xác thông qua 3 nhóm test:

| Nhóm | Mục đích | Số TC |
|---|---|---|
| **A. Algorithm White-Box** | Verify công thức toán học đúng | 12 |
| **B. Dashboard Integration** | Verify dữ liệu hiển thị chính xác | 8 |
| **C. Chatbot E2E** | Verify luồng hội thoại hoàn chỉnh | 10 |

---

## A. ALGORITHM WHITE-BOX TEST CASES

### A1. Content-Based (RRF Fusion)

**File**: `rag.service.js → _reciprocalRankFusion()`  
**Công thức**: `RRF(d) = Σ 1/(k + rank_i + 1)`, k=60

| TC | Input | Expected | Verify |
|---|---|---|---|
| A1.1 | Product X ở rank 0 trong Semantic, rank 0 trong Keyword | `score = 1/61 + 1/61 = 0.0328` | Kiểm tra `rrf_score` trong metadata |
| A1.2 | Product Y chỉ xuất hiện ở Semantic rank 2 | `score = 1/63 = 0.0159` | Score thấp hơn A1.1 |
| A1.3 | Semantic=[], Keyword=[] (empty) | Return mảng rỗng, không crash | `products: []` |

**Cách test**:
```
1. Mở Customer chatbot → Hỏi "có thịt bò không?"
2. Kiểm tra Network tab → chat:stream_complete event
3. Trong metadata.steps.fusion → top5Scores phải có productId + rrfScore
4. Xác nhận product xuất hiện ở CẢ 2 list có score cao hơn
```

---

### A2. Apriori (Support / Confidence / Lift)

**File**: `nightly-batch.js → _runApriori()`  
**Công thức**:
- `support = count(A∧B) / total_orders`
- `confidence(A→B) = count(A∧B) / count(A)`
- `lift = count(A∧B) × total / (count(A) × count(B))`

| TC | Input | Expected | Verify |
|---|---|---|---|
| A2.1 | Pair (1,3): co_purchase=15, countA=25, countB=20, total=100 | support=0.15, conf_ab=0.60, lift=3.00 | SQL query verify |
| A2.2 | countA=0 (division by zero guard) | confidence=0, lift=0 | Không crash |
| A2.3 | Lift < 1 | Pair KHÔNG xuất hiện trong Apriori cache | `_aprioriCache` skip |

**Cách test (SQL)**:
```sql
-- A2.1: Verify metrics cho cặp cụ thể
SELECT product_id_a, product_id_b, co_purchase_count,
       support, confidence_ab, confidence_ba, lift, total_orders
FROM co_purchase_stats
WHERE store_id = 1 AND lift > 1
ORDER BY lift DESC LIMIT 5;

-- Verify: confidence_ab = co_purchase_count / (SELECT order_count FROM product_order_frequency WHERE product_id = product_id_a)
-- Verify: lift > 1 cho tất cả rows (partial index filter)
```

---

### A3. Collaborative Filtering (Cosine Similarity)

**File**: `cf.service.js → computeItemSimilarities()`  
**Công thức**: `sim(i,j) = dot(R[*,i], R[*,j]) / (||R[*,i]|| × ||R[*,j]||)`

| TC | Input | Expected | Verify |
|---|---|---|---|
| A3.1 | Items cùng cluster (Bò↔Nấm) | sim ≥ 0.5 | SQL check `item_similarity` |
| A3.2 | Items khác cluster (Bò↔Bia) | sim < 0.3 hoặc không có row | Không tồn tại trong table |
| A3.3 | common_users < 2 | Pair bị loại (không INSERT) | Row count = 0 |

**Cách test (SQL)**:
```sql
-- A3.1: Verify cluster separation
SELECT item_a, item_b, similarity, common_users
FROM item_similarity
WHERE store_id = 1
ORDER BY similarity DESC LIMIT 10;

-- Top pairs phải là items cùng cluster (Nội trợ: 1,2,3,4,5 / Sinh viên: 7,8,11,12,19)
```

---

### A4. Hybrid Ensemble Scoring

**File**: `hybrid.service.js → score()`  
**Công thức**: `final = α×content + β×cf + γ×apriori + δ×personal`

| TC | Input | Expected | Verify |
|---|---|---|---|
| A4.1 | Product có content=1.0, cf=0, apriori=0, VIP | `0.40×1 + 0 + 0 + 0.10×1.0 = 0.50` (nếu β→α redistribute: `0.65×1 + 0.10 = 0.75`) | metadata.scores |
| A4.2 | Cold-start user (no CF data) | β redistributed to α: `α_eff = α + β` | `scores.cf = 0` |
| A4.3 | Product có apriori=0.6 boost | final_score tăng so với không có apriori | Compare 2 products |

**Cách test**:
```
1. Hỏi chatbot "gợi ý thịt bò" với user đã có interaction data
2. Kiểm tra metadata.steps.hybrid.weights → α, β, γ, δ
3. So sánh final_score giữa products → product có nhiều sources (content+cf+apriori) phải rank cao hơn
```

---

### A5. Weight Learner

**File**: `weight-learner.js → learn()`  
**Công thức**: `score(source) = purchased×1.0 + cart×0.5 + clicked×0.2 + hovered×0.1`

| TC | Input | Expected | Verify |
|---|---|---|---|
| A5.1 | feedbackCount < 20 | `skipped: true`, weights KHÔNG thay đổi | Force Learn → check response |
| A5.2 | Source "content" có CVR cao nhất | α tăng sau learn | Compare old vs new weights |
| A5.3 | Smoothing: 80% old + 20% new | Weights thay đổi từ từ, không nhảy đột ngột | Diff ≤ 0.05 per cycle |

**Cách test (Dashboard)**:
```
1. Dashboard → AI Insights → Force AI Learn
2. Nếu skipped: message "only X feedbacks (need 20)"
3. Nếu success: hiển thị α_new, β_new, γ_new
4. WeightEvolutionChart: thêm 1 điểm mới trên biểu đồ (triggerType=manual)
```

---

### A6. Session Context Boost

**File**: `session-context.service.js → inferSessionIntent()`

| TC | Input | Expected | Verify |
|---|---|---|---|
| A6.1 | Products [1,3] + message "lẩu" | cluster=lau_bo, confidence≥0.8, boost=+0.15 | Log output |
| A6.2 | Products [1,8] + message "ngon" | cluster=exploring, boost=0 | Không boost |
| A6.3 | Empty productSequence | Return null, no boost | Products giữ nguyên order |

---

## B. DASHBOARD INTEGRATION TEST CASES

### B1. API Connectivity

| TC | Endpoint | Expected | Verify |
|---|---|---|---|
| B1.1 | `GET /chatbot/stats/recommendations?storeId=1&days=30` | 200, funnel data với 5 actions | Response có `totalHovered` |
| B1.2 | `GET /chatbot/stats/latency?storeId=1` | 200, P95 latency data | `sampleSize > 0` |
| B1.3 | `GET /chatbot/stats/feedback-stream?storeId=1&limit=50` | 200, feedbacks array | Mỗi item có productName |
| B1.4 | `GET /chatbot/stats/weight-history?storeId=1&limit=30` | 200, history array (chronological) | `α+β+γ+δ ≈ 1.0` cho mỗi row |

**Cách test**:
```
1. Mở Browser DevTools → Network tab
2. Navigate tới Dashboard → AI Insights tab
3. Kiểm tra 4 API calls song song (Promise.all)
4. Mỗi response phải có success: true
```

---

### B2. Widget Data Accuracy

| TC | Widget | Verify |
|---|---|---|
| B2.1 | ConversionFunnel | 5 bước: Recommended → **Hovered** → Clicked → Cart → Purchased. Giá trị giảm dần. |
| B2.2 | WeightEvolutionChart | α+β+γ+δ = 1.0 tại mỗi điểm. Manual trigger có dot lớn hơn. |
| B2.3 | SourcePerformance | Mỗi source (content/cf/apriori) có CTR ≤ 1.0, CVR ≤ CTR. |
| B2.4 | LiveFeedbackStream | Actions hiển thị đúng badge color. Sorted by created_at DESC. |

**Cách test**:
```
1. Dashboard → AI Insights
2. ConversionFunnel: Đếm số bước = 5 (không phải 4)
3. Hover Rate hiển thị giữa Recommended và Clicked
4. Force Learn → WeightEvolutionChart thêm 1 điểm mới
```

---

### B3. Hướng Dẫn Test Trực Tiếp Phễu 5 Bước (End-to-End)

Để quan sát hệ thống Tracking thời gian thực (Real-time) trên AI Dashboard, bạn cần thực hiện chuỗi hành động của End-User từ Customer Web:

**Bước 1: Tạo Recommendation (Khởi tạo phễu)**
1. Mở Customer Web, đăng nhập tài khoản.
2. Mở Chatbot và nhắn: "Gợi ý cho tôi vài loại nước giải khát".
3. Chờ Chatbot trả về danh sách các Product Cards (Card sản phẩm).
*Verify Dashboard:* Trong `Live Feedback Stream` sẽ xuất hiện dòng log `[Send/⚪] Recommended Product X`. Thanh `Recommended` trên `Conversion Funnel` tăng lên.

**Bước 2: Kích hoạt Hover Tracking**
1. Tại Customer Web, di chuột (Mouse Hover) lên một Product Card bất kỳ và giữ yên trong ít nhất 1.5 giây (để kích hoạt timer).
*Verify Dashboard:* `Live Feedback Stream` cập nhật tức thì dòng log `[Eye/👁️] Hovered Product X`. Thanh `Hovered` tăng, `Hover Rate` được cập nhật.

**Bước 3: Kích hoạt Click Tracking**
1. Click vào Product Card bạn vừa hover để xem chi tiết.
*Verify Dashboard:* Xuất hiện log `[MousePointerClick/🔵] Clicked Product X`. Thanh `Clicked` tăng, `CTR` (Click-Through Rate) thay đổi.

**Bước 4: Kích hoạt Add To Cart Tracking**
1. Trong màn hình chi tiết, bấm nút "Thêm vào giỏ hàng".
*Verify Dashboard:* Xuất hiện log `[ShoppingCart/🟡] Added to Cart Product X`. Thanh `Added to Cart` tăng, `A2C Rate` được tính lại.

**Bước 5: Kích hoạt Purchase Tracking (Hoàn tất phễu)**
1. Vào giỏ hàng và tiến hành thanh toán thành công đơn hàng.
*Verify Dashboard:* Xuất hiện log `[CreditCard/🟢] Purchased Product X`. Thanh `Purchased` (Đáy phễu) tăng. Tỉ lệ `CVR` (Conversion Rate) thay đổi. AI Model sẽ dùng dữ liệu này để tính lại Weight Learner trong đợt Batch Job tiếp theo!

---

## C. CHATBOT E2E TEST CASES

### C1. Intent Classification

| TC | Message | Expected Intent | Verify |
|---|---|---|---|
| C1.1 | "còn sữa không?" | CHECK_STOCK | Response chứa "trên kệ" hoặc "hết hàng" |
| C1.2 | "giá bán mì Hảo Hảo" | CHECK_PRICE | Response chứa giá VND |
| C1.3 | "đơn hàng gần đây" | ORDER_STATUS | Response chứa orderNumber |
| C1.4 | "gợi ý sản phẩm nấu lẩu" | RECOMMENDATION | Response có ProductCards |
| C1.5 | "hello" | FREE_CHAT | Response streaming tự nhiên |

---

### C2. RAG Pipeline E2E

| TC | Scenario | Verify |
|---|---|---|
| C2.1 | Hỏi "thịt bò" → Semantic+Keyword match | ProductCards hiển thị, có giá + tồn kho |
| C2.2 | Hỏi "cái đó giá bao nhiêu?" (coreference) | Query Reformulation viết lại thành câu đầy đủ |
| C2.3 | Hỏi sản phẩm không tồn tại "xyz123" | Response: "không tìm thấy", products=[] |

---

### C3. Tracking Funnel E2E

| TC | Action | Verify |
|---|---|---|
| C3.1 | Hover ChatProductCard ≥2s | Network: POST /feedback action=hovered, dwellTimeMs≈2000 |
| C3.2 | Hover cùng product 3 lần | Chỉ 1 POST (dedup bằng isHoverTrackedRef) |
| C3.3 | Click ChatProductCard | POST action=clicked + Navigate /product/:id?ref=chat&src=... |
| C3.4 | Add to Cart trên PDP (từ chat) | POST action=added_to_cart + URL params bị xóa (replaceState) |
| C3.5 | Add to Cart trên PDP (trực tiếp) | KHÔNG có POST (vì không có ?ref=chat) |

---

## Verification Checklist — Thứ Tự Thực Hiện

### Phase X.1: Backend Algorithms (SQL Verification)

```sql
-- 1. Apriori: Verify metrics exist
SELECT COUNT(*) AS total_pairs,
       COUNT(*) FILTER (WHERE lift > 1) AS positive_correlation,
       MAX(lift) AS max_lift,
       MAX(confidence_ab) AS max_confidence
FROM co_purchase_stats WHERE store_id = 1;
-- Expected: total_pairs > 0, positive_correlation > 0, max_lift > 1

-- 2. CF: Verify similarity matrix
SELECT COUNT(*) AS total_pairs,
       AVG(similarity) AS avg_sim,
       COUNT(*) FILTER (WHERE common_users >= 2) AS valid_pairs
FROM item_similarity WHERE store_id = 1;
-- Expected: total_pairs > 0, avg_sim between 0.1-0.9

-- 3. Feedback funnel counts
SELECT action, COUNT(*) AS count
FROM recommendation_feedback
WHERE store_id = 1
GROUP BY action
ORDER BY CASE action
  WHEN 'recommended' THEN 1 WHEN 'hovered' THEN 2
  WHEN 'clicked' THEN 3 WHEN 'added_to_cart' THEN 4
  WHEN 'purchased' THEN 5 END;
-- Expected: counts decrease down the funnel

-- 4. Weight history
SELECT alpha, beta, gamma, delta,
       alpha+beta+gamma+delta AS weight_sum,
       trigger_type, created_at
FROM ensemble_weights_history
WHERE store_id = 1
ORDER BY created_at DESC LIMIT 5;
-- Expected: weight_sum ≈ 1.0 for all rows

-- 5. Hover metadata verification
SELECT COUNT(*) AS hover_count,
       AVG((metadata->>'dwellTimeMs')::int) AS avg_dwell_ms
FROM recommendation_feedback
WHERE action = 'hovered' AND store_id = 1;
-- Expected: avg_dwell_ms >= 1500 (threshold)
```

### Phase X.2: Dashboard Visual Verification

```
[ ] Mở Dashboard → AI Insights tab → 4 widgets load thành công
[ ] ConversionFunnel hiển thị 5 bước (có Hovered)
[ ] Force Learn → WeightEvolutionChart cập nhật
[ ] SourcePerformance → bars hiện CTR/CVR per algorithm
[ ] LiveFeedbackStream → rows hiển thị action badges
[ ] Period selector (7d/30d/90d) → data thay đổi tương ứng
```

### Phase X.3: Chatbot Flow Verification

```
[ ] Customer web → ChatWidget mở thành công
[ ] Gửi "gợi ý sản phẩm" → nhận ProductCards
[ ] Hover ProductCard 2s → Network tab thấy POST hovered
[ ] Click ProductCard → navigate /product/:id?ref=chat&src=...
[ ] Add to Cart trên PDP → POST added_to_cart + URL cleaned
[ ] Quay lại Chat → gửi "cái đó giá bao nhiêu?" → Query Reformulation hoạt động
[ ] Gửi "trạng thái đơn hàng" → hiển thị order info
```

### Phase X.4: Batch Job Verification

```
[ ] Force Learn trên Dashboard → response success/skipped
[ ] ensemble_weights_history có row mới
[ ] Nightly batch status hiển thị trên SystemHealth widget
[ ] Weight Learner skip nếu feedbackCount < 20
```

---

## Design Decisions

| Quyết định | Lý do |
|---|---|
| **SQL verification trước UI** | Database là source of truth — nếu data sai, UI sẽ sai theo |
| **Manual test thay vì automated** | Hệ thống phụ thuộc LLM (non-deterministic) → automated assertions khó viết |
| **Funnel counts giảm dần** | Nếu clicked > recommended → bug tracking hoặc data leak |
| **weight_sum ≈ 1.0** | Nếu ≠ 1.0 → normalization bug trong weight-learner |
| **avg_dwell ≥ 1500** | Nếu < 1500 → threshold guard bị bypass |
