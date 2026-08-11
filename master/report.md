# Báo cáo kiểm duyệt Full-Catalog Recommendation — chẩn đoán v3 và readiness v4

## Cập nhật thực thi benchmark v4 — 2026-08-11

```text
R1 OBSERVABILITY/GATES SOURCE: PASS
R2 DATABASE SEED/DATASET/RULE READINESS: PASS
R3 SOURCE CONTRACTS: PASS
R3 DIAGNOSTIC RUNS: PENDING SOURCE FREEZE
R4 LINEAGE/AUDIT/PROBES/AI-SERVICE/CUDA: PASS
BACKEND MONOREPO LEGACY JEST GATE: FAIL OUTSIDE R2 SCOPE
PRODUCTION TRAINING: BLOCKED
HYBRID VICTORY: NOT ESTABLISHED
```

Database seed canonical là `benchmark-v4-s42-7f40639b0d-ca692e71b3`, status
`ready`, gồm đúng 15,000 benchmark orders. Snapshot
`benchmark-v4-20260811-49b2cdb902b1` có 823,371 events, 5,000 users, 5,200
items và 250 cold items; audit trả `training_suitability_passed=true`.

RuleArtifact duy nhất đủ training capability là
`benchmark-v4-20260811-49b2cdb902b1-rules-v3-d7ba48f8b8b5` với semantics
`semantic-trap-purchase-v2`: 14,106 directed rules, 14,086 non-trap, 20
trap-anchored, 4,143 organic rule items, VAL context coverage
`4156/4975 = 0.8353768844221106` và novel-target alignment
`380/4975 = 0.07638190954773869`. Full epoch-1 scan trên 136,518 rows đạt
`rows_with_any_rule_rate=0.69097115398702`; in-batch/explicit candidate
density lần lượt là `0.0012234062155234186` và `0.0015117054161356011`.
Semantic readiness pass `10/10`; mỗi trap có 75 baskets, count 75 và lift 200.
Hai density này phải được theo dõi bằng Wide RMS/top-k impact trong R3; chúng
không tự chứng minh Hybrid thành công.

Incident audit: lần seed trước đã chạy qua logic reclaim cũ và xóa event lineage
trước đó khỏi database. Artifact local cũ vẫn audit-only nhưng không còn là một
database lineage hoàn chỉnh. Script mới kiểm tra run-ID collision trước mọi
mutation, chỉ đánh `failed` cho run còn `staging`, không xóa benchmark event/order
lineage và có regression tests. Không được dùng incident này để tuyên bố mọi
lineage lịch sử đã được bảo toàn.

Probe v4:

| Probe | GAUC | HR@10 | NDCG@10 |
|---|---:|---:|---:|
| Permutation | `0.497918259645826` | `0.005630404182585964` | `0.0008282526229445643` |
| Persona-only | `0.786681251542651` | `0.08083651719284134` | `0.013031762846767202` |
| ItemCF | `0.827843070099922` | `0.03317916750452443` | `0.0072545901348188965` |
| SBERT | `0.6514863054947796` | `0.05087472350693746` | `0.012887701021567116` |
| Apriori-only | `0.5141621087395152` | `0.07721697164689323` | `0.02820988600329229` |

Apriori-vs-Random đã vượt gate paired bootstrap: GAUC delta
`0.01624384909368924`, CI lower `0.01114156795970724`; NDCG delta
`0.027381633380347725`, CI lower `0.024328941012233856`.

Các số này thay thế probe v3 làm reference cho diagnostic v4. ItemCF GAUC và
SBERT NDCG không phải absolute early-stopping thresholds cho Deep; Hybrid chỉ
pass khi strengthened seven-gate matrix chứng minh dominance theo từng metric
với paired CI. R3 chưa chạy nên chưa có metric Deep/Hybrid v4 hợp lệ để kết luận.

Quality gate sau triển khai: Ruff/mypy pass, seed-product Node `9/9`, Python
`374 passed, 2 skipped`, branch coverage `88.64%`; sáu critical targets đều
pass. Root `backend npm test` còn đỏ ở các Jest suites Catalog/Chatbot có sẵn,
ngoài các file R2. CUDA smoke
`smoke-r4-readiness-20260811-2042` pass và không tạo release side effects.

