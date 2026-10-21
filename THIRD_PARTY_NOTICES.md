# Sources and third-party notices

## Scope of the root MIT license

The root MIT license covers SSI-owned source code, tests and documentation.
It does not replace the licenses or release status of the materials below.
References to "MIT code" do not assert that all bundled assets use MIT.

## HLS sample

- **Dataset:** HLS Foundation Burnscars Dataset, 2023.
- **Creators:** Christopher Phillips, Sujit Roy, Kumar Ankur, Rahul Ramachandran.
- **DOI:** https://doi.org/10.57967/hf/0956
- **Source:** https://huggingface.co/datasets/ibm-nasa-geospatial/hls_burn_scars
- **Source license:** CC-BY-4.0, as indicated by the official dataset card.
- **License:** https://creativecommons.org/licenses/by/4.0/
- **Included derivative:** `assets/samples/hls_sample.npz`, one 128×128 image/mask pair resized from a 512×512 training example. Image interpolation is bilinear with `align_corners=False`; mask interpolation is nearest-neighbor. Missing mask labels are mapped from -1 to 255. Normalization is performed at runtime.
- Dataset revision, original filenames, hashes, band order and changes are recorded in `assets/samples/hls_metadata.json`. No additional restrictions are imposed here on the upstream dataset.

## Demo model implementation — MIT

`third_party/brain_unet.py` is an unchanged copy of `unet.py` from
[mateuszbuda/brain-segmentation-pytorch](https://github.com/mateuszbuda/brain-segmentation-pytorch/blob/d45f8908ab2f0246ba204c702a6161c9eb25f902/unet.py), commit `d45f8908ab2f0246ba204c702a6161c9eb25f902`.
Copyright (c) 2019 mateuszbuda. The full original MIT license is included in
`LICENSES/brain-segmentation-pytorch-MIT.txt`; hashes and source URLs are in
`third_party/provenance.json`.

The SSI adapter in `lab/models/hls_unet.py` uses its convolution block factory to assemble the
HLS checkpoint architecture (two levels, widths 4/8/16, decoder widths 4/4,
bilinear upsampling with aligned corners, skip-first concatenation, two output
logits). It maps the historical tensor names at load time without modifying
values. The original GPL model implementation is not included or imported by
this release. The adapter and checkpoint metadata record the architecture and source hashes.

The adapter and the SSI-owned source/documentation use the root MIT license,
Copyright (c) 2026 SSI contributors. Upstream attribution remains in force.

## Demo weights

`assets/checkpoints/hls_unet.pt` contains only the `model.*` tensors from the supplied `HLS_BurnScars/unet/segmentation/train_1/best.ckpt`, with the prefix removed. The weights are unchanged; optimizer state, callbacks and training metadata are excluded. See the accompanying `metadata.json` for hashes and architecture. The weight file is separate from the MIT-licensed source code and is provided for the bundled demonstration.
The root MIT license does not grant additional rights to the weights.

## Manuscript figures

`assets/figures/fig1.png` and `fig2.png` were extracted from the supplied manuscript's embedded images. `fig3.png` and `fig4.png` were rendered from their figure regions at 300 dpi. They correspond to manuscript Figures 1–4. Page text and reviewer-copy footers are not included. These figures are separate from the root MIT-licensed source code.

`assets/figures/hls_paper_comparison.png` is the author-supplied HLS panel from manuscript Figure 4, copied unchanged from the provided image. It is used as the README illustration and is subject to the manuscript figure attribution above. It is separate from the runnable demo output.

`assets/demo_output.png` and `tests/fixtures/hls_legacy_reference.npz` are generated from the attributed HLS derivative above. Their underlying HLS material retains CC-BY-4.0 attribution and modification notices. The fixture contains numerical model outputs, attribution arrays and a synthetic input probe; it contains no legacy model source code. These generated materials are separate from the manuscript figures and pretrained weight file.

## Additional playground weights and samples

`assets/checkpoints/` holds tensor-only weights stripped from the training checkpoints named in `assets/metadata/model_manifest.json`. Optimizer state is not included. The segmentation weights load through the existing MIT U-Net block adapter in `lab/models/hls_unet.py` (`convert_legacy_state_dict`); the GPL U-Net source is not copied into this repository. The ResNet-18 classifiers are reconstructed in `lab/adapters/backbones.py` under the root MIT license so their parameter names match those checkpoints. No torchvision package is required.

`assets/samples/` holds one training-normalized model input per dataset, plus a display RGB preview:

- CUB-200-2011 test index 158. Source: Caltech-UCSD Birds-200-2011, used here as a single preprocessed research sample.
- EuroSAT multispectral test index 1294. Band order is B01, B02, B03, B04, B05, B06, B07, B08, B8A, B09, B10, B11, B12.
- Pavia University val tile 8, Salinas corrected val tile 0, and WHU-Hi-LongKou val tile 0. These are 32×32 patches from the public cubes, split with seed 1 and normalized by the labeled training-pixel mean and standard deviation. Salinas wavelengths are a linear index from 400 nm to 2500 nm across the corrected 204 bands. Pavia University uses 430–860 nm and WHU-Hi-LongKou uses 400–1000 nm, also linear in band index.

The weight files and these samples are separate from the root MIT-licensed source code. SHA-256 hashes are in `assets/metadata/model_manifest.json`.

## Code and documentation organization

The SSI core is refactored from the supplied research implementation's observed-context, full-grid path. The new `ssi.py` and adapter contain no SAR implementation code. The implementation and demonstration are organized as a standalone SSI repository.
