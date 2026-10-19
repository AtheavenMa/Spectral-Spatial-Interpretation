# SSI Playground deployment

The repository includes a real CPU-compatible SSI Playground. It serves a minimal HTML interface and JSON API using the bundled HLS checkpoint and HLS sample.

## Local

From the repository root:

```bash
python -m pip install -r requirements_lab.txt
uvicorn lab.app:app --host 127.0.0.1 --port 7860
```

Open http://127.0.0.1:7860. The frontend calls `/api/catalog`, `/api/preview`, and `/api/explain`. FastAPI also publishes its OpenAPI schema at `/openapi.json` and interactive API reference at `/docs`.

## CPU Docker

```bash
docker build -t ssi-playground .
docker run --rm -p 7860:7860 ssi-playground
```

For Hugging Face Spaces, create a **Docker** Space with the files from this repository and set `app_port: 7860` in the Space README metadata. The Dockerfile already starts the server on port 7860. No GPU is required by the bundled HLS example. Public deployment needs account/Space write permission and should happen separately from committing source files.

## API

```bash
curl -s http://127.0.0.1:7860/api/catalog

curl -s -X POST http://127.0.0.1:7860/api/explain \
  -H "Content-Type: application/json" \
  -d '{"model_id":"hls-unet","sample_id":"hls-burn-scar","grid":8,"baseline":"mean","method":"permutation","permutations":10,"seed":0}'
```

The API returns signed `attribution` of shape `[grid][grid][channel]`, `spatial`, `spectral`, computation settings, and a matching CLI reproduction command. The browser visualizes these arrays rather than swapping pre-rendered images.

Only the bundled model and sample are registered initially. Model identifiers and sample identifiers are allowlisted; the server does not execute arbitrary uploaded checkpoints or accept filesystem paths from HTTP requests. Extend model choices by implementing a validated adapter and adding corresponding metadata. Future model/input placeholders are tracked in [work_plan/01_ssi_playground.md](../work_plan/01_ssi_playground.md).

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
