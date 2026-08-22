# R6-E1 RecBole environment risk report

## Verdict and boundary

**Verdict: HIGH-CONFIDENCE CURRENT CPU PROFILE PROPOSED, NOT MATERIALIZED.** The selected target is official CPython 3.11.9 x86-64 on Windows with `torch==2.2.2+cpu`, NumPy 1.26.4, and the exact direct pins in `environment_lock_proposal.json`. Confidence applies to the evidence-backed proposal and wheel availability, not to runtime behavior. No environment, package, wheel, hash, import receipt, dataset, model run, or benchmark result was created in R6-E1.

This is a current compatibility proposal for RecBole source revision `9a6f63d8d4a5b989fe27955a833f813a6d86041e`. It is not a reconstruction of the unknown historical producer environment behind README NDCG@10=0.2768. That number remains provisional documentation only and is not producer-bound or paper-valid.

## Source-derived dependency boundary

The pinned `setup.py:9-30` provides lower bounds, two exact legacy pins, a Ray upper bound, and a Hyperopt extra. It does not provide `python_requires`, a platform marker, a lock, or a modern build-system declaration. `requirements.txt` is not identical: it includes `hyperopt==0.2.5` and relaxes the color packages, whereas `setup.py` treats Hyperopt as an extra and requires `colorlog==4.7.2` and `colorama==0.4.4`. This proposal treats `setup.py` as the install-metadata authority and records its lower bounds separately from the proposed exact lock.

The minimum BPR/ML-100K source and import closure is CPython, RecBole, torch, NumPy, SciPy, pandas, scikit-learn, PyYAML, tqdm, colorlog, colorama, and texttable. The relevant source locators include:

- configuration/YAML: `recbole/config/configurator.py:18,477-511`;
- data: `recbole/data/dataset/dataset.py:18-25` and `recbole/data/interaction.py:15-18`;
- evaluator: `recbole/evaluator/metrics.py:27-30`;
- BPR/all-general-model import surface: `recbole/model/general_recommender/__init__.py:1-33` and `bpr.py`;
- utilities/logging: `recbole/utils/utils.py:20-26` and `recbole/utils/logger.py:23-27`.

TensorBoard, Ray, THOP, Plotly, tabulate, and psutil are not intrinsic to BPR math. They are kept separate as optional-feature packages. Some nevertheless enter the exact lock because the legacy package metadata declares them as hard dependencies, `recbole.utils` unconditionally imports TensorBoard's `SummaryWriter` (`recbole/utils/utils.py:25`), `recbole.quick_start` unconditionally imports `ray.tune` (`recbole/quick_start/quick_start.py:20`), or the stock path calls `get_flops` before fitting (`quick_start.py:141`; `utils.py:250-330`). Including a package does not authorize its feature.

Hyperopt, W&B, accelerator packages, distributed launchers, and non-BPR model ecosystems are excluded. Hyperopt imports are contained in tuning helpers (`recbole/trainer/hyper_tuning.py:25-411`), and W&B is lazy behind `log_wandb` (`recbole/utils/wandblogger.py:21-38`; default false at `recbole/properties/overall.yaml:15`).

## Authoritative current compatibility evidence

All web evidence below was retrieved on **2026-08-23**.

