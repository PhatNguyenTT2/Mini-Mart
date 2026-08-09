# Báo cáo kiểm định chuyên sâu `ai-service`

**Ngày kiểm định:** 2026-08-09  
**Phạm vi:** `ai-service/`, artifact hiện có, tích hợp Chatbot/Compose/CI  
**Chuẩn đối chiếu:** `master-plan/audit-plan.md`, `master-plan/ai-service-remediation-plan.md`  
**Kết luận phát hành:** **BLOCKED — chưa sẵn sàng production**  
**Điểm sức khỏe:** **31/100**

## 1. Tóm tắt điều hành

Đường chạy production hiện tại là `ai-service/src/ai_service`, được Docker khởi động bằng `python -m ai_service.serving.app`. Đường này chưa được bộ 31 test hiện hữu kiểm tra: các test đó import các module legacy ở gốc như `config`, `data`, `models`, `training`, thay vì `ai_service.*`. Vì vậy kết quả `31 passed` không phải bằng chứng release cho container hiện tại.

Một bộ acceptance test production đã được bổ sung tại `ai-service/tests/acceptance/test_production_contracts.py`. Kết quả hiện tại là **13/13 failed**. Những lỗi này xác nhận các blocker về temporal/cold isolation, negative sampling, feature fallback, evaluator/baseline, sparse Apriori và serving contract.

Các điểm tích cực đã được đo độc lập:

- Checkpoint hiện có load strict vào model production.
- Ba ONNX tower và file hybrid hiện có đều qua `onnx.checker`.
- PyTorch–ONNX parity của user/item/wide tower và hybrid score đạt sai số tối đa dưới `1e-5`.
- Kernel hybrid `1 x 5,200` đạt p95 xấp xỉ `0.997 ms` trên máy kiểm định.

Tuy nhiên, các file ONNX không có lineage nhất quán với manifest/checkpoint/report; exporter hiện tại không tạo hybrid graph, checksum hybrid bị ghi bằng checksum wide layer, và `0.85 ms`/`0.42 ms` trong manifest/report là hằng số. API container không load hay chạy ONNX mà trả score dựa trên rule lookup; `/health` vẫn báo `onnx_ready=true` chỉ vì snapshot tồn tại.

### 1.1 Bảng điểm

| Miền kiểm định | Điểm | Tối đa | Nhận định |
|---|---:|---:|---|
| Data provenance, temporal, cold isolation | 8 | 20 | Có event contract nhưng split/cold/artifact lineage chưa đạt |
| Feature, Apriori, negative sampling | 5 | 15 | Có deterministic mock path nhưng fallback và cấu trúc rule sai contract |
| Model và training | 8 | 15 | Shape/L2 cơ bản tốt; thiếu fail-fast, reproducibility và checkpoint contract |
| Evaluation và baselines | 3 | 20 | Full-catalog tồn tại nhưng relevance, GAUC và 7-way comparison chưa đúng |
| ONNX, API và deployment | 6 | 20 | Parity kernel tốt; exporter/serving/readiness/container chưa production |
| CI, tests và reproducibility | 1 | 10 | Production path chưa được CI/test bảo vệ |
| **Tổng** | **31** | **100** | **BLOCKED** |

## 2. Ma trận kiểm thử tái hiện

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Compile production package | `.venv\\Scripts\\python.exe -m compileall -q src` | PASS |
| Legacy unit + ONNX tests | `.venv\\Scripts\\python.exe -m pytest tests/unit tests/test_onnx_serving.py -q` | **31 passed**, 15 ONNX warnings |
| Production acceptance contracts | `.venv\\Scripts\\python.exe -m pytest tests/acceptance/test_production_contracts.py -q` | **13 failed** |
| Production coverage | `.venv\\Scripts\\python.exe -m pytest tests/acceptance --cov=ai_service` | **61%**, dưới gate 85% |
| Ruff production source | `.venv\\Scripts\\ruff.exe check src --statistics` | **169 errors**, 137 auto-fixable |
| Ruff format | `.venv\\Scripts\\ruff.exe format --check src` | 18 file cần format |
| mypy production source | `.venv\\Scripts\\mypy.exe src` | **7 errors** trong 3 file |
| Dependency consistency | `.venv\\Scripts\\python.exe -m pip check` | PASS sau khi cài bổ sung ONNX dependencies |
| Docker build | `docker build -t ai-service-audit:local .` | PASS, khoảng **612 giây** |
| Docker runtime smoke | container 1 GiB, port 18000 | Start được; readiness sai và recommend không dùng ONNX |

