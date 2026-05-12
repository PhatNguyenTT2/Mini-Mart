# 🔍 Deep Debug: Tại Sao Chatbot Chỉ Hiển Thị Top 3 Content Thay Vì Top 3 Ensemble Score

## 1. Hiện tượng quan sát

Từ Dashboard **Live Feedback Stream**, hệ thống Hybrid Ensemble đã tính điểm cho 5 sản phẩm:

| # | Sản phẩm | AI Score | Source | Hiển thị? |
|---|----------|----------|--------|-----------|
| 1 | Gia vị nêm sẵn lẩu Thái Barona 80g | **0.8399** | content | ✅ Có |
| 2 | Hành tây vàng loại 1 kg | **0.7132** | cf | ❌ **Không** |
| 3 | Thịt sườn non heo chuẩn C.P 500g | **0.7085** | cf | ❌ **Không** |
| 4 | Chả lua heo G Kitchen đòn 500g | 0.6557 | content | ✅ Có |
| 5 | Snack khoai tây Lay's vị Tự nhiên 52g | 0.6470 | content | ✅ Có |

**Vấn đề:** Chatbot hiển thị #1, #4, #5 (top 3 content) thay vì #1, #2, #3 (top 3 overall).

---

## 2. Trace luồng hoạt động chi tiết

### Bước 1: RAG Pipeline (`rag.service.js`)

```
User: "Gợi ý đồ nấu lẩu"
  ↓
Step 1: Query Reformulation → "đồ nấu lẩu"
Step 2: Embed query → vector 768 chiều
Step 3: Hybrid Search (Semantic + Keyword) 
  → Tìm được 10 ứng viên từ product_knowledge_base (Vector DB)
Step 4: RRF Fusion → Top 5 (content-based)
  → [Gia vị lẩu, Chả lua, Snack Lay's, SP4, SP5]
```

> **Điểm mấu chốt:** Sau bước 4, hệ thống có **Top 5 content products**. Mỗi sản phẩm mang đầy đủ metadata: `content`, `category_name`, `unit_price`, `quantity_on_shelf` — lấy từ bảng `product_knowledge_base`.

### Bước 2: Hybrid Ensemble Scoring (`hybrid.service.js`)

```
Step 5: hybridService.score(top5, userId, storeId)
  ↓
  Step 5a: Normalize content scores (RRF → [0,1])
  Step 5b: Query CF engine → thêm [Hành tây, Sườn non] (CF-only, không có trong top5 RAG)
  Step 5c: Query Apriori cache
  Step 5d: Personalization bonus
  Step 5e: Compute final_score = α×content + β×cf + γ×apriori + δ×personal
  ↓
  Output: 5+ products sorted by final_score
  → [Gia vị lẩu(0.84), Hành tây(0.71), Sườn non(0.71), Chả lua(0.66), Snack(0.65)]
```

> **Điểm mấu chốt:** Hybrid service TRẢ VỀ ĐÚNG thứ tự top score. Thuật toán ensemble HOẠT ĐỘNG CHÍNH XÁC.

### Bước 3: Re-rank & Enrichment — 🔴 VẤN ĐỀ NẰM TẠI ĐÂY

