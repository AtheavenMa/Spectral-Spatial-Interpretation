"""Build the SSI video's raster plates and data module from the authentic GitHub run.

Every number comes from assets/video/hls_burnscar_0163/result.json (checked against
the design package copy) and from g_permutations.json, which was produced by
re-running the repository's original compute-runtime.js (bit-identical to result.json).
signed_overlay() is copied verbatim from the design package's make_keyframes.py so the
heatmaps match the approved keyframes; only output size changes.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

REPO = Path(sys.argv[1])
PKG = Path(sys.argv[2])
HARNESS = Path(sys.argv[3])
OUT = Path(sys.argv[4])
IMG = OUT / "assets/img"
IMG.mkdir(parents=True, exist_ok=True)

VID = REPO / "assets/video/hls_burnscar_0163"
SAMPLE = REPO / "docs/playground/assets/samples/HLS_BurnScars/sample_0163"

# --- provenance: package assets must equal GitHub assets -------------------
for name in ("result.json", "input.png", "analysis.json"):
    a = (VID / name).read_bytes()
    b = (PKG / "assets" / name).read_bytes()
    assert a == b, f"{name} differs between package and GitHub"

data = json.loads((VID / "result.json").read_text())
phi = np.array(data["attribution"], dtype=np.float64)
assert phi.shape == (16, 16, 6)
S = phi.sum(axis=2)
T = phi.sum(axis=(0, 1))
assert np.allclose(S, np.array(data["spatial"])) and np.allclose(T, np.array(data["spectral"]))
GROW, GCOL = 9, 11
local = phi[GROW, GCOL, :]

perm = json.loads((HARNESS / "g_permutations.json").read_text())
assert perm["checks"]["full_rerun_max_abs_diff_vs_result_json"] == 0
assert perm["checks"]["cell_g_max_abs_diff_vs_result_json"] == 0
assert np.allclose(perm["phi_g_result_json"], local)

image = Image.open(VID / "input.png").convert("RGB")
POS = (0xEE, 0x76, 0x67)
NEG = (0x4D, 0x91, 0xCA)
EXPOSURE = 0.07535534570403755  # value used by make_keyframes.py for band maps
assert np.isclose(EXPOSURE, np.max(np.abs(phi))), "exposure is max|phi|"


def signed_overlay(a, side, orig=None, exposure=None):  # verbatim from make_keyframes.py
    a = np.asarray(a)
    if exposure is None:
        exposure = np.max(np.abs(a)) if np.any(a) else 1
    interp = Image.fromarray(a.astype(np.float32), mode="F").resize((side, side), Image.Resampling.BICUBIC)
    v = np.asarray(interp, dtype=np.float32)
    v = np.nan_to_num(v)
    ratio = np.clip(np.abs(v) / max(exposure, 1e-8), 0, 1) ** .57
    mix = (.08 + .75 * ratio)[:, :, None]
    if orig is None:
        substrate = np.full((side, side, 3), 252, dtype=np.float32)
    else:
        pil = ImageOps.fit(orig, (side, side), method=Image.Resampling.LANCZOS)
        substrate = np.asarray(pil.convert("RGB"), dtype=np.float32) * .65 + 255 * .35
    tones = np.where(v[:, :, None] >= 0, np.array(POS, dtype=np.float32), np.array(NEG, dtype=np.float32))
    out = substrate * (1 - mix) + tones * mix
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


SIDE = 576
names = ["blue", "green", "red", "nir", "swir1", "swir2"]
for c, n in enumerate(names):
    signed_overlay(phi[:, :, c], SIDE, image, exposure=EXPOSURE).save(IMG / f"phi_{n}.png", optimize=True)
signed_overlay(np.zeros((16, 16)), SIDE, image, exposure=EXPOSURE).save(IMG / "phi_substrate.png", optimize=True)
signed_overlay(S, SIDE, image, exposure=float(np.max(np.abs(S)))).save(IMG / "spatial_S.png", optimize=True)
image.save(IMG / "input.png", optimize=True)

# Cell g: the true 8x8 model pixels (rgb.webp is the 128x128 aligned preview), nearest-upscaled.
rgb128 = Image.open(SAMPLE / "rgb.webp").convert("RGB")
assert rgb128.size == (128, 128)
cell = rgb128.crop((GCOL * 8, GROW * 8, GCOL * 8 + 8, GROW * 8 + 8))
cell.resize((464, 464), Image.Resampling.NEAREST).save(IMG / "g_observed.png", optimize=True)

# Display colour of the per-channel mean baseline under the preview's affine RGB stretch.
meta = json.loads((SAMPLE / "meta.json").read_text())
x = np.fromfile(SAMPLE / "x.f32", dtype=np.float32).reshape(6, 128, 128)
rgbf = np.asarray(rgb128, dtype=np.float64)
base_rgb = []
for ch, band in enumerate([2, 1, 0]):
    v, y = x[band].ravel(), rgbf[:, :, ch].ravel()
    m = (y > 3) & (y < 252)
    a, b = np.polyfit(v[m], y[m], 1)
    base_rgb.append(int(round(np.clip(a * meta["baseline_mean"][band] + b, 0, 255))))
baseline_hex = "#%02x%02x%02x" % tuple(base_rgb)

out = {
    "source": "github.com/AtheavenMa/Spectral-Spatial-Interpretation assets/video/hls_burnscar_0163/result.json",
    "channels": data["channels"],
    "g": {"row1": GROW + 1, "col1": GCOL + 1},
    "local": local.tolist(),
    "spectral": T.tolist(),
    "spatial_abs_max": float(np.max(np.abs(S))),
    "phi_abs_max": EXPOSURE,
    "orders": [o["order"] for o in perm["orders"]],
    "deltas": [[s["delta"] for s in o["steps"]] for o in perm["orders"]],
    "baseline_display_hex": baseline_hex,
    "full_value": data["full_value"],
}
(OUT / "data").mkdir(exist_ok=True)
(OUT / "data/ssi-data.js").write_text("window.SSI_DATA = " + json.dumps(out, indent=1) + ";\n")
print("baseline", baseline_hex)
print("local", np.round(local, 5).tolist())
print("spectral", np.round(T, 4).tolist())
print("orders", out["orders"])
