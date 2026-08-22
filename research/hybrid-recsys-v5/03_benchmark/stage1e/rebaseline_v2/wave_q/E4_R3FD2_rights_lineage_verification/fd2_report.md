# Stage 1E R3-FD2 — rights and lineage verification report

Date: `2026-08-22`  
Runtime profile: `Sol XHigh Standard` (`gpt-5.6-sol`, reasoning `xhigh`, service tier `standard`)  
Lane: `R3-FD2`  
Selection authority: `NONE`

## Frozen input binding

- Path: `research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_p/E4_R3FD1_bundle_seed_discovery/candidate_bundle_seeds.json`
- Canonical LF bytes: `23034`
- Canonical LF SHA-256: `dce058850afb537f062531d1b128a1c36685bc878a3761e35a22db3d72db8781`
- Candidate order preserved exactly: Cornac ML100K, Elliot ML1M, DaisyRec ML1M.

The local deterministic recheck matched both frozen values. No candidate was added, removed, renamed, ranked, merged, or selected.

## Method and boundary

Only primary or authoritative owner/provider pages were used for decision-bearing claims. Cached GitHub failures were retried through the live owner page without cloning or downloading. Failed checksum-sidecar retrievals remain `UNRESOLVED`; sidecar existence was not promoted into a verified digest. No repository, dataset, checkpoint, package, environment, preprocessing job, split, training run, evaluation run, TEST access, terms acceptance, or maintainer contact occurred.

## R3-BUNDLE-CORNAC-ML100K-001

Status: `EVIDENCE_INCOMPLETE`

- Repository identity is verified at immutable commit [`42a327f26241790e99f56284e89c3ab903b69c45`](https://github.com/PreferredAI/cornac/commit/42a327f26241790e99f56284e89c3ab903b69c45), and the owner release binds v2.6.0 to that commit.
- The revision-pinned [`LICENSE`](https://github.com/PreferredAI/cornac/blob/42a327f26241790e99f56284e89c3ab903b69c45/LICENSE) is Apache-2.0 and provides affirmative code-use rights subject to its conditions.
- GroupLens identifies [MovieLens 100K](https://grouplens.org/datasets/movielens/100k/) as the stable 1998-04 release. Its [README](https://files.grouplens.org/datasets/movielens/ml-100k-README.txt) permits conditional research use, requires acknowledgement, and restricts redistribution and commercial use.
- The frozen [Cornac loader](https://github.com/PreferredAI/cornac/blob/42a327f26241790e99f56284e89c3ab903b69c45/cornac/datasets/movielens.py) points directly to provider-hosted `ml-100k/u.data`; the provider [unzipped index](https://files.grouplens.org/datasets/movielens/ml-100k/) and README establish its schema. The frozen [RatioSplit](https://github.com/PreferredAI/cornac/blob/42a327f26241790e99f56284e89c3ab903b69c45/cornac/eval_methods/ratio_split.py) establishes shuffled seeded split lineage.
- Incompleteness: the published archive MD5 payload did not replay, no checksum for directly served `u.data` was verified, and no byte-level archive-to-`u.data` equality proof is available.

## R3-BUNDLE-ELLIOT-ML1M-001

Status: `EVIDENCE_INCOMPLETE`

- The owner [v0.3.1 release](https://github.com/sisinflab/elliot/releases/tag/v0.3.1) binds immutable commit [`641100a89c707619e557eafc46df7ff46c359a73`](https://github.com/sisinflab/elliot/commit/641100a89c707619e557eafc46df7ff46c359a73).
- The pinned [`LICENSE`](https://github.com/sisinflab/elliot/blob/641100a89c707619e557eafc46df7ff46c359a73/LICENSE) is Apache-2.0.
- GroupLens identifies [MovieLens 1M](https://grouplens.org/datasets/movielens/1m/) as the stable 2003-02 release. Its [README](https://files.grouplens.org/datasets/movielens/ml-1m-README.txt) provides the same conditional research-use, attribution, no-redistribution, and non-commercial boundaries.
- Frozen [`sample_main.py`](https://github.com/sisinflab/elliot/blob/641100a89c707619e557eafc46df7ff46c359a73/sample_main.py) identifies `ml-1m.zip`, extracts `ratings.dat`, converts `::` to tabs, and writes `dataset.tsv`. The frozen [configuration](https://github.com/sisinflab/elliot/blob/641100a89c707619e557eafc46df7ff46c359a73/config_files/advanced_configuration.yml), [dataset loader](https://github.com/sisinflab/elliot/blob/641100a89c707619e557eafc46df7ff46c359a73/elliot/dataset/dataset.py), [prefilter](https://github.com/sisinflab/elliot/blob/641100a89c707619e557eafc46df7ff46c359a73/elliot/prefiltering/standard_prefilters.py), and [splitter](https://github.com/sisinflab/elliot/blob/641100a89c707619e557eafc46df7ff46c359a73/elliot/splitter/base_splitter.py) provide preprocessing and split lineage.
- Incompleteness: the conversion script uses HTTP, checks no digest, the provider MD5 payload did not replay, and no digest chain binds archive to `ratings.dat` to generated `dataset.tsv`.

## R3-BUNDLE-DAISYREC-ML1M-001

Status: `EVIDENCE_INCOMPLETE`

- Repository identity is verified at immutable commit [`e9d0326457fb8aa138f7bb04ab751b17345cdb65`](https://github.com/recsys-benchmark/DaisyRec-v2.0/commit/e9d0326457fb8aa138f7bb04ab751b17345cdb65).
- The exact frozen [`LICENSE`](https://github.com/recsys-benchmark/DaisyRec-v2.0/blob/e9d0326457fb8aa138f7bb04ab751b17345cdb65/LICENSE) is Apache-2.0. This corrects, and does not preserve, the seed's MIT label.
- The canonical dataset release and conditional use terms are the same [MovieLens 1M release](https://grouplens.org/datasets/movielens/1m/) and [provider README](https://files.grouplens.org/datasets/movielens/ml-1m-README.txt).
- The frozen [README](https://github.com/recsys-benchmark/DaisyRec-v2.0/blob/e9d0326457fb8aa138f7bb04ab751b17345cdb65/README.md) directs manual provider acquisition. Frozen [loader](https://github.com/recsys-benchmark/DaisyRec-v2.0/blob/e9d0326457fb8aa138f7bb04ab751b17345cdb65/daisy/utils/loader.py), [splitter](https://github.com/recsys-benchmark/DaisyRec-v2.0/blob/e9d0326457fb8aa138f7bb04ab751b17345cdb65/daisy/utils/splitter.py), [test entrypoint](https://github.com/recsys-benchmark/DaisyRec-v2.0/blob/e9d0326457fb8aa138f7bb04ab751b17345cdb65/main.py), and [tuning entrypoint](https://github.com/recsys-benchmark/DaisyRec-v2.0/blob/e9d0326457fb8aa138f7bb04ab751b17345cdb65/hpo_tuner.py) verify post-acquisition preprocessing and temporal split lineage.
- Incompleteness: no frozen acquisition/extraction/checksum recipe binds provider archive bytes to `./data/ml-1m/ratings.dat`; the provider MD5 payload did not replay.

## Lane disposition

All three rows are `EVIDENCE_INCOMPLETE`. None is a dispositive rights rejection: each frozen code revision has an affirmative Apache-2.0 license, and GroupLens provides a conditional research-use basis. None may be promoted to sufficient because unresolved byte-identity/checksum evidence remains. R3-FD2 selects no winner and authorizes no materialization.

## Persistent truth state

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- `project_benchmark_numbers=INVALID_FOR_PAPER`
