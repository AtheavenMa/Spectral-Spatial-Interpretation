# HLS Burn Scar demo guide

Detailed setup, explanation settings, output files and validation for the bundled example. See the [English README](../README.md) for the project overview.

## Installation

Clone the repository, then use Python 3.10 or newer in an isolated environment:

```bash
git clone https://github.com/AtheavenMa/Spectral-Spatial-Interpretation.git
cd Spectral-Spatial-Interpretation
```

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate`. For a particular CUDA setup, install the appropriate PyTorch build before the remaining requirements.

The core needs **NumPy**. The HLS demo additionally needs **PyTorch** and **Matplotlib**. There is no dataset download or model download at runtime: the prepared sample and tensor-only weights are bundled. No training framework is required.

## Running and interpreting the demo

```bash
python demo.py
python demo.py --baseline zero
python demo.py --method exact --output outputs/hls_exact
```

The default uses a **128 × 128 image, 6 bands, an 8 × 8 grid and 10 permutations per cell**. `--grid 8` means eight cells along each side, so each cell is 16 × 16 pixels. The `mean` baseline is the original training-split per-channel mean in normalized model space. `zero` means raw zero reflectance followed by the same normalization; it does not mean zero in normalized space.

The scalar target is the **burn-class logit averaged over the fixed ground-truth burn region**. This example requires a GT mask. The mask is not recomputed from perturbed predictions, and the result explains a regional segmentation score rather than each output pixel separately.

Bands are ordered **Blue, Green, Red, NIR, SWIR1, SWIR2** (B02, B03, B04, B8A, B11, B12). The prepared image stores reflectance before normalization. The demo multiplies it by 10,000 and applies the means/stds in `lab/adapters/hls.py`.

The sample is the first image encountered in the pinned official dataset archive, selected before evaluation. It belongs to the **training split** and is an illustrative example, not held-out evidence. The supplied demo weights were exported from a `train_1` checkpoint without retraining. See
[sample metadata](../assets/samples/hls_metadata.json) and [model metadata](../assets/checkpoints/metadata.json)
for hashes and provenance.

**MIT model implementation.** The demo assembles its two-level network from the convolution blocks in a pinned MIT-licensed U-Net source. Historical checkpoint keys are mapped at load time without changing the weights. No training framework or original project dependency is required.

A verified CPU run produced:

```text
permutation | 2152 scored inputs | 107 batches
Full GT-region logit: 2.371968 | sample burn IoU: 0.8144
Max local-efficiency error: 1.388e-17
  Blue   -0.083984
  Green  +0.178652
  Red    -0.304284
  NIR    +0.115718
  SWIR1  -0.547710
  SWIR2  +4.576118
```

Attribution took about **6.5 seconds** in the recorded CPU run with four threads and batch size 32. This excludes model loading and plotting and is not a cross-machine speed guarantee. The [recorded summary](../assets/demo_summary.json) contains the environment and full precision values. Batched floating-point results may differ slightly across devices and library versions.

In the [runnable demo output](../assets/demo_output.png), blue/red in attribution maps represent negative/positive contributions. All six channel maps share one signed color scale; the spatial map has its own scale. The RGB percentile stretch is for display only. Channel totals are model attributions under the chosen target and baseline, not direct measurements of physical causation.

The demo saves `demo_output.png`, `attribution.npz` and `summary.json` under `outputs/hls_demo/`. Set `--output` to preserve another run. The NPZ stores signed cell/channel scores, spatial and spectral summaries, position contrasts, the prediction and GT mask.

Useful controls: `--device cpu|cuda|mps|auto`, `--batch-size 32`, `--threads 4`, `--grid 8`, `--permutations 10`, `--seed 0`, `--sample PATH`, `--weights PATH`. Auto selects CUDA when available, otherwise CPU. Explicitly select MPS on supported Macs.

A custom `--sample` must be an NPZ with `image` shaped `(6, H, W)` in reflectance units and `mask` shaped `(H, W)`, with labels 0 (unburned), 1 (burned) and optionally 255 (no data). Both dimensions must be divisible by `--grid`, and the mask must contain burned pixels. Custom weights must match the architecture in `lab/models/hls_unet.py`; both the bundled historical key layout and native adapter state dictionaries are accepted; other models can use the core through their own scoring adapter.

## Repository layout and checks

```text
ssi.py                  Independent NumPy core
lab/adapters/hls.py      HLS preprocessing and batched scoring adapter
lab/models/hls_unet.py   MIT HLS model and historical weight-key conversion
third_party/            Pinned, unchanged MIT upstream source and provenance
demo.py                 Command-line demo and visualization
assets/samples/         Prepared reflectance image, GT mask and provenance
assets/checkpoints/     Tensor-only pretrained weights and provenance
assets/figures/          Figures extracted from the supplied manuscript
assets/demo_output.png  Verified demo preview
tests/                  Mathematical and adapter checks
```

Run the checks with the same environment:

```bash
python -m unittest discover -s tests -v
```

They cover known additive and interacting games, fixed external context, local/global efficiency, seeded permutation sampling, score-shift invariance, the segmentation masking adapter, and model/attribution regression against stored numerical references. 
