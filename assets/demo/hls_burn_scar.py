"""Bundled HLS Burn Scar demo. Run from repository root: python assets/demo/hls_burn_scar.py."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import platform
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import torch

from lab.adapters.hls import BAND_NAMES, HLSValueFunction, load_model, load_sample
from ssi import explain


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plot_result(image, mask, prediction, result, grid, baseline, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    rgb = image[[2, 1, 0]].transpose(1, 2, 0)
    low, high = np.percentile(rgb, [2, 98], axis=(0, 1))
    rgb = np.clip((rgb-low)/(high-low+1e-8), 0, 1)
    attr = result.attribution.reshape(grid, grid, 6).transpose(2, 0, 1)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.titlesize": 12, "axes.titleweight": "medium"})
    fig = plt.figure(figsize=(13.8, 9.2), layout="constrained", facecolor="white")
    gs = fig.add_gridspec(3, 4, width_ratios=[1, 1, 1, 1.12])
    top = [fig.add_subplot(gs[0, i]) for i in range(4)]
    top[0].imshow(rgb); top[0].set_title("HLS image · RGB")
    gt = np.where(mask == 255, 2, mask)
    top[1].imshow(gt, cmap=ListedColormap(["#edf0ef", "#c45d2f", "#8e9497"]), vmin=0, vmax=2)
    top[1].set_title("Ground truth · burn region")
    top[2].imshow(np.where(mask == 255, 2, prediction),
                  cmap=ListedColormap(["#edf0ef", "#c45d2f", "#8e9497"]), vmin=0, vmax=2)
    top[2].set_title("UNet prediction")
    spatial = result.spatial.reshape(grid, grid)
    lim = max(float(np.abs(spatial).max()), 1e-12)
    im = top[3].imshow(spatial, cmap="RdBu_r", vmin=-lim, vmax=lim, interpolation="nearest")
    top[3].set_title("Spatial attribution · channel sum")
    fig.colorbar(im, ax=top[3], orientation="horizontal", fraction=.065, pad=.06, label="Logit contribution")
    for ax in top:
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)
    axes = []
    lim = max(float(np.abs(attr).max()), 1e-12)
    for c, name in enumerate(BAND_NAMES):
        ax = fig.add_subplot(gs[1+c//3, c%3]); axes.append(ax)
        im = ax.imshow(attr[c], cmap="RdBu_r", vmin=-lim, vmax=lim, interpolation="nearest")
        ax.set_title(name)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)
    fig.colorbar(im, ax=axes, orientation="horizontal", fraction=.035, pad=.025,
                 label="Channel contribution per cell · shared signed scale")
    ax = fig.add_subplot(gs[1:, 3])
    scores = result.spectral
    ax.barh(BAND_NAMES, scores, color=["#bd5035" if v >= 0 else "#347caa" for v in scores], height=.55)
    ax.invert_yaxis(); ax.axvline(0, color="#89949b", linewidth=.8)
    ax.set_title("Spectral attribution\nsum over spatial cells", pad=18)
    ax.set_xlabel("Logit contribution")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=.2); ax.set_axisbelow(True)
    for i, value in enumerate(scores):
        ax.annotate(f"{value:+.3f}", (value, i), xytext=(4 if value >= 0 else -4, 0),
                    textcoords="offset points", ha="left" if value >= 0 else "right", va="center", fontsize=9)
    ax.margins(x=.35)
    fig.suptitle(f"SSI · HLS Burn Scar\n{grid} × {grid} cells · {baseline} baseline · fixed GT-region burn logit",
                 fontsize=17, fontweight="medium")
    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=ROOT/"assets/samples/hls_sample.npz")
    parser.add_argument("--weights", type=Path, default=ROOT/"assets/checkpoints/hls_unet.pt")
    parser.add_argument("--output", type=Path, default=ROOT/"outputs/hls_demo")
    parser.add_argument("--grid", type=int, default=8, help="Cells per spatial side (128 px / 8 = 16 px per cell)")
    parser.add_argument("--baseline", choices=["mean", "zero"], default="mean")
    parser.add_argument("--method", choices=["auto", "exact", "permutation"], default="auto")
    parser.add_argument("--permutations", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads")
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be positive")
    torch.set_num_threads(args.threads)
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device)
    if device.type == "cuda" and not torch.cuda.is_available(): parser.error("CUDA is not available")
    if device.type == "mps" and not torch.backends.mps.is_available(): parser.error("MPS is not available")
    torch.manual_seed(args.seed)
    image, mask, x = load_sample(args.sample)
    model = load_model(args.weights, device)
    vf = HLSValueFunction(model, x, mask, grid=args.grid, baseline=args.baseline,
                          batch_size=args.batch_size, device=device)
    with torch.inference_mode():
        logits = model(torch.as_tensor(x, device=device)[None])
        prediction = logits.argmax(1)[0].cpu().numpy().astype(np.uint8)
        burn_probability = float(logits.softmax(1)[0, 1][torch.as_tensor(mask == 1, device=device)].mean().cpu())
    valid = mask != 255
    union = np.sum(((prediction == 1) | (mask == 1)) & valid)
    iou = float(np.sum((prediction == 1) & (mask == 1) & valid) / union)
    print(f"HLS Burn Scar | device={device} | image={image.shape} | grid={args.grid}x{args.grid}", flush=True)
    start = time.perf_counter()
    result = explain(vf, args.grid**2, 6, method=args.method, n_permutations=args.permutations, seed=args.seed)
    elapsed = time.perf_counter() - start
    args.output.mkdir(parents=True, exist_ok=True)
    sample_digest = sha256(args.sample)
    bundled_sample = sample_digest == sha256(ROOT/"assets/samples/hls_sample.npz")
    payload = {
        "sample_sha256":sample_digest, "weights_sha256":sha256(args.weights),
        "model_implementation":"MIT HLS adapter with pinned mateuszbuda convolution blocks",
        "model_source_sha256":sha256(ROOT/"lab/models/hls_unet.py"),
        "image_shape":list(image.shape), "grid":[args.grid,args.grid], "bands":list(BAND_NAMES),
        "target":"mean burn-class logit over the fixed ground-truth burn region",
        "baseline":args.baseline, "baseline_normalized":vf.baseline.cpu().numpy().ravel().tolist(),
        "method":result.method, "n_permutations":result.n_permutations, "seed":args.seed,
        "n_evaluations":result.n_evaluations, "attribution_forward_batches":vf.forward_calls,
        "attribution_seconds":elapsed, "device":str(device), "cpu_threads":args.threads,
        "batch_size":args.batch_size, "full_value":result.full_value,
        "mean_burn_probability_on_gt":burn_probability, "sample_burn_iou":iou,
        "max_local_efficiency_error":result.max_local_efficiency_error,
        "spectral_attribution":dict(zip(BAND_NAMES,result.spectral.tolist())),
        "versions":{"python":platform.python_version(),"numpy":np.__version__,"torch":torch.__version__},
        "scope":("One illustrative training-split sample; not a held-out benchmark or full-paper reproduction."
                 if bundled_sample else
                 "User-supplied sample; split and provenance are not verified by this demo. Not a dataset benchmark.")
    }
    (args.output/"summary.json").write_text(json.dumps(payload, indent=2)+"\n")
    np.savez_compressed(args.output/"attribution.npz", attribution=result.attribution,
                         spatial=result.spatial.reshape(args.grid,args.grid), spectral=result.spectral,
                         position_contrasts=result.position_contrasts, prediction=prediction, mask=mask)
    plot_result(image, mask, prediction, result, args.grid, args.baseline, args.output/"demo_output.png")
    print(f"{result.method} | {result.n_evaluations} scored inputs | {vf.forward_calls} batches | {elapsed:.2f}s")
    print(f"Full GT-region logit: {result.full_value:.6f} | sample burn IoU: {iou:.4f}")
    print(f"Max local-efficiency error: {result.max_local_efficiency_error:.3e}")
    for name, value in zip(BAND_NAMES, result.spectral): print(f"  {name:6s} {value:+.6f}")
    print(f"Saved figure, arrays and metadata to {args.output}")


if __name__ == "__main__":
    main()
