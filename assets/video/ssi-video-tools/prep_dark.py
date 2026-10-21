"""v3 dark-ground plates. Same signed_overlay mapping as make_keyframes.py
(ratio**.57, mix .08 + .75*ratio, POS/NEG tones, same exposures); only the substrate
blends toward the dark canvas (#0a0a0a) instead of white. Values are untouched."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

VID = Path(sys.argv[1]) / "assets/video/hls_burnscar_0163"  # repo root
OUT = Path(sys.argv[2])  # ssi-video/assets/img
data = json.loads((VID / "result.json").read_text())
phi = np.array(data["attribution"])
S = phi.sum(axis=2)
image = Image.open(VID / "input.png").convert("RGB")
POS = (0xEE, 0x76, 0x67)
NEG = (0x4D, 0x91, 0xCA)
DARK = np.array((10, 10, 10), np.float32)
EXP = 0.07535534570403755
assert np.isclose(EXP, np.abs(phi).max())


def overlay(a, side, exposure):
    interp = Image.fromarray(np.asarray(a).astype(np.float32), mode="F").resize((side, side), Image.Resampling.BICUBIC)
    v = np.nan_to_num(np.asarray(interp, dtype=np.float32))
    ratio = np.clip(np.abs(v) / max(exposure, 1e-8), 0, 1) ** 0.57
    mix = (0.08 + 0.75 * ratio)[:, :, None]
    sub = np.asarray(ImageOps.fit(image, (side, side), method=Image.Resampling.LANCZOS), dtype=np.float32) * 0.6 + DARK * 0.4
    tones = np.where(v[:, :, None] >= 0, np.array(POS, np.float32), np.array(NEG, np.float32))
    return Image.fromarray(np.clip(sub * (1 - mix) + tones * mix, 0, 255).astype("uint8"))


for c, n in enumerate(["blue", "green", "red", "nir", "swir1", "swir2"]):
    overlay(phi[:, :, c], 576, EXP).save(OUT / f"phi_{n}_dark.png", optimize=True)
overlay(np.zeros((16, 16)), 576, EXP).save(OUT / "phi_substrate_dark.png", optimize=True)
overlay(S, 576, float(np.abs(S).max())).save(OUT / "spatial_S_dark.png", optimize=True)

rng = np.random.default_rng(163)
a = (rng.random((540, 960)) ** 2.6 * 16).astype(np.uint8)
g = np.zeros((540, 960, 4), np.uint8)
g[..., :3] = (200, 225, 230)
g[..., 3] = a
Image.fromarray(g, "RGBA").save(OUT / "grain_dark.png", optimize=True)
