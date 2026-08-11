# Tiêu chuẩn Đánh giá Độ thưa thớt (Sparsity) & Chỉ số Kỳ vọng trong Bài toán Gợi ý

> **Chuẩn đang có hiệu lực — benchmark v5 (temporal novel-purchase full-catalog).**
> Các giả định 1,000,000 interactions, split ngẫu nhiên và mật độ 3.85% ở bên
> dưới chỉ là tài liệu lịch sử; không dùng để phê duyệt training/release.

## Protocol v5 bắt buộc

- Snapshot bất biến: **823,371 events**, **5,000 users**, **5,200 items**, **250
  cold items**, split temporal train/VAL/TEST `658,697 / 82,337 / 82,337`.
- Evaluation dùng organic novel purchases; history VAL = train, history TEST =
  train+VAL; seen items bị mask và ranking full catalog ổn định theo
  `(-score, raw_product_id)`.
- Reference density: `356,181 / 26,000,000 = 1.3699%` distinct user-item
  cells; event frequency `823,371 / 26,000,000 = 3.1668%`. Đây là mô tả dữ
  liệu, không phải quality gate.
- Hard promotion floors, không được hạ: **GAUC >= 0.75**, **HR@10 >= 0.15**,
  **NDCG@10 >= 0.08**. Đồng thời phải pass strongest-baseline paired CI,
  Random CI, semantic traps `10/10`, cold parity, strict rule readiness và
  Wide readiness.
- Safety kill-switch trong training vẫn là non-finite hoặc `val_gauc < 0.50`;
  safety này không thay thế các promotion floors ở trên.
- Không tuyên bố Hybrid victory nếu thiếu bất kỳ gate nào; không chạy seed kế
  tiếp khi single-seed VAL fail.

Phần dưới đây giữ lại các phép tính cũ để truy vết lịch sử, nhưng không còn là
specification cho benchmark v5.

Độ thưa thớt (**Sparsity**) là một trong những đặc điểm quan trọng nhất quyết định độ khó của bài toán gợi ý. Nó phản ánh tỷ lệ giữa số lượng tương tác đã xảy ra so với tổng số tương tác có thể xảy ra.

---

## 1. Cách tính độ thưa thớt

Công thức tính Sparsity dựa trên ma trận User-Item:

$$Sparsity = 1 - \frac{\text{Số lượng tương tác (Interactions)}}{\text{Tổng số User} \times \text{Tổng số Item}}$$

Tương tự, ta có chỉ số Mật độ (**Density**), thường được dùng phổ biến hơn để nói về độ "dày":

$$Density = 1 - Sparsity$$

### Với tập dữ liệu của bạn:
- **Users:** 5,000
- **Items:** 5,200
- **Tương tác (Interactions):** 1,000,000

### Tính toán:
- **Tổng số ô trong ma trận (Khả năng tương tác tối đa):** $5,000 \times 5,200 = 26,000,000$
- **Density (Mật độ):** $1,000,000 / 26,000,000 = 0.03846$ (khoảng **3.85%**)
- **Sparsity (Độ thưa thớt):** $1 - 0.03846 = 0.9615$ (khoảng **96.15%**)

---

## 2. Dữ liệu khi nào là Thưa thớt và Dày đặc?

Trong ngành Recommender Systems, các mốc đánh giá thường không có một ranh giới tuyệt đối, nhưng dựa trên kinh nghiệm từ các tập dữ liệu benchmark phổ biến (như MovieLens, Amazon, Taobao), ta có thể phân loại như sau:

| Mức độ | Mật độ (Density) | Độ thưa (Sparsity) | Đặc điểm & Ví dụ |
| :--- | :--- | :--- | :--- |
| **Rất thưa thớt** *(Extremely Sparse)* | < 0.1% | > 99.9% | Đặc trưng của thương mại điện tử lớn. Hầu hết user chỉ mua vài món trong hàng triệu món. Ví dụ: Amazon Books (Sparsity ~99.99%). Mô hình rất khó hội tụ, cần dùng đồ thị (GNN) hoặc thông tin phụ (content-based). |
| **Thưa thớt** *(Sparse)* | 0.1% - 1% | 99% - 99.9% | Rất phổ biến. Ví dụ: Criteo, Taobao, Yelp. Cần các kỹ thuật xử lý cold-start mạnh. |
| **Trung bình** *(Moderate)* | 1% - 5% | 95% - 99% | Tập dữ liệu lý tưởng cho nghiên cứu học thuật. Ví dụ: MovieLens 1M (Density ~4.19%). Các mô hình Collaborative Filtering truyền thống (Matrix Factorization) hoạt động rất tốt ở mốc này. |
| **Dày đặc** *(Dense)* | > 5% | < 95% | Ít gặp trong thực tế (trừ khi dữ liệu đã được lọc rất kỹ). Ví dụ: MovieLens 100K (Density ~6.3%). Dễ bị overfitting nếu mô hình quá phức tạp. |

### Đánh giá tập dữ liệu của bạn:
Với độ thưa thớt **96.15%** (Density **~3.85%**), dữ liệu của bạn nằm ở mức **Trung bình (Moderate)**, thậm chí có thể coi là khá "dày" so với tiêu chuẩn E-commerce thực tế. Đây là một tỷ lệ tuyệt vời để đào tạo mô hình. 

Trung bình, mỗi user trong tập của bạn có tới **200 tương tác** ($1,000,000 / 5,000$), cung cấp một lượng thông tin lịch sử rất dồi dào.

---

## 3. Các chỉ số kỳ vọng với mức Sparsity này (Density ~3.85%)

Vì dữ liệu của bạn khá "dày" (mỗi user có nhiều tương tác), mô hình sẽ học được biểu diễn (embeddings) của User và Item rất tốt. Do đó, các chỉ số đánh giá (trên tập test ngẫu nhiên, Full Catalog) kỳ vọng sẽ cao hơn đáng kể so với mức trung bình của các tập siêu thưa thớt.

Dưới đây là khoảng giá trị hợp lý *(rule of thumb)* nếu bạn áp dụng các mô hình Deep Learning chuẩn (như NCF, DIN, hoặc SASRec):

- **HR@10 (Hit Rate):** Kỳ vọng nằm trong khoảng **0.15 đến 0.35** (15% - 35%). Do số lượng Item khá nhỏ (5,200), việc tìm ra đúng item trong top 10 dễ dàng hơn nhiều so với việc mò mẫm trong 1 triệu item.
- **NDCG@10:** Kỳ vọng nằm trong khoảng **0.08 đến 0.20** (8% - 20%).
- **GAUC (Nếu áp dụng cho Ranking/CTR):** Kỳ vọng đạt mức khá cao, từ **0.70 đến 0.85**. Với lượng thông tin lịch sử dày đặc, mô hình dễ dàng phân biệt được sự ưu tiên của từng cá nhân.

> [!IMPORTANT]
> **Lưu ý quan trọng:** Nếu HR@10 của bạn thấp hơn 10% trên bộ dữ liệu có mật độ ~3.85% và không gian item chỉ 5,200, điều đó có thể báo hiệu lỗi trong quá trình xử lý dữ liệu (data leakage, split train/test sai cách) hoặc mô hình đang bị underfitting.