Phần báo cáo benchmark v3 bên dưới được giữ làm bằng chứng chẩn đoán lịch sử,
không còn là lineage dùng cho campaign kế tiếp.

Ngày kiểm chứng: **2026-08-11**

Snapshot: **`benchmark-v3-20260810-9088b0f3`**

Snapshot SHA-256: **`1ffcebe7dbe4fe5275bd2108a71567038a8bcc52120fa26c126b3e2be3409494`**

Source baseline đã push trước khi cập nhật tài liệu: **`aed0ab5e9f7a9877f22330a439f615ede97afd76`**

## 1. Kết luận điều hành

Trạng thái hiện tại:

```text
DATA_AND_SOURCE_INTEGRITY: PASS
MODEL_QUALITY: FAIL
PRODUCTION_TRAINING_CAMPAIGN: BLOCKED
HYBRID_VICTORY: NOT ESTABLISHED
```

Không bắt đầu lại campaign ba seed với nguyên trạng config `v3.toml`/`v4.toml`.

Lý do dừng:

- Best Deep seed 42 chỉ đạt GAUC `0.689057408`, NDCG@10 `0.009063882`, HR@10 `0.044538493`.
- Best Hybrid seed 42 chỉ đạt GAUC `0.689152525`, NDCG@10 `0.009174782`, HR@10 `0.044941556`.
- Hybrid không đạt minimum release GAUC `0.75`.
- Hybrid thấp hơn ItemCF GAUC `0.822937404`.
- Hybrid best checkpoint thấp hơn SBERT ở cả NDCG@10 và HR@10.
- Hybrid gần như trùng Deep; Wide branch chưa tạo ảnh hưởng xếp hạng có ý nghĩa.

Hai run seed 42 trên được lưu trữ để chẩn đoán tại:

```text
ai-service/artifacts/_archive/
campaign-e57ecd5-cold-parity-blocked-20260811/
```

Đây là diagnostic evidence, không phải immutable Victory Matrix hoặc release evidence.

> Các số liệu lịch sử Hybrid GAUC `0.8507`, HR@10 `0.4940`, NDCG@10 `0.0644`
> thuộc dataset/pipeline cũ với khoảng 1,380 items. Không được dùng làm acceptance
> threshold trực tiếp cho benchmark v3 có 5,200 items.

## 2. Phân biệt ba tầng kiểm duyệt

Không được trộn lẫn data probe, training safety và model victory.

| Tầng | Mục đích | Pass có chứng minh Hybrid thành công không? |
|---|---|---:|
| Data/artifact readiness | Xác minh snapshot có tín hiệu, lineage và artifact hợp lệ | Không |
| Training safety | Dừng NaN/Inf hoặc mô hình tệ hơn random rõ rệt | Không |
| Single-seed/aggregate Victory Gates | Chứng minh Hybrid đạt chất lượng và thắng đối thủ | Có, nếu tất cả gate pass |

### 2.1. Training safety hiện hành

`training/stopping.py` đang thực thi:

1. Bất kỳ GAUC/NDCG/HR non-finite: `FAILED` ngay.
2. GAUC `< 0.50`: catastrophic `FAILED` ngay.
3. GAUC tăng hơn `1e-4`: lưu best checkpoint và reset patience.
4. GAUC nằm trong tie window: NDCG rồi HR chỉ dùng làm tie-break.
5. Patience `4`: dừng plateau.

GAUC `0.50` chỉ là **kill-switch an toàn**, không phải ngưỡng chất lượng chấp nhận.

### 2.2. Single-seed Victory Gates hiện hành

`evaluation/gates.py` hiện yêu cầu:

- Random GAUC nằm trong `[0.48, 0.52]` và CI chứa `0.5`.
- Hybrid GAUC `>= 0.75`.
- Hybrid HR@10 thắng competitor có HR cao nhất với paired CI lower `> 0`.
- Hybrid NDCG@10 thắng **Apriori-only** với paired CI lower `> 0`.
- Semantic traps `10/10`.
- Cold parity pass.

Hai khoảng trống quan trọng của contract hiện hành:

