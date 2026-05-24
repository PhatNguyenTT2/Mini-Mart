# Chatbot UI Improvement (Hiding Algorithm & Displaying Product Images)

🤖 **Applying knowledge of `@frontend-specialist` and `@backend-specialist`...**

## Proposed Changes

---

### Chatbot UI (Customer Frontend)

#### [MODIFY] [ChatProductCard.jsx](file:///e:/UIT/cv/backend/customer/src/components/ChatWidget/components/ChatProductCard.jsx)

- **Hide source badge**: Comment out or remove the absolute positioned `div` containing `{source}` (lines 101-104), as it violates clean UX and confuses standard customers.
- **Ensure correct image rendering**: Keep standard image loading with safety fallback.

---

### RAG Service (Chatbot Backend)

#### [MODIFY] [rag.service.js](file:///e:/UIT/cv/backend/backend/services/chatbot/src/services/rag.service.js)

- **Query catalog details for image URL**:
  In [recommend()](file:///e:/UIT/cv/backend/backend/services/chatbot/src/services/rag.service.js#29-334), after parsing synchronized products:
  1. Retrieve product IDs from `syncedProducts`.
  2. Batch query Catalog service using `this.apiClient.getProductsByIds(ids)` to get real-time product details including image paths.
  3. Map the returned `image` along with name, categoryName, unitPrice, and quantityOnShelf to avoid stale data.
  4. Perform this for both Phase 3 and Phase 2 fallback return paths.

---

### Unit Tests

#### [MODIFY] [rag.service.test.js](file:///e:/UIT/cv/backend/backend/services/chatbot/tests/unit/rag.service.test.js)

- Mock `apiClient.getProductsByIds` in global test fixtures.
- Add test case verifying that [recommend()](file:///e:/UIT/cv/backend/backend/services/chatbot/src/services/rag.service.js#29-334) correctly fetches and merges product images from Catalog API for recommended products.

---

## Verification Plan

### Automated Tests
- Run `npx jest tests/unit/rag.service.test.js` to ensure the mock calls and image enrichment works properly.

### Manual UI Verification
1. Clean-build and start the application.
2. Ask the chatbot "gợi ý đồ nấu lẩu".
3. Verify that the product cards (e.g. Ba chỉ bò Mỹ, Nấm kim châm, Gia vị lẩu Thái, Bún tươi, Gạo thơm) render matching actual product image cards (no blank placeholders).
4. Verify the top-right yellow/blue/green source badges ("content", "apriori", "session") are completely hidden.
