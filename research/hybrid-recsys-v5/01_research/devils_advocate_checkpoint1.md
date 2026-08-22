# Devil's Advocate Report — Checkpoint 1

> Reviewed artifacts: `rq_brief.md`, `rq_estimand_matrix.md`, `methodology_blueprint.md`  
> Material Passport: `stage1a_v1` · single-model review (`ARS_CROSS_MODEL` unset)

## Verdict: PASS

Không có critical issue sau khi các sửa đổi scoping dưới đây đã được đưa trực tiếp vào Stage 1A artifacts. Verdict này chỉ cho phép chuyển sang Stage 1B; không mở quyền chạy TEST hoặc viết claims cuối.

## Critical Issues (Blocks Progression)

No critical issues identified.

## Major Issues

1. **Primary question từng gộp ba outcome và cho phép metric shopping**
   - **Type:** Scope / Method / Bias
   - **Location:** RQ1 và H1 ban đầu
   - **Problem:** Một RQ hỏi đồng thời HR, NDCG và GAUC không chỉ compound mà còn để ngỏ metric nào được ưu tiên khi kết quả mâu thuẫn.
   - **Impact:** Có thể chọn outcome thuận lợi sau TEST và làm claim “wins” không xác định.
   - **Recommendation:** Đã xử lý: `NDCG@10` là primary inferential estimand; H1 vẫn là conjunction bắt buộc cả ba CI lower `>0`.
   - **Status:** RESOLVED IN STAGE 1A ARTIFACTS.

2. **“Strongest baseline” có selection bias nếu chọn trên TEST**
   - **Type:** Method / Bias
   - **Location:** RQ1 comparator
   - **Problem:** Comparator tốt nhất thay đổi theo metric và có thể bị chọn hậu nghiệm.
   - **Impact:** Nominal paired CI không còn hợp lệ và exaggerate advantage.
   - **Recommendation:** Đã xử lý: chọn riêng theo metric bằng validation mean từ preregistered registry, lexicographic tie-break, khóa ID/config/checkpoint trước TEST; nếu vi phạm dùng simultaneous interval hoặc rerun đúng protocol.
   - **Status:** RESOLVED IN DESIGN; IMPLEMENTATION PENDING STAGE 1E.

3. **Generated v5 có thể structurally favor chính Hybrid**
   - **Type:** Construct / External validity
   - **Location:** Problem statement và contribution framing
   - **Problem:** Nếu generator tạo basket rules, semantic traps và item text phù hợp với Apriori/content branch, improvement có thể chỉ phản ánh generator–model alignment.
   - **Impact:** Positive v5 result không chứng minh architecture novelty hoặc real-world Vietnamese effectiveness.
   - **Recommendation:** Đã xử lý bằng explicit controlled-benchmark label, H3 mechanism test, distribution/provenance gate và H4 full-contract external validation. Claim bị giới hạn ở v5 nếu H4 fail/not tested.
   - **Status:** RESOLVED AS A CLAIM BOUNDARY; EMPIRICAL RISK REMAINS BY DESIGN.

4. **External validation có nguy cơ trở thành unfalsifiable**
   - **Type:** Scope / Method
   - **Location:** RQ4/H4
   - **Problem:** Chọn dataset sau khi xem compatibility/results hoặc gọi reduced model là full Hybrid có thể tạo một “replication” không nhất quán.
   - **Impact:** H4 có thể luôn được giải thích là pass bất kể data support.
   - **Recommendation:** Đã xử lý: audit compatibility trước run; full-contract external dataset mới test H4; otherwise `NOT_TESTED`; official và harmonized tables tách riêng; không pool raw metrics.
   - **Status:** RESOLVED IN DESIGN; DATASET SELECTION PENDING STAGE 1E.

5. **Cold-item “does not reduce” thiếu operational criterion**
   - **Type:** Method
   - **Location:** H2
   - **Problem:** Cụm “không giảm chất lượng” không xác định margin hoặc uncertainty rule.
   - **Impact:** Có thể tuyên bố preservation từ một point estimate gần 0 nhưng CI rộng.
   - **Recommendation:** Đã xử lý bảo thủ: lower bound của paired 95% CI cho cold-item NDCG Hybrid − Deep phải `>=0`, cộng semantic traps `10/10`; denominator bắt buộc.
   - **Status:** RESOLVED.

## Minor Issues

- RQ5 chưa có numerical runtime thresholds. Đây là block cho runtime experiment, không block Stage 1B; Stage 1E phải khóa trước profiling.
- Ba training seeds cho seed-level inference còn hạn chế. Phải báo từng seed và không che instability bằng aggregate.
- Exact finalist set cho common eligible-user intersection chưa khóa. Stage 1E phải version hóa trước aggregate inference.
- Novelty score chỉ provisional. Stage 1B phải kiểm chứng primary papers trước bất kỳ “first/new” wording nào.

## Observations

- Việc tách official reproduction khỏi harmonized comparison là điểm mạnh thiết kế, vì adapter validity và method superiority là hai loại bằng chứng khác nhau.
- RQ2/RQ3 biến “cold start” và “Apriori” thành cohort/ablation falsifiable thay vì marketing claims.
- Efficiency đặt sau accuracy gate tránh tối ưu deployment cho một model chưa có empirical value.

## Strongest Counter-Argument

> The benchmark was generated with explicit semantic and basket-rule structure that mirrors the proposed Hybrid's inductive biases; therefore, even a statistically stable advantage may demonstrate alignment with the data generator rather than a general recommendation advance.

Phản biện này không thể bị loại chỉ bằng internal statistics. Nó chỉ được giảm sức nặng bằng generator disclosure, real-data distribution audit, faithful baselines và full-contract external validation.

## What's Missing

- Stage 1B verified evidence cho novelty, architecture positioning và benchmark methodology.
- Stage 1E frozen adapter revisions/tolerances, tuning budget, finalist set, runtime gates và external dataset compatibility receipts.
- Institutional ethics/exempt determination nếu public human-derived interaction data được dùng.
- Target venue/year và official artifact/reporting rules.

## Stress Test Results

| Test | Result |
|---|---|
| Remove strongest source — does argument hold? | `NOT_APPLICABLE_YET`: Stage 1A chưa tạo source-based argument; phải rerun ở Checkpoint 2. |
| Flip the research question — is opposing view credible? | `YES`: Hybrid có thể không hơn faithful baseline hoặc Wide branch có thể không đóng góp. |
| Apply to different context — does finding generalize? | `NOT_ESTABLISHED`: H4 bắt buộc; v5 alone không đủ. |
| “So what?” — is significance justified? | `CONDITIONAL YES`: giá trị nằm ở fair/reproducible comparison và mechanism evidence, không ở raw score. |

## Frame-lock check

Premise bị chất vấn: “kiến trúc hiện có là contribution”. Stage 1A không chấp nhận premise này; architecture chỉ trở thành contribution nếu H1/H3 và external-boundary evidence cho phép. Nếu không, paper vẫn có thể đóng góp benchmark/protocol hoặc một negative result có thể tái lập.

