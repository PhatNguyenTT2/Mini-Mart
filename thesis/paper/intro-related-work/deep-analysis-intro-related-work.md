# GIẢI NGHĨA VÀ PHÂN TÍCH HỌC THUẬT CHUYÊN SÂU: SECTION 1 (INTRODUCTION) & SECTION 2 (RELATED WORK)
## BẢN DỊCH NGHĨA TIẾNG VIỆT SÁT NGHĨA VÀ LUẬN GIẢI HỌC THUẬT TOÀN DIỆN

**Tài liệu tham chiếu:** Bài báo khoa học hoàn chỉnh `paper.tex` và bản in xuất bản `paper.pdf` (10 trang chuẩn IEEE)  
**Tiêu đề bài báo:** *Reproducible Hybrid Recommendation for Vietnamese Retail*  
**Giảng viên hướng dẫn:** TS. Nguyễn Thị Xuân Hương  
**Nhóm tác giả sinh viên:** 
- Nguyễn Trương Tiến Phát (MSSV: 23521148)
- Đỗ Minh Đức (MSSV: 23520303)  
**Đơn vị:** Khoa Công nghệ Phần mềm, Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  
**Địa chỉ lưu trữ:** `thesis/paper/intro-related-work/deep-analysis-intro-related-work.md`

---

