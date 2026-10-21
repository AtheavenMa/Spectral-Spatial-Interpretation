"""Real CPU inference for the interactive SSI laboratory.

This module uses the exact HLS weights, bundled input, preprocessing, target,
baseline and SSI implementation used by demo.py. Additional modalities should
be registered with their own validated model/input adapters.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from io import BytesIO
import os
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from lab.adapters.hls import BAND_NAMES, HLSValueFunction, load_model, load_sample
from lab.commands import explain_command
from lab.runtime import wrap_value
from ssi import explain as explain_ssi

HLS_COMPUTE = {
    "default_grid": 8, "default_permutations": 10,
    "default_baseline": "mean", "default_method": "permutation",
    "permutation_cap": {"4": 20, "8": 20, "16": 10},
    "presets": [
        {"id": "quick", "label": "Quick", "grid": 4, "permutations": 1},
        {"id": "balanced", "label": "Balanced", "grid": 8, "permutations": 10},
    ],
}

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "assets" / "checkpoints" / "hls_unet.pt"
SAMPLE = ROOT / "assets" / "examples" / "hls_sample.npz"
MODEL_ID = "hls-unet"
SAMPLE_ID = "hls-burn-scar"
GRIDS = (4, 8, 16)
BASELINES = ("mean", "zero")
METHODS = ("auto", "permutation", "exact")


def catalog() -> dict:
    from lab.adapters.extra import catalog_entries
    return {
        "models": [{
            "id": MODEL_ID,
            "label": "HLS · UNet",
            "checkpoint": "assets/checkpoints/hls_unet.pt",
            "adapter": "HLS",
            "samples": [{
                "id": SAMPLE_ID,
                "label": "HLS Burn Scar · bundled sample",
                "input": "assets/examples/hls_sample.npz",
            }],
            "channels": list(BAND_NAMES),
            "grids": list(GRIDS),
            "baselines": list(BASELINES),
            "methods": list(METHODS),
            "target": "Burn-class logit · fixed GT burn region",
            "band_note": "HLS bands in order: Blue, Green, Red, NIR, SWIR1, SWIR2.",
            "compute": HLS_COMPUTE,
        }, *catalog_entries()]
    }


def _check_selection(model_id: str, sample_id: str) -> None:
    if model_id == MODEL_ID and sample_id == SAMPLE_ID:
        if not CHECKPOINT.is_file() or not SAMPLE.is_file():
            raise FileNotFoundError("The bundled model checkpoint or input sample is missing.")
        return
    from lab.adapters.extra import SPECS, known
    if not known(model_id, sample_id):
        raise ValueError("Unknown model or input. Select an available pair from /api/catalog.")
    spec = SPECS[model_id]
    if not spec["checkpoint"].is_file() or not spec["sample"].is_file():
        raise FileNotFoundError(f"Checkpoint or input for {model_id} is missing.")


@lru_cache(maxsize=1)
def _bundle():
    _check_selection(MODEL_ID, SAMPLE_ID)
    thread_count = min(max(int(os.getenv("SSI_CPU_THREADS", "4")), 1), 16)
    torch.set_num_threads(thread_count)
    image, mask, x = load_sample(SAMPLE)
    model = load_model(CHECKPOINT, torch.device("cpu"))
    with torch.inference_mode():
        logits = model(torch.as_tensor(x, dtype=torch.float32)[None])
        prediction = logits.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
    return image, mask, x, model, prediction


def _png_data(rgb: np.ndarray) -> str:
    stream = BytesIO()
    Image.fromarray(np.asarray(rgb, dtype=np.uint8), mode="RGB").save(stream, format="PNG")
    return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")


def _mask_rgb(labels: np.ndarray) -> np.ndarray:
    colors = np.asarray([
        [235, 238, 237],   # unburned
        [196, 93, 47],     # burned
        [142, 148, 151],   # invalid
    ], dtype=np.uint8)
    return colors[np.where(labels == 255, 2, labels)]


@lru_cache(maxsize=8)
def previews(model_id: str = MODEL_ID, sample_id: str = SAMPLE_ID) -> dict:
    _check_selection(model_id, sample_id)
    if model_id != MODEL_ID:
        from lab.adapters.extra import previews as extra_previews
        return extra_previews(model_id, sample_id)
    image, mask, _, _, prediction = _bundle()
    rgb = image[[2, 1, 0]].transpose(1, 2, 0)
    low, high = np.percentile(rgb, [2, 98], axis=(0, 1))
    rgb = np.clip((rgb - low) / (high - low + 1e-8), 0, 1)
    return {
        "input": _png_data(np.rint(rgb * 255)),
        "ground_truth": _png_data(_mask_rgb(mask)),
        "target_mask": _png_data(np.repeat(((mask == 1).astype(np.uint8) * 255)[..., None], 3, axis=2)),
        "prediction": _png_data(_mask_rgb(np.where(mask == 255, 255, prediction))),
        "height": int(mask.shape[0]),
        "width": int(mask.shape[1]),
        "summary": "HLS · 6 bands",
        "target_name": "Burn scar",
        "captions": {
            "input": "Input · RGB",
            "ground_truth": "Ground truth",
            "prediction": "UNet prediction",
        },
    }


@lru_cache(maxsize=24)
def run(
    model_id: str, sample_id: str, grid: int, baseline: str,
    method: str, permutations: int, seed: int,
) -> dict:
    _check_selection(model_id, sample_id)
    if grid not in GRIDS:
        raise ValueError("Grid must be one of 4, 8, or 16.")
    allowed = _model_grids(model_id)
    if grid not in allowed:
        raise ValueError(f"This model supports grids {allowed}.")
    if baseline not in BASELINES or method not in METHODS:
        raise ValueError("Unsupported baseline or estimation method.")
    if not isinstance(permutations, int) or not 1 <= permutations <= 20:
        raise ValueError("Permutations must be between 1 and 20.")
    if not isinstance(seed, int) or not 0 <= seed <= 100000:
        raise ValueError("Seed must be between 0 and 100000.")
    if grid == 16 and method == "exact":
        raise ValueError("Exact enumeration is limited to grid sizes 4 and 8 in the lab.")
    cap = _permutation_cap(model_id, grid)
    if method != "exact" and permutations > cap:
        raise ValueError(
            f"This model allows at most {cap} permutations on a {grid}×{grid} grid."
        )
    if model_id != MODEL_ID:
        from lab.adapters.extra import channel_count, run as extra_run
        if method == "exact" and channel_count(model_id) > 6:
            raise ValueError(
                "Exact enumeration in the lab is limited to models with at most 6 channels."
            )
        return extra_run(model_id, sample_id, grid, baseline, method, permutations, seed)

    image, mask, x, model, _ = _bundle()
    if any(d % grid for d in mask.shape):
        raise ValueError("Grid size must divide both image dimensions.")
    value_fn = wrap_value(HLSValueFunction(
        model, x, mask, grid=grid, baseline=baseline,
        batch_size=32, device="cpu",
    ))
    result = explain_ssi(
        value_fn, n_cells=grid * grid, n_channels=len(BAND_NAMES),
        method=method, n_permutations=permutations, seed=seed,
    )
    attr = result.attribution.reshape(grid, grid, len(BAND_NAMES))
    spatial = result.spatial.reshape(grid, grid)
    return {
        "model_id": model_id,
        "sample_id": sample_id,
        "grid": grid,
        "baseline": baseline,
        "method": result.method,
        "permutations": result.n_permutations,
        "seed": seed,
        "channels": list(BAND_NAMES),
        "attribution": attr.tolist(),
        "spatial": spatial.tolist(),
        "spectral": result.spectral.tolist(),
        "full_value": result.full_value,
        "n_evaluations": result.n_evaluations,
        "local_efficiency_error": result.max_local_efficiency_error,
        "target": catalog()["models"][0]["target"],
        "target_name": "Burn scar",
        "command": explain_command(model_id, sample_id, grid, baseline, method, permutations, seed),
        "provenance": _hls_provenance(),
    }


def _model_grids(model_id: str) -> tuple[int, ...]:
    for model in catalog()["models"]:
        if model["id"] == model_id:
            return tuple(model["grids"])
    raise ValueError("Unknown model or input. Select an available pair from /api/catalog.")


def _permutation_cap(model_id: str, grid: int) -> int:
    for model in catalog()["models"]:
        if model["id"] == model_id:
            return int(model["compute"]["permutation_cap"][str(grid)])
    raise ValueError("Unknown model or input. Select an available pair from /api/catalog.")


def score_masks(model_id: str, sample_id: str, grid: int, baseline: str, masks):
    """Score one coalition directly. This does not call ssi.explain."""
    _check_selection(model_id, sample_id)
    if model_id != MODEL_ID:
        from lab.adapters.extra import score_masks as extra_score
        return extra_score(model_id, sample_id, grid, baseline, masks)
    _, mask, x, model, _ = _bundle()
    value = HLSValueFunction(model, x, mask, grid=grid, baseline=baseline, batch_size=32, device="cpu")
    return value(np.asarray(masks, dtype=bool))


@lru_cache(maxsize=4)
def _sha(path: str) -> str:
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hls_provenance() -> dict:
    return {
        "checkpoint_sha256": _sha(str(CHECKPOINT)),
        "sample_sha256": _sha(str(SAMPLE)),
        "band_note": "HLS bands in order: Blue, Green, Red, NIR, SWIR1, SWIR2.",
    }
