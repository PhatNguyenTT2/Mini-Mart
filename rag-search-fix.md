# RAG Search Quality — Fix Plan (v2)

## Goal
Fix 2 production bugs trong RAG pipeline:
1. "Tôi muốn mua đồ ăn vặt" → không trả product cards (fallback keyword miss)
2. Kết quả "đồ ăn vặt" trộn lẫn Gạo, Rau muống, Chả lụa (semantic search quality)

## Root Cause (Sửa lại sau dashboard evidence)

### Bug 1: Tin nhắn đầu tiên mất products
- `handleRecommendation()` → ragService null → fallback `handleSearchProductFallback()`
- Fallback extract keyword bằng `['tìm', 'search', 'có gì']` → KHÔNG cover "muốn mua"
- → keyword = CẢ CÂU → `searchProducts()` SQL ILIKE fail

### Bug 2: Semantic Search trộn sản phẩm lạc danh mục
**⚠️ Dashboard xác nhận: tất cả 5 sản phẩm đều source `content` — KHÔNG phải CF inject.**

```
Snack Lays      → AI Score: 0.2994  ← Top 1 (đúng danh mục)
Gạo thơm        → AI Score: 0.2951  ← SAI (Gạo ≠ Đồ ăn vặt)
Chả lụa heo     → AI Score: 0.2908  ← SAI
Rau muống        → AI Score: 0.2868  ← SAI
Xúc xích xông   → AI Score: 0.2828  ← SAI
```

**Nguyên nhân gốc:** Vietnamese SBERT embedding model coi "đồ ăn vặt" gần nghĩa với TẤT CẢ thực phẩm (cosine similarity ~0.28-0.30, chênh lệch chỉ 0.02). Content text hiện tại:
```
"Sản phẩm "Rau muống VietGAP", danh mục "Rau lá", giá 15.000 VND..."
```
→ Embedding không nhận diện "Rau lá" ≠ "Bánh, kẹo, snack" đủ mạnh.

## Tasks

### Bug 1: Fallback Keyword Extraction
- [ ] **T1:** Bổ sung trigger words cho RECOMMENDATION vào `handleSearchProductFallback()`
  - File: `handlers/read.handler.js:273`
  - Thêm: `['gợi ý', 'muốn mua', 'cần mua', 'mua đồ', 'đề xuất']`
  - Verify: Khi RAG chưa ready, "Tôi muốn mua đồ ăn vặt" → keyword = "đồ ăn vặt" → SQL search tìm được Snack

- [ ] **T2:** Retry nhẹ khi ragService null — check `embeddingClient.isReady` + delay 2s + retry 1 lần
  - File: `handlers/read.handler.js:20-23`
  - Logic: `if (!ragService && embeddingClient.isReady) → wait(2s) → re-check` 
  - Verify: Tin nhắn đầu tiên sau restart → vẫn trả products (hoặc fallback graceful)

### Bug 2: Semantic Search Quality (2 layer fix)

- [ ] **T3: Anchor Category Re-ranking** (review suggestion: "Mỏ neo")
  - File: `services/rag.service.js` → sau RRF Fusion (line 70-71)
  - Logic:
    1. Lấy Root Category của Top 1 RRF result → **Anchor = "Bánh, kẹo, snack"**
    2. Boost +0.05 cho các products cùng Root Category
    3. Penalize -0.03 cho products KHÁC Root Category
    4. Re-sort top5 theo adjusted RRF score
  - Verify: "đồ ăn vặt" → Top 1 = Snack Lays (Bánh kẹo) → Anchor boost → Bánh quy, Kẹo, Hạt điều lên top, Gạo/Rau muống bị đẩy xuống

- [ ] **T4: Enriching Embedding Content** — thêm rootCategoryName vào embedding text
  - File: `services/data-ingestion.service.js:222-237` (`_buildContentText`)
  - Sửa: `"Sản phẩm "X", thuộc nhóm "Bánh, kẹo, snack", danh mục "Snack & Đồ nhắm"..."`
  - **Cần:** Catalog API trả về rootCategoryName hoặc map từ categoryId → root
  - Verify: Sau re-sync, "đồ ăn vặt" semantic score của Snack Lays tăng rõ rệt (>0.35), Gạo giảm (<0.25)

### Cập nhật docs
- [ ] **T5:** Update `test-assistant.md` — thêm hướng dẫn user cluster cho demo

### Verification
- [ ] **T6:** `npm test` → 145/145 pass
- [ ] **T7:** E2E: "Tôi muốn mua đồ ăn vặt" → product cards hiện ngay
- [ ] **T8:** E2E: Dashboard feedback stream → top 5 "đồ ăn vặt" KHÔNG chứa Gạo/Rau muống

## Thứ tự thực hiện
```
T4 (embedding enrichment) → Re-sync data → T3 (anchor re-ranking) → T1 (fallback keywords) → T2 (retry) → T5 (docs) → T6-T8 (verify)
```
> T4 trước vì re-sync mất thời gian. T3 sau vì phụ thuộc vào category_name trong knowledge base.

## Done When
- [ ] "Tôi muốn mua đồ ăn vặt" trả product cards
- [ ] "đồ ăn vặt" → top 5 không chứa Gạo, Rau muống (thuộc nhóm Bánh kẹo snack)  
- [ ] 145/145 tests pass
# RAG Search Quality — Fix Plan (v2)