`onnx` và `onnxscript` phải được cài thủ công để test exporter chạy, nhưng chưa được khai báo trong `ai-service/pyproject.toml:11-34`. Đây là lỗi dependency manifest, không phải điều kiện ngẫu nhiên của máy kiểm định.

## 3. Xác định source of truth

### 3.1 Hai code path đang cùng tồn tại

- **Production/Docker:** `ai-service/src/ai_service/**`.
- **Legacy:** `ai-service/config.py`, `ai-service/data/**`, `ai-service/models/**`, `ai-service/training/**`, `ai-service/evaluation/**`.

Dockerfile copy `src` và CMD vào package production (`ai-service/Dockerfile:1-22`). Trong khi đó test hiện hữu chủ yếu import đường legacy. Hai implementation có hành vi khác nhau; ví dụ production trainer đã bỏ fabricated GAUC, nhưng evaluator/baseline và serving vẫn chưa đạt contract.

### 3.2 Quyết định bắt buộc

Chỉ giữ `src/ai_service` làm authoritative package. Mọi test phải import `ai_service.*`; module legacy cần được xóa hoặc chuyển thành compatibility shim có cảnh báo deprecation, không được giữ một implementation thứ hai.

## 4. Kiểm định data pipeline và artifact

### 4.1 Nguồn PostgreSQL

`ai-service/src/ai_service/data/sources.py:31-99` đọc event-level source, là hướng đúng. Tuy nhiên:

- Product query chỉ lấy `id`, `name`, `unit_price`, `leaf_category_id`; thiếu vendor/category hierarchy theo feature contract.
- Order query tại `sources.py:75-81` chỉ lọc `status='delivered'`, thiếu `payment_status='paid'`, `store_id`/cutoff nhất quán và có rủi ro dùng sai cột thời gian.
- Connection không được đóng chắc chắn bằng context manager hoặc `finally` khi lỗi.

**Mức độ: CRITICAL.** Apriori mining từ order universe khác benchmark universe làm support/confidence/lift không thể so sánh hoặc tái hiện.

### 4.2 Temporal split

`ai-service/src/ai_service/data/snapshot.py:107-118` sort rồi cắt theo số dòng 80/10/10. Nếu nhiều event cùng timestamp nằm ở boundary, timestamp group bị chia; code sau đó ném `DataIntegrityError` thay vì chọn boundary theo timestamp group.

Contract cần đạt:

\[
\max(t_{train}) < \min(t_{val}) < \min(t_{test})
\]

và mọi event có cùng `event_ts` phải thuộc cùng một split. Boundary phải được lưu vào manifest, không suy lại theo row count ở mỗi run.

**Mức độ: CRITICAL.** Acceptance test `test_temporal_split_keeps_equal_timestamp_groups_together` đang fail.

### 4.3 Cold-start isolation

`snapshot.py:61-187` suy cold set bằng nhóm product ID lớn nhất thay vì đọc versioned manifest. Code chỉ kiểm tra cold không xuất hiện trong train/val; chưa kiểm tra:

- Đủ đúng 250 raw product IDs trong cold manifest.
- Mỗi cold SKU có ít nhất một purchase positive trong test.
- Cold SKU không nằm trong Apriori rules, negative pool và feature statistics train.
- Manifest hash được nối xuyên snapshot → rules → checkpoint → ONNX → report.

**Mức độ: CRITICAL.** Acceptance test về incomplete cold ground truth đang fail.

### 4.4 Synthetic fallback và provenance

- `ai-service/src/ai_service/training/pipeline.py:29-38` bắt mọi lỗi PostgreSQL rồi tự động chuyển sang synthetic.
- `ai-service/src/ai_service/data/snapshot.py:189-200` tự build synthetic nếu manifest không tồn tại.
- `snapshot.py:140-142` chỉ hash chuỗi count/source kind, không hash nội dung.
- `ai-service/src/ai_service/data/features.py:67-72` bắt mọi lỗi SBERT và đổi sang fake embeddings.

