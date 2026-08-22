# Phase 0 — Intake and Governance

```text
PHASE_STATUS                = COMPLETE_PENDING_CHECKPOINT
PIPELINE_ENTRY              = PHASE_0_INTAKE_GOVERNANCE
NEXT_STAGE                  = STAGE_1A_RQ_METHODOLOGY_BACKFILL
PAPER_DIRECTION             = METHODS_EMPIRICAL
TARGET_VENUE                = NOT_SELECTED
EXPERIMENT_INTAKE           = EXPERIMENTS_DECLARED_NOT_EXECUTED
ACCEPTED_MODEL_RESULTS      = NONE
HISTORICAL_EVIDENCE         = QUARANTINED
MANUSCRIPT_RESULTS_CLAIMS   = BLOCKED
SUBMISSION_FORMATTING       = BLOCKED_PENDING_VENUE
```

## 1. Intake decision

The project enters the ARS academic pipeline through a project-specific Phase 0
before Stage 1. The research questions, hypotheses, dataset contract, and planned
evaluation already exist, but the source corpus has not been verified and no
experiment has produced an accepted result.

The intended submission is a **methods/empirical paper**. The central scientific
claim, if eventually supported, must come from a same-dataset, same-protocol
comparison of the Hybrid method against faithfully adapted baselines. The v5
benchmark is controlled/semi-synthetic and must never be described as observed
Vietnamese shopper behavior.

## 2. Locked authoritative inputs

Phase 0 locks the following inputs by SHA-256 in `input_manifest.json`:

- `inputs/idea.md`;
- `inputs/experimental_log.md`;
- `inputs/conference_guidelines.md`.

`master/academic-research-master-plan.md` is locked separately as the governing
plan. Any byte change to one of these four files invalidates this intake bundle
and requires a new Phase 0 version; downstream artifacts then become `STALE`.

## 3. Evidence boundary

- `RESULT_STATUS=NOT_RUN` remains authoritative.
- No historical metric, figure, table, claim, citation, or template is accepted
  as current evidence.
- `workspace/`, `paper/`, `detail-report/`, old figures, and old LaTeX may only be
  treated as quarantined historical material.
- Results may enter the manuscript only from sealed result artifacts carrying a
  dataset hash, config hash, repository revision, seed, checkpoint hash, and
  per-user metric artifact.
- Hybrid superiority, production readiness, external validity, and latency
  claims are forbidden until their corresponding experiment gates pass.

## 4. Experiment intake

The scholar has declared three experiment namespaces. Their identifiers are
frozen at intake:

1. `EXP-REF-REPRO` — official baseline reproduction on source datasets;
2. `EXP-V5-HARMONIZED` — shared-protocol comparison on benchmark v5;
3. `EXP-EXTERNAL-VALIDITY` — full-mechanism and Vietnamese external tracks.

All planned units are currently `executed: false`. These declarations document
the planned evidence path; they do not support any empirical manuscript claim.

## 5. Venue state

No target venue has been selected. `venue_matrix.md` records only rules found on
official pages for the correct year. WSDM 2027 is marked infeasible for the
current campaign because its paper deadline occurs before the required research
and experiment gates can reasonably complete. RecSys 2027 remains the preferred
watch candidate, with all target-year rules left pending until its official CFP
is published.

No LaTeX class, page limit, review mode, literature cutoff, or generative-AI
policy may be inferred from a different year.

## 6. Phase 0 exit gate

Phase 0 is complete when all of the following hold:

- [x] Input checksums are recorded.
- [x] Paper direction is methods/empirical.
- [x] Historical evidence is quarantined.
- [x] Experiment declaration and stable experiment IDs exist.
- [x] Pipeline state and Material Passport exist.
- [x] Venue status and official-source watchlist exist.
- [x] Control artifacts pass syntax and ARS provenance validation.
- [ ] User confirms transition to Stage 1A.

Until the final checkbox is confirmed, the pipeline state is
`awaiting_confirmation` and Stage 1 remains pending.
