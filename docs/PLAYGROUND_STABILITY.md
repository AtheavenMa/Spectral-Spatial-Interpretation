# Hyperspectral SSI sampling sensitivity

This is a **real-model sensitivity check** for the channel rankings in the SSI Playground. It checks how the finite sampled-permutation estimator changes when the number of sampled orders or random seed changes. It is not an independent measurement of ground-truth feature relevance.

## Protocol

- One registered checkpoint and its bundled input for each dataset: Pavia University, Salinas, WHU-Hi-LongKou.
- Fixed **4×4 spatial grid**, **mean baseline**, and each adapter's previously defined **fixed scalar target**.
- Permutation SSI from the same `ssi.py`. No training and no generated or substituted image.
- Compare **absolute-value Top 10 channel scores**. Each run retains the original **signed** SSI values.
- Main comparison uses **seed 0** and permutation counts **K=1 versus K=3**.
- At **K=3**, compare seeds **0 and 1**. PaviaU additionally compares **K=3 and K=5** at seed 0. Salinas and LongKou are intentionally not run with K=5 because their current CPU lab caps are K=4 and K=3.
- Ranking of ties uses original channel order. `top10_overlap` counts shared bands, `Jaccard` divides shared by unique bands across the two Top 10 sets; Spearman compares the **entire absolute-score ranking**; sign agreement refers only to shared Top 10 bands.

GitHub Actions CPU environment: Linux Azure runner, **Python 3.11.17**, **PyTorch 2.6.0+cpu**, **4 threads**. Measurements were produced by:

```bash
python benchmarks/spectral_stability.py --second-seed --output /tmp/ssi_spectral_stability.json
```

CI source: [Actions run 39359117906](https://github.com/AtheavenMa/Spectral-Spatial-Interpretation/actions/runs/39359117906), artifact `ssi-spectral-stability`.

## Real results

| Model | Comparison | Shared Top 10 | Jaccard | Full absolute-rank Spearman |
|---|---|---:|---:|---:|
| PaviaU (103 bands) | K=1 vs K=3, seed 0 | 6 / 10 | 0.4286 | 0.6889 |
| PaviaU (103 bands) | K=3 vs K=5, seed 0 | 7 / 10 | 0.5385 | 0.8524 |
| PaviaU (103 bands) | K=3, seed 0 vs seed 1 | 6 / 10 | 0.4286 | 0.8465 |
| Salinas (204 bands) | K=1 vs K=3, seed 0 | 8 / 10 | 0.6667 | 0.9751 |
| Salinas (204 bands) | K=3, seed 0 vs seed 1 | 8 / 10 | 0.6667 | 0.9802 |
| WHU-Hi-LongKou (270 bands) | K=1 vs K=3, seed 0 | 9 / 10 | 0.8182 | 0.8757 |
| WHU-Hi-LongKou (270 bands) | K=3, seed 0 vs seed 1 | 7 / 10 | 0.5385 | 0.9132 |

The shared Top 10 channels have **100% sign agreement** for all these specific comparisons. All recorded local-efficiency errors were below `2e-15`, as expected for complete permutation paths. **Local efficiency does not establish the stability of individual estimated Shapley channel values.**

### CPU work in this run

| Model | K=1 seconds | K=3 seconds | Additional K=5 seconds |
|---|---:|---:|---:|
| PaviaU | 3.470 | 10.681 | 16.189 |
| Salinas | 8.237 | 24.793 | — |
| WHU-Hi-LongKou | 11.419 | 33.474 | — |

These are wall-clock measurements from this Actions runner for seed 0. They are not promises of a user's local runtime and are separate from the previous [CPU benchmark](PLAYGROUND_PERFORMANCE.md).

## Interpretation and interface decision

**One permutation is a legitimate fast SSI estimator, but its Top 10 should be treated as an exploratory ranking, not a converged or reproducibly invariant top-band set.** PaviaU changes four members between K=1 and K=3; increasing K to 5 still changes three of the K=3 members. Salinas has relatively high overall rank agreement but still changes two Top 10 members; LongKou changes two to three across these comparisons.

The interface retains **Quick = 4×4 / K=1**, so anyone can play with the real calculation quickly. PaviaU offers K=3 and up to K=8 at grid 4; Salinas offers K=3 and up to K=4; LongKou offers up to K=3. Each result displays the number of sampled channel orders. For a result intended to support a detailed feature interpretation, increase K and repeat with another seed if the ranking matters. Do not infer that the sampling has converged from these sparse comparisons alone.

The complete numeric attribution result is still available in the JSON download. No ranking is frozen or substituted from a pre-rendered figure.

## Scope

This is **one input per dataset, fixed grid and baseline**, not a dataset-wide stability evaluation, not a statistical confidence interval, and not evidence of physical causality. It answers the concrete release question of whether fast Top 10 displays are sensitive to finite permutation sampling. They are, so the product exposes the estimator settings and makes additional sampling possible without changing SSI's meaning.