## MỤC LỤC
1. [Triết lý khoa học và Khung phương pháp luận của bài báo](#1-triết-lý-khoa-học-và-khung-phương-pháp-luận-của-bài-báo)
2. [Section 1: Mở đầu (Introduction) - Dịch sát nghĩa & Luận giải chi tiết](#2-section-1-mở-đầu-introduction---dịch-sát-nghĩa--luận-giải-chi-tiết)
   - [Đoạn 1: Định nghĩa bài toán & Phân tách Sinh ứng viên vs Xếp hạng](#21-đoạn-1-định-nghĩa-bài-toán--phân-tách-sinh-ứng-viên-vs-xếp-hạng-dòng-46--47)
   - [Đoạn 2: Thiết lập Chuẩn đối sánh Bán lẻ VietRetail-Synth](#22-đoạn-2-thiết-lập-chuẩn-đối-sánh-bán-lẻ-vietretail-synth-dòng-48--49)
   - [Mục 1.1: Tại sao Tính khả so sánh là một Bài toán Nghiên cứu Cơ bản](#23-mục-11-tại-sao-tính-khả-so-sánh-là-một-bài-toán-nghiên-cứu-cơ-bản-dòng-50--55)
   - [Mục 1.2: Các Tín hiệu Khác biệt và Giả thuyết Bổ trợ về Mô hình Lai](#24-mục-12-các-tín-hiệu-khác-biệt-và-giả-thuyết-bổ-trợ-về-mô-hình-lai-dòng-56--61)
   - [Mục 1.3: Câu hỏi Nghiên cứu và Ba Đóng góp Khoa học Lớn](#25-mục-13-câu-hỏi-nghiên-cứu-và-ba-đóng-góp-khoa-học-lớn-dòng-62--75)
3. [Section 2: Tổng quan Nghiên cứu (Related Work) - Dịch sát nghĩa & Luận giải chi tiết](#3-section-2-tổng-quan-nghiên-cứu-related-work---dịch-sát-nghĩa--luận-giải-chi-tiết)
   - [Mục 2.1: Giao thức Đánh giá và Tính Tái lập trong Hệ Gợi ý](#31-mục-21-giao-thức-đánh-giá-và-tính-tái-lập-trong-hệ-gợi-ý-dòng-79--82)
   - [Mục 2.2: Lọc cộng tác, Xếp hạng Nơ-ron và Mô hình Tuần tự](#32-mục-22-lọc-cộng-tác-xếp-hạng-nơ-ron-và-mô-hình-tuần-tự-dòng-83--86)
   - [Mục 2.3: Kiến trúc Mạng Nơ-ron Two-Tower và Học Biểu diễn](#33-mục-23-kiến-trúc-mạng-nơ-ron-two-tower-và-học-biểu-diễn-dòng-87--90)
   - [Mục 2.4: Khai phá Luật Kết hợp và Gợi ý Giỏ hàng Kế tiếp](#34-mục-24-khai-phá-luật-kết-hợp-và-gợi-ý-giỏ-hàng-kế-tiếp-dòng-91--94)
   - [Mục 2.5: Tích chập Đồ thị và Học Tương phản](#35-mục-25-tích-chập-đồ-thị-và-học-tương-phản-dòng-95--98)
   - [Mục 2.6: Chiếu đặc trưng Nội dung, Xử lý Cold-start và Học Chuyển giao](#36-mục-26-chiếu-đặc-trưng-nội-dung-xử-lý-cold-start-và-học-chuyển-giao-dòng-99--102)
4. [Bảng Đối sánh Toàn diện 36 Trích dẫn Học thuật (Citation Registry)](#4-bảng-đối-sánh-toàn-diện-36-trích-dẫn-học-thuật-citation-registry)
5. [Từ điển Thuật ngữ Đối chiếu Anh - Việt (Academic Glossary)](#5-từ-điển-thuật-ngữ-đối-chiếu-anh---việt-academic-glossary)

---

## 1. TRIẾT LÝ KHOA HỌC VÀ KHUNG PHƯƠNG PHÁP LUẬN CỦA BÀI BÁO

Bài báo `paper.tex` được xây dựng dựa trên trường phái **Khắc kỷ học thuật và Liêm chính khoa học (Epistemological Rigor & Reproducibility First)**, trực tiếp giải quyết cuộc khủng hoảng tái lập trong lĩnh vực Hệ gợi ý (Recommender Systems):

1. **Tính bất định và dễ gãy của số đo ngoại tuyến (Offline Metric Brittleness):**
   Một kết quả thực nghiệm công bố "mô hình đạt NDCG cao hơn 3%" hoàn toàn vô nghĩa nếu không công khai: cách thức chia thời gian (Global Temporal Split vs Random Split), không gian lấy mẫu âm (Full-catalog vs Sampled 99), cơ chế che giấu sản phẩm đã mua (Seen-item Masking), và quy tắc hòa điểm (Tie-breaking).
2. **Phân định rõ rệt Không gian Minh chứng (Evidence Namespaces):**
   Tách biệt tuyệt đối giữa:
   - `PUBLIC_VALIDATION`: Kiểm chứng tính tất định của đường ống thực nghiệm trên bộ dữ liệu chuẩn quốc tế MovieLens 100K thông qua framework RecBole 1.2.1.
   - `RETAIL_BENCHMARK`: Thực nghiệm đánh giá đối chuẩn trên bộ dữ liệu bán lẻ kiểm soát **VietRetail-Synth** dưới giao thức xếp hạng toàn danh mục ($C_u = I \setminus H_u^{\mathrm{seen}}$).
3. **Đóng góp Kép (Phương pháp luận & Thực nghiệm Hoàn chỉnh):**
   Bài báo không chỉ đóng góp giao thức đánh giá nhận thức nguồn gốc (Provenance-Aware Evaluation Protocol) được khóa bằng mã băm SHA-256, mà còn xác thực thực nghiệm rằng kiến trúc lai **Wide-and-Deep Two-Tower Hybrid** vượt trội vượt bậc (+21.28% NDCG@10) so với các mô hình đơn lẻ.

---

## 2. SECTION 1: MỞ ĐẦU (INTRODUCTION) - DỊCH SÁT NGHĨA & LUẬN GIẢI CHI TIẾT

### 2.1. Đoạn 1: Định nghĩa bài toán & Phân tách Sinh ứng viên vs Xếp hạng (Dòng 46 – 47)

#### Nguyên văn tiếng Anh:
> *"Retail recommendation is frequently characterized as a model-selection problem, but an offline empirical result is first and foremost a statement about a defined ranking task. A recommendation engine must determine which portion of user history is legitimately accessible, which items are eligible candidates, what specific user action constitutes a positive future event, and how numerical scores are translated into an ordered presentation list. In modern production systems, candidate generation (retrieval) and precision ranking serve distinct operational roles rather than interchangeable names for a single predictor \cite{covington2016_youtube, yi2019_ndr}. This architectural distinction is particularly crucial in retail settings characterized by sparse user--item interaction matrices, rapidly shifting purchase sequences, rich multi-modal product metadata, and newly introduced products with sparse or non-existent interaction histories. The same nominal algorithm can yield vastly divergent estimands when the candidate space or the target definition is altered."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Hệ gợi ý bán lẻ thường được mô tả như một bài toán lựa chọn mô hình, nhưng một kết quả thực nghiệm ngoại tuyến trước hết và trên hết là một phát biểu về một tác vụ xếp hạng được định nghĩa cụ thể. Một cỗ máy gợi ý phải xác định phần lịch sử nào của người dùng là được phép truy cập một cách hợp lệ, những sản phẩm nào là ứng viên đủ điều kiện, hành động cụ thể nào của người dùng cấu thành nên một sự kiện tích cực trong tương lai, và cách thức các điểm số định lượng được chuyển dịch thành một danh sách trình bày có thứ tự. Trong các hệ thống vận hành thực tế hiện đại, việc sinh ứng viên (truy xuất) và xếp hạng chính xác đảm nhiệm các vai trò vận hành tách biệt, chứ không phải là những tên gọi có thể hoán đổi cho một bộ dự đoán duy nhất \cite{covington2016_youtube, yi2019_ndr}. Sự phân biệt kiến trúc này đặc biệt quan trọng trong các bối cảnh bán lẻ có ma trận tương tác người dùng - sản phẩm thưa thớt, chuỗi mua sắm biến đổi nhanh chóng, siêu dữ liệu sản phẩm đa phương thức phong phú, và các sản phẩm mới ra mắt với lịch sử tương tác thưa thớt hoặc hoàn toàn bằng không. Cùng một thuật toán trên danh nghĩa có thể mang lại các đối tượng ước lượng (estimands) hoàn toàn phân kỳ khi không gian ứng viên hoặc định nghĩa mục tiêu bị thay đổi."*

#### Luận giải học thuật chuyên sâu:
1. **Lật lại định kiến "chọn mô hình" (Model-Selection Fallacy):**
   Giới nghiên cứu thường hỏi: "Mô hình nào tốt hơn? Transformer hay Graph Convolution?". Tác giả chỉ rõ rằng điểm số đo đạc ngoại tuyến không đo lường "bản chất siêu việt" của thuật toán, mà đo lường **mức độ tương thích giữa mô hình với các giả định của tác vụ xếp hạng**.
2. **Bốn biến số cấu thành tác vụ xếp hạng:**
   - *Lịch sử được phép truy cập:* Phải cắt dữ liệu theo mốc thời gian chặt chẽ (Temporal Split) để tránh rò rỉ tương lai (Data Leakage).
   - *Ứng viên đủ điều kiện:* Ứng viên là toàn bộ danh mục sản phẩm của hệ thống hay chỉ là một danh sách nhỏ còn hàng tại cửa hàng cụ thể.
   - *Sự kiện tích cực mục tiêu:* Mua hàng tự nhiên (Organic purchase), thêm vào giỏ, hay nhấp chuột.
   - *Chuyển dịch điểm số thành danh sách:* Cách giải quyết điểm hòa (Tie-breaking) ảnh hưởng rất lớn đến độ đo top-K.
3. **Phân tách Sinh ứng viên (Retrieval) vs Xếp hạng (Ranking):**
   - Dẫn chứng 2 công trình kinh điển: **Covington et al. (2016)** của YouTube và **Yi et al. (2019)** của Google.
   - *Candidate Generation (Tầng 1):* Cần độ trễ cực thấp (< 10ms) để lọc hàng triệu sản phẩm xuống vài trăm sản phẩm tiềm năng, dựa trên tính toán vector tháp đôi và tìm kiếm láng giềng gần nhất (MIPS/HNSW).
   - *Ranking (Tầng 2):* Dùng các mô hình học máy phức tạp, tiếp nhận hàng trăm đặc trưng chéo để sắp xếp chính xác top 10 món tốt nhất cho người dùng.
4. **Khái niệm Estimand trong Thống kê học:**
   - *Estimand* là đại lượng phân phối lý thuyết mục tiêu cần ước lượng. Nếu không gian ứng viên thay đổi từ 100 sản phẩm lấy mẫu sang 5.200 sản phẩm toàn danh mục, bài toán đã chuyển sang ước lượng một *estimand* hoàn toàn khác.

---

### 2.2. Đoạn 2: Thiết lập Chuẩn đối sánh Bán lẻ VietRetail-Synth (Dòng 48 – 49)

#### Nguyên văn tiếng Anh:
> *"The present study addresses this challenge within a controlled Vietnamese retail benchmark setting, designated as \textbf{VietRetail-Synth}. The benchmark is engineered to mirror the operational data structures of chain-level retail stores, encompassing longitudinal customer purchasing records, catalog taxonomy, dynamic pricing signals, and basket checkout events. Its interaction patterns are controlled and semi-synthetic, designed deliberately to expose specific algorithmic mechanisms—such as rule-aligned co-purchase patterns and item-side semantic features—while maintaining full mathematical traceability. The declared benchmark manifest comprises 5,000 customers, 5,200 unique SKUs, 823,371 interaction events, and an isolated strict item-cold subset."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Nghiên cứu hiện tại giải quyết thách thức này trong một thiết lập chuẩn đối sánh bán lẻ Việt Nam được kiểm soát, mang định danh chính thức là **VietRetail-Synth**. Chuẩn đối sánh này được thiết kế kỹ thuật để phản ánh cấu trúc dữ liệu vận hành của các chuỗi cửa hàng bán lẻ, bao gồm hồ sơ mua sắm dài hạn của khách hàng, phân loại danh mục, tín hiệu giá động, và các sự kiện thanh toán giỏ hàng. Các hình mẫu tương tác của nó được kiểm soát và mang tính bán tổng hợp, được thiết kế có chủ đích nhằm bóc tách các cơ chế giải thuật cụ thể—chẳng hạn như các mẫu mua kèm phù hợp với luật kết hợp và các đặc trưng ngữ nghĩa phía sản phẩm—trong khi vẫn duy trì khả năng truy xuất nguồn gốc toán học đầy đủ. Bản tuyên bố chuẩn đối sánh chỉ định 5.000 khách hàng, 5.200 SKU sản phẩm duy nhất, 823.371 sự kiện tương tác và một tập con sản phẩm cold-start nghiêm ngặt được cô lập riêng biệt."*

#### Luận giải học thuật chuyên sâu:
1. **Chuẩn hóa danh xưng học thuật (`VietRetail-Synth`):**
   Xóa bỏ triệt để mã phiên bản nội bộ `v5`, thay bằng tên gọi chính thức **VietRetail-Synth Benchmark**. Tên gọi này thể hiện rõ bản chất: Dữ liệu đặc trưng cho thị trường bán lẻ Việt Nam, có tính chất bán tổng hợp (Semi-synthetic) nhưng tuân thủ cấu trúc dữ liệu chuỗi siêu thị thực tế.
2. **Luận điểm Liêm chính Khoa học (Transparency & Reproducibility):**
   Tác giả không tuyên bố mập mờ đây là "dữ liệu thu thập từ người tiêu dùng thực tế hàng triệu người" (dễ bị phản biện về tính vi phạm quyền riêng tư hoặc thiếu tính khái quát thống kê). Thay vào đó, việc công khai dữ liệu là *semi-synthetic* cho phép kiểm soát hoàn toàn các biến số ngoại lai, từ đó đo lường chính xác cơ chế hoạt động của thuật toán (Mechanism Study).
3. **Quy mô bộ dữ liệu chuẩn:**
   - Khách hàng: 5.000 users.
   - Mặt hàng (SKUs): 5.200 items.
   - Giao dịch: 823.371 interactions.
   - Tập Cold-start: Nhóm sản phẩm hoàn toàn không có cạnh tương tác nào trong tập huấn luyện (Strict Zero-Edge Cold Items).

---

### 2.3. Mục 1.1: Tại sao Tính khả so sánh là một Bài toán Nghiên cứu Cơ bản (Dòng 50 – 55)

#### Nguyên văn tiếng Anh:
> *"Comparative conclusions in offline recommender literature are acutely sensitive to design choices that are frequently dismissed as mere implementation details. For instance, data partitioning policy directly dictates the information horizon available at inference time. Recent empirical investigations into data-splitting strategies reveal that sequential recommender performance fluctuates substantially depending on whether random, user-level, or global temporal splits are adopted \cite{gusak2025_time_split}. Concurrently, systematic replicability studies on deep architectures such as BERT4Rec demonstrate that subtle training configurations and negative-sampling schemes fundamentally alter published outcomes \cite{petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo}. Candidate set construction, seen-item masking, score tie-breaking, cutoff thresholds ($K$), and aggregation operators collectively define the underlying statistical quantity being estimated. Performance metrics bearing identical names (e.g., NDCG@10 or Hit Ratio) cannot be legitimately compared across papers unless these experimental preconditions are identical.*
> 
> *This paper addresses this vulnerability by treating the evaluation protocol as a first-class, immutable scientific artifact. The protocol locks a global temporal split, full-catalog candidate evaluation, strict seen-item masking, deterministic identifier-based tie-breaking, and independent metric evaluation. Every candidate model exports raw predicted scores into a decoupled, shared evaluator. The evaluator—completely isolated from model training code—applies the masking operators, executes full ranking, and computes per-user metrics. This separation ensures that model differences are transparently inspectable and prevents source-native performance figures from being conflated with full-catalog benchmarks."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Các kết luận so sánh trong y văn hệ gợi ý ngoại tuyến đặc biệt nhạy cảm với các lựa chọn thiết kế mà vốn dĩ thường bị xem nhẹ như những chi tiết cài đặt lặt vặt. Chẳng hạn, chính sách phân chia dữ liệu quyết định trực tiếp chân trời thông tin khả dụng tại thời điểm suy luận. Các điều tra thực nghiệm gần đây về chiến lược chia dữ liệu chỉ ra rằng hiệu năng của mô hình gợi ý tuần tự biến động mạnh mẽ tùy thuộc vào việc áp dụng phương thức chia ngẫu nhiên, chia theo thời gian ở cấp người dùng, hay chia theo thời gian toàn cục \cite{gusak2025_time_split}. Đồng thời, các nghiên cứu có hệ thống về tính tái lập trên các kiến trúc sâu như BERT4Rec chứng minh rằng các cấu hình huấn luyện tinh vi và phương thức lấy mẫu âm thay đổi căn bản các kết quả công bố \cite{petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo}. Cách thức xây dựng tập ứng viên, che giấu các sản phẩm đã xem, giải quyết điểm hòa, ngưỡng cắt ($K$), và các toán tử gom cụm tập hợp lại cùng nhau định nghĩa đại lượng thống kê nền tảng đang được ước lượng. Các độ đo hiệu năng mang tên gọi giống hệt nhau (ví dụ: NDCG@10 hoặc Hit Ratio) không thể được so sánh một cách hợp lệ giữa các bài báo trừ phi các điều kiện tiên quyết thực nghiệm này hoàn toàn đồng nhất.*
> 
> *Bài báo này giải quyết lỗ hổng đó bằng cách coi giao thức đánh giá như một sản phẩm khoa học bất biến hạng nhất. Giao thức khóa chặt việc phân tách thời gian toàn cục, đánh giá ứng viên trên toàn bộ danh mục, che giấu nghiêm ngặt các sản phẩm đã xem, giải quyết điểm hòa mang tính tất định dựa trên mã định danh, và đánh giá độ đo độc lập. Mọi mô hình ứng viên đều xuất điểm dự đoán thô sang một bộ đánh giá dùng chung được phân tách riêng biệt. Chính bộ đánh giá—hoàn toàn cô lập khỏi mã huấn luyện mô hình—sẽ áp dụng các toán tử che mặt nạ, thực thi việc xếp hạng đầy đủ và tính toán các độ đo trên từng người dùng. Sự phân tách này đảm bảo rằng các sai khác giữa các mô hình có thể được thanh tra một cách minh bạch và ngăn chặn việc đánh đồng các con số hiệu năng gốc với các chuẩn đối sánh toàn danh mục."*

#### Luận giải học thuật chuyên sâu:
1. **Rò rỉ dữ liệu qua phân tách thời gian (Temporal Split Sensitivities):**
   - **Gusak et al. (RecSys 2025):** Nếu chia ngẫu nhiên (Random Split) hoặc chia Leave-one-out không neo thời gian toàn cục, mô hình sẽ thấy các tương tác trong tương lai để dự đoán quá khứ, tạo ra ảo tưởng về độ chính xác cao.
2. **Khủng hoảng tính tái lập từ cài đặt huấn luyện (BERT4Rec Replicability):**
   - **Petrov & Macdonald (RecSys 2022):** Chứng minh rằng cách lấy mẫu âm (Uniform sampling vs Popularity-biased sampling) và quy tắc tie-breaking có thể làm thay đổi kết quả NDCG tới 30–50%.
3. **Giao thức Đánh giá Độc lập (Shared Decoupled Evaluator):**
   - Nguyên tắc *"không để mô hình vừa đá bóng vừa thổi còi"*: Mô hình chỉ có nhiệm vụ sinh điểm thô $S(u, i)$. Toàn bộ việc che giấu sản phẩm đã mua ($H_u^{\mathrm{seen}}$), xếp hạng toàn danh mục ($C_u$), và tính NDCG@10 do một bộ đánh giá độc lập có kiểm soát mã băm SHA-256 thực thi.

---

### 2.4. Mục 1.2: Các Tín hiệu Khác biệt và Giả thuyết Bổ trợ về Mô hình Lai (Dòng 56 – 61)

#### Nguyên văn tiếng Anh:
> *"The proposed model architecture integrates an association rule-derived Wide component with a content-augmented Deep Two-Tower neural network. The underlying rationale rests upon a \textit{complementarity hypothesis}: an association rule branch captures explicit, high-frequency co-purchase regularities observed within customer checkout baskets (memorization), whereas a deep representation branch generalises across semantic feature spaces to identify relevant items that lack direct co-purchase history (generalization).*
> 
> *This design draws inspiration from, yet substantively differs from, Google's classical Wide \& Deep framework \cite{cheng2016_wide_deep}, which relies on linear cross-product transformations over binned continuous features. It is likewise distinct from neighborhood-based item collaborative filtering (ItemCF) \cite{sarwar2001_itemcf}, which relies strictly on interaction cosine overlaps, and pairwise matrix factorization trained via Bayesian Personalized Ranking (BPR) \cite{rendle2009_bpr}. Association rules mined via the Apriori algorithm \cite{agrawal1994_apriori, ghoshal2014_multi_item_rules} provide an interpretable mechanism for cross-selling, but association rules alone do not constitute a full-catalog ranking system. Prior next-basket studies confirm that combining transition, popularity, and associative signals enhances basket completion \cite{liu2009_hybrid_seq_cf, peng2022_ham, peng2023_m2}. However, determining the exact synergistic benefit of combining Wide association rules with Deep Two-Tower representations under a strict temporal novel-purchase protocol remains an open empirical question."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Kiến trúc mô hình đề xuất tích hợp một thành phần Rộng (Wide) kế thừa từ luật kết hợp cùng một mạng nơ-ron Tháp Đôi Sâu (Deep Two-Tower) được tăng cường nội dung. Cơ sở lý luận nền tảng dựa trên một **giả thuyết bổ trợ**: nhánh luật kết hợp nắm bắt các quy luật mua kèm tường minh có tần suất cao được quan sát trong các giỏ hàng thanh toán của khách hàng (ghi nhớ - memorization), trong khi nhánh biểu diễn sâu khái quát hóa trên các không gian đặc trưng ngữ nghĩa để định danh các sản phẩm liên quan vốn thiếu lịch sử mua kèm trực tiếp (khái quát hóa - generalization).*
> 
> *Thiết kế này lấy cảm hứng từ, nhưng khác biệt về mặt bản chất so với, khung làm việc Wide & Deep kinh điển của Google \cite{cheng2016_wide_deep} vốn dựa trên các phép biến đổi tích chéo tuyến tính trên các đặc trưng liên tục được phân thùng. Nó cũng tương tự khác biệt so với lọc cộng tác láng giềng dựa trên sản phẩm (ItemCF) \cite{sarwar2001_itemcf} vốn chỉ dựa nghiêm ngặt vào độ trùng lặp cosine tương tác, và phân rã ma trận theo cặp được huấn luyện qua Xếp hạng Cá nhân hóa Bayes (BPR) \cite{rendle2009_bpr}. Các luật kết hợp được khai phá qua giải thuật Apriori \cite{agrawal1994_apriori, ghoshal2014_multi_item_rules} cung cấp một cơ chế có khả năng diễn giải cho việc bán chéo, nhưng bản thân các luật kết hợp đơn lẻ không cấu thành một hệ thống xếp hạng toàn danh mục. Các nghiên cứu giỏ hàng kế tiếp trước đây xác nhận rằng việc kết hợp các tín hiệu chuyển dịch, độ phổ biến và tính liên kết giúp tăng cường việc hoàn thiện giỏ hàng \cite{liu2009_hybrid_seq_cf, peng2022_ham, peng2023_m2}. Tuy nhiên, việc xác định lợi ích cộng hưởng chính xác của việc kết hợp luật liên kết Wide với các biểu diễn Two-Tower Deep dưới một giao thức mua sản phẩm mới theo thời gian nghiêm ngặt vẫn là một câu hỏi thực nghiệm mở."*

#### Luận giải học thuật chuyên sâu:
1. **Giả thuyết Bổ trợ (Complementarity Hypothesis):**
   - **Nhánh Wide (Luật kết hợp Apriori):** Đảm bảo tính chính xác cực cao trên các mẫu hành vi quen thuộc tại quầy (ví dụ: mua kem đánh răng thì gợi ý bàn chải). Đây là cơ chế *Memorization*.
   - **Nhánh Deep (Two-Tower):** Ánh xạ khách hàng và sản phẩm vào không gian vector chung $d$ chiều, tích hợp ngữ nghĩa văn bản tiếng Việt qua SBERT. Cho phép gợi ý những sản phẩm người dùng chưa từng mua nhưng có cùng sở thích tiềm ẩn. Đây là cơ chế *Generalization*.
2. **Phân biệt rạch ròi với các công trình kinh điển:**
   - Khác Google Wide & Deep: Google dùng tích chéo tuyến tính các trường thuộc tính (Cross-product feature transformations); bài báo này dùng các **luật kết hợp khai phá thực sự (Mined Association Rules)** từ giỏ hàng.
   - Khác ItemCF: ItemCF chỉ tính tương đồng lịch sử mua chung, không có khả năng hiểu được ngữ nghĩa mô tả sản phẩm như Two-Tower.

---

### 2.5. Mục 1.3: Câu hỏi Nghiên cứu và Ba Đóng góp Khoa học Lớn (Dòng 62 – 75)

#### Nguyên văn tiếng Anh:
> *"This investigation centers on the following primary research question:
> \begin{quote}
> \textit{Under a fixed temporal, novel-purchase, full-catalog ranking protocol on the controlled Vietnamese retail benchmark, does a decoupled Wide-and-Deep Two-Tower Hybrid yield statistically significant ranking improvements over faithfully tuned single-paradigm baselines?}
> \end{quote}
> Secondary research questions examine performance variations across designated item-cold cohorts (zero interaction history in training) and the isolated ablation of the Wide rule branch.
> 
> The primary contributions of this paper are summarized as follows:
> \begin{enumerate}
>     \item \textbf{A Provenance-Aware Evaluation Protocol:} We specify an end-to-end reproducible protocol wherein data splits, candidate sets, masking filters, seed sequences, and evaluation pipelines are cryptographically bound via SHA-256 hashes.
>     \item \textbf{Separation of Evidence Namespaces:} We formally separate public dataset protocol verification (MovieLens 100K) from controlled retail benchmark evaluation (VietRetail-Synth), preventing procedural validation from being conflated with domain-specific algorithmic claims.
>     \item \textbf{Empirical Validation of the Hybrid Architecture:} We report rigorous benchmark evaluations on the controlled retail dataset. The proposed Wide-and-Deep Hybrid demonstrates superior ranking effectiveness across all evaluated metrics, achieving an NDCG@10 of 0.1385 (+21.3\% over BPR Two-Tower alone) and a Macro GAUC of 0.7812, confirming the validity of the complementarity hypothesis.
> \end{enumerate}"*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Cuộc điều tra này tập trung vào câu hỏi nghiên cứu chính sau đây:
> \begin{quote}
> \textit{Dưới một giao thức xếp hạng toàn danh mục, mua sản phẩm mới, phân tách theo thời gian cố định trên chuẩn đối sánh bán lẻ Việt Nam có kiểm soát, liệu mô hình Lai Wide-and-Deep Two-Tower tách rời có mang lại những cải thiện xếp hạng có ý nghĩa thống kê so với các đường cơ sở đơn hình thái được tinh chỉnh một cách trung thực hay không?}
> \end{quote}
> Các câu hỏi nghiên cứu thứ cấp kiểm tra các biến thiên hiệu năng trên các nhóm thuần tập sản phẩm cold-start được chỉ định (hoàn toàn không có lịch sử tương tác trong huấn luyện) và phân tích bóc tách cô lập nhánh luật Rộng.
> 
> Các đóng góp chính của bài báo này được tóm tắt như sau:
> \begin{enumerate}
>     \item \textbf{Một Giao thức Đánh giá Nhận thức Nguồn gốc:} Chúng tôi chỉ định một giao thức có khả năng tái lập đầu-cuối, trong đó việc phân tách dữ liệu, các tập ứng viên, các bộ lọc che mặt nạ, các chuỗi seed ngẫu nhiên và các đường ống đánh giá đều được ràng buộc bằng mật mã học qua mã băm SHA-256.
>     \item \textbf{Phân tách các Không gian Minh chứng:} Chúng tôi phân tách chính thức việc xác minh quy trình trên tập dữ liệu công khai (MovieLens 100K) khỏi việc đánh giá chuẩn đối sánh bán lẻ có kiểm soát (VietRetail-Synth), ngăn chặn việc đánh đồng giữa kiểm chứng thủ tục với các tuyên bố thuật toán mang tính miền cụ thể.
>     \item \textbf{Xác thực Thực nghiệm của Kiến trúc Lai:} Chúng tôi báo cáo các đánh giá đối chuẩn nghiêm ngặt trên tập dữ liệu bán lẻ có kiểm soát. Mô hình Lai Wide-and-Deep đề xuất thể hiện hiệu quả xếp hạng vượt trội trên mọi độ đo được đánh giá, đạt NDCG@10 là 0.1385 (tăng tương đối +21.3\% so với chỉ dùng Two-Tower BPR đơn lẻ) và Macro GAUC là 0.7812, xác nhận tính đúng đắn của giả thuyết bổ trợ.
> \end{enumerate}"*

#### Luận giải học thuật chuyên sâu:
1. **Cấu trúc Câu hỏi Nghiên cứu chuẩn mực (Primary RQ):**
   - Đóng khung đầy đủ 4 điều kiện ràng buộc: (1) Phân tách thời gian cố định, (2) Tác vụ mua món mới (Novel-purchase), (3) Toàn danh mục ($C_u$), (4) Đối thủ so sánh là đường cơ sở đơn hình thái được tái lập trung thực.
2. **Ba Đóng góp Khoa học Đột phá:**
   - *Đóng góp 1 (Giao thức tái lập mã băm SHA-256):* Tạo ra tiêu chuẩn công bố dữ liệu minh bạch, bất biến.
   - *Đóng góp 2 (Phân vùng Không gian Minh chứng):* Ngăn chặn sai lầm phổ biến là dùng kết quả MovieLens để quảng bá cho bán lẻ hoặc ngược lại.
   - *Đóng góp 3 (Xác thực thực nghiệm định lượng):* Đưa ra số liệu kiểm chứng thuyết phục: **NDCG@10 = 0.1385** (+21.28%), **HR@10 = 0.2190**, **Macro GAUC = 0.7812**, hoàn tất trọn vẹn mục tiêu nghiên cứu.

---

## 3. SECTION 2: TỔNG QUAN NGHIÊN CỨU (RELATED WORK) - DỊCH SÁT NGHĨA & LUẬN GIẢI CHI TIẾT

### 3.1. Mục 2.1: Giao thức Đánh giá và Tính Tái lập trong Hệ Gợi ý (Dòng 79 – 82)

#### Nguyên văn tiếng Anh:
> *"A recurring vulnerability in recommendation literature is the reliance on headline summary metrics that mask fundamental disparities in task contracts. Evaluating recommenders over randomly sampled negatives (e.g., 99 random unobserved items) has been shown to produce severe metric distortion and rank inversion compared to full-catalog evaluation \cite{petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo}. Similarly, Gusak et al. \cite{gusak2025_time_split} demonstrated that random or leave-one-out splits inadvertently leak future interaction tokens into sequential representations, creating an illusion of high predictive accuracy. Consequently, sound scientific methodology necessitates that temporal cutoffs, candidate sets ($C_u$), masking rules, and evaluation code be frozen and version-controlled independently of model code."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Một lỗ hổng mang tính lặp lại trong y văn hệ gợi ý là sự phụ thuộc vào các chỉ số tóm tắt dòng tít vốn che giấu những sai khác căn bản trong hợp đồng tác vụ. Việc đánh giá hệ gợi ý trên các mẫu âm được lấy mẫu ngẫu nhiên (chẳng hạn: 99 sản phẩm chưa quan sát ngẫu nhiên) đã được chứng minh là tạo ra sự biến dạng độ đo nghiêm trọng và đảo lộn thứ hạng mô hình so với đánh giá trên toàn bộ danh mục \cite{petrov2022_a_systematic_review_and_replicability_study_of_bert4rec_fo}. Tương tự, Gusak cùng các cộng sự \cite{gusak2025_time_split} đã chứng minh rằng các phép chia ngẫu nhiên hoặc chia kiểu để-lại-một (leave-one-out) đã vô tình làm rò rỉ các token tương tác tương lai vào các biểu diễn tuần tự, tạo ra một ảo tưởng về độ chính xác dự báo cao. Do đó, phương pháp luận khoa học đúng đắn đòi hỏi các mốc cắt thời gian, các tập ứng viên ($C_u$), các quy tắc che mặt nạ, và mã nguồn đánh giá phải được đóng băng và kiểm soát phiên bản độc lập hoàn toàn khỏi mã nguồn mô hình."*

#### Luận giải học thuật chuyên sâu:
* **Hiện tượng Đảo lộn Thứ hạng (Rank Inversion):** Mô hình A có thể vượt trội Mô hình B khi kiểm thử trên 99 mẫu âm ngẫu nhiên, nhưng khi đưa vào bài toán xếp hạng thực tế trên 5.200 sản phẩm toàn danh mục, Mô hình B lại vượt trội hoàn toàn. Do đó, bài báo bác bỏ việc lấy mẫu âm khi kiểm thử, cam kết đánh giá trên toàn bộ $C_u = I \setminus H_u^{\mathrm{seen}}$.

---

### 3.2. Mục 2.2: Lọc cộng tác, Xếp hạng Nơ-ron và Mô hình Tuần tự (Dòng 83 – 86)

#### Nguyên văn tiếng Anh:
> *"Classical Item-based Collaborative Filtering (ItemCF) \cite{sarwar2001_itemcf} computes static item-to-item similarities over historical transaction matrices. Rendle et al. \cite{rendle2009_bpr} introduced Bayesian Personalized Ranking (BPR), establishing a maximum posterior framework for pairwise ranking from implicit feedback. Neural Collaborative Filtering (NCF) \cite{he2017_ncf} replaced linear inner products with multi-layer perceptrons, while DeepFM \cite{guo2017_deepfm} integrated factorization machines with deep networks to model high-order feature interactions. In sequential settings, SASRec \cite{kang2018_sasrec} utilized unidirectional causal self-attention, whereas BERT4Rec \cite{sun2019_bert4rec} applied bidirectional cloze masking. While these models represent milestones, importing their reported benchmark numbers across incompatible candidate spaces is methodologically invalid without an aligned evaluation bridge."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Lọc cộng tác dựa trên sản phẩm kinh điển (ItemCF) \cite{sarwar2001_itemcf} tính toán độ tương đồng tĩnh giữa các sản phẩm trên các ma trận giao dịch lịch sử. Rendle cùng các cộng sự \cite{rendle2009_bpr} giới thiệu Xếp hạng Cá nhân hóa Bayes (BPR), thiết lập một khung xác suất hậu nghiệm cực đại cho việc xếp hạng theo cặp từ phản hồi ngầm. Lọc Cộng tác Nơ-ron (NCF) \cite{he2017_ncf} thay thế tích vô hướng tuyến tính bằng mạng perceptron đa tầng, trong khi DeepFM \cite{guo2017_deepfm} tích hợp máy nhân tử hóa (factorization machines) với các mạng sâu để mô hình hóa các tương tác đặc trưng bậc cao. Trong các thiết lập tuần tự, SASRec \cite{kang2018_sasrec} sử dụng cơ chế tự chú ý nhân quả một chiều, trong khi BERT4Rec \cite{sun2019_bert4rec} áp dụng kỹ thuật che mặt nạ điền khuyết hai chiều. Mặc dù các mô hình này đại diện cho những cột mốc quan trọng, việc nhập khẩu các con số đối chuẩn công bố của chúng qua các không gian ứng viên không tương thích là không hợp lệ về mặt phương pháp luận nếu thiếu một cầu nối đánh giá được căn chỉnh thống nhất."*

#### Luận giải học thuật chuyên sâu:
* Khảo sát 6 cột mốc công nghệ: Sarwar (2001 - ItemCF), Rendle (2009 - BPR Loss), He (2017 - NCF), Guo (2017 - DeepFM), Kang (2018 - SASRec Attention), Sun (2019 - BERT4Rec). Khẳng định không thể lấy điểm số từ bài báo gốc đem so sánh nếu môi trường và tập ứng viên không đồng nhất.

---

### 3.3. Mục 2.3: Kiến trúc Mạng Nơ-ron Two-Tower và Học Biểu diễn (Dòng 87 – 90)

#### Nguyên văn tiếng Anh:
> *"Two-Tower architectures have emerged as the industry standard for scalable retrieval \cite{covington2016_youtube, yi2019_ndr}. By projecting user context and item metadata into a shared latent Euclidean space, inference reduces to Maximum Inner Product Search (MIPS) executed via graph indexes (e.g., HNSW) in sub-10ms latencies. Recent theoretical advances explore representation properties beyond inner products: Wang et al. \cite{wang2022_directau} proposed DirectAU, directly optimizing alignment and uniformity on hyperspheres. Advanced extensions such as ContextGNN \cite{yuan2025_contextgnn} and T2Diff \cite{wang2025_t2diff} incorporate local graph interactions and diffusion processes to mitigate the expressive limitations of decoupled towers."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Các kiến trúc Tháp Đôi (Two-Tower) đã nổi lên như một tiêu chuẩn công nghiệp cho việc truy xuất có khả năng mở rộng quy mô \cite{covington2016_youtube, yi2019_ndr}. Bằng cách chiếu ngữ cảnh người dùng và siêu dữ liệu sản phẩm vào một không gian ẩn Euclid dùng chung, quá trình suy luận được rút gọn về bài toán Tìm kiếm Tích vô hướng Cực đại (MIPS) được thực thi qua các chỉ mục đồ thị (ví dụ: HNSW) với độ trễ dưới 10 mili-giây. Các tiến bộ lý thuyết gần đây khám phá các đặc tính biểu diễn vượt ra ngoài tích vô hướng: Wang cùng các cộng sự \cite{wang2022_directau} đề xuất DirectAU, trực tiếp tối ưu hóa tính căn chỉnh (alignment) và tính đồng đều (uniformity) trên các hình cầu siêu chiều. Các phần mở rộng tiên tiến như ContextGNN \cite{yuan2025_contextgnn} và T2Diff \cite{wang2025_t2diff} tích hợp các tương tác đồ thị cục bộ và các quy trình khuếch tán để giảm thiểu các giới hạn về năng lực biểu đạt của các tháp tách rời."*

#### Luận giải học thuật chuyên sâu:
* Tháp Đôi cho phép tách biệt tính toán: Vector User và Vector Item được tính độc lập và lưu vào cơ sở dữ liệu vector. Độ trễ truy xuất chỉ mất dưới 10ms nhờ thuật toán đồ thị HNSW. Các nghiên cứu mới nhất năm 2025 (ContextGNN, T2Diff) tập trung bù đắp sự thiếu hụt tương tác chéo giữa 2 tháp.

---

### 3.4. Mục 2.4: Khai phá Luật Kết hợp và Gợi ý Giỏ hàng Kế tiếp (Dòng 91 – 94)

#### Nguyên văn tiếng Anh:
> *"Association rule mining via Apriori \cite{agrawal1994_apriori} identifies co-occurring transaction sets based on minimum support and confidence thresholds. Ghoshal and Sarkar \cite{ghoshal2014_multi_item_rules} demonstrated that multi-item rules provide potent complementary signals for retail baskets. Recent reality-check analyses in next-basket recommendation emphasize the critical necessity of separating repeat consumption from novel exploration \cite{li2023_nbr_reality, li2023_repetition_exploration, li2023_mask_swap, mansouri2026_repeat_explore_lightgcn}. If an evaluation includes frequently re-purchased items (e.g., milk or bread), naive popularity heuristics appear deceptively strong. The protocol in this paper isolates novel-item recommendation by masking all previously seen items from candidate sets."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Khai phá luật kết hợp qua thuật toán Apriori \cite{agrawal1994_apriori} định danh các tập giao dịch đồng xuất hiện dựa trên các ngưỡng độ hỗ trợ (support) và độ tin cậy (confidence) tối thiểu. Ghoshal và Sarkar \cite{ghoshal2014_multi_item_rules} chứng minh rằng các luật đa sản phẩm cung cấp các tín hiệu bổ trợ mạnh mẽ cho giỏ hàng bán lẻ. Các phân tích kiểm chứng thực tế gần đây trong gợi ý giỏ hàng kế tiếp nhấn mạnh sự cần thiết sống còn của việc tách biệt giữa hành vi tiêu dùng lặp lại và hành vi khám phá sản phẩm mới \cite{li2023_nbr_reality, li2023_repetition_exploration, li2023_mask_swap, mansouri2026_repeat_explore_lightgcn}. Nếu một đánh giá bao gồm cả các mặt hàng thường xuyên được mua lại (ví dụ: sữa hoặc bánh mì), các thuật toán heuristics độ phổ biến ngây thơ sẽ có vẻ mạnh mẽ một cách đánh lừa. Giao thức trong bài báo này cô lập việc gợi ý sản phẩm mới bằng cách che giấu toàn bộ các sản phẩm đã từng xem trước đó khỏi các tập ứng viên."*

#### Luận giải học thuật chuyên sâu:
* **Hiện tượng "Ảo tưởng Độ phổ biến" (Popularity Illusion in Retail):** Nếu khách hàng vào siêu thị mua lại sữa tươi, một giải thuật đơn giản chỉ cần đoán "sữa tươi" là đạt điểm cao. Tuy nhiên, giá trị kinh doanh thực sự của hệ gợi ý nằm ở việc **khám phá sản phẩm mới (Novel exploration)**. Giao thức che mặt nạ $C_u = I \setminus H_u^{\mathrm{seen}}$ triệt tiêu hoàn toàn sự thiên lệch này.

---

### 3.5. Mục 2.5: Tích chập Đồ thị và Học Tương phản (Dòng 95 – 98)

#### Nguyên văn tiếng Anh:
> *"Graph neural networks propagate collaborative signals across high-order interaction paths. LightGCN \cite{he2020_lightgcn} streamlined graph convolution by eliminating non-linear activations and weight matrices, retaining only linear neighborhood smoothing. SimGCL \cite{yu2022_simgcl} and LightGCL \cite{cai2023_lightgcl} introduced contrastive self-supervised objectives to combat graph edge sparsity. However, as noted by Meehan et al. \cite{meehan2025_cold_popbias, meehan2026_semco}, graph propagation mechanisms operate strictly over connected components and fail catastrophically when evaluating strict zero-edge cold items."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Các mạng nơ-ron đồ thị lan truyền các tín hiệu cộng tác qua các đường dẫn tương tác bậc cao. LightGCN \cite{he2020_lightgcn} tinh giản tích chập đồ thị bằng cách loại bỏ các hàm kích hoạt phi tuyến tính và ma trận trọng số, chỉ giữ lại phép làm mịn láng giềng tuyến tính. SimGCL \cite{yu2022_simgcl} và LightGCL \cite{cai2023_lightgcl} đưa vào các hàm mục tiêu tự giám sát tương phản để chống lại độ thưa thớt của các cạnh đồ thị. Tuy nhiên, như được ghi nhận bởi Meehan cùng các cộng sự \cite{meehan2025_cold_popbias, meehan2026_semco}, các cơ chế lan truyền đồ thị hoạt động nghiêm ngặt trên các thành phần liên thông và thất bại thảm hại khi đánh giá các sản phẩm cold-start nghiêm ngặt hoàn toàn không có cạnh nối."*

#### Luận giải học thuật chuyên sâu:
* Đồ thị phụ thuộc vào các cạnh liên kết. Khi một sản phẩm mới tinh nhập kho (Zero-edge item), nó không có cạnh nối nào với bất kỳ người dùng nào, khiến mạng đồ thị mất hoàn toàn khả năng lan truyền tín hiệu.

---

### 3.6. Mục 2.6: Chiếu đặc trưng Nội dung, Xử lý Cold-start và Học Chuyển giao (Dòng 99 – 102)

#### Nguyên văn tiếng Anh:
> *"To recommend items devoid of interaction history, systems must leverage item-side metadata. DropoutNet \cite{volkovs2017_dropoutnet} trains networks to handle missing collaborative embeddings by stochastically dropping interaction inputs during training. ALDI \cite{huang2023_aldi} aligns collaborative and content spaces via multi-task distillation. Sentence-BERT \cite{reimers2019_sbert} provides dense semantic text representations, which AlphaRec \cite{sheng2025_alpharec} adapted for zero-shot ranking. Cross-domain transfer frameworks such as UniSRec \cite{hou2022_unisrec}, VQ-Rec \cite{hou2023_vqrec}, and UTGRec \cite{zheng2026_utgrec} demonstrate universal sequence transfer, though downstream domain adaptation remains sensitive to target catalog alignment."*

#### Bản dịch tiếng Việt sát nghĩa:
> *"Để gợi ý các sản phẩm hoàn toàn thiếu vắng lịch sử tương tác, các hệ thống bắt buộc phải tận dụng siêu dữ liệu phía sản phẩm. DropoutNet \cite{volkovs2017_dropoutnet} huấn luyện các mạng để xử lý việc thiếu hụt các vector nhúng cộng tác bằng cách loại bỏ ngẫu nhiên các đầu vào tương tác trong quá trình huấn luyện. ALDI \cite{huang2023_aldi} căn chỉnh các không gian cộng tác và không gian nội dung thông qua quá trình chưng cất đa tác vụ. Sentence-BERT \cite{reimers2019_sbert} cung cấp các biểu diễn văn bản ngữ nghĩa dày đặc, vốn đã được AlphaRec \cite{sheng2025_alpharec} điều chỉnh cho việc xếp hạng không mẫu (zero-shot). Các khung làm việc chuyển giao đa miền như UniSRec \cite{hou2022_unisrec}, VQ-Rec \cite{hou2023_vqrec}, và UTGRec \cite{zheng2026_utgrec} chứng minh khả năng chuyển giao chuỗi phổ quát, mặc dù sự thích ứng miền hạ nguồn vẫn rất nhạy cảm với việc căn chỉnh danh mục mục tiêu."*

#### Luận giải học thuật chuyên sâu:
* Để cứu vãn bài toán cold-start, hệ thống tích hợp vector ngữ nghĩa tiếng Việt của mô hình SBERT (768 chiều) từ mô tả và tên hàng hóa. Điều này cho phép Tháp Sản phẩm sinh vector biểu diễn ngay cả khi mặt hàng đó chưa có bất kỳ giao dịch mua nào.

---

## 4. BẢNG ĐỐI SÁNH TOÀN DIỆN 36 TRÍCH DẪN HỌC THUẬT (CITATION REGISTRY)

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
