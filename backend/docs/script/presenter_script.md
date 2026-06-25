# 🎤 KỊCH BẢN THUYẾT MINH CHO NGƯỜI TRÌNH BÀY

## Trình Diễn 4 Thuật Toán

> **Nguyên lý điều hướng (Contextual Router):** Hệ thống tự động kích hoạt thuật toán tối ưu dựa trên ý định người dùng:

| Thuật toán | Khi nào kích hoạt | Ví dụ thực tế |
|---|---|---|
| **Content-Based RAG (α)** | Khách tìm kiếm chủ động, hỏi rộng | *"Tôi muốn mua đồ ăn vặt"* -> Gợi ý hạt điều, snack, khô gà |
| **Apriori (γ)** | Đã xác định sản phẩm mỏ neo cụ thể | *"Tôi muốn mua bia Heineken"* -> Gợi ý thêm đồ ăn kèm (Khô gà, Coca) |
| **Collaborative Filtering (β)** | Khách lướt xem chung, không đích danh | *"Gợi ý cho tôi vài món"* -> Gợi ý Nước mắm, Rau muống (nếu là Nội trợ) |
| **Session Context (δ)** | Chat nhiều lượt, ý định biến đổi liên tục | Lượt 1: *Lẩu Thái* -> Lượt 2: *Rau ăn kèm* -> Lượt 3: *"Gợi ý thêm đi"* -> Bún, Bò Mỹ |

---

## 🎭 ACT 1 · Sức Mạnh Ngữ Nghĩa (Content-Based RAG)

> **Mục đích:** Chứng minh RAG hiểu ngữ nghĩa (không chỉ khớp từ khóa). Truy vấn rộng "đồ ăn vặt" hoặc "bánh kẹo" trả về đúng sản phẩm thuộc danh mục bánh kẹo mà không cần gõ tên cụ thể.
>
> **Điểm mạnh:** Giải quyết vấn đề của Keyword Search truyền thống (từ đồng nghĩa, từ lóng). Pipeline song song Semantic + Keyword, hợp nhất bằng RRF.

### Thao tác
1. Gõ vào Chatbot: **"Tôi muốn mua đồ ăn vặt"**
2. Đợi 2–3s → 3 product cards xuất hiện
3. Click vào **Bánh xốp phô mai Nabati**
4. Chỉ tay sang Dashboard → badge `[content]` nhảy lên

### Lời thuyết minh

> *"Dạ thưa cô, đầu tiên em xin demo khả năng tìm kiếm ngữ nghĩa — Semantic Search. Thay vì gõ đúng tên sản phẩm, em chỉ nhập ý định chung là 'đồ ăn vặt'.*
>
> *Lập tức, hệ thống trả về Bánh xốp, Bánh quy và Kẹo mút. Cơ chế đằng sau là sự kết hợp song song giữa:*
> - *(1) Semantic Search — mã hóa câu hỏi thành Vector đa chiều bằng, tính Cosine Similarity trên pgvector;*
> - *(2) Keyword Search — full-text search bằng PostgreSQL tsvector tiếng Việt.*
>
> *Hai kết quả được hợp nhất bằng Reciprocal Rank Fusion (RRF), đảm bảo vừa đúng ngữ nghĩa vừa chính xác từ khóa.*
>
> *(Chỉ tay vào Dashboard)* *3 sản phẩm đầu tiên đều là kết quả Content-Based — 'bánh xốp', 'bánh quy', 'kẹo mút' đều tự động được tìm thấy mặc dù khách hàng không cần truy vấn đúng nhãn tên. Nhãn* ***[content]*** *xác nhận tín hiệu Content-RAG đóng vai trò chủ đạo."*

---

## 🎭 ACT 2 · Khai Phá Quy Luật (Apriori Cross-sell)

> **Mục đích:** Chứng minh hệ thống phát hiện quy luật "mua kèm" từ các đơn hàng lịch sử.
>
> **Điểm mạnh:** Khai phá luật kết hợp xuyên danh mục (Cross-Category Discovery) — phát hiện mối quan hệ ẩn giữa các mặt hàng dường như không liên quan (Bia → Khô gà, Coca). Hiện tượng "Bia và Bỉm" kinh điển, tối ưu AOV (Average Order Value).


### Thao tác
1. **Bấm 🔄 Phiên chat mới**
2. Gõ: **"Tôi muốn mua bia Heineken"**
3. Đợi kết quả → chỉ vào Coca-Cola và Khô gà (badge `[apriori]`)
4. Click vào **Khô gà lá chanh**
5. Chỉ tay sang Dashboard → badge `[apriori]` nhảy lên

### Lời thuyết minh

> *"Kế tiếp là thuật toán Apriori khai phá luật kết hợp. Khi em hỏi mua Bia Heineken, hệ thống không chỉ trả về Bia, mà còn tự động chèn thêm Coca-Cola và Khô gà.*
>
> *(Chỉ tay lên màn hình)* *Thưa Thầy Cô, sản phẩm Coca-Cola và Khô gà xuất hiện dù người dùng KHÔNG hỏi về chúng. Đây là thuật toán Apriori — khai phá luật kết hợp từ các đơn hàng. Hệ thống phát hiện khách mua Bia Heineken thường mua kèm Coca-Cola (Lift=1.90, 165 đơn mua kèm) và Khô gà (Lift=1.74, 146 đơn mua kèm).*
>
> *Đây chính là hiện tượng 'Bia và Bỉm' kinh điển trong Data Mining. Nhãn* ***[apriori]*** *trên Dashboard xác nhận thuật toán bán chéo Cross-sell đang hoạt động chính xác."*

---

## 🎭 ACT 3 · Cá Nhân Hóa Ẩn Danh (Collaborative Filtering)