- GAUC chỉ có absolute floor `0.75`, chưa bắt buộc thắng ItemCF.
- NDCG chỉ so với Apriori, chưa bắt buộc thắng SBERT hoặc competitor NDCG mạnh nhất.

Vì vậy, pass source gate hiện tại chưa đủ để tuyên bố “Hybrid thắng mọi baseline”.

## 3. Audit snapshot và artifact

### 3.1. Snapshot audit

| Thông số | Kết quả |
|---|---:|
| Events | `823,371` |
| Users | `5,000` |
| Items | `5,200` |
| Cold items | `250` |
| Eligible VAL users | `4,962` |
| Audit status | **PASS** |

### 3.2. Probe parity

Tất cả probe dưới đây dùng cùng frozen organic VAL split, cùng seen-item masking,
deterministic ranking và metric implementation với neural evaluator.

| Probe | GAUC | HR@10 | NDCG@10 | Vai trò |
|---|---:|---:|---:|---|
| Label permutation | `0.501544873` | `0.006247481` | `0.001109681` | Random sanity |
| Popularity-only | `0.674616713` | `0.002015316` | `0.000383116` | Popularity signal |
| Persona-only | `0.782826951` | `0.076582023` | `0.012376735` | Persona/category signal |
| ItemCF | `0.822937404` | `0.032849657` | `0.006524864` | Co-occurrence signal |
| SBERT centroid | `0.652163809` | `0.049375252` | `0.014869867` | Semantic/top-k signal |
| Apriori-only | `0.499991265` | `0.002015316` | `0.000365922` | Current Wide rule signal |

Kết luận probe:

- Permutation gần `0.5`: evaluator không có label leakage rõ ràng.
- Persona và ItemCF có tín hiệu rất mạnh: dataset có khả năng học được.
- SBERT có NDCG@10 mạnh nhất trong các baseline release hiện có.
- Apriori-only gần random: RuleArtifact hợp lệ về cấu trúc nhưng không có coverage đủ rộng.

### 3.3. RuleArtifact

| Contract | Kết quả |
|---|---:|
| Full-stat RuleArtifact | **PASS** |
| Directed rules | `216` |
| Feature schema | `2.0.0` |
| `min_count` | `3` |
| `min_lift` | `1.0` |
| Legacy artifact | Training reject đúng contract |

`Full-stat PASS` chỉ chứng minh artifact đầy đủ arrays, dtype, checksum và statistics.
Nó không chứng minh Wide signal đủ mạnh cho training.

## 4. Trả lời trực tiếp về GAUC, NDCG@10 và HR@10

### 4.1. Deep và Hybrid có bắt buộc vượt ItemCF GAUC `0.8229` không?

**Theo source contract hiện tại: không.**

- Deep-only là control/ablation; chỉ bị catastrophic kill khi GAUC `< 0.50`.
- Hybrid có absolute release floor GAUC `0.75`.
- Chưa có paired GAUC dominance gate bắt Hybrid thắng ItemCF.

**Theo mục tiêu “Hybrid thắng các mô hình còn lại”: có, cần bổ sung gate.**

ItemCF và Hybrid được đánh giá trên cùng cohort và evaluator, nên `0.822937404` là
data-specific competitor hợp lệ, không phải một con số “chuẩn ngành” tùy ý.

Policy đề xuất để tuyên bố Hybrid victory:

```text
Hybrid GAUC >= 0.75
AND paired GAUC CI lower(Hybrid - strongest competitor) > 0
```

Deep không bắt buộc thắng ItemCF. Tuy nhiên Deep thấp hơn ItemCF là tín hiệu chẩn đoán
rằng neural retrieval chưa học được co-occurrence structure đang hiện diện trong data.

### 4.2. Hybrid/Deep NDCG@10 thấp hơn SBERT `0.01487` có chứng minh thất bại không?

**Nó chứng minh best release checkpoint thất bại về mục tiêu thắng baseline Top-10.**

Nó không tự chứng minh code bị corruption, vì:

- Tất cả metrics finite.
- Random sanity pass.
- GAUC có học và tăng từ khoảng `0.59` lên `0.689`.
- Epoch muộn có NDCG tăng trong khi GAUC giảm.

