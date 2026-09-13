# GIẢI NGHĨA VÀ PHÂN TÍCH HỌC THUẬT CHUYÊN SÂU: CÁC MỤC CÒN LẠI TRONG PAPER
## BẢN DỊCH SÁT NGHĨA, TỔNG QUAN VÀ LUẬN GIẢI TOÀN DIỆN (SECTIONS 3 – 7 & ABSTRACT)

**Tài liệu tham chiếu:** Bài báo khoa học hoàn chỉnh `paper.tex` và bản in xuất bản `paper.pdf` (10 trang chuẩn IEEE)  
**Tiêu đề bài báo:** *Reproducible Hybrid Recommendation for Vietnamese Retail*  
**Giảng viên hướng dẫn:** TS. Nguyễn Thị Xuân Hương  
**Nhóm tác giả sinh viên:** 
- Nguyễn Trương Tiến Phát (MSSV: 23521148)
- Đỗ Minh Đức (MSSV: 23520303)  
**Đơn vị:** Khoa Công nghệ Phần mềm, Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  
**Địa chỉ lưu trữ:** `thesis/paper/methodology-results-conclusion/deep-analysis-methodology-results-conclusion.md`

---

## MỤC LỤC
1. [Tổng quan Điều hành Các Mục Còn lại của Bài báo](#1-tổng-quan-điều-hành-các-mục-còn-lại-của-bài-báo)
2. [Tóm tắt (Abstract) & Từ khóa - Dịch sát nghĩa & Luận giải](#2-tóm-tắt-abstract--từ-khóa---dịch-sát-nghĩa--luận-giải)
3. [Section 3: Phương pháp luận và Giao thức Đánh giá (Methodology & Protocol)](#3-section-3-phương-pháp-luận-và-giao-thức-đánh-giá-methodology--protocol)
   - [Mục 3.1: Thiết kế Nghiên cứu và Đối tượng Ước lượng Toán học (Estimand)](#31-mục-31-thiết-kế-nghiên-cứu-và-đối-tượng-ước-lượng-toán-học-estimand)
   - [Mục 3.2: Lược đồ Dữ liệu và Ranh giới Thời gian UTC (VietRetail-Synth)](#32-mục-32-lược-đồ-dữ-liệu-và-ranh-giới-thời-gian-utc-vietretail-synth)
   - [Mục 3.3: Kiến trúc Mạng Nơ-ron Tháp Đôi Phân rã Wide & Deep](#33-mục-33-kiến-trúc-mạng-nơ-ron-tháp-đôi-phân-rã-wide--deep)
   - [Mục 3.4: Suy luận Thống kê và Phân tích Độ Bất định (Hierarchical Bootstrap)](#34-mục-34-suy-luận-thống-kê-và-phân-tích-độ-bất-định-hierarchical-bootstrap)
4. [Section 4: Thiết kế Thực nghiệm và Phân định Không gian Minh chứng](#4-section-4-thiết-kế-thực-nghiệm-và-phân-định-không-gian-minh-chứng)
5. [Section 5: Kết quả Thực nghiệm và Phân tích Cơ chế (Empirical Results)](#5-section-5-kết-quả-thực-nghiệm-và-phân-tích-cơ-chế-empirical-results)
   - [Mục 5.1: Kết quả Kiểm chứng Quy trình Công khai (MovieLens 100K - Bảng 1)](#51-mục-51-kết-quả-kiểm-chứng-quy-trình-công-khai-movielens-100k---bảng-1)
   - [Mục 5.2: Kết quả Đối chuẩn Bán lẻ Kiểm soát (VietRetail-Synth - Bảng 2)](#52-mục-52-kết-quả-đối-chuẩn-bán-lẻ-kiểm-soát-vietretail-synth---bảng-2)
   - [Mục 5.3: Phân tích Bóc tách Thành phần và Bốn Phát hiện Cơ chế Cốt lõi](#53-mục-53-phân-tích-bóc-tách-thành-phần-và-bốn-phát-hiện-cơ-chế-cốt-lõi)
6. [Section 6: Thảo luận Chuyên sâu và Giới hạn Nghiên cứu (Discussion & Limitations)](#6-section-6-thảo-luận-chuyên-sâu-và-giới-hạn-nghiên-cứu-discussion--limitations)
7. [Section 7: Kết luận, Cam kết Dữ liệu và Đạo đức Khoa học](#7-section-7-kết-luận-cam-kết-dữ-liệu-và-đạo-đức-khoa-học)

---

## 1. TỔNG QUAN ĐIỀU HÀNH CÁC MỤC CÒN LẠI CỦA BÀI BÁO

Nếu như Section 1 (Introduction) và Section 2 (Related Work) thiết lập nền tảng động lực khoa học và vị trí học thuật của bài báo, thì **toàn bộ các mục còn lại (Section 3 đến Section 7)** đại diện cho phần **thực chất, đóng góp kỹ thuật và kết quả đo lường định lượng** của nghiên cứu:

1. **Phương pháp luận Toán học Chặt chẽ (Section 3):** Định nghĩa không gian ứng viên toàn danh mục loại trừ hàng đã mua $C_u = I \setminus H_u^{\mathrm{seen}}$, công thức hóa hàm mất mát Bayesian Personalized Ranking (BPR), giải thuật khai phá luật kết hợp Apriori, và phát kiến **Additive Per-User Z-Score Fusion** nhằm giải quyết sự lệch pha thang đo giữa Deep và Wide.
2. **Liêm chính Thực nghiệm Tuyệt đối (Section 4):** Phân chia hai không gian minh chứng độc lập có khóa mật mã SHA-256 (`PUBLIC_VALIDATION` trên MovieLens 100K và `RETAIL_BENCHMARK` trên VietRetail-Synth).
3. **Bằng chứng Thực nghiệm Vượt bậc (Section 5):** Cung cấp hai bảng số liệu chi tiết. Mô hình đề xuất **Wide-and-Deep Two-Tower Hybrid** vượt trội áp đảo các đường cơ sở: đạt **NDCG@10 = 0.1385** (**+21.28%**), **HR@10 = 0.2190** (**+17.11%**), **Recall@10 = 0.1256** (**+21.47%**) và **Macro GAUC = 0.7812** (**+6.29%**) với độ tin cậy thống kê $p < 0.001$.
4. **Tính Khiêm nhường và Liêm chính Khoa học (Section 6 & 7):** Thẳng thắn chỉ rõ các giới hạn về dữ liệu bán tổng hợp, sản phẩm cold-start tuyệt đối và độ trễ POS tại cửa hàng thực tế.

---

## 2. TÓM TẮT (ABSTRACT) & TỪ KHÓA - DỊCH SÁT NGHĨA & LUẬN GIẢI

### Nguyên văn tiếng Anh (Dòng 38 – 42):
> **Abstract**—Offline recommender system evaluations are notoriously difficult to interpret when algorithmic performance is reported without complete specifications of the underlying data split, candidate generation space, masking rules, loss objectives, and evaluation contracts. This paper introduces a provenance-aware, reproducible protocol for evaluating a decoupled Wide-and-Deep Two-Tower recommender within a controlled Vietnamese retail setting (*VietRetail-Synth*). The protocol strictly enforces a temporal novel-purchase prediction task, full-catalog ranking without negative downsampling ($C_u = I \setminus H_u^{\mathrm{seen}}$), deterministic tie-breaking, per-user paired metrics, and a hierarchical bootstrap uncertainty framework. We isolate public protocol validation from the controlled benchmark evaluation into distinct evidence namespaces to prevent data leakage and cherry-picking. On the public benchmark lane (GroupLens MovieLens 100K via RecBole), the protocol confirms deterministic pipeline execution and checkpoint traceability across multiple random seeds. On the controlled retail benchmark, extensive empirical comparison demonstrates that the proposed Hybrid architecture—fusing an Apriori association rule component with a Deep Two-Tower model optimized via Bayesian Personalized Ranking (BPR)—significantly outperforms baselines, achieving an NDCG@10 of 0.1385 (+21.3% relative gain over single-tower BPR) and an HR@10 of 0.2190. The paper provides an end-to-end, auditable comparison design with verifiable cryptographic artifact bindings, establishing a rigorous benchmark for omnichannel retail recommendation.
> 
> **Keywords:** Recommender systems, reproducibility, full-catalog evaluation, two-tower models, association rules, Bayesian personalized ranking, retail analytics.

### Bản dịch tiếng Việt sát nghĩa:
> **Tóm tắt**—Các đánh giá hệ thống gợi ý ngoại tuyến nổi tiếng là khó diễn giải khi hiệu năng thuật toán được báo cáo mà thiếu vắng các đặc tả đầy đủ về phương thức chia dữ liệu nền tảng, không gian sinh ứng viên, các quy tắc che mặt nạ, các hàm mục tiêu mất mát, và các hợp đồng đánh giá. Bài báo này giới thiệu một giao thức nhận thức nguồn gốc, có khả năng tái lập để đánh giá mô hình gợi ý Tháp Đôi Phân rã Rộng & Sâu (Wide-and-Deep Two-Tower) trong một thiết lập bán lẻ Việt Nam có kiểm soát (*VietRetail-Synth*). Giao thức thực thi nghiêm ngặt tác vụ dự đoán mua sản phẩm mới theo thời gian, xếp hạng trên toàn bộ danh mục không rút gọn mẫu âm ($C_u = I \setminus H_u^{\mathrm{seen}}$), giải quyết điểm hòa tất định, các độ đo ghép cặp trên từng người dùng, và khung phân tích độ bất định bootstrap phân tầng. Chúng tôi cô lập việc xác thực giao thức công khai khỏi việc đánh giá đối chuẩn có kiểm soát thành các không gian minh chứng tách biệt nhằm ngăn chặn rò rỉ dữ liệu và thiên vị chọn lọc (cherry-picking). Trên làn đối chuẩn công khai (GroupLens MovieLens 100K thông qua RecBole), giao thức xác nhận việc thực thi đường ống mang tính tất định và khả năng truy vết checkpoint qua nhiều seed ngẫu nhiên. Trên chuẩn đối sánh bán lẻ có kiểm soát, so sánh thực nghiệm sâu rộng chứng minh rằng kiến trúc Lai đề xuất—kết hợp thành phần luật kết hợp Apriori với mô hình Deep Two-Tower được tối ưu hóa qua Xếp hạng Cá nhân hóa Bayes (BPR)—vượt trội đáng kể so với các đường cơ sở, đạt NDCG@10 là 0.1385 (tăng tương đối +21.3% so với BPR đơn tháp) và HR@10 là 0.2190. Bài báo cung cấp một thiết kế so sánh đầu-cuối, có thể thanh tra với các ràng buộc sản phẩm mật mã học có thể kiểm chứng, thiết lập một chuẩn đối sánh nghiêm ngặt cho bài toán gợi ý bán lẻ đa kênh.
> 
> **Từ khóa:** Hệ gợi ý, tính tái lập, đánh giá toàn danh mục, mô hình tháp đôi, luật kết hợp, xếp hạng cá nhân hóa Bayes, phân tích bán lẻ.

### Luận giải học thuật:
* Tóm tắt đóng vai trò là "bản đồ thu nhỏ" của toàn bài báo: Nêu bật vấn đề (khủng hoảng tính tái lập), giải pháp (giao thức mã băm SHA-256, phân tách không gian minh chứng), mô hình (Wide Apriori + Deep Two-Tower), và con số thực nghiệm định lượng ấn tượng (NDCG@10 đạt 0.1385, +21.3%).

---

## 3. SECTION 3: PHƯƠNG PHÁP LUẬN VÀ GIAO THỨC ĐÁNH GIÁ (METHODOLOGY & PROTOCOL)

### 3.1. Mục 3.1: Thiết kế Nghiên cứu và Đối tượng Ước lượng Toán học (Estimand - Dòng 105 – 118)

#### Nguyên văn tiếng Anh:
> *"The study is designed as a controlled, offline comparative benchmark. The statistical unit of analysis is the per-user metric vector evaluated under fixed seed conditions. For an eligible customer $u \in U$ and a candidate catalog $I$, the candidate set $C_u$ at inference time comprises all items in the global catalog excluding items observed in user $u$'s training history:"*

$$
C_u = I \setminus H_u^{\mathrm{seen}} \qquad (1)
$$

> *"The global item catalog is ordered deterministically by primary product identifier. Candidate scoring produces a descending list, with ascending product ID serving as the deterministic tie-breaking criterion.*
> 
> *The target evaluation event is a novel organic purchase occurring within the designated split window. The top-$K$ rank evaluation sets $K=10$. For a user with true relevant positive items $T_u \subset C_u$, Normalized Discounted Cumulative Gain (NDCG@10) is defined as:"*

$$
\mathrm{NDCG@10}_u = \frac{\mathrm{DCG@10}_u}{\mathrm{IDCG@10}_u} = \frac{\sum_{k=1}^{10} \frac{2^{\mathbb{I}(R_{u,k} \in T_u)} - 1}{\log_2(k + 1)}}{\sum_{k=1}^{\min(|T_u|, 10)} \frac{1}{\log_2(k + 1)}} \qquad (2)
$$

> *"where $R_{u,k}$ denotes the item placed at rank $k$. Hit Rate (HR@10) indicates whether at least one relevant item appears within the top 10 recommendations. Recall@10 measures the fraction of relevant targets successfully retrieved: $\mathrm{Recall@10}_u = \frac{|R_{u, 1:10} \cap T_u|}{|T_u|}$. Macro per-user GAUC computes the Wilcoxon-Mann-Whitney rank statistic between positive targets and all unobserved negative candidates within $C_u$, averaged uniformly across eligible test users."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Nghiên cứu được thiết kế như một chuẩn đối sánh so sánh ngoại tuyến có kiểm soát. Đơn vị phân tích thống kê là vector độ đo trên từng người dùng được đánh giá dưới các điều kiện seed cố định. Đối với một khách hàng đủ điều kiện $u \in U$ và một danh mục ứng viên $I$, tập ứng viên $C_u$ tại thời điểm suy luận bao gồm toàn bộ các sản phẩm trong danh mục toàn cục ngoại trừ các sản phẩm đã được quan sát trong lịch sử huấn luyện của người dùng $u$ theo Phương trình (1):*
> 
> *Danh mục sản phẩm toàn cục được sắp xếp thứ tự một cách tất định theo mã định danh sản phẩm chính. Việc tính điểm ứng viên tạo ra một danh sách giảm dần, với mã ID sản phẩm tăng dần đóng vai trò là tiêu chuẩn giải quyết điểm hòa tất định.*
> 
> *Sự kiện đánh giá mục tiêu là một **giao dịch mua hàng tự nhiên mới** diễn ra trong khung thời gian phân chia được chỉ định. Đánh giá xếp hạng top-$K$ thiết lập $K=10$. Đối với một người dùng có các sản phẩm tích cực thực sự liên quan $T_u \subset C_u$, độ đo Lợi ích Tích lũy Giảm giá Chuẩn hóa (NDCG@10) được định nghĩa theo Phương trình (2).*
> 
> *trong đó $R_{u,k}$ biểu thị sản phẩm được xếp ở vị trí thứ $k$. Tỷ lệ Đánh trúng (HR@10) chỉ ra liệu có ít nhất một sản phẩm liên quan xuất hiện trong top 10 gợi ý hay không. Recall@10 đo lường tỷ lệ các mục tiêu liên quan được truy xuất thành công: $\mathrm{Recall@10}_u = \frac{|R_{u, 1:10} \cap T_u|}{|T_u|}$. Macro per-user GAUC tính toán đại lượng thống kê thứ hạng Wilcoxon-Mann-Whitney giữa các mục tiêu tích cực và toàn bộ các ứng viên âm chưa quan sát trong $C_u$, được lấy trung bình đồng đều trên toàn bộ những người dùng kiểm thử hợp lệ."*

#### Luận giải học thuật và Toán học:
1. **Phương trình (1) — Không gian ứng viên toàn danh mục ($C_u = I \setminus H_u^{\mathrm{seen}}$):**
   - Loại trừ hoàn toàn việc rút gọn mẫu âm (Sampled Metrics). Mỗi người dùng phải cạnh tranh với toàn bộ hơn 5.000 sản phẩm còn lại.
   - Cơ chế che mặt nạ $H_u^{\mathrm{seen}}$ ép buộc hệ thống phải gợi ý các sản phẩm khách hàng **chưa từng mua**, phản ánh bài toán tăng trưởng rổ hàng mới.
2. **Quy tắc Giải quyết Hòa điểm Tất định (Deterministic Tie-breaking):**
   - Khi hai sản phẩm có cùng điểm số dự đoán, hệ thống sắp xếp theo ID sản phẩm tăng dần ($id_a < id_b$). Quy tắc này triệt tiêu hoàn toàn sự ngẫu nhiên của hàm `sort()` trong Python/C++.
3. **Phương trình (2) — Chuẩn hóa DCG@10:**
   - Sử dụng cơ số nhị phân $2^{\mathbb{I}} - 1$ để phạt nặng các vị trí xếp sai ở đầu danh sách.
   - Chia cho IDCG (Ideal DCG) để đưa giá trị về thang đo $[0, 1]$.
4. **Macro per-user GAUC (Group AUC):**
   - Tính diện tích dưới đường cong ROC cho từng người dùng dựa trên thống kê Wilcoxon-Mann-Whitney:

$$
\mathrm{GAUC}_u = \frac{\sum_{i \in T_u} \sum_{j \in C_u \setminus T_u} \mathbb{I}(S(u, i) > S(u, j))}{|T_u| \cdot |C_u \setminus T_u|}
$$

   - Độ đo này không phụ thuộc vào ngưỡng top-10 mà đánh giá khả năng xếp hạng tổng thể trên toàn bộ danh mục ứng viên.

---

### 3.2. Mục 3.2: Lược đồ Dữ liệu và Ranh giới Thời gian UTC (VietRetail-Synth - Dòng 119 – 128)

#### Nguyên văn tiếng Anh:
> *"The benchmark evaluation utilizes the VietRetail-Synth retail dataset. The temporal boundary is partitioned strictly by timestamp in UTC:*
> - **Training Partition ($\mathcal{D}_{\mathrm{train}}$):** 2026-01-01 00:00:00 to 2026-06-19 23:59:59 UTC.
> - **Validation Partition ($\mathcal{D}_{\mathrm{val}}$):** 2026-06-20 00:00:00 to 2026-07-10 23:59:59 UTC.
> - **Test Partition ($\mathcal{D}_{\mathrm{test}}$):** 2026-07-11 00:00:00 to 2026-08-01 23:59:59 UTC.
> 
> *Data integrity is enforced through schema validation, duplicate transaction removal, and cryptographic hash verification across all splits."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Việc đánh giá đối chuẩn sử dụng bộ dữ liệu bán lẻ **VietRetail-Synth**. Ranh giới thời gian được phân chia nghiêm ngặt theo mốc thời gian giờ chuẩn quốc tế UTC:*
> - **Phân vùng Huấn luyện ($\mathcal{D}_{\mathrm{train}}$):** Từ 2026-01-01 00:00:00 đến 2026-06-19 23:59:59 UTC.
> - **Phân vùng Thẩm định ($\mathcal{D}_{\mathrm{val}}$):** Từ 2026-06-20 00:00:00 đến 2026-07-10 23:59:59 UTC.
> - **Phân vùng Kiểm thử ($\mathcal{D}_{\mathrm{test}}$):** Từ 2026-07-11 00:00:00 đến 2026-08-01 23:59:59 UTC.
> 
> *Tính toàn vẹn của dữ liệu được thực thi thông qua việc xác thực lược đồ, loại bỏ giao dịch trùng lặp, và kiểm chứng mã băm mật mã học trên toàn bộ các tập phân chia."*

#### Luận giải học thuật:
* Việc cố định các mốc thời gian đến từng giây theo chuẩn UTC ngăn ngừa tình trạng rò rỉ dữ liệu xuyên múi giờ.
* Tập Huấn luyện dài gần 6 tháng cho phép mô hình nơ-ron học các mẫu hành vi dài hạn và thuật toán Apriori khai phá các luật mua kèm ổn định.
* Tập Thẩm định 20 ngày dùng để tinh chỉnh siêu tham số trọng số $w_{\mathrm{wide}}$, không được đụng vào tập Kiểm thử.

---

### 3.3. Mục 3.3: Kiến trúc Mạng Nơ-ron Tháp Đôi Phân rã Wide & Deep (Dòng 129 – 160)

#### Nguyên văn tiếng Anh:
> *"The proposed architecture decomposes scoring into two specialized components:*
> 
> ***1. Deep Two-Tower Network ($S_{\mathrm{deep}}$):** The User Tower maps customer interaction histories into a normalized embedding vector $\vec{e}_u \in \mathbb{R}^d$:*

$$
\vec{h}_u = \tanh \left( (\vec{u} + \vec{h}_{\mathrm{hist}}) \mathbf{W}_1^{(u)} + \vec{b}_1^{(u)} \right), \quad \vec{e}_u = \frac{\vec{h}_u \mathbf{W}_2^{(u)} + \vec{b}_2^{(u)}}{\|\vec{h}_u \mathbf{W}_2^{(u)} + \vec{b}_2^{(u)}\|_2} \qquad (3)
$$

> *The Item Tower integrates item ID embeddings with dense semantic text projections derived from Vietnamese SBERT and normalized price signals:*

$$
\vec{h}_i = \tanh \left( (\vec{v}_i + \vec{f}_i \mathbf{W}_{\mathrm{proj}}) \mathbf{W}_1^{(i)} + \vec{b}_1^{(i)} \right), \quad \vec{e}_i = \frac{\vec{h}_i \mathbf{W}_2^{(i)} + \vec{b}_2^{(i)}}{\|\vec{h}_i \mathbf{W}_2^{(i)} + \vec{b}_2^{(i)}\|_2} \qquad (4)
$$

> *The matching score represents latent affinity: $S_{\mathrm{deep}}(u, i) = \vec{e}_u \cdot \vec{e}_i$. The network parameters $\Theta$ are optimized via Bayesian Personalized Ranking (BPR) loss:*

$$
\mathcal{L}_{\mathrm{BPR}} = - \sum_{(u, i, j) \in \mathcal{D}_{\mathrm{train}}} \ln \sigma \left( S_{\mathrm{deep}}(u, i) - S_{\mathrm{deep}}(u, j) \right) + \frac{\lambda_{\Theta}}{2} \|\Theta\|_2^2 \qquad (5)
$$

> *where $i$ denotes a purchased item and $j \in I \setminus H_u^{\mathrm{seen}}$ denotes an unobserved candidate.*
> 
> ***2. Wide Apriori Rule Scorer ($S_{\mathrm{wide}}$):** Association rules $X \Rightarrow Y$ are mined exclusively from $\mathcal{D}_{\mathrm{train}}$ transactions using Apriori with minimum support threshold $s_{\min} = 0.001$ and confidence $c_{\min} = 0.05$. For an active cart or recent history $H_u$, the Wide score is computed via confidence aggregation:*

$$
S_{\mathrm{wide}}(u, i) = \max_{X \subseteq H_u, X \Rightarrow \{i\}} \mathrm{Confidence}(X \Rightarrow \{i\}) \qquad (6)
$$

> ***3. Additive Per-User Z-Score Fusion ($S_{\mathrm{hybrid}}$):** Because deep dot products and rule confidences inhabit distinct numerical distributions, raw linear combination induces severe calibration distortion. We apply per-user Z-score normalization across all candidates in $C_u$:*

$$
\mathrm{Norm}(S(u, i)) = \frac{S(u, i) - \mu_u}{\sigma_u + \epsilon} \qquad (7)
$$

> *The final unified ranking score is synthesized additively:*

$$
S_{\mathrm{hybrid}}(u, i) = \mathrm{Norm}(S_{\mathrm{deep}}(u, i)) + w_{\mathrm{wide}} \cdot \mathrm{Norm}(S_{\mathrm{wide}}(u, i)) \qquad (8)
$$

> *where $w_{\mathrm{wide}} \ge 0$ is tuned strictly on $\mathcal{D}_{\mathrm{val}}$."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Kiến trúc đề xuất phân rã việc tính điểm thành hai thành phần chuyên biệt:
> 
> **1. Mạng Tháp Đôi Sâu ($S_{\mathrm{deep}}$):** Tháp Người dùng ánh xạ lịch sử tương tác của khách hàng thành một vector nhúng đã được chuẩn hóa $\vec{e}_u \in \mathbb{R}^d$ theo Phương trình (3).
> 
> Tháp Sản phẩm tích hợp các vector nhúng mã ID sản phẩm với các phép chiếu văn bản ngữ nghĩa dày đặc được trích xuất từ mô hình SBERT tiếng Việt cùng các tín hiệu giá bán đã được chuẩn hóa theo Phương trình (4).
> 
> Điểm số tương khớp đại diện cho mức độ yêu thích tiềm ẩn: $S_{\mathrm{deep}}(u, i) = \vec{e}_u \cdot \vec{e}_i$. Các tham số mạng $\Theta$ được tối ưu hóa thông qua hàm mất mát Xếp hạng Cá nhân hóa Bayes (BPR) theo Phương trình (5), trong đó $i$ biểu thị một sản phẩm đã mua và $j \in I \setminus H_u^{\mathrm{seen}}$ biểu thị một ứng viên chưa từng quan sát.
> 
> **2. Bộ Tính điểm Luật Rộng Apriori ($S_{\mathrm{wide}}$):** Các luật kết hợp $X \Rightarrow Y$ được khai phá độc quyền từ các giao dịch trong $\mathcal{D}_{\mathrm{train}}$ bằng thuật toán Apriori với ngưỡng độ hỗ trợ tối thiểu $s_{\min} = 0.001$ và độ tin cậy $c_{\min} = 0.05$. Đối với một giỏ hàng đang hoạt động hoặc lịch sử gần đây $H_u$, điểm số Wide được tính toán qua phép gom cụm độ tin cậy cực đại theo Phương trình (6).
> 
> **3. Hợp nhất Điểm Chuẩn hóa Z-Score theo từng Người dùng ($S_{\mathrm{hybrid}}$):** Bởi vì tích vô hướng sâu và độ tin cậy của luật kết hợp tồn tại trong các phân phối số học hoàn toàn khác biệt, việc kết hợp tuyến tính thô sơ sẽ gây ra sự biến dạng căn chỉnh nghiêm trọng. Chúng tôi áp dụng chuẩn hóa Z-score trên từng người dùng trên toàn bộ các ứng viên trong $C_u$ theo Phương trình (7). Điểm số xếp hạng hợp nhất cuối cùng được tổng hợp theo phép cộng theo Phương trình (8), trong đó $w_{\mathrm{wide}} \ge 0$ được tinh chỉnh nghiêm ngặt trên $\mathcal{D}_{\mathrm{val}}$."*

#### Luận giải học thuật và Toán học chuyên sâu:
1. **Phương trình (3) & (4) — Chuẩn hóa L2 trên Hình cầu Đơn vị:**
   - Vector nhúng $\vec{e}_u$ và $\vec{e}_i$ đều được chuẩn hóa $L_2$: $\|\vec{e}_u\|_2 = 1, \|\vec{e}_i\|_2 = 1$.
   - Nhờ đó, tích vô hướng $S_{\mathrm{deep}}(u, i) = \vec{e}_u \cdot \vec{e}_i$ chính là **Độ tương đồng Cosine (Cosine Similarity)**, bị chặn chặt trong khoảng $[-1, 1]$.
   - Tích hợp SBERT tiếng Việt vào Tháp Sản phẩm cho phép sản phẩm mới (chưa có tương tác) vẫn có vector $\vec{h}_i$ hợp lệ nhờ nội dung văn bản.
2. **Phương trình (5) — Hàm mất mát BPR:**
   - Cặp tương tác $(u, i, j)$: $i$ là sản phẩm người dùng đã mua, $j$ là sản phẩm người dùng chưa từng mua.
   - Hàm sigmoid $\sigma(x) = \frac{1}{1 + e^{-x}}$ ép điểm số của sản phẩm đã mua $S(u, i)$ phải lớn hơn điểm số của sản phẩm chưa mua $S(u, j)$.
3. **Phương trình (6) — Tính điểm Luật Apriori Cực đại:**
   - Nếu trong giỏ hàng $H_u$ có nhiều tập con kích hoạt nhiều luật khác nhau dẫn đến cùng sản phẩm $i$, hệ thống chọn luật có độ tin cậy (Confidence) cao nhất:

$$
\mathrm{Confidence}(X \Rightarrow \{i\}) = \frac{\mathrm{Support}(X \cup \{i\})}{\mathrm{Support}(X)}
$$

4. **Phương trình (7) & (8) — Đột phá về Hợp nhất Z-Score (Per-User Z-Score Normalization):**
   - *Vấn đề lệch pha thang đo:* Điểm $S_{\mathrm{deep}}$ dao động từ $[-1, 1]$ với trung bình xấp xỉ 0; trong khi điểm luật $S_{\mathrm{wide}}$ có giá trị bằng 0 ở hầu hết các món (do luật không phủ tới) và nhảy vọt lên $0.6 - 0.9$ ở một vài món. Nếu cộng trực tiếp, nhánh Wide sẽ chi phối hoàn toàn hoặc làm mất dấu nhánh Deep.
   - *Giải pháp Z-score per-user:* Chuyển đổi cả hai điểm số về phân phối chuẩn chuẩn tắc có trung bình $\mu_u = 0$ và độ lệch chuẩn $\sigma_u = 1$ trên từng người dùng cụ thể trước khi cộng có trọng số $w_{\mathrm{wide}}$.

---

### 3.4. Mục 3.4: Suy luận Thống kê và Phân tích Độ Bất định (Hierarchical Bootstrap - Dòng 162 – 169)

#### Nguyên văn tiếng Anh:
> *"Model comparisons are evaluated across three predetermined random seeds (42, 2027, 31415). For any model $m$ and baseline $b$, the effect contrast is defined as the paired mean difference across seeds and users:"*

$$
\Delta_{\mathrm{NDCG}} = \frac{1}{|S| \cdot |U_{\mathrm{test}}|} \sum_{s \in S} \sum_{u \in U_{\mathrm{test}}} \left( \mathrm{NDCG@10}_{m,s,u} - \mathrm{NDCG@10}_{b,s,u} \right) \qquad (9)
$$

> *"Statistical confidence is assessed via a two-sided 95% hierarchical paired bootstrap using 2,000 resamples. Resampling occurs over random seed assignments and subsequently over user indices with replacement, preserving within-user correlation."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Các so sánh mô hình được đánh giá trên ba seed ngẫu nhiên được định trước (42, 2027, 31415). Đối với bất kỳ mô hình $m$ và đường cơ sở $b$ nào, độ tương phản hiệu ứng được định nghĩa là sự chênh lệch trung bình ghép cặp qua các seed và các người dùng theo Phương trình (9).*
> 
> *Độ tin cậy thống kê được đánh giá thông qua kiểm định bootstrap phân tầng có ghép cặp hai phía 95% sử dụng 2.000 lần lấy mẫu lại. Việc lấy mẫu lại diễn ra trên các phân bổ seed ngẫu nhiên và sau đó diễn ra trên các chỉ mục người dùng có hoàn lại, bảo toàn tương quan nội tại bên trong từng người dùng."*

#### Luận giải học thuật:
* Tránh kiểm định $t$-test thông thường vì phân phối của NDCG không tuân theo phân phối chuẩn (Non-Gaussian).
* Phương pháp Hierarchical Paired Bootstrap với 2.000 lần lặp đảm bảo rằng sự cải thiện điểm số không phải do may mắn ngẫu nhiên của một seed cụ thể hay một nhóm người dùng cá biệt.

---

## 4. SECTION 4: THIẾT KẾ THỰC NGHIỆM VÀ PHÂN ĐỊNH KHÔNG GIAN MINH CHỨNG (DÒNG 170 – 177)

### Nguyên văn tiếng Anh:
> *"To maintain rigorous scientific boundaries, experimental artifacts are partitioned into two immutable namespaces:*
> 1. **Public Protocol Validation Namespace** (`PUBLIC_VALIDATION`): Establishes pipeline correctness, full-sort ranking execution, and checkpoint determinism on GroupLens MovieLens 100K using the standardized RecBole framework (version 1.2.1) \cite{zhao2021_recbole}.
> 2. **Controlled Retail Benchmark Namespace** (`RETAIL_BENCHMARK`): Executes the full comparative benchmark on the VietRetail-Synth retail dataset under the locked full-catalog protocol ($C_u$)."*

### Bản dịch tiếng Việt sát nghĩa:
> *"Để duy trì các ranh giới khoa học nghiêm ngặt, các sản phẩm thực nghiệm được phân vùng thành hai không gian danh xưng bất biến:*
> 1. **Không gian Danh xưng Xác thực Giao thức Công khai** (`PUBLIC_VALIDATION`): Thiết lập tính đúng đắn của đường ống, việc thực thi xếp hạng sắp xếp đầy đủ, và tính tất định của checkpoint trên bộ dữ liệu GroupLens MovieLens 100K sử dụng khung làm việc RecBole chuẩn hóa (phiên bản 1.2.1) \cite{zhao2021_recbole}.
> 2. **Không gian Danh xưng Chuẩn đối sánh Bán lẻ có Kiểm soát** (`RETAIL_BENCHMARK`): Thực thi toàn bộ chuẩn đối sánh so sánh trên bộ dữ liệu bán lẻ VietRetail-Synth dưới giao thức xếp hạng toàn danh mục đã được khóa chặt ($C_u$)."*

### Luận giải học thuật:
* Nguyên tắc Liêm chính Dữ liệu: Không bao giờ gộp chung kết quả kiểm thử quy trình với kết quả đóng góp của bài báo. Tách biệt rõ ràng để người đọc và ban phản biện thấy được: MovieLens 100K dùng để chứng minh mã nguồn chạy chuẩn xác; còn VietRetail-Synth là nơi kiểm chứng sức mạnh thực sự của mô hình Hybrid đề xuất.

---

## 5. SECTION 5: KẾT QUẢ THỰC NGHIỆM VÀ PHÂN TÍCH CƠ CHẾ (EMPIRICAL RESULTS)

### 5.1. Mục 5.1: Kết quả Kiểm chứng Quy trình Công khai (MovieLens 100K - Bảng 1, Dòng 180 – 202)

#### Bảng 1 và Phân tích:
| Mô hình | Seed | Recall@10 | MRR@10 | NDCG@10 | Hit@10 | Precision@10 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Pop Baseline | 42 | 0.042678 | 0.053217 | 0.031164 | 0.186837 | 0.021444 |
| BPR Reference | 42 | 0.101423 | 0.105435 | 0.070481 | 0.283439 | 0.038535 |
| BPR Reference | 2027 | 0.106237 | 0.113953 | 0.075893 | 0.299363 | 0.041507 |
| BPR Reference | 31415 | 0.109880 | 0.116951 | 0.077937 | 0.301486 | 0.042569 |

* **Nguyên văn nhận xét (Dòng 201):**
  > *"The three stochastic BPR runs demonstrate tight clustering around a mean NDCG@10 of 0.074770 ($\pm 0.003853$), confirming protocol stability prior to retail benchmark deployment."*
* **Bản dịch sát nghĩa:** *"Ba lượt chạy ngẫu nhiên của BPR thể hiện sự gom cụm chặt chẽ xung quanh mức NDCG@10 trung bình là 0.074770 ($\pm 0.003853$), xác nhận tính ổn định của giao thức trước khi triển khai trên chuẩn đối sánh bán lẻ."*

---

### 5.2. Mục 5.2: Kết quả Đối chuẩn Bán lẻ Kiểm soát (VietRetail-Synth - Bảng 2, Dòng 204 – 227)

#### Bảng 2 Đối sánh Chính thức:
| Kiến trúc Mô hình (Model Architecture) | NDCG@10 | HR@10 | Recall@10 | Macro GAUC |
|:---|:---:|:---:|:---:|:---:|
| Popularity Baseline (MostPop) | 0.0421 | 0.0812 | 0.0385 | 0.5412 |
| Rule-Based (Apriori Alone) | 0.0784 | 0.1245 | 0.0692 | 0.6120 |
| Deep Two-Tower (BPR Alone) | 0.1142 | 0.1870 | 0.1034 | 0.7350 |
| **Proposed Hybrid (Wide + Deep Two-Tower)** | **0.1385** | **0.2190** | **0.1256** | **0.7812** |
| *Mức tăng tương đối so với Baseline mạnh nhất* | ***+21.28%*** | ***+17.11%*** | ***+21.47%*** | ***+6.29%*** |

---

### 5.3. Mục 5.3: Phân tích Bóc tách Thành phần và Bốn Phát hiện Cơ chế Cốt lõi (Dòng 228 – 237)

#### Nguyên văn tiếng Anh:
> *"The empirical findings substantiate several core insights regarding retail recommendation:*
> - **Failure of Popularity Heuristics under Novelty Constraints:** MostPop achieves poor effectiveness (NDCG@10 = 0.0421), indicating that when previously purchased staples are masked, recommending generic top-sellers fails to satisfy individualized customer needs.
> - **Narrow Precision of Association Rules:** The standalone Apriori branch achieves respectable precision on frequent itemsets but suffers from low catalog coverage ($< 15\%$), failing on long-tail and cold items.
> - **Generalization Advantage of Deep Representations:** The Deep Two-Tower network substantially outperforms Apriori alone (NDCG@10 = 0.1142 vs. 0.0784), confirming that projecting semantic text and category signals facilitates cross-category discovery.
> - **Synergistic Superiority of the Hybrid Architecture:** The Proposed Hybrid attains the highest effectiveness across all evaluation dimensions. By anchoring deep generalized embeddings with explicit transactional co-purchase rules, the hybrid framework captures immediate basket affinities while maintaining discovery breadth. The hierarchical bootstrap confirms that the performance gain ($\Delta_{\mathrm{NDCG}} = +0.0243$) is statistically significant with $p < 0.001$."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Các phát hiện thực nghiệm minh chứng vững chắc cho một số hiểu biết cốt lõi liên quan đến hệ gợi ý bán lẻ:*
> - **Sự thất bại của Thuật toán Phổ biến dưới Ràng buộc Khám phá mới:** Mô hình MostPop đạt hiệu quả rất kém (NDCG@10 = 0.0421), chỉ ra rằng khi các mặt hàng thiết yếu đã mua trước đó bị che giấu, việc gợi ý các sản phẩm bán chạy chung chung không thể thỏa mãn các nhu cầu cá nhân hóa của khách hàng.
> - **Độ chính xác Hẹp của Luật Kết hợp:** Nhánh Apriori đơn lẻ đạt độ chính xác đáng nể trên các tập sản phẩm thường xuyên nhưng chịu thiệt thòi bởi độ phủ danh mục thấp ($< 15\%$), thất bại hoàn toàn trên các sản phẩm đuôi dài (long-tail) và sản phẩm mới (cold items).
> - **Lợi thế Khái quát hóa của Biểu diễn Sâu:** Mạng Deep Two-Tower vượt trội đáng kể so với việc chỉ dùng Apriori đơn lẻ (NDCG@10 = 0.1142 so với 0.0784), xác nhận rằng việc chiếu văn bản ngữ nghĩa và các tín hiệu danh mục tạo điều kiện thuận lợi cho việc khám phá sản phẩm xuyên danh mục.
> - **Sự Vượt trội Mang tính Cộng hưởng của Kiến trúc Lai:** Mô hình Lai Đề xuất đạt hiệu quả cao nhất trên mọi chiều kích đánh giá. Bằng cách neo giữ các vector nhúng sâu có tính khái quát hóa cùng các luật mua kèm giao dịch tường minh, khung làm việc lai vừa nắm bắt được các mối liên kết giỏ hàng tức thời vừa duy trì được độ rộng của việc khám phá. Kiểm định bootstrap phân tầng xác nhận rằng mức tăng hiệu năng ($\Delta_{\mathrm{NDCG}} = +0.0243$) có ý nghĩa thống kê với $p < 0.001$."*

#### Luận giải học thuật và Ý nghĩa Thực tiễn:
1. **Tại sao MostPop sụp đổ (NDCG = 0.0421):**
   Trong bán lẻ, người dùng thường mua lại các món đồ quen thuộc. Khi ép bài toán sang *Novel-purchase*, các món top-seller chung chung (như mì tôm, nước suối) bị che giấu hoặc không còn phù hợp với từng cá nhân. Gợi ý phổ biến hoàn toàn bất lực.
2. **Tại sao Apriori bị nghẽn độ phủ (< 15%):**
   Luật kết hợp đòi hỏi phải đạt ngưỡng Support và Confidence. Với hàng nghìn mặt hàng đuôi dài (ít người mua), không có đủ giao dịch để sinh luật. Apriori đạt điểm tốt khi trúng tủ, nhưng hầu hết các trường hợp khác điểm trả về bằng 0.
3. **Tại sao Two-Tower BPR đạt điểm cao (NDCG = 0.1142):**
   Nhờ có vector nhúng ngữ nghĩa văn bản từ SBERT tiếng Việt, ngay cả khi sản phẩm chưa có nhiều giao dịch, mô hình vẫn biết nó thuộc nhóm tương đồng nào để xếp hạng.
4. **Tại sao mô hình Lai lại bứt phá đỉnh cao (+21.28%):**
   Sự kết hợp giữa Memorization (Apriori bắt trọn các giỏ hàng mua kèm chuẩn xác tại quầy) và Generalization (Two-Tower bao quát toàn bộ danh mục 5.200 món) bổ sung hoàn hảo cho nhau, tạo ra bước nhảy vọt hiệu năng đã được kiểm chứng thống kê $p < 0.001$.

---

## 6. SECTION 6: THẢO LUẬN CHUYÊN SÂU VÀ GIỚI HẠN NGHIÊN CỨU (DISCUSSION & LIMITATIONS - DÒNG 238 – 248)

### Nguyên văn tiếng Anh:
> *"The empirical evidence affirms that enforcing protocol immutability—spanning temporal partitioning, full-catalog negative universes, and independent metric evaluation—is indispensable for establishing trustworthy recommender comparisons. 
> 
> Nevertheless, several methodological limitations must be acknowledged:*
> 1. **Semi-Synthetic Data Characteristics:** While VietRetail-Synth faithfully captures catalog topologies and basket co-occurrences, generated consumer trajectories cannot fully substitute for observational field logs subject to organic macroeconomic fluctuations.
> 2. **Strict Zero-Edge Cold Items:** While content projection mitigates item cold-start, zero-edge items remain inherently challenging due to the absence of collaborative gradient updates during training.
> 3. **Offline vs. Online Latency Trade-Offs:** The evaluation protocol focuses strictly on ranking accuracy. Real-world retail deployment must additionally navigate distributed inference latency budgets ($\le 50\mathrm{ms}$) across store POS terminals."*

### Bản dịch tiếng Việt sát nghĩa:
> *"Bằng chứng thực nghiệm khẳng định rằng việc thực thi tính bất biến của giao thức—bao gồm phân chia thời gian, các vũ trụ âm toàn danh mục, và đánh giá độ đo độc lập—là không thể thiếu để thiết lập các so sánh hệ gợi ý đáng tin cậy.
> 
> Tuy nhiên, một số giới hạn về mặt phương pháp luận cần phải được thừa nhận một cách thẳng thắn:*
> 1. **Đặc tính Dữ liệu Bán tổng hợp:** Mặc dù VietRetail-Synth nắm bắt một cách trung thực cấu trúc liên kết danh mục và sự đồng xuất hiện giỏ hàng, các quỹ đạo tiêu dùng được sinh ra không thể thay thế hoàn toàn cho các nhật ký thực địa quan sát được vốn chịu ảnh hưởng bởi các biến động kinh tế vĩ mô tự nhiên.
> 2. **Sản phẩm Cold-start Tuyệt đối Không có Cạnh nối:** Mặc dù việc chiếu đặc trưng nội dung giúp giảm nhẹ bài toán khởi đầu lạnh sản phẩm, các sản phẩm không có cạnh nối vốn dĩ vẫn là một thách thức cố hữu do sự vắng mặt của các cập nhật gradient lọc cộng tác trong quá trình huấn luyện.
> 3. **Sự Đánh đổi giữa Độ trễ Ngoại tuyến và Trực tuyến:** Giao thức đánh giá tập trung nghiêm ngặt vào độ chính xác xếp hạng. Việc triển khai bán lẻ trong thế giới thực đòi hỏi phải xử lý thêm ngân sách độ trễ suy luận phân tán ($\le 50\mathrm{ms}$) trên các thiết bị đầu cuối máy POS tại cửa hàng."*

### Luận giải học thuật:
* Thể hiện tinh thần khiêm nhường và liêm chính khoa học của tác giả. Việc chủ động nêu rõ 3 giới hạn này bảo vệ bài báo trước các chất vấn gay gắt của hội đồng phản biện quốc tế.

---

## 7. SECTION 7: KẾT LUẬN, CAM KẾT DỮ LIỆU VÀ ĐẠO ĐỨC KHOA HỌC (DÒNG 249 – 265)

### Nguyên văn tiếng Anh:
> *"This paper has presented a reproducible, provenance-aware benchmark protocol for omnichannel retail recommendation. By enforcing full-catalog ranking ($C_u = I \setminus H_u^{\mathrm{seen}}$), global temporal splitting, and decoupled evaluation, the framework establishes a verifiable foundation for algorithmic comparison. Empirical evaluations on the VietRetail-Synth benchmark demonstrate that the decoupled Wide-and-Deep Two-Tower Hybrid achieves a 21.3% relative gain in NDCG@10 over single-paradigm neural baselines. Future work will investigate online multi-armed bandit dispatchers for dynamic Wide-Deep weight adaptation in live store environments.*
> 
> ### Data and Artifact Availability
> *All protocol configurations, synthetic catalog schemas, and evaluation artifacts are version-controlled and verifiable via cryptographic SHA-256 digests in the study repository.*
> 
> ### Ethical Statement
> *This investigation utilizes secondary public benchmarks and synthetic retail data; no human subjects were surveyed, and no personally identifiable customer records were processed.*
> 
> ### Acknowledgments
> *This research was supported by the Faculty of Software Engineering, University of Information Technology, Vietnam National University, Ho Chi Minh City."*

### Bản dịch tiếng Việt sát nghĩa:
> *"Bài báo này đã trình bày một giao thức chuẩn đối sánh có khả năng tái lập, nhận thức nguồn gốc cho hệ gợi ý bán lẻ đa kênh. Bằng cách thực thi việc xếp hạng trên toàn bộ danh mục ($C_u = I \setminus H_u^{\mathrm{seen}}$), phân chia thời gian toàn cục, và đánh giá được phân rã độc lập, khung làm việc thiết lập một nền tảng có thể kiểm chứng cho việc so sánh thuật toán. Các đánh giá thực nghiệm trên chuẩn đối sánh VietRetail-Synth chứng minh rằng mô hình Lai Wide-and-Deep Two-Tower phân rã đạt mức tăng tương đối 21.3% về NDCG@10 so với các đường cơ sở nơ-ron đơn hình thái. Công trình tương lai sẽ điều tra các bộ điều phối multi-armed bandit trực tuyến để thích ứng trọng số Wide-Deep một cách động trong môi trường cửa hàng trực tiếp.*
> 
> ### Tính Khả dụng của Dữ liệu và Sản phẩm Nghiên cứu
> *Toàn bộ các cấu hình giao thức, lược đồ danh mục tổng hợp, và các sản phẩm đánh giá đều được kiểm soát phiên bản và có thể kiểm chứng qua các mã băm mật mã học SHA-256 trong kho lưu trữ của nghiên cứu.*
> 
> ### Tuyên bố về Đạo đức Khoa học
> *Cuộc điều tra này sử dụng các chuẩn đối sánh công khai thứ cấp và dữ liệu bán lẻ tổng hợp; không có đối tượng con người nào bị khảo sát, và không có hồ sơ thông tin định danh cá nhân của khách hàng nào bị xử lý.*
> 
> ### Lời Cảm ơn
> *Nghiên cứu này được tài trợ bởi Khoa Công nghệ Phần mềm, Trường Đại học Công nghệ Thông tin, Đại học Quốc gia Thành phố Hồ Chí Minh."*

### Luận giải học thuật:
* Tuyên bố rõ ràng về hướng đi tương lai (Multi-armed bandit trực tuyến để điều chỉnh $w_{\mathrm{wide}}$ theo thời gian thực tại quầy thu ngân).
* Đầy đủ các tuyên bố bắt buộc của các hội nghị hàng đầu thế giới (Data Availability, Ethical Statement, Acknowledgments dành cho Khoa CNPM và Trường ĐH Công nghệ Thông tin, ĐHQG-HCM).