Trong production, các fallback này phải fail closed. Mock/synthetic chỉ được bật bằng CLI/config explicit như `--source synthetic` và `--embedding-source mock`; manifest phải ghi source kind, seed, input snapshot hash, model revision và output checksum.

**Mức độ: CRITICAL.** Hai acceptance tests về real-source fallback đang fail.

### 4.5 Artifact hiện có

`ai-service/artifacts/data/scaled-v1` trộn hai layout/generation:

- Layout production mới: `train_events.parquet`, `val_events.parquet`, `test_events.parquet`.
- Layout legacy: `splits/*`, mappings và cold files cũ.

Snapshot production mới ghi `source_kind=synthetic`, có 823,371 events, nhưng test split chỉ chứa 250 cold items. Đây không phải benchmark test hỗn hợp warm/cold có thể dùng để báo cáo HR/NDCG tổng thể.

Snapshot `main-production-snapshot` có temporal/cold invariants tốt hơn, nhưng loader production hiện tại không đọc được layout `splits/train.parquet`. Apriori artifact ở đó chỉ có **562 directed rules**, không phải 13,046. Artifact `scaled-v1` hiện tại chỉ có **8 directed rules**.

**Mức độ: CRITICAL.** Báo cáo 13,046 rules không có artifact lineage hỗ trợ.

## 5. Feature, rules và sampling

### 5.1 SBERT

`ai-service/src/ai_service/data/features.py:52-91` chỉ encode product name và fallback silently sang fake vector. Manifest chưa có model revision, input text/hash, mapping hash, dtype, normalization flag và device/runtime version.

Yêu cầu sửa:

1. Tách `RealSBERTEncoder` và `DeterministicMockEncoder` thành hai implementation explicit.
2. `source_kind=real` phải propagate exception; không catch-all.
3. Text template chuẩn hóa tối thiểu: name + leaf/root category + vendor/brand + normalized description.
4. Assert shape `[5200, 768]`, `float32`, finite và `||v_i||_2 = 1 ± 1e-5`.
5. Hash raw-ID mapping và ordered text input vào embedding manifest.

### 5.2 Apriori rule store

`ai-service/src/ai_service/data/rules.py:16-58` gọi là CSR nhưng thực tế lưu Python dictionary và lookup bằng loop. Mining tại `rules.py:61-118` dùng toàn bộ order baskets, không ràng buộc train cutoff. File NPZ là triplet list, không phải CSR/`torch.sparse`.

Các công thức phải dùng cùng một basket universe train-only:

\[
support(A,B)=\frac{c_{AB}}{N},\quad
confidence(A\to B)=\frac{c_{AB}}{c_A},\quad
lift(A\to B)=\frac{c_{AB}N}{c_Ac_B}
\]

Yêu cầu lưu `crow_indices`, `col_indices`, `values=log1p(lift)`, shape `[5200,5200]`; validate sorted indices, finite values và `cold ∩ rules = ∅`.

**Mức độ: HIGH.** Acceptance test sparse CSR đang fail.

### 5.3 Dynamic negative sampling 1:4

`ai-service/src/ai_service/data/dataset.py:60-183` hard-code 4 negatives và output width 5, không dùng `settings.negative_ratio`. Các exclusion positive/cold/duplicate đã tốt hơn legacy, nhưng vẫn thiếu:

- Cấu hình ratio động.
- Exhaustion guard khi candidate pool không đủ.
- Batch-aware/vectorized sampler.
- Guarantee deterministic theo global seed + epoch + worker + user/event.

Context hiện lấy event trước theo thứ tự, kể cả view và cùng timestamp. Contract đúng phải là purchase positive có `context_ts < target_ts`; sentinel phải riêng biệt, không trùng item index 0.

**Mức độ: HIGH.** Hai acceptance tests về ratio và strict-purchase context đang fail.

## 6. Model và training

### 6.1 Tensor contract

Các tower tại `ai-service/src/ai_service/models/user.py:20-65` và `models/item.py:20-78` có L2 normalization và dimension cơ bản đúng. Hybrid score tại `models/hybrid.py:17-61` dùng deep dot product theo temperature và cộng wide term.

Các thiếu sót:

- Persona embedding chỉ có row 0..7, thiếu row UNK riêng.
- Validator temperature chỉ kiểm tra `>0`; nên enforce `tau >= 1e-3`.
- Không assert input shape/dtype/range/finite tại public boundary.
- `WideLayer` tại `models/wide.py:18-54` có thể biến NaN thành zero qua mask, che lỗi upstream thay vì fail-fast.
- mypy báo return `Any` ở wide và hybrid model.