> **Mục đích:** Chứng minh cá nhân hóa mù (Blind Personalization) — AI nhận diện thói quen riêng khi người dùng hỏi chung chung, không có từ khóa mỏ neo.
>
> **Điểm mạnh:** Ma trận tương đồng Item-Item phân loại user theo hành vi cộng đồng. Cùng một câu hỏi, nhưng kết quả khác nhau hoàn toàn giữa các nhóm người dùng (Nội trợ → Nước mắm, Rau muống, Gia vị lẩu; Sinh viên → Mì tôm, Xúc xích, Coca).
>
> **Tài khoản demo:** User #51 thuộc nhóm **Nội trợ Nấu lẩu** (ID 1–150). CF phân tích user interactions, phát hiện User #51 có hành vi tương đồng với nhóm mua bò, nấm, rau, gia vị → gợi ý sản phẩm từ cùng cluster.


### Thao tác
1. **Bấm 🔄 Phiên chat mới**
2. Gõ câu lệnh bâng quơ: **"Gợi ý cho tôi vài món"**
3. Đợi kết quả → 4/5 sản phẩm có badge `[cf]`
4. Click vào **Nước mắm Nam Ngư**
5. Chỉ tay sang Dashboard → badge `[cf]` nhảy lên, AI Score ~0.7695

### Lời thuyết minh

> *"Hệ thống thực hiện cá nhân hóa bằng Collaborative Filtering. Em cố tình dùng một câu hỏi hoàn toàn không chứa từ khóa cụ thể: 'Gợi ý cho tôi vài món'. Vậy tại sao Nước mắm Nam Ngư, Gia vị lẩu Thái, Cá viên chiên xuất hiện?*
>
> *Đó là nhờ Collaborative Filtering — hệ thống phân tích dữ liệu tương tác của các người dùng trong nhóm trước đó, phát hiện tài khoản #51 thuộc nhóm 'Nội trợ Nấu lẩu' (User 1–150), nên gợi ý sản phẩm mà 150 user tương tự thường xuyên mua.*
>
> *Nếu em đổi sang tài khoản sinh viên (User 151–300), kết quả sẽ hoàn toàn khác — Mì Hảo Hảo, Xúc xích, Coca-Cola.*
>

---

## 🎭 ACT 4 · Ngữ Cảnh Xuyên Phiên (Session Context) — Cú Chốt

> **Mục đích:** Chứng minh AI duy trì ngữ cảnh xuyên suốt phiên chat (Multi-turn Context) — giải bài toán Đại từ thế vị.
>
> **Điểm mạnh:** Khi khách hỏi "Gợi ý thêm đi" (không chứa bất kỳ từ khóa chính nào), Toàn bộ dữ liệu warmUp in-memory, runtime cực nhanh với O(1). Tự động nhận diện chủ đề từ lịch sử, khóa chặt danh mục mà không cần truy xuất lại DB.


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

## 🎓 KẾT LUẬN — Vòng Lặp Học Hỏi Tự Động (30 giây)

*(Nói chậm lại, chỉ tay vào toàn bộ bảng Live Feedback và biểu đồ Weight Evolution)*

> *"Thưa cô, những thao tác Click vừa rồi không chỉ để xem. Toàn bộ chúng đang được lưu xuống Database với nguồn gốc rõ ràng.*
>
> *Cụ thể, mỗi hành động của khách hàng đều được chấm điểm theo mức độ cam kết:*
> - *Rê chuột qua (hover) tính 0.1 điểm*
> - *Click vào sản phẩm tính 0.2 điểm*
> - *Thêm vào giỏ hàng tính 0.5 điểm*
> - *Mua hàng thành công tính trọn 1.0 điểm*
>
> *Ví dụ thực tế: Khi em vừa click Bánh xốp Nabati ở ACT 1, hệ thống ghi nhận nguồn là `content` với 0.2 điểm. Click Khô gà ở ACT 2 ghi nhận nguồn `apriori` với 0.2 điểm. Như vậy, mỗi ACT đều đóng góp tín hiệu cho riêng thuật toán của nó.*
>
> *(Chỉ vào biểu đồ Weight Evolution)* *Hàng đêm, thuật toán Weight Learner tự động:*
> 1. *Tính Weighted Conversion Rate cho từng thuật toán — tức là tỷ lệ khách hàng tương tác trên tổng số sản phẩm được gợi ý*
> 2. *Chuẩn hóa các tỷ lệ đó thành trọng số mới*
> 3. *Làm mượt bằng EWMA — công thức 80% giá trị cũ cộng 20% giá trị mới — để tránh dao động đột ngột*
> 4. *Giới hạn mỗi trọng số trong khoảng an toàn 5% đến 60%, đảm bảo không thuật toán nào bị triệt tiêu hoàn toàn*
>
> *Hệ thống còn có guardrail an toàn: nếu tổng feedback dưới 20 mẫu hoặc không có tương tác mới trong 24 giờ, Weight Learner sẽ TỪ CHỐI điều chỉnh và giữ nguyên trọng số. Riêng trọng số δ của Session Context được cố định, không tham gia vào vòng lặp tự học, để tránh overfitting trên dữ liệu phiên ngắn hạn.*
>
> *Kết quả được lưu vào bảng `ensemble_weights_history` — chính là dữ liệu nguồn cho biểu đồ Weight Evolution mà Thầy Cô đang thấy trên Dashboard.*
>
> *Đây là vòng lặp khép kín: Gợi ý → Tương tác → Tự học → Gợi ý tốt hơn. Hệ thống hoàn toàn tự hoàn thiện mà không cần con người can thiệp. Em xin kết thúc phần Demo Hệ thống Khuyến nghị."*