| Component | Primary evidence and implication |
|---|---|
| CPython 3.11.9 | The [official Python 3.11.9 release page](https://www.python.org/downloads/release/python-3119/) identifies it as the last 3.11 bugfix release and provides the official 64-bit Windows installer. The [Python version-status table](https://devguide.python.org/versions/) keeps 3.11 in security support through 2027-10 but explains that security-phase releases are source-only. |
| PyTorch CPU | The [official previous-version instructions](https://pytorch.org/get-started/previous-versions/) specify the CPU-only index for torch 2.2.2 on Windows/Linux. The [official CPU wheel index](https://download.pytorch.org/whl/cpu/torch/) lists a `2.2.2+cpu` CPython 3.11 Windows AMD64 wheel. [PyPI torch 2.2.2 metadata](https://pypi.org/project/torch/2.2.2/) independently shows a CPython 3.11 Windows AMD64 public-version wheel. |
| NumPy | [NumPy 1.26.4 distribution metadata](https://pypi.org/project/numpy/1.26.4/) requires Python >=3.9 and provides a CPython 3.11 Windows AMD64 wheel. The official [NumPy 2.0 migration guide](https://numpy.org/doc/2.0/numpy_2_0_migration_guide.html) documents a major compatibility boundary; pinning 1.26.4 avoids adding it to this legacy closure. |
| Scientific/tabular/evaluator stack | [SciPy 1.11.4](https://pypi.org/project/scipy/1.11.4/), [pandas 2.1.4](https://pypi.org/project/pandas/2.1.4/), [scikit-learn 1.3.2](https://pypi.org/project/scikit-learn/1.3.2/), and [PyYAML 6.0.2](https://pypi.org/project/PyYAML/6.0.2/) publish CPython 3.11 Windows AMD64 wheels and declare compatible Python floors. |
| Optional-but-included import/metadata packages | [TensorBoard 2.15.2](https://pypi.org/project/tensorboard/2.15.2/) supports Python 3.11 and provides a universal wheel. [Ray 2.6.3](https://pypi.org/project/ray/2.6.3/) provides a CPython 3.11 Windows AMD64 wheel at the source-declared upper bound. The selected [THOP release](https://pypi.org/project/thop/0.1.1.post2207130030/), [Plotly 5.18.0](https://pypi.org/project/plotly/5.18.0/), [tabulate 0.9.0](https://pypi.org/project/tabulate/0.9.0/), [texttable 1.7.0](https://pypi.org/project/texttable/1.7.0/), [psutil 5.9.8](https://pypi.org/project/psutil/5.9.8/), [tqdm 4.66.5](https://pypi.org/project/tqdm/4.66.5/), [colorlog 4.7.2](https://pypi.org/project/colorlog/4.7.2/), and [colorama 0.4.4](https://pypi.org/project/colorama/0.4.4/) have official release metadata/wheels satisfying the source bounds. |
| Reproducible installation method | pip's [repeatable-install guidance](https://pip.pypa.io/en/stable/topics/repeatable-installs/) distinguishes exact pins, hashes, and wheelhouses. Its [secure-install guidance](https://pip.pypa.io/en/stable/topics/secure-installs/) requires complete hashes, supports binary-only installs, and recommends `pip --no-deps` rather than direct `setup.py install`. [`pip download` documentation](https://pip.pypa.io/en/stable/cli/pip_download/) explains wheel collection for later offline installation. The [Python 3.11 `venv` documentation](https://docs.python.org/3.11/library/venv.html) defines isolated environment creation. |

## Risk register

### R1 — Python patch-level security versus official Windows binary availability (medium)

Python 3.11.9 is the last normal bugfix release with the official Windows installer, but it has been superseded by source-only security releases. The profile uses 3.11.9 because Ray 2.6.3 and the selected binary stack have an evidenced CPython 3.11 Windows closure and because relying on an unofficial or locally compiled interpreter would reduce reproducibility. The environment must remain isolated, non-service-facing, and bounded to research materialization. Any requirement for network-facing or production use requires a new profile and security review.

### R2 — PyTorch/NumPy/wheel ABI load risk (medium until imports pass)

Wheel existence proves distribution availability, not that every DLL loads on the future host. `torch==2.2.2+cpu`, NumPy, SciPy, pandas, scikit-learn, PyYAML, psutil, and Ray include platform-specific wheels. Windows runtime prerequisites, CPU instruction support, PATH/DLL interactions, or a wrongly selected wheel can still fail at import. The materializer must accept only CPython 3.11 Windows AMD64/pure wheels, reject source builds and accelerator artifacts, and then assert exact versions, `torch.version.cuda is None`, and `torch.cuda.is_available() is False`.

NumPy is capped at 1.26.4 to avoid the NumPy 2.0 boundary. This does not make every optional source path compatible: `recbole/trainer/hyper_tuning.py:386` uses `np.str`, which is absent in modern NumPy. Hyperparameter visualization is therefore explicitly prohibited rather than silently patched.

### R3 — Transitive dependency conflict risk (medium until resolver closure)

The direct pins are exact, but R6-E1 did not download metadata or resolve transitive wheels. TensorBoard and Ray share transitive areas such as protobuf and requests; pandas, scikit-learn, SciPy, and THOP constrain NumPy/torch; Plotly adds packaging/tenacity; scikit-learn adds joblib/threadpoolctl. A high-confidence direct profile can be proposed because the primary distributions support CPython 3.11 Windows, but only an actual binary-only resolver closure can establish one exact transitive set.

The later gate must capture one actual wheel per normalized identity, the resolver logs/report, and a locally computed SHA-256. It must then generate a complete, fully pinned `requirements-hashed.txt` and install it offline with `--require-hashes --no-deps`. Public index hashes observed during research are not copied into this proposal; doing so would falsely imply those exact files had been materialized.

### R4 — Legacy setup.py behavior (medium)

The source has no `pyproject.toml`, `setup.cfg`, `python_requires`, console entry point, platform lock, or historical lock. Direct `python setup.py install/develop` is prohibited. The proposal pins `pip==24.0`, `setuptools==69.5.1`, and `wheel==0.43.0`, verifies source bytes, copies the source to a writable staging area, and proposes `python -m pip wheel --no-deps --no-build-isolation`. Any deprecation failure, undeclared build dependency, metadata drift, network access, or source mutation is an escalation condition, not permission to update build tools or patch the source.

### R5 — Ray and distributed behavior (medium, feature excluded)

Ray 2.6.3 is included because it is the setup upper bound and `recbole.quick_start` imports `ray.tune` unconditionally. This does not authorize `ray.init`, worker launch, `tune.run`, distributed sampling, or the stock hyperparameter script. RecBole's `nproc>1` branch initializes NCCL/CUDA (`recbole/config/configurator.py:496-511`), so the profile hard-requires `nproc=1`, `world_size=-1`, `use_gpu=false`, and an empty `gpu_id`. A Ray import failure blocks the stock quick-start import closure; it does not justify dropping Ray or switching versions without a new reviewed proposal.

### R6 — Hyperopt, Plotly, TensorBoard, THOP, and W&B (medium/low by isolation)

- **Hyperopt:** excluded because it is a setup extra and all tuning is prohibited. The differing `requirements.txt` must not be installed wholesale.
- **Plotly:** installed only to satisfy setup metadata; visualization is prohibited and the `np.str` source usage is known-incompatible.
- **TensorBoard:** feature use is prohibited, but the package is required for the unconditional `SummaryWriter` import. No event writer is to be instantiated in materialization checks.
- **THOP:** installed at the exact source floor. Import compatibility with torch 2.2.2+cpu must pass; profiling must not run in this stage.
- **W&B:** excluded; `log_wandb=false` is mandatory and no external account/network integration is allowed.

### R7 — Stock entrypoints cross the execution boundary (high if invoked)

`run_recbole.py:46` calls the stock runner. `recbole/quick_start/quick_start.py:95-170` builds data, computes FLOPs, calls `trainer.fit`, evaluates test data, and reports results. `run_hyper.py` and `hyper_tuning.py` launch tuning/evaluation paths. None may be invoked for environment closure. The proposed bounded checks import modules and compile syntax only; they do not instantiate `Config`, create a dataset, preprocess ML-100K, train, evaluate, tune, download checkpoints, open project v5 TEST, or admit a result.

### R8 — Historical provenance remains unresolved (high for any paper claim)

The pinned source tree establishes code provenance, not producer-environment provenance. No historical interpreter, package inventory, command receipt, dataset bytes, split artifact, seed receipt, checkpoint, or evaluation receipt binds README NDCG@10=0.2768 to this proposed environment. Even a successful future materialization would only establish a current runnable profile. Project benchmark numbers remain `INVALID_FOR_PAPER` until a separately authorized execution and benchmark-admission process produces accepted result rows.

## Exact fail-closed escalation conditions

The later central materializer must stop and request a new reviewed environment decision if any of the following occurs:

1. Official CPython 3.11.9 x86-64 cannot be selected exactly, or the interpreter is not CPython/Windows/64-bit.
2. Any frozen source file is missing or differs in size/SHA-256, or the revision/tree identity differs from `9a6f63d8d4a5b989fe27955a833f813a6d86041e` / `08915121fea069a30f7e3e97a72e16e7e76d43c6`.
3. The materialization root already exists, or any write would escape its exact allowlist or touch `00_control`, the frozen source, or this R6-E1 closure.
4. A requested direct version is unavailable, a transitive conflict occurs, more than one wheel is selected for an identity, or the resolver would substitute any direct pin.
5. Any package requires an sdist/egg/local compilation, or any wheel tag is not CPython 3.11 Windows AMD64 or an allowed pure-Python tag.
6. A host outside `pypi.org`, `files.pythonhosted.org`, `download.pytorch.org`, or its official payload redirect appears in package-resolution logs.
7. torch is not exactly `2.2.2+cpu`, its actual wheel is not from the official CPU index, or any CUDA/ROCm/nvidia/triton artifact appears.
8. Any actual wheel hash, size, filename, normalized identity, version, or second deterministic resolution differs from the captured closure. No pre-download hash in this proposal may be treated as an actual receipt.
9. The RecBole wheel build reaches the network, mutates frozen inputs, requires an undeclared build dependency, produces zero/multiple wheels, or emits name/version metadata other than RecBole 1.2.1.
10. `pip check`, an exact version assertion, a bounded import, TensorBoard/Ray/THOP import closure, the CPU assertions, or syntax compilation fails.
11. A proposed/assembled command contains training, evaluation, preprocessing, tuning, dataset download/open, checkpoint activity, project TEST access, `run_recbole.py`, `run_hyper.py`, `trainer.fit`, `trainer.evaluate`, `tune.run`, or `ray.init`.
12. A timeout, 2 GiB wheelhouse limit, 4 GiB materialization limit, single-process limit, or zero-GPU/zero-Ray-worker condition is exceeded.

No escalation condition authorizes an automatic fallback. Changing Python, torch, NumPy, Ray, a direct pin, package index, source revision, source bytes, platform, or excluded feature requires a new evidence-backed proposal and central approval.

## Persistent truth

`RESULT_STATUS=NOT_RUN`; `TEST_SET_OPENED=NO`; `ACCEPTED_RESULT_ROWS=0`; `execution_authorized=false`; project benchmark numbers are `INVALID_FOR_PAPER`.
