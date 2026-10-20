# Playground validation

Checked on the six registered models. Each row is one real checkpoint and one real input. "Verified here" means this repository reproduced the check. It is not a claim that an external training log was reopened, except where a file in this repo already records that fact.

## Models

| Model | Checkpoint | Input | Target | Band labels |
|---|---|---|---|---|
| hls-unet | `assets/checkpoints/hls_unet.pt` | `assets/examples/hls_sample.npz` | Mean burn-class logit on pixels whose fixed mask equals 1. 255 is ignored. | Blue, Green, Red, NIR, SWIR1, SWIR2 |
| cub-200 | `assets/lab/checkpoints/cub_resnet18.pt` | test index 158, `cub_0158.npz` | Logit of class 6, Parakeet Auklet, fixed before masking | Red, Green, Blue after ImageNet normalization |
| eurosat | `assets/lab/checkpoints/eurosat_resnet18.pt` | test index 1294, `eurosat_1294.npz` | Logit of class 2, HerbaceousVegetation, fixed before masking | Sentinel-2 ids B01–B12 with nominal centers |
| paviau | `assets/lab/checkpoints/paviau_unet.pt` | val tile 8, seed 1 | Mean logit of class 8, Self-Blocking Bricks, on the fixed ground-truth region | Band 001–103 |
| salinas | `assets/lab/checkpoints/salinas_unet.pt` | val tile 0, seed 1 | Mean logit of class 2, Brocoli green weeds 2, on the fixed ground-truth region | Band 001–204 |
| whu-hi-longkou | `assets/lab/checkpoints/longkou_unet.pt` | val tile 0, seed 1 | Mean logit of class 4, Broad-leaf soybean, on the fixed ground-truth region | Band 001–270 |

SHA-256 values for the five `assets/lab` files are in `assets/lab/manifest.json`. `tests/test_audit.py` recomputes them. HLS hashes remain in `assets/checkpoints/metadata.json` and `assets/examples/metadata.json`.

Training experiment ids, from the export that produced these tensors:

- CUB-200: `CUB_200/resnet18_mlp/classification/train_1`
- EuroSAT: `EuroSAT/resnet18_mlp/classification/train_1`
- PaviaU, Salinas, WHU-Hi-LongKou: `*/unet/segmentation/basic_1`

The state dicts are tensor-only. Optimizer state was dropped. Segmentation weights still use the training key names and are mapped onto the MIT U-Net blocks by `convert_legacy_state_dict`. The GPL U-Net source is not in this repository.

## Normalization and baselines

Stored inputs are already in the training normalization.

- Mean baseline is the zero vector in that space for CUB, EuroSAT, PaviaU, Salinas and LongKou. For HLS it is `TRAIN_MEAN_NORMALIZED` from `hls.py`.
- Zero baseline is raw zero after the same normalization: `-mean/std`. For HLS that is `-HLS_MEAN/HLS_STD`.

## Band names

Pavia University, Salinas corrected and WHU-Hi-LongKou `.mat` files contain the cube and the label map only. They do not contain a wavelength vector. Earlier interpolated nanometer labels were removed. The UI and the JSON use `Band 001` in file order. EuroSAT keeps the Sentinel-2 band ids and their nominal center wavelengths. HLS keeps the six named bands.

RGB previews stored in the sample NPZ are for display. They are not the tensors that SSI perturbs.

## WHU-Hi-LongKou region agreement

`assets/lab/manifest.json` records `region_agreement = 0.44959128065395093` for the LongKou tile. That number is the fraction of pixels inside the fixed ground-truth target region whose unperturbed argmax equals the target class. It is recall on that region, not overall accuracy and not IoU. The region has 367 pixels and is non-empty, so the tile stays the registered sample. PaviaU and Salinas tiles in the same export score 1.0 on this same definition. The sample was kept because the mask is a real labeled region, not because the model is perfect on it.

## Numerical checks

`python -m unittest discover -s tests -v` includes:

- The original HLS 8×8, mean, 10 permutations, seed 0 comparison with `assets/demo_summary.json`.
- Each extra model at 4×4, mean, 1 permutation, seed 0 against `assets/lab/references.json`, with absolute tolerance `1e-4`. Those vectors were saved on PyTorch 2.11. The CPU 2.6 wheel used in GitHub Actions differs by about `1e-5` on CUB-200.
- A direct model call, outside `ssi.explain`, for the unperturbed score and for one fully masked cell. The difference matches `spatial[0][0]` for HLS, CUB and PaviaU.
- Mean and zero baselines on HLS, CUB and Salinas, with local efficiency under `1e-5`.
- CUB exact enumeration against 20 permutations at 4×4. Both report the same full score. Their spectral vectors correlate above 0.8. They are not expected to be identical at finite sample size.
- A cancelled hook raises before scoring.
- `python -m lab.cli explain` matches the CUB reference. Pointing the CUB family at the PaviaU checkpoint fails.

These checks show the current implementation is repeatable and that one masked cell agrees with an independent forward. They do not replay the original training loop.

## Commands

```bash
python -m unittest discover -s tests -v
python -m lab.cli explain --model-id paviau --sample-id paviau-0008 --grid 4 --permutations 1 --seed 0
```

## Reliability closeout

The numerical tests now include `tests/test_jobs.py`, which simulates an unexpected model RuntimeError and a cancelled worker. Both must leave the task in a terminal state and release the single-run slot. An unexpected model exception is logged server-side while the client receives an actionable, non-sensitive error message.

`lab/browser_smoke.py` exercises actual browser races when SSI parameters change **both before POST /api/jobs has returned its job ID and after the job starts**. The frontend now invalidates every result-affecting control change, waits for cooperative cancellation before starting a replacement run, and refuses stale preview responses/errors. Old results cannot be displayed as though they correspond to the new parameters.

The real HSI sampling check is in [PLAYGROUND_STABILITY.md](PLAYGROUND_STABILITY.md), computed from the bundled PaviaU, Salinas and LongKou checkpoints by `benchmarks/spectral_stability.py`. The **K=1 versus K=3 Top 10 overlap** was 6/10, 8/10 and 9/10, respectively, at grid 4, mean baseline, seed 0. At K=3, two seeds also produced different Top 10 sets. The UI keeps K=1 as an immediate preview, labels the sampled-order count, and permits more sampling within measured CPU limits. This is sensitivity evidence, not proof of convergence.

The earlier CPU memory note has been made precise: the recorded peak RSS was for the **whole multi-model benchmark process**, not an independently measured maximum for each dataset.
