# R2-ER1-A1 LightGCN repository and license report

## Decision

`E3-LIGHTGCN-GOWALLA-PYTORCH-001` is `EVIDENCE_INCOMPLETE` with the fail-closed disposition `KEEP_PENDING`.

The SIGIR paper confirms a PyTorch implementation at the original `gusye1234/pytorch-light-gcn` path, which GitHub redirects to the archived `gusye1234/LightGCN-PyTorch` repository. The repository is pinned to commit `947ca2b3b1d2d3545b114145710cb06c4e57b3d2` and root tree `69cd7ff201f745598757cc99566705aa0364c2f6`. The complete recursive tree resolves to 43 entries and is not truncated.

No affirmative code-use or reuse license was found at that pin. The complete tree contains no `LICENSE`, `LICENCE`, `COPYING`, `COPYRIGHT`, or `NOTICE` path; the pinned README provides no permission grant; and official GitHub repository metadata reports no detected license. These are negative observations only. Public visibility, paper publication, and absence of a license file do not create permission. This report is an evidence determination under the frozen contract, not legal advice.

No experiment, preprocessing, training, evaluation, or test-set access was performed. `RESULT_STATUS=NOT_RUN`, `TEST_SET_OPENED=NO`, `execution_authorized=false`, and no candidate was selected.

## Primary evidence

- The author-hosted SIGIR proceedings copy states that TensorFlow and PyTorch implementations are available and links the original PyTorch repository on page 1, footnote 2, and page 6, footnote 7: <https://hexiangnan.github.io/papers/sigir20-LightGCN.pdf>.
- The official arXiv record fixes the paper identity as `arXiv:2002.02126v4` and DOI `10.1145/3397271.3401063`: <https://arxiv.org/abs/2002.02126>.
- The paper author's SIGIR slides identify the current repository as the PyTorch code on slide 24: <https://hexiangnan.github.io/slides/sigir20-slides-LightGCN.pdf>.
- The original paper URL redirects to the current repository: <https://github.com/gusye1234/pytorch-light-gcn>.
- Immutable commit: <https://github.com/gusye1234/LightGCN-PyTorch/commit/947ca2b3b1d2d3545b114145710cb06c4e57b3d2>.
- Immutable root tree through the official GitHub API: <https://api.github.com/repos/gusye1234/LightGCN-PyTorch/git/trees/69cd7ff201f745598757cc99566705aa0364c2f6?recursive=1>.
- Pinned README and repository command: <https://github.com/gusye1234/LightGCN-PyTorch/blob/947ca2b3b1d2d3545b114145710cb06c4e57b3d2/README.md#L33-L39>.

Search results were used only for discovery. Closure claims use the direct paper, author slides, immutable repository files or Git objects, and official repository metadata.

## Paper-to-repository binding

The relationship status is `CONFIRMED_PAPER_LINK_WITH_RENAMED_PATH_REDIRECT`. This establishes that the repository is the paper-linked PyTorch implementation. It does not establish the stronger proposition that every later revision was authored or maintained by a listed paper author: source headers credit Jianbai Ye, while the pinned 2023 tip commit is authored by Hozayfa El Rifai.

The TensorFlow repository remains a separate implementation and was not substituted or cross-joined.

## Immutable repository identity and boundaries

The pinned identity is:

- repository: `https://github.com/gusye1234/LightGCN-PyTorch`
- full commit: `947ca2b3b1d2d3545b114145710cb06c4e57b3d2`
- root tree: `69cd7ff201f745598757cc99566705aa0364c2f6`
- commit parents: 1
- recursive tree entries: 43
- recursive tree truncated: false
- archived repository: true

The tree has no gitlink (`160000`) entries, `.gitmodules`, symlink (`120000`) entries, `.gitattributes`, or tree-level Git LFS marker. `code/sources/sampling.cpp` is an ordinary repository blob, not a submodule.

External and generated boundaries remain separate: Python dependencies, unspecified-version `pybind11` and `cppimport` build dependencies, the generated compiled sampler extension, generated checkpoints, and TensorBoard runs are not immutable repository-owned execution receipts. Bundled Gowalla files prove only their Git blob identities; R2-ER1-A1 does not decide dataset rights or raw-to-processed lineage.

