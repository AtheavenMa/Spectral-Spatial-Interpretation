"""High-resolution, Atlas-format visualization for numerical SSI results.

The image and all channel thumbnails are actual model input displays with
transparent, bicubically interpolated SSI on top. The exported attribution
numbers are not smoothed or changed. Segmentation contours use the fixed GT
region, never a model prediction. No fictitious localization boxes.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image


RED = np.array([189, 67, 74], dtype=np.float32) / 255
BLUE = np.array([48, 113, 159], dtype=np.float32) / 255


def rgba_overlay(grid: np.ndarray, width: int, height: int, scale: float) -> np.ndarray:
    """Use Pillow float-image bicubic interpolation only for a display overlay."""
    if grid.ndim != 2:
        raise ValueError("Expected a 2D grid of signed attribution values.")
    scalar = Image.fromarray(np.asarray(grid, dtype=np.float32), mode="F")
    smooth = np.asarray(scalar.resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32)
    t = np.clip(np.abs(smooth) / max(float(scale), 1e-12), 0, 1)
    rgba = np.empty((height, width, 4), dtype=np.float32)
    rgba[..., :3] = np.where(smooth[..., None] >= 0, RED, BLUE)
    rgba[..., 3] = 0.80 * (t ** 0.84)
    rgba[..., 3] = np.where(t < 0.015, 0, rgba[..., 3])
    return rgba


def _outline(ax, roi: np.ndarray | None):
    if roi is None or not roi.any():
        return
    data = roi.astype(np.float32)
    # A double outline matches the Visual Atlas's gold/ink region boundary.
    ax.contour(data, levels=[.5], colors=["#1c2b32"], linewidths=[2.3], origin="upper")
    ax.contour(data, levels=[.5], colors=["#f6dfa0"], linewidths=[1.05], origin="upper")


def _target_view(sample):
    h, w = sample.image.shape[:2]
    if sample.roi is None:
        return sample.image
    image = np.empty((h, w, 3), dtype=np.uint8)
    image[:] = (246, 247, 246)
    image[sample.roi] = (188, 65, 74)
    if sample.labels is not None:
        image[np.asarray(sample.labels) == 255] = (195, 200, 204)
    return image


def _label(name: str) -> str:
    if len(name) <= 26:
        return name
    return name[:23] + "…"


def draw_atlas(
    sample, attribution: np.ndarray, spatial: np.ndarray,
    spectral: np.ndarray, output: str | Path, *, display_channels: int = 10,
) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    output = Path(output)
    h, w = sample.image.shape[:2]
    channels = len(sample.bands)
    if attribution.shape != (*spatial.shape, channels) or len(spectral) != channels:
        raise ValueError("Attribution and spatial/spectral dimensions do not match.")
    if not np.all(np.isfinite(attribution)) or not np.all(np.isfinite(spatial)):
        raise ValueError("Attributions must be finite.")

    if channels <= display_channels:
        selected = list(range(channels))
    else:
        selected = sorted(range(channels), key=lambda i: (-abs(float(spectral[i])), i))[:display_channels]
    count = len(selected)
    max_spatial = max(float(np.abs(spatial).max()), 1e-12)
    max_channel = max(float(np.abs(attribution).max()), 1e-12)

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 15,
        "axes.titleweight": "medium",
        "savefig.facecolor": "white",
    })
    fig = plt.figure(figsize=(17.5, 11.5), layout="constrained", facecolor="white")
    outer = fig.add_gridspec(3, 1, height_ratios=[3.2, 2.3, 1.5], hspace=.04)
    upper = outer[0].subgridspec(1, 3, wspace=.06)

    names = ("(a) Image", "(b) Ground Truth", "(c) Spatial SSI")
    for j in range(3):
        ax = fig.add_subplot(upper[0, j])
        if j == 0:
            ax.imshow(sample.image)
        elif j == 1:
            ax.imshow(_target_view(sample), interpolation="nearest")
            if sample.roi is None:
                ax.text(
                    .03, .94, f"Target class: {_label(sample.target_name)}",
                    transform=ax.transAxes, ha="left", va="top", fontsize=11,
                    bbox={"facecolor": "white", "edgecolor": "#d1d7dc", "boxstyle": "round,pad=.5", "alpha": .94},
                )
        else:
            ax.imshow(sample.image)
            ax.imshow(rgba_overlay(spatial, w, h, max_spatial), interpolation="nearest")
            _outline(ax, sample.roi)
        ax.set_title(names[j], loc="left", pad=11, fontsize=17)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    thumbs = outer[1].subgridspec(1, count, wspace=.06)
    for position, c in enumerate(selected):
        ax = fig.add_subplot(thumbs[0, position])
        ax.imshow(sample.image)
        ax.imshow(rgba_overlay(attribution[:, :, c], w, h, max_channel),
                  interpolation="nearest")
        ax.set_title(_label(sample.bands[c]), fontsize=10 if count >= 9 else 12, loc="center", pad=8)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    ax = fig.add_subplot(outer[2])
    values = spectral[selected]
    indices = np.arange(count)
    bars = ax.bar(indices, values,
                  color=[RED if v >= 0 else BLUE for v in values],
                  width=.55, linewidth=0, zorder=3)
    ax.set_xticks(indices, labels=[_label(sample.bands[c]) for c in selected])
    ax.tick_params(axis="x", labelsize=9 if count >= 9 else 11, length=0, pad=8)
    ax.axhline(0, color="#8697a3", linewidth=1)
    ax.set_yticks([])
    ax.grid(axis="y", alpha=.12)
    for spine in ax.spines.values():
        spine.set_visible(False)
    m = max(float(np.max(np.abs(values))), 1e-12)
    ax.set_ylim(-1.32 * m, 1.38 * m)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, v + (.06*m if v >= 0 else -.07*m),
                f"{v:+.3f}", ha="center", va="bottom" if v >= 0 else "top",
                fontsize=9.3 if count >= 9 else 11)
    ax.set_title("(e) Spectral contributions", loc="left", fontsize=17, pad=12)
    ax.legend(
        handles=[Patch(facecolor=BLUE, label="Negative"),
                 Patch(facecolor=RED, label="Positive")],
        loc="upper right", ncol=2, frameon=False, fontsize=11,
    )
    fig.suptitle(
        f"SSI   /   {sample.family}   /   {sample.target_name}",
        x=.04, y=1.015, ha="left", fontsize=20, color="#1b2937",
    )
    # A compact legend explains that all thumbnails use a shared signed scale.
    fig.text(.51, .32, "(d) Spectral SSI  ·  shared channel scale",
             ha="center", fontsize=12, color="#637481")
    fig.savefig(output, dpi=175, bbox_inches="tight", pad_inches=.2, facecolor="white")
    plt.close(fig)
    return {"indices": [int(i) for i in selected], "channel_limit": max_channel,
            "spatial_limit": max_spatial}
