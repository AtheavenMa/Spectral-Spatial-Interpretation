"""Local SSI commands for the six registered models and a matching file pair.

Registered runs:

    python -m lab.cli explain --model-id cub-200 --sample-id cub-0158 --grid 4 \\
        --baseline mean --method permutation --permutations 1 --seed 0

A checkpoint is accepted only when its tensors match one supported architecture.
An unknown network, or an input whose channel count does not match, fails before scoring.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from lab.engine import run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lab.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    explain = sub.add_parser("explain", help="Score one registered model and input")
    explain.add_argument("--model-id", required=True)
    explain.add_argument("--sample-id", required=True)
    explain.add_argument("--grid", type=int, default=4)
    explain.add_argument("--baseline", default="mean", choices=("mean", "zero"))
    explain.add_argument("--method", default="permutation", choices=("auto", "permutation", "exact"))
    explain.add_argument("--permutations", type=int, default=1)
    explain.add_argument("--seed", type=int, default=0)

    files = sub.add_parser("explain-files", help="Score a supported checkpoint with a matching NPZ")
    files.add_argument("--family", required=True, choices=(
        "cub-200", "eurosat", "paviau", "salinas", "whu-hi-longkou",
    ))
    files.add_argument("--checkpoint", type=Path, required=True)
    files.add_argument("--sample", type=Path, required=True)
    files.add_argument("--grid", type=int, default=4)
    files.add_argument("--baseline", default="mean", choices=("mean", "zero"))
    files.add_argument("--method", default="permutation", choices=("auto", "permutation", "exact"))
    files.add_argument("--permutations", type=int, default=1)
    files.add_argument("--seed", type=int, default=0)
    return parser


def explain_files(family: str, checkpoint: Path, sample: Path, grid: int, baseline: str,
                  method: str, permutations: int, seed: int) -> dict:
    from lab.adapters.extra import SPECS, _Value, _load_model
    from lab.runtime import wrap_value
    from ssi import explain as explain_ssi

    if family not in SPECS:
        raise ValueError(f"Unsupported architecture family {family!r}.")
    spec = dict(SPECS[family])
    spec["checkpoint"] = Path(checkpoint)
    if not spec["checkpoint"].is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")
    if not Path(sample).is_file():
        raise FileNotFoundError(f"Sample not found: {sample}")
    try:
        state = torch.load(spec["checkpoint"], map_location="cpu", weights_only=True)
    except Exception as exc:
        raise ValueError(f"Checkpoint is not a tensor-only state dict: {exc}") from exc
    if not isinstance(state, dict) or not state:
        raise ValueError("Checkpoint is not a tensor-only state dict.")
    with np.load(sample, allow_pickle=False) as data:
        required = ("x", "label", "mean", "std", "target_class")
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError("Sample NPZ is missing " + ", ".join(missing) + ".")
        x = data["x"].astype(np.float32)
        label = data["label"].astype(np.int64)
        mean = data["mean"].astype(np.float32)
        std = data["std"].astype(np.float32)
        target_class = int(data["target_class"])
    if x.ndim != 3 or x.shape[0] != spec["in_channels"] or not np.isfinite(x).all():
        raise ValueError(
            f"{family} expects a finite input shaped ({spec['in_channels']}, H, W), got {tuple(x.shape)}."
        )
    if mean.shape != (spec["in_channels"],) or std.shape != (spec["in_channels"],):
        raise ValueError("mean and std must be one value per input channel.")
    try:
        model = _load_model(spec)
    except (RuntimeError, ValueError) as exc:
        raise ValueError(f"Checkpoint does not match the {family} architecture: {exc}") from exc
    value = _Value(model, x, spec, label, mean, std, target_class, grid, baseline)
    result = explain_ssi(
        wrap_value(value), n_cells=grid * grid, n_channels=value.channels,
        method=method, n_permutations=permutations, seed=seed,
    )
    return {
        "family": family,
        "grid": grid,
        "baseline": baseline,
        "method": result.method,
        "spectral": result.spectral.tolist(),
        "full_value": result.full_value,
        "n_evaluations": result.n_evaluations,
        "local_efficiency_error": result.max_local_efficiency_error,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "explain":
        payload = run(
            args.model_id, args.sample_id, args.grid, args.baseline,
            args.method, args.permutations, args.seed,
        )
        print(json.dumps({
            "model_id": payload["model_id"],
            "sample_id": payload["sample_id"],
            "spectral": payload["spectral"],
            "full_value": payload["full_value"],
            "n_evaluations": payload["n_evaluations"],
            "local_efficiency_error": payload["local_efficiency_error"],
            "command": payload["command"],
        }))
        return 0
    payload = explain_files(
        args.family, args.checkpoint, args.sample, args.grid, args.baseline,
        args.method, args.permutations, args.seed,
    )
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
