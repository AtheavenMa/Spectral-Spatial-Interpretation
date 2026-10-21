"""Exact two-cell SSI toy example, using only NumPy."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from ssi import explain


def score(masks):
    return (
        2 * masks[:, 0, 0]
        + 4 * masks[:, 0, 1]
        + 6 * (masks[:, 0, 0] & masks[:, 0, 1])
        + 8 * (masks[:, 0, 0] & masks[:, 1, 0])
    )


def main():
    result = explain(score, n_cells=2, n_channels=2)
    np.testing.assert_allclose(result.attribution, [[13., 7.], [8., 0.]])
    np.testing.assert_allclose(result.spatial, result.position_contrasts)
    print(result.attribution)
    print("Spatial:", result.spatial)
    print("Cell contrasts:", result.position_contrasts)


if __name__ == "__main__":
    main()
