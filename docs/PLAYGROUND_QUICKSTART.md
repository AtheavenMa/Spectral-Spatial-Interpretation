# Playground quickstart

## Play directly in HTML

[**Open the browser SSI Playground ↗**](https://atheavenma.github.io/Spectral-Spatial-Interpretation/playground/)

The static page has six verified ONNX model families and 57 registered Atlas samples, plus a separate bundled HLS example. Each ready sample uses its original input tensor and target, and SSI is recomputed in the browser when the settings change. The Python API for six model families is below.

## Local Python

From the repository root, with a CPU PyTorch install:

```bash
python -m pip install -r requirements.txt
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
