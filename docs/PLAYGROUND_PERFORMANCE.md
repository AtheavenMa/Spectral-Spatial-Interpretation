# Playground CPU timings

Measured with `python benchmarks/playground_cpu.py --skip-after 25` on this machine:

- Linux 6.8.0-139-generic, x86_64
- Python 3.12.14
- PyTorch 2.11.0+cu128, running on CPU with 4 threads
- Peak RSS for the **entire multi-model benchmark process**: 811328 KB (about 792 MiB). This is **not** per-model peak memory, and model caches remain loaded between cases.

Times below are wall clock for `lab.engine.run`, including the first checkpoint load for each model. Later rows for the same model reuse the loaded weights. Every measured row finished with local efficiency under `1e-12`. Nothing in this table is an estimate.

| Model | Grid | Permutations | Seconds | Evaluations |
|---|---:|---:|---:|---:|
| hls-unet | 4 | 1 | 0.122 | 97 |
| hls-unet | 8 | 1 | 0.345 | 385 |
| hls-unet | 8 | 10 | 2.216 | 2152 |
| hls-unet | 16 | 1 | 1.371 | 1537 |
| hls-unet | 16 | 10 | 8.877 | 8701 |
| cub-200 | 4 | 1 | 1.356 | 49 |
| cub-200 | 8 | 1 | 4.983 | 193 |
| cub-200 | 8 | 4 | 8.905 | 364 |
| cub-200 | 8 | 10 | 11.089 | 444 |
| cub-200 | 16 | 1 | 20.197 | 769 |
| eurosat | 4 | 1 | 1.235 | 209 |
| eurosat | 8 | 1 | 4.770 | 833 |
| eurosat | 8 | 3 | 13.161 | 2336 |
| eurosat | 8 | 10 | 51.569 | 7263 |
| eurosat | 16 | 1 | 19.859 | 3329 |
| paviau | 4 | 1 | 2.461 | 1649 |
| paviau | 4 | 3 | 5.194 | 4911 |
| paviau | 8 | 1 | 6.331 | 6593 |
| paviau | 8 | 3 | 18.543 | 19644 |
| salinas | 4 | 1 | 3.842 | 3265 |
| salinas | 4 | 3 | 11.785 | 9761 |
| salinas | 8 | 1 | 15.646 | 13057 |
| salinas | 8 | 3 | 46.463 | 39038 |
| whu-hi-longkou | 4 | 1 | 5.815 | 4321 |
| whu-hi-longkou | 4 | 3 | 18.567 | 12929 |
| whu-hi-longkou | 8 | 1 | 23.812 | 17281 |
| whu-hi-longkou | 8 | 3 | 72.879 | 51712 |

EuroSAT 16×16 / 1 was skipped inside the ramp because the previous EuroSAT setting took 51.6 s. It was then measured on its own: 19.859 s, 3329 evaluations. The 8×8 / 10 setting is real, and the catalog no longer offers it.

16×16 was not run for PaviaU, Salinas or WHU-Hi-LongKou. Those models do not list grid 16. The measured 8×8 / 3 runs were already 18.5 s, 46.5 s and 72.9 s, and a 16×16 grid has four times as many cells.

## Defaults the page applies

| Model | Default | Permutation cap |
|---|---|---|
| hls-unet | 8×8, 10 permutations | 4: 20, 8: 20, 16: 10 |
| cub-200 | 8×8, 4 permutations | 4: 20, 8: 10, 16: 1 |
| eurosat | 8×8, 3 permutations | 4: 20, 8: 3, 16: 1 |
| paviau | 4×4, 1 permutation | 4: 8, 8: 3 |
| salinas | 4×4, 1 permutation | 4: 4, 8: 1 |
| whu-hi-longkou | 4×4, 1 permutation | 4: 3, 8: 1 |

Quick presets stay at 4×4 / 1 permutation. Switching models replaces the previous grid and permutation count with that model's default, so an HLS 8×8 / 10 setting is not left on a 270-band model.

## Browser ONNX, static HTML

Measured in headless Chromium with Playwright, `onnxruntime-web` 1.21.0, on the same machine. Each time is wall clock from navigation to a finished grid **4 × 4**, **1 permutation**, mean baseline, seed 0 run, so it includes fetching the ONNX model and the float32 input. Local efficiency was 0 and the unperturbed score matched the Python reference. `heap` is `performance.memory.usedJSHeapSize` after that run, not a peak.

| Sample | Channels | Seconds | Evaluations | Heap after run |
|---|---:|---:|---:|---:|
| hls-bundled | 6 | 0.871 | 97 | 10.4 MB |
| HLS_BurnScars/sample_0045 | 6 | 0.849 | 97 | 14.0 MB |
| CUB_200/sample_0158 | 3 | 16.103 | 49 | 11.0 MB |
| EuroSAT/sample_1294 | 13 | 20.814 | 209 | 10.4 MB |
| PaviaU/sample_0008 | 103 | 29.276 | 1649 | 6.7 MB |
| Salinas/sample_0000 | 204 | 65.855 | 3265 | 55.5 MB |
| WHU_Hi_LongKou/sample_0000 | 270 | 94.713 | 4321 | 51.5 MB |

The static browser Playground now starts with **grid 8×8, zero baseline and 3 permutations for every dataset**, as requested for the public interactive presentation. Explicit URL parameters still override these defaults. The table above remains historical performance evidence for **grid 4×4 / mean baseline / 1 permutation**, not a latency measurement of the new defaults. In particular, 8×8 / 3 on 103–270-channel models can be substantially slower, and the Run/Stop controls remain available. The browser smoke tests now validate the new default and alternative settings.
