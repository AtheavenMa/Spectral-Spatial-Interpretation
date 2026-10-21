# Repository structure

SSI separates its small mathematical core from model adapters, reproducible model assets, and two browser applications.

| Path | Purpose |
| --- | --- |
| `ssi.py` | Standalone NumPy implementation of the observed-context SSI game |
| `demo.py` | Direct, offline HLS demonstration (`python demo.py`) |
| `lab/models/` | Verified HLS U-Net and ResNet-18 architectures |
| `lab/adapters/` | Dataset-specific preprocessing, model scoring and provenance |
| `lab/app.py`, `lab/cli.py` | FastAPI service and local commands |
| `lab/atlas_api.py`, `lab/atlas_plot.py` | Reproducible Atlas PNG, JSON and NPZ exports |
| `lab/static/` | Python service frontend |
| `docs/` | GitHub Pages tutorial and browser-only SSI Playground |
| `docs/playground/assets/` | Browser-runtime ONNX files and the validated inputs for 57 Atlas samples |
| `assets/checkpoints/` | Original PyTorch weights and HLS checkpoint metadata |
| `assets/samples/` | Original inputs, targets and sample provenance |
| `assets/metadata/` | Model and sample integrity manifest |
| `assets/video/` | Complete video and original production assets (preserved) |
| `examples/` | Original 57-image Visual Atlas |
| `tests/fixtures/` | Golden numerical outputs and regression fixtures |
| `tools/` | Export, browser verification and synchronization scripts |
| `benchmarks/` | CPU and spectral-stability measurements |
| `work_plan/` | Completed historical implementation plans |
| `third_party/`, `LICENSES/` | Unchanged vendored source and its license |

Run tests from the repository root using `python -m unittest discover -s tests -v`. Run the full six-model browser and Docker checks through GitHub Actions.

The two browser frontends have distinct deployment roots. `docs/playground/atlas-render.js` is the canonical renderer; `lab/static/atlas-render.js` is its deployment copy. Run `python tools/sync_atlas_renderer.py` after changing the renderer, or `python tools/sync_atlas_renderer.py --check` to verify byte-for-byte parity.

GitHub Pages must serve `docs/playground/assets/` as published. Moving these files outside `docs/` would break client-side inference. PyTorch checkpoints are intentionally separate from the exported ONNX models because Python and browser execution need different formats.

`docs/playground/57_sources.template.json` is a re-import template; `docs/playground/compute-manifest.json` is the authoritative published sample/model registry. The historical work plans are not live system state.
