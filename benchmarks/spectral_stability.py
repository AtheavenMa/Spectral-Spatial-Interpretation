"""Measure how finite channel-permutation sampling changes hyperspectral Top 10.

Uses the actual registered checkpoints and NPZ inputs, a fixed 4x4 grid and
mean baseline. All comparisons are within the *same* model/input/target;
they are sensitivity checks, not a claim of ground-truth feature relevance.

Runs: PaviaU K=1,3,5; Salinas and LongKou K=1,2,3 (their tested caps).
Optionally compare a second seed at K=3.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from lab.engine import run

CASES = {
    "paviau": ("paviau-0008", (1, 3, 5)),
    "salinas": ("salinas-0000", (1, 2, 3)),
    "whu-hi-longkou": ("longkou-0000", (1, 2, 3)),
}


def top_indices(values: np.ndarray, k: int = 10) -> list[int]:
    """Deterministic absolute-score ranking with band index as a tie-break."""
    return sorted(range(len(values)), key=lambda i: (-abs(values[i]), i))[:k]


def compare(a: np.ndarray, b: np.ndarray) -> dict:
    """Comparing full spectral vectors, not averaged display heatmaps."""
    left = set(top_indices(a))
    right = set(top_indices(b))
    common = sorted(left & right)
    n = len(common)
    rank_a = np.argsort(np.argsort(np.abs(a), kind="stable"), kind="stable")
    rank_b = np.argsort(np.argsort(np.abs(b), kind="stable"), kind="stable")
    rank_corr = float(np.corrcoef(rank_a, rank_b)[0, 1])
    return {
        "top10_overlap": n,
        "top10_jaccard": round(n / len(left | right), 4),
        "full_abs_rank_spearman": round(rank_corr, 4),
        "common_top10_sign_agreement": (
            round(sum(np.sign(a[i]) == np.sign(b[i]) for i in common) / n, 4)
            if n else None
        ),
    }


def measure(second_seed: bool = False) -> dict:
    rows = []
    comparisons = []
    for model_id, (sample_id, levels) in CASES.items():
        results = {}
        for k in levels:
            begin = time.perf_counter()
            r = run(model_id, sample_id, 4, "mean", "permutation", k, 0)
            results[(k, 0)] = np.asarray(r["spectral"], dtype=np.float64)
            assert r["local_efficiency_error"] < 1e-5
            rows.append({
                "model": model_id, "grid": 4, "permutations": k, "seed": 0,
                "n_evaluations": r["n_evaluations"], "seconds": round(time.perf_counter() - begin, 3),
                "local_efficiency_error": r["local_efficiency_error"],
                "top10_bands": [i + 1 for i in top_indices(results[(k, 0)])],
            })
            print(json.dumps(rows[-1]), flush=True)
        comparisons.append({
            "model": model_id, "comparison": "K=1 vs K=3, seed=0",
            **compare(results[(1, 0)], results[(3, 0)]),
        })
        if 5 in levels:
            comparisons.append({
                "model": model_id, "comparison": "K=3 vs K=5, seed=0",
                **compare(results[(3, 0)], results[(5, 0)]),
            })
        if second_seed:
            begin = time.perf_counter()
            r = run(model_id, sample_id, 4, "mean", "permutation", 3, 1)
            other = np.asarray(r["spectral"], dtype=np.float64)
            rows.append({
                "model": model_id, "grid": 4, "permutations": 3, "seed": 1,
                "n_evaluations": r["n_evaluations"], "seconds": round(time.perf_counter() - begin, 3),
                "local_efficiency_error": r["local_efficiency_error"],
                "top10_bands": [i + 1 for i in top_indices(other)],
            })
            comparisons.append({
                "model": model_id, "comparison": "K=3, seed=0 vs seed=1",
                **compare(results[(3, 0)], other),
            })
    return {
        "machine": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__, "threads": torch.get_num_threads(),
        "scope": "One real input per model; 4x4, mean baseline, permutation SSI. Exploratory sampling sensitivity.",
        "runs": rows, "comparisons": comparisons,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    p.add_argument("--second-seed", action="store_true")
    args = p.parse_args()
    report = measure(args.second_seed)
    print(json.dumps(report["comparisons"], indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
