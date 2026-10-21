"""Export a reproducible HLS Atlas plate from the stored real SSI computation.

The original Atlas sample_0163.png used a DIFFERENT experiment setting and must
not be paired with these signed spectral totals.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from lab.atlas_plot import draw_atlas


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets/video/hls_burnscar_0163/result.json"
META = ROOT / "docs/playground/assets/samples/HLS_BurnScars/sample_0163/meta.json"
ASSETS = META.parent
OUTPUT = ROOT / "examples/HLS_BurnScars/sample_0163_mean_g16_k5.png"


def main() -> None:
    result = json.loads(DATA.read_text())
    meta = json.loads(META.read_text())

    assert result["sample_id"] == "HLS_BurnScars/sample_0163"
    assert result["grid"] == 16
    assert result["baseline"] == "mean"
    assert result["permutations"] == 5
    assert result["method"] == "permutation"
    assert meta["region_pixels"] == 2734

    attribution = np.asarray(result["attribution"], dtype=np.float64)
    spatial = np.asarray(result["spatial"], dtype=np.float64)
    spectral = np.asarray(result["spectral"], dtype=np.float64)
    assert attribution.shape == (16, 16, 6)
    assert spatial.shape == (16, 16)
    assert spectral.shape == (6,)
    assert np.allclose(spatial, attribution.sum(axis=-1), rtol=0, atol=1e-7)
    assert np.allclose(spectral, attribution.sum(axis=(0, 1)), rtol=0, atol=1e-7)
    assert spectral[4] > 0 and spectral[5] > 0, (
        "The image may only be displayed if BOTH SWIR contributions are positive."
    )

    w, h = int(meta["width"]), int(meta["height"])
    image = np.asarray(Image.open(ASSETS / "rgb.webp").convert("RGB"), dtype=np.uint8)
    labels = np.fromfile(ASSETS / "mask.u8", dtype=np.uint8).reshape(h, w)
    roi = labels == 1
    assert image.shape == (h, w, 3)
    assert int(roi.sum()) == meta["region_pixels"], "Mismatched GT image"

    sample = SimpleNamespace(
        image=image,
        roi=roi,
        labels=labels,
        bands=result["channels"],
        target_name="Burn scar",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    draw_atlas(sample, attribution, spatial, spectral, OUTPUT)
    with Image.open(OUTPUT) as generated:
        assert generated.width >= 2400 and generated.height >= 1500
    print(f"Saved: {OUTPUT}")
    for name, value in zip(result["channels"], spectral):
        print(f"{name}: {value:+.6f}")


if __name__ == "__main__":
    main()
