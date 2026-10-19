"""Runnable adapters for the five datasets beyond the bundled HLS demo.

Each entry loads one exported checkpoint and one original model input. The
scalar target is fixed before any coalition is scored.
"""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import torch
import torch.nn.functional as F

from lab.adapters.backbones import ResNet18Classifier
from lab.commands import explain_command
from lab.runtime import raise_if_cancelled, wrap_value
from model import UNet, convert_legacy_state_dict
from ssi import explain as explain_ssi

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "lab"

PAVIA_NAMES = {
    1: "Asphalt", 2: "Meadows", 3: "Gravel", 4: "Trees",
    5: "Painted metal sheets", 6: "Bare Soil", 7: "Bitumen",
    8: "Self-Blocking Bricks", 9: "Shadows",
}
SALINAS_NAMES = {
    1: "Brocoli green weeds 1", 2: "Brocoli green weeds 2", 3: "Fallow",
    4: "Fallow rough plow", 5: "Fallow smooth", 6: "Stubble", 7: "Celery",
    8: "Grapes untrained", 9: "Soil vinyard develop", 10: "Corn senesced green weeds",
    11: "Lettuce romaine 4wk", 12: "Lettuce romaine 5wk", 13: "Lettuce romaine 6wk",
    14: "Lettuce romaine 7wk", 15: "Vinyard untrained", 16: "Vinyard vertical trellis",
}
LONGKOU_NAMES = {
    1: "Corn", 2: "Cotton", 3: "Sesame", 4: "Broad-leaf soybean",
    5: "Narrow-leaf soybean", 6: "Rice", 7: "Water", 8: "Roads and houses",
    9: "Mixed weed",
}


def _bands(n: int) -> tuple[str, ...]:
    """Original channel index. These cubes do not store instrument wavelengths."""
    return tuple(f"Band {index + 1:03d}" for index in range(n))


HSI_BAND_NOTE = (
    "The source cube has no wavelength vector. Labels are 1-based channel indices "
    "in the file's original order, not measured nanometer centers."
)


def _spec(**kwargs) -> dict:
    kwargs["checkpoint"] = ASSETS / "checkpoints" / kwargs["weight_file"]
    kwargs["sample"] = ASSETS / "samples" / kwargs["sample_file"]
    return kwargs


