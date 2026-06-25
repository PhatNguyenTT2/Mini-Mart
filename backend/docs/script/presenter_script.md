# 🎤 KỊCH BẢN THUYẾT MINH CHO NGƯỜI TRÌNH BÀY
## Demo Hybrid RAG Recommendation — Bảo Vệ Đồ Án

> **Mục đích tài liệu:** Script nói cho người đứng trước Hội đồng. Mỗi ACT gồm: (1) hành động thao tác trên máy, (2) lời thuyết minh đọc/nói tương ứng.

---

## Chuẩn Bị Trước Khi Lên Bục

- Mở sẵn **2 cửa sổ song song**: Customer App (Chatbot) + Admin Dashboard (Tab Live Feedback).
- Đăng nhập tài khoản **Customer ID #51** (Nhóm Nội trợ).
- Reset bảng dữ liệu feedback nếu cần.

---

## 🎭 ACT 1 · Sức Mạnh Ngữ Nghĩa (Content-Based RAG)

### Thao tác
1. Gõ vào Chatbot: **"Tôi muốn mua đồ ăn vặt"**
2. Đợi 2–3s → 3 product cards xuất hiện
3. Click vào **Bánh xốp phô mai Nabati**
4. Chỉ tay sang Dashboard → badge `[content]` nhảy lên

### Lời thuyết minh

> *"Dạ thưa Hội đồng, đầu tiên em xin demo khả năng tìm kiếm ngữ nghĩa — Semantic Search. Thay vì gõ đúng tên sản phẩm, em chỉ nhập ý định chung là 'đồ ăn vặt'.*
>
> *Lập tức, hệ thống trả về Bánh xốp, Bánh quy và Kẹo mút. Cơ chế đằng sau là sự kết hợp song song giữa:*
> - *(1) Semantic Search — mã hóa câu hỏi thành Vector 768 chiều bằng mô hình multilingual-e5-base, tính Cosine Similarity trên pgvector;*
> - *(2) Keyword Search — full-text search bằng PostgreSQL tsvector tiếng Việt.*
>
> *Hai kết quả được hợp nhất bằng Reciprocal Rank Fusion (RRF), đảm bảo vừa đúng ngữ nghĩa vừa chính xác từ khóa.*
>
> *(Chỉ tay vào Dashboard)* *3 sản phẩm đầu tiên đều là kết quả Content-Based — 'bánh xốp', 'bánh quy', 'kẹo mút' đều tự động được tìm thấy mặc dù khách hàng không cần truy vấn đúng nhãn tên. Nhãn* ***[content]*** *xác nhận tín hiệu Content-RAG đóng vai trò chủ đạo."*

---

## 🎭 ACT 2 · Khai Phá Quy Luật (Apriori Cross-sell)

### Thao tác
1. **Bấm 🔄 Phiên chat mới**
2. Gõ: **"Tôi muốn mua bia Heineken"**
3. Đợi kết quả → chỉ vào Coca-Cola và Khô gà (badge `[apriori]`)
4. Click vào **Khô gà lá chanh**
5. Chỉ tay sang Dashboard → badge `[apriori]` nhảy lên

### Lời thuyết minh

> *"Kế tiếp là thuật toán Apriori khai phá luật kết hợp. Khi em hỏi mua Bia Heineken, hệ thống không chỉ trả về Bia, mà còn tự động chèn thêm Coca-Cola và Khô gà.*
>
> *(Chỉ tay lên màn hình)* *Thưa Thầy Cô, sản phẩm Coca-Cola và Khô gà xuất hiện dù người dùng KHÔNG hỏi về chúng. Đây là thuật toán Apriori — khai phá luật kết hợp từ 500 đơn hàng. Hệ thống phát hiện khách mua Bia Heineken thường mua kèm Coca-Cola (Lift=1.90, 165 đơn mua kèm) và Khô gà (Lift=1.74, 146 đơn mua kèm).*
>
> *Đây chính là hiện tượng 'Bia và Bỉm' kinh điển trong Data Mining. Nhãn* ***[apriori]*** *trên Dashboard xác nhận thuật toán bán chéo Cross-sell đang hoạt động chính xác."*

---

## 🎭 ACT 3 · Cá Nhân Hóa Ẩn Danh (Collaborative Filtering)

### Thao tác
1. **Bấm 🔄 Phiên chat mới**
2. Gõ câu lệnh bâng quơ: **"Gợi ý cho tôi vài món"**
3. Đợi kết quả → 4/5 sản phẩm có badge `[cf]`
4. Click vào **Nước mắm Nam Ngư**
5. Chỉ tay sang Dashboard → badge `[cf]` nhảy lên, AI Score ~0.7695

### Lời thuyết minh

