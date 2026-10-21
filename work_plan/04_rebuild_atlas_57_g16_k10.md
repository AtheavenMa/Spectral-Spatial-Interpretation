# Work Plan 04 — Regenerate All 57 SSI Atlas Images

## Goal
Recompute and **replace the original 57 Atlas PNGs** with genuine SSI results using **grid=16×16, method=permutation, permutations=10, baseline=mean, seed=0**. Preserve every existing image path and filename.

## Input
Use `docs/playground/atlas-catalog.json` as the definitive 57-image list and `docs/playground/compute-manifest.json` plus `docs/playground/assets/samples/<dataset>/<sample>/` for the verified original tensors, metadata, GT masks, and model checkpoints. Six groups: CUB_200 (10), EuroSAT (10), HLS_BurnScars (10), PaviaU (10), Salinas (10), WHU_Hi_LongKou (7). Exclude the separate `hls-bundled` demo.

## Execution
1. Run `python tools/export_playground_assets.py validate --require-complete`. Verify all 57 original inputs, channel counts, checkpoints, fixed targets and checksums.
2. Build a resumable **offline** batch script to compute SSI for every registered sample using the real PyTorch model and all original channels. Do not use the interactive Playground's restrictive grid/permutation caps. Run CUDA with safe batching if available, otherwise CPU. Keep the rest of the input observed when perturbing one cell. Use each sample's recorded **normalized mean baseline** (HLS mean is nonzero), original target-class logit, and original fixed GT region for segmentation. Do not reconstruct inputs from old PNGs.
3. For each sample compute real signed `attribution[16,16,C]`, `spatial[16,16]` and `spectral[C]`, then render with the current `lab/atlas_plot.py` layout. Preserve authentic positive/negative signs, GT, channel labels, and the recently removed “Shared signed channel scale” caption. For 103/204/270-channel inputs, compute **all** channels but display the existing top-channel selection.
4. Stage outputs as `atlas.png`, `result.json`, `attribution.npz` in a separate temporary directory for each ID; checkpoint progress, resume completed validated samples, and log runtimes/errors. Only after validation, replace the exact **57 existing** files `examples/<dataset>/sample_<id>.png` without creating new public filenames.
5. Audit all 57 images and numerical results: grid=16; permutations=10; seed=0; baseline=mean; valid target/mask; finite values; `spatial == attribution.sum(axis=2)`; `spectral == attribution.sum(axis=(0,1))`; local efficiency and model full-score consistency. Ensure 57/57 generated, replaced and visually readable. Produce a concise manifest/report with sample ID, model, paths, settings, hashes, evaluation count, runtime, validation result.
6. Commit and push the 57 replacements and batch script to GitHub. Confirm the existing `examples/README.md`, catalog, and image links still resolve. Report the commit SHA, counts, failures (if any), and test results.

## Boundaries
Do **not** change training, checkpoints, source assets, paper results, Playground defaults, UI, or the root README. The additional root README showcase `examples/HLS_BurnScars/sample_0163_mean_g16_k5.png` is **not** among the 57 and must remain untouched. No generated imagery, invented measurements, simulated attribution, resampling from previous PNGs, or reduced settings. Do not report completion if any of the 57 required images fails.