SPECS = {
    "cub-200": _spec(
        model_id="cub-200", sample_id="cub-0158", label="CUB-200 · ResNet-18",
        sample_label="Parakeet Auklet · test index 158",
        weight_file="cub_resnet18.pt", sample_file="cub_0158.npz",
        kind="cls", head="linear", small_input=False, dropout=0.0,
        in_channels=3, n_classes=200, channels=("Red", "Green", "Blue"),
        target="Predicted class logit, fixed before masking",
        band_note="RGB channels after ImageNet normalization. Red, Green, Blue are the stored order.",
        batch_size=4,
        compute={
            "default_grid": 8, "default_permutations": 4,
            "default_baseline": "mean", "default_method": "permutation",
            "permutation_cap": {"4": 20, "8": 10, "16": 1},
            "presets": [
                {"id": "quick", "label": "Quick", "grid": 4, "permutations": 1},
                {"id": "balanced", "label": "Balanced", "grid": 8, "permutations": 4},
            ],
        },
    ),
    "eurosat": _spec(
        model_id="eurosat", sample_id="eurosat-1294", label="EuroSAT · ResNet-18",
        sample_label="HerbaceousVegetation · test index 1294",
        weight_file="eurosat_resnet18.pt", sample_file="eurosat_1294.npz",
        kind="cls", head="mlp", small_input=True, dropout=0.15,
        in_channels=13, n_classes=10,
        channels=(
            "B01 443 nm", "B02 490 nm", "B03 560 nm", "B04 665 nm", "B05 705 nm",
            "B06 740 nm", "B07 783 nm", "B08 842 nm", "B8A 865 nm", "B09 945 nm",
            "B10 1375 nm", "B11 1610 nm", "B12 2190 nm",
        ),
        target="Predicted class logit, fixed before masking",
        band_note="Sentinel-2 band ids and nominal center wavelengths, in dataset order.",
        batch_size=16,
        compute={
            "default_grid": 8, "default_permutations": 3,
            "default_baseline": "mean", "default_method": "permutation",
            "permutation_cap": {"4": 20, "8": 3, "16": 1},
            "presets": [
                {"id": "quick", "label": "Quick", "grid": 4, "permutations": 1},
                {"id": "balanced", "label": "Balanced", "grid": 8, "permutations": 3},
            ],
        },
    ),
    "paviau": _spec(
        model_id="paviau", sample_id="paviau-0008", label="Pavia University · UNet",
        sample_label="Self-Blocking Bricks · val tile 8",
        weight_file="paviau_unet.pt", sample_file="paviau_0008.npz",
        kind="seg", in_channels=103, n_classes=10, base_channels=64,
        grids=(4, 8),
        channels=_bands(103),
        band_note=HSI_BAND_NOTE,
        class_names=PAVIA_NAMES,
        target="Mean target-class logit on the fixed ground-truth region",
        batch_size=16,
        compute={
            "default_grid": 4, "default_permutations": 1,
            "default_baseline": "mean", "default_method": "permutation",
            "permutation_cap": {"4": 8, "8": 3},
            "presets": [
                {"id": "quick", "label": "Quick", "grid": 4, "permutations": 1},
                {"id": "balanced", "label": "Balanced", "grid": 4, "permutations": 3},
            ],
        },
    ),
    "salinas": _spec(
        model_id="salinas", sample_id="salinas-0000", label="Salinas · UNet",
        sample_label="Brocoli green weeds 2 · val tile 0",
        weight_file="salinas_unet.pt", sample_file="salinas_0000.npz",
        kind="seg", in_channels=204, n_classes=17, base_channels=64,
        grids=(4, 8),
        channels=_bands(204),
        band_note=HSI_BAND_NOTE,
        class_names=SALINAS_NAMES,
        target="Mean target-class logit on the fixed ground-truth region",
        batch_size=16,
        compute={
            "default_grid": 4, "default_permutations": 1,
            "default_baseline": "mean", "default_method": "permutation",
            "permutation_cap": {"4": 4, "8": 1},
            "presets": [
                {"id": "quick", "label": "Quick", "grid": 4, "permutations": 1},
            ],
        },
    ),
    "whu-hi-longkou": _spec(
        model_id="whu-hi-longkou", sample_id="longkou-0000", label="WHU-Hi-LongKou · UNet",
        sample_label="Broad-leaf soybean · val tile 0",
        weight_file="longkou_unet.pt", sample_file="longkou_0000.npz",
        kind="seg", in_channels=270, n_classes=10, base_channels=64,
        grids=(4, 8),
        channels=_bands(270),
        band_note=HSI_BAND_NOTE,
        class_names=LONGKOU_NAMES,
        target="Mean target-class logit on the fixed ground-truth region",
        batch_size=8,
        compute={
            "default_grid": 4, "default_permutations": 1,
            "default_baseline": "mean", "default_method": "permutation",
            "permutation_cap": {"4": 3, "8": 1},
            "presets": [
                {"id": "quick", "label": "Quick", "grid": 4, "permutations": 1},
            ],
        },
    ),
}


def known(model_id: str, sample_id: str) -> bool:
    spec = SPECS.get(model_id)
    return spec is not None and spec["sample_id"] == sample_id


def channel_count(model_id: str) -> int:
    return len(SPECS[model_id]["channels"])


def catalog_entries() -> list[dict]:
    entries = []
    for spec in SPECS.values():
        entries.append({
            "id": spec["model_id"],
            "label": spec["label"],
            "checkpoint": f"assets/lab/checkpoints/{spec['weight_file']}",
            "adapter": spec["model_id"],
            "samples": [{
                "id": spec["sample_id"],
                "label": spec["sample_label"],
                "input": f"assets/lab/samples/{spec['sample_file']}",
            }],
            "channels": list(spec["channels"]),
            "grids": list(spec.get("grids", (4, 8, 16))),
            "baselines": ["mean", "zero"],
            "methods": ["auto", "permutation", "exact"],
            "target": spec["target"],
            "band_note": spec["band_note"],
            "compute": spec["compute"],
        })
    return entries


def _load_arrays(spec: dict):
    if not spec["checkpoint"].is_file() or not spec["sample"].is_file():
        raise FileNotFoundError(f"Missing checkpoint or sample for {spec['model_id']}.")
    with np.load(spec["sample"], allow_pickle=False) as data:
        x = data["x"].astype(np.float32)
        rgb = data["rgb"].astype(np.uint8)
        label = data["label"].astype(np.int64)
        mean = data["mean"].astype(np.float32)
        std = data["std"].astype(np.float32)
        target_class = int(data["target_class"])
    if x.shape[0] != spec["in_channels"] or mean.shape != (spec["in_channels"],):
        raise ValueError(f"{spec['model_id']} sample channel count does not match the adapter.")
    return x, rgb, label, mean, std, target_class


