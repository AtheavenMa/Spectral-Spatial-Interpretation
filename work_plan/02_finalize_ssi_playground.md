# Work Plan 02 · Finalize SSI Playground

**Status: TO EXECUTE**
**Date: 2026-10-19**
**Baseline: main at a8842dfc09240a8828cbf4e312bff364a544892a**
**Previous plan: [01_ssi_playground.md](01_ssi_playground.md)**

## 0. Mission

**Finish the entire SSI Playground as a polished, reliable, reproducible, six-model local research application. The sole excluded task is deployment to Hugging Face.**

This plan is an implementation instruction for the next agent, not a request for further planning. Make the code changes, perform real CPU computations, run automated browser tests, measure costs, inspect screenshots, update technical documentation, and record final commits/CI evidence. Do not stop at scaffolding or TODOs. Do not require a local GPU. Use existing six real checkpoints and one real input per model before asking for more data.

**Explicit exclusions:** Do not create, push, publish or deploy any Hugging Face Space, repository, organization integration, account connection or public deployment URL. Keep a local and Docker runnable product ready for later deployment, but do not deploy it.

Keep the presentation as minimal as SAR in Five Minutes: visitors should play with real model inputs and parameters, not read long explanatory text. Keep engineering explanations in docs, not front-end/README. Avoid artificial blocking gates, extensive random seed tests, retraining, full-dataset experiments and extra benchmark scope. For expensive settings, measure cost and implement a useful alternative. Never invent measurements, wavelengths, data provenance or verification claims.

## 1. Current implementation and known gaps

At the baseline commit, these are already present:

- SSI mathematical core in ssi.py with actual observed-context Shapley calculations.
- Six registered model choices: hls-unet, cub-200, eurosat, paviau, salinas, whu-hi-longkou.
- Real weights and model inputs in assets/checkpoints, assets/examples and assets/lab; five new models with SHA-256 entries in assets/lab/manifest.json.
- The original HLS input, inference adapter and demo.py; five additional adapters in lab/adapters/extra.py and backbones.py.
- FastAPI in lab/app.py; UI in lab/static/; real checkpoint inference; baseline/method/grid/seed selection, signed spatial map, channel selection, selected cell, JSON export and reproduction command.
- Six-dataset numeric references in assets/demo_summary.json and assets/lab/references.json.
- Local Docker and CI. The latest pre-plan GitHub Actions run 39330945421 passed.

The added five-dataset reference tests currently use **4x4 grid, mean baseline, 1 permutation, seed 0**. This validates those tested configurations, not the performance of default 8x8/10 permutations on 103, 204 and 270 channels.

Known issues to resolve:
1. High-dimensional default settings may require a large number of actual forward passes; no measured six-model interactive latency/memory matrix yet.
2. Full 103/204/270-band bar charts are not user-friendly.
3. lab/adapters/extra.py uses linearly interpolated wavelength labels for the three hyperspectral cubes. These must not be presented as exact instrument wavelengths without verified metadata.
4. User-facing compute queue, cancellation/progress, rapid model-change race behavior and per-model presets need a final pass.
5. Stored references are produced using the same implementation; add independent correctness checks and distinguish original training-pipeline parity from in-repository repeatability.
6. Work Plan 01 documents an HLS-first app; extend docs and browser tests to six models.

## 2. Release behavior

User sees Model, Input, basic SSI parameters, and **Run SSI**. A run must score true perturbed images using the selected checkpoint and ssi.py, not swap a pre-rendered image.

Afterward users can inspect actual input, GT/true label, prediction, target class, signed spatial SSI, any channel map, and channel importance at a selected cell or summed globally. Grid/baseline/method/permutations actually recompute SSI.

For high-band models, show a compact **Top 10 by absolute signed contribution** with a searchable/browsable complete band selector; do not render 270 bars by default. Preserve all output values and exact original band ordering in downloads.

Reproduce controls should export full attribution and provenance metadata, give a working command for the selected model, and retain URL state (model, sample, grid, baseline, method, permutations, seed and selected channel). Fast model switching must not display a response from a previous model. Details can be expandable; interface text should stay minimal.

## 3. P0 · Six-model numerical, preprocessing and provenance audit