> *"Đỉnh cao của hệ thống nằm ở ACT 3: Cá nhân hóa bằng Collaborative Filtering. Em cố tình dùng một câu hỏi hoàn toàn không chứa từ khóa cụ thể: 'Gợi ý cho tôi vài món'. Vậy tại sao Nước mắm Nam Ngư, Gia vị lẩu Thái, Cá viên chiên xuất hiện?*
>
> *Đó là nhờ Collaborative Filtering — hệ thống phân tích dữ liệu tương tác của 500 người dùng, phát hiện tài khoản #51 thuộc nhóm 'Nội trợ Nấu lẩu' (User 1–150), nên gợi ý sản phẩm mà 150 user tương tự thường xuyên mua.*
>
> *Nếu em đổi sang tài khoản sinh viên (User 151–300), kết quả sẽ hoàn toàn khác — Mì Hảo Hảo, Xúc xích, Coca-Cola.*
>
> *Slot Partitioning ưu tiên CF chiếm 3–4 slot đầu cho welcome query, đảm bảo cá nhân hóa nổi bật. Sản phẩm CF ban đầu không có metadata hiển thị — hệ thống giải quyết bằng Two-Tier Hydration: tra cứu Local KB trước, fallback Catalog API với timeout 500ms."*

---

## 🎭 ACT 4 · Ngữ Cảnh Xuyên Phiên (Session Context) — Cú Chốt

### Thao tác (3 lượt liên tiếp)
1. **Bấm 🔄 Phiên chat mới**
2. **Lượt 1:** Gõ **"Tôi muốn nấu lẩu Thái cuối tuần"** → Đợi kết quả
3. **Lượt 2:** Gõ **"Gợi ý rau ăn kèm lẩu đi"** → Đợi kết quả (Rau muống, Nấm)
4. **Lượt 3:** Gõ cộc lốc **"Gợi ý thêm đi"** → Kết quả có badge **`[session]`**
5. Click vào **Hành tây vàng**
6. Chỉ tay sang Dashboard → badge `[session]` nhảy lên, AI Score bứt phá **~0.9480** 🎉

### Lời thuyết minh (sau khi kết quả Lượt 3 hiển thị)

> *"Phần cuối cùng giải quyết bài toán đại từ thế vị trong hội thoại đa lượt. Ở lượt thứ 3, người dùng hoàn toàn KHÔNG sử dụng từ khóa liên quan đến lẩu hay rau — chỉ gõ 'Gợi ý thêm đi'. Tuy nhiên hệ thống vẫn trả về Hành tây vàng, Rau muống, Nấm kim châm với nhãn nguồn gốc là* ***[session]***.*
>
> *Lý giải cơ chế hoạt động:*
> *1. Bộ giải nghĩa Deterministic Reformulator phát hiện ý định tiếp tục và kết hợp dữ liệu lịch sử chat cũ (Lượt 2 hỏi về rau ăn lẩu) để duy trì ngữ cảnh lẩu.*
> *2. Dịch vụ Session Context Service kích hoạt và so khớp nhóm sản phẩm thuộc cụm chủ đề lẩu (vegetables/hotpot cluster).*
> *3. Hệ thống áp dụng Session Boost — cộng trực tiếp giá trị boost khoảng 0.15–0.20 vào điểm score để ưu tiên các mặt hàng liên đới.*
> *4. Bộ gán nhãn của RAG service phát hiện sản phẩm có thuộc tính `session_boosted = true`, tiến hành ghi đè `topSource = 'session'` để báo về Feedback Stream chính xác thuật toán chịu trách nhiệm.*
>
> *Điểm ưu việt: Nhờ cơ chế gán nhãn [session], bộ học tự động Weight Learner hàng đêm sẽ nhận diện được chính xác hành vi bấm click của khách có phải là do gợi ý bám sát ngữ cảnh phiên chat hay không, từ đó tối ưu trọng số delta (δ).*
>
> *Điểm thiết kế quan trọng: Session Context sử dụng Category-Driven mapping thay vì hardcode Product ID — khi admin thêm sản phẩm mới vào danh mục rau/bún/thịt, hệ thống tự động nhận diện mà không cần sửa code. Toàn bộ dữ liệu warmUp in-memory, runtime cực nhanh với O(1)."*

---

## 🎓 KẾT LUẬN (Vòng Lặp EWMA — 30 giây)

*(Nói chậm lại, chỉ tay vào toàn bộ bảng Live Feedback)*

> *"Thưa Hội đồng, những thao tác Click vừa rồi không chỉ để xem. Toàn bộ chúng đang được lưu xuống Database với nguồn gốc rõ ràng là content, cf, hay apriori.*
>
> *Tất cả 4 tương tác vừa rồi đều được ghi nhận vào bảng `recommendation_feedback` với nguồn gốc thuật toán rõ ràng.*
>
> *Hàng đêm, thuật toán Weight Learner sẽ tự động:*
> - *Tính Conversion Rate (click → mua) của từng thuật toán*
> - *Điều chỉnh trọng số α, β, γ, δ bằng EWMA (Exponential Weighted Moving Average)*
> - *Lưu lịch sử điều chỉnh vào bảng `ensemble_weights_history`*
>
> *Đây là vòng lặp khép kín: Gợi ý → Tương tác → Tự học → Gợi ý tốt hơn. Hệ thống hoàn toàn tự hoàn thiện mà không cần con người can thiệp. Em xin kết thúc phần Demo Hệ thống Khuyến nghị."*