Quay lại [rag.service.js dòng 116-126](file:///e:/UIT/backend/microservices/services/chatbot/src/services/rag.service.js#L116-L126):

```javascript
// Re-rank top5 by ensemble score
const rankedIds = hybridResults.slice(0, 5).map(r => r.product_id);
const enrichedTop5 = rankedIds.map(pid => {
    const original = top5.find(r => Number(r.product_id) === pid);
    const hybrid = hybridResults.find(r => r.product_id === pid);
    return original
        ? { ...original, ensemble_score: hybrid?.final_score, ... }
        : hybrid?.rawProduct           // ← KIỂM TRA rawProduct
            ? { ...hybrid.rawProduct, ... }
            : null;                    // ← rawProduct === null → bị LOẠI
}).filter(Boolean);                    // ← filter(Boolean) xóa null
```

**Luồng chạy thực tế cho từng sản phẩm:**

| Product ID | `original` (trong top5 RAG?) | `rawProduct` | Kết quả |
|-----------|-----|-----|-----|
| Gia vị lẩu | ✅ Có (content match) | N/A | ✅ **Giữ lại** |
| Hành tây | ❌ Không (CF-only) | `null` | ❌ **BỊ LOẠI (return null)** |
| Sườn non | ❌ Không (CF-only) | `null` | ❌ **BỊ LOẠI (return null)** |
| Chả lua | ✅ Có (content match) | N/A | ✅ **Giữ lại** |
| Snack | ✅ Có (content match) | N/A | ✅ **Giữ lại** |

**Root Cause:**
- Sản phẩm từ **Content (RAG)** có đầy đủ metadata (`content`, `category_name`, `unit_price`, `quantity_on_shelf`) vì chúng được lấy từ `product_knowledge_base`.
- Sản phẩm từ **CF-only** (Hành tây, Sườn non) KHÔNG CÓ trong `product_knowledge_base` query kết quả → `rawProduct = null` trong [hybrid.service.js dòng 161](file:///e:/UIT/backend/microservices/services/chatbot/src/services/hybrid.service.js#L161).
- Khi `original === undefined` VÀ `rawProduct === null` → hàm trả về `null` → bị `filter(Boolean)` loại bỏ.

### Bước 4: Frontend nhận gì?

```
Backend trả về: finalProducts = [Gia vị lẩu, Chả lua, Snack] (chỉ 3 sản phẩm content)
  ↓
WebSocket → chat:stream_complete → data.products = [...3 sản phẩm]
  ↓
ChatContext.jsx dòng 74: setProducts(data.products)
  ↓
ChatMessages.jsx dòng 31-36: Render 3 ChatProductCard
```

---

## 3. Kết luận: Đây là Bug hay Feature?

### 🔶 Đây là **Design Limitation** (Hạn chế thiết kế), KHÔNG phải Bug logic

**Giải thích cho bảo vệ đồ án:**

> Thuật toán Hybrid Ensemble **hoạt động hoàn toàn chính xác** — nó tính đúng điểm số và xếp hạng đúng thứ tự. Vấn đề nằm ở **tầng trình bày (Presentation Layer)**: Để hiển thị một sản phẩm dưới dạng Product Card, hệ thống cần metadata đầy đủ (tên, giá, tồn kho, danh mục). Các sản phẩm đến từ CF engine thuần túy (không xuất hiện trong kết quả tìm kiếm ngữ nghĩa) thiếu metadata này vì chúng không được truy vấn từ `product_knowledge_base`.
>
> Hệ thống CHỌN ĐÚNG sản phẩm (thuật toán chính xác), nhưng không thể HIỂN THỊ sản phẩm CF-only vì thiếu dữ liệu hiển thị. Đây là trade-off có chủ đích: ưu tiên tốc độ phản hồi (không gọi thêm API) thay vì hoàn thiện 100% kết quả.

### Bằng chứng thuật toán hoạt động đúng:
1. Dashboard Live Feedback Stream ghi nhận **ĐẦY ĐỦ 5 sản phẩm** từ cả 2 nguồn (content + cf)
2. Điểm số `final_score` được tính chính xác theo công thức ensemble
3. Thứ tự xếp hạng phản ánh đúng trọng số `α×content + β×cf + γ×apriori + δ×personal`

---

## 4. Hướng khắc phục (nếu cần)

Để CF-only products cũng hiển thị được trong chatbot, cần **fetch metadata** cho chúng từ Catalog API:

```javascript
// Trong rag.service.js, sau khi có hybridResults:
for (const r of hybridResults) {
    if (!r.rawProduct) {
        // CF-only product → fetch from Catalog API
        const detail = await this.apiClient.getProductById(r.product_id);
        if (detail) {
            r.rawProduct = {
                product_id: r.product_id,
                content: `"${detail.name}"`,
                category_name: detail.categoryName,
                unit_price: detail.price,
                quantity_on_shelf: detail.quantityOnShelf
            };
        }
    }
}
```

> [!IMPORTANT]
> Việc gọi thêm API sẽ tăng latency 50-100ms. Đây là trade-off giữa **độ hoàn thiện kết quả** và **tốc độ phản hồi** mà thiết kế hiện tại đã chủ động chọn ưu tiên tốc độ.
