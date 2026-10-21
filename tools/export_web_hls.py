"""Export the bundled HLS SSI example for genuine in-browser ONNX inference.

Output is one real checkpoint, one real normalized HLS input, one fixed label
mask, metadata and a true-color display image. The browser computes new SSI
coalition scores using the exported network rather than switching PNGs.

Usage:
  pip install torch onnx onnxruntime pillow numpy
  python tools/export_web_hls.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

# The script is executed directly by GitHub Actions from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image
import torch

from lab.adapters.hls import HLS_MEAN, HLS_STD, TRAIN_MEAN_NORMALIZED, load_model, load_sample
from lab.engine import CHECKPOINT, SAMPLE, ROOT


OUT = ROOT / "docs" / "playground" / "assets"


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    import onnx
    import onnxruntime as ort

    OUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    raw, mask, x = load_sample(SAMPLE)
    model = load_model(CHECKPOINT, torch.device("cpu"))
    model.eval()

    h, w = mask.shape
    dummy = torch.from_numpy(x[None].copy())
    with torch.inference_mode():
        reference = model(dummy).cpu().numpy()

    path = OUT / "hls_unet.onnx"
    torch.onnx.export(
        model,
        dummy,
        str(path),
        opset_version=17,
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
        do_constant_folding=True,
        dynamo=False,
    )
    onnx.checker.check_model(str(path))
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    actual = session.run(None, {"image": dummy.numpy()})[0]
    max_diff = float(np.max(np.abs(reference - actual)))
    assert max_diff < 1e-4, f"ONNX / PyTorch mismatch: {max_diff}"

    # Also check one nontrivial coalition at model input level.
    hidden = x.copy()
    hidden[5, 0:h // 4, 0:w // 4] = TRAIN_MEAN_NORMALIZED[5]
    other = hidden[None].astype("float32")
    with torch.inference_mode():
        ref2 = model(torch.from_numpy(other)).cpu().numpy()
    actual2 = session.run(None, {"image": other})[0]
    mask_diff = float(np.max(np.abs(ref2 - actual2)))
    assert mask_diff < 1e-4, f"Masked ONNX / PyTorch mismatch: {mask_diff}"

    (OUT / "hls_input.f32").write_bytes(np.ascontiguousarray(x, dtype="<f4").tobytes())
    (OUT / "hls_mask.u8").write_bytes(np.ascontiguousarray(mask, dtype=np.uint8).tobytes())
    rgb = raw[[2, 1, 0]].transpose(1, 2, 0)
    low, high = np.percentile(rgb, [2, 98], axis=(0, 1))
    rgb = np.uint8(np.rint(255 * np.clip((rgb - low) / (high - low + 1e-8), 0, 1)))
    Image.fromarray(rgb, "RGB").save(OUT / "hls_rgb.webp", "WEBP", quality=94, method=6)

    roi = mask == 1
    score_ref = float(reference[0, 1][roi].mean())
    score_onnx = float(actual[0, 1][roi].mean())
    assert abs(score_ref - score_onnx) < 1e-5
    meta = {
        "version": 1,
        "dataset": "HLS Burn Scars",
        "model": "Original HLS UNet, 6 input bands, 2 output classes",
        "width": w, "height": h,
        "channels": ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"],
        "grid_options": [4, 8, 16],
        "baseline_mean": [float(v) for v in TRAIN_MEAN_NORMALIZED],
        "baseline_zero": [float(v) for v in (-HLS_MEAN / HLS_STD)],
        "region_pixels": int(roi.sum()),
        "target": "Mean burn-class logit over the fixed ground-truth burn region",
        "reference_full_score": score_ref,
        "onnx_full_score": score_onnx,
        "onnx_max_logit_diff": max_diff,
        "masked_onnx_max_logit_diff": mask_diff,
        "original_checkpoint_sha256": checksum(CHECKPOINT),
        "original_sample_sha256": checksum(SAMPLE),
        "files": {},
    }
    for entry in ("hls_unet.onnx", "hls_input.f32", "hls_mask.u8", "hls_rgb.webp"):
        asset = OUT / entry
        meta["files"][entry] = {"sha256": checksum(asset), "bytes": asset.stat().st_size}
    (OUT / "hls_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"export": meta, "out": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
