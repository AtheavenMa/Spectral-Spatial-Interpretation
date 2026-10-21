"""v6 masking plates: what "masked at g" does to the data.

For cell g (row 10, col 12; pixels rows 72-79, cols 88-95 of the 128x128 input) and each
of the six channels: the observed 8x8 values, and the per-channel mean baseline
(meta.json baseline_mean) that masking writes into those 64 pixels. Both are shown through
the same per-band 2-98 % stretch + band-colour ramp as the input stack (prep_stack.py),
so observed and masked tiles of one channel are directly comparable.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SAMPLE = Path(sys.argv[1]) / "docs/playground/assets/samples/HLS_BurnScars/sample_0163"
OUT_IMG = Path(sys.argv[2])
OUT_JS = Path(sys.argv[3])
meta = json.loads((SAMPLE / "meta.json").read_text())
x = np.fromfile(SAMPLE / "x.f32", dtype=np.float32).reshape(6, 128, 128)
COL = ["#3277C8", "#27986F", "#DA5A58", "#8062B5", "#D59A3F", "#A45B45"]
DARK = np.array((12, 12, 14), np.float32)
LIGHT = np.array((244, 244, 240), np.float32)
ROW, COLG = 9, 11
r0, c0 = ROW * 8, COLG * 8


def rgb(h):
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], np.float32)


def ramp(v, c, k=0.58):
    return np.where(v < k, DARK + (c - DARK) * (v / k), c + (LIGHT - c) * ((v - k) / (1 - k)) * 0.6)


flat = []
for b in range(6):
    lo, hi = np.percentile(x[b], [2, 98])
    c = rgb(COL[b])
    cell = x[b, r0 : r0 + 8, c0 : c0 + 8]
    v = np.clip((cell - lo) / (hi - lo + 1e-8), 0, 1)[:, :, None]
    tile = np.clip(ramp(v, c), 0, 255).astype("uint8")
    Image.fromarray(tile, "RGB").resize((216, 216), Image.Resampling.NEAREST).save(OUT_IMG / f"g_band_{b + 1}.png", optimize=True)
    vb = np.clip((meta["baseline_mean"][b] - lo) / (hi - lo + 1e-8), 0, 1)
    f = np.clip(ramp(np.array([[[vb]]], np.float32), c), 0, 255).astype(int)[0, 0]
    flat.append("#%02x%02x%02x" % tuple(f))
    print(meta["channels"][b], "cell mean %.3f" % cell.mean(), "baseline %.3f" % meta["baseline_mean"][b], flat[-1])
OUT_JS.write_text("window.SSI_MASK = " + json.dumps({"baseline_display": flat, "baseline_mean": meta["baseline_mean"]}) + ";\n")
