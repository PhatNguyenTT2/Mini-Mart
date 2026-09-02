# Research Benchmark Context

This context defines the language used by the independent recommender-system
research runner. It keeps implementation fixtures, protocol reproductions, and
paper-admissible results from being conflated.

## Language

**Dataset Snapshot**:
An immutable, hash-bound collection of interaction splits, item records, raw-to-internal ID mappings, and provenance metadata admitted for one experiment lineage.
_Avoid_: Dataset dump, current data, old snapshot

**Source Bundle**:
An immutable export of raw users, items, events, training baskets, generator specification, and source-lineage hashes before internal IDs or evaluation splits are materialized.
_Avoid_: Raw snapshot, database dump, canonical dataset

**Training Basket**:
A train-period purchase order containing at least two distinct items and an explicit origin; only organic Training Baskets may fit the main Apriori feature.
_Avoid_: Session, event group, semantic trap

**Dataset Admission**:
A fail-closed receipt stating whether one Source Bundle can produce a Dataset Snapshot with verified lineage, scope, provenance, and task-suitability checks.
_Avoid_: Dataset validation, data ready, snapshot created

**Protocol**:
A hash-bound specification of split boundaries, eligible users, positives, candidate catalog, seen-item masking, tie handling, cutoff, metrics, and TEST state.
_Avoid_: Evaluation settings, benchmark defaults

**Score Artifact**:
An immutable, ordered matrix of model scores bound to one run, one Protocol, one user order, and one candidate-catalog order.
_Avoid_: Predictions, recommendations, model metrics

**Official Protocol Reproduction**:
A source-bound rerun that preserves the reference implementation, dataset, split, configuration, checkpoint rule, and evaluator semantics closely enough to test a published result center.
_Avoid_: Baseline rerun, reproduced benchmark

**Harmonized v5 Comparison**:
A comparison in which every admitted method exports scores for the same v5 Dataset Snapshot and is evaluated by the same Protocol and shared evaluator.
_Avoid_: Official reproduction, cross-dataset comparison

**Fixture Run**:
A deterministic test execution over synthetic, test-only records that validates software seams but produces no empirical evidence.
_Avoid_: Experiment, benchmark run, pilot result

**Accepted Result Row**:
A metric row whose source, data, protocol, run, score, evaluator, and statistical artifacts have all passed the applicable independent gate.
_Avoid_: Result, observed number, diagnostic row

**TEST Seal**:
The fail-closed state that prevents test-split cases from being prepared or evaluated before the registered configurations and checkpoints are frozen.
_Avoid_: Hidden test, unused test set

**Historical Service**:
The quarantined `ai-service` implementation retained only for schema, API, domain-term, and failure-mode inventory.
_Avoid_: Baseline service, previous model, reference implementation
