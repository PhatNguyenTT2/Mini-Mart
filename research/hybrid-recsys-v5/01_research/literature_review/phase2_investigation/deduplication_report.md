# Stage 1B Deduplication and Corpus-Freeze Report

Verdict: PASS for paper-level identity deduplication; independent audit pending.

## Accounting

- Lane-accepted records: 60.
- Canonical paper-level duplicates merged: 3.
- Relevance/redundancy exclusions after merge: 2.
- Frozen pre-audit corpus: 55 unique sources.
- Target range in the master plan: 45–55; result: 55.

## Canonical duplicate merges

| Canonical key | Lane records merged | Reason |
|---|---|---|
| `cheng2016_wide_deep` | L2-04; L3-WD | Same paper and DOI `10.1145/2988450.2988454`. L2 owns architecture framing; L3 owns the Apriori/H3 boundary. |
| `cai2023_lightgcl` | L2-11; L4-12 | Same ICLR 2023 paper/OpenReview record. L2 owns comparator positioning; L4 owns collaborative-only cold-item caveat. |
| `sheng2025_alpharec` | L2-12; L4-07 | Same ICLR 2025 paper/proceedings record. L2 owns architecture positioning; L4 owns text/cold-item boundary. |

Repositories, publisher pages, challenge pages, and paper pages were treated as evidence pointers within one source family—not independent sources.

## Central exclusions

| Lane record | Decision | Reason |
|---|---|---|
| L1-S02 — Jin et al. (2021), *On Estimating Recommendation Evaluation Metrics under Sampling* | Exclude from final 55; retain in lane log | Redundant counterpoint after retaining the newer Li et al. (2023) adaptive/reliable sampling source. Exclusion avoids double-weighting one sampling-estimator family. |
| L4-09 — Nguyen et al. (2024), *Cold-start Recommendation by Personalized Embedding Region Elicitation* | Exclude from final 55; retain in lane log | New-user elicitation is outside the frozen cold-item estimand. The conceptual boundary remains in Stage 1A and does not need an out-of-scope source in the final corpus. |

## Dependence that is not duplication

These records remain separate but must not be counted as independent corroboration:

- `hou2026_blair` / Amazon Reviews 2023 and `robinson2024_relbench` / `rel-amazon`: shared upstream data family.
- H&M competition and `robinson2024_relbench` / `rel-hm`: RelBench adapts the H&M source data into a relational task.
- Amazon-M2 paper, repository, Amazon Science page, and KDD Cup challenge: one artifact family.
- Coveo workshop page, overview paper, repository, and terms: one artifact family.
- ViEcomRec, Vietnamese Food, ViHoRec, OTTO, and MUSE paper/repository pairs: one source family each.
- Complete Journey provider release and the community R package: provider dataset plus adapter/distribution layer, not two independent datasets.

## Matching procedure and degradation

1. Exact DOI equality where available.
2. Canonicalized title and year matching.
3. OpenAlex DOI/title lookup.
4. Crossref DOI/title lookup.
5. Official proceedings/provider page exception check.
6. Semantic Scholar ID matching was attempted but unavailable due HTTP 429. The S2 layer is recorded as degraded, not as a negative match.

No same-paper aliases remain in the 55-source registry. Dataset lineage dependencies remain explicit because collapsing them would hide protocol differences.

