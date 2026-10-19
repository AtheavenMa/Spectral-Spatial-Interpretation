"""Reproduction commands shared by the API and the local CLI."""
from __future__ import annotations


def explain_command(
    model_id: str, sample_id: str, grid: int, baseline: str,
    method: str, permutations: int, seed: int,
) -> str:
    return (
        "python -m lab.cli explain "
        f"--model-id {model_id} --sample-id {sample_id} "
        f"--grid {grid} --baseline {baseline} --method {method} "
        f"--permutations {permutations} --seed {seed}"
    )
