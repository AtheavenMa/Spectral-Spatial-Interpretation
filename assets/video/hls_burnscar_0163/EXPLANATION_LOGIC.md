# Final explanation logic · SSI / HLS sample_0163

**Purpose:** establish a scientifically correct explanation *before* another promotional video is made. One image, one fixed scalar target, one computation, two consistent summaries. Original research imagery must occupy at most 20% of the finished screen time; the other 80% explains the mechanism and the shared joint attribution.

**Exact real data:** [result.json](result.json) · [analysis.json](analysis.json) · [visual plates](ssi_explanation_overview.png) · [regeneration script](../../../tools/export_video_hls_0163.py)

## The central question

**Which spectral channels support a model's burn-scar decision, and exactly where in the image do they do so?**

A conventional spatial heatmap loses channel identity. A global channel ranking loses location. The key SSI result is **not** just that we can display both charts: we can derive both from the **same joint attribution**.

## One explicit computation, in logical order

**1. Define the observable and the target.** The real input is HLS sample_0163, six reflectance bands, 128×128 pixels. Use the trained HLS UNet. The scalar function is its *burn-class logit averaged over the 2,734 pixels belonging to the fixed GT burn region*. The GT mask defines the target score, not an extra channel or a prediction injected into the model.

**2. Choose one spatial cell.** Partition the image into 16×16 cells, each 8×8 pixels. At every cell $g$, its six bands are the local Shapley players. Masking means replacing *only that cell's selected channels* by the corresponding **per-channel mean baseline**. The other 255 cells keep their original observed values. Never animate masking the whole surrounding image.

**3. Evaluate the local channel game.** First take the whole cell at its baseline, then restore its channels to their original observed values in sampled orders. For any channel subset $R$ within the target cell:

$$
w_g(R)=f(x_{B_g\cup R})-f(x_{B_g}),\qquad
B_g=\mathcal P\setminus S_g.
$$

The experiment uses **five** channel permutations per cell (not exhaustive enumeration) with seed 0. Add each channel's successive marginal contribution, average over the five orders, and obtain six real signed numbers for that cell.

**4. Complete the joint explanation.** Repeat across **256 cells**. The sole attribution object is the table

$$
\Phi(g,c),\qquad g=1,\ldots,256,\quad c=1,\ldots,6.
$$

That means **1,536 position/channel contributions**; it does *not* mean that only 1,536 model evaluations were required.

**5. Read two projections of the same object.** These are *aggregations*, not independent explainers:

$$
\underbrace{S(g)=\sum_c\Phi(g,c)}_{\text{spatial map: where?}},
\qquad
\underbrace{T(c)=\sum_g\Phi(g,c)}_{\text{global spectral totals: which bands?}}.
$$

Each fixed-band map $g\mapsto\Phi(g,c)$ shows **where that band contributes**. Spatial accumulation is locally consistent: $S(g)=f(x)-f(x_{B_g})$ for each cell. Crucially, $\sum_g S(g)$ need *not* equal $f(x)$ or the image-wide input-to-baseline contrast; the paper explicitly establishes this distinction (Theorem 2, Proposition 1).

## What the actual sample demonstrates

| Quantity | Verified result | Safe reading |
|---|---:|---|
| GT burn-scar area | 2,734 / 16,384 = **16.69%** | The fixed score target occupies a minority of the pixels |
| Positive spatial SSI weighted within the GT region | **83.82%** | Positive contextual attribution is concentrated near the actual burn region |
| SWIR2 aggregate signed SSI | **+0.7510** | Strongest positive contribution to the target logit |
| SWIR1 aggregate signed SSI | **+0.5668** | Second strongest positive contribution |
| Red aggregate signed SSI | **−0.1921** | This image's red band has net *negative* signed contribution |
| NIR aggregate signed SSI | **−0.0482** | Small negative net contribution |
| Full unmasked model target logit | **+1.2065** | Not the sum of SSI contributions |
| Sum of contextual spatial/spectral totals | **+0.8746** | Exact mutual aggregation; *not* a global score decomposition |

### The distinctive joint-attribution observation

**The two most positive bands are not spatially interchangeable.** From the true 256-cell attribution maps, SWIR1 and SWIR2 both have positive aggregate scores, yet their **Pearson spatial correlation is approximately −0.532** (signed-map cosine similarity approximately −0.456). Thus their *spatial attribution patterns are different, even opposed*, despite the positive global totals.

