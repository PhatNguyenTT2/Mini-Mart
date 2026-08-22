Có, clone một repo chuẩn để tham chiếu là hợp lý, nhưng không nên thay hoàn toàn ai-service bằng repo đó. Phương án mạnh nhất cho paper là:
Official repo + official dataset
        ↓ tái hiện kết quả gốc
Official repo + dataset v5 của dự án
        ↓ shared split/evaluator
Proposed Hybrid + cùng dataset v5
        ↓ shared split/evaluator
Proposed Hybrid + external dataset tương thích
        ↓ kiểm tra external validity
Đánh giá hai phương án
Phương án	Đánh giá
Đưa dataset khác vào ai-service	Khả thi nhưng chưa plug-and-play. Phải viết adapter chuyển dữ liệu sang Snapshot contract, temporal split, item/user mapping, basket/order, text embeddings và lineage. Dataset thiếu basket/co-purchase chỉ chạy được phiên bản Hybrid rút gọn.
Đưa dataset v5 vào pipeline benchmark chuẩn	Phù hợp hơn để xây bằng chứng tham chiếu. Baseline được chạy bằng implementation chuẩn; dataset v5 được export sang schema của repo; mọi model xuất score về một evaluator chung.


Phương án tối ưu
Không ép tất cả model dùng cùng training engine. Hãy dùng:
Repo chính thức để tái hiện baseline
Ví dụ:
RecBole cho BPR, LightGCN, SASRec, BERT4Rec.
BTBR/Mask-Swap-NNBR cho next-novel-basket.
UniSRec, AlphaRec.
SimGCL/XSimGCL/LightGCL từ các repository tác giả.
Phải pin commit và tái hiện trước trên dataset/protocol gốc.

Export dataset v5 thành dataset nghiên cứu trung lập
Không để dataset chỉ có thể đọc bởi ai-service. Cần một immutable export gồm:
user/item mappings;
train/VAL/TEST temporal splits;
events và purchase baskets;
item text/category/brand;
seen-item sets và eligible users;
lineage/hash.
Mỗi repo tham chiếu có một adapter đọc export này.

Train baseline chuẩn trên dataset v5
Giữ nguyên thuật toán/loss chính thức; chỉ thay data adapter. Đây là baseline hợp lệ trên dữ liệu dự án.

Train Hybrid trên cùng dataset
Có thể tiếp tục dùng ai-service, nhưng tốt hơn nên có thêm research adapter hoặc bản port mỏng của Hybrid trong benchmark framework. Hai implementation phải có parity test về logits/ranking trên fixture nhỏ.

Dùng một evaluator độc lập cho tất cả model
Dù model được train bằng RecBole, BTBR repo hay ai-service, chúng đều phải xuất score/top-k về cùng evaluator:
cùng eligible users;
cùng full catalog;
cùng seen masking;
cùng tie-break;
cùng HR@10/NDCG@10/GAUC;
cùng statistical test.
Đây là điểm quan trọng hơn việc tất cả model phải dùng chung training code.

Dataset bên ngoài nên dùng
Ta-Feng, Dunnhumby hoặc Instacart: phù hợp nhất để kiểm tra basket/co-purchase và full Hybrid.
Amazon-M2: phù hợp session/next-product và multilingual e-commerce.
ViEcomRec: phù hợp validation miền thương mại điện tử Việt Nam, nhưng có thể thiếu basket/rule signal.
Tenrec: phù hợp multi-behavior, nhưng không đặc thù tiếng Việt.
Nếu dataset thiếu basket/co-purchase, chỉ được gọi kết quả là reduced-method ablation, không phải replication của full Hybrid.
Kết luận
Lựa chọn tối ưu là dual-pipeline, shared-evaluator:
Repo chuẩn giữ vai trò baseline/reference training.
ai-service giữ vai trò proposed model và production implementation.
Dataset v5 được export trung lập cho cả hai.
Một evaluator độc lập chấm tất cả outputs.
Sau đó chạy thêm ít nhất một public external dataset tương thích.
Không hợp lệ nếu so:
Baseline trên dataset/protocol gốc
vs.
Hybrid trên dataset v5/protocol riêng
Chỉ có thể chứng minh ưu thế khi baseline nguyên bản và Hybrid đều được train/evaluate trên cùng dataset, split, candidate universe và evaluator.