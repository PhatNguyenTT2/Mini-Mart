# Lộ Trình Chi Tiết: Viết Paper với PaperOrchestra (Native Google AI Studio Pipeline)

> **Mục tiêu:** Sử dụng PaperOrchestra + **Google AI Studio API Key Native** (không qua Local Proxy) để tự động sinh bản thảo LaTeX/PDF chuẩn IEEE cho đề tài *"Hybrid Cascade Ranking Recommender System: Wide (Apriori) + Deep (Two-Tower with SBERT)"*

---

## Tổng Quan Lộ Trình

```mermaid
graph LR
    A["Phase 1:<br/>Cấu Hình<br/>API Key"] --> B["Phase 2:<br/>Raw Materials<br/>(✅ DONE)"]
    B --> C["Phase 3:<br/>IEEE Template<br/>(✅ DONE)"]
    C --> D["Phase 4:<br/>Phục Hồi Code<br/>Literature Agent"]
    D --> E["Phase 5:<br/>Chạy<br/>PaperOrchestra"]
    E --> F["Phase 6:<br/>Hậu Xử Lý<br/>& Fact-Check"]
```

---

## Phase 1: Thiết Lập Môi Trường & Cấu Hình Khóa API (Critical)

> [!WARNING]
> Bước này **THAY THẾ HOÀN TOÀN** cấu hình Local API Gateway port 9000 trước đó.

