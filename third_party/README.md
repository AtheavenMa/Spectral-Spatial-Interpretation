# MIT U-Net source

`brain_unet.py` is an **unchanged** copy of `unet.py` from
[mateuszbuda/brain-segmentation-pytorch](https://github.com/mateuszbuda/brain-segmentation-pytorch/blob/d45f8908ab2f0246ba204c702a6161c9eb25f902/unet.py),
commit `d45f8908ab2f0246ba204c702a6161c9eb25f902`.

Copyright (c) 2019 mateuszbuda. Its original [MIT license](../LICENSES/brain-segmentation-pytorch-MIT.txt)
is included unchanged. Source URLs and SHA-256 hashes are in [provenance.json](provenance.json).

`model.py` calls this implementation's Conv/BatchNorm/ReLU block factory to
assemble the two-level HLS architecture: widths 4, 8, 16; two decoder stages
with width 4; bilinear upsampling with aligned corners; skip-first concatenation;
and two output logits without sigmoid. It does not instantiate the upstream
four-level model and does not use its pretrained weights.

The HLS checkpoint's old tensor names are converted at load time. Tensor values
and the checkpoint file are unchanged. The legacy GPL implementation is not
vendored or imported by this release.
