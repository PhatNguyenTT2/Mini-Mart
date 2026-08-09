# Kế hoạch Audit Production cho Hybrid Recommender `ai-service`

## 1. Kết quả bàn giao và nguyên tắc bằng chứng

Tạo một báo cáo Markdown duy nhất, đúng sáu phần người dùng yêu cầu:

1. Executive Summary và health score 0–100.
2. Benchmark Evolution & Metric Discrepancy Analysis.
3. Mock & Seed Script Audit.
4. AI Pipeline & Model Audit.
5. Vulnerabilities & Fixes theo `CRITICAL/HIGH/MEDIUM/LOW`.
6. Final Production Readiness Assessment.

Thứ tự ưu tiên nguồn sự thật:

1. Code đang thực thi, schema và artifact có checksum.
2. Kết quả test/benchmark có thể tái hiện.
3. Manifest, checkpoint và report JSON.
4. Hai file walkthrough và experimental log.

Mỗi mệnh đề sẽ được gắn một trạng thái: `VERIFIED`, `CONTRADICTED`, `UNSUBSTANTIATED`, hoặc `NOT REPRODUCIBLE`. Không xem nội dung walkthrough là bằng chứng nếu không truy được về dữ liệu, checkpoint và phép đo tương ứng.

Báo cáo sẽ ghi nhận rõ các mâu thuẫn cần phân xử:

- `823,376` so với `823,371`; tổng ba split thực tế là `823,371`.
- Walkthrough ghi GAUC `0.8500`, trong khi artifact full-catalog ghi Hybrid GAUC `0.5056`.
- Report quảng bá `13,046` rules, trong khi artifact hiện tại chứa 562 directed rules.
- ONNX latency `0.42 ms` đang được truyền bằng hằng số, không phải phép đo.
- Pipeline dùng mock Gaussian embeddings nhưng manifest vẫn có thể mang tên SBERT thật.
- Artifact report, snapshot, checkpoint và ONNX có thời điểm tạo không cùng một lineage.

## 2. Ba luồng audit chính

### A. Benchmark và metric mechanics

- Xác nhận full-catalog evaluator thật sự tạo ma trận \(S=UV^\top/\tau\) kích thước `[B, 5200]` và không lấy negative mẫu lúc evaluation.
- Trình bày công thức chính xác:

\[
HR@K=\frac1{|U|}\sum_u \mathbf1[T_u^K\cap G_u\ne\varnothing]
\]

\[
E[HR@K]_{\text{random}}
=1-\frac{\binom{N_u-|G_u|}{K}}{\binom{N_u}{K}}
\]

\[
NDCG@10=\frac{\sum_{r\le10}\mathrm{rel}_r/\log_2(r+1)}
{\sum_{r=1}^{\min(|G_u|,10)}1/\log_2(r+1)}
\]