Nhưng không được tuyên bố Hybrid thành công khi best checkpoint có:

```text
Hybrid NDCG@10 = 0.009174782
SBERT NDCG@10  = 0.014869867
Delta          = -0.005695085
```

Current NDCG gate chỉ so Hybrid với Apriori `0.000365922`; gate này quá yếu để chứng
minh Hybrid thắng SBERT.

### 4.3. HR@10 nào được xem là chấp nhận?

Không dùng một “industry HR range” cố định. HR phụ thuộc catalog size, truth cardinality
và masking. Với benchmark v3, phải dùng paired comparison trên 4,962 eligible users.

Các mốc thực tế:

```text
Random HR@10       = 0.006247481
ItemCF HR@10       = 0.032849657
Hybrid best HR@10  = 0.044941556
SBERT HR@10        = 0.049375252
Persona HR@10      = 0.076582023
```

Current release gate so với strongest competitor trong seven-way comparison; với các
mean hiện có, SBERT đã cao hơn Hybrid. Candidate thấp hơn baseline về mean thì paired
CI lower không thể dương, do đó HR gate sẽ fail.

Persona-only hiện chỉ là data probe, chưa có trong release comparison. Nếu mục tiêu là
“thắng mọi baseline”, persona phải được đưa vào immutable evaluation artifact và strongest
competitor selection.

## 5. Evidence seed 42

### 5.1. Best checkpoints

| Variant | Best epoch | GAUC | HR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| Deep | `2` | `0.689057408` | `0.044538493` | `0.009063882` |
| Hybrid | `2` | `0.689152525` | `0.044941556` | `0.009174782` |

Hybrid minus Deep:

```text
GAUC delta    = +0.000095117
HR@10 delta   = +0.000403063
NDCG@10 delta = +0.000110900
```

Các delta quá nhỏ để chứng minh Wide tạo lợi ích có ý nghĩa thống kê.

### 5.2. Epoch cuối trước plateau

| Variant | Epoch | GAUC | HR@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| Deep | `6` | `0.651680653` | `0.054413543` | `0.014790777` |
| Hybrid | `6` | `0.651592196` | `0.055018138` | `0.014928121` |

Epoch 6 Hybrid vừa vượt SBERT NDCG về mean, nhưng GAUC giảm khoảng `0.03756` so với
best epoch và vẫn thấp hơn release floor `0.75`. Không được dùng epoch 6 thay best
checkpoint để che GAUC failure.

### 5.3. Quyết định

```text
Seed-42 model quality: FAIL
Train seeds 2027/31415: PROHIBITED
Aggregate VAL/TEST: NOT AUTHORIZED
Seal/export: NOT AUTHORIZED
```

## 6. Deep scan nguyên nhân

### Finding Q0 — Wide branch không có coverage đủ rộng

Bằng chứng:

```text
Directed rules                              = 216
VAL users có context với outgoing rule      = 461 / 4,962 = 9.2906%
Wide edges trên full VAL catalog pairs      = 2,234 / 25,802,400 = 0.008658%
Training in-batch rule-pair coverage        = 0.041681%
Training explicit-negative rule coverage   = 0.009318%
Training rows có ít nhất một rule           = 8.5414%
```

Tại Hybrid best checkpoint:

```text
Deep logit RMS   = 2.847416
Wide logit RMS   = 0.000533
Wide / Deep RMS  = 0.0187%
```

Hybrid và Deep ranking metrics trong cùng Hybrid model giống nhau đến gần machine
tolerance. Wide branch có gradient nhưng score quá hiếm và quá nhỏ để đổi ranking.

### Finding Q1 — Seed order baskets tạo rule quanh semantic traps, không tạo organic rule graph

`backend/docs/chatbot/seed-product/mock-orders.js` hiện:

- Chọn semantic trap với xác suất `0.45`.
- Sau đó fill basket bằng warm items chọn gần như uniform.
- Không tạo basket theo persona/category affinity hoặc repeated organic bundles.

Kết quả deep scan:

```text
100% (216/216) directed rules có ít nhất một endpoint thuộc semantic-trap products.
0/216 rules nối hai sản phẩm organic thông thường.
```