### 6.2 Trainer

Điểm tốt: production trainer có best-checkpoint reload và không còn fabricated GAUC.

Blocker tại `ai-service/src/ai_service/training/trainer.py:70-190`:

- `val_evaluator` vẫn optional và được tự tạo tại `trainer.py:77-79`, trong khi validation contract phải mandatory.
- Thiếu SBERT artifact trở thành zero matrix tại `trainer.py:85-90`.
- Không có finite checks cho logits/loss/gradients.
- Epoch loss average theo batch, không weighted theo số sample.
- Checkpoint ghi không atomic và chỉ chứa `state_dict`; thiếu optimizer/scheduler, RNG state, config hash, snapshot/embedding/rule hashes và metric state.
- Run directory cố định `artifacts/runs/main`, có thể ghi đè lineage.

**Mức độ: HIGH.** Acceptance test mandatory evaluator đang fail.

## 7. Evaluation và benchmark mechanics

### 7.1 Full-catalog protocol

`ai-service/src/ai_service/evaluation/full_catalog.py:80-221` chấm toàn bộ catalog, là hướng đúng. Tuy nhiên relevance hiện lấy mọi event type, không giới hạn novel test purchases. Split nhận string; typo rơi về train tại `full_catalog.py:115-121`.

Metric contract cần cố định:

- Candidate set: toàn bộ 5,200 SKU sau policy mask đã version hóa.
- Ground truth: purchase positives trong test, loại item đã thấy ở train/val nếu đo novel recommendation.
- HR@10: `1` nếu top-10 giao với ground truth, ngược lại `0`, sau đó mean theo eligible users.
- NDCG@10: gain trên top-10 chia cho IDCG được tính từ cùng ground-truth definition.
- GAUC: pairwise positive-vs-negative per user, weighted/mean policy phải ghi rõ.

Hiện `compute_user_auc` tại `full_catalog.py:32-37` tạo ma trận `P x N`, có thể gây memory spike. Dùng rank-sum/Mann–Whitney hoặc streaming comparison để giữ O(C log C) time và O(C) memory. `np.argsort(-scores)` tại dòng 184 cần stable tie policy.

### 7.2 Baselines

`ai-service/src/ai_service/evaluation/baselines.py:30-75` chỉ triển khai 5 biến thể, không đủ seven-way:

1. Proposed Hybrid.
2. Deep-only.
3. Wide-only.
4. Noisy Hybrid.
5. SBERT centroid.
6. Item-item CF.
7. Stateless Random.

Random hiện là model neural random-init, không phải scorer deterministic theo `(seed,user,item)`. Wide-only vẫn chạy deep path. Noisy Hybrid chưa có noise mechanism rõ. `rule_store=None` còn mang nghĩa auto-load, khiến ablation không explicit.

Artifact report hiện có Hybrid và Deep metrics giống hệt nhau; semantic trap chỉ tăng rank 1950 → 1949 nhưng được ghi “improved”, trong khi HR@10 vẫn bằng 0; cold HR/NDCG đều bằng 0 dù coverage ratio bằng 1.0. Những số này không đạt release gate.

**Mức độ: CRITICAL.** Ba acceptance tests về split enum, GAUC memory và seven-way baselines đang fail.

## 8. ONNX export, parity và latency

### 8.1 Kết quả đo độc lập

| Graph | Parity max abs | CPU ORT p95 |
|---|---:|---:|
| User tower | `8.94e-08` | `0.0467 ms` |
| Item tower, 7 items | `2.16e-07` | `0.0539 ms` |
| Wide layer | `3.73e-09` | `0.0303 ms` |
| Hybrid, `3 x 7` | `2.38e-07` | `0.0518 ms` |
| Hybrid, `1 x 256` | `9.54e-07` | `0.0787 ms` |
| Hybrid, `1 x 5200` | `9.54e-07` | `0.9965 ms` |

Parity đạt gate `<=1e-5`. Kernel full-catalog chỉ vừa dưới 1 ms trên máy kiểm định, và con số này **không** bao gồm feature lookup, tower preprocessing, HTTP, serialization hay concurrent load.