## Goal
Fix 2 production bugs trong RAG pipeline:
1. "Tôi muốn mua đồ ăn vặt" → không trả product cards (fallback keyword miss)
2. Kết quả "đồ ăn vặt" trộn lẫn Gạo, Rau muống, Chả lụa (semantic search quality)

## Root Cause (Sửa lại sau dashboard evidence)

### Bug 1: Tin nhắn đầu tiên mất products
- `handleRecommendation()` → ragService null → fallback `handleSearchProductFallback()`
- Fallback extract keyword bằng `['tìm', 'search', 'có gì']` → KHÔNG cover "muốn mua"
- → keyword = CẢ CÂU → `searchProducts()` SQL ILIKE fail

### Bug 2: Semantic Search trộn sản phẩm lạc danh mục
**⚠️ Dashboard xác nhận: tất cả 5 sản phẩm đều source `content` — KHÔNG phải CF inject.**

```
Snack Lays      → AI Score: 0.2994  ← Top 1 (đúng danh mục)
Gạo thơm        → AI Score: 0.2951  ← SAI (Gạo ≠ Đồ ăn vặt)
Chả lụa heo     → AI Score: 0.2908  ← SAI
Rau muống        → AI Score: 0.2868  ← SAI
Xúc xích xông   → AI Score: 0.2828  ← SAI
```

**Nguyên nhân gốc:** Vietnamese SBERT embedding model coi "đồ ăn vặt" gần nghĩa với TẤT CẢ thực phẩm (cosine similarity ~0.28-0.30, chênh lệch chỉ 0.02). Content text hiện tại:
```
"Sản phẩm "Rau muống VietGAP", danh mục "Rau lá", giá 15.000 VND..."
```
→ Embedding không nhận diện "Rau lá" ≠ "Bánh, kẹo, snack" đủ mạnh.

## Tasks

### Bug 1: Fallback Keyword Extraction
- [ ] **T1:** Bổ sung trigger words cho RECOMMENDATION vào `handleSearchProductFallback()`
  - File: `handlers/read.handler.js:273`
  - Thêm: `['gợi ý', 'muốn mua', 'cần mua', 'mua đồ', 'đề xuất']`
  - Verify: Khi RAG chưa ready, "Tôi muốn mua đồ ăn vặt" → keyword = "đồ ăn vặt" → SQL search tìm được Snack

- [ ] **T2:** Retry nhẹ khi ragService null — check `embeddingClient.isReady` + delay 2s + retry 1 lần
  - File: `handlers/read.handler.js:20-23`
  - Logic: `if (!ragService && embeddingClient.isReady) → wait(2s) → re-check` 
  - Verify: Tin nhắn đầu tiên sau restart → vẫn trả products (hoặc fallback graceful)

### Bug 2: Semantic Search Quality (2 layer fix)

- [ ] **T3: Anchor Category Re-ranking** (review suggestion: "Mỏ neo")
  - File: `services/rag.service.js` → sau RRF Fusion (line 70-71)
  - Logic:
    1. Lấy Root Category của Top 1 RRF result → **Anchor = "Bánh, kẹo, snack"**
    2. Boost +0.05 cho các products cùng Root Category
    3. Penalize -0.03 cho products KHÁC Root Category
    4. Re-sort top5 theo adjusted RRF score
  - Verify: "đồ ăn vặt" → Top 1 = Snack Lays (Bánh kẹo) → Anchor boost → Bánh quy, Kẹo, Hạt điều lên top, Gạo/Rau muống bị đẩy xuống

- [ ] **T4: Enriching Embedding Content** — thêm rootCategoryName vào embedding text
  - File: `services/data-ingestion.service.js:222-237` (`_buildContentText`)
  - Sửa: `"Sản phẩm "X", thuộc nhóm "Bánh, kẹo, snack", danh mục "Snack & Đồ nhắm"..."`
  - **Cần:** Catalog API trả về rootCategoryName hoặc map từ categoryId → root
  - Verify: Sau re-sync, "đồ ăn vặt" semantic score của Snack Lays tăng rõ rệt (>0.35), Gạo giảm (<0.25)

### Cập nhật docs
- [ ] **T5:** Update `test-assistant.md` — thêm hướng dẫn user cluster cho demo

### Verification
- [ ] **T6:** `npm test` → 145/145 pass
- [ ] **T7:** E2E: "Tôi muốn mua đồ ăn vặt" → product cards hiện ngay
- [ ] **T8:** E2E: Dashboard feedback stream → top 5 "đồ ăn vặt" KHÔNG chứa Gạo/Rau muống

## Thứ tự thực hiện
```
T4 (embedding enrichment) → Re-sync data → T3 (anchor re-ranking) → T1 (fallback keywords) → T2 (retry) → T5 (docs) → T6-T8 (verify)
```
> T4 trước vì re-sync mất thời gian. T3 sau vì phụ thuộc vào category_name trong knowledge base.

## Done When
- [ ] "Tôi muốn mua đồ ăn vặt" trả product cards
- [ ] "đồ ăn vặt" → top 5 không chứa Gạo, Rau muống (thuộc nhóm Bánh kẹo snack)  
- [ ] 145/145 tests pass
