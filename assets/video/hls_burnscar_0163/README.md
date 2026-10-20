# SSI video evidence · HLS Burn Scars · sample_0163

This folder contains **authentic, newly computed SSI results**, not copies of the paper's Atlas. All layers correspond to the same original HLS input, same fixed target, same model and same run:

**Sample** \`HLS_BurnScars/sample_0163\` · **Grid** 16×16 · **Baseline** per-channel mean · **Permutations** 5 · **Seed** 0 · **Target** mean burn-class logit on the 2,734 fixed GT burn pixels.

The input is a six-band HLS satellite image (128×128). The PyTorch checkpoint was exported into the verified ONNX model \`docs/playground/assets/hls_unet.onnx\`. The computation uses the actual SSI Playground browser implementation \`SSIComputeRuntime.explain\`, including its JavaScript permutation sampler. Numerical values in the JSON are **not interpolated**.

## Evidence for the explanatory narrative

### 1. Where? Spatial interpretation

The burn-scar GT occupies **16.69%** of this image's pixels. For this input and seed, **83.82% of positive spatial SSI mass**, proportionally weighted by the GT fraction within each grid cell, falls in the burn-scar region. All 16 spatial cells with largest absolute SSI scores overlap the GT region by more than 50%, and 15 of those 16 cells have positive attribution.

This is a **single-example descriptive observation**, not an independent localization test: the explained scalar target was defined over the GT region itself. Heatmap intensity is not burn probability, and pixels outside the region can matter through model context.

### 2. Which channels? Spectral interpretation

Total signed channel contribution, obtained by summing $\Phi(g,c)$ across all 256 grid cells:

| Channel | Sum of signed SSI | Interpretation |
|---|---:|---|
| SWIR2 | +0.751038 | Strongest positive support for the chosen burn-class logit |
| SWIR1 | +0.566800 | Second-largest positive support |
| Blue | −0.020774 | Small net negative |
| NIR | −0.048171 | Small net negative |
| Green | −0.182233 | Negative total |
| Red | −0.192078 | Negative total |

The displayed ranking by **absolute** size is SWIR2, SWIR1, Red, Green, NIR, Blue. The signed sum of all bands over all cells is **+0.874582**.

**Why joint SSI matters even in this one example:** SWIR2 and SWIR1 both have positive global totals, but their signed 256-cell attribution maps have **Pearson correlation −0.532**. A fraction-of-GT-weighted spatial breakdown gives SWIR2 **+0.936 inside versus −0.185 outside** the burn region, compared with SWIR1 **+0.0215 inside versus +0.545 outside**. This is a descriptive grid-cell weighting, not pixel-level Shapley values. It shows why one global channel vector cannot replace channel-resolved maps. See [EXPLANATION_LOGIC.md](EXPLANATION_LOGIC.md) for the full scientific argument.

In the **normalized original model input**, target pixels have a higher SWIR2 average (0.752 versus 0.095 elsewhere) and SWIR1 average (0.506 versus 0.284), and a slightly lower NIR average (−0.928 versus −0.813). This is broadly consistent with burn-related SWIR increases and NIR decreases discussed in the paper's physical band priors. However, the model's attribution sign is determined by its conditional prediction contrast, not by whether a reflectance value itself increases or decreases.

The paper cites Red, SWIR1 and SWIR2 as **dataset-level physically motivated prior bands**, not as channels required to have positive SSI on every single image. **Red is negative in this example**; do not claim that all physically motivated bands have positive attribution.

### 3. How the two views are mathematically connected

SSI does not run a spatial explainer and a spectral explainer separately. It computes **one joint attribution table** $\Phi(g,c)$, with shape **16 × 16 × 6**:

- Choose grid cell $g$ and fix all other spatial cells at their observed values.
- Replace the channels of cell $g$ by the per-channel mean baseline, and restore those channels in five sampled orders.
- Allocate the *local contextual contrast* among the six channels by sampled Shapley marginals.
- Spatial map: $S(g) = \sum_c \Phi(g,c)$.
- Global spectral totals: $T(c) = \sum_g \Phi(g,c)$.
- Individual spectral maps: $g \mapsto \Phi(g,c)$, using the **same** joint table. In this image, SWIR2's positive attribution is localized in the burn region; SWIR1 also supports the logit but has a more spatially distributed pattern.

**Do not claim global efficiency:** $\sum_{g,c}\Phi(g,c)=0.874582$ is the sum of cellwise observed-context contrasts; it is *not* the predicted burn logit, which is **1.206524** in this run. SSI's exact aggregation identity is **within each cell**, $\sum_c\Phi(g,c)=f(x)-f(x_{\text{cell }g\text{ masked}})$.

The observed contextual region/target is the mean burn logit at the GT burn pixels. The GT mask is a scoring-region definition, not an extra input channel to the model.

## Video narrative (the example is one short proof, not the entire film)

1. **The scientific question.** “Which spectral channels matter, and where?” Show the original HLS image and the single scalar target (burn-class logit over a fixed GT region).
2. **The method.** Split the image into 16×16 spatial cells and six bands. Animate one cell being masked against its *observed* surroundings, then its six channels being restored in different orders. Represent these steps as **five sampled permutations**, not an exhaustive calculation.
3. **The joint object.** Construct $\Phi(g,c)$: 256 locations × 6 spectral channels. This is the main innovation and the visual centerpiece of the video.
4. **Two views from one computation.** Collapse the channel axis to produce the Spatial SSI overlay; collapse the location axis to produce one global Spectral Contributions chart. Then reveal the SWIR2 per-channel spatial map to demonstrate the link.
5. **Real-result check.** The positive spatial attribution is concentrated in the actual burn region (83.82% positive mass weighted by GT fraction versus 16.69% GT area); SWIR2 and SWIR1 deliver the strongest positive support for the burn logit. Explain that this is a single-example finding, not a method theorem.
6. **Close.** “One joint explanation. Where and which channels.” Link to the live SSI Playground.

The original Atlas figures, benchmarking charts, and cross-dataset showcases should collectively take **no more than about 20%** of screen time. The rest belongs to the scientific motivation, the explicit observed-context Shapley process, the joint $\Phi(g,c)$ object, and the exact relationship between the two aggregations.

## Video asset files

| File | Intended use |
|---|---|
| \`input.png\` | Original image RGB display, aligned to 128×128 HLS input |
| \`ground_truth.png\` | Real burn-scar GT mask, red target and neutral background |
| \`spatial_ssi.png\` | Signed spatial SSI continuously overlaid on original image |
| \`channel_01_blue.png\` through \`channel_06_swir2.png\` | Six authentic signed SSI channel overlays |
| \`spectral_contributions.png\` | Single global signed contribution chart |
| \`ssi_explanation_overview.png\` | Multi-panel editorial composition, ideal as storyboard reference |
| \`playground_screenshot.png\` | Screenshot of the actual complete numerical result in the browser |
| \`result.json\` | Full 16×16×6 signed unaltered SSI tensor plus settings/provenance |
| \`analysis.json\` | Derived scores, GT overlap, spectral ranking and input-band comparisons |
| \`manifest.json\` | Per-file checksum and source provenance |

To reproduce the assets: \`python tools/export_video_hls_0163.py\`. The GitHub Actions workflow \`.github/workflows/video-evidence.yml\` independently produces them and validates the computation. The resulting images are **designed for animation**, but no animation is implied to be physically observed.

**Paper:** [Spectral-Spatial Interpretation (NeurIPS 2026)](https://arxiv.org/abs/2610.21114). Relevant theory: Sections 3.2–3.5, especially the conditional position game and Theorem 2. Relevant physical context: Appendix C.3 on HLS band priors. Relevant qualitative interpretation: Section 4.4. These support the method and why certain spectral bands are worth checking; they do not independently verify the new individual sample's attribution values, which come from \`result.json\`.
