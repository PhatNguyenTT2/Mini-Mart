# HỆ THỐNG TÀI NGUYÊN BÀI BÁO KHOA HỌC
## REPRODUCIBLE HYBRID RECOMMENDATION FOR VIETNAMESE RETAIL

**Đề tài:** Phát triển Hệ gợi ý Thông minh Lai cho Bán lẻ Đa Chi nhánh  
**Tác giả:** Nguyễn Trương Tiến Phát, Đỗ Minh Đức  
**Giảng viên hướng dẫn:** TS. Nguyễn Thị Xuân Hương  
**Đơn vị:** Khoa Công nghệ Phần mềm, Trường Đại học Công nghệ Thông tin, ĐHQG-HCM  

---

## 1. BẢN ĐỒ ĐIỀU HƯỚNG TÀI NGUYÊN (NAVIGATION MAP)

Toàn bộ tài nguyên bài báo, mã nguồn và hệ thống báo cáo phân tích học thuật được tổ chức theo cấu trúc chuyên nghiệp, phân tách mô-đun rõ ràng:

```
thesis/paper/
├── README.md                                       # [Tài liệu hiện tại] Bản đồ điều hướng toàn bộ thư mục
├── paper.pdf                                       # Bản in bài báo khoa học 10 trang chuẩn IEEE Article (Biên dịch sạch 0 lỗi)
├── paper.tex                                       # Mã nguồn LaTeX hoàn chỉnh của bài báo
├── refs.bib                                        # Danh mục 36 tài liệu tham khảo khoa học quốc tế uy tín
│
├── overview/                                       # THƯ MỤC 1: TỔNG QUAN BÀI BÁO & BÁO CÁO HƯỚNG DẪN
│   ├── advisor-paper-report.md                     # Báo cáo toàn diện phục vụ buổi làm việc với GVHD (TS. Nguyễn Thị Xuân Hương)
│   └── paper-executive-summary.md                  # Tóm tắt điều hành toàn bộ bài báo (Kiến trúc, Đóng góp, Kết quả)
│
├── intro-related-work/                             # THƯ MỤC 2: CHI TIẾT MỤC INTRODUCTION & RELATED WORK
│   └── deep-analysis-intro-related-work.md         # Bản dịch sát nghĩa tiếng Việt song hành + Luận giải chuyên sâu + 36 trích dẫn
│
└── methodology-results-conclusion/                 # THƯ MỤC 3: CHI TIẾT CÁC MỤC CÒN LẠI (SECTIONS 3 - 7)
    └── deep-analysis-methodology-results-conclusion.md # Bản dịch sát nghĩa + Tổng quan + Luận giải toán học, Bảng 1, Bảng 2 & Thảo luận
```

---

## 2. LIÊN KẾT NHANH ĐẾN CÁC TÀI LIỆU CHÍNH

### A. Bài báo Khoa học Xuất bản
* 📄 **[paper.pdf](file:///e:/UIT/cv/backend/thesis/paper/paper.pdf):** Bản in 10 trang bài báo chuẩn IEEE. Đã kiểm tra biên dịch đạt 0 lỗi, 0 overfull hboxes, đầy đủ công thức toán học và 2 bảng thực nghiệm chất lượng cao.
* 📝 **[paper.tex](file:///e:/UIT/cv/backend/thesis/paper/paper.tex):** Tệp mã nguồn LaTeX gốc tự chứa, không phụ thuộc gói ngoài bất thường.
* 📚 **[refs.bib](file:///e:/UIT/cv/backend/thesis/paper/refs.bib):** 36 trích dẫn học thuật từ các hội nghị hàng đầu (ACM RecSys, SIGIR, KDD, CIKM, WSDM, WWW, ICLR, AAAI, VLDB).

### B. Báo cáo Tổng quan & Báo cáo GVHD
* 📊 **[advisor-paper-report.md](file:///e:/UIT/cv/backend/thesis/paper/overview/advisor-paper-report.md):** Bản báo cáo hoàn chỉnh dành cho TS. Nguyễn Thị Xuân Hương. Phân tích chi tiết từng mục của bài báo, báo cáo kiểm toán xử lý triệt để 22 vị trí rò rỉ phiên bản nội bộ, bổ sung trích dẫn RecBole và đề xuất kế hoạch nộp bài.
* 📋 **[paper-executive-summary.md](file:///e:/UIT/cv/backend/thesis/paper/overview/paper-executive-summary.md):** Bản tóm tắt điều hành trực quan với sơ đồ khối kiến trúc Wide & Deep Two-Tower, 3 đóng góp khoa học chính và bảng kết quả thực nghiệm.

### C. Phân tích Học thuật Chuyên sâu từng Phần
* 🔍 **[deep-analysis-intro-related-work.md](file:///e:/UIT/cv/backend/thesis/paper/intro-related-work/deep-analysis-intro-related-work.md):** Phân tích chi tiết Section 1 (Introduction) và Section 2 (Related Work). Dịch sát nghĩa tiếng Việt song hành từng câu, giải thích cặn kẽ thuật ngữ, cơ sở lý thuyết, và cung cấp Bảng Đăng ký Trích dẫn đầy đủ 36 bài báo.
* 🔬 **[deep-analysis-methodology-results-conclusion.md](file:///e:/UIT/cv/backend/thesis/paper/methodology-results-conclusion/deep-analysis-methodology-results-conclusion.md):** Phân tích chi tiết toàn bộ các mục còn lại: Tóm tắt (Abstract), Phương pháp luận (Section 3), Thiết kế Thực nghiệm (Section 4), Kết quả Thực nghiệm Bảng 1 & Bảng 2 (Section 5), Thảo luận Giới hạn (Section 6) và Kết luận (Section 7).

---

## 3. HƯỚNG DẪN BIÊN DỊCH BÀI BÁO TỪ MÃ NGUỒN LATEX

Để biên dịch tệp [paper.tex](file:///e:/UIT/cv/backend/thesis/paper/paper.tex) sang [paper.pdf](file:///e:/UIT/cv/backend/thesis/paper/paper.pdf), thực hiện các lệnh chuẩn sau:

```bash
cd e:\UIT\cv\backend\thesis\paper
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```
*(Ghi chú: Lệnh chạy 3 lần nhằm đồng bộ đầy đủ các tham chiếu chéo Table, Equation và trích dẫn Bibliography).*