### 8.2 Lineage và exporter

`ai-service/src/ai_service/export/onnx.py:16-99` hiện chỉ export user/item/wide tower. Nó không tạo `hybrid_recommender.onnx`, nhưng artifact hiện có file đó. Manifest tại `export/onnx.py:91` ghi `onnx_recommender_checksum=w_cs`; `latency_p95_ms=0.85` tại dòng 95 là hằng số.

Thời điểm file trong `artifacts/runs/main` cho thấy checkpoint, tower ONNX, manifest, hybrid ONNX và report không thuộc một atomic run. External `.onnx.data` chưa được checksum/package. Vì vậy parity tốt của từng file không chứng minh đúng checkpoint đã chọn hoặc đúng artifact đã deploy.

Yêu cầu exporter:

1. Reload best checkpoint bằng strict load.
2. Export một hybrid graph authoritative với dynamic `[B,C]` axes.
3. Package mọi external data file.
4. Chạy ONNX checker, finite checks và parity trên `[1,1]`, `[3,7]`, `[1,256]`, `[1,5200]`.
5. Warm-up rồi đo p50/p95/p99 bằng fixed ORT provider/thread settings.
6. Ghi SHA-256 của checkpoint, snapshot, embeddings, rules, ONNX graph/data và benchmark environment vào một immutable manifest.
7. Fail export nếu parity/latency gate không đạt; không ghi hằng số.

## 9. FastAPI, Docker, Chatbot và CI

### 9.1 API không chạy model

`ai-service/src/ai_service/serving/app.py:14-92` chỉ load snapshot/rules. `/recommend` trả `0.5 + rule lookup`, không tạo ORT session, không gọi tower/hybrid graph và bỏ qua user/persona/store trong scoring.

`/health` tại `app.py:33-39` đặt `onnx_ready = snapshot is not None`. Trong smoke test container, health trả HTTP 200 và `onnx_ready=true` dù không có model artifact của ứng dụng. Hai request với user/store/persona khác hẳn nhau trả cùng danh sách score `0.5`.

Schema tại `ai-service/src/ai_service/serving/schemas.py:8` mặc định `store_id=1`; đây là fail-open multi-tenant. `store_id` phải bắt buộc, được truyền xuyên Chatbot → AI client → API → artifact bundle/store-scoped policy.

### 9.2 Docker

Image build thành công nhưng:

- Kích thước **3,182,049,466 bytes** (~3.18 GB).
- Build khoảng 612 giây.
- Chạy bằng root.
- Không có image-level `HEALTHCHECK`.
- Dockerfile không copy/mount artifact production.
- Install kéo GPU PyTorch/CUDA/cuDNN/NCCL/Triton dù serving mục tiêu CPU ORT.
- Runtime dùng khoảng 354 MiB sau khi tự sinh synthetic snapshot.

`ai-service/src/ai_service/config.py:10-15` tính `SERVICE_DIR` từ vị trí package. Trong wheel/container, nó trở thành `/usr/local/lib/python3.11`, khiến synthetic artifacts được ghi dưới thư mục Python installation. Path phải đến từ required environment variable hoặc application working directory, không suy từ installed package path.

### 9.3 Chatbot và Compose

`backend/services/chatbot/src/services/ai.client.js:48-83` không nhận/gửi `store_id`; caller tại `backend/services/chatbot/src/services/hybrid.service.js:52-57` cũng không truyền store. Trong khi Compose đã có `AI_SERVICE_URL` (`backend/docker-compose.yml:232`) và service block (`backend/docker-compose.yml:270-272`), nó không mount immutable model bundle hoặc cấu hình DB/artifact production đầy đủ.

### 9.4 CI

`.github/workflows/ci.yml:3-40` không có path trigger/job cho `ai-service`. Không có gate production tests, coverage, Ruff, mypy, ONNX parity, Docker smoke hoặc artifact validation.

**Mức độ: CRITICAL.** Serving hiện “healthy” nhưng không phục vụ recommender model.

## 10. Danh sách lỗ hổng theo mức độ

### CRITICAL

