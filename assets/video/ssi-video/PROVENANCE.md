# SSI 15s — data provenance

Built with HyperFrames from `SSI_15s_Design_Package` (motion direction + keyframes) and
`github.com/AtheavenMa/Spectral-Spatial-Interpretation`.

## Sources

| On screen | Source | Check |
|---|---|---|
| Input stack (v5, beat 1) | the six model-input bands from `docs/playground/.../sample_0163/x.f32` (6×128×128), per-band 2–98 % stretch, ramped through each band colour (`ssi-video-tools/prep_stack.py`) | real inputs; the package's `channel_0X_*.png` are SSI attribution overlays, so they are **not** used as inputs |
| Input image | `assets/video/hls_burnscar_0163/input.png` | byte-identical to the package copy |
| Φ(g,c) 16×16×6, bars, maps, totals | `assets/video/hls_burnscar_0163/result.json` | byte-identical to the package copy |
| Band maps, spatial map | `signed_overlay()` copied verbatim from `make_keyframes.py`; band maps exposure = max\|Φ\| = 0.0753553; S map exposure = max\|S\| | only raster size changed (576 px) |
| Location g | cell (row 10, col 12), 1-indexed; true 8×8 model pixels from `docs/playground/.../sample_0163/rgb.webp`, nearest-neighbour upscaled | — |
| "Masked at g" colour `#969084` | per-channel mean baseline (`meta.json`) mapped through the preview's affine RGB stretch fitted on the sample | display-only |
| Five restoration orders + 30 Δf ticks/pulses | `docs/playground/compute-runtime.js` re-run in Node (onnxruntime-web 1.21.0, the playground's version); the only change is exporting its own `rngFromSeed` so the seed-0 sampler can be replayed to cell g | full re-run vs `result.json`: max abs diff **0**, 5502 evaluations; mean of the five orders at g reproduces Φ(g,·) exactly |

## Values shown

- Φ(g,·) Blue…SWIR2: −0.0016, +0.0113, −0.0032, +0.0035, −0.0313, +0.0730
- T(c) SWIR1 / SWIR2: +0.567 / +0.751 (other totals shown as bars only, as in the storyboard)
- Restoration orders at g (band indices 0=Blue … 5=SWIR2):
  `[0,3,5,1,2,4] [0,2,5,3,1,4] [4,5,0,1,2,3] [4,2,1,3,0,5] [5,2,3,0,4,1]`

## v10 — opening title

- "Which bands matter, and where?" → "Which channels matter, and where?"

## v9 — "Sum to get…" and a continuous two-views finale

- Beat 5 title: "Sum to get six signed contributions." ("Sum" in the accent colour), 76 px.
- Beat 7 rebuilt as the two sums of Φ, with no object swaps:
  Σ over c — the six band maps glide into the same orthographic stack used for the input
  in beat 1 (c₁ on top), close up into one layer on which S(g) appears (orange rim glow),
  and that same layer turns face-on and settles as the WHERE map. The old version faded
  S(g) in underneath the tiles and then hid the tiles, which produced a visible jump.
  Σ over g — the WHICH CHANNELS chart starts only after the maps have left the right half,
  so nothing crosses the bars while they grow.

## v8 — scan-complete flash (32.9 s)

- When the orange scan line reaches the last grid row of the six band maps, it flares out;
  then each map, left to right (0.06 s apart), gets a short completion light: a screen-blend
  flash, a diagonal sheen, an orange rim glow that settles back, and a small spark burst.
  Beat 6 +0.3 s; starts 0 / 6.0 / 8.8 / 14.2 / 20.6 / 24.0 / 28.7 s; end 32.9 s.

## v7 — slower masking and restoration, no captions (32.6 s)

- Removed the two small caption lines from beat 3 (the x_{g,c} → x̄_c line and the
  "other 255 cells" line); "Context stays fixed" remains.
- Beat 3 4.2 → 5.4 s: slower split into channels, a 1.0 s drop to the channel means, the
  scene patch 1.3 s after the drop begins.
- Beat 4 4.2 → 6.4 s: first order one channel per 0.26 s; the next four at 0.11 / 0.095 /
  0.085 / 0.075 s per channel. Beat 6 hold trimmed by 0.4 s.
- Starts 0 / 6.0 / 8.8 / 14.2 / 20.6 / 24.0 / 28.4 s; end 32.6 s (1956 frames).

## v6 — what "masked at g" means (29.6 s)

- Beat 3 (8.8–13.0 s) now shows the operation on the data. Cell g is pulled out of the
  scene and split into its six channels: the observed row holds the real 8×8 values of
  c₁…c₆ at g (`x.f32`, rows 72–79, cols 88–95); in the masked row every channel's 64 pixels
  become that channel's mean baseline (`meta.json` baseline_mean), shown through the same
  per-band stretch and colour ramp so each pair is directly comparable
  (`ssi-video-tools/prep_mask.py`). All six drop together — B_g is the whole cell at the
  baseline — and each band token switches to its masked state at the same moment.
  Caption: x_{g,c} → x̄_c, "each channel at g is set to its mean (the baseline)".
  The RGB column shows the composite before/after; the scene receives the same patch.
  "Context stays fixed" + "Only g changes; the other 255 cells keep their observed values."
- At g the SWIR channels sit far above their means (SWIR1 0.508 → −0.130, SWIR2 0.898 →
  −0.156 in model units), so their masked tiles darken most — the same channels whose
  restoration later carries the largest Δf.
- Later beats shifted by +1.6 s (starts 0 / 6.0 / 8.8 / 13.0 / 17.2 / 20.6 / 25.4 s; end 29.6 s).

## v5 — the input explained as channels c × grid g (28 s)

- Beat 1 (0–6 s) now shows the input the way the paper's Fig. 2 does: six stacked channel
  layers (real bands), each labelled c₁…c₆ with its band name; a left bracket
  "c · Spectral channels · 6 bands"; one shared 16×16 grid on every layer with a bottom
  bracket "g · Spatial grids · 16 × 16 cells"; cell g (row 10, col 12) lit on all six layers
  and joined by a dashed column — one cell g holds all six channels c, the two indices of Φ(g, c).
  Then stack → U-Net → f(x) burn-region logit.
- Beat 2: the stack flattens into the observed scene; each layer's colour chip becomes the
  band token in its pill. Later beats unchanged, shifted by +3 s (starts 0 / 6.0 / 8.8 /
  11.4 / 15.6 / 19.0 / 23.8 s; end 28 s, 1680 frames).

## v4 — ember accent + effects

- Accent cyan → orange `#FF8A24` (hue ≈ 28°, between positive-sign coral ≈ 5° and SWIR1 ≈ 36°);
  used only for titles, labels, connectors and light effects — never on bars, tokens, ticks or maps.
  Cool counter-glow switched to indigo.
- Effects, each tied to a step: 3D hinge entrance of the input image; sheen across each band
  pill; shockwave + flash + sparks at the masking instant at g; sign-coloured sparks on each
  restoration of the first (slow) order; glowing leading edge on the six signed bars; an orange
  scan line leading the row-by-row band-map reveal; the six maps fan into a 3D stack and
  flatten into S(g); anamorphic flare + bloom on the SSI reveal; slow floating camera.
  All are deterministic functions of timeline time (seeded hashes, no clocks).

## v3 — dark, 25 s

- Template: **Data Drift** from `hyperframes-creative/references/visual-styles.md` (§ 5),
  recorded as `design.md`. Canvas `#0a0a0a`, single accent cyan `#06b6d4`, purple used
  only in an atmospheric glow. Atmosphere: seeded particle field (canvas, a pure function
  of timeline time), light traces along the four connector arrows, two drifting radial
  glows, vignette, static grain. Band and sign palettes unchanged.
- Heatmaps for the dark canvas: identical `signed_overlay` mapping and exposures; only the
  substrate blends toward `#0a0a0a` (×0.4) instead of white (`ssi-video-tools/prep_dark.py`).
- Timing: 15 s → 25 s (1500 frames at 60 fps). Beats start at 0 / 3.0 / 5.8 / 8.4 / 12.6 /
  16.0 / 20.8 s. Most of the added time goes to the middle: the first restoration order
  runs one channel per 0.17 s, then the next four orders speed up; the six signed values
  hold ~1 s before contracting; the band-map sweep runs over 1.8 s.
- Title: "Which bands matter, and where?" on one line.

## Typography (v2)

- Two voices: **Inter Display** (spec) for language and figures; **TeX / Computer Modern**
  for mathematics. Every symbol is typeset by MathJax 3.2.2 from TeX source
  (`\Phi(g,c)`, `\Delta f`, `f(x)`, `g`) into self-contained SVG paths — upright capital
  Greek, italic variables, TeX spacing after the comma. Scaled ×1.12 to match Inter's x-height.
- Figures: `tnum` + `lnum`, true minus U+2212, right-aligned so decimals line up.
- Titles: per-word masked arrivals; two-sentence titles set in two tones (ink / teal),
  the same pattern as "and where?" and "Φ(g, c)". Tracking −0.03em at display size.
- Dashes: em dash closes line 1 ("Which bands matter—") instead of opening line 2;
  en dash in "Spectral–Spatial"; caps overlines use the `case` feature and +0.13em tracking.
- Layout on a 110 px margin grid; the image no longer shifts between beats 2 and 3.
- All morphs are paint/transform-only (clip-path rects, translate/scale) — no width/height tweens.

## Display choices

- Positive bars use `#EE7667`, negative `#4D91CA` as specified. Signed *numbers* use the
  same hues darkened (`#D9634F` / `#3B7DB6`) so text meets WCAG 3:1 on the light ground.
- Δf ticks are scaled to the largest |Δf| at g (0.1008); pulse size scales the same way.
- The 9–11 s raster sweep reveals each band map one grid row (16 cells) per step to show
  the local game repeated over all positions; it is not a recording of computation order timing.
