---
lane: L4
task_id: 019ffb38-af70-7f21-ab78-79f721273291
model: 5.6 Tera / XHigh
status: complete
captured_at: 2026-08-13
provenance: verbatim task final handoff
---

# L4 raw literature-search handoff

Đã sàng lọc 19 candidate, shortlist 12 nguồn. Không có nguồn nào được dùng để suy ra metric kỳ vọng hoặc chứng minh Hybrid thắng; H2 vẫn chỉ được kiểm định bằng artifact v5 đã khóa. Không chỉnh sửa file nào.

## SEARCH_LOG

- Mode: ARS `deep-research / lit-review`, giới hạn Phase 2 discovery + verification; không tạo synthesis/Introduction/Related Work.
- Thời điểm: 2026-08-13.
- Nguồn tra cứu: ACM/DOI, NeurIPS, PMLR, ACL Anthology, ICLR/OpenReview, IEEE DOI, và repository do tác giả/nhóm tác giả xác nhận.
- Query families: `cold-start item recommendation`, `content representation cold item`, `transferable sequential recommendation text`, `UniSRec`, `AlphaRec`, `SimGCL`, `XSimGCL`, `LightGCL`, `SBERT`, và `new-user elicitation`.
- Screening: 19 identities, với các preprint/published variants được gộp theo title/DOI; accepted 12, excluded 7.
- Tiêu chí include: paper kỹ thuật primary, venue/proceedings chính thức, liên quan trực tiếp cold-item/content/transfer/representation hoặc boundary cold-user; 2022–2026 ưu tiên, foundation chỉ khi cần.
- Giới hạn: identity/venue/DOI đã kiểm tra từ trang chính thức; không thực hiện full-text local acquisition, retraction-database check, hay Semantic Scholar-ID lookup.

Quy tắc dùng evidence:

- Architecture evidence: dùng để mô tả input, objective, và điều kiện adapter.
- Official-protocol result: chỉ dùng trong `T1_official_reference_reproduction`, không copy metric sang v5.
- Harmonized-v5/H2: chỉ sealed per-user result trên cohort cold-item v5 mới trả lời H2.

## ACCEPTED_SOURCES

Tất cả các nguồn dưới đây là `ARS evidence level VI` (primary technical study, field-relative) và `quality tier_1` (peer-reviewed venue/journal), trừ khi ghi khác. “Accepted” không đồng nghĩa “đủ điều kiện adapter READY”.