\[
AUC_u=\frac{\#(s^+>s^-)+0.5\#(s^+=s^-)}{|P_u||N_u|},
\qquad GAUC=\frac1{|U|}\sum_u AUC_u
\]

- Chỉ ra rằng `IDCG@10` đạt trần khoảng `4.54356` khi người dùng có từ 10 positives; nó không tiếp tục tăng vì có 100+ positives. NDCG `0.00318` chủ yếu phản ánh gần như không có relevant item ở top 10, phù hợp HR `0.0312`, không chỉ do “IDCG denominator lớn”.
- Không quy toàn bộ thay đổi HR/NDCG cho việc tăng 1,380 lên 5,200 SKUs vì số user, persona, mật độ, split policy, label semantics và model state đều thay đổi.
- Đánh giá `0.5324` và `0.5005` theo đúng ý nghĩa: kỳ vọng random GAUC là 0.5; `±0.02` là sanity band thực nghiệm, không phải theoretical exact bound. Random GAUC một mình không chứng minh zero leakage.
- Truy vết lỗi benchmark wiring: Random baseline không dùng seed, vẫn có thể auto-load Wide rules; Deep-only truyền `None` nhưng evaluator hiểu là “load rules”; harness “seven-way” hiện chỉ chạy bốn biến thể.
- Kiểm tra relevance policy: view và order hiện bị coi như positive tương đương; test chỉ mask train history thay vì train + validation history.
- Vì không có frozen prototype snapshot/checkpoint 1,380-SKU trong repo, so sánh lịch sử sẽ được ghi là observational. Mọi kết luận nhân quả cần một nested-catalog ablation giữ nguyên user, positives, scores và masking.

### B. Seed scripts và PostgreSQL

- Audit timestamp Jan-01 đến Aug-01, split cutoff thực tế, PRNG reproducibility, event cardinality và việc một aggregate row đang bị chuyển thành đúng một synthetic event.
- Chứng minh hoặc bác bỏ cold-start contract xuyên suốt interactions, orders, events, rules và evaluator. Yêu cầu một cold manifest dùng chung và các bất biến:

\[
C\cap Train=C\cap Val=C\cap Rules=\varnothing,\qquad C\subseteq Test
\]

- Kiểm tra tám persona ranges, Pareto/Zipf claim, Semantic Trap injection probabilities, PostgreSQL BIGINT string/number mismatch và duplicate handling.
- Kiểm tra Apriori trên cùng một eligible basket universe:

\[
support=\frac{c_{AB}}N,\quad
confidence(A\to B)=\frac{c_{AB}}{c_A},\quad
lift=\frac{c_{AB}N}{c_Ac_B}
\]

- Đối chiếu mining SQL và validator SQL về `store_id`, delivered/paid status, train cutoff và target alternatives.
- Audit transaction safety: global `TRUNCATE ... CASCADE`, delete-before-reseed, partial batch commits, session-level `SET default_transaction_read_only=off`, transaction-pooler behavior, TLS verification và runtime `pip install`.
- Không chạy các seed script có mutation. Nếu database hiện tại truy cập được, chỉ dùng transaction `READ ONLY`; nếu không, mọi claim về live DB sẽ được đánh dấu chưa kiểm chứng.

### C. `ai-service`, model và serving

- Xác minh nguồn snapshot là PostgreSQL hay synthetic; kiểm tra query/schema mismatch, silent fallback, mapping completeness, timestamp ties và checksum lineage.
- Audit negative sampler 1:4: negatives không được trùng positive, không được là known user positives, không trùng nhau và không chứa cold items. Kiểm tra việc `user_positive_sets`, `seed`, `event_type` và `interaction_weight` hiện có thực sự được dùng.
- Kiểm tra sentinel item `0`, vì internal product index 0 là hợp lệ nhưng đang đồng thời mang nghĩa “không có context”, khiến Wide rules của item đầu tiên bị vô hiệu.
- Xác nhận tensor contracts:

  - User tower: `[B] → [B,64]`.
  - Item tower: `[B,C,768] + [B,C] + [B,C] → [B,C,64]`.
  - Deep logits: `[B,C]`, \(UV/\tau\).
  - Wide input `[B,C,1]`, output `[B,C]`, và `WideLayer(0)=0`.

- Thử zero vector, NaN/Inf SBERT, NaN/negative lift, invalid category IDs, very-small temperature và AMP overflow. Phân biệt epsilon-protected L2 normalization với khả năng NaN truyền thẳng qua mạng.
- Audit trainer: metric validation giả lập, thiếu real evaluator, final-epoch model được export thay vì reload best checkpoint, thiếu finite-loss guard và random SBERT fallback.
- Audit `RuleStore`: artifact CSR NumPy hiện tại không phải `torch.sparse`; full-catalog Wide path vẫn lookup/scatter bằng Python theo user.
- Audit semantic-trap evaluator: anchor raw ID ánh xạ về internal index 0, missing-ID fallback về item 0, và Deep baseline hiện dùng một UNK-user vector chung thay vì anchor-to-item semantic similarity.
- Xác nhận serving gap: `service/api.py`, `service/schemas.py` và Dockerfile hiện không tồn tại.
- Phân tách ba phép đo:

  1. ONNX kernel latency.
  2. Feature lookup + reranking latency.
  3. FastAPI end-to-end p50/p95/p99 latency.

- ONNX acceptance: load đúng best checkpoint, package cả external `.onnx.data`, parity tối đa \(\le10^{-5}\) trên nhiều `[B,C]`, finite outputs, bounded RSS, provider/thread configuration cố định và p95 kernel dưới 1 ms trên phần cứng được ghi rõ.

Các diff đề xuất sẽ bao gồm các contract tối thiểu: versioned cold manifest; snapshot provenance fields; explicit `rule_mode=auto|enabled|disabled`; explicit relevance/masking policy; deterministic random scorer; SBERT `source_kind=real|mock`; checkpoint/artifact hashes; và FastAPI request/response/health schemas.

## 3. Cấu trúc finding, scoring và recommended diffs

Mỗi finding sẽ có:

- ID và severity.
- Exact absolute file path cùng line range của worktree hiện tại.
- Claim bị ảnh hưởng.
- Code/data evidence.
- Production hoặc benchmark impact.
- Lệnh tái hiện.
- Minimal unified diff đề xuất.
- Acceptance test sau khi sửa.
- Residual risk.

Health score được tính theo maturity 0–5 cho từng miền:

| Miền | Trọng số |
|---|---:|
| Data provenance, temporal và cold isolation | 25 |
| Metric và benchmark validity | 25 |
| Seed/DB correctness và safety | 20 |
| Model/training integrity | 15 |
| ONNX/API/deployment readiness | 15 |

\[
Score=\operatorname{round}\left(\sum_d weight_d\frac{maturity_d}{5}\right)
\]

Readiness bands:

- `85–100`: Ready, chỉ khi không còn Critical/High.
- `70–84`: Conditional.
- `50–69`: Not Ready.
- `<50`: Blocked.

Bất kỳ lỗi nào làm giả metric, gây cross-tenant data loss, vi phạm temporal/cold isolation, hoặc khiến service không deploy được sẽ là hard production blocker bất kể tổng điểm.

## 4. Verification matrix

Chạy và ghi nguyên trạng kết quả:

```powershell
cd E:\UIT\cv\backend\backend\docs\chatbot\seed-product
node --check seed-ml-events-v2.js
node --check mock-interactions-v2.js
node --check mock-orders-v2.js
node --check populate-copurchase-v2.js
```

```powershell
cd E:\UIT\cv\backend\ai-service
python -m pytest -q
python -m pytest tests/test_onnx_serving.py -q
python -m ruff check .
python -m mypy .
```

Bổ sung invariant tests cho:

- Strict temporal boundaries và không chia cùng timestamp qua hai split.
- Event-ID disjointness và mapping không có null.
- Cold isolation và đủ 250 cold test ground truths.
- 10,000 sampled candidate groups không có false negative/duplicate.
- Apriori recomputation khớp stored support/confidence/lift trong tolerance.
- Deterministic random GAUC qua nhiều seeds và confidence interval chứa 0.5.
- Hybrid/Deep-only thực sự đi qua hai code path khác nhau.
- Full-catalog candidate count đúng 5,200 và test masking gồm train + validation.
- Model shapes, L2 norms, finite gradients/logits và Wide zero mask.
- ONNX parity \(\le10^{-5}\), p50/p95/p99 latency và peak memory.

Các Node/Python syntax checks đã khả dụng; interpreter hiện tại thiếu `pytest`, `pandas` và `pyarrow`, nên claim “31/31 PASSED” sẽ không được xem là đã tái hiện độc lập. Audit không tự cài dependency; thiếu runtime tương thích sẽ được ghi rõ là verification limitation.

## 5. Giả định và production gates

- Audit áp dụng cho worktree hiện tại, bao gồm cả file modified/untracked; không chỉnh sửa code hay database.
- Cả `E:\UIT\cv\backend\inputs\walkthrough.md` và `E:\UIT\cv\backend\walkthrough.md` đều được audit riêng.
- Artifact hiện tại chỉ được chấp nhận nếu snapshot → SBERT/rules → checkpoint → ONNX → report có checksum và lineage nhất quán.
- “Real PostgreSQL”, “real SBERT”, “10/10 traps”, “zero leakage”, “0.42 ms” và “0.8500 GAUC” đều phải có bằng chứng đo được; tên file hoặc manifest label không đủ.
- Production chỉ được đánh giá Ready khi: temporal/cold invariants đạt; validator đúng 10/10 theo cùng SQL universe; full seven-way baselines chạy đúng; real validation/test metrics vượt gate; ONNX parity/latency được benchmark thật; và FastAPI/Docker serving path tồn tại với health, limits và memory controls.
