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
