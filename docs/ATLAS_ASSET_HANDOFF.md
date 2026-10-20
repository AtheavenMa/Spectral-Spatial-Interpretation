# Complete Visual Atlas input handoff

The HTML gallery now indexes all **57 PNG examples** from CUB-200, EuroSAT, HLS Burn Scars, Pavia University, Salinas and WHU-Hi-LongKou. The current static HTML compute mode uses a verified HLS checkpoint and one corresponding HLS sample. The six-model Python API can compute SSI and produce Atlas PNG + JSON for compatible checkpoint/input pairs.

To make **every one of the 57 exact gallery examples** recomputable (rather than merely browsable), export the following for each sample from the original experiment. No extra training or new ground-truth labels are requested.

## Files per Atlas sample

1. **Original input tensor**, not an RGB screenshot: NPZ with x in exact model-normalized C,H,W order, float32, plus mean/std (one value per channel).
2. **Preview RGB**, optionally rgb H,W,3 uint8 corresponding to the same crop/orientation, not a model input.
3. **Fixed target**: for classification an integer target_class in the original mapping; for segmentation an H,W ground-truth label array and fixed target_class (or separate ROI PNG).
4. **Source checkpoint** path, family adapter/architecture and immutable SHA-256. A shared checkpoint can serve multiple images.
5. **Preprocessing metadata**: original split/index, crop/resize/band-selection, no-data mask, label mapping and original band index/wavelength metadata if actually known.
6. **Sanity reference**: unperturbed selected class/GT-region logit and one inexpensive 4x4 / 1-permutation SSI reference (or a checksum and command that computes it).

## Dataset handoff

| Dataset | Atlas PNGs | Current runnable model family | Most important missing item |
|---|---:|---|---|
| CUB-200 | 10 | cub-200 | Matching original input tensors and target classes for the other nine images; bounding boxes if Atlas localization frames are desired |
| EuroSAT | 10 | eurosat | Original 13-band, model-normalized inputs (RGB renders cannot recover the bands) |
| HLS Burn Scars | 10 | hls-unet | Original six-band reflectance arrays plus 0/1/255 masks for the ten gallery sample indices |
| PaviaU | 10 | paviau | 103-band model-normalized crop tensors, GT regions and exact band indices |
| Salinas | 10 | salinas | 204-band tensors and GT target regions |
| WHU-Hi-LongKou | 7 | whu-hi-longkou | 270-band tensors and GT target regions |

The original gallery PNG filenames and dataset grouping are listed in [atlas-catalog.json](../docs/playground/atlas-catalog.json). Ensure sample ID and target metadata match each figure. Do not substitute visually similar images or invent hyperspectral wavelength centers.

## First verification for the input-export agent

For each exported sample, execute the already supported command, using the corresponding registered family:

~~~~bash
python -m lab.cli atlas \
  --family paviau \
  --checkpoint assets/lab/checkpoints/paviau_unet.pt \
  --image /path/to/exported/sample_0010.npz \
  --grid 4 --baseline mean --permutations 1 \
  --output outputs/paviau_sample_0010
~~~~

This must produce an **atlas.png**, **result.json** and **attribution.npz**, with the matching target class/ROI and channel labels. Cross-check the generated input image, target region, signed SSI overlays and numeric spectral contributions against the original example, allowing expected differences when estimator settings or random seeds differ.

Once the source assets are validated, the registered dataset sample catalogs can be extended and future browser inference adapters can be exported selectively. The standalone static site should not claim that a static PNG is an interactive model run.
