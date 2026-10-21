# SSI in Five Minutes

The seven-slide interactive browser tutorial at [`index.html`](index.html) follows the presentation pattern used by [SAR](https://github.com/OpenSAE/SAE-Behavioral-Compositionality) and [RSS](https://github.com/OpenSAE/Redistribution-Sensitivity-Score): fixed 1920×1080 stage, alternating dark and light sections, keyboard navigation and slide details.

## Preview locally

From the repository root:

```bash
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000/`. Use arrow keys, digits 1–7, `D` for details and `?` for help. The tutorial can be hosted as a static site; it needs no backend, GPU or model download.

## Data and scientific scope

- `assets/ssi-tour/result.json` is an unmodified copy of `assets/video/hls_burnscar_0163/result.json`.
- The tutorial uses the real 16×16×6 SSI attribution tensor, mean baseline, five sampled permutations, seed 0 and HLS Burn Scars sample_0163.
- The five permutation orders are reproduced from the browser runtime's seeded xorshift32/Fisher–Yates sampler in row-major cell order.
- Local masked scores follow the exact within-cell aggregation identity; the interactive restoration paths form a consistent illustrative coalition game whose five-order averages match the stored SSI attribution values.
- The input, ground-truth target mask and spatial overlay are copied unchanged from the recorded video-evidence assets.
- The final-slide comparison numbers come from the paper's mean-baseline Table 1, not from sample_0163. The single sample is illustrative.

## Live pages

- [5-minute tutorial](https://atheavenma.github.io/Spectral-Spatial-Interpretation/)
- [SSI Playground](https://atheavenma.github.io/Spectral-Spatial-Interpretation/playground/)

Both pages are published from the SSI repository's `docs/` folder using GitHub Pages. Run `python -m http.server 8000 --directory docs` for local browsing.
