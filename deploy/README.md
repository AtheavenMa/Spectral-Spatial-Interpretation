# SSI Playground deployment

The repository includes a real CPU-compatible SSI Playground. It serves a minimal HTML interface and JSON API. The default model is the bundled HLS checkpoint and sample. CUB-200, EuroSAT, Pavia University, Salinas and WHU-Hi-LongKou are additional catalog entries under `assets/checkpoints` and `assets/samples`.

## Browser version

[Open the standalone SSI HTML](https://atheavenma.github.io/Spectral-Spatial-Interpretation/playground/), which runs the verified 57 Atlas samples and the bundled HLS example via browser-side ONNX inference. For the six-model or custom checkpoint API, run the Python service below.

## Local

From the repository root:

```bash
python -m pip install -r requirements_lab.txt
uvicorn lab.app:app --host 127.0.0.1 --port 7860
```

Open http://127.0.0.1:7860. The page calls `/api/catalog`, `/api/preview`, and `/api/jobs`. `POST /api/explain` remains for scripts. OpenAPI is at `/docs`. A short tour is in [docs/PLAYGROUND_QUICKSTART.md](../docs/PLAYGROUND_QUICKSTART.md).

## CPU Docker

```bash
docker build -t ssi-playground .
docker run --rm -p 7860:7860 ssi-playground
```

The image listens on port 7860 and does not need a GPU. This repository is not published as a hosted Space.

## API

```bash
curl -s http://127.0.0.1:7860/api/catalog

curl -s -X POST http://127.0.0.1:7860/api/explain \
  -H "Content-Type: application/json" \
  -d '{"model_id":"hls-unet","sample_id":"hls-burn-scar","grid":8,"baseline":"mean","method":"permutation","permutations":10,"seed":0}'
```

The API returns signed `attribution` of shape `[grid][grid][channel]`, `spatial`, `spectral`, computation settings, and a matching CLI reproduction command. The browser visualizes these arrays rather than swapping pre-rendered images.

Model and sample ids are allowlisted. HTTP requests cannot pass filesystem paths or an arbitrary checkpoint. A local command can score one supported architecture from files you already have:

```bash
python -m lab.cli explain --model-id cub-200 --sample-id cub-0158 --grid 4 --permutations 1 --seed 0
```

## Testing

```bash
python -m pip install -r requirements_lab_test.txt
python -m unittest discover -s tests -v
node --check lab/static/app.js
```

The integration tests exercise actual CPU inference on the included checkpoint and input; they verify preview dimensions, API validation, attribution shapes, aggregation consistency, and local efficiency.

To inspect the actual HTML in a local Chromium session while the API is running:

```bash
python -m pip install "playwright>=1.54,<2"
python -m playwright install chromium
python lab/browser_smoke.py
```

The browser test changes grid size, switches bands, clicks a spatial cell, checks real images, verifies mobile overflow, and writes desktop/mobile screenshots to the system temporary directory. The GitHub Actions workflow performs these checks and uploads the screenshots as run artifacts.

## Notes

A single compute lock limits concurrent inference, and the last 24 parameter combinations are cached in process. Grid sizes are 4, 8 and 16. The web UI limits 16 × 16 to permutation sampling with at most 10 permutations, and exact enumeration to 4 × 4 or 8 × 8. A production service with more traffic should add a bounded request queue, metrics, and rate limiting.
