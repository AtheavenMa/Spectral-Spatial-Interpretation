# Work Plan 01 · SSI Interactive Playground

Status: **CPU implementation and automated verification complete.** Real-checkpoint tests, reference parity, Docker API smoke test, headless desktop/mobile interactions all passed on GitHub Actions. External Space publication and five additional dataset assets remain pending.
Date: 2026-10-19
Repository: [Spectral-Spatial-Interpretation](https://github.com/AtheavenMa/Spectral-Spatial-Interpretation)

## 1. Goal and product behavior

Build a SAR-inspired interactive SSI HTML research demo with very little narration. A visitor chooses a real checkpoint (via a supported model option), a real input, and SSI settings, presses **Run SSI**, then explores genuinely recalculated spatial and channel contributions.

The initial live demonstration is the bundled 6-band HLS Burn Scar sample and its pretrained UNet. We do not need local GPU files to complete it. The six-dataset PNG Visual Atlas remains an independent browsing gallery.

The user flow is:

1. Select **Model** and **Input** from the registered catalog.
2. Choose **Grid** (4×4, 8×8, or 16×16), **Baseline** (mean/zero), **Method** (auto/permutation/exact), permutations, and seed.
3. Click **Run SSI**. The server loads the real checkpoint/input and uses the actual SSI Shapley implementation.
4. Inspect RGB input, fixed ground truth and model prediction.
5. Toggle Spatial or one of six spectral channels; click any cell to see its six contributions, or view the global channel totals.
6. Export numeric JSON and copy the exact CLI command to reproduce the run.

The site must never swap a PNG in place of recomputing SSI when the user changes grid or baseline. All displayed attribution numbers originate from the model/scoring adapter and ssi.py.

## 2. What is now in the repository

| File | Function | Status |
|---|---|---|
| lab/app.py | FastAPI routes, validated request schema, static hosting, single-compute lock | [x] committed |
| lab/engine.py | Genuine bundled checkpoint+NPZ loading, previews, SSI calls, cache and output schema | [x] committed |
| lab/static/index.html | Compact SAR-inspired webpage | [x] committed |
| lab/static/style.css | Desktop/mobile layout, warm light + navy design | [x] committed |
| lab/static/app.js | Parameter controls, HTTP calls, signed map canvas, cell/channel scores, exports | [x] committed |
| tests/test_lab.py | CPU integration tests using real HLS checkpoint and input | [x] test source committed; execution requires CI confirmation |
| requirements_lab.txt / requirements_lab_test.txt | Runtime and test dependencies | [x] committed |
| Dockerfile | CPU PyTorch + FastAPI container, port 7860 | [x] committed |
| deploy/README.md | Local, Docker, Spaces, API and test instructions | [x] committed |
| lab/adapters/pending_models.json | Non-runnable slots for five extra datasets | [x] committed |
| lab/adapters/README.md | Required adapter and asset schema | [x] committed |
| .github/workflows/tests.yml | CPU tests and JavaScript syntax check | [x] source updated; wait for Actions result |
| README.md | Lab entrypoint and local run commands | [x] source updated |

### Available assets, no GPU request

- Real checkpoint: `assets/checkpoints/hls_unet.pt`; exported tensor-only UNet weights, architecture in `model.py`.
- Real original prepared sample: `assets/examples/hls_sample.npz`; normalized in `hls.py`; fixed GT burn region.
- Attribution algorithm: `ssi.py`, unchanged.
- Runnable paper-aligned adapter: `hls.py`, using six bands Blue, Green, Red, NIR, SWIR1, SWIR2.
- Preserved CLI: `demo.py`; same model, target and baseline semantics.

## 3. API contract and reproducibility

```http
GET  /
GET  /api/health
GET  /api/catalog
GET  /api/preview?model_id=hls-unet&sample_id=hls-burn-scar
POST /api/explain
```

Example POST:

```json
{
  "model_id": "hls-unet",
  "sample_id": "hls-burn-scar",
  "grid": 8,
  "baseline": "mean",
  "method": "permutation",
  "permutations": 10,
  "seed": 0
}
```

Response data: `attribution[grid][grid][6]`, `spatial[grid][grid]`, `spectral[6]`, full score, evaluation count, method, max local-efficiency error, channel names, model/sample IDs, parameters and CLI reproduction command.

The baseline/target remain fixed across all coalitions, and outside the target cell the actual input stays observed. The spatial sum per cell must equal the difference between the complete input score and that same input with the cell masked. The global sum over cells need not equal a global input-to-baseline contrast.

Security/compute rules: no arbitrary filesystem paths or untrusted pickle/checkpoint uploads via HTTP; allowlisted model/sample IDs only; CPU compute is serialized; input options constrained to tested configurations. Exact enumeration supports 4×4 and 8×8 for the six-channel demo; 16×16 uses <=10 permutations.

## 4. Verification checklist

Completed in source:

- [x] Genuine CPU inference path wired to the existing checkpoint and NPZ.
- [x] No fabricated metrics, no fake outputs and no gallery PNG substitution in the interactive results.
- [x] Grid/baseline/method/seed/permutation controls propagated to SSI.
- [x] Valid JSON output shape and interactive 2D signed attribution visualization.
- [x] Channel selection, selected-cell bar chart, export and reproduction command.
- [x] API input validation and basic compute concurrency protection.
- [x] FastAPI integration tests and GitHub Actions CPU tests + Docker service smoke test pass.

Remaining confirmation tasks (not GPU tasks):

- [x] GitHub Actions tests pass with CPU PyTorch and actual HLS checkpoint (including JavaScript syntax validation).
- [x] Default 8×8, mean baseline, 10 permutations, seed 0 run agrees with assets/demo_summary.json spectral totals and 2,152 evaluations.
- [x] Headless Chromium checked desktop/mobile, input previews, real grid change, channel selection, cell inspection, and zero horizontal mobile overflow; saved screenshots as GitHub Actions artifacts.
- [x] GitHub Actions built the CPU Docker image, started the FastAPI service, checked asset readiness, and requested genuine 4×4 SSI inference.
- [ ] Publish a Docker Hugging Face Space under the desired account/organization once write access and Space name are available.
- [ ] Validate live Space CPU cold start, memory and multi-visitor behavior.

## 5. Additional dataset placeholders: exact assets needed

`lab/adapters/pending_models.json` lists CUB-200, EuroSAT, PaviaU, Salinas and WHU-Hi-LongKou as **not yet runnable**. Each currently has pre-rendered PNGs, not a confirmed complete checkpoint + original input + scoring adapter bundle.

For **each** dataset, the GPU/research agent should hand off:

1. **Checkpoint:** tensor-only model state with an SHA-256, original training experiment ID, epoch/checkpoint selection rationale and license/provenance. If the checkpoint is a large file, store it under a Hugging Face model repository or use Git LFS, not ordinary Git blobs.
2. **Exact model loader:** architecture/module code, configuration, framework versions and a minimal inference snippet that loads the state strictly.
3. **Real input:** at least **one** original, unrendered image/cube tensor or path to publicly redistributable sample data, preferably NPZ; include GT/class if used, channel order, original units, shape and sample ID. A screenshot/PNG of an SSI figure does not suffice.
4. **Preprocessing:** resizing, normalization statistics, band selection, no-data handling, shape/channel conventions, and exactly how the training pipeline transformed this sample.
5. **Fixed scalar target:** for classifiers, specify the target-class logit and whether class comes from a fixed GT label; for segmentation, specify target-class logit and a fixed spatial region, never a region recomputed from masked predictions.
6. **Baseline:** mean/zero choices in model-normalized units and how the means were calculated. Ensure the zero choice is unambiguous.
7. **Channel metadata:** human-readable band names or physical wavelengths; no meaningless numeric channel labels.
8. **Reference:** command, sample input/checkpoint hashes, grid/method/seed and a stored numeric attribution output to check against.
9. **Licensing:** permission for model weights, representative sample, annotations and rendered preview in a public Space.

Dataset-specific intake:

| Dataset | Model/input contract | Notes |
|---|---|---|
| CUB-200 | RGB classifier checkpoint, preprocessing and target class | Three channels; exact subset enumeration inexpensive |
| EuroSAT | 13-band classifier checkpoint, 13-band input and ordered bands | Prefer permutation-based SSI |
| PaviaU | Hyperspectral segmentation/classification model, spectral cube, annotation/ROI | Supply band wavelengths and fixed target region |
| Salinas | Hyperspectral model, cube, label mapping and fixed target | Report spectral band selection/removal |
| WHU-Hi-LongKou | Hyperspectral model, cube, labels and channel metadata | Specify the precise evaluation crop |

Do **not** train substitute checkpoints merely to make a button work. Use artifacts corresponding to the actual examples/experiments. If a checkpoint is unavailable, keep that entry unselectable until the real artifacts arrive.

## 6. Adapter integration procedure

1. Place a validated loader under `lab/adapters/<dataset>.py`. Follow [adapter contract](../lab/adapters/README.md).
2. Reuse `ssi.explain` without changing its mathematical semantics. Implement a value function from (batch, grid², C) Boolean coalitions to a 1D scalar score vector.
3. Return previews, channel names and target metadata in the same API schema.
4. Add the validated model/input IDs to `/api/catalog`, and route the request to the new adapter.
5. Test at least one CPU-compatible small setting, compare numeric output with independent CLI, and only then enable the option.
6. Cache repeated parameter combinations by artifact hash + model/input ID + grid/baseline/method/permutations/seed. Preserve exact values in downloads.

GPU tasks are limited to finding/exporting unavailable training artifacts, preparing representative raw samples, and possibly generating reference outputs for large models. The HLS example needs none of that.

## 7. Local commands

```bash
python -m pip install -r requirements_lab_test.txt
python -m unittest discover -s tests -v
uvicorn lab.app:app --host 127.0.0.1 --port 7860
```

Visit http://127.0.0.1:7860, choose grid 4/8/16 and Run SSI. Inspect /docs for the interactive JSON API.

## 8. Definition of done

**CPU milestone:** the bundled checkpoint + NPZ load on CPU; the HTML runs genuine Shapley attribution under changed grid and baseline; signed maps, channel totals and cell values correspond to the returned arrays; download/reproduction work; integration tests are green; page is usable on desktop/mobile.

**Publication milestone:** same source serves successfully through a public Docker Space, with acceptable CPU latency and no unsafe upload/execution path.

**Expansion milestone:** each new dataset is enabled separately after its real checkpoint, raw input, metadata, scalar target, preprocessing and numeric reproducibility checks are available. Never mark a placeholder as runnable based solely on PNGs.