| ID | Vị trí | Lỗi | Sửa bắt buộc |
|---|---|---|---|
| C-01 | `tests/**`, `Dockerfile:1-22` | Test xanh trên legacy path, Docker chạy production path | Chuyển toàn bộ test sang `ai_service.*`; loại implementation legacy |
| C-02 | `data/snapshot.py:107-142` | Row slicing có thể cắt cùng timestamp; checksum giả | Group-aware boundaries; content SHA-256 + frozen cutoffs |
| C-03 | `data/snapshot.py:61-187` | Cold set suy từ ID; thiếu test GT/rules isolation | Versioned cold manifest và bất biến end-to-end |
| C-04 | `training/pipeline.py:29-38`, `data/features.py:67-72` | Real source/SBERT silently fallback mock | Explicit mode; production fail closed |
| C-05 | `evaluation/full_catalog.py:115-205` | Relevance/split/GAUC chưa đúng contract | Typed split, purchase ground truth, rank-sum GAUC, stable ties |
| C-06 | `evaluation/baselines.py:30-75` | Seven-way benchmark chưa tồn tại/ablation sai | 7 scorer độc lập, explicit rule mode, deterministic random |
| C-07 | `export/onnx.py:16-99` | Không export hybrid, checksum/latency hard-code | Unified export + measured parity/perf + immutable manifest |
| C-08 | `serving/app.py:14-92` | API không load/chạy ONNX; false readiness | ModelBundle singleton, `/live`, `/ready`, ORT scoring, fail startup |
| C-09 | `serving/schemas.py:8`, Chatbot client | `store_id` fail-open và không truyền xuyên service | Required positive store ID; propagate và test cross-tenant |
| C-10 | `artifacts/**` | Artifact/report nhiều lineage; rule count không khớp | Atomic run directories; reject orphan/mixed artifacts |

### HIGH

| ID | Vị trí | Lỗi | Sửa bắt buộc |
|---|---|---|---|
| H-01 | `data/rules.py:16-130` | Dict rules, non-train baskets, missing file thành empty store | CSR/torch.sparse, train cutoff, checksum, fail-fast |
| H-02 | `data/dataset.py:60-183` | Ratio hard-code; context không strict purchase | Dynamic ratio, exhaustion guard, strict-earlier purchase sentinel |
| H-03 | `training/trainer.py:70-190` | Evaluator optional; zero SBERT; checkpoint thiếu state/lineage | Mandatory evaluator; finite checks; atomic full checkpoint |
| H-04 | `data/sources.py:31-99` | Order universe/store/payment/close semantics chưa an toàn | Store-scoped paid+delivered query, train cutoff, safe connection lifecycle |
| H-05 | `Dockerfile:1-22` | 3.18 GB root image, GPU deps, không artifact/healthcheck | Multi-stage CPU serving image, non-root, immutable bundle, healthcheck |
| H-06 | `.github/workflows/ci.yml:3-40` | Không kiểm tra ai-service | Thêm Python/ONNX/Docker release gates |

### MEDIUM

| ID | Vị trí | Lỗi | Sửa bắt buộc |
|---|---|---|---|
| M-01 | `models/*.py` | Thiếu UNK persona, tau lower-bound, input/finite validation | Typed tensor validators và dedicated UNK row |
| M-02 | `pyproject.toml:11-34` | Thiếu `onnx`, `onnxscript`; chưa tách train/serve deps | Lock dependencies; separate optional train/export/serve groups |
| M-03 | `config.py:10-15` | Artifact path phụ thuộc vị trí installed package | Required absolute `AI_ARTIFACT_DIR`; read-only serving path |
| M-04 | `src/**` | Ruff 169, mypy 7, format 18 file | Chạy autofix có kiểm soát, sửa type errors và bật CI |

### LOW

| ID | Vị trí | Lỗi | Sửa đề xuất |
|---|---|---|---|
| L-01 | Reporting | “improved” dù rank ngoài top-10; latency hard-code | Report pass/fail theo gate và link raw measurement |
| L-02 | API observability | Thiếu `/metrics`, latency/error counters, model version | Prometheus metrics và structured logs không chứa PII |

## 11. Kế hoạch sửa mã nguồn theo release waves

### Wave 0 — Chuẩn hóa package và CI

- Chốt `src/ai_service` là source of truth.
- Di chuyển hoặc viết lại test imports; xóa implementation duplicate.
- Khóa dependencies và thêm `onnx`, `onnxscript`, CPU-only serving set.
- Gate: compile, Ruff, mypy, production tests và coverage `>=85%`.