## Repository-owned command and configuration

The pinned README publishes this command from the repository's `code` directory:

```text
cd code && python main.py --decay=1e-4 --lr=0.001 --layer=3 --seed=2020 --dataset="gowalla" --topks="[20]" --recdim=64
```

At the pin, this resolves through `code/main.py`, `code/parse.py`, `code/world.py`, and `code/register.py` to `lgn -> model.LightGCN` and `gowalla -> ../data/gowalla`. The command consumes parser defaults including batch size 2048, 1000 epochs, no graph dropout, model `lgn`, checkpoint directory `./checkpoints`, and TensorBoard enabled. The model uses 64-dimensional embeddings, three propagation layers, a uniform mean over layers 0 through 3, normal initialization with standard deviation 0.1, Adam at learning rate 0.001, and pairwise BPR softplus loss with L2 coefficient 0.0001. `code/main.py` contains no validation stage or early stopping and overwrites `lgn-gowalla-3-64.pth.tar` after each epoch.

The command identity is confirmed at the pin, but the executable semantics for the printed center are not complete. `code/utils.py` attempts a `cppimport`/`pybind11` sampler and falls back to Python after any import or build exception. No command-line option selects the branch. The C++ branch samples a fixed per-user count, whereas the Python branch samples random users for `trainDataSize` iterations. The README center has no receipt identifying which branch ran, and `requirements.txt` omits versions and hashes for both build dependencies.

## Center/config mismatch

The paper Table 3 center and the pinned PyTorch README center are distinct and must not be cross-joined:

| Dimension | SIGIR paper | Pinned PyTorch repository |
| --- | --- | --- |
| Gowalla batch size | 1024 | 2048 |
| Embedding initialization | Xavier | normal, standard deviation 0.1 |
| Selection rule | validation and early stopping as in NGCF | fixed loop; no validation or early stopping |
| Three-layer Recall@20 | 0.1823 | 0.1824 |
| Three-layer NDCG@20 | 0.1555 | 0.1547 |

The repository README additionally reports Precision@20 `0.05589` for seed 2020 and stop at 1000 epochs. Its command is partially bound to that repository-owned center, but no immutable executed-config dump, sampler-branch receipt, checkpoint hash, or run log closes the execution identity.

## License scope

The license status is `NO_AFFIRMATIVE_CODE_USE_GRANT_FOUND_AT_PIN` for repository-owned Python source, C++ sampler source, and repository documentation. No SPDX identifier or license file is established. Dependency licenses, any paper distribution terms, and the arXiv record do not transfer a license to repository code. Processed Gowalla artifacts are outside this A1 license decision.

Because affirmative permission is required by the frozen evidence contract, the missing code-use basis alone prevents `EVIDENCE_SUFFICIENT_FOR_G1_REVIEW`.

## Retrieval incidents

- ACM and DOI landing-page retrieval returned HTTP 403. Needed paper claims were resolved through the author-hosted proceedings copy and official arXiv record; no ACM-only claim was used.
- Browser retrieval of the GitHub commit/tree API intermittently returned an internal error, and the first sandboxed PowerShell request failed authentication/TLS handling. An approved read-only replay against the official GitHub API succeeded.
- Browser retrieval of several raw repository files returned cache-miss/internal errors. Their exact immutable blobs were decoded in memory from the official GitHub blob API.

No source payload was saved, no repository was cloned or fetched, and no archive, dataset, or checkpoint was downloaded.

## Remaining blockers

1. No affirmative code-use or reuse license basis exists in the authoritative evidence at the pinned revision.
2. The sampler branch that produced the printed repository center is not identified.
3. `pybind11`, `cppimport`, and the generated extension are not pinned by version and artifact hash.
4. Paper and repository settings/results differ and must remain separate.
5. No immutable executed-config, run, or checkpoint receipt binds the repository center.

The lane is complete as evidence work but remains fail-closed: `EVIDENCE_INCOMPLETE`, `KEEP_PENDING`, and not execution-authorized.