Splitting each cell's attribution according to the fraction of its pixels inside the fixed GT region gives the following descriptive, **fraction-weighted cell accounting**:

| Band | GT-weighted signed SSI | Non-GT-weighted signed SSI | Global total |
|---|---:|---:|---:|
| SWIR2 | +0.9362 | −0.1852 | +0.7510 |
| SWIR1 | +0.0215 | +0.5453 | +0.5668 |

These are fractional assignments of **grid-cell contributions**, not pixel-level Shapley attributions. In particular, SWIR1's positive aggregate contribution is primarily associated with cells outside the GT mask under this descriptive partition, whereas SWIR2 is strongly positive in the target region and negative in the remaining area.

This is a **stronger motivation for SSI than displaying two charts alone**: if a method forced a single spatial map times one global spectral vector, it could not represent these two different signed spatial profiles with both global coefficients positive. SSI preserves the position-specific channel patterns before aggregation.

**Important qualification:** the evaluation target was *defined using the GT burn region*. High attribution inside that region is therefore not independent evidence of localization accuracy: the chosen score already favors explaining that region. Use this case to demonstrate one actual model's **joint spectral–spatial evidence**, and use the paper's independent faithfulness/localization protocols when claiming method performance.

Both SWIR channels are physically relevant to fire mapping. In the normalized original input, the burn region's mean SWIR2 is **0.752** versus **0.095** elsewhere, while SWIR1 is **0.506** versus **0.284**. These are observed differences in model-normalized values, not direct reflectance measurements; a negative band attribution does *not* imply the image's reflectance is negative.

The paper's HLS spectral priors include **Red, SWIR1 and SWIR2** based on known burn-scar spectroscopy and NBR-related reasoning. That is a dataset-level *prior* for evaluation: it does not require Red to be positively attributed for every sample. **The Red result here is negative**, and should be preserved.

The single sample illustrates a physically intelligible model attribution, *not* proof that SSI is causally correct, or that an isolated high SSI map confirms the underlying remote-sensing physics. Model faithfulness claims require the paper's deletion/insertion and localization evaluations.

## 30-second communication logic (not video production)

| Beat | Information on screen | Logical requirement |
|---|---|---|
| **0–5 s · Question** | One real image and the fixed burn-class target. “Which channels matter—and where?” | Viewers know what is being explained |
| **5–13 s · Mechanism** | Divide into cells, pick one, keep the surrounding cells observed, mask and restore its six bands with multiple sampled orders | Must show *observed context*, *per-channel mean baseline*, and local Shapley allocation |
| **13–20 s · Main result** | Build the 256×6 attribution table; aggregate it once across channels for Spatial SSI, and once across cells for Spectral SSI | The two projections emerge from the **same table**, not independent pipelines |
| **20–26 s · Scientific example** | Briefly show authentic sample_0163 spatial overlay and SWIR2/SWIR1 signed contributions, GT overlap if readable | **20% of running time maximum** for example/Atlas imagery; avoid false sign or physical claims |
| **26–30 s · Close** | “One image. One joint explanation.” Paper / GitHub / Playground | End with the method, not an image slideshow |

### Proposed five caption lines

1. **One image. Six spectral channels.**
2. **Keep the observed spatial context fixed.**
3. **Allocate channel contributions within each cell.**
4. **One joint attribution. Two consistent views.**
5. **Where the evidence is. Which channels contribute.**

### Things the explanation must not claim

- Do not present the sample as **all** red/SWIR bands positively contributing: **Red is negative**.
- Do not treat a positive heatmap as a class probability or an accuracy/ground-truth prediction.
- Do not equate the sum of SSI contributions (0.8746) with the model's target logit (1.2065).
- Do not imply SSI partitions the whole model score into globally efficient cell contributions.
- Do not smooth numerical values; interpolation applies only to rendered overlay pixels.
- Do not substitute the older Atlas sample_0163 PNG for the genuine **grid=16, K=5** recomputation, which is separately recorded in this folder.
- Do not show a Local/Selected-cell Spectral Contributions panel in the **public Playground**. It now shows **one global channel-contribution chart**, while per-cell values remain in the full SSI tensor/JSON.

**Research source:** [Spectral-Spatial Interpretation](https://arxiv.org/html/2610.21114), Sections 3.1–3.5, 4.4 and Appendix C.3. **Instance-level evidence:** [analysis.json](analysis.json) and [result.json](result.json) in this folder.
