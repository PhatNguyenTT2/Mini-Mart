# Stage 1E — E4-R2 / R2-A1 source and license decisions

Created: `2026-08-22T17:16:59+07:00`

Lane: `R2-A1` — official repository/source/license/config evidence

Mode: evidence-only, fail-closed; execution denied

## Scope and truth state

This decision record covers exactly the seven frozen candidate rows, in manifest order. It decides only repository identity, immutable source identity, repository code-license scope, source-tree implications, entry/config availability, and paper↔repository↔command↔config coupling.

It does **not** decide dataset rights, provider release, raw/processed lineage, result-center acceptance, metric parity, evaluator parity, or candidate selection. A repository-bundled dataset, paper license, README badge, or public GitHub page is never promoted into rights evidence for another scope.

- `RESULT_STATUS=NOT_RUN`
- `TEST_SET_OPENED=NO`
- `ACCEPTED_RESULT_ROWS=0`
- `execution_authorized=false`
- Candidate selection: none

## Decisions

| Order | Candidate | Immutable repository decision | Code-license decision at pin | Entry/config decision | A1 evidence status |
|---:|---|---|---|---|---|
| 1 | `E3-LIGHTGCN-GOWALLA-PYTORCH-001` | Commit `947ca2b3b1d2d3545b114145710cb06c4e57b3d2` resolves; README self-identifies as the PyTorch implementation for the LightGCN paper, but the official arXiv record does not link it and the source credits Jianbai Ye. Relationship remains repository-asserted/lab-maintained, not paper-linked. | No `LICENSE`/`COPYING` in the non-truncated 43-entry tree. No affirmative grant. | `code/main.py` + argparse is noninteractive and README binds the three-layer Gowalla argv. Build closure is incomplete because the C++ sampler requires README-named `pybind11`/`cppimport` absent from `requirements.txt`. | `EVIDENCE_INCOMPLETE` |
| 2 | `E3-SIMGCL-YELP2018-QREC-001` | The [official SimGCL arXiv record](https://arxiv.org/abs/2112.08679) links QRec; commit `a141bb37cb7706b2f53b2eed5843de3269f9f37f` resolves. | No license file or affirmative grant in the non-truncated 145-entry tree. | `main.py` uses `input()`; `q5` selects immutable `config/SimGCL.conf` (Yelp2018, top-20, 2 layers, λ=0.5, ε=0.1), but no public noninteractive argv exists. | `EVIDENCE_INCOMPLETE` |
| 3 | `E3-XSIMGCL-YELP2018-SELFREC-001` | The [official XSimGCL arXiv record](https://arxiv.org/abs/2209.02544) links SELFRec; commit `5b0229423cb1c727e85a704d63e460368c8b9dde` resolves. | No license file or affirmative grant in the non-truncated 92-entry tree. | `main.py` interactively selects `conf/XSimGCL.yaml`. The same pinned README binds the candidate center to `layer=3`, while the selected YAML fixes `n_layer: 2`. This is an exact source/config mismatch; changing the file would be an unauthorized mutation. | `DISPOSITIVE_REJECT` |
| 4 | `E3-LIGHTGCL-YELP-UPDATED-001` | The [official LightGCL arXiv record](https://arxiv.org/abs/2302.08191) links HKUDS/LightGCL; commit `5590453ad86782f58017e58d0b698d7f32175be3` resolves. | No license file or affirmative grant in the non-truncated 25-entry tree. | `python main.py --data yelp` is noninteractive. Immutable defaults specify two GNN layers, SVD rank 5, λ1=0.2, τ=0.2, λ2=1e-7. `utils.py` samples each positive interaction row with a uniformly sampled unobserved negative. Seed and executed-config receipt are absent. | `EVIDENCE_INCOMPLETE` |
| 5 | `E3-UNISREC-SCIENTIFIC-TRANS-001` | The [official UniSRec arXiv record](https://arxiv.org/abs/2206.05941) links RUCAIBox/UniSRec; commit `05aa5cba2809112c32808f70d16abc61c05c6538` resolves. | Pinned `LICENSE` blob `abaa88c213d7e0a06cc6c4fa2414b48c7410612e` is an affirmative MIT grant for repository software/documentation. It does not cover external data, text, checkpoint, or an unspecified dependency build. | The Scientific transductive command is noninteractive and binds `props/UniSRec.yaml` + `props/finetune.yaml`. The checkpoint and processed dataset are external; `recbole>=1.1.1` is unpinned. Preprocessing instructions generate `ln -s` links even though the Git tree itself has none. | `EVIDENCE_INCOMPLETE` |
| 6 | `E3-SASREC-SCIENTIFIC-UNISREC-FRAMEWORK-001` | The same immutable UniSRec commit publishes the framework-bound SASRec baseline command. It is not the original SASRec author repository, and the pinned tree does not implement SASRec; `run_baseline.py` delegates to external RecBole. | UniSRec MIT covers the pinned wrapper/config only. Because `recbole>=1.1.1` is not resolved to an exact source revision, a complete result-bound source/license set cannot be closed. | The command is noninteractive and binds Scientific plus `props/finetune.yaml` and `hidden_size=300`. SASRec objective/source defaults remain in an unpinned RecBole installation. | `EVIDENCE_INCOMPLETE` |
| 7 | `E3-ALPHAREC-MOVIES-TV-001` | The [official ICLR 2025 proceedings record](https://proceedings.iclr.cc/paper_files/paper/2025/hash/e4bab1843c8d5a69f5abfd0824593493-Abstract-Conference.html) matches the pinned README title/authors; commit `4b6c6cf378f292c31dd75b09a8075e8344561415` is authored by first author Leheng Sheng. | README shows an MIT image badge, but the non-truncated 64-entry tree has no license file or grant text. Badge-only evidence is not an affirmative license. | The Movies & TV command is noninteractive; `--clear_checkpoints` takes the no-prompt branch. The command binds MLP AlphaRec, two graph layers, 256 negatives, `lm_model=v3`, τ=0.15, InfoNCE, default seed 101. Data and `item_cf_embeds_large3_array.npy` are external; PyTorch and compiled Cython/C++ artifacts are not hash-locked. | `EVIDENCE_INCOMPLETE` |

## License-scope rule applied

Only one pinned tree, RUCAIBox/UniSRec, contains affirmative license text. Its MIT grant applies to the repository software and associated documentation, subject to the notice condition. It is not a grant for separately downloaded datasets, pretrained checkpoints, text, embedding bundles, or an unspecified RecBole build.

The other repositories are public but unlicensed at the pinned revisions. For LightGCN-PyTorch, QRec, SELFRec, and LightGCL, the absence of a license file remains `NO_AFFIRMATIVE_GRANT_FOUND_AT_PIN`. For AlphaRec, an MIT badge without grant text remains `BADGE_ONLY_NO_AFFIRMATIVE_GRANT_AT_PIN`. Paper-level Creative Commons terms are not code licenses.

## Source-tree implications

All six distinct pinned repositories were replayed through complete, non-truncated GitHub recursive trees. No tree contains `.gitmodules`, `.gitattributes`, a gitlink (`160000`), or a symlink entry (`120000`). This is tree-level evidence only; it does not prove that runtime materialization has no external or generated artifacts.

- LightGCN-PyTorch, QRec and SELFRec contain processed dataset files as regular Git blobs. Their presence closes only file identity at the commit, never provider rights or lineage.
- LightGCL contains regular Yelp/Gowalla pickle blobs and regular dataset zip blobs. Extraction remains a future, separately authorized operation.
- UniSRec contains README placeholders rather than the Scientific dataset or pretrained checkpoint. Its preprocessing guide explicitly creates symlinks with `ln -s`; this conflicts with the later no-symlink runtime namespace unless a change-controlled regular-file materialization is specified.
- AlphaRec contains Cython/C++ evaluator source but no dataset or embedding bundle. A future build would generate native artifacts and requires a compiler/toolchain receipt.

## Fail-closed disposition

R2-A1 returns six `EVIDENCE_INCOMPLETE` rows and one `DISPOSITIVE_REJECT`. The XSimGCL rejection is lane-dispositive because a three-layer center cannot be joined to the only pinned two-layer config. No candidate is promoted, accepted, selected, materialized, or authorized.

Lane verdict: `COMPLETE_FAIL_CLOSED_READY_FOR_CENTRAL_G1`.

This verdict means only that the A1 evidence packet is complete enough for central intersection. It is not reproduction readiness and grants no acquisition or execution authority.
