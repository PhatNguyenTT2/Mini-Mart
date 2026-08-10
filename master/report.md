# Báo Cáo Đánh Giá Metric Full-Catalog Recommendation System

Dưới đây là khoảng giá trị thực tế của các hệ thống thương mại điện tử lớn (Amazon, Taobao, Instacart) khi đo lường trên bài toán xếp hạng **Full-Catalog Evaluation** (không lấy mẫu âm / zero-sampling):

---

## Bảng Tổng hợp Benchmarks & Kết quả Mô hình

| Metric | Random Baseline | Chuẩn Ngành (Small/Dense Catalog) | Kết quả Mô hình Hybrid | Đánh giá Hiệu năng |
| :--- | :---: | :---: | :---: | :---: |
| **GAUC** | `0.5000` | `0.6500 - 0.7500` | **`0.8507`** | **Xuất sắc** |
| **HR@10** | `~0.0072` | `0.2000 - 0.4000` | **`0.4940`** | **Rất cao** |
| **NDCG@10** | `~0.0010` | `0.0300 - 0.0800` | **`0.0644`** | **Tốt / Đúng chuẩn** |

---

## 1. GAUC (Group AUC / User-level AUC)

### Bản chất Metric
- Đo lường khả năng phân loại cặp (pairwise ranking): Xác suất mô hình xếp một sản phẩm người dùng thích cao hơn một sản phẩm người dùng không thích.
- **Ưu điểm lớn nhất**: Miễn nhiễm với quy mô danh mục (scale-invariant).

### Khoảng chuẩn ngành
- **Ngẫu nhiên (Random Baseline)**: Luôn xoay quanh mức `0.5000`.
- **Trung bình / Chấp nhận được**: `0.6500 - 0.7500`.
- **Tốt đến Rất Tốt**: `0.7500 - 0.8500`.
- **Xuất sắc**: `> 0.8500`.

> [!TIP]
> **Đánh giá mô hình của bạn**:
> Mô hình Hybrid của bạn đạt **GAUC = 0.8507**. Đây là một con số xuất sắc trong môi trường E-commerce thực tế, chứng tỏ mô hình học được ranh giới quyết định (*decision boundary*) cực kỳ sắc bén giữa hàng liên quan và hàng nhiễu.

---

## 2. HR@10 (Hit Rate @ 10)

### Bản chất Metric
- Tỷ lệ người dùng có **ít nhất 1 sản phẩm liên quan** xuất hiện trong Top 10 gợi ý.
- Chỉ số này bị ảnh hưởng nặng nề bởi quy mô danh mục (*Catalog Size*) và độ thưa (*Sparsity*).

### Khoảng chuẩn ngành (Full-Catalog Evaluation)
- **Mega-scale** (Hàng triệu SKUs, ví dụ *Amazon*): `0.0100 - 0.0500` (1% - 5%). Tìm đúng 1 món trong hàng triệu món vào Top 10 là cực khó.
- **Large-scale** (Vài chục ngàn SKUs, ví dụ *Taobao*, *Instacart*): `0.0500 - 0.1500`.
- **Small/Dense-scale** (Dưới 10,000 SKUs, mật độ cao như *Mini-Mart*): `0.2000 - 0.4000`.

> [!NOTE]
> **Đánh giá mô hình của bạn**:
> Con số **HR@10 = 0.4940** (gần 50%) là rất cao. Điều này đạt được nhờ 2 yếu tố:
> 1. Tập dữ liệu có mật độ tương tác dày (`7.2% - 10%`).
> 2. Đặc thù ngành hàng tiêu dùng/bách hóa (groceries) có tính chu kỳ và quy luật mua kèm (*co-purchase*) lặp lại cao, giúp nhánh **Wide Apriori** phát huy tối đa sức mạnh.

---

## 3. NDCG@10 (Normalized Discounted Cumulative Gain @ 10)

### Bản chất Metric
- Đánh giá chất lượng và vị trí của các sản phẩm được xếp hạng trong Top 10.
- Đây luôn là con số nhỏ trong báo cáo Full-Catalog. Lý do là mẫu số (*Ideal DCG - IDCG*) được tính dựa trên **toàn bộ** các sản phẩm người dùng thực sự tương tác. Nếu người dùng tương tác với 50 sản phẩm, IDCG sẽ rất lớn, làm điểm NDCG@10 bị chia nhỏ hơn nhiều so với phương pháp Lấy mẫu (*Sampled Evaluation* - nơi người dùng chỉ có 1 sản phẩm đúng).

### Khoảng chuẩn ngành (Full-Catalog Evaluation)
- **Mega-scale**: Thường `< 0.0100`.
- **Large-scale**: `0.0100 - 0.0300`.
- **Small/Dense-scale**: `0.0300 - 0.0800`.

> [!IMPORTANT]
> **Đánh giá mô hình của bạn**:
> Con số **NDCG@10 = 0.0644** hoàn toàn phản ánh đúng thực tế của một bài toán Full-Catalog Ranking với danh mục 1,380 SKUs.
> 
> *So sánh với Baseline*:
> - Mức `0.00318` của baseline Deep-only gần như không đưa được relevant item vào Top 10.
> - Việc kiến trúc **Hybrid** kéo điểm số lên **`0.0644`** (gấp 20 lần Deep-only) thể hiện một bước nhảy vọt về chất lượng xếp hạng.