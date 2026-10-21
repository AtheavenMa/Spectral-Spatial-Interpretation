"""Spectral-Spatial Interpretation: Shapley allocation in observed-context games.

The only external dependency is NumPy. ``value_fn`` scores batches of Boolean
coalitions shaped (batch, cells, channels); True keeps an observed player and
False replaces it with the chosen baseline. All non-target cells stay observed.
"""
from dataclasses import dataclass
from math import comb
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class SSIResult:
    """Cell/channel scores and the quantities needed to check local efficiency."""

    attribution: np.ndarray                  # (cells, channels), signed
    position_contrasts: np.ndarray           # full input minus one masked cell
    full_value: float
    n_evaluations: int                       # scored inputs, not batch calls
    method: str
    n_permutations: int | None

    @property
    def spatial(self) -> np.ndarray:
        return self.attribution.sum(axis=1)

    @property
    def spectral(self) -> np.ndarray:
        return self.attribution.sum(axis=0)

    @property
    def max_local_efficiency_error(self) -> float:
        return float(np.max(np.abs(self.spatial - self.position_contrasts)))


def explain(
    value_fn: Callable[[np.ndarray], np.ndarray],
    n_cells: int,
    n_channels: int,
    *,
    method: str = "auto",
    n_permutations: int = 10,
    seed: int = 0,
) -> SSIResult:
    """Explain every cell/channel pair while fixing all surrounding cells.

    ``value_fn(masks)`` must return one finite scalar per input coalition. Use
    the same target, baseline, and (for segmentation) fixed region for every
    call. The function must be deterministic; evaluate neural models in eval
    mode. Scores need not be probabilities or centered at the empty input.

    ``auto`` enumerates 2**C subsets for C <= 3 and samples channel permutations
    otherwise. ``exact`` enumerates all subsets (limited to C <= 16);
    ``permutation`` always uses ``n_permutations`` channel orderings per cell.
    Complete permutation paths preserve local efficiency even at finite K.
    A local NumPy generator controls sampling without changing global RNG state.

    The output is (cells, channels). Its row sums equal the full-context cell
    contrasts, but the sum over all cells need not equal a global input contrast.
    ``n_evaluations`` counts unique states within each cell, sharing the full
    input across cells. The model adapter may split these into several batches.
    """
    for name, count in (("n_cells", n_cells), ("n_channels", n_channels),
                        ("n_permutations", n_permutations)):
        if isinstance(count, (bool, np.bool_)) or not isinstance(count, (int, np.integer)) or count < 1:
            raise ValueError(f"{name} must be a positive integer")
    if method not in ("auto", "exact", "permutation"):
        raise ValueError("method must be 'auto', 'exact', or 'permutation'")
    resolved = ("exact" if n_channels <= 3 else "permutation") if method == "auto" else method
    if resolved == "exact" and n_channels > 16:
        raise ValueError("Exact enumeration is limited to 16 channels; use permutation sampling")
    rng = np.random.default_rng(seed)
    evaluated = 0

    def score(masks):
        nonlocal evaluated
        values = np.asarray(value_fn(masks), dtype=np.float64)
        if values.shape != (len(masks),):
            raise ValueError(f"value_fn must return shape ({len(masks)},), got {values.shape}")
        if not np.isfinite(values).all():
            raise ValueError("value_fn returned a non-finite score")
        evaluated += len(masks)
        return values

    full = float(score(np.ones((1, n_cells, n_channels), dtype=bool))[0])
    phi = np.zeros((n_cells, n_channels), dtype=np.float64)
    contrasts = np.zeros(n_cells, dtype=np.float64)
    for g in range(n_cells):
        if resolved == "exact":
            indices = np.arange(1 << n_channels)
            states = ((indices[:, None] >> np.arange(n_channels)) & 1).astype(bool)
        else:
            orders = np.asarray([rng.permutation(n_channels) for _ in range(n_permutations)])
            paths = np.zeros((n_permutations, n_channels + 1, n_channels), dtype=bool)
            for k, order in enumerate(orders):
                for j, c in enumerate(order):
                    paths[k, j + 1] = paths[k, j]
                    paths[k, j + 1, c] = True
            states, inverse = np.unique(paths.reshape(-1, n_channels), axis=0, return_inverse=True)
        is_full = states.all(axis=1)
        coalitions = np.ones((int((~is_full).sum()), n_cells, n_channels), dtype=bool)
        coalitions[:, g, :] = states[~is_full]
        values = np.empty(len(states), dtype=np.float64)
        values[is_full] = full
        values[~is_full] = score(coalitions)
        contrasts[g] = full - float(values[~states.any(axis=1)][0])
        if resolved == "exact":
            for c in range(n_channels):
                absent = indices[~states[:, c]]
                sizes = states[absent].sum(axis=1)
                weights = np.asarray([1.0 / (n_channels * comb(n_channels - 1, int(s))) for s in sizes])
                phi[g, c] = weights @ (values[absent | (1 << c)] - values[absent])
        else:
            path_values = values[inverse].reshape(n_permutations, n_channels + 1)
            marginals = np.diff(path_values, axis=1)
            for k, order in enumerate(orders):
                phi[g, order] += marginals[k] / n_permutations
    return SSIResult(phi, contrasts, full, evaluated, resolved,
                     n_permutations if resolved == "permutation" else None)