def _load_model(spec: dict) -> torch.nn.Module:
    torch.set_num_threads(min(max(int(os.getenv("SSI_CPU_THREADS", "4")), 1), 16))
    if spec["kind"] == "cls":
        model = ResNet18Classifier(
            spec["in_channels"], spec["n_classes"], head=spec["head"],
            small_input=spec["small_input"], dropout=spec["dropout"],
        )
        state = torch.load(spec["checkpoint"], map_location="cpu", weights_only=True)
    else:
        model = UNet(
            n_channels=spec["in_channels"], n_classes=spec["n_classes"],
            base_channels=spec["base_channels"], bilinear=True,
        )
        state = torch.load(spec["checkpoint"], map_location="cpu", weights_only=True)
        state = convert_legacy_state_dict(state)
    model.load_state_dict(state, strict=True)
    return model.eval()


class _Value:
    def __init__(self, model, x, spec, label, mean, std, target_class, grid: int, baseline: str):
        self.model = model
        self.grid = grid
        self.channels = int(x.shape[0])
        self.height, self.width = int(x.shape[1]), int(x.shape[2])
        if self.height % grid or self.width % grid:
            raise ValueError("Grid size must divide both image dimensions.")
        self.x = torch.as_tensor(x, dtype=torch.float32)[None]
        if baseline == "mean":
            values = np.zeros(self.channels, dtype=np.float32)
        elif baseline == "zero":
            values = (-mean / std).astype(np.float32)
        else:
            raise ValueError("baseline must be 'mean' or 'zero'")
        self.baseline = torch.as_tensor(values)[None, :, None, None]
        self.kind = spec["kind"]
        self.target_class = target_class
        if self.kind == "seg":
            self.region = torch.as_tensor(label == target_class)
            if not bool(self.region.any()):
                raise ValueError("The fixed ground-truth region is empty.")
        self.batch_size = int(spec["batch_size"])

    def __call__(self, masks):
        masks = np.asarray(masks)
        if masks.dtype != np.bool_ or masks.ndim != 3 or masks.shape[1:] != (self.grid ** 2, self.channels):
            raise ValueError("Expected Boolean coalitions (batch, grid**2, channels)")
        scores = []
        with torch.inference_mode():
            for start in range(0, len(masks), self.batch_size):
                raise_if_cancelled()
                coalition = torch.as_tensor(masks[start:start + self.batch_size])
                coalition = coalition.permute(0, 2, 1).reshape(-1, self.channels, self.grid, self.grid).float()
                coalition = F.interpolate(coalition, size=(self.height, self.width), mode="nearest")
                perturbed = self.baseline + coalition * (self.x - self.baseline)
                logits = self.model(perturbed)
                if self.kind == "cls":
                    scores.append(logits[:, self.target_class].cpu().numpy())
                else:
                    scores.append(logits[:, self.target_class][:, self.region].mean(dim=1).cpu().numpy())
        return np.concatenate(scores).astype(np.float64) if scores else np.empty(0)


@lru_cache(maxsize=8)
def _bundle(model_id: str):
    spec = SPECS[model_id]
    x, rgb, label, mean, std, target_class = _load_arrays(spec)
    model = _load_model(spec)
    with torch.inference_mode():
        logits = model(torch.as_tensor(x, dtype=torch.float32)[None])
    if spec["kind"] == "cls":
        prediction = int(logits.argmax(dim=1).item())
    else:
        prediction = logits.argmax(dim=1)[0].cpu().numpy().astype(np.int64)
    return spec, x, rgb, label, mean, std, target_class, model, prediction


def _png(rgb: np.ndarray) -> str:
    import base64
    from io import BytesIO
    stream = BytesIO()
    Image.fromarray(np.asarray(rgb, dtype=np.uint8), mode="RGB").save(stream, format="PNG")
    return "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")


def _stamp(rgb: np.ndarray, text: str) -> np.ndarray:
    image = Image.fromarray(np.asarray(rgb, dtype=np.uint8), mode="RGB")
    draw = ImageDraw.Draw(image)
    height = 22
    top = image.height - height
    draw.rectangle((0, top, image.width, image.height), fill=(246, 246, 244))
    draw.text((6, top + 4), text, fill=(28, 38, 68))
    return np.asarray(image)


