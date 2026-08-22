# Conference and Research-Integrity Guidelines

## 0. Trạng thái venue

```text
TARGET_VENUE             = NOT_SELECTED
TARGET_YEAR_TRACK        = NOT_SELECTED
OFFICIAL_CFP_VERIFIED    = NO
SUBMISSION_DEADLINE      = TBD
PAGE_LIMIT               = TBD
TEMPLATE                 = TBD
REVIEW_MODE              = TBD
GENERATIVE_AI_POLICY     = TBD
```

Không có căn cứ để giữ deadline `2026-08-01`, giới hạn 6–8 trang hoặc
`IEEEtran` như yêu cầu chính thức. Chúng đã bị loại. Không được suy ra literature
cutoff từ một deadline chưa có nguồn.

`workspace/final/paper.tex` là historical draft, không phải submission template
và không phải nguồn kết quả. Chỉ được tham khảo cách tổ chức LaTeX cũ; dataset,
citations, model claims, figures và tables trong đó phải được xây lại.
`inputs/template.tex` hiện cũng chỉ là IEEE placeholder; không được dùng để khởi
tạo submission cho tới khi target venue và official template đã được xác minh.

## 1. Authority order

Khi chọn venue, chỉ dùng nguồn theo thứ tự:

1. official conference website và Call for Papers của đúng year/track;
2. official author kit/template linked từ CFP;
3. official submission-system instructions;
4. publisher ethics, artifact và AI policies;
5. generic IEEE/ACM guidance chỉ khi CFP dẫn chiếu trực tiếp.

Blog, deadline aggregator, paper cũ và template của năm khác không phải nguồn có
thẩm quyền. Mỗi rule phải lưu URL, retrieval date và archived copy/hash nếu
license cho phép.

## 2. Venue intake form bắt buộc

Hoàn thành bảng này trước khi chỉnh `paper.tex`:

| Field | Verified value | Official source | Retrieved UTC |
|---|---|---|---|
| Venue / acronym | PENDING | PENDING | PENDING |
| Year and track | PENDING | PENDING | PENDING |
| Submission deadline + timezone | PENDING | PENDING | PENDING |
| Abstract deadline | PENDING | PENDING | PENDING |
| Paper page limit | PENDING | PENDING | PENDING |
| Reference-page policy | PENDING | PENDING | PENDING |
| Supplementary/material limit | PENDING | PENDING | PENDING |
| Double-/single-blind | PENDING | PENDING | PENDING |
| Anonymization rules | PENDING | PENDING | PENDING |
| Preprint policy | PENDING | PENDING | PENDING |
| Artifact/data/code policy | PENDING | PENDING | PENDING |
| Human-data/ethics requirements | PENDING | PENDING | PENDING |
| Generative-AI policy | PENDING | PENDING | PENDING |
| Citation/template style | PENDING | PENDING | PENDING |
| Conflict-of-interest policy | PENDING | PENDING | PENDING |

Nếu một field chưa xác minh, ghi `PENDING`; không tự điền “typical IEEE”.

## 3. Chọn loại submission phù hợp

Trước khi chọn track cần quyết định contribution thực sự:

- **methods/empirical paper:** phù hợp nếu trọng tâm là shared-protocol comparison
  và hybrid mechanism;
- **dataset/benchmark paper:** chỉ phù hợp nếu dataset có license phát hành,
  data card, provenance, privacy/ethics audit và reproducible construction;
- **systems/demo paper:** phù hợp nếu contribution chính là serving/runtime,
  nhưng accuracy vẫn cần benchmark trung thực;
- **short paper/workshop:** chỉ dùng khi scope/validation phù hợp, không dùng để
  né thiếu external benchmark.

Với behavior tổng hợp và catalog có nguồn bên ngoài, không chọn dataset track
trước khi legal/release audit hoàn thành.

## 4. Scientific acceptance gate trước paper drafting

### 4.1 Dataset disclosure

Paper phải nói rõ:

