# SSI Playground · 57-sample asset contract

**Target:** the existing 57 Atlas examples must be individually selectable and recomputable from their corresponding original model input, actual checkpoint and a fixed target. The 57 original PNGs are visual references, **not** input data for inference.

This is a machine-executable handoff specification for the local data/GPU agent. The browser implementation and registry already exist in `docs/playground/`; the source exporter is `tools/export_playground_assets.py`. The local Python generation API is `python -m lab.cli atlas`.

## 1. Inventory, no substitutions

| Dataset | Original channels | Atlas figures | Exact sample identifiers |
|---|---:|---:|---|
| CUB-200 RGB classification | 3 | 10 | sample_0158, sample_0714, sample_1125, sample_1631, sample_2002, sample_2390, sample_3296, sample_4020, sample_4136, sample_4325 |
| EuroSAT multispectral classification | 13 | 10 | sample_1294, sample_1972, sample_2190, sample_2247, sample_2390, sample_2995, sample_3042, sample_3276, sample_4044, sample_4141 |
| HLS Burn Scar segmentation | 6 | 10 | sample_0045, sample_0052, sample_0067, sample_0076, sample_0106, sample_0120, sample_0127, sample_0163, sample_0187, sample_0222 |
| Pavia University hyperspectral segmentation | 103 | 10 | sample_0003, sample_0006, sample_0008, sample_0010, sample_0011, sample_0012, sample_0013, sample_0016, sample_0017, sample_0027 |
| Salinas hyperspectral segmentation | 204 | 10 | sample_0000, sample_0001, sample_0002, sample_0004, sample_0005, sample_0006, sample_0010, sample_0011, sample_0012, sample_0014 |
| WHU-Hi-LongKou hyperspectral segmentation | 270 | 7 | sample_0000, sample_0001, sample_0002, sample_0003, sample_0004, sample_0005, sample_0006 |

**Current status:** 57 indexed gallery examples are awaiting source-data registration; the separately bundled `hls-bundled` example has verified browser computation. Five original NPZ/checkpoint pairs exist in `assets/lab/` but **must be individually matched and visually verified** against their Atlas figure before promotion to `ready`. `HLS` bundle is not evidence that it matches any of the ten HLS gallery filenames.

## 2. Required assets per dataset

For each **sample**, provide the exact original normalized model input (all channels, C × H × W, float32), fixed target and provenance. For non-HLS families package:

- `x`: model-normalized `float32[C,H,W]`, contiguous or safely convertible.
- `mean` and `std`: finite `float32[C]` matching original preprocessing; every std strictly positive. These determine the mean and raw-zero baselines.
- `target_class`: fixed integer class ID using the same checkpoint class mapping.
- `label`: `H×W` GT labels for segmentation and a nonempty region equal to `target_class`; for classification labels are optional.
- `rgb`: aligned true-color/pseudo-RGB `uint8[H,W,3]` for display; do not convert the model's spectral tensor into three channels.
- Matching `.json` sidecar with **`atlas_id`** equal to the exact registry ID (e.g. `PaviaU/sample_0008`), dataset split/index/crop, target class/name, input shape and data license/source. An `index` alone is accepted by the CLI for backwards compatibility, but `atlas_id` is preferred for reliable matching.

For **HLS**, supply NPZ with original raw reflectance `image[6,H,W]` and GT `mask[H,W]` with valid labels `0,1,255`, fixed burn target 1, and the matching `.json` sidecar. Do not normalize HLS a second time.

For each **model family**, supply/confirm the actual trained checkpoint and its architecture, class/channel ordering, preprocessing version, original source and license. Export one ONNX model per family with batch-dynamic input for web inference. Check that all sample shapes are compatible with the ONNX export (or document a deterministic resolution/padding strategy and update the exporter to support it). **Do not regenerate fake checkpoints or infer high-dimensional data from rendered PNGs.**

Source checkpoint locations:

| Model ID | Checkpoint | Browser ONNX destination |
|---|---|---|
| `cub-200` | `assets/lab/checkpoints/cub_resnet18.pt` | `docs/playground/assets/models/cub-200/model.onnx` |
| `eurosat` | `assets/lab/checkpoints/eurosat_resnet18.pt` | `docs/playground/assets/models/eurosat/model.onnx` |
| `hls-unet` | `assets/checkpoints/hls_unet.pt` | `docs/playground/assets/hls_unet.onnx` |
| `paviau` | `assets/lab/checkpoints/paviau_unet.pt` | `docs/playground/assets/models/paviau/model.onnx` |
| `salinas` | `assets/lab/checkpoints/salinas_unet.pt` | `docs/playground/assets/models/salinas/model.onnx` |
| `whu-hi-longkou` | `assets/lab/checkpoints/longkou_unet.pt` | `docs/playground/assets/models/whu-hi-longkou/model.onnx` |