@dataclass(frozen=True)
class ImageSSIResult:
    """Image-grid SSI scores. Spatial cell size is measured in input pixels."""

    attribution: np.ndarray       # (grid_rows, grid_cols, channels)
    position_contrasts: np.ndarray  # (grid_rows, grid_cols)
    full_value: float
    n_evaluations: int
    image_size: tuple[int, int]
    grid_size: tuple[int, int]

    @property
    def spatial(self) -> np.ndarray:
        return self.attribution.sum(axis=-1)

    @property
    def spectral(self) -> np.ndarray:
        return self.attribution.sum(axis=(0, 1))

    @property
    def max_local_efficiency_error(self) -> float:
        return float(np.max(np.abs(self.spatial - self.position_contrasts)))


def _pixels(value, name: str) -> tuple[int, int]:
    """Accept square pixel sizes or explicit (height, width), never grid counts."""
    if isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_)):
        value = (int(value), int(value))
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(isinstance(v, (bool, np.bool_)) or
                   not isinstance(v, (int, np.integer)) or v <= 0 for v in value)):
        raise ValueError(f"{name} must be a positive pixel count or (height, width)")
    return int(value[0]), int(value[1])


class SSI:
    """Explain one image with a PyTorch model and a per-channel dataset baseline.

    input: CHW or HWC tensor/array, or a PIL image. Integer images are scaled
    to [0, 1]; floating-point tensors must already be model-ready.
    image_size: resized input (height, width) in pixels, or None to keep size.
    grid_size: pixels per cell, NOT the number of cells per side.
    baseline: required channel vector in the same space as the model input.
    target: fixed class index, or callable mapping model outputs to B scores.
    target_mask: fixed HxW region for segmentation with an integer target.

    The original model's preprocessing is not guessed or reconstructed.
    """

    def __init__(
        self, model, input, *, target, baseline,
        image_size=None, grid_size=16, permutations=5, seed=0,
        batch_size=8, target_mask=None,
    ):
        try:
            import torch
            import torch.nn.functional as F
        except ImportError as exc:
            raise ImportError("Image SSI requires PyTorch: install spectral-spatial-interpretation[torch]") from exc

        if not isinstance(model, torch.nn.Module):
            raise TypeError("model must be a torch.nn.Module")
        if isinstance(baseline, str):
            raise TypeError("baseline must be a numeric dataset-level vector, not 'mean' or 'zero'")
        try:
            channel_baseline = torch.as_tensor(baseline, dtype=torch.float32)
        except (TypeError, ValueError, RuntimeError) as exc:
            raise ValueError("baseline must be a finite numeric channel vector") from exc
        if channel_baseline.ndim != 1 or channel_baseline.numel() == 0 or not torch.isfinite(channel_baseline).all():
            raise ValueError("baseline must be a nonempty finite vector of shape (channels,)")

        raw = torch.as_tensor(np.asarray(input) if not isinstance(input, torch.Tensor) else input)
        if raw.ndim == 4 and raw.shape[0] == 1:
            raw = raw[0]
        if raw.ndim != 3:
            raise ValueError("input must be one CHW/HWC image, optionally with a leading batch dimension of 1")
        channels = int(channel_baseline.numel())
        if raw.shape[0] == channels and raw.shape[-1] == channels:
            raise ValueError("Ambiguous channel dimension: provide a CHW image with distinguishable dimensions")
        if raw.shape[0] == channels:
            pass
        elif raw.shape[-1] == channels:
            raw = raw.permute(2, 0, 1)
        else:
            raise ValueError(f"input must have {channels} channels matching baseline")
        if raw.is_complex():
            raise ValueError("input must be real-valued")
        if raw.dtype == torch.uint8:
            raw = raw.float().div(255)
        else:
            raw = raw.float()
        if not torch.isfinite(raw).all():
            raise ValueError("input must contain finite pixel values")

        original_size = (int(raw.shape[1]), int(raw.shape[2]))
        size = original_size if image_size is None else _pixels(image_size, "image_size")
        cell_size = _pixels(grid_size, "grid_size")
        if size[0] % cell_size[0] or size[1] % cell_size[1]:
            raise ValueError("image_size must be divisible by grid_size along both axes")
        self.grid_shape = (size[0] // cell_size[0], size[1] // cell_size[1])
        if self.grid_shape[0] * self.grid_shape[1] > 4096:
            raise ValueError("More than 4096 cells: increase grid_size to bound inference cost")
        if image_size is not None and size != original_size:
            raw = F.interpolate(raw.unsqueeze(0), size=size, mode="bilinear", align_corners=False)[0]

        if not (isinstance(target, (int, np.integer)) and not isinstance(target, (bool, np.bool_))
                and target >= 0) and not callable(target):
            raise ValueError("target must be a nonnegative class index or a callable scoring function")
        for name, value in (("permutations", permutations), ("batch_size", batch_size)):
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)) or seed < 0:
            raise ValueError("seed must be a nonnegative integer")

        mask = None
        if target_mask is not None:
            mask = torch.as_tensor(np.asarray(target_mask) if not isinstance(target_mask, torch.Tensor)
                                   else target_mask)
            if mask.ndim != 2 or tuple(mask.shape) not in (original_size, size):
                raise ValueError("target_mask must have the original or resized image HxW shape")
            mask = mask.to(torch.float32)[None, None]
            if tuple(mask.shape[-2:]) != size:
                mask = F.interpolate(mask, size=size, mode="nearest")
            mask = mask[0, 0] != 0
            if not mask.any():
                raise ValueError("target_mask must include at least one pixel")
        if callable(target) and mask is not None:
            raise ValueError("With callable target, handle any fixed region in the callable itself")

        self.model = model
        self.input = raw.detach()
        self.target = target
        self.baseline = channel_baseline.detach()
        self.target_mask = mask
        self.image_size = size
        self.grid_size = cell_size
        self.permutations = int(permutations)
        self.seed = int(seed)
        self.batch_size = int(batch_size)

    def explain(self) -> ImageSSIResult:
        """Run batched masking; output one signed attribution per cell and channel."""
        import torch
        import torch.nn.functional as F

        device = next((p.device for p in self.model.parameters()),
                      next((b.device for b in self.model.buffers()), torch.device("cpu")))
        x = self.input.to(device)
        baseline = self.baseline.to(device).reshape(1, -1, 1, 1)
        mask = self.target_mask.to(device) if self.target_mask is not None else None
        rows, cols = self.grid_shape
        cell_h, cell_w = self.grid_size
        channels = x.shape[0]

        def score(masks: np.ndarray) -> np.ndarray:
            result = []
            for start in range(0, len(masks), self.batch_size):
                subset = masks[start:start + self.batch_size]
                n = len(subset)
                keep = torch.as_tensor(subset, device=device).reshape(n, rows, cols, channels)
                keep = keep.permute(0, 3, 1, 2).repeat_interleave(cell_h, 2).repeat_interleave(cell_w, 3)
                logits = self.model(torch.where(keep, x[None], baseline))
                if callable(self.target):
                    selected = self.target(logits)
                elif not isinstance(logits, torch.Tensor):
                    raise TypeError("model must return a tensor of logits or supply a callable target")
                elif logits.ndim == 2:
                    if mask is not None:
                        raise ValueError("target_mask is only valid for spatial model outputs")
                    if self.target >= logits.shape[1]:
                        raise ValueError("target class is outside the model output")
                    selected = logits[:, self.target]
                elif logits.ndim == 4:
                    if mask is None:
                        raise ValueError("segmentation logits require a fixed target_mask")
                    if self.target >= logits.shape[1]:
                        raise ValueError("target class is outside the model output")
                    roi = mask
                    if tuple(roi.shape) != tuple(logits.shape[-2:]):
                        roi = F.interpolate(roi[None, None].float(),
                                            size=logits.shape[-2:], mode="nearest")[0, 0] > 0
                    if not roi.any():
                        raise ValueError("target_mask becomes empty at the model output resolution")
                    selected = logits[:, self.target, :, :][:, roi].mean(dim=1)
                else:
                    raise ValueError("model output must have shape (B, classes) or (B, classes, H, W)")
                if not isinstance(selected, torch.Tensor) or selected.shape != (n,):
                    raise ValueError("target must produce exactly one scalar per input (shape B,)")
                result.append(selected.detach().to("cpu", dtype=torch.float64).numpy())
            return np.concatenate(result)

        was_training = self.model.training
        self.model.eval()
        try:
            with torch.inference_mode():
                values = explain(score, rows * cols, int(channels),
                                 method="auto", n_permutations=self.permutations,
                                 seed=self.seed)
        finally:
            self.model.train(was_training)
        return ImageSSIResult(
            attribution=values.attribution.reshape(rows, cols, channels),
            position_contrasts=values.position_contrasts.reshape(rows, cols),
            full_value=values.full_value,
            n_evaluations=values.n_evaluations,
            image_size=self.image_size,
            grid_size=self.grid_size,
        )
