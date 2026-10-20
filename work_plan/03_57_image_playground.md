# Work Plan 03 · Complete 57-Image SSI Playground

**Status: DONE.** All 57 gallery samples are ready and all six ONNX models are verified. The bundled HLS demo remains a separate seventh runnable input and is not counted in the 57.
**Date: 2026-10-20**
**Execution: local agent asset delivery complete; final verification by assistant**
**Repository: AtheavenMa/Spectral-Spatial-Interpretation, branch main**

## 0. Non-negotiable final product

Deliver a directly accessible GitHub Pages HTML Playground. The visitor can choose **any of the 57 original Visual Atlas examples**, then change grid size, baseline and **Permutations 1 / 3 / 5**, and genuinely recompute SSI using the sample's full original tensor and its matching checkpoint. The result must show (a) Image, (b) GT or target class, (c) spatial SSI overlaid smoothly on the input, (d) spectral channel overlays and (e) signed spectral contributions.

Do not show Prediction, grid-cell outlines as the primary map, debugging model-score or efficiency counters, small unnecessary typography, or unrelated organization branding. Keep the root README's **SSI in Action** to one HLS Burn Scars figure and a Playground link. The root README header already links to the public HTML.

The same files must be usable from a trusted local Python API:
checkpoint + genuine input + fixed target + SSI settings -> atlas.png + result.json + attribution.npz.

**A static existing PNG is not a substitute for a recomputation.** If an original sample is unavailable, the page can still display it in the Visual Atlas, but Run must remain disabled for that sample until the source assets pass validation.

## 1. Engineering already committed

- [x] The 57 figure IDs, datasets and original PNG URLs are indexed in docs/playground/atlas-catalog.json.
- [x] docs/playground/compute-manifest.json contains 57 fully verified gallery inputs and six verified ONNX models. The separate hls-bundled demonstration is independently runnable and excluded from the 57.
- [x] docs/playground/index.html, playground.js and gallery.js implement dataset/image selection, 1/3/5 parameters, actual HLS inference, full Gallery and a ready/pending distinction.
- [x] docs/playground/compute-runtime.js computes observed-context permutation SSI for an arbitrary number of spectral channels using an ONNX scoring adapter; no six-band-only mask assumption.
- [x] tools/export_playground_assets.py has model, sample and validate subcommands, requiring provenance. The model exporter checks unmasked and masked PyTorch/ONNX parity.
- [x] lab/atlas_api.py and lab/atlas_plot.py generate a true Atlas-style PNG, JSON and NPZ for the six supported checkpoint architectures and original inputs.
- [x] Unit tests cover the 57-ID contract, wrong-provenance refusal, genuine NPZ export, batch mapping and unchanged HLS. Chromium tests cover switching, hidden unavailable runs, browser HLS and a 13-channel deterministic additive invariant.
- [x] README shows only one HLS example under SSI in Action, links to Playground, and no longer contains the debug score counter.
- [x] A public GitHub Pages site exists at https://atheavenma.github.io/ssi-playground/ .
- [x] Recompute all 57 figure examples from their **exact original** inputs and models and verify source-to-figure identities.
- [x] Verify CPU/browser performance of all six ONNX exports and complete the production Pages data publication.

The status of an Atlas image must be changed only by validated data export, not by manually changing a JSON flag.

## 1A. Earlier engineering checkpoint (historical, superseded by Section 7)