Vì vậy, data audit tổng quát pass nhưng dataset **không pass model-specific Wide
coverage readiness**. Đây là nguyên nhân chính khiến Hybrid de facto trở thành Deep-only.

### Finding Q2 — GAUC-primary checkpointing phơi bày trade-off, không phải lỗi patience

- Train loss giảm từ `3.7088` xuống khoảng `0.2505`.
- GAUC đạt đỉnh ở epoch 2 rồi giảm liên tục.
- HR/NDCG tiếp tục tăng tới epoch 6.
- Patience 4 dừng đúng contract.

Nhiều epoch hơn không phải hướng sửa chính. Model đang overfit/misaligned với GAUC trong
khi Top-10 cải thiện. Cần sửa representation/objective rồi mới đánh giá lại checkpoint policy.

### Finding Q3 — Deep tower học persona nhưng latent representation làm mất tín hiệu

Read-only checkpoint ablations:

| Ablation | GAUC | HR@10 | NDCG@10 | Diễn giải |
|---|---:|---:|---:|---|
| Full Deep | `0.689057` | `0.044538` | `0.009064` | Baseline neural |
| Không persona | `0.543582` | `0.013906` | `0.002193` | Persona là thiết yếu |
| Không user-ID | `0.691852` | `0.046755` | `0.009392` | User-ID overfit nhẹ |
| Không history | `0.678715` | `0.044538` | `0.008766` | History có ích cho GAUC |
| Persona-only neural | `0.679335` | `0.049778` | `0.009320` | Thấp hơn persona probe `0.782827` |
| Không item-ID residual | `0.681064` | `0.044135` | `0.009151` | Item-ID có ích nhẹ |
| Không SBERT | `0.665150` | `0.043128` | `0.008184` | SBERT có ích |
| Không category | `0.552185` | `0.029827` | `0.006437` | Category là thiết yếu |
| Không price | `0.707662` | `0.051794` | `0.010873` | Price branch đang gây hại |

Kết luận:

- Không có bằng chứng persona mapping bị sai.
- User-ID và price features đang làm giảm generalization.
- Category/persona signal tồn tại nhưng learned dot-product representation chưa bảo toàn
  được rule-based persona affinity mạnh của data generator.
- Cần retrain ablations; zero-out sau checkpoint chỉ là diagnosis, không phải model candidate.

### Finding Q4 — `rule_present_rate` instrumentation sai với sampled-softmax

`training/trainer.py` chỉ tăng `present_count/candidate_count` trong nhánh `TrainingBatch`.
Production config dùng `PurchaseBatch`, nên history ghi `rule_present_rate=0.0` dù Wide
rules thực tế xuất hiện trong một số batch.

Lỗi này không trực tiếp làm score sai, nhưng che mất nguyên nhân Wide coverage thấp và
phải được sửa trước training tiếp theo.

### Finding Q5 — Metric/cohort mismatch đã bị bác bỏ

Probes và paired baselines đều dùng:

- `prepare_split(snapshot, VAL)`;
- 4,962 eligible users;
- organic novel purchases;
- cùng seen masking;
- cùng deterministic ranking và GAUC/HR/NDCG helpers.

Do đó khoảng cách ItemCF/SBERT so với neural metrics là thật trên cùng evaluation
definition, không phải do so nhầm sampled evaluation với full-catalog evaluation.

## 7. Stop policy trước campaign tiếp theo

### Dừng ngay trong epoch

- Bất kỳ NaN/Inf ở logits, loss, gradients, parameters hoặc metrics.
- Validation GAUC `< 0.50`.
- Wide epoch 1 gradient không finite hoặc `<= 0` với Hybrid.
- Hard-negative cache không được cập nhật.

### Dừng sau Deep seed 42

Deep là control nên không bắt buộc thắng ItemCF. Tuy nhiên phải dừng để chẩn đoán nếu:

- GAUC không vượt random một cách rõ ràng;
- loss giảm nhưng VAL GAUC đạt đỉnh quá sớm rồi giảm;
- ablation mới không cải thiện so với Deep baseline đã lưu trữ.

### Dừng sau Hybrid seed 42

Không tạo seed 2027 nếu bất kỳ điều kiện sau fail:

