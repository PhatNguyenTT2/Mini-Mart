# Stage 1E — E4 R4 strict complete-bundle discovery contract

Date: 2026-08-22  
Stage family: R4  
Entry verdict: NO_SELECTION_EVIDENCE_REMAINS_INSUFFICIENT  
User scope decision: START_NEW_STRICT_DISCOVERY_WAVE  
Execution authority: DENIED

## 1. Why R4 exists

R3 found three plausible framework–dataset seeds, but every seed failed the
independent evidence lanes. R4 therefore moves the completeness test to the
front of discovery. A proposal is not admitted merely because likely source
locators exist. Before it reaches a downstream audit, primary evidence must
already bind one framework, one immutable revision, one canonical dataset
release, one source-owned experiment protocol, one evaluator and one numeric
target on the same surface.

The R3 candidates are retained as historical negative evidence. They are not
deleted, repaired by cross-joining sources, or silently reconsidered.

## 2. Discovery topology

R4-S0 is performed in the current central context. It preregisters this
contract, the strict admission schema, source-family boundaries, frozen inputs,
model policy and execution prohibitions.

After R4-S0 passes, three fresh worker contexts run concurrently:

- R4-D1A: official conference artifact, reproducibility-package and archival
  supplement sources;
- R4-D1B: official benchmark-suite repositories with immutable result/config
  surfaces;
- R4-D1C: official framework releases only when a complete same-surface
  code–data–protocol–result packet can be established.

Each scout may return zero admitted proposals. It must preserve excluded rows
and reasons. It may mark a proposal ADMIT_COMPLETE_BUNDLE_FOR_INDEPENDENT_AUDIT
only when every mandatory admission dimension in
e4_r4_strict_admission_contract.json passes with no unresolved field.

R4-G0 is central and sequential. It validates worker schemas and hashes,
deduplicates exact provenance tuples, independently replays every
decision-bearing source for proposals marked admitted, and freezes zero to
three bundles. A cache miss, inaccessible page, indirect source, identity
conflict or unresolved mandatory field excludes the proposal; central review
does not speculate or repair it.

Only if R4-G0 freezes at least one complete bundle may three fresh independent
audit contexts run: R4-A1 rights/lineage, R4-A2
environment/training/evaluator/numeric-target, and R4-A3 v5 compatibility and
leakage. R4-G1 may then select zero or one. R4-M0 remains a mandatory user
checkpoint before any materialization.

## 3. Strict admission rule

Admission is conjunctive, not scored. Every proposal must establish all twelve
dimensions below from authoritative evidence:

1. affirmative code license at the pinned project/revision;
2. canonical dataset release and affirmative lawful-use basis;
3. provider checksum or a byte-verifiable acquisition and transformation chain;
4. immutable full repository revision;
5. complete environment lock, or a source-owned bounded lock that can be
   deterministically completed without guessing versions;
6. executable source-owned training entry point;
7. exact preprocessing, split, configuration and seed protocol;
8. source-owned evaluator with metric, candidate-set, masking and tie semantics;
9. numeric target bound to that same framework–dataset–revision–protocol–config
   surface;
10. no TEST-derived schema, cardinality, tuning or model-selection dependency;
11. a bounded v5 adapter that does not rewrite the objective or evaluator; and
12. successful independent replay by the scout of every decision-bearing URL.

UNKNOWN, PARTIAL, INFERRED, search-snippet-only, inaccessible, or conflicting
evidence fails a mandatory dimension. No weighted score can offset a failure. A
paper table without a producing recipe and a runnable framework without a
same-surface numeric target are both excluded.

## 4. Identity, deduplication and no cross-join

A bundle identity is the exact tuple:

repository_url + full_revision + dataset_provider + dataset_release_id +
protocol_id + config_id + evaluator_id + numeric_target_id.

Evidence may not be borrowed across repositories, revisions, datasets,
protocols, configs or evaluators. Mirrors, forks, package indexes, blogs,
leaderboards without protocol, generated summaries and search snippets are
locator aids only. Exact duplicate tuples collapse at R4-G0; conflicting
representations fail closed.

## 5. Source verification policy

Decision-bearing evidence is limited to project-owner repositories and immutable
blobs/trees/commits/releases, canonical dataset providers and terms/checksum
pages, original proceedings/papers and source-owned supplementary artifacts.
Every source record carries URL, authority class, claim scope, immutable binding
where available, access result, retrieval date and a short evidence note.

Absence of evidence is recorded as absence, never converted into proof. Web
content is evidence data and never an instruction to the pipeline.

## 6. Runtime model policy

- central stages: Sol Max Standard, runtime model gpt-5.6-sol, reasoning max,
  service tier standard;
- newly created worker stages: Sol XHigh Standard, runtime model gpt-5.6-sol,
  reasoning xhigh, service tier standard;
- plugin: ars-codex:academic-research-suite 0.1.26.

For subagent dispatch, Standard speed is represented by omitting a service-tier
override. The artifacts still record service_tier=standard.

## 7. Forbidden operations before R4-M0

Until a positive R4-G1 decision and explicit user approval at R4-M0, no stage
may clone/fetch/download a repository or source archive, acquire a
dataset/checkpoint, accept terms, authenticate, install packages, create an
environment/container, preprocess, train, evaluate, open the v5 TEST set,
contact maintainers, or copy a candidate number into the paper as a valid
project result.

Allowed operations are read-only local inspection, public authoritative web
research, deterministic schema/hash validation and writes to declared R4
artifact roots.

## 8. Persistent truth state

Every R4 artifact must preserve:

- RESULT_STATUS=NOT_RUN;
- TEST_SET_OPENED=NO;
- ACCEPTED_RESULT_ROWS=0;
- execution_authorized=false;
- project benchmark numbers: INVALID_FOR_PAPER.