| Bước | Hành động | File cụ thể | Trạng thái |
|------|-----------|-------------|------------|
| 1.1 | Cấu hình `GEMINI_API_KEY` trong `.env` (xóa `OPENAI_BASE_URL`) | [.env](file:///e:/UIT/cv/backend/paper-orchestra/.env) | ⏳ Pending |
| 1.2 | Đảm bảo `openai_utils.py` **không còn** `base_url` routing | [openai_utils.py](file:///e:/UIT/cv/backend/paper-orchestra/utils/openai_utils.py) | ✅ Done (User đã sửa) |
| 1.3 | Cài đặt SDK: `pip install google-genai` | Terminal | ⏳ Pending |

**Chi tiết `.env` mới:**
```env
GEMINI_API_KEY=AIzaSyDZbbMdKpA82kM8L383wfbdHcp6XlA9np0
# XÓA OPENAI_BASE_URL — không dùng Local Proxy nữa
```

---

## Phase 2: Raw Materials (Nguyên Liệu Đầu Vào) ✅ ĐÃ HOÀN THÀNH

Tất cả nguyên liệu đã sẵn sàng:

| File | Vị trí | Trạng thái |
|------|--------|------------|
| `idea_sparse.md` | [paper/raw_materials/](file:///e:/UIT/cv/backend/paper/raw_materials/idea_sparse.md) | ✅ Done (English, IEEE format) |
| `experimental_log.md` | [paper/raw_materials/](file:///e:/UIT/cv/backend/paper/raw_materials/experimental_log.md) | ✅ Done (7-Way real data) |
| `architecture_overview.tex` | [paper/raw_materials/figures/](file:///e:/UIT/cv/backend/paper/raw_materials/figures/architecture_overview.tex) | ✅ Done (TikZ) |
| `latency_comparison.png` | [paper/raw_materials/figures/](file:///e:/UIT/cv/backend/paper/raw_materials/figures/latency_comparison.png) | ✅ Done (300 DPI) |
| `performance_ablation.png` | [paper/raw_materials/figures/](file:///e:/UIT/cv/backend/paper/raw_materials/figures/performance_ablation.png) | ✅ Done (300 DPI) |
| `info.json` | [paper/raw_materials/figures/](file:///e:/UIT/cv/backend/paper/raw_materials/figures/info.json) | ✅ Done |

> [!IMPORTANT]
> Cần copy toàn bộ thư mục `paper/raw_materials/` vào `paper-orchestra/raw_materials/` trước khi chạy CLI.

---

## Phase 3: IEEE LaTeX Template ✅ ĐÃ HOÀN THÀNH

| File | Trạng thái |
|------|------------|
| `templates/ieee/template.tex` | ✅ Done |
| `templates/ieee/guidelines.md` | ✅ Done |
| `templates/ieee/IEEEtran.cls` | ✅ Done |
| `templates/ieee/IEEEtran.bst` | ✅ Done |
| `templates/ieee/references.bib` | ✅ Done |

---

## Phase 4: Phục Hồi Code Cho Literature Agent

> [!IMPORTANT]
> Vì chuyển sang API Key chính chủ Google AI Studio, **BẮT BUỘC GIỮ LẠI** `google_search_tool` trong Literature Agent (ngược lại với kế hoạch cũ đã xóa nó).

### 4.1. `literature_review_agent.py` — **GIỮ NGUYÊN** Google Search Tool
Đoạn code ở dòng 464-468 **phải được giữ nguyên**:
```python
response_dict = call_gemini_with_contents(
    model_name="gemini-1.5-pro",  # Dùng Pro cho chất lượng literature review
    contents=[prompt],
    generation_configs={
        "tools": [self.google_search_tool],  # BẮT BUỘC GIỮ LẠI
        "temperature": 0.1 if task.get("search_type") == "targeted" else 0.4,
    },
)
```

### 4.2. `llm_backend_utils.py` — **BỎ QUA** Patch Port 9000
**KHÔNG** thực hiện patch routing `gemini` → OpenAI SDK như kế hoạch cũ. Để hệ thống tự động sử dụng `call_gemini_with_contents` mặc định.

### 4.3. `autoraters/agent_review.py` — Kiểm tra routing
Nếu file này gọi trực tiếp `call_gemini_with_text_prompt`, giữ nguyên (vì giờ đây Gemini SDK sẽ hoạt động trực tiếp qua `GEMINI_API_KEY`).

---

## Phase 5: Kích Hoạt PaperOrchestra

### Bước 5.1: Cài đặt Dependencies
```powershell
cd e:\UIT\cv\backend\paper-orchestra
pip install google-genai
pip install -r requirements.txt
```

### Bước 5.2: Copy Raw Materials
```powershell
Copy-Item -Recurse -Force "e:\UIT\cv\backend\paper\raw_materials" "e:\UIT\cv\backend\paper-orchestra\raw_materials"
```

### Bước 5.3: Khởi chạy CLI
```powershell
cd e:\UIT\cv\backend\paper-orchestra
python paper_writing_cli.py `
  --raw_materials_dir ./raw_materials/ `
  --latex_template_dir ./templates/ieee/ `
  --output_dir ./paper_output_ieee/ `
  --writer_model_name gemini-1.5-flash `
  --reflection_model_name gemini-1.5-pro `
  --research_cutoff 2024-11 `
  --use_plotting true `
  --plotting_model_name gemini-1.5-flash
```

> **Mẹo:** `gemini-1.5-pro` cho `reflection_model` tăng chất lượng vòng lặp tự phản biện (AI Peer Reviewer).

### Bước 5.4: Theo dõi Output
| Output | Mô tả |
|--------|--------|
| `outline.json` | Dàn ý chi tiết do OutlineAgent sinh |
| `literature_agent_output/references.bib` | File BibTeX tự động |
| `literature_agent_output/citation_map.json` | Bản đồ trích dẫn |
| `raw_draft_paper.tex` | Bản nháp LaTeX thô |
| `content_refinement_workdir/` | Logs vòng lặp AI Peer Review |
| `final_paper.pdf` | **Bản thảo PDF hoàn chỉnh** |

---

## Phase 6: Hậu Xử Lý & Xác Thực Chéo (Fact-Checking)

### Bước 6.1: Kiểm tra `citation_map.json` & `references.bib`
Đối chiếu chéo 18 tài liệu nền tảng (Base papers). Nếu AI thiếu bài kinh điển Apriori/Two-Tower → bổ sung thủ công vào `.bib`.

### Bước 6.2: NotebookLM Fact-Checking
Upload bản PDF nháp + PDF nguồn → truy vấn xác thực công thức toán và biểu đồ.

### Bước 6.3: Biên dịch LaTeX lần cuối
Chỉnh sửa → `pdflatex` → Submit.

---

## Verification Plan

### Kiểm tra tự động
```powershell
# Test 1: Kiểm tra GEMINI_API_KEY hoạt động (thay thế test Local Proxy cũ)
python -c "import google.genai as genai; client = genai.Client(); print('SDK OK')"

# Test 2: Kiểm tra raw_materials/ đầy đủ
python -c "import os; d='raw_materials'; files=['idea_sparse.md','experimental_log.md','figures/info.json']; [print(f'{f}: {os.path.exists(os.path.join(d,f))}') for f in files]"

# Test 3: Dry-run CLI
python paper_writing_cli.py --help
```

### Kiểm tra thủ công
1. Mở `paper_output_ieee/final_paper.pdf` → xác nhận đúng format IEEE, đủ 6 sections.
2. Mở `citation_map.json` → xác nhận có ≥15 bài báo với abstract hợp lệ.
3. Mở `content_refinement_workdir/content_refinement_worklog.json` → xác nhận refinement score ≥6/10.
