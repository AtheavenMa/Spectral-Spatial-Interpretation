"""Measure real CPU cost for the registered playground models.

The script runs a short ramp and skips a larger setting when the previous
setting for that model already took longer than --skip-after seconds.
It prints one JSON object. It does not estimate unrun settings.
"""
from __future__ import annotations

import argparse
import json
import platform
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch

from lab.engine import catalog, run


RAMP = {
    "hls-unet": [(4, 1), (8, 1), (8, 10), (16, 1), (16, 10)],
    "cub-200": [(4, 1), (8, 1), (8, 4), (8, 10), (16, 1)],
    "eurosat": [(4, 1), (8, 1), (8, 3), (8, 10), (16, 1)],
    "paviau": [(4, 1), (4, 3), (8, 1), (8, 3)],
    "salinas": [(4, 1), (4, 3), (8, 1), (8, 3)],
    "whu-hi-longkou": [(4, 1), (4, 3), (8, 1), (8, 3)],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-after", type=float, default=25.0)
    args = parser.parse_args()
    rows = []
    cold = {}
    for model in catalog()["models"]:
        plan = RAMP[model["id"]]
        previous = 0.0
        for grid, permutations in plan:
            cap = int(model["compute"]["permutation_cap"][str(grid)])
            if permutations > cap:
                rows.append({
                    "model_id": model["id"], "grid": grid, "permutations": permutations,
                    "status": "blocked", "reason": f"catalog cap is {cap}",
                })
                continue
            if previous > args.skip_after:
                rows.append({
                    "model_id": model["id"], "grid": grid, "permutations": permutations,
                    "status": "skipped",
                    "reason": f"previous measured run took {previous:.1f}s",
                })
                continue
            started = time.perf_counter()
            result = run(
                model["id"], model["samples"][0]["id"], grid, "mean",
                "permutation", permutations, 0,
            )
            elapsed = time.perf_counter() - started
            previous = elapsed
            if model["id"] not in cold:
                cold[model["id"]] = elapsed
            rows.append({
                "model_id": model["id"], "grid": grid, "permutations": permutations,
                "status": "measured", "seconds": round(elapsed, 3),
                "channels": len(result["channels"]),
                "n_evaluations": result["n_evaluations"],
                "local_efficiency_error": result["local_efficiency_error"],
            })
            print(json.dumps(rows[-1]), flush=True)
    rows_note = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({
        "machine": platform.platform(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "threads": torch.get_num_threads(),
        "max_rss_kb": rows_note,
        "cold_includes_checkpoint_load": cold,
        "rows": rows,
    }, indent=2))


if __name__ == "__main__":
    main()