```text
Hybrid GAUC >= 0.75
Hybrid GAUC paired CI lower > strongest GAUC competitor
Hybrid HR@10 paired CI lower > strongest HR competitor
Hybrid NDCG@10 paired CI lower > strongest NDCG competitor
Hybrid paired metrics improve over independent Deep
Semantic traps = 10/10
Cold parity = PASS
```

Các dominance conditions là contract mục tiêu cần được implement trước campaign mới.

## 8. Lộ trình codebase bắt buộc trước khi retrain

### Phase R1 — Sửa observability và gate contract

#### `ai-service/src/ai_service/training/trainer.py`

- Trong nhánh `PurchaseBatch`, cộng riêng:
  - `in_batch_rule_present/numel`;
  - `explicit_rule_present/numel`;
  - số training rows có ít nhất một rule.
- Không để `rule_present_rate=0` giả khi dùng sampled-softmax.
- Ghi diagnostics vào immutable epoch history.

#### `ai-service/src/ai_service/contracts.py`

- Mở rộng `EpochMetrics` bằng typed Wide coverage diagnostics.
- Mở rộng comparison/Victory evidence để chứa persona baseline và strongest competitor
  cho từng GAUC/HR/NDCG.
- Không dùng generic dictionary cho metric evidence.

#### `ai-service/src/ai_service/evaluation/baselines.py`

- Đưa persona-only scorer vào paired baseline evaluation.
- Giữ cùng `PreparedEvaluationSplit` và per-user arrays.
- Đổi tên seven-way contract nếu số baseline thay đổi; không giữ tên sai thực tế.

#### `ai-service/src/ai_service/evaluation/gates.py`

- Giữ absolute Hybrid GAUC floor `0.75`.
- Thêm paired GAUC dominance so với competitor GAUC mạnh nhất.
- Đổi NDCG gate từ Apriori-only sang strongest NDCG competitor.
- HR tiếp tục strongest competitor nhưng phải bao gồm persona.
- Mọi dominance gate require paired bootstrap CI lower `> 0`.

#### `ai-service/src/ai_service/evaluation/report.py`

- Bổ sung persona per-user HR/NDCG/GAUC vào exact NPZ schema.
- Bind revised comparison signature và immutable matrix hash.
- Reject artifact schema cũ; không compatibility shim.

#### `ai-service/src/ai_service/evaluation/release.py`

- Aggregate Hybrid-vs-Deep victory phải dùng positive paired CI, không chỉ negative
  guardrail nếu mục tiêu là tuyên bố Hybrid thắng Deep.
- Giữ absolute safety guardrails dưới dạng evidence riêng.

#### Tests validate Phase R1

- `tests/unit/test_trainer_contract.py`: sampled-softmax Wide coverage khác zero khi fixture có rule.
- `tests/unit/test_full_catalog_contract.py`: persona streaming/reference parity.
- `tests/unit/test_release_gate_contract.py`: strongest competitor khác nhau cho từng metric.
- `tests/unit/test_checkpoint_report_and_trap_contracts.py`: exact persona arrays và hash corruption.
- Gate phải fail khi Hybrid thắng Apriori nhưng thua SBERT NDCG.
- Gate phải fail khi Hybrid GAUC `0.76` nhưng thua ItemCF `0.82`.

### Phase R2 — Sửa seed Wide signal

#### `backend/docs/chatbot/seed-product/mock-orders.js`

- Không fill phần lớn basket bằng uniform warm items.
- Sinh organic baskets theo deterministic persona/category affinity và repeated bundle
  templates, tách khỏi semantic-trap fixtures.
- Giữ exact seed/reproducibility và temporal cutoff.

#### `backend/docs/chatbot/seed-product/populate-copurchase.js`

- Báo cáo riêng:
  - total directed rules;
  - non-trap directed rules;
  - distinct organic rule items;
  - context-user coverage;
  - full-catalog pair coverage.
- Không coi rule count tổng là đủ nếu mọi rule đều trap-anchored.

#### `backend/docs/chatbot/seed-product/seed-ml-benchmark.js`

- Fail seed validation nếu organic rule graph không đạt thresholds đã resolve.
- Reject dataset có `non_trap_directed_rules == 0`.
- Persist coverage evidence cùng benchmark run metadata.

