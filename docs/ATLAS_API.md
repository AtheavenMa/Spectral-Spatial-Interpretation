# SSI Atlas API

**Checkpoint + original image + SSI parameters → atlas.png + result.json + attribution.npz.**

This is a real Python API that evaluates the requested checkpoint with the original SSI observed-context Shapley estimator. The generated figure follows the Visual Atlas layout: image, true target/ground truth, spatial SSI overlaid on the image, spectral overlays and signed channel contributions.

## Quickstart

Install from the repository root:

~~~~bash
python -m pip install -r requirements_lab.txt
~~~~

**Bundled HLS checkpoint and input**

~~~~bash
python -m lab.cli atlas \
  --family hls-unet \
  --checkpoint assets/checkpoints/hls_unet.pt \
  --image assets/examples/hls_sample.npz \
  --grid 4 --baseline mean --method permutation --permutations 1 --seed 0 \
  --output outputs/atlas_hls
~~~~

**Bundled Pavia University checkpoint and input**

~~~~bash
python -m lab.cli atlas \
  --family paviau \
  --checkpoint assets/lab/checkpoints/paviau_unet.pt \
  --image assets/lab/samples/paviau_0008.npz \
  --grid 4 --baseline mean --permutations 1 \
  --output outputs/atlas_paviau
~~~~

**Your own CUB-200 RGB image and compatible ResNet-18 weights**

~~~~bash
python -m lab.cli atlas \
  --family cub-200 \
  --checkpoint /path/to/compatible_resnet18.pt \
  --image /path/to/bird.jpg \
  --target-class 6 \
  --grid 4 --permutations 3 \
  --output outputs/atlas_bird
~~~~

For the direct RGB image path, this adapter resizes to 448×448 with bicubic filtering and applies ImageNet RGB mean/std. If the training pipeline differs, use an NPZ containing your correctly preprocessed input tensor.

## Python function

~~~~python
from lab.atlas_api import explain_artifacts

files = explain_artifacts(
    checkpoint="assets/lab/checkpoints/salinas_unet.pt",
    image="assets/lab/samples/salinas_0000.npz",
    family="salinas",
    output="outputs/atlas_salinas",
    grid=4,
    baseline="mean",
    method="permutation",
    permutations=1,
    seed=0,
    display_channels=10,
)
print(files["png"], files["json"], files["npz"])
~~~~

The checkpoint must match a registered architecture. PyTorch tensor-only weights are loaded with weights_only=True, using strict parameter matching. Arbitrary unknown checkpoints cannot be reconstructed without model architecture, preprocessing and scalar-target semantics.

## Supported data formats

| Model family | Image/input format | Fixed target |
|---|---|---|
| hls-unet | NPZ with original six-band reflectance image (6,H,W) and GT mask (H,W) | Burn-class logit over fixed GT burn region |
| cub-200 | RGB PNG, JPG, WebP with explicit target class, or model-normalized NPZ | Fixed class logit |
| eurosat | Model-normalized 13-band NPZ | Fixed class logit |
| paviau | Model-normalized 103-band NPZ | Mean class logit within fixed GT region |
| salinas | Model-normalized 204-band NPZ | Same |
| whu-hi-longkou | Model-normalized 270-band NPZ | Same |

NPZ fields for classifiers and high-band models:

- **x**: (C,H,W) tensor in the model's normalized input space.
- **mean / std**: C-element normalization statistics (all std values positive).
- **target_class**: integer class index, or supply --target-class.
- **label**: GT class map, required for segmentation unless --target-mask is supplied.
- **rgb**: optional aligned H×W×3 display image. If absent for high-band input, a contrast-stretched pseudo-RGB is generated from fixed channels only for display. SSI always uses the complete original tensor.

For segmentation, --target-mask can supply an aligned binary PNG region; it must be nonempty and remain fixed throughout scoring. The target region is never selected from perturbed predictions. A standard RGB PNG is not an adequate input for multispectral/hyperspectral models: it cannot preserve all original bands.

## Output contract

**atlas.png** is a high-resolution research figure showing:

1. (a) original RGB/pseudo-RGB image
2. (b) real ground truth or class target
3. (c) signed spatial SSI transparently interpolated **for display only** over the original image, with ground-truth region outline for segmentation
4. (d) signed channel-level SSI overlays, sharing a common signed scale. For many bands, select the largest contributions by absolute aggregate score
5. (e) signed spectral contribution bar plot

**result.json** contains the full unmodified grid×grid×C numeric attribution tensor, spectral/spatial sums, channel IDs, checkpoint/input SHA-256 hashes, target class/region, settings, evaluation count and local-efficiency residual. **attribution.npz** contains lossless arrays plus the fixed mask.

The original CUB example metadata has no bounding-box annotation. The API does not fabricate one.

## Verification and limits

~~~~bash
python -m unittest tests.test_atlas_api -v
~~~~

Tests run the API on actual HLS/PaviaU weights and inputs and a CUB RGB PNG with an explicit class target. Tests inspect the PNG/JSON/NPZ and numerical aggregation identities.

The [HTML Visual Atlas gallery](https://atheavenma.github.io/ssi-playground/?view=atlas) includes all 57 existing research figures. Each of those 57 samples now has its original tensor and a verified ONNX model, so the browser recomputes SSI from that tensor. The gallery PNG is only the stored figure. The Python API covers the same six families.
