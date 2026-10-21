"""Small PyTorch adapter for the bundled HLS Burn Scar demonstration."""
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from lab.runtime import raise_if_cancelled
from lab.models.hls_unet import UNet, convert_legacy_state_dict

BAND_NAMES = ("Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2")
# Original dataset loader uses these statistics on reflectance * 10,000.
HLS_MEAN = np.array([775.640, 911.585, 1043.467, 2971.804, 2496.875, 1865.025], dtype=np.float32)
HLS_STD = np.array([602.194, 557.980, 660.052, 1065.752, 1056.892, 854.436], dtype=np.float32)
# Full training-split channel means after the original deterministic preprocessing.
TRAIN_MEAN_NORMALIZED = np.array(
    [-.39958634, -.22098443, -.12259903, -.79981593, -.12976274, -.15640178], dtype=np.float32)


def load_sample(path: Path):
    """Read a prepared 6xHxW reflectance image and an HxW label mask (0/1/255)."""
    with np.load(path, allow_pickle=False) as data:
        image = data["image"].astype(np.float32)
        mask = data["mask"]
    if image.ndim != 3 or image.shape[0] != 6 or mask.shape != image.shape[1:]:
        raise ValueError("Sample requires image (6,H,W) and mask (H,W)")
    if not np.isfinite(image).all() or not np.isin(mask, [0, 1, 255]).all():
        raise ValueError("Expected finite reflectance and mask labels 0, 1 or 255")
    if not (mask == 1).any():
        raise ValueError("The fixed GT burn region is empty; this demo requires burned pixels")
    x = (image * 10000 - HLS_MEAN[:, None, None]) / HLS_STD[:, None, None]
    return image, mask.astype(np.uint8), x


def load_model(weights: Path, device: torch.device):
    model = UNet(n_channels=6, n_classes=2, base_channels=4, bilinear=True)
    state = torch.load(weights, map_location="cpu", weights_only=True)
    if "inc.net.0.weight" in state or "model.inc.net.0.weight" in state:
        state = convert_legacy_state_dict(state)
    model.load_state_dict(state, strict=True)
    return model.to(device).eval()


class HLSValueFunction:
    """Average burn-class logit on a FIXED ground-truth region, with batched masks.

    The region is fixed before attribution and never recomputed from perturbed
    predictions. Coalitions are shaped (batch, cells, channels), in row-major
    cell order. ``grid`` is the number of cells along each side, not pixel size.
    """

    def __init__(self, model, x, mask, *, grid=8, baseline="mean", batch_size=32, device="cpu"):
        if grid < 1 or batch_size < 1:
            raise ValueError("grid and batch_size must be positive")
        self.device = torch.device(device)
        self.model = model.to(self.device).eval()
        self.x = torch.as_tensor(x, device=self.device, dtype=torch.float32)[None]
        self.grid = grid
        self.batch_size = batch_size
        _, self.channels, self.height, self.width = self.x.shape
        if self.height % grid or self.width % grid:
            raise ValueError("Image height and width must be divisible by grid")
        self.region = torch.as_tensor(mask == 1, device=self.device)
        if not self.region.any():
            raise ValueError("The fixed GT burn region is empty")
        if baseline == "mean":
            values = TRAIN_MEAN_NORMALIZED
        elif baseline == "zero":
            values = -HLS_MEAN / HLS_STD  # raw zero AFTER normalization
        else:
            raise ValueError("baseline must be 'mean' or 'zero'")
        self.baseline = torch.as_tensor(values, device=self.device)[None, :, None, None]
        self.forward_calls = 0

    def __call__(self, masks):
        masks = np.asarray(masks)
        if masks.dtype != np.bool_ or masks.ndim != 3 or masks.shape[1:] != (self.grid**2, self.channels):
            raise ValueError("Expected Boolean coalitions (batch, grid**2, channels)")
        scores = []
        with torch.inference_mode():
            for start in range(0, len(masks), self.batch_size):
                raise_if_cancelled()
                m = torch.as_tensor(masks[start:start+self.batch_size], device=self.device)
                m = m.permute(0, 2, 1).reshape(-1, self.channels, self.grid, self.grid).float()
                m = F.interpolate(m, size=(self.height, self.width), mode="nearest")
                perturbed = self.baseline + m * (self.x - self.baseline)
                logits = self.model(perturbed)
                scores.append(logits[:, 1, self.region].mean(dim=1).cpu().numpy())
                self.forward_calls += 1
        return np.concatenate(scores).astype(np.float64) if scores else np.empty(0)