- **Source main:** [e61da51291c1](https://github.com/AtheavenMa/Spectral-Spatial-Interpretation/commit/e61da51291c1) successfully passed both [Python / numerical / Docker CI 39463374805](https://github.com/AtheavenMa/Spectral-Spatial-Interpretation/actions/runs/39463374805) and [browser / live Pages CI 39463374881](https://github.com/AtheavenMa/Spectral-Spatial-Interpretation/actions/runs/39463374881).
- **Production HTML:** [https://atheavenma.github.io/ssi-playground/](https://atheavenma.github.io/ssi-playground/). GitHub Pages code mirrors `docs/playground/index.html`, `playground.js`, `compute-runtime.js` and `compute-manifest.json` at matching Git blob SHAs. Deploy workflows succeeded for the last mirrored site commit.
- **At that earlier checkpoint only:** 1 verified bundled HLS example, 0 numbered gallery examples. **Superseded:** all 57 gallery samples are now ready, as verified in Section 7.
- **Source asset registry:** 57 exact IDs, including 10 CUB, 10 EuroSAT, 10 HLS, 10 PaviaU, 10 Salinas and 7 LongKou; 6 model adapters are declared. Existing checkpoints plus five NPZ samples may help, but must be associated with the exact gallery source before enabling any Run action.
- **Batch handoff:** fill [57_sources.template.json](../docs/playground/57_sources.template.json), then run `python tools/export_playground_assets.py batch --mapping docs/playground/57_sources.template.json --report outputs/atlas_57_import_report.json`; follow with `validate` and finally `validate --require-complete` when all 57 have authentic source data.
- **Earlier tasks now completed:** the 57 matching source inputs, associated sidecars, five non-HLS ONNX exports and real high-band browser timings are recorded in Section 7.
- **User-facing style:** README has a single HLS visual in `SSI in Action`; the web HTML has 1/3/5 permutation choices, readable typography and no model-score debug line or unrelated lab branding.

### Historical local-agent acceptance (completed)

The completed importer reported all 57 gallery samples ready; no missing IDs remain. The original per-sample identity and ONNX parity checks are documented below.

## 2. Original inputs the local agent must provide

### Exact 57 image inventory

| Dataset | Model ID | Channels | Samples | Exact image IDs |
|---|---|---:|---:|---|
| CUB_200 | cub-200 | 3 | 10 | sample_0158, sample_0714, sample_1125, sample_1631, sample_2002, sample_2390, sample_3296, sample_4020, sample_4136, sample_4325 |
| EuroSAT | eurosat | 13 | 10 | sample_1294, sample_1972, sample_2190, sample_2247, sample_2390, sample_2995, sample_3042, sample_3276, sample_4044, sample_4141 |
| HLS_BurnScars | hls-unet | 6 | 10 | sample_0045, sample_0052, sample_0067, sample_0076, sample_0106, sample_0120, sample_0127, sample_0163, sample_0187, sample_0222 |
| PaviaU | paviau | 103 | 10 | sample_0003, sample_0006, sample_0008, sample_0010, sample_0011, sample_0012, sample_0013, sample_0016, sample_0017, sample_0027 |
| Salinas | salinas | 204 | 10 | sample_0000, sample_0001, sample_0002, sample_0004, sample_0005, sample_0006, sample_0010, sample_0011, sample_0012, sample_0014 |
| WHU_Hi_LongKou | whu-hi-longkou | 270 | 7 | sample_0000, sample_0001, sample_0002, sample_0003, sample_0004, sample_0005, sample_0006 |

**Per-sample mandatory deliverable:** an original tensor NPZ and a JSON provenance sidecar named/associated with the exact Atlas ID. For CUB, EuroSAT, PaviaU, Salinas and LongKou the input NPZ must include x (float32 C,H,W normalized input), mean/std (float32[C]), target_class (integer), rgb (aligned H,W,3), and label H×W for segmentation. For HLS: image (raw reflectance six-band C,H,W) and mask (H,W, 0/1/255). The sidecar must specify atlas_id, source split/index and crop, preprocessing, target identity, model family and licensing metadata. Do not infer spectral bands from an RGB render.

**Model deliverables:** one genuine trained checkpoint per family, its architecture and class/band mapping, reproducible SHA-256, and one ONNX export with unperturbed and masked PyTorch-vs-ONNX parity. Supported model IDs and checkpoint paths are in compute-manifest.json.

**Original sample provenance:** a match between numeric sample index and filename is necessary but not sufficient. Confirm same crop, orientation, target ROI and visualization as the corresponding Atlas PNG. When a sample has no source mapping, report the exact ID; do not use a nearby image as a replacement.

One incomplete HLS sample must not force the other 56 ready inputs to fail their own computation. Preserve independent per-sample statuses.

## 3. Executable ingestion contract

Read docs/PLAYGROUND_57_ASSET_CONTRACT.md first. It contains all field definitions and destination paths. Use **tools/export_playground_assets.py** rather than writing browser data assets by hand.

Install project dependencies, ONNX and ONNX Runtime in an environment with the original data. From the repo root, begin with:

~~~bash
python tools/export_playground_assets.py validate
~~~

**Fastest handoff:** edit docs/playground/57_sources.template.json, filling the source path for each exact original sample ID; keep a missing source set to null, not a substitute image. Then import all known models and samples in one deterministic command:

~~~bash
python tools/export_playground_assets.py batch \
  --mapping docs/playground/57_sources.template.json \
  --report outputs/atlas_57_import_report.json
~~~

Each item reports success, pending input, or the exact failure reason. The importer continues on independently valid samples. Re-run validate after corrections. The following individual commands remain useful for isolated debugging.

For each model, export a real, validated ONNX adapter. Example:

~~~bash
python tools/export_playground_assets.py model \
  --id paviau \
  --checkpoint assets/lab/checkpoints/paviau_unet.pt \
  --sample assets/lab/samples/paviau_0008.npz
~~~

For every **exact** Atlas image ID, export the original tensor and sidecar:

~~~bash
python tools/export_playground_assets.py sample \
  --id PaviaU/sample_0008 \
  --source /path/to/original/validated/sample_0008.npz
~~~

The source must have a sidecar with matching atlas_id, e.g. PaviaU/sample_0008. It must not be a screenshot. The tool writes original float32 input bytes, an aligned image preview, a fixed GT mask if appropriate, metadata, checksums and a registry status update.

Also run the tested trusted-local figure generator for one representative of each family:

~~~bash
python -m lab.cli atlas \
  --family paviau \
  --checkpoint assets/lab/checkpoints/paviau_unet.pt \
  --image /path/to/original/validated/sample_0008.npz \
  --grid 4 --baseline mean --permutations 1 \
  --output outputs/paviau_0008
~~~

Expected outputs: atlas.png, result.json, attribution.npz. Never interpolate the numerical tensor; interpolate only the image display.

## 4. Verification required from the local agent

1. **Asset inventory:** 57/57 IDs and hash/provenance manifest, checkpoint paths and actual inputs; each actual sample's model target and mask independently checked.
2. **Numerical parity:** one direct unmasked PyTorch-vs-ONNX score and at least one masked coalition per model. Verify float tolerances, spatial/spectral sums and local efficiency, with seed/baseline fixed.
3. **Shape/band correctness:** 3, 6, 13, 103, 204 and 270 channels. For high-band cubes use source-provided band IDs and wavelengths only if verified; otherwise Band 001 etc. Keep model input, GT and preview image exactly aligned.
4. **Performance:** measure local browser WASM time/memory per family for grid 4 and K=1; evaluate K=3/5 and grid 8 only as feasible, without expensive full-dataset experiments. Choose default settings grounded in measurement, retain 1/3/5 choices and avoid leaving the public HTML frozen on an impractical run.
5. **UI:** every example is selectable, correct model and image are loaded, Run uses the full original input and never a gallery PNG, and changing parameters changes the computed numerical result. Channel selection, signed alpha overlay, target outline, click-cell scores and JSON export must work after model switching and on mobile.
6. **Technical release:** run full unit tests, the standalone HTML Playwright test, cross-model tests and the --require-complete validation. Publish only validated static assets to the existing AtheavenMa.github.io/ssi-playground path. Don't deploy Hugging Face.

~~~bash
python tools/export_playground_assets.py validate --require-complete
python -m unittest discover -s tests -v
python tools/test_browser_web.py
~~~

Run the final tests against the **actual live Pages URL** once the new files have been deployed, not before the other repository's Pages workflow has finished.

## 5. Acceptance state and nonblocking reporting

The definition of “57 interactive examples completed” is **57 ready gallery samples** (the separately bundled HLS demo does not count), all six model exports verified, with source-input provenance and matching figure/target. Merely having 57 gallery PNGs is not sufficient.

If original training assets are missing, the agent should deliver a machine-readable list of blocked IDs with precise reason, and publish all individually validated samples that are ready. The final report must include:

- Exact counts **ready / pending / verified models**, source/hashes, and original sample identities.
- A representative Atlas PNG and JSON/NPZ from each ready model family, verified live HTML behavior and performance measurements.
- All commits pushed to main, the production Pages deployment commit/URL, passing browser and CI URLs.
- Any remaining missing sample IDs; no invented provenance, guessed checkpoints, fabricated wavelength metadata or artificial default results.

## 6. Separate assistant engineering closeout

The assistant should finish and commit all available framework/API/UI work **before** the local data handoff: fix races on model/image switching; validate checksums and registration metadata; test generic spectral scoring with a deterministic multi-channel fake adapter and real HLS; keep public HTML/source mirror in sync; and make sure 57 image selectors, 1/3/5 UI, readable font sizes and the concise README survive full automated checks.

After that, the local agent's only necessary contributions are the original missing assets, trusted model export and the final 57-sample CPU/browser performance and visual match verification.

**Do not create Work Plan 04 for this same milestone. Update this file with progress/results and close it when the sources become available.**

## 7. Closeout (October 20, 2026)

`python tools/export_playground_assets.py validate --require-complete` reports `ready_gallery: 57`, `pending: 0`, and verified models `cub-200`, `eurosat`, `hls-unet`, `paviau`, `salinas`, `whu-hi-longkou`. No sample was skipped or substituted. Five previously published single-sample NPZ files match the corresponding Atlas tensors with max absolute difference 0. Ground-truth class names match the dataset index. For the six misclassified CUB/EuroSAT figures, the fixed explained class is the predicted class recorded with that figure, not the ground-truth label.

ONNX parity (max absolute logit error, unmasked / one masked coalition):

| Model | ONNX SHA-256 | Unmasked | Masked |
|---|---|---:|---:|
| cub-200 | `73b966713cca5f8ec5fe0fdd7923a9a00d4c15393828735672a4ebf9360d7368` | 1.3e-6 | 6.7e-6 |
| eurosat | `8ad2e8849544e1167c8db59bf254901346a7aacefeb287f6a0a12eb601c60155` | 1.7e-6 | 1.9e-6 |
| paviau | `2baec31d6c25b6df945a1ee7871f4e4f9ea38c9ce9f2b59f81f613efd507bde6` | 3.8e-6 | 4.8e-6 |
| salinas | `cd0b38d973d479945a69d5721601505da3b24999d970be81ed157858100dc5ce` | 1.9e-6 | 1.9e-6 |
| whu-hi-longkou | `8bef52619dde424c613ceae5f0af22bd735da45d00552733b47ab06acbd68967` | 2.1e-6 | 1.9e-6 |

HLS keeps the previously verified ONNX `486994917c4501964bec765be8cf4a330fa8a31aa4e058dec80744391abeb493`. Hyperspectral channel names stay `Band 001` onward because the MAT cubes have no wavelength vector.

Browser grid 4 / 1 permutation wall times, including model download, are in `docs/PLAYGROUND_PERFORMANCE.md`. The slowest measured run is WHU-Hi-LongKou at 94.7 s and 4321 evaluations. The static page therefore opens at grid 4 and 1 permutation; 3 and 5 remain selectable. One Python Atlas figure per family (grid 4, 1 permutation, seed 0) finished with local efficiency 0.

Blocked IDs: none. Hugging Face was not deployed.

### Final-release verification

- GitHub `main` at `cf2d8a8a4a1f` delivered all 57 original gallery tensors and five additional ONNX exports.
- [Full numerical / API / Docker CI](https://github.com/AtheavenMa/Spectral-Spatial-Interpretation/actions/runs/39484880345) passed on that asset commit.
- [HTML and live GitHub Pages browser CI](https://github.com/AtheavenMa/Spectral-Spatial-Interpretation/actions/runs/39484880328) passed on the same asset commit, including loading a 270-band LongKou sample and switching back to HLS.
- The complete 57-sample directory inventory in `docs/playground/assets/samples/` was independently confirmed in both the source repository and `AtheavenMa.github.io/ssi-playground/`. The published model and sample assets are not merely manifest placeholders.
- A separate six-model one-cell real-inference regression test was added as `tools/test_browser_six_models.py` / `.github/workflows/six-model-browser.yml` to test every model numerically with a bounded CPU budget. Record its final Actions outcome here after the test completes.
- Browser usability: the default 4×4 / K=1 path has measured CPU latency by model. Higher K and grid sizes use more evaluations and may be slow on high-dimensional samples. The UI retains 1 / 3 / 5 selections; no fabricated low latency is claimed.

**Project state:** feature-complete and published on GitHub Pages; no additional local input assets are requested for Work Plan 03. Only CI and any final bugs discovered in end-to-end tests remain within this same plan.

