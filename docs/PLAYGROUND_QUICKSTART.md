# Playground quickstart

## Cloud workspace (no local Python environment)

Open [SSI Playground in GitHub Codespaces](https://codespaces.new/AtheavenMa/Spectral-Spatial-Interpretation) and create or resume a codespace. The dev container is configured to install the CPU Python dependencies, start the FastAPI app, and forward **port 7860**. Open the forwarded **SSI Playground** port to interact with the real bundled models.

This uses your own GitHub Codespaces environment and may consume Codespaces quota. The project does **not** have a publicly hosted, always-on web endpoint. No Hugging Face deployment is involved.

## Local Python

From the repository root, with a CPU PyTorch install:

```bash
python -m pip install -r requirements_lab.txt
uvicorn lab.app:app --host 127.0.0.1 --port 7860
```

Open http://127.0.0.1:7860. Pick a model, then Run. The page scores the bundled checkpoint and the one bundled input for that model. It does not display a pre-rendered attribution figure.

The same run from the command line:

```bash
python -m lab.cli explain --model-id cub-200 --sample-id cub-0158 \
  --grid 4 --baseline mean --method permutation --permutations 1 --seed 0
```

`POST /api/explain` accepts the same fields. The page itself starts `POST /api/jobs` and polls so a run can be cancelled.

Docker:

```bash
docker build -t ssi-playground .
docker run --rm -p 7860:7860 ssi-playground
```

Measured timings and the per-model defaults are in [PLAYGROUND_PERFORMANCE.md](PLAYGROUND_PERFORMANCE.md). What was checked is in [PLAYGROUND_VALIDATION.md](PLAYGROUND_VALIDATION.md).