- catalog metadata tiếng Việt và provenance của nó;
- behavior được sinh deterministic, không phải log người dùng thật;
- 5,000 users là synthetic identities;
- 250-item cohort chỉ chứng minh cold-item;
- temporal boundaries, eligibility và candidate universe;
- distinct-cell density khác event-frequency density;
- khả năng/giới hạn phát hành data và code.

Cấm các cụm chưa có bằng chứng:

- “proprietary real-world Vietnamese user behavior”;
- “eliminates cold-start”;
- “guarantees zero leakage”;
- “state of the art”;
- “production-ready”;
- “sub-millisecond” nếu chưa có fixed-runner artifact.

### 4.2 Reference-compatible experiments

Không nộp paper nếu thiếu:

- reproduction của ít nhất một official baseline trên public dataset;
- harmonized comparison trên v5 với exact mandatory suite: BPR-MF, LightGCN,
  SASRec, BERT4Rec, BTBR, UniSRec, AlphaRec, SimGCL, XSimGCL và LightGCL;
- một public Vietnamese track nếu license/schema cho phép;
- một established external e-commerce track, ưu tiên Amazon-M2;
- exact split/candidate/masking/metric statement;
- equal declared tuning budget và method-faithful objectives;
- preregistered reproduction tolerance cho từng reference adapter;
- immutable baseline registry chọn trên validation và khóa model ID cho TEST;
- three-seed hierarchical seed/user statistical evidence.

Cross-paper raw metric không được dùng để tuyên bố superiority.

### 4.3 Results integrity

- Không copy metric từ Markdown hoặc console vào paper bằng tay.
- Table generator phải strict-load verified report/NPZ và ghi artifact SHA.
- Negative result và failed hypothesis phải được giữ.
- Không đổi threshold, exclusions hoặc primary metric sau khi xem TEST.
- Validation chọn model; TEST chỉ dùng một lần sau freeze.
- Performance claims cần paired confidence intervals, không chỉ best seed.
- TEST/aggregate code không được chọn lại strongest baseline sau khi thấy TEST.

## 5. Required paper structure

Cấu trúc cuối phụ thuộc venue, nhưng nội dung tối thiểu là:

1. **Introduction** — problem, Vietnamese context, comparability problem,
   research gap, conditional contributions.
2. **Related Work** — reproducible evaluation; sequential/graph/content/LLM;
   cold-item vs cold-user; Vietnamese resources.
3. **Dataset and Ethics** — construction, synthetic behavior, provenance,
   language/license/privacy, limitations.
4. **Task and Evaluation Protocol** — temporal split, novel truth, full catalog,
   metrics, statistical tests.
5. **Methods and Baselines** — official sources, adaptations, objectives and
   budget; proposed Hybrid only one entry trong comparison.
6. **Experiments** — internal + Vietnamese public + external e-commerce tracks,
   ablations and sensitivity.
7. **Results** — generated from artifacts, uncertainty and contradictions.
8. **Deployment/Efficiency** — only after verified bundle/runtime benchmark.
9. **Limitations and Threats to Validity** — synthetic behavior, transfer,
   catalog license, hardware and offline-to-online gap.
10. **Conclusion** — proportional to evidence; no claim beyond tested cohorts.

Nếu venue giới hạn trang, không được bỏ Dataset/Ethics hoặc Evaluation Protocol
để ưu tiên kiến trúc. Có thể chuyển engineering detail vào supplement nếu policy
cho phép.

## 6. Introduction quality checklist

- [ ] Không mở đầu bằng claim SOTA chưa chứng minh.
- [ ] Nêu recommendation setting cụ thể: temporal novel-purchase top-k.
- [ ] Phân biệt controlled benchmark và observed behavior.
- [ ] Trích dẫn ít nhất một work về reproducible metric protocol.
- [ ] Trích dẫn Vietnamese resources hiện có; không claim “no prior dataset”.
- [ ] Nêu cold-item scope; không trộn user cold-start.
- [ ] Nêu research questions có thể falsify.
- [ ] Contributions viết theo artifact thực tế, không theo kế hoạch.

## 7. Related Work quality checklist

