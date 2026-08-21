# Stage 1E Rebaseline v2 — Dataset Exclusion and Hold Log

## Material Passport

| Field | Value |
|---|---|
| Lane | E2_reference_datasets |
| Skill/workflow | ars-codex:academic-research-suite v0.1.26; experiment-agent evidence-discovery and lock |
| Model | gpt-5.6-sol |
| Reasoning | xhigh |
| Access date | 2026-08-22 |
| Input manifest SHA-256 | 107299c026434366ed6ddb18f4ee6e25fd790d9799fd81c1c1e87871ed60744d |
| Verification state | UNVERIFIED until E4/E5 |
| RESULT_STATUS | NOT_RUN |
| ACCEPTED_RESULT_ROWS | 0 |
| TEST_SET_OPENED | NO |

REJECTED means the dataset cannot enter the current Stage 1E evidence contract on the available record. PENDING is a reversible hold with an explicit re-entry gate. SENSITIVITY_ONLY is not permission to claim full-contract compatibility. Nothing in this log authorizes acquisition or execution.

## Hard exclusions

| Dataset/artifact | Exclusion reason | Evidence and locator | Re-entry condition |
|---|---|---|---|
| Ta-Feng grocery dataset | No current canonical provider page, provider release/version, lawful access terms, published digest or dataset license was found. Original/author papers describe the transaction period and basket use but point to or rely on noncanonical copies. Hashing a mirror would establish byte identity only, not provenance or permission. | [IJCAI original paper, Section 5.1 dataset description and citation](https://www.ijcai.org/proceedings/2019/0389.pdf); [Mask-Swap original paper, Dataset and Evaluation Protocol](https://arxiv.org/abs/2308.01308); [Mask-Swap author repository, Ta-Feng command](https://github.com/liming-7/Mask-Swap-NNBR); [Reality Check author repository, Dataset/Preprocess](https://github.com/liming-7/A-Next-Basket-Recommendation-Reality-Check) | Produce a primary provider release or provider-authorized archival record, current applicable terms, canonical bytes/schema, and an immutable digest or E4-acquired SHA-256. |
| ViFoodRec | The official paper evaluates content similarity and rating prediction, not chronological next-item or basket recommendation. It reports 50,000 collected explicit ratings and approximately 180,000 after missing-value imputation; there are no timestamps, sessions or baskets. No dataset/repository license was located, and website-derived content/participant rights remain unresolved. Vietnamese language alone cannot establish compatibility. | [ACL Anthology archival record](https://aclanthology.org/2024.paclic-1.4/); [original paper, Dataset, Data Preprocessing, Models and Evaluation](https://aclanthology.org/2024.paclic-1.4.pdf); [author repository, README/Data and no observed license](https://github.com/QuocAn55/DS300) | Re-open only in a separately preregistered content/rating study after participant/source-content rights, immutable data version and non-imputed target semantics are explicitly approved. |

## Pending holds

| Dataset/artifact | Why it is not admitted now | Current primary evidence | Minimum re-entry gate |
|---|---|---|---|
| LightGCN processed Gowalla/Yelp2018/Amazon-book/LastFM pack | Exact author command is defensible, but raw-to-processed transformations, split/candidate semantics, per-source rights and immutable data release are not. Gowalla also creates location privacy risk. | [LightGCN author repository, Dataset/example/archive notice](https://github.com/gusye1234/LightGCN-PyTorch); [SNAP Gowalla provider page](https://snap.stanford.edu/data/loc-gowalla.html); [current Yelp provider page](https://business.yelp.com/data/resources/open-dataset/) | E4 commit/file hashes and full source lineage; E3 evaluator/split lock; E5 rights per dataset and location/privacy decision. |
| SELFRec Yelp2018 | Framework YAMLs are exact framework evidence, not original-model-author reference evidence. The bundled Yelp2018 version/provenance/rights are not bridged to a canonical provider release. | [SELFRec README](https://github.com/Coder-Yu/SELFRec); [config directory](https://github.com/Coder-Yu/SELFRec/tree/main/conf); [dataset directory](https://github.com/Coder-Yu/SELFRec/tree/main/dataset); [current Yelp provider page](https://business.yelp.com/data/resources/open-dataset/) | Label as FRAMEWORK_OFFICIAL, select immutable commit, reconstruct provider/version/filter/split lineage, and clear applicable Yelp terms. |
| LightGCL processed multi-dataset pack | Author commands and files exist, but Yelp, Gowalla, MovieLens-10M, Amazon and Tmall cannot inherit one common data license. The author ml10m processing cannot be assumed identical to the provider five-fold pack. | [LightGCL author README](https://github.com/HKUDS/LightGCL); [author data directory](https://github.com/HKUDS/LightGCL/tree/main/data); [MovieLens 10M provider README, Cross-Validation](https://files.grouplens.org/datasets/movielens/ml-10m-README.html) | Lock repository commit, map each file to canonical raw bytes and transformation, and clear each upstream source separately. |
| Amazon Review Data (2018) | Useful ordered user histories and text, but no basket/order structure or official cold-item split. Provider notes post-2018 metadata changes, publishes no digest on the page, and no data license was located. | [UCSD provider page, Important Notes, downloads and schemas](https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/index.html) | Choose exact categories/raw-versus-k-core variant, capture bytes and SHA-256, establish rights, and preregister a reduced sequential/text adapter. |
| UniSRec processed bundle | Author commands and inductive mode are documented, but hosted artifacts have no locked release/hash, named domains are not yet proven file-by-file against a canonical raw version, and processed text/embedding rights are unresolved. | [UniSRec author repository, Quick Start, processed data, fine-tuning/inductive commands and preprocessing](https://github.com/RUCAIBox/UniSRec); [UCSD Amazon provider page](https://cseweb.ucsd.edu/~jmcauley/datasets/amazon_v2/index.html) | E4 artifact SHA-256 and raw-to-processed lineage; E3 code/config/candidates; E5 raw text, embedding, redistribution and model-output rights. |
| AlphaRec processed bundle | Anonymous hosted artifact, no data release/version/hash, no dataset-specific license, unclear raw lineage, and advertised zero-shot/user-intention artifacts remain unfinished. | [AlphaRec author README, Status, Dataset and commands](https://github.com/LehengTHU/AlphaRec) | Lock only actually released features at an immutable commit; acquire/hash lawful data; resolve source/semantic-artifact rights and exact protocol. |
| The Complete Journey | Provider evidence supports strong household purchase/basket/history content and academic-research purpose, but the observed page did not expose a resolvable current file, exact package/schema/version/hash, or dataset-specific terms. | [dunnhumby Source Files, The Complete Journey](https://www.dunnhumby.com/source-files/); [Mask-Swap author repository, Complete Journey configuration](https://github.com/liming-7/Mask-Swap-NNBR) | Obtain provider package/schema and current terms; hash it; clear household/privacy, redistribution, derivatives and outputs; preregister split/candidates. |
| Instacart Market Basket Analysis | Excellent repeat-basket fit, but the official competition is disabled at the host's request and the original Instacart URL is unavailable. Mirror licenses and files are not accepted. | [official competition overview/disabled state](https://www.kaggle.com/c/basket-analysis/overview); [original provider URL](https://www.instacart.com/datasets/grocery-shopping-2017); [Reality Check author repository](https://github.com/liming-7/A-Next-Basket-Recommendation-Reality-Check) | Restore official provider/competition access, capture applicable rules, acquire/hash TRAIN assets without opening TEST, and clear rights. |
| Tenrec | Official endpoint exists and author repo requires license acceptance, but current terms/files/version/hash were not captured. It is a multi-behavior/session substrate, not a commerce basket/text contract. | [Tenrec author repository, official access route](https://github.com/yuangh-x/2022-nips-tenrec); [official Tencent endpoint](https://static.qblv.qq.com/qblv/h5/algo-frontend/tenrec_dataset.html); [original paper, task fields/protocol/checklist](https://proceedings.neurips.cc/paper_files/paper/2022/file/4ad4fc1528374422dd7a69dea9e72948-Paper-Datasets_and_Benchmarks.pdf) | Capture accepted terms and file SHA-256; freeze one exact task/config/candidate policy; E5 privacy/rights decision. |

## Sensitivity-only restrictions

| Dataset | Permitted evidentiary role | Prohibited claim | Evidence and remaining gate |
|---|---|---|---|
| ViEcomRec | Vietnamese e-commerce item-text, rating/time and user-history sensitivity after E4/E5. | Do not call it basket/order/session/full-contract or official cold-item validation; do not treat language as compatibility. | [original paper, pp.2-4 Dataset/Problem/Experimental Setting](https://doras.dcu.ie/29693/1/viecomrec.pdf); [author repository](https://github.com/linh222/face_cleanser_recommendation_dataset); [CC BY-NC-SA 4.0 license](https://github.com/linh222/face_cleanser_recommendation_dataset/blob/main/LICENSE). E4 must hash exact artifact/split without opening TEST; E5 must clear Shopee provenance/privacy and output classification. |
| ViHoRec | Vietnamese hotel rating/time and basic user-history sensitivity, conditional on E1 venue-cutoff and E5 source-rights decisions. | Do not call it commerce basket, item-text or cold-item validation; do not treat the July 2026 preprint as cutoff-admissible until E1 rules. | [author README, benchmark/license/anonymization](https://github.com/MinhNguyenDS/ViHoRec); [author datasheet, source restrictions and linkage risk](https://github.com/MinhNguyenDS/ViHoRec/blob/Master/DATASHEET.md); [preprint record/date](https://arxiv.org/abs/2607.12946). |

## Explicitly inadmissible substitutes and inferences

| Excluded shortcut | Reason |
|---|---|
| Kaggle or arbitrary cloud mirrors when a provider route is missing | A mirror can neither establish the provider's release identity nor grant rights the uploader did not hold. Instacart and Ta-Feng therefore remain blocked despite widespread copies. |
| “Latest” mutable provider files without an acquisition manifest | Amazon Review metadata changed after its 2018 label. Every selected file/variant needs a resolved URL, date, byte size and SHA-256. |
| Repository code license used as dataset license | LightGCN, LightGCL, SELFRec, UniSRec and AlphaRec code rights do not automatically cover upstream data, product/review text or redistributed processed files. |
| Git commit hash used as proof of lawful redistribution | A commit proves identity. It does not prove that bundled data were licensed for redistribution. |
| Paper-reported processed counts used as canonical provider counts | Processed counts reflect paper filters/splits. The registry records users/items/interactions only when the named primary source explicitly states them and labels the level. |
| Metrics compared across MovieLens, Yelp, Gowalla, Amazon, grocery or Vietnamese datasets | Different data, splits, filters and candidate policies make raw centers non-comparable. This lane locks compatibility only; RESULT_STATUS remains NOT_RUN. |
| Vietnamese language treated as full-contract compatibility | Language does not establish basket/order/session structure, history semantics, lawful reuse, cold-item support, split/candidates or selected-model configs. |
| Provider page descriptions treated as execution permission | The Complete Journey and Tenrec need the actual current access contract/package; Amazon-M2 needs authenticated terms capture; no acquisition is authorized by this lane. |

## Accepted reference boundary

MovieLens 1M and MovieLens 10M are not listed as holds because their provider-canonical release, direct access, README terms and checksum mechanisms support REFERENCE_REPRODUCTION_READY classification. This does not bypass E4 byte acquisition/hash or E5 rights/privacy verification.

Amazon-M2 is not a hold because its primary paper and author repository support HARMONIZED_EXTERNAL_CANDIDATE classification. It remains explicitly limited to a reduced session-specific multilingual/text/cold-item external contract, with authenticated access, hashing and E5 review still required.