## 3. Required local-agent execution

From a clean checkout, install the project, ONNX and ONNX Runtime libraries. First validate the manifest without requiring missing assets:

~~~~bash
python tools/export_playground_assets.py validate
~~~~

**Batch import:** fill the 57 `source` paths in `docs/playground/57_sources.template.json` with exact original NPZ files. Do not overwrite missing paths with other samples. Run:

~~~~bash
python tools/export_playground_assets.py batch \
  --mapping docs/playground/57_sources.template.json \
  --report outputs/atlas_57_import_report.json
~~~~

The batch report lists successes, skipped missing sample paths and per-item errors. It does not promote an unverified sample. Individual commands below are useful for diagnosing a specific source.

For every model family with a real checkpoint and a matching real NPZ, export and verify:

~~~~bash
python tools/export_playground_assets.py model --id paviau \
  --checkpoint assets/lab/checkpoints/paviau_unet.pt \
  --sample assets/lab/samples/paviau_0008.npz
~~~~

For **each of the 57 exact Atlas IDs**, export its full original input and provenance sidecar:

~~~~bash
python tools/export_playground_assets.py sample \
  --id PaviaU/sample_0008 \
  --source /path/to/original/validated/sample_0008.npz
~~~~

The exporter generates `meta.json`, `x.f32`, `rgb.webp` and a `mask.u8` where required, writes SHA-256 checksums and original tensor metadata, and marks a sample ready **only when both verified ONNX and complete source input are present**. It never uses the gallery PNG as the SSI input.

For one example per family, generate an independently inspectable numerical/visual reference:

~~~~bash
python -m lab.cli atlas --family paviau \
  --checkpoint assets/lab/checkpoints/paviau_unet.pt \
  --image /path/to/original/validated/sample_0008.npz \
  --grid 4 --baseline mean --method permutation --permutations 1 --seed 0 \
  --output outputs/paviau_0008
~~~~

This produces `atlas.png`, `result.json` and `attribution.npz`. Compare sample input/target, orientation and model score against the original experimental code. The original Atlas figures may use different SSI parameters or sampling seeds; report such differences rather than modifying numerical results to match pixels.

**Final completeness check, only once all assets are supplied:**

~~~~bash
python tools/export_playground_assets.py validate --require-complete
python tools/test_browser_web.py
~~~~

The first command must count **57 ready gallery examples**; the second must exercise real browser computation and every dataset selection. Use the existing GitHub Actions browser test and create any additional high-band parity/budget checks needed.

## 4. Browser metadata contract

`docs/playground/compute-manifest.json` is authoritative for model IDs, sample IDs, status and published asset paths. One `sample` record is identified by `{dataset}/sample_NNNN`; the separate `hls-bundled` is a runnable demonstration outside the numbered 57.

Each ready sample's `meta.json` must contain:

- `version=1`, `sample_id`, `model_id`, `width`, `height`
- `channels` in the exact order used by the checkpoint, `target_class`, `target_name`, `target_kind`
- `baseline_mean[C]`, `baseline_zero[C]`, `reference_full_score`
- `region_pixels` for segmentation, SHA-256 of original checkpoint and original sample, and per-file SHA-256/byte length metadata

The web inference contract is `Float32Array[C,H,W] → ONNX float32[batch,C,H,W] → logits`, with a fixed target class or fixed GT-region mean logit. `SSIComputeRuntime.explain(ctx, {grid,baseline,permutations,seed})` returns `attribution[grid][grid][C]`, `spatial[grid][grid]`, `spectral[C]`, and numerical provenance. The renderer interpolates **only visual maps**. Every numeric export preserves original cell/channel scores.

Do not set `status: ready` by hand or bypass the model/sample parity checks.

## 5. Final quality gates and delivery

The local agent must provide:

1. Dataset-by-dataset input provenance and exact mapping for all 57 Atlas files; count and checksum lists.
2. Checkpoint hash, ONNX hash, unmasked and at least one masked PyTorch-vs-ONNX parity per family; correct class/band labels. Use verified original band IDs rather than interpolating wavelengths.
3. A ready manifest and all referenced static files (or a documented external asset host with immutable URLs), with GitHub Pages size/load constraints observed.
4. Measured browser CPU cost at K=1/3/5 and grid 4/8 where practicable, including high-band memory; choose safe default/preset per model, not an invented latency.
5. Representative full-size Atlas PNG+JSON+NPZ produced by the Python API per family; inspect overlays and target region for alignment, no prediction panel.
6. Green CPU math tests, full browser tests, CSS/mobile checks, and the production Pages link after publishing updated assets.

If an original input/checkpoint/provenance is unavailable, **report the exact sample ID as blocked** and leave it as `awaiting_assets`; do not mark a fake success, substitute another crop or promote an unverified PNG.

No Hugging Face deployment is requested; keep the static site on the existing GitHub Pages.