### Wave 1 — Immutable data contract

- Thêm `ColdManifest`, `SplitBoundaries`, `SnapshotManifest` typed models.
- Query event/order bằng store, paid+delivered, frozen train cutoff.
- Split theo timestamp group, content hashes, no silent synthetic fallback.
- Gate: strict temporal, zero event overlap, exact 250 cold, đủ cold test purchase, zero cold train/val/rules.

### Wave 2 — Feature/rules/dataset

- Explicit real/mock encoder; full text schema và manifest.
- CSR train-only Apriori với formula verification.
- Dynamic 1:N negative sampler; strict purchase context và exhaustion error.
- Gate: deterministic checksum, finite normalized SBERT, sampler invariants.

### Wave 3 — Model/trainer

- Thêm input contract/UNK persona/tau guard/NaN checks.
- Mandatory full-catalog validation; atomic resumable checkpoints.
- Gate: deterministic small-run, best checkpoint reload, no fabricated metrics.

### Wave 4 — Evaluation

- Typed split/relevance/masking policy.
- Memory-bounded GAUC; stable tie policy.
- Implement đúng bảy baselines và semantic/cold evaluators.
- Gate: Random GAUC trong `0.50 ± 0.02`; trap 10/10 theo top-10 gate; cold metrics có ground truth hợp lệ.

### Wave 5 — Export và serving

- Unified hybrid ONNX export với complete lineage.
- Startup load immutable `ModelBundle`; fail readiness khi thiếu/mismatch artifact.
- Required `store_id`; batch bounds, timeout, concurrency/memory controls.
- Gate: parity `<=1e-5`, measured p95, two non-identical users có thể nhận score khác nhau, `/ready` phản ánh model thật.

### Wave 6 — Container và release evidence

- Multi-stage non-root CPU image, artifact mount/read-only, image healthcheck.
- Chatbot propagate store và có contract tests.
- CI build/smoke/load test rồi tạo signed evaluation report từ cùng run manifest.
- Gate: image/startup/RSS budgets được định nghĩa và đo trên hardware ghi rõ.

## 12. Release gates bắt buộc

Không phát hành nếu một trong các gate sau chưa đạt:

1. Không còn dual implementation không được test.
2. Production acceptance suite 100% pass; coverage `>=85%`; Ruff/mypy zero error.
3. Temporal boundaries strict và versioned.
4. Exact 250 cold items: zero train/val/rules, mỗi item có test purchase.
5. Real data/SBERT mode fail closed; không silent mock.
6. Seven-way benchmark đúng và artifact metrics được sinh từ cùng lineage.
7. ONNX parity `<=1e-5`; latency là số đo, không phải hằng số.
8. API thực sự chạy ONNX; `/ready` fail khi model/checksum thiếu.
9. Required `store_id` xuyên Chatbot/API/data policy.
10. Docker CPU/non-root/bounded; CI smoke test chính image phát hành.

## 13. Lệnh tái kiểm định sau khi sửa

```powershell
Set-Location E:\UIT\cv\backend\ai-service
.\.venv\Scripts\python.exe -m compileall -q src
.\.venv\Scripts\ruff.exe format --check src tests
.\.venv\Scripts\ruff.exe check src tests
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\python.exe -m pytest tests -q --cov=ai_service --cov-report=term-missing --cov-fail-under=85
.\.venv\Scripts\python.exe -m pytest tests\acceptance\test_production_contracts.py -q
docker build -t ai-service-release-candidate:local .
```

Sau build, smoke test phải kiểm tra ít nhất: non-root user, image size, startup time, `/live`, `/ready`, bundle checksum, hai recommendation requests khác user/store, RSS sau warm-up và p95 dưới tải đồng thời. Không chấp nhận log/manifest chứa latency mặc định.

## 14. Kết luận production readiness

`ai-service` hiện có nền móng model/ONNX khả dụng và parity tốt, nhưng chưa phải một production recommender hoàn chỉnh. Data provenance, evaluation semantics, artifact lineage và serving path đều có lỗi có thể làm metric sai hoặc tạo false-positive readiness. Kết luận chính thức là **NOT READY / BLOCK RELEASE** cho đến khi toàn bộ CRITICAL/HIGH findings được sửa và các release gates ở trên được chạy lại trên authoritative package cùng một immutable artifact lineage.