For each of the six:
- Verify strict loading of **actual** checkpoint, architecture and head; validate SHA-256 hashes against every asset in the manifest, input tensor shape, dtype and finite values.
- Reconstruct the model scoring from an independent unperturbed forward pass. Verify target class/logit selection, classification label mapping, segmentation fixed GT target region and ignored labels. The region must be constant across all coalitions.
- Verify normalization parameters and both mean/zero baselines in model input coordinates. Raw zero is not necessarily normalized zero. Preserve spatial cell ordering and resizing semantics.
- Verify displayed input/GT/prediction orientation, preview RGB conversion and actual band order.
- For WHU-Hi-LongKou, investigate manifest region_agreement = 0.44959128065395093. Determine exactly what it measures, check whether the selected target mask/prediction is appropriate, and choose a better existing sample if needed. Do not call this metric accuracy until established.
- Record experiment IDs, model versions, source checkpoint/export method, sample split/index, input preprocessing, class/ROI metadata, hashes and available redistribution/licensing facts. Distinguish verified facts from missing original metadata rather than guessing.

**Band metadata correction**
- Replace interpolated per-band nm labels derived from _waves(...) in PaviaU, Salinas, and WHU-Hi-LongKou. Prefer actual source-provided instrument wavelength centers with original channel selection/removal mapping.
- If exact wavelengths cannot be established, display genuine channel IDs or Band 001, Band 002, etc. Never invent precise nm labels. Include labels and original indices in API/export consistently.
- Preserve verified EuroSAT Sentinel-2 band IDs and named HLS bands. Link source data metadata in technical docs.

**Independent numerical checks**
- Preserve HLS 8x8, mean, permutation 10, seed 0 reference regression.
- For each extra model, run stored 4x4/1-permutation reference and compare spectral totals, full score, evaluation counts, finite values, and local efficiency.
- Independently calculate the unperturbed score and at least one manually masked cell score via direct model calls; compare with summed channel contributions. Do not rely only on saved outputs created by the same run() function.
- Check attribution tensor shape; sum of channels equals spatial per cell; sum of spatial cells equals aggregate spectral totals (but not necessarily global baseline contrast).
- Test low-cost 4x4/8x8/16x16 grids and click-to-cell indexing. Test exact 3-channel CUB result against sufficiently sampled permutation results. For high-channel models use finite-sample efficiency and deterministic repeats, not exponential exact enumeration.
- Clearly separate "verified in current implementation" from "independently matched original experiment" if original training/evaluation code cannot be recovered.

**Deliverables:** updated tests and metadata, docs/PLAYGROUND_VALIDATION.md with actual checked results and commands.

## 4. P0 · Real CPU performance, usability and compute lifecycle

Create benchmarks/playground_cpu.py and docs/PLAYGROUND_PERFORMANCE.md with actual CPU hardware, versions, threads, checkpoint cold load, warm run time, maximum RSS/memory (where measurable), grid, baseline, number of permutations, channels, scored inputs, and forward-batch counts.

**Purposeful execution matrix**
- All six models: start with the already proven 4x4/1-permutation reference.
- HLS, CUB, EuroSAT: measure practical 8x8 and 16x16 settings.
- PaviaU (103 channels), Salinas (204), LongKou (270): progress through 4x4/1, 4x4/3, 8x8/1, and only increase to 8x8/3 or 8x8/10 if the previous costs justify it.
- Do not run unnecessary seed sweeps or enormous full combinatorial evaluations. Report skipped high-cost cases with the measured reason. Do not pretend an estimate is a measurement.

**Implementation**
- Use observed results to choose **model-specific default grid and permutations** and optionally Quick / Balanced / Detailed presets. Avoid applying HLS 8x8/10 to a 270-channel model without measuring it.
- Expose model-specific supported grids, methods, costs and reasonable defaults through the catalog/API. Frontend should not hardcode a separate incompatible copy of backend limitations.
- Display a clear busy/progress state; for large runs implement bounded jobs/queue and cancellation if feasible. Preserve synchronous API compatibility. Avoid a busy 429 as the only understandable user experience.
- Make results safe against races: changing model/input/parameters while an old response runs must not show stale output.
- Cache by checkpoint/input identity and parameters, bounded in memory. Avoid reload of identical checkpoints, excessive CPU threads and inappropriate batching.
- Avoid sending huge uncompressed attribution JSON when this causes delays. Support downloadable complete arrays and optionally compressed transport or per-channel loading. Numerical data may never be silently truncated.
- An advanced expensive choice should be possible within measured safety bounds; otherwise present a measured lower-cost alternative. Do not create arbitrary failure-only tests or unexplained hard blockers.

