# R5-M0 source-only materialization operation log

Created: 2026-08-23T00:42:43+07:00

R5-S0 v2 passed before checkout. The preflight correction narrowed the
RecBole sparse policy to exclude nested example-data files and corrected
nonexistent RecBole-GNN paths. The initial Windows Schannel metadata-clone
attempt failed before target creation; the OpenSSL retry materialized Git
metadata only. No source blob was checked out before the correction.

## Candidate receipts

- R5-CAND-RECBOLE-BPR-ML100K-001: origin and detached HEAD verified; tree 08915121fea069a30f7e3e97a72e16e7e76d43c6; 736 tree entries, 265 materialized files, 1541044 bytes; zero prohibited artifacts, submodules, symlinks, LFS pointers or worktree modifications.
- R5-CAND-RECBOLE-GNN-LIGHTGCN-ML1M-001: origin and detached HEAD verified; tree b9abfd3e61d563b32885839858ff0a3cb09bca09; 78 tree entries, 65 materialized files, 245308 bytes; zero prohibited artifacts, submodules, symlinks, LFS pointers or worktree modifications.

## Persistent boundary

No dataset/checkpoint was acquired; no package/environment was created;
vendor source was neither modified nor executed; preprocessing, training
and evaluation were not run; project v5 TEST was not opened. Numeric
targets remain provisional and invalid for the paper.