def _card(text: str, side: int) -> np.ndarray:
    image = Image.new("RGB", (side, side), (246, 246, 244))
    draw = ImageDraw.Draw(image)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial) < side * 0.84:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    height = 18 * max(len(lines), 1)
    y = max(8, (side - height) // 2)
    for line in lines:
        draw.text(((side - draw.textlength(line)) / 2, y), line, fill=(28, 38, 68))
        y += 18
    return np.asarray(image)


_SEG_COLORS = np.asarray([
    [230, 230, 228], [166, 206, 227], [31, 120, 180], [178, 223, 138],
    [51, 160, 44], [251, 154, 153], [227, 26, 28], [253, 191, 111],
    [255, 127, 0], [202, 178, 214], [106, 61, 154], [255, 255, 153],
    [177, 89, 40], [141, 211, 199], [190, 186, 218], [251, 128, 114],
    [128, 177, 211],
], dtype=np.uint8)


def _seg_rgb(labels: np.ndarray) -> np.ndarray:
    out = np.full(labels.shape + (3,), 198, dtype=np.uint8)
    valid = (labels >= 0) & (labels < len(_SEG_COLORS))
    out[valid] = _SEG_COLORS[labels[valid]]
    out[labels == 255] = (246, 246, 244)
    return out


def previews(model_id: str, sample_id: str) -> dict:
    if not known(model_id, sample_id):
        raise ValueError("Unknown model or input. Select an available pair from /api/catalog.")
    spec, _, rgb, label, _, _, target_class, _, prediction = _bundle(model_id)
    side = int(rgb.shape[0])
    if spec["kind"] == "cls":
        names = json.loads((spec["sample"].with_suffix(".json")).read_text())["class_names"]
        gt_name = names[int(label.reshape(-1)[0])]
        pred_name = names[int(prediction)]
        return {
            "input": _png(rgb),
            "ground_truth": _png(_stamp(rgb, gt_name)),
            "prediction": _png(_stamp(rgb, pred_name)),
            "height": side, "width": int(rgb.shape[1]),
            "summary": f"{spec['label'].split('·')[0].strip()} · {len(spec['channels'])} bands",
            "target_name": gt_name,
            "captions": {
                "input": "Input",
                "ground_truth": "True label",
                "prediction": "Predicted label",
            },
        }
    pred = np.where(label == 255, 255, prediction)
    target_name = spec["class_names"][target_class]
    return {
        "input": _png(rgb),
        "ground_truth": _png(_seg_rgb(label)),
        "prediction": _png(_seg_rgb(pred)),
        "height": side, "width": int(rgb.shape[1]),
        "summary": f"{spec['label'].split('·')[0].strip()} · {len(spec['channels'])} bands",
        "target_name": target_name,
        "captions": {
            "input": "Input",
            "ground_truth": "Ground truth · " + target_name,
            "prediction": "Prediction",
        },
    }


def run(model_id: str, sample_id: str, grid: int, baseline: str, method: str, permutations: int, seed: int) -> dict:
    spec, x, _, label, mean, std, target_class, model, _ = _bundle(model_id)
    value = _Value(model, x, spec, label, mean, std, target_class, grid, baseline)
    result = explain_ssi(
        wrap_value(value), n_cells=grid * grid, n_channels=value.channels,
        method=method, n_permutations=permutations, seed=seed,
    )
    attr = result.attribution.reshape(grid, grid, value.channels)
    return {
        "model_id": model_id,
        "sample_id": sample_id,
        "grid": grid,
        "baseline": baseline,
        "method": result.method,
        "permutations": result.n_permutations,
        "seed": seed,
        "channels": list(spec["channels"]),
        "attribution": attr.tolist(),
        "spatial": result.spatial.reshape(grid, grid).tolist(),
        "spectral": result.spectral.tolist(),
        "full_value": result.full_value,
        "n_evaluations": result.n_evaluations,
        "local_efficiency_error": result.max_local_efficiency_error,
        "target": spec["target"],
        "target_name": _target_name(spec, target_class),
        "command": explain_command(model_id, sample_id, grid, baseline, method, permutations, seed),
        "provenance": _provenance(spec),
    }


def score_masks(model_id: str, sample_id: str, grid: int, baseline: str, masks) -> np.ndarray:
    """Score coalitions with the adapter directly, without calling ssi.explain."""
    spec, x, _, label, mean, std, target_class, model, _ = _bundle(model_id)
    value = _Value(model, x, spec, label, mean, std, target_class, grid, baseline)
    return value(np.asarray(masks, dtype=bool))


def _target_name(spec: dict, target_class: int) -> str:
    if spec["kind"] == "seg":
        return spec["class_names"][target_class]
    names = json.loads(spec["sample"].with_suffix(".json").read_text())["class_names"]
    return names[target_class]


@lru_cache(maxsize=16)
def _sha(path: str) -> str:
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _provenance(spec: dict) -> dict:
    return {
        "checkpoint_sha256": _sha(str(spec["checkpoint"])),
        "sample_sha256": _sha(str(spec["sample"])),
        "band_note": spec["band_note"],
    }