#### `backend/docs/chatbot/seed-product/benchmark-spec.json`

- Thêm explicit, reviewed thresholds cho:
  - minimum non-trap directed rules;
  - minimum user-context rule coverage;
  - minimum distinct organic rule items.
- Threshold phải được xác lập bằng probe/ablation, không chọn tùy ý để làm gate xanh.

#### `ai-service/src/ai_service/data/rules.py`

- Bind coverage statistics vào RuleArtifact manifest/identity.
- `require_training_capability()` phải kiểm tra cả full statistics và model-specific
  coverage readiness.
- Artifact cũ tiếp tục audit-only; không overwrite.

#### Validate Phase R2

- Regenerate snapshot/rules với artifact IDs mới.
- Audit/probe parity lại từ đầu; reference values cũ không còn áp dụng cho dataset mới.
- Apriori GAUC/NDCG phải vượt random có ý nghĩa trên organic cohort.
- Wide rule coverage phải xuất hiện trong cả training candidates và VAL contexts.

### Phase R3 — Neural ablation, không sửa `v3.toml`/`v4.toml` tại chỗ

#### `ai-service/src/ai_service/config.py`

- Thêm typed ablation flags cho user-ID và price features nếu chưa có.
- Mỗi thay đổi phải đi vào training/comparison signatures phù hợp.

#### `ai-service/src/ai_service/models/user_tower.py`

- Thử control không user-ID hoặc tăng user-ID dropout bằng config mới.
- Không zero parameter sau checkpoint trong candidate chính thức.

#### `ai-service/src/ai_service/models/item_tower.py`

- Thử config không price embedding.
- Giữ category và SBERT vì ablation chứng minh hai nhánh có ích.
- Đo lại item-ID residual bằng retraining, không kết luận từ post-hoc zeroing.

#### `ai-service/configs/ablations/`

- Tạo file mới cho từng single-variable ablation.
- Không thay đổi frozen `v3.toml`/`v4.toml`.
- Mỗi config dùng run ID diagnostic riêng, không dùng production six-run IDs.

#### Validate Phase R3

Thứ tự:

```text
Deep no-price seed 42
→ Deep no-user-ID seed 42
→ Deep no-price/no-user-ID seed 42
→ chọn bằng full-catalog VAL GAUC/HR/NDCG
→ Hybrid với RuleArtifact organic-coverage mới
→ paired VAL gate
```

Chỉ config thắng baseline archived và đạt strengthened gates mới được promote thành
production campaign config.

### Phase R4 — Full readiness trước production campaign

Chạy:

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy src scripts
.\.venv\Scripts\python.exe -m pytest `
  --cov=ai_service --cov-branch --cov-fail-under=85 -q
```

Sau đó require:

- Critical-file coverage pass.
- Audit/probes/rules coverage pass trên lineage mới.
- Source commit clean và đã push.
- Production environment pass.
- Tất cả diagnostic run IDs tách khỏi production IDs.
- Không bắt đầu seed 2027 trước khi seed 42 strengthened Victory Matrix pass.

## 9. Acceptance matrix mới

| Gate | Điều kiện |
|---|---|
| Data integrity | Audit snapshot pass |
| Random sanity | GAUC `[0.48,0.52]`, CI chứa `0.5` |
| Rule integrity | Full-stat + checksum/schema pass |
| Rule usefulness | Non-trap organic coverage pass |
| Training safety | Finite; GAUC không dưới `0.50` |
| Hybrid absolute quality | GAUC `>=0.75` |
| GAUC victory | Paired CI lower > strongest competitor |
| HR victory | Paired CI lower > strongest competitor |
| NDCG victory | Paired CI lower > strongest competitor |
| Hybrid vs Deep | Positive paired evidence, không chỉ non-regression |
| Semantic/cold | `10/10` traps và cold parity pass |
| Multi-seed | Cả ba VAL, aggregate VAL/TEST pass |
| Release | Selected Hybrid sealed; bundle/parity/benchmark pass |

Không tuyên bố Hybrid thành công nếu thiếu bất kỳ dòng nào trong acceptance matrix.
