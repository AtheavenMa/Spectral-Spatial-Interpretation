# SPDX-License-Identifier: MIT
# Copyright (c) 2026 SSI contributors
"""Two-level HLS model assembled from an MIT-licensed U-Net block.

The unchanged upstream implementation is vendored in third_party/brain_unet.py
(Copyright (c) 2019 mateuszbuda). See third_party/README.md for its pinned source.
This adapter uses only its Conv/BatchNorm/ReLU block, with the architecture and
tensor layout required by the existing HLS checkpoint. It returns two logits,
uses bilinear upsampling, and puts skip features before decoder features.
"""
from collections import OrderedDict
from collections.abc import Mapping

import torch
from torch import nn
from torch.nn import functional as F

from third_party.brain_unet import UNet as UpstreamUNet


class UNet(nn.Module):
    """HLS checkpoint architecture, using MIT upstream convolution blocks.

    Encoder widths: b, 2b, 4b. Both decoder stages output b channels.
    bilinear=False is not supported by this HLS-only adapter.
    Images may have odd dimensions, but each side must be at least four pixels.
    """

    def __init__(self, n_channels=6, n_classes=2, bilinear=True, base_channels=4):
        super().__init__()
        if not bilinear:
            raise ValueError("The HLS checkpoint requires bilinear=True")
        widths = (n_channels, n_classes, base_channels)
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in widths):
            raise ValueError("Channel counts must be positive integers")
        self.n_channels = n_channels
        b = base_channels
        self.encoder1 = UpstreamUNet._block(n_channels, b, name="enc1")
        self.encoder2 = UpstreamUNet._block(b, 2*b, name="enc2")
        self.bottleneck = UpstreamUNet._block(2*b, 4*b, name="bottleneck")
        self.decoder2 = UpstreamUNet._block(6*b, b, name="dec2")
        self.decoder1 = UpstreamUNet._block(2*b, b, name="dec1")
        self.conv = nn.Conv2d(b, n_classes, kernel_size=1)

    @staticmethod
    def _join(skip, coarse):
        expanded = F.interpolate(coarse, scale_factor=2, mode="bilinear", align_corners=True)
        # Pooling floors odd dimensions. Restore that discarded bottom/right
        # pixel with zeros, preserving the checkpoint's alignment convention.
        if expanded.shape[-2:] != skip.shape[-2:]:
            canvas = expanded.new_zeros((*expanded.shape[:-2], *skip.shape[-2:]))
            canvas[..., :expanded.shape[-2], :expanded.shape[-1]] = expanded
            expanded = canvas
        return torch.cat((skip, expanded), dim=1)

    def forward(self, image):
        if image.ndim != 4 or image.shape[1] != self.n_channels or min(image.shape[-2:]) < 4:
            raise ValueError(f"Expected (batch, {self.n_channels}, H>=4, W>=4)")
        enc1 = self.encoder1(image)
        enc2 = self.encoder2(F.max_pool2d(enc1, kernel_size=2))
        center = self.bottleneck(F.max_pool2d(enc2, kernel_size=2))
        dec2 = self.decoder2(self._join(enc2, center))
        dec1 = self.decoder1(self._join(enc1, dec2))
        return self.conv(dec1)


def convert_legacy_state_dict(state: Mapping[str, torch.Tensor]):
    """Rename all 62 tensors in the historical HLS state dict, without arithmetic.

    Accepts either the tensor-only export or its model.-prefixed training keys.
    Unexpected keys are rejected; strict model loading then checks missing keys
    and tensor shapes. The source mapping and tensors are never modified.
    """
    blocks = {
        "inc.net": ("encoder1", "enc1"),
        "down1.net.1.net": ("encoder2", "enc2"),
        "down2.net.1.net": ("bottleneck", "bottleneck"),
        "up1.conv.net": ("decoder2", "dec2"),
        "up2.conv.net": ("decoder1", "dec1"),
    }
    layers = {"0": "conv1", "1": "norm1", "3": "conv2", "4": "norm2"}
    converted = OrderedDict()
    for source_key, tensor in state.items():
        if not isinstance(source_key, str) or not isinstance(tensor, torch.Tensor):
            raise ValueError("Expected a string-to-tensor state dictionary")
        key = source_key.removeprefix("model.")
        if key in ("outc.weight", "outc.bias"):
            target = "conv." + key.split(".")[-1]
        else:
            stem, index, parameter = key.rsplit(".", 2) if key.count(".") >= 2 else ("", "", "")
            if stem not in blocks or index not in layers:
                raise ValueError(f"Unrecognized HLS checkpoint key: {source_key}")
            module, prefix = blocks[stem]
            target = f"{module}.{prefix}{layers[index]}.{parameter}"
        if target in converted:
            raise ValueError(f"Duplicate checkpoint destination: {target}")
        converted[target] = tensor
    return converted