**Deliverables:** benchmark script, actual results table, per-model defaults, reliable job handling, tests.

## 5. P1 · Visual polish and interaction finish

- Visually follow SAR tutorial philosophy: minimal explanation, large images, clean layout, strong hierarchy, real interactive results, details hidden until requested.
- Remove all hardcoded "HLS", "6 bands" and similar literals from shared UI status, labels, and explanations; use selected model metadata.
- Classification examples should show a real image with true label vs predicted label. Segmentation should show input, GT mask and predicted mask with consistent color interpretation and fixed highlighted target.
- Give spatial-sum attribution a sensible signed scale; channel maps within the same run should use a consistent channel scale. Display legend/range and avoid confusing global and channel normalization.
- For >8 channels build a searchable band selector, compact Top 10 ranking by **absolute** contribution, and a way to view all bands if requested. A selected cell should show its local values, not an unchanged global ranking.
- Ensure click/touch on a cell highlights that cell, updates its channel contribution, and works when the grid is changed.
- Proper states for initial load, busy, invalid input, computation error, completed result, changed parameters, and downloads.
- Support keyboard navigation, accessible controls, 1440x900, 1920x1080, tablet and narrow mobile with no clipped plots or horizontal overflow.
- Make model+sample+settings+channel URL state round-trip, with correct restored selection and no stale requests.
- Add export of all signed numeric arrays plus actual run metadata/hashes; optional image download if it can be made correctly. Reproduce commands must work for all six models, not just the HLS script.

**Browser verification:** extend lab/browser_smoke.py to switch between HLS, CUB, EuroSAT and at least one >100-band model; test actual API-driven results, model-specific labels, baseline/grid, channel search, Top 10, selected cells, URL restore, and mobile. Save desktop/mobile screenshots, inspect them, fix layout defects. Prefer validating all six model previews while using cost-aware SSI settings for browser integration.

## 6. P1 · Finalize the actual API / local SDK

Original requirement: **checkpoint + input + SSI settings -> true explanation and visualization**.

Keep existing registered-model workflow:
- GET /api/health, /api/catalog, /api/preview and POST /api/explain, plus OpenAPI docs.
- Strong request validation, structured responses and useful errors.
- Model capabilities and defaults supplied by the backend. No arbitrary user-controlled server file paths or remote checkpoint execution.

Add a documented **local extension path**:
- Python API or CLI accepting one supported-architecture checkpoint, matching input file, fixed target/ROI and SSI parameters.
- Explicit validation of channel count, preprocessing, tensor format, class label/mask and baseline. An arbitrary checkpoint of an unknown architecture is not universally supported.
- Reuse existing adapter where possible; demonstrate on at least one known real sample. Wrong-shape input and invalid model checkpoint must fail clearly.
- If upload over the web would compromise safety or require expensive architecture work, keep browser options allowlisted and support local sample/checkpoint paths only in the trusted local CLI.
- Provide a maintained runnable reproduction CLI for non-HLS examples (not just an ad hoc Python -c command). Every command displayed in the UI must be tested.

**Deliverables:** documented local API/CLI, reproducible commands and negative/positive integration tests.

## 7. P1 · Docs, package, assets and release readiness

- Keep main README short: title, paper link, representative images, short local Playground quickstart, 57-image Visual Atlas, citations. No verbose defensive explanations.
- Move provenance, CPU benchmark results, validation, method details, troubleshooting and dataset constraints to docs/.
- Add docs/PLAYGROUND_QUICKSTART.md, docs/PLAYGROUND_VALIDATION.md and docs/PLAYGROUND_PERFORMANCE.md. Update deploy/README.md for local Python and Docker only. Do not publish a Space.
- Check a fresh clone, dependency installation, Python support, CPU wheel, original demo.py, existing mathematical tests, model/input assets, Docker size, permissions and static assets. Use .dockerignore to avoid packaging caches/test artifacts.
- Verify that weights and samples have appropriate source/redistribution attribution. The root MIT license should not be implied to cover third-party datasets/checkpoints.
- Maintain existing SSI core, original HLS demo, paper figures, 57 PNG gallery and tutorial links intact.
- Avoid unnecessary files in root, large regenerated figures, placeholder demos, or renamed concepts.

