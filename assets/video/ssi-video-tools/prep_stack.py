"""v5 input-stack plates: the six REAL model-input bands of HLS sample_0163.

Source: docs/playground/assets/samples/HLS_BurnScars/sample_0163/x.f32 (6x128x128, the
tensor the U-Net receives). Each band gets a per-band 2-98 percentile stretch (display
only) and a ramp dark -> band colour -> light, so the layer reads as that channel.
(The package's channel_0X_*.png are SSI attribution overlays, not inputs — not used here.)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SAMPLE = Path(sys.argv[1]) / "docs/playground/assets/samples/HLS_BurnScars/sample_0163"
OUT = Path(sys.argv[2])
meta = json.loads((SAMPLE / "meta.json").read_text())
x = np.fromfile(SAMPLE / "x.f32", dtype=np.float32).reshape(6, 128, 128)
assert meta["channels"] == ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]
COL = ["#3277C8", "#27986F", "#DA5A58", "#8062B5", "#D59A3F", "#A45B45"]
DARK = np.array((12, 12, 14), np.float32)
LIGHT = np.array((244, 244, 240), np.float32)


def rgb(h):
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], np.float32)


for b in range(6):
    lo, hi = np.percentile(x[b], [2, 98])
    v = np.clip((x[b] - lo) / (hi - lo + 1e-8), 0, 1)[:, :, None]
    c = rgb(COL[b])
    k = 0.58
    low = DARK + (c - DARK) * (v / k)
    high = c + (LIGHT - c) * ((v - k) / (1 - k)) * 0.6
    img = np.where(v < k, low, high)
    Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB").resize((768, 768), Image.Resampling.LANCZOS).save(
        OUT / f"band_{b + 1}.png", optimize=True
    )
print("bands written")
