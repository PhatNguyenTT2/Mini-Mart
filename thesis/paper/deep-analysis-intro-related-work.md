# GIẢI NGHĨA VÀ PHÂN TÍCH HỌC THUẬT CHUYÊN SÂU
## PHẦN MỞ ĐẦU (INTRODUCTION) VÀ CÁC CÔNG TRÌNH LIÊN QUAN (RELATED WORK)
**Tài liệu tham chiếu:** Bài báo khoa học hoàn chỉnh `paper.tex` và bản dựng xuất bản `paper.pdf` (10 trang chuẩn IEEE)  
**Tiêu đề bài báo:** *Reproducible Hybrid Recommendation for Vietnamese Retail*  
**Giảng viên hướng dẫn:** TS. Nguyễn Thị Xuân Hương  
**Nhóm tác giả sinh viên:** 
- Nguyễn Trương Tiến Phát (MSSV: 23521148)
- Đỗ Minh Đức (MSSV: 23520303)  
**Đơn vị:** Khoa Công nghệ Phần mềm, Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  
**Mục tiêu tài liệu:** Bóc tách chi tiết từng đoạn văn, từng câu chữ, thuật ngữ chuyên ngành, cơ sở lý thuyết, 36 trích dẫn học thuật, và luận điểm bảo vệ tính liêm chính khoa học của bài báo hiện tại.

---

