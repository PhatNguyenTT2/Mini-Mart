# Stage 1E Rebaseline v2 — official training pipeline command map

Material Passport: `ars-codex:academic-research-suite/experiment-agent` v0.1.26; mode `plan`; model `gpt-5.6-sol`; reasoning `xhigh`; date 2026-08-22; status **UNVERIFIED**; version `Stage 1E Rebaseline v2 / Wave A / E1`.

This is a source-discovery lock, not an execution sheet. No command below was run. `RESULT_STATUS=NOT_RUN`, `ACCEPTED_RESULT_ROWS=0`, and `TEST_SET_OPENED=NO`. Dataset acquisition and dataset licensing are deliberately absent and remain E2 work. Commands from different repositories do not imply comparable splits, negatives, candidates, metrics, or reported centers.

Status vocabulary: `VERIFIED` means the entrypoint and literal command/config surface were observed in an immutable official repository. `VERIFIED_COMPOSED` means a method name was inserted into an official generic CLI without changing the method. `PENDING` means the repository does not expose that stage or an E2/E3/E4 decision is required.

## Framework controls: Random, MostPop, ItemCF/ItemKNN, BPR-MF

Authority: RecBole at [`7b02be5ec80a88310f2d04a27a82adfcbb5dc211`](https://github.com/RUCAIBox/RecBole/commit/7b02be5ec80a88310f2d04a27a82adfcbb5dc211), provenance `FRAMEWORK_AUTHORITATIVE`. The paper authors did not provide a singular official executable repository for these heuristic/classical controls in the sources found. RecBole is not promoted over author code for any paper method.

| Stage | Exact locked surface | Status | Direct evidence and locator |
|---|---|---|---|
| Input preprocessing | `run_recbole.py` calls the RecBole `Dataset`/`create_dataset` and `data_preparation` pipeline; no separate preprocessing command is required for an atomic dataset | VERIFIED | [`run_recbole.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/run_recbole.py), argument parser and `run_recbole`; [`docs/user_guide/usage/data_flow.md`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/docs/source/user_guide/usage/data_flow.md), atomic files → Dataset → DataLoader |
| Random | `python run_recbole.py --model=Random --dataset=ml-100k` | VERIFIED_COMPOSED | [`run_recbole.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/run_recbole.py), `--model`/`--dataset`; [`random.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/model/general_recommender/random.py), class `Random` |
| MostPop | `python run_recbole.py --model=Pop --dataset=ml-100k` | VERIFIED_COMPOSED | [`pop.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/model/general_recommender/pop.py), class `Pop`; generic CLI above |
| ItemCF/ItemKNN | `python run_recbole.py --model=ItemKNN --dataset=ml-100k` | VERIFIED_COMPOSED | [`itemknn.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/model/general_recommender/itemknn.py), `ItemKNN`; [`ItemKNN.yaml`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/properties/model/ItemKNN.yaml), `k`, `shrink`, `knn_method` |
| BPR-MF | `python run_recbole.py --model=BPR --dataset=ml-100k` | VERIFIED | [`README.md`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/README.md), Quick Start; [`bpr.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/model/general_recommender/bpr.py), BPR model/loss |
| Train/evaluate | The command performs `Trainer.fit()` and `Trainer.evaluate()` in one flow | VERIFIED | [`quick_start.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/quick_start/quick_start.py), dataset creation, data preparation, `fit`, `evaluate` |
| Checkpoint | `saved/<model>-<dataset>-<timestamp>.pth` when `saved=True` | VERIFIED | [`trainer.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/trainer/trainer.py), `checkpoint_dir`, `saved_model_file`, `torch.save` |
| Results | logger emits `best valid result` and `test result` dictionaries | VERIFIED | [`README.md`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/README.md), output example |
| Per-user export | Call `full_sort_scores`/`full_sort_topk`; serialize returned score/top-k arrays. Per-user metric rows need a bounded collector before aggregation | VERIFIED_METHOD_PRESERVING_ADAPTER | [`case_study.py`](https://github.com/RUCAIBox/RecBole/blob/7b02be5ec80a88310f2d04a27a82adfcbb5dc211/recbole/utils/case_study.py), `full_sort_scores`, `full_sort_topk` |

Promotion gates: E3 must replace `ml-100k` and RecBole defaults with the locked benchmark dataset/split/evaluator configuration. E4 must review the MIT license file against the repository README’s academic-purpose wording.

## Apriori

Original paper: Agrawal and Srikant, *Fast Algorithms for Mining Association Rules*, VLDB 1994 ([official proceedings PDF](http://www.vldb.org/conf/1994/P487.PDF), title page and Apriori sections). No author-official GitHub implementation was identified.

### Mining component candidate

mlxtend at [`9aadcee334f8b07003246d436cd9135b6d62a6b2`](https://github.com/rasbt/mlxtend/commit/9aadcee334f8b07003246d436cd9135b6d62a6b2), provenance `FRAMEWORK_AUTHORITATIVE`:

```python
te = TransactionEncoder()
te_ary = te.fit(dataset).transform(dataset)
df = pd.DataFrame(te_ary, columns=te.columns_)
frequent_itemsets = apriori(df, min_support=0.6, use_colnames=True)
```

This is the official API pattern in the [mlxtend Apriori user guide](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/apriori/) (Usage/API example) and implementation in [`mlxtend/frequent_patterns/apriori.py`](https://github.com/rasbt/mlxtend/blob/9aadcee334f8b07003246d436cd9135b6d62a6b2/mlxtend/frequent_patterns/apriori.py). It returns a frequent-itemset DataFrame and has no recommender training, evaluation, checkpoint, result, or per-user prediction interface. Status: `REJECTED_END_TO_END`, retained as the authoritative mining component.

### Project Apriori condition

The executable benchmark condition is the project-native `AprioriRuleMiner` plus the raw-lift `WIDE_ONLY` scorer, provenance `INDEPENDENT`, pending a clean immutable source commit.

| Stage | Exact local surface | Status | Direct locator |
|---|---|---|---|
| Snapshot | `.\.venv\Scripts\python.exe -m ai_service.cli snapshot --source postgres --store-id 1 --snapshot-id <new-v5-snapshot-id> --benchmark-run-id <published-v5-benchmark-run-id> --benchmark-spec ..\backend\docs\chatbot\seed-product\benchmark-spec-v5.json --config configs\diagnostics\r3-v5\deep-control.toml` | VERIFIED_FILE_HASH_ONLY / DO_NOT_RUN | `E:/UIT/cv/backend/ai-service/README.md:74-88`, SHA-256 `0460df5104b74f06eab9e3d8dd84edf6785b7d6824541869fc26f2d0879eea38` |
| Rules | `.\.venv\Scripts\python.exe -m ai_service.cli rules --config configs\diagnostics\r3-v5\deep-control.toml --snapshot-id <new-v5-snapshot-id>` | VERIFIED_FILE_HASH_ONLY / DO_NOT_RUN | same README locator; `data/rules.py:291-423`, SHA-256 `ec2fde60f9608ca6b7a8db4eedaaf04bee4891477fc55b49ea0d73fcc4a8fab4` |
| Evaluate | `ai_service.evaluation.baselines.run_full_catalog_comparison` invokes the raw-lift scorer and `FullCatalogEvaluator.evaluate_external_scores(..., variant=ModelVariant.WIDE_ONLY)` | VERIFIED_FILE_HASH_ONLY | `E:/UIT/cv/backend/ai-service/src/ai_service/evaluation/baselines.py:154-170`, SHA-256 `0bac2f0e5f40c68735caebc63fef76a8afc9736a818b3b7a48484a3f21ab2813` |
| Checkpoint | immutable `rules/<artifact-id>/{rules.npz,manifest.json}`; this condition has no learned model checkpoint | VERIFIED_FILE_HASH_ONLY | `data/rules.py:392-422` |
| Results/export | shared evaluation publisher writes `per-user-metrics.npz`, `victory-matrix.json`, `report.json`; top-k predictions exist in memory and need bounded serialization | VERIFIED_FILE_HASH_ONLY | `evaluation/report.py:193-236`, SHA-256 `803e21cb3f99bcf7ee0882ee97887bb6482718fae11dde476974fd529c1c42e9`; `full_catalog.py:55,215` |

## LightGCN

Authority: author repository [`kuandeng/LightGCN@b067ec0`](https://github.com/kuandeng/LightGCN/commit/b067ec05f16a24e0e1efe63cd82385f0c469af20), TensorFlow reference, provenance `AUTHOR_OFFICIAL`.

```bash
python LightGCN.py --dataset gowalla --regs [1e-4] --embed_size 64 --layer_size [64,64,64] --lr 0.001 --batch_size 2048 --epoch 1000
```

- Preprocess: use the included `Data/<dataset>/train.txt` and `test.txt`; compile `evaluator.cpp` as directed. No raw-data converter is provided. Evidence: [README, Environment/Evaluation/Dataset and examples](https://github.com/kuandeng/LightGCN/blob/b067ec05f16a24e0e1efe63cd82385f0c469af20/README.md). Status `VERIFIED`.
- Train/evaluate: [`LightGCN.py`](https://github.com/kuandeng/LightGCN/blob/b067ec05f16a24e0e1efe63cd82385f0c469af20/LightGCN.py), argument parse, epoch loop and `test`; [`batch_test.py`](https://github.com/kuandeng/LightGCN/blob/b067ec05f16a24e0e1efe63cd82385f0c469af20/batch_test.py), evaluation. Status `VERIFIED`.
- Checkpoint/results: enable official `--save_flag 1` for `tf.train.Saver`; result file `output/<dataset>/LightGCN.result`. Same `LightGCN.py`, Saver and output block. Status `VERIFIED`.
- Export: retain `rate_batch`/ranked IDs and `test_one_user` rows before aggregation; bounded adapter, no method change. Status `VERIFIED_METHOD_PRESERVING_ADAPTER`.
- Gate: no code license file was found. Status `PENDING_E4_LICENSE`.

## SASRec

Authority: author repository [`kang205/SASRec@e373896`](https://github.com/kang205/SASRec/commit/e3738967fddab206d6eeb4fda433e7a7034dd8b1), provenance `AUTHOR_OFFICIAL`.

```bash
python main.py --dataset=ml-1m --train_dir=default --maxlen=200 --dropout_rate=0.2
```

The literal training command and the Video/Steam alternatives are under [README Training](https://github.com/kang205/SASRec/blob/e3738967fddab206d6eeb4fda433e7a7034dd8b1/README.md). Preprocessing is [`data/DataProcessing.ipynb`](https://github.com/kang205/SASRec/blob/e3738967fddab206d6eeb4fda433e7a7034dd8b1/data/DataProcessing.ipynb); `util.py:data_partition` performs leave-last-two splitting. [`main.py`](https://github.com/kang205/SASRec/blob/e3738967fddab206d6eeb4fda433e7a7034dd8b1/main.py) trains, calls `evaluate_valid`/`evaluate`, and writes `<dataset>_<train_dir>/args.txt` and `log.txt`. There is no persistent checkpoint in the locked script. Predictions and per-user metric rows can be serialized from `model.predict` and `util.evaluate` before aggregation without changing the method. All surfaces `VERIFIED`; checkpoint `VERIFIED_NONE`.

## BERT4Rec

Authority: author repository [`FeiSun/BERT4Rec@615eaf2`](https://github.com/FeiSun/BERT4Rec/commit/615eaf2004abecda487a38d5b0c72f3dcfcae5b3), provenance `AUTHOR_OFFICIAL`.

```bash
./run_ml-1m.sh
```

- Preprocess: [`gen_data_fin.py`](https://github.com/FeiSun/BERT4Rec/blob/615eaf2004abecda487a38d5b0c72f3dcfcae5b3/gen_data_fin.py) writes TFRecord, vocabulary and user-history artifacts; the official ML-1M wrapper is [`run_ml-1m.sh`](https://github.com/FeiSun/BERT4Rec/blob/615eaf2004abecda487a38d5b0c72f3dcfcae5b3/run_ml-1m.sh). Status `VERIFIED`.
- Train/evaluate/checkpoint/results: [`run.py`](https://github.com/FeiSun/BERT4Rec/blob/615eaf2004abecda487a38d5b0c72f3dcfcae5b3/run.py), `--do_train`, `--do_eval`, Estimator `checkpoint_dir`, checkpoint cadence and `eval_results.txt`. Status `VERIFIED`.
- Alternative official wrappers: `run_ml-20m.sh`, `run_beauty.sh`, `run_steam.sh` in the [locked tree](https://github.com/FeiSun/BERT4Rec/tree/615eaf2004abecda487a38d5b0c72f3dcfcae5b3). Dataset licenses remain `PENDING_E2`.
- Export: bounded Estimator prediction/logit collector and pre-aggregation metric collector. Status `VERIFIED_METHOD_PRESERVING_ADAPTER`.

## BTBR / Mask-Swap-NNBR

Authority: author repository [`liming-7/Mask-Swap-NNBR@8e0b796`](https://github.com/liming-7/Mask-Swap-NNBR/commit/8e0b796a9910888d6a8142f2d39dc7cbe87e349c), provenance `AUTHOR_OFFICIAL`.

```bash
cd nnbr
python train_main_gpu_batch.py --batch_size=64 --bert_loss=1 --dataset=tafeng --dropout_prob=0.1 --epochs=50 --foldk=0 --hidden_size=128 --mask_ratio=0.1 --mask_type=select --nbr_loss=2 --nbr_type=all --swap_hop=1 --swap_ratio=0
```

The literal `python train_main_gpu_batch.py ...` line and W&B sweep use are in the [official README](https://github.com/liming-7/Mask-Swap-NNBR/blob/8e0b796a9910888d6a8142f2d39dc7cbe87e349c/README.md), lines 4–60. The preceding `cd nnbr` is a `VERIFIED_COMPOSED` working-directory precondition inferred from the locked tree (the script is under `nnbr/`) and its `../keyset`/`../mergeddata` paths; it is not printed in the README. The script’s dataset selector covers `tafeng`, `dunnhumby`, and `instacart`; no raw preprocessing command is documented, so preprocessing is `PENDING`. [`nnbr/train_main_gpu_batch.py`](https://github.com/liming-7/Mask-Swap-NNBR/blob/8e0b796a9910888d6a8142f2d39dc7cbe87e349c/nnbr/train_main_gpu_batch.py) performs train/evaluation and writes `pred/.../best_overall_prediction.json`; active checkpoint writes are commented out. Native per-user prediction export is `VERIFIED`; per-user metrics need a bounded collector. Code license and dependency lock are `PENDING_E4`.

## UniSRec

Authority: author repository [`RUCAIBox/UniSRec@05aa5cb`](https://github.com/RUCAIBox/UniSRec/commit/05aa5cba2809112c32808f70d16abc61c05c6538), provenance `AUTHOR_OFFICIAL`.

```bash
python finetune.py -d Scientific -p saved/UniSRec-FHCKM-300.pth
python finetune.py -d Scientific -p saved/UniSRec-FHCKM-300.pth --train_stage=inductive_ft
python finetune.py -d Scientific
python run_baseline.py -m SASRec -d Scientific --config_files=props/finetune.yaml --hidden_size=300
python pretrain.py
CUDA_VISIBLE_DEVICES=0,1,2,3 python ddp_pretrain.py
```

The exact fine-tune/pretrain variants, including the pretrained-model option and multi-GPU launch, are under [README Fine-tuning and Pre-training](https://github.com/RUCAIBox/UniSRec/blob/05aa5cba2809112c32808f70d16abc61c05c6538/README.md). The preprocessing entry is [`preprocess/process_amazon.py`](https://github.com/RUCAIBox/UniSRec/blob/05aa5cba2809112c32808f70d16abc61c05c6538/preprocess/process_amazon.py); parameters are under [`props/`](https://github.com/RUCAIBox/UniSRec/tree/05aa5cba2809112c32808f70d16abc61c05c6538/props). RecBole Trainer supplies `.pth` checkpoints and logged best-valid/test results. Per-user export uses the RecBole full-sort adapter. Entrypoints `VERIFIED`; exact E3 launch command remains `PENDING` until train-stage and target-domain semantics are locked.

## AlphaRec

Authority: author repository [`LehengTHU/AlphaRec@4b6c6cf`](https://github.com/LehengTHU/AlphaRec/commit/4b6c6cf378f292c31dd75b09a8075e8344561415), provenance `AUTHOR_OFFICIAL`.

```bash
pushd models/General/base
python setup.py build_ext --inplace
popd
nohup python main.py --rs_type General --clear_checkpoints --saveID tau_0.15_v3_mlp_ --dataset amazon_book_2014 --model_name AlphaRec --n_layers 2 --patience 20 --cuda 0 --no_wandb --train_norm --pred_norm --neg_sample 256 --lm_model v3 --model_version mlp --tau 0.15 --infonce 1 &>logs/amazon_book_2014_tau_0.15_v3_mlp__2.log &
```

These are literal [README lines 98–147](https://github.com/LehengTHU/AlphaRec/blob/4b6c6cf378f292c31dd75b09a8075e8344561415/README.md#L98-L147); Movie and Game alternatives are adjacent. The repo expects prebuilt data; raw preprocessing is not released. `main.py` and the General runner train/evaluate; checkpoints are `weights/General/<dataset>/<model>/<saveID>/epoch=*.checkpoint.pth.tar`; logs/results are written by the command/runner. `predict(users, items=None)` provides a bounded prediction-export seam. The README’s user-intention datasets and zero-shot scripts are TODO and therefore `REJECTED_NOT_RELEASED`. The MIT badge is not a license grant; code license remains `PENDING_E4`.

## SimGCL

Authority: paper-author framework [`Coder-Yu/QRec@a141bb3`](https://github.com/Coder-Yu/QRec/commit/a141bb37cb7706b2f53b2eed5843de3269f9f37f), provenance `AUTHOR_OFFICIAL` for SimGCL.

```text
python main.py
At the prompt, choose q5 (SimGCL); configuration: config/SimGCL.conf
```

The interactive official flow is documented in [README Usage lines 59–68](https://github.com/Coder-Yu/QRec/blob/a141bb37cb7706b2f53b2eed5843de3269f9f37f/README.md#L59-L68) and wired in [`main.py`](https://github.com/Coder-Yu/QRec/blob/a141bb37cb7706b2f53b2eed5843de3269f9f37f/main.py). [`config/SimGCL.conf`](https://github.com/Coder-Yu/QRec/blob/a141bb37cb7706b2f53b2eed5843de3269f9f37f/config/SimGCL.conf) fixes input paths, ranking/evaluation and output directory. There is no raw preprocessing entrypoint and no persistent checkpoint; QRec writes per-user top-N recommendations and aggregate measures. Prediction export is native, metric rows need a bounded collector. Code license remains `PENDING_E4`.

## XSimGCL

Authority: paper-linked repository [`Coder-Yu/SELFRec@5b02294`](https://github.com/Coder-Yu/SELFRec/commit/5b0229423cb1c727e85a704d63e460368c8b9dde), provenance `AUTHOR_OFFICIAL`.

```text
pip install -r requirements.txt
python main.py
At the prompt, choose XSimGCL; configuration: conf/XSimGCL.yaml
```

The official interactive flow is [README How to Use lines 27–32](https://github.com/Coder-Yu/SELFRec/blob/5b0229423cb1c727e85a704d63e460368c8b9dde/README.md#L27-L32); the model/paper mapping is [lines 57–69](https://github.com/Coder-Yu/SELFRec/blob/5b0229423cb1c727e85a704d63e460368c8b9dde/README.md#L57-L69); the locked config is [`conf/XSimGCL.yaml`](https://github.com/Coder-Yu/SELFRec/blob/5b0229423cb1c727e85a704d63e460368c8b9dde/conf/XSimGCL.yaml). There is no raw preprocessing command or persistent checkpoint; SELFRec writes per-user top-N and aggregate performance. Prediction export is native, metric rows need a bounded collector. README/requirements version conflict and code license are `PENDING_E4`.

## LightGCL

Authority: author repository [`HKUDS/LightGCL@5590453`](https://github.com/HKUDS/LightGCL/commit/5590453ad86782f58017e58d0b698d7f32175be3), provenance `AUTHOR_OFFICIAL`.

```bash
python main.py --data yelp
python main.py --data gowalla --lambda2 0
python main.py --data ml10m --temp 0.5
python main.py --data tmall --gnn_layer 1
python main.py --data amazon --gnn_layer 1 --lambda2 0 --temp 0.1
```

These literal commands and the dataset-directory instructions are [README lines 11–55](https://github.com/HKUDS/LightGCL/blob/5590453ad86782f58017e58d0b698d7f32175be3/README.md#L11-L55). Preprocessing is limited to unzipping supplied matrices; `main.py` loads `data/<dataset>/trnMat.pkl` and `tstMat.pkl`, trains/evaluates, saves model/optimizer under `saved_model/`, and writes `log/result_<data>_<hour>.csv` ([`main.py`](https://github.com/HKUDS/LightGCL/blob/5590453ad86782f58017e58d0b698d7f32175be3/main.py), data load, loop, save, result path). Test-time rankings and pre-mean metric rows provide bounded export seams. Code license remains `PENDING_E4`.

## Local Deep and Hybrid conditions

Authority: project-native code under `E:/UIT/cv/backend/ai-service`, provenance `INDEPENDENT`. The observed Git HEAD is [`31d8092`](https://github.com/PhatNguyenTT2/Mini-Mart/commit/31d8092554119aa7d1ba22db2e094d701ba83c29), but current `cli.py` and `training/pipeline.py` are modified relative to it. The byte hashes in `official_repo_registry.json` are the only present lock; no production execution is authorized until those bytes are committed immutably.

Preprocessing commands copied from `E:/UIT/cv/backend/ai-service/README.md:74-88` (SHA-256 `0460df5104b74f06eab9e3d8dd84edf6785b7d6824541869fc26f2d0879eea38`):

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli snapshot --source postgres --store-id 1 `
  --snapshot-id <new-v5-snapshot-id> --benchmark-run-id <published-v5-benchmark-run-id> `
  --benchmark-spec ..\backend\docs\chatbot\seed-product\benchmark-spec-v5.json `
  --config configs\diagnostics\r3-v5\deep-control.toml
.\.venv\Scripts\python.exe -m ai_service.cli features --embedding-source real `
  --snapshot-id <new-v5-snapshot-id> --config configs\diagnostics\r3-v5\deep-control.toml
.\.venv\Scripts\python.exe -m ai_service.cli rules `
  --config configs\diagnostics\r3-v5\deep-control.toml --snapshot-id <new-v5-snapshot-id>
```

CLI-validated train/evaluate templates (not present as an authorized fresh-production command in the README, hence `VERIFIED_COMPOSED/PENDING_E3`):

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id <deep-run-id> --variant deep_only `
  --config configs\diagnostics\r3-v5\deep-control.toml `
  --snapshot-id <new-v5-snapshot-id> --seed <seed> --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id <hybrid-run-id> --variant hybrid `
  --config configs\diagnostics\r3-v5\hybrid-h0-main.toml `
  --snapshot-id <new-v5-snapshot-id> --seed <seed> --device cuda
.\.venv\Scripts\python.exe -m ai_service.cli evaluate `
  --split val --hybrid-run-id <hybrid-run-id> --deep-run-id <deep-run-id> --device cuda
```

Evidence: `E:/UIT/cv/backend/ai-service/src/ai_service/cli.py:51-79`, SHA-256 `93ce7d1aea4080753fe540103a79da99eb4b721fc8da1c4696666e2e828579d4`; configs SHA-256 `b391445c30d1e8a3afe1690adc59ff0943fd5144b9c5fd92f224621240478a71` and `237a6cbebc6f6e81551d02e2840b8c6c33fbae4fc1e56e36e7c86b2ba26e264b`.

Resume is the only production train form explicitly printed in the README (`README.md:112-121`):

```powershell
.\.venv\Scripts\python.exe -m ai_service.cli train `
  --run-id <interrupted-run-id> --variant <same-variant> `
  --config <same-config> --snapshot-id <same-v5-snapshot-id> `
  --seed <same-seed> --device cuda --resume
```

Checkpoint/results/export:

- `artifacts/runs/<run-id>/checkpoints/best.pt` and `last.pt`; resume requires the latter plus manifest/history. Evidence: README lines 112–121 and local `training/checkpoint.py`. Status `VERIFIED_FILE_HASH_ONLY`.
- `artifacts/runs/<run-id>/evaluation/<split>/per-user-metrics.npz`, `victory-matrix.json`, `report.json`. Evidence: `evaluation/report.py:193-236`, SHA-256 `803e21cb3f99bcf7ee0882ee97887bb6482718fae11dde476974fd529c1c42e9`. Status `VERIFIED_FILE_HASH_ONLY`.
- `EvaluationReport.top_k_by_user` exists in memory; serialization is a bounded adapter and does not change scoring/ranking. Evidence: `evaluation/full_catalog.py:55,215`, SHA-256 `927d1ed05956112e959f4902b3418129db99692db7d899cc25404b31d4feeb6f`. Status `VERIFIED_METHOD_PRESERVING_ADAPTER`.

## Execution lock

Every command remains disabled until E2 dataset authorization, E3 protocol lock, E4 compatibility/license/adaptation review, and E5 independent verification complete. In particular, this map does not authorize package installation, dataset retrieval, preprocessing, training, evaluation, checkpoint creation, W&B upload, or TEST access.