1. `L4-01` — Maksims Volkovs, Guangwei Yu, Tomi Poutanen (2017), *DropoutNet: Addressing Cold Start in Recommender Systems*, NeurIPS 30. [Official paper](https://papers.neurips.cc/paper_files/paper/2017/hash/dbd22ba3bd0df8f385bdac3e9f8be207-Abstract.html); [author repository](https://github.com/layer6ai-labs/DropoutNet).
2. `L4-02` — Xiaoyu Du, Xiang Wang, Xiangnan He, Zechao Li, Jinhui Tang, Tat-Seng Chua (2020), *How to Learn Item Representation for Cold-Start Multimedia Recommendation?*, ACM Multimedia 2020. DOI: [10.1145/3394171.3413628](https://doi.org/10.1145/3394171.3413628).
3. `L4-03` — Yinwei Wei, Xiang Wang, Qi Li, Liqiang Nie, Yan Li, Xuanping Li, Tat-Seng Chua (2021), *Contrastive Learning for Cold-Start Recommendation*, ACM Multimedia 2021. DOI: [10.1145/3474085.3475665](https://doi.org/10.1145/3474085.3475665); [official repository](https://github.com/iLearn-Lab/MM21-CLCRec).
4. `L4-04` — Feiran Huang, Zefan Wang, Xiao Huang, Yufeng Qian, Zhetao Li, Hao Chen (2023), *Aligning Distillation For Cold-start Item Recommendation*, SIGIR 2023, pp. 1147–1157. DOI: [10.1145/3539618.3591732](https://doi.org/10.1145/3539618.3591732). Official public code not located in this bounded search.
5. `L4-05` — Yupeng Hou, Shanlei Mu, Wayne Xin Zhao, Yaliang Li, Bolin Ding, Ji-Rong Wen (2022), *Towards Universal Sequence Representation Learning for Recommender Systems*, KDD 2022, pp. 585–593. DOI: [10.1145/3534678.3539381](https://doi.org/10.1145/3534678.3539381); [official repository](https://github.com/RUCAIBox/UniSRec).
6. `L4-06` — Yupeng Hou, Zhankui He, Julian McAuley, Wayne Xin Zhao (2023), *Learning Vector-Quantized Item Representation for Transferable Sequential Recommenders*, WWW 2023, pp. 1162–1171. DOI: [10.1145/3543507.3583434](https://doi.org/10.1145/3543507.3583434); [author-team repository](https://github.com/RUCAIBox/VQ-Rec).
7. `L4-07` — Leheng Sheng, An Zhang, Yi Zhang, Yuxin Chen, Xiang Wang, Tat-Seng Chua (2025), *Language Representations Can Be What Recommenders Need: Findings and Potentials*, ICLR 2025. [Official proceedings page](https://proceedings.iclr.cc/paper_files/paper/2025/hash/e4bab1843c8d5a69f5abfd0824593493-Abstract-Conference.html); [official repository](https://github.com/LehengTHU/AlphaRec).
8. `L4-08` — Nils Reimers, Iryna Gurevych (2019), *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*, EMNLP-IJCNLP 2019, pp. 3982–3992. DOI: [10.18653/v1/D19-1410](https://doi.org/10.18653/v1/D19-1410); [official paper](https://aclanthology.org/D19-1410/). Restricted to encoder/representation rationale only.
9. `L4-09` — Hieu Trung Nguyen, Duy Nguyen, Khoa Doan, Viet Anh Nguyen (2024), *Cold-start Recommendation by Personalized Embedding Region Elicitation*, UAI 2024, PMLR 244, pp. 2766–2786. [Official proceedings page](https://proceedings.mlr.press/v244/nguyen24a.html). Boundary source for new-user cold-start only.
10. `L4-10` — Junliang Yu, Hongzhi Yin, Xin Xia, Tong Chen, Lizhen Cui, Quoc Viet Hung Nguyen (2022), *Are Graph Augmentations Necessary?: Simple Graph Contrastive Learning for Recommendation*, SIGIR 2022, pp. 1294–1303. DOI: [10.1145/3477495.3531937](https://doi.org/10.1145/3477495.3531937); [author-maintained repository](https://github.com/Coder-Yu/QRec).
11. `L4-11` — Junliang Yu, Xin Xia, Tong Chen, Lizhen Cui, Nguyen Quoc Viet Hung, Hongzhi Yin (2024), *XSimGCL: Towards Extremely Simple Graph Contrastive Learning for Recommendation*, IEEE TKDE 36(2), pp. 913–926. DOI: [10.1109/TKDE.2023.3288135](https://doi.org/10.1109/TKDE.2023.3288135); [repository linked by paper](https://github.com/Coder-Yu/SELFRec).
12. `L4-12` — Xuheng Cai, Chao Huang, Lianghao Xia, Xubin Ren (2023), *LightGCL: Simple Yet Effective Graph Contrastive Learning for Recommendation*, ICLR 2023. [Official OpenReview record](https://openreview.net/forum?id=FKXVK9dyMM); [official repository](https://github.com/HKUDS/LightGCL).

## EXCLUDED_SOURCES

- `E01` — Xu Zhao et al. (2022), *Improving Item Cold-start Recommendation via Model-agnostic Conditional Variational Autoencoder*, SIGIR 2022, DOI [10.1145/3477495.3531902](https://doi.org/10.1145/3477495.3531902). Direct but redundant with the stronger complementary cold-item set; its limited-interaction/warm-up framing is not automatically the v5 completely-cold cohort.
- `E02` — Hao Chen et al. (2022), *Generative Adversarial Framework for Cold-Start Item Recommendation*, SIGIR 2022, DOI [10.1145/3477495.3531897](https://doi.org/10.1145/3477495.3531897). Valid primary paper, but excluded from shortlist for redundancy and adapter/compute expansion.
- `E03` — Jing Du et al. (2022), *Socially-aware Dual Contrastive Learning for Cold-Start Recommendation*, SIGIR 2022, DOI [10.1145/3477495.3531780](https://doi.org/10.1145/3477495.3531780). Exclude: cold-user plus social graph, not cold-item evidence.
- `E04` — Jiayi Liao et al. (2024), *LLaRA: Large Language-Recommendation Assistant*, SIGIR 2024, DOI [10.1145/3626772.3657690](https://doi.org/10.1145/3626772.3657690). Conditional compute-tier LLM comparator; no need for L4 claim boundary unless it is actually implemented.
- `E05` — Sein Kim et al. (2024), *Large Language Models meet Collaborative Filtering: An Efficient All-round LLM-based Recommender System*, KDD 2024, DOI [10.1145/3637528.3671931](https://doi.org/10.1145/3637528.3671931). Same reason as E04.
- `E06` — Wei Jin et al. (2023), *Amazon-M2: A Multilingual Multi-locale Shopping Session Dataset for Recommendation and Text Generation*, NeurIPS 2023 Datasets & Benchmarks. [Official paper](https://proceedings.neurips.cc/paper_files/paper/2023/hash/193df57a2366d032fb18dcac0698d09a-Abstract-Datasets_and_Benchmarks.html). Transfer/external-dataset ownership belongs to another lane; not evidence of cold-item efficacy.
- `E07` — Minh Hoang Nguyen (2026), *ViHoRec: A Quality-Controlled Vietnamese Hotel Recommendation Dataset and Cold-Start Benchmark*, [arXiv preprint](https://arxiv.org/abs/2607.12946). Exclude from peer-reviewed shortlist: concurrent preprint and short-history-user setting.

## UNRESOLVED

- MTPR, ALDI, and PERE: no author-official code repository confirmed in this bounded search.
- All repositories require commit/tag, license, dataset version, text preprocessing, encoder/tokenizer, and metric/candidate policy audits before any adapter is called faithful.
- Exact candidate sampling/full-catalog semantics of the literature experiments were not promoted into this report; they must be extracted from official full text before setting T1 reproduction tolerance.
- No source establishes a Vietnamese-language encoder choice or SBERT model revision suitable for the v5 catalog. SBERT is not recommender efficacy evidence.
- Retraction and complete author-conflict checks remain pending central bibliography audit.
- `ESCALATION_RECOMMENDED: NO`.

## CLAIM_SOURCE_CARDS

| Source(s) | Supports | Method/task/protocol | Metric semantics and limitation | RQ/H mapping |
|---|---|---|---|---|
| L4-01, L4-02, L4-03, L4-04 | Cold item means item-side behavior history is absent or inadequate; content can bridge missing collaborative representation. | Dropout simulation; MTPR dual/counterfactual item representations; CLCRec content–collaborative contrast; ALDI warm-to-cold distillation. | Paper-native offline results only. CLCRec explicitly reports cold-item Recall@10/NDCG@10; none supplies v5 full-catalog NDCG. | RQ2/H2 architecture and comparator rationale; not a pass criterion. |
| L4-05, L4-06 | Item text can be used for transferable sequential representations across domains/platforms. | UniSRec: text-aware universal sequence pretraining; VQ-Rec: text → discrete code → representation. | Candidate/split/metric semantics remain paper-native; VQ-Rec warns that direct text–representation binding can overemphasize text/domain gap. | RQ2 comparator eligibility; RQ4 adapter feasibility only. |
| L4-07 | Language representations can be projected/combined with CF components; title text may carry usable item signal. | AlphaRec uses language representations of item textual metadata with projection, graph convolution, and contrastive objective. | Does not prove every text encoder or Vietnamese title field has behavioral signal. | Conditional AlphaRec comparator; no direct H2 proof. |
| L4-08 | SBERT creates fixed semantic text embeddings usable for similarity/retrieval. | NLP sentence-embedding method, not a recommender. | No retail ranking, cold-item, or collaborative objective. | Encoder ablation/provenance only; cannot justify “SBERT solves cold item.” |
| L4-09 | New-user cold-start entails missing preference knowledge and requires elicitation. | Personalized rating elicitation after a new user arrives. | Explicitly user-side; cannot be transferred to cold-item evidence. | Negative boundary for H2 wording. |
| L4-10–L4-12 | Graph-contrastive methods are credible collaborative-only comparators for sparse interaction graphs. | Noise-based SimGCL/XSimGCL; SVD-derived global contrastive view in LightGCL. | Their sparse-graph results require interaction edges; they are not evidence that a zero-interaction item can be represented from text. | RQ1 comparator family; RQ2 secondary collaborative contrast only. |

## OVERLAP_FLAGS

- `L4 ↔ evaluation/reproducibility lane`: do not reuse any paper-native Recall/NDCG/HR as comparable metrics. Candidate universe, split, masking, and aggregation must remain in that lane’s contract.
- `L4 ↔ architecture/hybrid lane`: MTPR/DropoutNet only support cold-item representation design; they do not support an Apriori/Wide causal mechanism claim.
- `L4 ↔ external/Vietnamese-data lane`: Amazon-M2 and ViHoRec are dataset/transfer candidates, not accepted L4 efficacy evidence. Amazon-M2 needs an essential-signal audit before H4; ViHoRec remains a 2026 preprint and is short-history-user oriented.
- `L4 ↔ LLM lane`: LLaRA and A-LLMRec are conditional only. Excluding them for compute does not permit any “SOTA versus LLM recommender” claim.

## CENTRAL_REVIEW_ALERTS

1. `HIGH` — Define the v5 cold-item cohort independently of the literature: zero train interactions versus a bounded low-count definition cannot be chosen after TEST. Report item and eligible-user denominators.
2. `HIGH` — H2 wording must remain “cold item”; PERE, social cold-user work, and ViHoRec cannot substantiate a new-user/zero-history claim.
3. `HIGH` — SBERT can be cited only for semantic embedding construction. Replacing UniSRec/AlphaRec encoders with SBERT is a separately labelled ablation, never faithful reproduction.
4. `HIGH` — SimGCL/XSimGCL/LightGCL are strong collaborative controls but cannot establish content transfer to completely cold items.
5. `MEDIUM` — Cite XSimGCL as IEEE TKDE 36(2), 913–926 (2024); the DOI contains `2023` because of online publication and should not determine the bibliographic year.
6. `MEDIUM` — Amazon-M2’s repository metadata says “NeurIPS’22” and shows an inconsistent year; use the official NeurIPS 2023 record for publication metadata.
7. `MEDIUM` — Before Stage 1E, every accepted code source needs immutable revision, license, official protocol, reproduction target/tolerance, and text-encoder artifact receipt.