## 8. Acceptance matrix: execute, observe and report

| Area | Minimum actual verification |
|---|---|
| Mathematics | toy additive/interactive games, per-cell efficiency, deterministic sampling |
| HLS | reference 8x8 / 10-permutation parity and original CLI |
| All six models | original checkpoint + real input, 4x4 / 1-permutation, saved-reference agreement |
| Independently scored mask | direct manual perturbation for every adapter family |
| Baselines | mean and zero with fixed target for one RGB, HLS, and one hyperspectral case |
| Grids | 4, 8, 16 where cost appropriate; measured high-channel ramp |
| Metadata | true model/sample hashes, band mapping, target, licenses, LongKou region agreement |
| GUI | six models browsable; relevant real runs, band selector, Top 10, cell, export, URL restore |
| CLI/API | valid/invalid inputs, supported custom sample/checkpoint, reproducible commands |
| Docker | image builds, health, actual inference request and browser smoke |
| Usability | inspected screenshots desktop/mobile, no overflow, simple interaction |
| Regression | original demo, existing tests and Visual Atlas paths |

GitHub Actions must pass **on the final SHA**; an earlier green CI run is not sufficient to claim final completion.

Keep experimental scope purposeful: one verified sample per dataset is enough. If one expensive configuration cannot finish within reasonable CPU capacity, implement a tested quick mode and document the realistic boundary instead of marking the entire project a failure.

## 9. Execution order (complete the work)

1. Audit all six models; correct true band names, preprocessing/target metadata and LongKou region issue.
2. Add CPU performance benchmark, run the inexpensive measurement ramp, choose model defaults and safe compute handling.
3. Implement polished high-band UI, top-10/search, model-aware preview/results, proper plot scaling, exports and state.
4. Finish local programmatic API/CLI with supported user-owned inputs and actual model-specific reproduction commands.
5. Extend numerical regression tests and the six-model browser/Docker smoke tests; run and fix. Inspect screenshots.
6. Update quickstart, provenance, validation/performance reports and concise README.
7. Record actual findings in this document. Commit changes and confirm the final GitHub Actions run passes.

Parallelize independent code tasks where useful, but do not race commits for the same files. If a configuration fails, diagnose the exact failure and provide a justified, functioning alternative. Do not conclude with a plan instead of implementation.

## 10. Final completion checklist

- [ ] Six models correctly use actual checkpoints, inputs and fixed scoring targets.
- [ ] Checkpoint hashes, preprocessing, source attribution and numeric correctness audited.
- [ ] All wavelength labels are true source data or honest original channel IDs.
- [ ] LongKou region-agreement issue investigated and documented.
- [ ] Real per-model CPU time and memory recorded; practical defaults/presets enabled.
- [ ] Large hyperspectral channel selection and Top 10 are usable.
- [ ] Compute lifecycle prevents stale output and provides responsive user feedback.
- [ ] Full exports and working reproducible CLI/API commands for all supported models.
- [ ] Original HLS demo still runs; complete numerical and regression tests pass.
- [ ] Multi-model desktop/mobile browser tests and Docker tests pass.
- [ ] README, asset notices, quickstart, validation, performance docs and local Docker setup finished.
- [ ] Final main SHA and green Actions URL recorded here, with real measured numbers.
- [ ] **No Hugging Face deployment performed.**

### Execution log (fill during the work)

Record what changed, files touched, measured per-model CPU times/memory, verified band sources, failed/changed configurations and fixes, screenshot paths, latest CI URL, final commit SHA, and any narrowly stated remaining non-deployment limitation. Do not check off an item on the strength of a plan alone.

### Final handoff

Deliver an explicit six-model support table, chosen default parameters, real CPU timing summary, test results, local run instructions, sample non-HLS reproduction command, screenshot previews, and the finished commit/CI link. Confirm explicitly that Hugging Face has **not** been deployed.
