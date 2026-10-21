# Core SSI API

SSI separates the numerical observed-context Shapley solver from its optional
PyTorch image adapter. The public image API handles pixels, not manually
specified grid counts.

## Install

From the repository (core NumPy module and optional PyTorch support):

```bash
pip install "spectral-spatial-interpretation[torch] @ git+https://github.com/AtheavenMa/Spectral-Spatial-Interpretation.git"
```

Alternatively, clone the repository and run \`pip install -r requirements.txt\`
for the complete demo, model adapters, API server and tests.

The project is installable directly through pip from GitHub; this does **not**
imply that a package with the same name has been published to PyPI.

## Explain one image

```python
import numpy as np
from ssi import SSI

# my_model must be a PyTorch nn.Module returning class logits (B, classes).
# image is CHW (or HWC), already preprocessed into the model's input space.
# baseline is the dataset-level mean *in that same input space*, not a string.
dataset_channel_mean = np.asarray([0.0, 0.0, 0.0], dtype=np.float32)
result = SSI(
    model=my_model,
    input=image,
    target=6,
    baseline=dataset_channel_mean,
    image_size=(128, 128),
    grid_size=(16, 16),
    permutations=5,
).explain()

print(result.attribution.shape)  # (8, 8, 3)
print(result.spatial.shape)      # (8, 8)
print(result.spectral.shape)     # (3,)
```

- \`image_size\`: output model-input resolution, in pixels (height, width).
  An integer means a square. If omitted, keep the input resolution.
- \`grid_size\`: spatial cell extent in **pixels**, not the number of cells.
  For \`image_size=(128,128)\` and \`grid_size=16\`, SSI computes an 8×8 grid.
  Both image axes must be divisible by their respective grid sizes.
- \`baseline\`: required numeric vector of length C, e.g. training-set
  per-channel mean. It must use exactly the same normalization and channel
  order as the tensor **received by the model**. Do not pass \`"mean"\`,
  \`"zero"\` or a single global number.
- \`input\`: one float CHW/HWC tensor or NumPy array, optionally with a
  batch dimension of 1, or a PIL RGB image. Unsigned 8-bit input is scaled
  to [0,1]; float input is **not automatically normalized**. CHW is preferred
  when dimensions are ambiguous.
- \`target\`: fixed nonnegative class index. Classifiers return (B,C);
  segmentation models return (B,C,H,W) and require \`target_mask\`.
  Advanced users can pass a callable \`target(logits) -> tensor(B,)\`.
- \`permutations\`: number of sampled channel restoration orders per cell;
  RGB with <=3 channels uses exact subset enumeration automatically.
  \`batch_size\` (default 8) bounds inference memory; \`seed\` defaults to 0.

Resizing uses bilinear interpolation of model-input tensors with
\`align_corners=False\`. A supplied fixed segmentation \`target_mask\` is
resized using nearest neighbors. If the checkpoint requires a particular input
resolution, use that \`image_size\` and match the model's original
preprocessing (including channel normalization) before SSI.

For a segmentation output, e.g. burn region, pass the fixed mask:

```python
result = SSI(
    model=segmentation_model,
    input=normalized_six_band_tensor,
    target=1,
    target_mask=ground_truth_burn_region,
    baseline=training_split_normalized_channel_means,  # shape (6,)
    image_size=128,
    grid_size=16,
).explain()
```

SSI always keeps cells outside the one being evaluated at their observed
values. Within the selected cell, masked channels are replaced by the fixed
dataset-level vector. The result is signed \`(grid_rows, grid_cols, channels)\`.
The sum over channels at each location equals its full-context cell contrast.
Summing across all cells is **not** guaranteed to yield the global
input-to-baseline score difference when spatial cells interact.

The model is evaluated with gradients off, and its previous train/eval flags
are restored after the explanation. Non-finite input, bad baseline shape,
nondivisible geometry, invalid targets and empty segmentation masks fail
explicitly.

## Research and legacy interfaces

\`from ssi import explain\` remains the direct NumPy oracle API.
It accepts \`value_fn(masks)\` and explicit cell/channel counts and does
not perform input resizing or choose any baseline. This preserves published
numerical regression tests and model adapters. The old demo and registered
six-model CLI continue to use \`--grid\` as a **grid count**, solely for their
recorded experiment configurations; the new public \`SSI\` image interface uses
\`grid_size\` in **pixels**, with no independent grid-count parameter.

Run the added tests with:

```bash
python -m unittest tests.test_ssi_image -v
```
