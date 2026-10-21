"""Generate reproducible Visual-Atlas-style SSI figures from real files.

The checkpoint must match a supported architecture family. A multispectral or
hyperspectral "image" must be a lossless NPZ with channel tensors and fixed
target metadata; a rendered RGB PNG cannot preserve hundreds of spectral
channels. For CUB-200, a regular RGB image is also supported if target_class is
specified. All experiments score *real* model coalitions with ssi.explain.

Outputs:
  atlas.png        (a) input, (b) GT/target, (c) spatial SSI on image,
                   (d) signed per-channel overlays, (e) spectral contributions
  result.json      full signed grid x grid x band attribution and provenance
  attribution.npz  lossless attribution, spatial, spectral, original target mask
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
import torch

from lab.adapters.hls import BAND_NAMES, HLSValueFunction, load_model, load_sample
from lab.adapters.extra import SPECS, _Value, _load_model
from ssi import explain as ssi_explain


@dataclass
class Prepared:
    family: str
    image: np.ndarray       # RGB display image HxWx3, uint8
    labels: np.ndarray | None
    roi: np.ndarray | None
    target_class: int
    target_name: str
    bands: tuple[str, ...]
    checkpoint: Path
    source: Path
    model: torch.nn.Module
    scorer_factory: Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def true_color(source: np.ndarray, indices: tuple[int, int, int] | None = None) -> np.ndarray:
    """Contrast-stretch only the displayed RGB. Never change inference tensor."""
    bands = source.shape[0]
    if indices is None:
        indices = (min(2, bands - 1), min(1, bands - 1), 0)
    rgb = np.asarray(source[list(indices)].transpose(1, 2, 0), dtype=np.float32)
    lo = np.percentile(rgb, 2, axis=(0, 1))
    hi = np.percentile(rgb, 98, axis=(0, 1))
    return np.asarray(
        np.rint(255 * np.clip((rgb - lo) / np.maximum(hi - lo, 1e-7), 0, 1)),
        dtype=np.uint8,
    )


def _target_name(family: str, target_class: int) -> str:
    from lab.adapters.extra import SPECS
    spec = SPECS.get(family)
    if spec is None:
        return "Burn scar"
    if spec["kind"] == "seg":
        return spec["class_names"].get(target_class, f"Class {target_class}")
    meta_path = Path(spec["sample"]).with_suffix(".json")
    if meta_path.is_file():
        data = json.loads(meta_path.read_text())
        names = data.get("class_names", [])
        if 0 <= target_class < len(names):
            return str(names[target_class])
    return f"Class {target_class}"


def prepare(
    family: str, checkpoint: str | Path, image: str | Path,
    *, target_class: int | None = None, target_mask: str | Path | None = None,
) -> Prepared:
    checkpoint = Path(checkpoint).expanduser().resolve()
    image = Path(image).expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Checkpoint does not exist: {checkpoint}")
    if not image.is_file():
        raise FileNotFoundError(f"Input image does not exist: {image}")
    if family not in ("hls-unet", *SPECS.keys()):
        raise ValueError(f"Unsupported model family: {family!r}. Choose a registered architecture.")

    if family == "hls-unet":
        if image.suffix.lower() != ".npz":
            raise ValueError("HLS requires NPZ with 'image' (6,H,W) and 'mask' (H,W).")
        raw, gt, x = load_sample(image)
        target = 1 if target_class is None else int(target_class)
        if target != 1:
            raise ValueError("The registered HLS UNet target is burn class 1.")
        if target_mask is not None:
            raise ValueError("For HLS, supply the fixed burn region in the sample NPZ mask.")
        model = load_model(checkpoint, torch.device("cpu"))

        def scorer(grid: int, baseline: str):
            return HLSValueFunction(model, x, gt, grid=grid, baseline=baseline, device="cpu", batch_size=32)

        return Prepared(
            family, true_color(raw, (2, 1, 0)), gt, gt == 1, 1, "Burn scar",
            tuple(BAND_NAMES), checkpoint, image, model, scorer,
        )

    spec = dict(SPECS[family])
    spec["checkpoint"] = checkpoint
    if image.suffix.lower() == ".npz":
        with np.load(image, allow_pickle=False) as data:
            required = ("x", "mean", "std")
            absent = [name for name in required if name not in data]
            if absent:
                raise ValueError(f"Input NPZ is missing {', '.join(absent)}.")
            x = np.asarray(data["x"], dtype=np.float32)
            mean = np.asarray(data["mean"], dtype=np.float32)
            std = np.asarray(data["std"], dtype=np.float32)
            gt = np.asarray(data["label"], dtype=np.int64) if "label" in data else None
            tc = int(target_class) if target_class is not None else (
                int(data["target_class"]) if "target_class" in data else None
            )
            rgb = np.asarray(data["rgb"]) if "rgb" in data else None
    elif family == "cub-200" and image.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        if target_class is None:
            raise ValueError("RGB image classification requires --target-class.")
        # Explicit local-input convention: resize to this checkpoint's 448px
        # classification tensor shape and apply ImageNet RGB normalization.
        original = Image.open(image).convert("RGB").resize((448, 448), Image.Resampling.BICUBIC)
        rgb = np.asarray(original, dtype=np.uint8)
        x = rgb.astype(np.float32).transpose(2, 0, 1) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = (x - mean[:, None, None]) / std[:, None, None]
        gt, tc = None, int(target_class)
    else:
        raise ValueError(
            f"{family} requires an NPZ with original model input (C,H,W), "
            "mean/std and target metadata; an RGB PNG loses spectral channels."
        )

    if x.ndim != 3 or x.shape[0] != spec["in_channels"]:
        raise ValueError(f"{family} requires input (C,H,W) with C={spec['in_channels']}.")
    c, h, w = x.shape
    if h < 4 or w < 4 or not np.isfinite(x).all():
        raise ValueError("Input must have spatial dimensions >=4 and finite model-normalized values.")
    if mean.shape != (c,) or std.shape != (c,) or not np.isfinite(mean).all() or \
            not np.isfinite(std).all() or np.any(std <= 0):
        raise ValueError("mean/std must each contain C finite values, std strictly positive.")
    if tc is None or not 0 <= tc < spec["n_classes"]:
        raise ValueError("The target class is missing or out of range for the checkpoint.")

    if spec["kind"] == "seg":
        if target_mask is not None:
            roi = np.asarray(Image.open(target_mask).convert("L")) > 0
            gt = np.where(roi, tc, 0).astype(np.int64)  # fixed ROI, not a prediction
        else:
            if gt is None:
                raise ValueError("Segmentation needs a GT label map in NPZ or --target-mask.")
            if gt.shape != (h, w):
                raise ValueError(f"Ground-truth label map must have shape {(h, w)}.")
            roi = gt == tc
        if roi.shape != (h, w) or not roi.any():
            raise ValueError("The fixed target region is empty or has an invalid shape.")
    else:
        if target_mask is not None:
            raise ValueError("Classification has a fixed target class, not a segmentation ROI.")
        gt = np.asarray(tc, dtype=np.int64)
        roi = None

    if rgb is None:
        # Hyperspectral pseudo-RGB uses three sampled channel positions for display.
        # It does not alter the full model input or infer unrecorded wavelengths.
        indices = (min(c - 1, round(c * .68)), min(c - 1, round(c * .38)), min(c - 1, round(c * .12)))
        rgb = true_color(x * std[:, None, None] + mean[:, None, None], indices)
    if rgb.ndim != 3 or rgb.shape != (h, w, 3):
        raise ValueError(f"RGB display image must have shape ({h},{w},3).")
    if not np.isfinite(rgb).all():
        raise ValueError("RGB display image contains nonfinite pixels.")
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    model = _load_model(spec)

    def scorer(grid: int, baseline: str):
        return _Value(model, x, spec, gt, mean, std, tc, grid, baseline)

    return Prepared(
        family, rgb, gt, roi, tc, _target_name(family, tc),
        tuple(spec["channels"]), checkpoint, image, model, scorer,
    )


def explain_artifacts(
    checkpoint: str | Path, image: str | Path, *,
    family: str, output: str | Path,
    grid: int = 4, baseline: str = "mean", method: str = "permutation",
    permutations: int = 1, seed: int = 0, target_class: int | None = None,
    target_mask: str | Path | None = None, display_channels: int = 10,
) -> dict:
    """Run the original SSI estimator and write a PNG, JSON and numeric NPZ.

    This callable is intended for a trusted local Python process. Do not turn
    arbitrary user-provided pickle files into an unauthenticated web endpoint.
    """
    if grid < 1 or grid > 32 or not isinstance(grid, int):
        raise ValueError("Grid must be an integer between 1 and 32.")
    if not 1 <= permutations <= 50:
        raise ValueError("Permutations must be in [1, 50].")
    if method not in ("exact", "permutation", "auto"):
        raise ValueError("method must be exact, permutation or auto.")
    if baseline not in ("mean", "zero"):
        raise ValueError("Baseline must be mean or zero.")
    if not 1 <= display_channels <= 12:
        raise ValueError("display_channels must be in [1, 12].")

    sample = prepare(family, checkpoint, image, target_class=target_class, target_mask=target_mask)
    channels = len(sample.bands)
    if method == "exact" and channels > 16:
        raise ValueError("Exact Shapley enumeration is unavailable for >16 channels.")
    h, w = sample.image.shape[:2]
    if h % grid or w % grid:
        raise ValueError(f"Grid {grid} must divide image height and width ({h},{w}).")

    vf = sample.scorer_factory(grid, baseline)
    result = ssi_explain(vf, grid * grid, channels, method=method,
                         n_permutations=permutations, seed=seed)
    attribution = result.attribution.reshape(grid, grid, channels)
    spatial = result.spatial.reshape(grid, grid)
    spectral = result.spectral

    output = Path(output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    plot_path = output / "atlas.png"
    json_path = output / "result.json"
    npz_path = output / "attribution.npz"
    from lab.atlas_plot import draw_atlas
    visual = draw_atlas(sample, attribution, spatial, spectral, plot_path,
                        display_channels=display_channels)
    if sample.roi is None:
        saved_mask = np.empty((0, 0), dtype=bool)
    else:
        saved_mask = sample.roi
    np.savez_compressed(npz_path, attribution=attribution, spatial=spatial,
                        spectral=spectral, fixed_target_mask=saved_mask)
    payload = {
        "model_family": family, "checkpoint_sha256": sha256(sample.checkpoint),
        "image_sha256": sha256(sample.source),
        "input_tensor_shape": [channels, h, w],
        "target_class": sample.target_class,
        "target_name": sample.target_name,
        "target": ("Fixed GT region class logit" if sample.roi is not None else "Fixed class logit"),
        "fixed_region_pixels": int(sample.roi.sum()) if sample.roi is not None else None,
        "channels": list(sample.bands),
        "grid": grid, "baseline": baseline, "method": result.method,
        "permutations": result.n_permutations, "seed": seed,
        "full_value": result.full_value,
        "n_evaluations": result.n_evaluations,
        "local_efficiency_error": result.max_local_efficiency_error,
        "attribution": attribution.tolist(),
        "spatial": spatial.tolist(),
        "spectral": spectral.tolist(),
        "visualized_channel_indices": visual["indices"],
        "files": {"png": plot_path.name, "json": json_path.name, "npz": npz_path.name},
    }
    json_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    return {"png": str(plot_path), "json": str(json_path), "npz": str(npz_path),
            "target": sample.target_name, "n_evaluations": result.n_evaluations,
            "local_efficiency_error": result.max_local_efficiency_error}