- [ ] Có 10–15 primary recent sources 2022–2026, không nhồi source để đủ năm.
- [ ] Foundational baselines được cite riêng và không dùng làm novelty evidence.
- [ ] Mỗi citation đã mở primary paper/proceedings page.
- [ ] Official GitHub được cite cho implementation, không dùng làm efficacy proof.
- [ ] ViHoRec được đánh dấu 2026 preprint/concurrent work.
- [ ] Mỗi subsection kết thúc bằng unresolved gap liên quan trực tiếp tới RQ.
- [ ] Không có raw-number comparison giữa datasets/protocols.
- [ ] Contradictory evidence và compute limitations được nêu.

## 8. Citation and bibliography policy

- Ưu tiên DOI/proceedings/ACL/PMLR/NeurIPS/OpenReview pages.
- arXiv được phép cho preprint hoặc khi là author-hosted copy; ghi đúng status.
- Không cite ResearchGate, blog, Wikipedia hoặc Papers with Code nếu primary
  source có sẵn.
- Verify title, authors, venue, year và DOI trước khi thêm BibTeX.
- Chỉ cite official repository cho code revision/reproducibility.
- Literature search log phải ghi query, source, inclusion/exclusion và date.
- Các paper sau submission cutoff thật chỉ được xử lý theo policy của venue;
  không tự động gọi chúng là prior work.

## 9. AI-assisted research policy

Cho tới khi venue được chọn, áp dụng policy bảo thủ:

- con người chịu trách nhiệm cho mọi claim, citation, code và analysis;
- không đưa confidential/unpublished data vào external model/service;
- không dùng AI-generated citation nếu chưa mở và kiểm tra primary source;
- lưu provenance của search/synthesis và disclose AI use nếu venue yêu cầu;
- AI không được liệt kê là tác giả;
- policy chính thức của venue luôn chi phối submission. Safeguard nội bộ nghiêm
  ngặt hơn chỉ được giữ khi không xung đột với policy chính thức.

## 10. Reproducibility and artifact package

Submission artifact tối thiểu:

```text
environment lock / container digest
dataset card + immutable lineage
language/provenance/license receipt
split and evaluator implementation + tests
official baseline repository revisions and adapter patches
resolved configs and search spaces
run/checkpoint/evaluation manifests
per-user metric arrays
table/figure generation scripts
negative/failure log
bundle/runtime receipt when claimed
```

Nếu dataset không thể phát hành, cần mô tả access restriction và cung cấp public
external benchmark scripts đủ để kiểm tra phương pháp. “Code available later”
không thay thế artifact plan.

## 11. Formatting gate sau khi chọn venue

Chỉ sau khi intake form hoàn tất mới quyết định:

- `IEEEtran`, ACM `acmart` hay template khác;
- one/two column;
- page and reference limits;
- anonymous author block/repository;
- figure resolution, font size, accessibility và color rules;
- bibliography style;
- supplement/anonymized artifact layout.

Khi đó tạo LaTeX project mới hoặc migrate có kiểm soát. Không sửa trực tiếp
paper cũ rồi giữ lại các bảng/claim lịch sử.

## 12. Submission stop conditions

Dừng submission nếu một trong các điều kiện sau đúng:

- venue rule chưa được verify;
- model-result tables không trace được tới artifact;
- current method và reference baselines không chạy trên shared protocol;
- chỉ có controlled synthetic-behavior benchmark, nhưng paper claim real-world
  Vietnamese shopper superiority;
- cold-user claim chỉ dựa trên 250 cold items;
- public baseline reproduction fail hoặc bị bỏ mà không disclosure;
- dataset license/ethics/provenance chưa rõ;
- source/config/test changed sau experiment freeze mà runs không được invalidated;
- Hybrid không đạt preregistered gates nhưng paper vẫn gọi là successful.

## 13. Completion record

| Gate | Status |
|---|---|
| Venue selected and official rules verified | BLOCKED |
| Research design drafted | DRAFTED |
| Research design locked | BLOCKED |
| Reference adapters reproduced | BLOCKED |
| Dataset/language/license audit | BLOCKED |
| Experiments completed | NOT_STARTED |
| Result artifacts verified | NONE |
| Paper template selected | BLOCKED |
| Submission authorized | NO |