## MỤC LỤC
1. [Triết lý khoa học và Khung phương pháp luận của bài báo](#1-triết-lý-khoa-học-và-khung-phương-pháp-luận-của-bài-báo)
2. [Phân tích chi tiết Section 1: Introduction](#2-phân-tích-chi-tiết-section-1-introduction)
   - [Đoạn 1: Định nghĩa bài toán và Phân tách Sinh ứng viên vs Xếp hạng](#21-đoạn-1-định-nghĩa-bài-toán-và-phân-tách-sinh-ứng-viên-vs-xếp-hạng-dòng-46--47)
   - [Đoạn 2: Thiết lập Chuẩn đối sánh Bán lẻ VietRetail-Synth](#22-đoạn-2-thiết-lập-chuẩn-đối-sánh-bán-lẻ-vietretail-synth-dòng-48--49)
   - [Mục 1.1: Tại sao Tính khả so sánh là một Bài toán Nghiên cứu](#23-mục-11-tại-sao-tính-khả-so-sánh-là-một-bài-toán-nghiên-cứu-dòng-50--55)
   - [Mục 1.2: Các Tín hiệu Khác biệt và Giả thuyết Bổ trợ về Mô hình Lai](#24-mục-12-các-tín-hiệu-khác-biệt-và-giả-thuyết-bổ-trợ-về-mô-hình-lai-dòng-56--61)
   - [Mục 1.3: Câu hỏi Nghiên cứu và Các Đóng góp Khoa học Lớn](#25-mục-13-câu-hỏi-nghiên-cứu-và-các-đóng-góp-khoa-học-lớn-dòng-62--75)
3. [Phân tích chi tiết Section 2: Related Work](#3-phân-tích-chi-tiết-section-2-related-work)
   - [Mục 2.1: Đánh giá và Tính tái lập (Evaluation and Reproducibility)](#31-mục-21-đánh-giá-và-tính-tái-lập-evaluation-and-reproducibility-dòng-79--82)
   - [Mục 2.2: Lọc cộng tác, Mạng nơ-ron và Gợi ý tuần tự](#32-mục-22-lọc-cộng-tác-mạng-nơ-ron-và-gợi-ý-tuần-tự-dòng-83--86)
   - [Mục 2.3: Wide & Deep, Two-Tower và Biểu diễn Ngữ nghĩa](#33-mục-23-wide--deep-two-tower-và-biểu-diễn-ngữ-nghĩa-dòng-87--90)
   - [Mục 2.4: Apriori, Luật kết hợp và Gợi ý Giỏ hàng kế tiếp](#34-mục-24-apriori-luật-kết-hợp-và-gợi-ý-giỏ-hàng-kế-tiếp-dòng-91--94)
   - [Mục 2.5: Gợi ý dựa trên Đồ thị và Học tương phản](#35-mục-25-gợi-ý-dựa-trên-đồ-thị-và-học-tương-phản-dòng-95--98)
   - [Mục 2.6: Nội dung, Sản phẩm Cold-start và Học chuyển giao](#36-mục-26-nội-dung-sản-phẩm-cold-start-và-học-chuyển-giao-dòng-99--102)
4. [Bảng đối sánh Toàn diện 36 Trích dẫn Học thuật (Citation Registry)](#4-bảng-đối-sánh-toàn-diện-36-trích-dẫn-học-thuật-citation-registry)
5. [Từ điển Thuật ngữ Đối chiếu Anh - Việt (Academic Glossary)](#5-từ-điển-thuật-ngữ-đối-chiếu-anh---việt-academic-glossary)

---

## 1. TRIẾT LÝ KHOA HỌC VÀ KHUNG PHƯƠNG PHÁP LUẬN CỦA BÀI BÁO

Khác với các bài báo công nghệ thông thường vốn chỉ tập trung "quảng bá" một mô hình mới và công bố điểm số vượt trội hơn các mô hình cũ (thường dựa trên việc tối ưu hóa có chủ đích các siêu tham số hoặc tinh chỉnh tập kiểm thử thuận lợi), bài báo `paper.tex` tiếp cận theo trường phái **Khắc kỷ học thuật và Liêm chính khoa học (Epistemological Rigor & Reproducibility First)**:

1. **Tính bất định của số đo ngoại tuyến (Offline Metric Brittleness):** Một con số NDCG hay Hit Ratio cao hơn 2% không có ý nghĩa khoa học nếu không đi kèm với định nghĩa chính xác về: tập dữ liệu, phương thức chia thời gian (Temporal Split), không gian ứng viên (Full-catalog vs Sampled), cơ chế che dấu lịch sử (Masking), và bộ tính toán độc lập (Independent Evaluator).
2. **Tách biệt Không gian Minh chứng (Evidence Namespaces):** Bài báo tách bạch rõ ràng giữa:
   - *Public Data Protocol Validation (`PUBLIC_VALIDATION`):* Kiểm tra luồng thực thi trên dữ liệu chuẩn quốc tế (MovieLens 100K với RecBole 1.2.1) qua 3 seed ngẫu nhiên.
   - *Controlled Retail Benchmark (`RETAIL_BENCHMARK`):* Đánh giá trên tập dữ liệu bán lẻ được kiểm soát đóng băng mã băm SHA-256 (`VietRetail-Synth`).
   - Tuyệt đối không lấy kết quả của không gian này để bù trừ hoặc đại diện cho không gian khác.
3. **Đóng góp về Phương pháp luận và Thực nghiệm Hoàn chỉnh:** Bài báo không chỉ đóng góp thiết kế so sánh có khả năng tái lập và ranh giới minh chứng rõ ràng, mà còn chứng minh mô hình **Wide-and-Deep Two-Tower Hybrid** vượt trội có ý nghĩa thống kê ($p < 0.001$) trên toàn bộ danh mục bán lẻ.

---

## 2. PHÂN TÍCH CHI TIẾT SECTION 1: INTRODUCTION

### 2.1. Đoạn 1: Định nghĩa bài toán và Phân tách Sinh ứng viên vs Xếp hạng (Dòng 46 – 47)

#### Câu 1:
> *"Retail recommendation is frequently characterized as a model-selection problem, but an offline empirical result is first and foremost a statement about a defined ranking task."*

* **Dịch nghĩa:** Hệ thống gợi ý bán lẻ thường được mô tả như một bài toán lựa chọn mô hình, nhưng một kết quả thực nghiệm ngoại tuyến trước hết và trên hết là một phát biểu về một tác vụ xếp hạng được định nghĩa cụ thể.
* **Thuật ngữ trọng tâm:**
  * `model-selection problem`: Bài toán chọn mô hình (chọn xem ResNet, Transformer, Two-Tower hay LightGCN tốt hơn).
  * `offline empirical result`: Kết quả thực nghiệm ngoại tuyến (dựa trên dữ liệu thu thập quá khứ, không phải A/B testing trực tiếp trên người dùng thật).
  * `defined ranking task`: Tác vụ xếp hạng được định nghĩa rõ ràng về toán học và ngữ cảnh dữ liệu.
* **Phân tích chiều sâu:** Tác giả mở đầu bằng việc đảo ngược lối tư duy truyền thống: Trong giới học thuật RecSys, các nhà nghiên cứu thường lầm tưởng rằng "Mô hình A tốt hơn Mô hình B". Tác giả chỉ ra rằng kết quả đo lường không phản ánh bản chất tuyệt đối của mô hình, mà nó phản ánh sự tương thích giữa mô hình đó với một bài toán xếp hạng cụ thể mà người làm thực nghiệm đã đặt ra.

#### Câu 2:
> *"A recommendation engine must determine which portion of user history is legitimately accessible, which items are eligible candidates, what specific user action constitutes a positive future event, and how numerical scores are translated into an ordered presentation list."*

* **Dịch nghĩa:** Một hệ gợi ý phải xác định phần lịch sử nào của người dùng là được phép truy cập một cách hợp lệ, những sản phẩm nào là ứng viên đủ điều kiện, hành động cụ thể nào của người dùng cấu thành nên một sự kiện tích cực trong tương lai, và cách thức các điểm số định lượng được chuyển dịch thành một danh sách trình bày có thứ tự.
* **Phân tích chiều sâu:** Đây là 4 biến số cốt tử quyết định tính hợp lệ của bài toán xếp hạng:
  1. `user history legitimately accessible`: Lịch sử quan sát được (phải cắt trước thời điểm dự báo để tránh rò rỉ dữ liệu tương lai).
  2. `eligible candidates`: Tập sản phẩm ứng viên (ví dụ: còn hàng trong kho chi nhánh, hay toàn bộ danh mục sản phẩm).
  3. `positive future event`: Định nghĩa nhãn tích cực (mua hàng, click, hay thêm vào giỏ).
  4. `numerical scores translated into ordered list`: Quy tắc sắp xếp điểm (và cơ chế giải quyết điểm hòa - deterministic tie-breaking).

#### Câu 3 – 4:
> *"In modern production systems, candidate generation (retrieval) and precision ranking serve distinct operational roles rather than interchangeable names for a single predictor \cite{covington2016_youtube, yi2019_ndr}. This architectural distinction is particularly crucial in retail settings characterized by sparse user--item interaction matrices, rapidly shifting purchase sequences, rich multi-modal product metadata, and newly introduced products with sparse or non-existent interaction histories."*

* **Dịch nghĩa:** Trong các hệ thống vận hành thực tế hiện đại, việc sinh ứng viên (truy xuất) và xếp hạng chính xác đảm nhiệm các vai trò vận hành tách biệt, chứ không phải là những tên gọi có thể hoán đổi cho một bộ dự đoán duy nhất \cite{covington2016_youtube, yi2019_ndr}. Sự phân biệt kiến trúc này đặc biệt quan trọng trong các bối cảnh bán lẻ có ma trận tương tác người dùng - sản phẩm thưa thớt, chuỗi mua sắm biến đổi nhanh chóng, siêu dữ liệu sản phẩm đa phương thức phong phú, và các sản phẩm mới ra mắt với lịch sử tương tác thưa thớt hoặc hoàn toàn bằng không.
* **Trích dẫn và Cơ sở khoa học:**
  * Trích dẫn 1: **Covington, Adams, & Sargin (2016)**, *"Deep Neural Networks for YouTube Recommendations"*, ACM RecSys 2016.
    * *Vị trí neo (Anchor):* Sections 2 System Overview, 3 Candidate Generation, và 4 Ranking.
    * *Cơ sở:* Đặt nền móng cho kiến trúc 2 tầng công nghiệp: Tầng 1 (Candidate Generation) lọc hàng triệu video xuống vài trăm bằng mạng nơ-ron tháp đôi với Softmax xấp xỉ; Tầng 2 (Ranking) dùng mạng sâu với hàng trăm đặc trưng tinh vi để xếp hạng top vài chục.
  * Trích dẫn 2: **Yi et al. (2019)**, *"Sampling-bias-corrected neural modeling for large corpus string recommendations"*, ACM RecSys 2019.
    * *Vị trí neo (Anchor):* Sections 2.3 Two-tower Models, 3 Modeling Framework, và 5 Neural Retrieval System.
    * *Cơ sở:* Google đề xuất mô hình Two-Tower mở rộng với cơ chế hiệu chỉnh độ lệch chọn mẫu (Streaming frequency estimation) cho tầng truy xuất quy mô lớn.
* **Luận điểm bảo vệ:** Không thể đánh đồng một thuật toán sinh ứng viên (như Two-Tower với In-batch Negative) với một thuật toán xếp hạng chi tiết. Trong bán lẻ, tính chất thưa thớt (sparsity) và sản phẩm mới (cold items) đòi hỏi mỗi tầng phải có vai trò và giả định dữ liệu rõ ràng.

#### Câu 5:
> *"The same nominal algorithm can yield vastly divergent estimands when the candidate space or the target definition is altered."*

* **Dịch nghĩa:** Cùng một thuật toán trên danh nghĩa có thể mang lại các đối tượng ước lượng (estimands) hoàn toàn phân kỳ khi không gian ứng viên hoặc định nghĩa mục tiêu bị thay đổi.
* **Thuật ngữ:** `estimand` (khái niệm thống kê học: đại lượng hoặc phân phối xác suất cần được ước lượng trong tổng thể). Nếu tập ứng viên đổi từ 100 sản phẩm ngẫu nhiên sang 5.200 sản phẩm toàn danh mục, estimand đã thay đổi hoàn toàn bản chất.

---

### 2.2. Đoạn 2: Thiết lập Chuẩn đối sánh Bán lẻ VietRetail-Synth (Dòng 48 – 49)

#### Nguyên văn và Phân tích:
> *"The present study addresses this challenge within a controlled Vietnamese retail benchmark setting, designated as \textbf{VietRetail-Synth}. The benchmark is engineered to mirror the operational data structures of chain-level retail stores, encompassing longitudinal customer purchasing records, catalog taxonomy, dynamic pricing signals, and basket checkout events. Its interaction patterns are controlled and semi-synthetic, designed deliberately to expose specific algorithmic mechanisms—such as rule-aligned co-purchase patterns and item-side semantic features—while maintaining full mathematical traceability. The declared benchmark manifest comprises 5,000 customers, 5,200 unique SKUs, 823,371 interaction events, and an isolated strict item-cold subset."*

* **Dịch nghĩa:** Nghiên cứu hiện tại giải quyết thách thức này trong một thiết lập chuẩn đối sánh bán lẻ Việt Nam được kiểm soát, mang định danh chính thức là **VietRetail-Synth**. Chuẩn đối sánh này được thiết kế kỹ thuật để phản ánh cấu trúc dữ liệu vận hành của các chuỗi cửa hàng bán lẻ, bao gồm hồ sơ mua sắm dài hạn của khách hàng, phân loại danh mục, tín hiệu giá động, và các sự kiện thanh toán giỏ hàng. Các hình mẫu tương tác của nó được kiểm soát và mang tính bán tổng hợp, được thiết kế có chủ đích nhằm bóc tách các cơ chế giải thuật cụ thể—chẳng hạn như các mẫu mua kèm phù hợp với luật kết hợp và các đặc trưng ngữ nghĩa phía sản phẩm—trong khi vẫn duy trì khả năng truy xuất nguồn gốc toán học đầy đủ. Bản tuyên bố chuẩn đối sánh chỉ định 5.000 khách hàng, 5.200 SKU sản phẩm duy nhất, 823.371 sự kiện tương tác và một tập con sản phẩm cold-start nghiêm ngặt được cô lập riêng biệt.
* **Luận điểm liêm chính khoa học:** 
  1. Bài báo **thành thật tuyên bố** dữ liệu là bán tổng hợp (semi-synthetic) có kiểm soát chứ không ngụy tạo là "dữ liệu thực tế của hàng triệu người tiêu dùng Việt Nam". Tính trung thực này bảo vệ bài báo trước các chất vấn về tính đại diện thống kê.
  2. Việc định danh chính thức là `VietRetail-Synth` thay vì các mã phiên bản nội bộ như "v5" giúp công trình đạt chuẩn mực bài báo nghiên cứu độc lập, có thể công bố công khai cho cộng đồng nghiên cứu quốc tế.

---

### 2.3. Mục 1.1: Tại sao Tính khả so sánh là một Bài toán Nghiên cứu (Dòng 50 – 55)

#### Câu 1 – 3:
> *"Comparative conclusions in offline recommender literature are acutely sensitive to design choices that are frequently dismissed as mere implementation details. For instance, data partitioning policy directly dictates the information horizon available at inference time. Recent empirical investigations into data-splitting strategies reveal that sequential recommender performance fluctuates substantially depending on whether random, user-level, or global temporal splits are adopted \cite{gusak2025_time_split}. Concurrently, systematic replicability studies on deep architectures such as BERT4Rec demonstrate that subtle training configurations and negative-sampling schemes fundamentally alter published outcomes \cite{petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo}."*

* **Trích dẫn và Cơ sở học thuật:**
  * Trích dẫn 3: **Gusak, Volodkevich, Klenitskiy, Vasilev, & Frolov (2025)**, *"Time to Split: Exploring Data Splitting Strategies for Offline Evaluation of Sequential Recommenders"*, ACM RecSys 2025.
    * *Vị trí neo:* Figure 1; Sections 1–3; global temporal split và results subsections.
    * *Ý nghĩa:* Chứng minh rằng các chiến lược chia dữ liệu khác nhau (Random split, User-level temporal split, Global temporal split) làm thay đổi hoàn toàn thứ hạng của các mô hình gợi ý tuần tự. Việc chia ngẫu nhiên gây rò rỉ dữ liệu tương lai nghiêm trọng.
  * Trích dẫn 4: **Petrov & Macdonald (2022)**, *"A systematic review and replicability study of BERT4Rec for sequential recommendation"*, ACM RecSys 2022.
    * *Vị trí neo:* Implementation review and RQ2 training-time analysis, including Table 4.
    * *Ý nghĩa:* Phân tích tính tái lập của mô hình kinh điển BERT4Rec, chỉ ra rằng các chi tiết cài đặt như negative sampling, độ dài chuỗi, điểm cắt tỉa (cutoff) và tie-breaking có thể làm thay đổi kết quả công bố tới hàng chục phần trăm.
* **Luận điểm cốt lõi:** Các thông số kỹ thuật (như cách chia thời gian, cách xử lý hòa điểm, cách lấy mẫu âm) không phải là "chi tiết lặt vặt" (implementation details) mà chính là **yếu tố cấu thành nên đại lượng khoa học được đo lường**.

#### Giải pháp của Bài báo (Dòng 53 – 55):
> *"This paper addresses this vulnerability by treating the evaluation protocol as a first-class, immutable scientific artifact. The protocol locks a global temporal split, full-catalog candidate evaluation, strict seen-item masking, deterministic identifier-based tie-breaking, and independent metric evaluation. Every candidate model exports raw predicted scores into a decoupled, shared evaluator. The evaluator—completely isolated from model training code—applies the masking operators, executes full ranking, and computes per-user metrics..."*

* **Dịch nghĩa:** Bài báo giải quyết lỗ hổng này bằng cách coi giao thức đánh giá như một sản phẩm khoa học bất biến hạng nhất. Giao thức khóa chặt phân tách thời gian toàn cục, đánh giá ứng viên toàn danh mục, che mặt nạ nghiêm ngặt sản phẩm đã thấy, giải quyết hòa điểm tất định dựa trên mã định danh, và đánh giá độ đo độc lập. Mọi mô hình ứng viên xuất điểm dự đoán thô sang một bộ đánh giá dùng chung tách biệt. Chính bộ đánh giá—hoàn toàn cô lập khỏi mã huấn luyện mô hình—sẽ áp dụng các toán tử che mặt nạ, thực thi xếp hạng đầy đủ và tính toán các độ đo trên từng người dùng.
* **Nguyên tắc phân quyền:** Tránh hiện tượng "vừa đá bóng vừa thổi còi" (mô hình tự tính điểm và tự báo cáo số liệu).

---

### 2.4. Mục 1.2: Các Tín hiệu Khác biệt và Giả thuyết Bổ trợ về Mô hình Lai (Dòng 56 – 61)

#### Phân tích giả thuyết bổ trợ (Complementarity Hypothesis):
> *"The proposed model architecture integrates an association rule-derived Wide component with a content-augmented Deep Two-Tower neural network. The underlying rationale rests upon a \textit{complementarity hypothesis}: an association rule branch captures explicit, high-frequency co-purchase regularities observed within customer checkout baskets (memorization), whereas a deep representation branch generalises across semantic feature spaces to identify relevant items that lack direct co-purchase history (generalization)."*

* **Giải nghĩa logic kết hợp:**
  * **Nhánh Wide (Luật kết hợp Apriori):** Ghi nhớ chuẩn xác các cặp sản phẩm thường xuyên mua kèm tự nhiên tại quầy thu ngân (Memorization).
  * **Nhánh Deep (Mạng Two-Tower tích hợp ngữ nghĩa Content):** Khái quát hóa và dự đoán sở thích trên các không gian đặc trưng ngữ nghĩa đối với các sản phẩm chưa từng xuất hiện cùng nhau hoặc sản phẩm mới (Generalization).

#### Đối sánh với các công trình kinh điển (Dòng 60):
* Trích dẫn 5: **Cheng et al. (2016)** - Google Wide & Deep: Khác biệt ở chỗ bài báo này dùng **Luật kết hợp Apriori (Association Rules)** cho nhánh Wide thay vì dùng tích chéo tuyến tính (linear cross-product) trên đặc trưng liên tục được phân thùng.
* Trích dẫn 6: **Sarwar et al. (2001)** - Item-based Collaborative Filtering: ItemCF tính độ tương đồng cosine/pearson giữa các vector tương tác trong quá khứ, khác với luật kết hợp tính xác suất có điều kiện (Confidence/Support).
* Trích dẫn 7: **Rendle et al. (2009)** - Bayesian Personalized Ranking (BPR): Tối ưu hóa thứ hạng theo cặp trên phản hồi ngầm, là hàm mục tiêu của nhánh Deep Two-Tower.

#### Cơ sở của Luật kết hợp và Gợi ý giỏ hàng (Dòng 60):
* Trích dẫn 8: **Agrawal & Srikant (1994)** - Khởi thủy của giải thuật Apriori và khai phá luật kết hợp trên cơ sở dữ liệu giao dịch lớn.
* Trích dẫn 9: **Ghoshal & Sarkar (2014)** - Ứng dụng luật kết hợp đa sản phẩm vào hệ gợi ý bán lẻ.
* Trích dẫn 10: **Liu et al. (2009)** - Mô hình lai kết hợp chuỗi hành vi và lọc cộng tác.
* Trích dẫn 11 & 12: **Peng et al. (2022, 2023)** - Mô hình HAM và M2: Kết hợp sở thích dài hạn và tín hiệu liên kết giỏ hàng trong gợi ý giỏ hàng tiếp theo (Next-Basket Recommendation).

---

### 2.5. Mục 1.3: Câu hỏi Nghiên cứu và Các Đóng góp Khoa học Lớn (Dòng 62 – 75)

#### Câu hỏi nghiên cứu chính (Primary RQ):
> *"Under a fixed temporal, novel-purchase, full-catalog ranking protocol on the controlled Vietnamese retail benchmark, does a decoupled Wide-and-Deep Two-Tower Hybrid yield statistically significant ranking improvements over faithfully tuned single-paradigm baselines?"*

* Tác giả đóng khung câu hỏi rất chặt chẽ:
  1. Dưới giao thức mua sản phẩm mới theo thời gian cố định (Temporal novel-purchase task).
  2. Xếp hạng trên toàn bộ danh mục hàng hóa ($C_u = I \setminus H_u^{\mathrm{seen}}$).
  3. So sánh với các đường cơ sở đơn hình thái (single-paradigm) được tinh chỉnh chuẩn xác và trung thực.

#### Ba đóng góp khoa học chính (Contributions):
1. **Giao thức nhận thức nguồn gốc (A Provenance-Aware Evaluation Protocol):** Toàn bộ dữ liệu phân tách, tập ứng viên, bộ lọc mặt nạ, chuỗi seed ngẫu nhiên và đường ống đánh giá được ràng buộc bằng mã băm mật mã SHA-256.
2. **Phân tách các không gian minh chứng (Separation of Evidence Namespaces):** Tách biệt chính thức việc kiểm chứng quy trình trên dữ liệu công khai (MovieLens 100K) khỏi việc đánh giá đối chuẩn bán lẻ kiểm soát (`VietRetail-Synth`), ngăn chặn việc đánh đồng giữa kiểm thử thủ tục và các tuyên bố giải thuật miền cụ thể.
3. **Xác thực thực nghiệm toàn diện của kiến trúc Lai (Empirical Validation of the Hybrid Architecture):** Báo cáo kết quả đối chuẩn thực nghiệm nghiêm ngặt trên tập dữ liệu bán lẻ. Mô hình Hybrid thể hiện hiệu quả xếp hạng vượt trội trên mọi độ đo: đạt **NDCG@10 = 0.1385** (**tăng +21.28%** so với Two-Tower BPR đơn lẻ) và **Macro GAUC = 0.7812**, khẳng định tính hợp lý và sự cộng hưởng của giả thuyết bổ trợ.

---

## 3. PHÂN TÍCH CHI TIẾT SECTION 2: RELATED WORK (DÒNG 77 – 102)

### 3.1. Mục 2.1: Đánh giá và Tính tái lập (Evaluation and Reproducibility - Dòng 79 – 82)

* **Luận điểm:** Phân tích sâu hơn bài học từ **Gusak et al. (2025)** về độ nhạy của phân tách thời gian và **Petrov & Macdonald (2022)** về tính tái lập của BERT4Rec.
* **Cảnh báo khoa học:** Việc đánh giá trên mẫu âm rút gọn (ví dụ: chỉ lấy ngẫu nhiên 99 sản phẩm âm) làm biến dạng nghiêm trọng thước đo và đảo lộn thứ hạng mô hình so với việc xếp hạng trên toàn bộ danh mục ($C_u$). Phân tách ngẫu nhiên làm rò rỉ các token tương tác tương lai vào biểu diễn tuần tự.

---

### 3.2. Mục 2.2: Lọc cộng tác, Mạng nơ-ron và Gợi ý tuần tự (Dòng 83 – 86)

Khảo sát toàn diện 6 mô hình kinh điển qua các thời kỳ:
1. **Sarwar et al. (2001) - ItemCF:** Lọc cộng tác dựa trên độ tương đồng láng giềng sản phẩm.
2. **Rendle et al. (2009) - BPR:** Tối ưu hóa xác suất hậu nghiệm theo cặp $(u, i, j)$ cho dữ liệu implicit.
3. **He et al. (2017) - Neural Collaborative Filtering (NCF):** Kết hợp Generalized Matrix Factorization (GMF) và Multi-Layer Perceptron (MLP) để học phi tuyến.
4. **Guo et al. (2017) - DeepFM:** Tích hợp Factorization Machine và Deep Neural Network để nắm bắt tương tác bậc thấp và bậc cao trong dự đoán CTR.
5. **Kang & McAuley (2018) - SASRec:** Áp dụng cơ chế Self-Attention nhân quả (Causal Attention) cho gợi ý sản phẩm tiếp theo theo chuỗi thời gian.
6. **Sun et al. (2019) - BERT4Rec:** Sử dụng kiến trúc Transformer hai chiều với hàm mục tiêu điền khuyết Cloze task (Masked Item Prediction).

* **Kết luận định vị:** Các mô hình này cung cấp tiền lệ về hàm mục tiêu và đối thủ so sánh, nhưng kết quả trong bài báo gốc của chúng không thể bê nguyên xi vào bảng so sánh nếu không có cầu nối giao thức thống nhất (protocol bridge).

---

### 3.3. Mục 2.3: Wide & Deep, Two-Tower và Biểu diễn Ngữ nghĩa (Dòng 87 – 90)

Phân tích các kiến trúc phục vụ truy xuất quy mô lớn:
* **Cheng et al. (2016) - Wide & Deep:** Khung phân rã giữa Memorization và Generalization.
* **Covington et al. (2016) & Yi et al. (2019) - Two-Tower Architecture:** Kiến trúc tháp đôi cho phép tính toán vector người dùng và vector sản phẩm độc lập, hỗ trợ tìm kiếm láng giềng gần nhất (MIPS/HNSW) với độ trễ dưới 10ms.
* **Wang et al. (2022) - DirectAU:** Tối ưu hóa trực tiếp tính căn chỉnh (Alignment) và tính đồng đều (Uniformity) của vector biểu diễn trên hình cầu đơn vị.
* **Yuan et al. (2025) - ContextGNN & Wang et al. (2025) - T2Diff:** Các nghiên cứu tiên phong mới nhất (năm 2025) về việc đưa ngữ cảnh đồ thị cục bộ và mô hình khuếch tán (diffusion) vào kiến trúc hai tháp nhằm khắc phục điểm yếu mất mát tương tác chéo.

---

### 3.4. Mục 2.4: Apriori, Luật kết hợp và Gợi ý Giỏ hàng kế tiếp (Dòng 91 – 94)

Cảnh báo học thuật sâu sắc về bản chất của gợi ý giỏ hàng:
* **Li et al. (2023a, RecSys) - NBR Reality Check:** Chỉ ra rằng phần lớn độ chính xác cao trong các hệ thống gợi ý giỏ hàng hiện nay là do **khách hàng mua lặp lại sản phẩm cũ (Repetition ratio cao)**.
* **Li et al. (2023b, SIGIR) - Repetition vs. Exploration:** Bóc tách bài toán thành 2 phần: Gợi ý sản phẩm mua lại (Repeat items) và Gợi ý khám phá sản phẩm mới (Novel items).
* **Li et al. (2023c, KDD) - Mask-Swap (BTBR):** Đề xuất cơ chế Mask-and-Swap để huấn luyện mô hình tập trung vào sản phẩm mới trong giỏ hàng tiếp theo.
* **Mansouri et al. (2026, WSDM):** Ứng dụng đồ thị phân biệt giữa hành vi lặp lại và hành vi khám phá.
* **Ứng dụng vào đề tài:** Thiết lập bài toán **Novel-purchase task** (chỉ đánh giá trên các sản phẩm người dùng chưa từng mua trong tập huấn luyện), loại bỏ hoàn toàn sự "ăn gian" điểm số từ việc đoán lặp lại các mặt hàng thiết yếu.

---

### 3.5. Mục 2.5: Gợi ý dựa trên Đồ thị và Học tương phản (Dòng 95 – 98)

* **He et al. (2020) - LightGCN:** Rút gọn mạng tích chập đồ thị (GCN), loại bỏ biến đổi phi tuyến tính và trọng số ma trận, chỉ giữ lại lan truyền thông điệp láng giềng (Neighborhood Aggregation).
* **Yu et al. (2022) - SimGCL & Cai et al. (2023) - LightGCL:** Bổ sung học tương phản (Contrastive Learning) và phân tích SVD để khử nhiễu đồ thị tương tác.
* **Ranh giới học thuật:** Các mô hình đồ thị hoạt động tốt trên các cạnh đã quan sát, nhưng **hoàn toàn bất lực trước sản phẩm Cold-start thực sự (Strict Zero-edge items)** vì đỉnh sản phẩm đó không có bất kỳ cạnh nối nào trong đồ thị huấn luyện.

---

### 3.6. Mục 2.6: Nội dung, Sản phẩm Cold-start và Học chuyển giao (Dòng 99 – 102)

Giải quyết bài toán Cold-start thông qua thông tin phụ trợ (Side information):
* **Volkovs et al. (2017) - DropoutNet:** Kỹ thuật Dropout ngẫu nhiên các vector biểu diễn tương tác trong quá trình huấn luyện để buộc mô hình phải học cách dự đoán chỉ dựa vào vector nội dung (Content features).
* **Huang et al. (2023) - ALDI:** Chưng cất tri thức (Knowledge Distillation) từ mô hình Warm sang mô hình Cold.
* **Reimers & Gurevych (2019) - Sentence-BERT:** Cung cấp vector nhúng ngữ nghĩa văn bản 768 chiều từ mô hình Transformer.
* **Sheng et al. (2025) - AlphaRec & Meehan et al. (2025, 2026):** Cảnh báo quan trọng: Việc căn chỉnh vector văn bản theo các giáo viên lọc cộng tác có thể khiến vector nội dung thừa hưởng **độ lệch độ phổ biến (Popularity Bias)**. Do đó, có vector văn bản không đồng nghĩa với việc giải quyết triệt để bài toán gợi ý công bằng cho sản phẩm mới.
* **Hou et al. (2022, 2023) - UniSRec, VQ-Rec & Zheng et al. (2026) - UTGRec:** Học biểu diễn mục chuyển giao tổng quát qua lượng tử hóa vector (Vector Quantization). Không thể tuyên bố tái lập các mô hình này nếu không khớp chính xác quy trình thích ứng hạ nguồn (Downstream adaptation).

---

## 4. BẢNG ĐỐI SÁNH TOÀN DIỆN 36 TRÍCH DẪN HỌC THUẬT (CITATION REGISTRY)

Dưới đây là toàn bộ 36 tài liệu tham khảo khoa học xuất hiện trong `paper.tex` và `refs.bib`, được đối chiếu chuẩn xác theo thứ tự bảng chữ cái của khóa trích dẫn:

| STT | Khóa trích dẫn | Tác giả & Năm | Tiêu đề bài báo | Hội nghị / Tạp chí | Vai trò & Điểm neo lý thuyết trong bài báo |
|:---:|:---|:---|:---|:---|:---|
| 1 | `agrawal1994_apriori` | Agrawal & Srikant (1994) | Fast Algorithms for Mining Association Rules... | VLDB 1994 | Định nghĩa ngưỡng Support & Confidence cho luật kết hợp Apriori trong nhánh Wide. |
| 2 | `cai2023_lightgcl` | Cai et al. (2023) | LightGCL: Simple Yet Effective Graph Contrastive... | ICLR 2023 | Tiền lệ học tương phản đồ thị có dẫn hướng SVD toàn cục. |
| 3 | `cheng2016_wide_deep` | Cheng et al. (2016) | Wide & Deep Learning for Recommender Systems | ACM DLRS 2016 | Khung lý thuyết phân rã Memorization (Wide) và Generalization (Deep). |
| 4 | `covington2016_youtube` | Covington et al. (2016) | Deep Neural Networks for YouTube Recommendations | ACM RecSys 2016 | Phân tách hai tầng hệ thống: Sinh ứng viên (Candidate Gen) và Xếp hạng (Ranking). |
| 5 | `ghoshal2014_multi_item_rules` | Ghoshal & Sarkar (2014) | Association Rules for Recommendations with Multiple Items | INFORMS J. Comput. 2014 | Cơ sở ứng dụng luật kết hợp đa sản phẩm vào hệ gợi ý bán lẻ. |
| 6 | `guo2017_deepfm` | Guo et al. (2017) | DeepFM: A Factorization-Machine based Neural Network... | IJCAI 2017 | Mô hình học tương tác bậc thấp và cao trên trường đặc trưng thưa. |
| 7 | `gusak2025_time_split` | Gusak et al. (2025) | Time to Split: Exploring Data Splitting Strategies... | ACM RecSys 2025 | Bằng chứng về sự thay đổi kết quả do chiến lược phân tách dữ liệu thời gian. |
| 8 | `he2017_ncf` | He et al. (2017) | Neural Collaborative Filtering | WWW 2017 | Học tương tác phi tuyến tính giữa User ID và Item ID qua mạng nơ-ron. |
| 9 | `he2020_lightgcn` | He et al. (2020) | LightGCN: Simplifying and Powering Graph Convolution... | ACM SIGIR 2020 | Tiền lệ lan truyền tuyến tính trên đồ thị tương tác người dùng - sản phẩm. |
| 10 | `hou2022_unisrec` | Hou et al. (2022) | Towards Universal Sequence Representation Learning... | ACM KDD 2022 | Học biểu diễn tuần tự phổ quát chuyển giao đa miền. |
| 11 | `hou2023_vqrec` | Hou et al. (2023) | Learning Vector-Quantized Item Representation... | ACM WebConf 2023 | Lượng tử hóa vector biểu diễn sản phẩm phục vụ gợi ý chuyển giao. |
| 12 | `huang2023_aldi` | Huang et al. (2023) | ALDI: Alignment-based Disentangled Distillation... | ACM KDD 2023 | Chưng cất tri thức gỡ rối căn chỉnh cho bài toán Cold-start sản phẩm. |
| 13 | `kang2018_sasrec` | Kang & McAuley (2018) | Self-Attentive Sequential Recommendation | IEEE ICDM 2018 | Cơ chế Causal Self-Attention cho bài toán dự báo sản phẩm kế tiếp. |
| 14 | `li2023_mask_swap` | Li et al. (2023c) | Mask-and-Swap: A Novel Data Augmentation... | ACM KDD 2023 | Kỹ thuật hoán đổi mặt nạ và đường cơ sở BTBR cho Next-Novel-Basket. |
| 15 | `li2023_nbr_reality` | Li et al. (2023a) | A Reality Check on Next-Basket Recommendation | ACM RecSys 2023 | Phân tích tỉ lệ lặp lại (Repeat ratio) và bóc trần hạn chế của độ đo tổng hợp. |
| 16 | `li2023_repetition_exploration` | Li et al. (2023b) | Repetition and Exploration in Next-Basket... | ACM SIGIR 2023 | Phân lập rõ rệt giữa bài toán gợi ý mua lại và bài toán khám phá món mới. |
| 17 | `liu2009_hybrid_seq_cf` | Liu et al. (2009) | A Hybrid Recommendation Approach based on... | Expert Syst. Appl. 2009 | Kết hợp chuỗi mẫu mua sắm tuần tự và lọc cộng tác. |
| 18 | `mansouri2026_repeat_explore_lightgcn` | Mansouri et al. (2026) | Graph-based Next-Basket Recommendation... | ACM WSDM 2026 | Tách biệt hành vi lặp lại và khám phá trên mạng đồ thị tương tác. |
| 19 | `meehan2025_cold_popbias` | Meehan et al. (2025) | Popularity Bias in Cold-Start Recommendation... | ACM RecSys 2025 | Chứng minh vector nội dung căn chỉnh theo CF vẫn bị nhiễm Popularity Bias. |
| 20 | `meehan2026_semco` | Meehan et al. (2026) | Semantic Collaborative Filtering for Sparse Cold-Start | ACM WSDM 2026 | Đánh giá lọc cộng tác ngữ nghĩa trong điều kiện dữ liệu sản phẩm cực thưa. |
| 21 | `peng2022_ham` | Peng et al. (2022) | Hierarchical Association-based Model for Next-Basket... | ACM KDD 2022 | Kết hợp liên kết phân tầng và sở thích dài hạn trong Next-Basket. |
| 22 | `peng2023_m2` | Peng et al. (2023) | Multi-view Multi-aspect Representation Learning... | ACM RecSys 2023 | Biểu diễn đa khung nhìn giỏ hàng, tiền lệ bóc tách thành phần (Ablation). |
| 23 | `petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo` | Petrov & Macdonald (2022) | A Systematic Review and Replicability Study of BERT4Rec... | ACM RecSys 2022 | Phân tích tính tái lập và ảnh hưởng của cài đặt huấn luyện. |
| 24 | `reimers2019_sbert` | Reimers & Gurevych (2019) | Sentence-BERT: Sentence Embeddings using Siamese... | EMNLP 2019 | Cơ sở toán học cho vector nhúng ngữ nghĩa câu từ mạng Siamese/Triplet. |
| 25 | `rendle2009_bpr` | Rendle et al. (2009) | BPR: Bayesian Personalized Ranking from Implicit... | UAI 2009 | Hàm mất mát tối ưu hóa thứ hạng cá nhân hóa theo cặp kinh điển. |
| 26 | `sarwar2001_itemcf` | Sarwar et al. (2001) | Item-based Collaborative Filtering Recommendation... | ACM WWW 2001 | Thuật toán kinh điển tính độ tương đồng giữa các sản phẩm từ lịch sử mua. |
| 27 | `sheng2025_alpharec` | Sheng et al. (2025) | AlphaRec: Language Representations for Zero-Shot... | ACM WSDM 2025 | Đánh giá biểu diễn ngôn ngữ trong gợi ý không mẫu (Zero-Shot). |
| 28 | `sun2019_bert4rec` | Sun et al. (2019) | BERT4Rec: Sequential Recommendation with Bidirectional... | ACM CIKM 2019 | Mô hình Transformer hai chiều huấn luyện qua tác vụ điền khuyết Cloze. |
| 29 | `volkovs2017_dropoutnet` | Volkovs et al. (2017) | DropoutNet: Addressing Cold Start in Recommender... | ACM RecSys 2017 | Kỹ thuật Dropout triệt tiêu vector tương tác để thích ứng với Cold-start. |
| 30 | `wang2022_directau` | Wang et al. (2022) | Towards Representation Alignment and Uniformity... | ACM SIGIR 2022 | Tối ưu hóa biểu diễn CF qua hai đặc tính Alignment và Uniformity. |
| 31 | `wang2025_t2diff` | Wang et al. (2025) | T2Diff: Two-Tower Diffusion Model for Efficient... | ACM WSDM 2025 | Tích hợp mô hình khuếch tán vào kiến trúc Two-Tower tăng tương tác chéo. |
| 32 | `yi2019_ndr` | Yi et al. (2019) | Sampling-bias-corrected Neural Modeling for Large... | ACM RecSys 2019 | Kỹ thuật sửa sai độ lệch chọn mẫu trong mạng tháp đôi của Google. |
| 33 | `yu2022_simgcl` | Yu et al. (2022) | Are Graph Augmentations Necessary? Simple Contrastive... | ACM SIGIR 2022 | Mô hình SimGCL chứng minh thêm nhiễu ngẫu nhiên tốt hơn biến đổi đồ thị. |
| 34 | `yuan2025_contextgnn` | Yuan et al. (2025) | ContextGNN: Beyond Two-Tower Recommendation Systems | ICLR 2025 | Kết hợp đồ thị ngữ cảnh cục bộ với tháp đôi dự phòng khám phá. |
| 35 | `zhao2021_recbole` | Zhao et al. (2021) | RecBole: Towards a Unified, Comprehensive and Efficient Framework for Recommendation Algorithms | ACM CIKM 2021 | Thư viện chuẩn hóa quốc tế thực thi làn kiểm chứng quy trình công khai (`PUBLIC_VALIDATION` trên MovieLens 100K). |
| 36 | `zheng2026_utgrec` | Zheng et al. (2026) | Universal Item Tokenization for Transferable Generative Recommendation | ACM SIGIR 2026 | Mô hình đồ thị chuyển giao tổng quát kết hợp tinh chỉnh hạ nguồn. |

---

## 5. TỪ ĐIỂN THUẬT NGỮ ĐỐI CHIẾU ANH - VIỆT (ACADEMIC GLOSSARY)

* **Estimand:** Đại lượng lý thuyết mục tiêu cần ước lượng trong tổng thể thống kê (phân biệt với *Estimator* là giải thuật ước lượng và *Estimate* là giá trị số thu được).
* **Provenance-aware Protocol:** Giao thức nhận thức nguồn gốc dữ liệu (mọi dữ liệu, phân tách, siêu tham số đều có biên lai mã băm kiểm chứng SHA-256).
* **VietRetail-Synth Benchmark:** Chuẩn đối sánh thực nghiệm bán lẻ có kiểm soát (5.000 khách hàng, 5.200 SKU sản phẩm, 823.371 tương tác), dùng để đo lường các cơ chế giải thuật dưới các điều kiện toán học minh bạch.
* **Full-catalog Ranking ($C_u = I \setminus H_u^{\mathrm{seen}}$):** Giao thức xếp hạng trên toàn bộ danh mục sản phẩm (loại trừ các món người dùng đã mua trong tập Train), không rút gọn mẫu âm (No negative downsampling at test time).
* **Seen-item Masking:** Cơ chế che mặt nạ các sản phẩm đã tương tác trong quá khứ để bắt buộc mô hình phải gợi ý sản phẩm mới.
* **Deterministic Tie Handling:** Quy tắc giải quyết điểm số bằng nhau mang tính tất định (sắp xếp giảm dần theo điểm số, nếu hòa điểm thì sắp xếp tăng dần theo ID sản phẩm gốc) nhằm triệt tiêu biến thiên ngẫu nhiên.
* **Strict Zero-Edge Cold Items:** Các sản phẩm hoàn toàn không có bất kỳ tương tác nào trong tập huấn luyện (khác với *Sparse Items* là sản phẩm hiếm có 1–2 tương tác).
* **Novel Organic Purchase:** Giao dịch mua hàng tự nhiên đối với một sản phẩm mới tinh mà người dùng chưa từng mua trước đó.
* **Additive Per-User Z-Score Fusion:** Kỹ thuật chuẩn hóa điểm số per-user về phân phối chuẩn chuẩn tắc ($z = \frac{s - \mu_u}{\sigma_u}$) trước khi cộng có trọng số, triệt tiêu sự lệch pha thang đo giữa điểm tích vô hướng (Deep) và độ tin cậy luật kết hợp (Wide).
* **Hierarchical Paired Bootstrap:** Kế hoạch lấy mẫu lại phân tầng có ghép cặp (resample theo seed, sau đó resample theo user index) với 2.000 lần lặp để tính khoảng tin cậy 95\% không phụ thuộc phân phối chuẩn.
* **Evidence Namespaces:** Các không gian minh chứng độc lập (tách biệt rạch ròi giữa kết quả kiểm chứng đường ống công khai `PUBLIC_VALIDATION` và kết quả thực nghiệm mô hình đề xuất `RETAIL_BENCHMARK`).
