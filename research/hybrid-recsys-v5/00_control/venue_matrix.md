# Phase 0 Venue Matrix

```text
TARGET_VENUE          = NOT_SELECTED
TARGET_YEAR_TRACK     = NOT_SELECTED
OFFICIAL_CFP_VERIFIED = PARTIAL_CANDIDATE_SCAN_ONLY
SUBMISSION_FORMAT     = BLOCKED
```

Retrieved: **2026-08-13 UTC**. Only official venue or society pages are treated
as authoritative. A previous-year CFP is contextual evidence only and cannot
set the target-year deadline, page limit, template, review mode, or AI policy.

## Candidate ranking

| Rank | Candidate | Current official evidence | Fit | Phase 0 decision |
|---:|---|---|---|---|
| 1 | ACM RecSys 2027 — Main Research Track | The 2027 CFP was not located on the official RecSys site as of retrieval. The official [RecSys 2026 call](https://recsys.acm.org/recsys26/call/) confirms strong topical alignment with foundations, evaluation, reproducibility, benchmarking, and real-world recommendation, but its dates and rules are not inherited. | Highest topical fit | `PREFERRED_PENDING_2027_CFP` |
| 2 | ACM SIGIR 2027 — Full Research Paper | An official 2027 paper CFP was not located as of retrieval. Official SIGIR material identifies the 2027 conference in Silicon Valley, but that does not establish submission rules. | Strong IR/ranking and evaluation fit | `WATCH_PENDING_CFP` |
| 3 | ACM CIKM 2027 — Research Track | No authoritative 2027 CFP was located as of retrieval. | Broad recommendation/data-mining fit | `WATCH_PENDING_CFP` |
| 4 | ACM WSDM 2027 — Full Paper | The official [WSDM 2027 full-paper CFP](https://www.wsdm-conference.org/2027/cffp.html) includes web recommender systems, benchmarking, and empirical evaluation. Abstract deadline: 2026-08-17 AoE; paper deadline: 2026-08-24 AoE. | Scientifically compatible | `NOT_FEASIBLE_CURRENT_CYCLE` because experiments are `NOT_RUN` |

The ranking is a watchlist, not a venue selection. RecSys 2027 becomes the target
only after its official CFP is published and all mandatory intake fields below
are verified.

## Verified WSDM 2027 snapshot

This record prevents accidental reuse while documenting why the current cycle
was rejected:

| Field | Verified value | Official source |
|---|---|---|
| Venue / track | WSDM 2027 Full Papers; main submissions may be considered for Findings | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Abstract deadline | 2026-08-17, 23:59 AoE | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Paper deadline | 2026-08-24, 23:59 AoE | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Page limit | 9 pages for content plus unrestricted references and ethical-considerations section | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Template | ACM `acmart`, `sigconf,anonymous,review`; English PDF | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Review | Double-blind to PC/SPC; author metadata visible to Associate Chairs | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Preprint | Earlier preprint/code posts permitted subject to anonymity precautions | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Supplement | External anonymous repositories permitted; reviewer use discretionary | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Ethics | Ethical Considerations section required and excluded from nine-page limit | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Generative AI | CFP points to the ACM policy; no project-specific interpretation has yet been approved | [Official CFP](https://www.wsdm-conference.org/2027/cffp.html) |
| Feasibility | Rejected for this campaign | Internal status: no accepted results and mandatory benchmark work outstanding |

## Target-venue intake form

These fields remain deliberately unresolved until one target venue is chosen:

| Field | Current value |
|---|---|
| Venue / acronym | `PENDING` |
| Year and track | `PENDING` |
| Submission and abstract deadlines | `PENDING` |
| Paper and reference limits | `PENDING` |
| Supplementary-material policy | `PENDING` |
| Blind-review and anonymization rules | `PENDING` |
| Preprint policy | `PENDING` |
| Artifact/data/code policy | `PENDING` |
| Human-data and ethics requirements | `PENDING` |
| Generative-AI policy | `PENDING` |
| Citation and template style | `PENDING` |
| Conflict-of-interest policy | `PENDING` |

## Recheck gate

- Monitor the official RecSys, SIGIR, and CIKM sites for their 2027 CFPs.
- Re-run venue intake before Stage 2 paper configuration or immediately when an
  official target-year CFP appears.
- Venue selection must be complete before any submission-specific LaTeX project
  or page-budget compression begins.
