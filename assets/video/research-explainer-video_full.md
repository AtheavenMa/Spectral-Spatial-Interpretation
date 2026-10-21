# research-explainer-video — full skill text

This file is the complete text of the `research-explainer-video` skill in one document:
the main `SKILL.md`, its two reference files and its helper script. The installable
package is `research-explainer-video.skill`; the content here is identical.

**Skill name:** `research-explainer-video`

**When it triggers (description):** Plan, build and iterate a data-faithful motion explainer of a research method, model, algorithm or result with HyperFrames (HTML to MP4), starting from a paper, a GitHub repo, a paper figure, a storyboard or a design package. Use it whenever someone wants to turn a scientific or ML method, an interpretability or attribution result, a pipeline diagram or "Fig. N" into an animated video or motion graphic, even if they only say "animate this figure", "make a 20 s video explaining our method" or "make the explainer look cooler". It sits on top of the public HyperFrames skills (/hyperframes, /hyperframes-core, /hyperframes-animation, /hyperframes-creative, /hyperframes-cli, /hyperframes-registry) and adds scientific provenance, notation-first storytelling, object continuity across beats, effects bound to method steps, and a review loop that survives many iterations.

## Package layout

```
research-explainer-video/
├── SKILL.md                         → Part 1
├── references/
│   ├── build-patterns.md            → Part 2
│   └── review-and-delivery.md       → Part 3
└── scripts/
    └── tex2svg.js                   → Part 4
```

## Contents

- [Part 1 — SKILL.md](#part-1--skillmd)
- [Part 2 — references/build-patterns.md](#part-2--referencesbuild-patternsmd)
- [Part 3 — references/review-and-delivery.md](#part-3--referencesreview-and-deliverymd)
- [Part 4 — scripts/tex2svg.js](#part-4--scriptstex2svgjs)

---

## Part 1 — SKILL.md

*Research explainer video (on HyperFrames)*

This skill is the *science layer*. The HyperFrames skills own the technical contract —
how a composition is timed, animated, checked and rendered. This skill owns what makes a
method explainer trustworthy and clear: every value is real, every symbol is introduced
before it is used, every on-screen object keeps its identity, and every effect means one
step of the method.

Read the HyperFrames skills for *how*; read this one for *what to build and in which order*.

### How this skill divides work with the HyperFrames skills

| Need | Load | What it gives you here |
|---|---|---|
| Entry, project state, intent interview, `BRIEF.md`, route choice | `/hyperframes` (+ `references/intent-interview.md`, `review-loop.md`, `production-loop.md`) | Route is usually `/general-video` (custom, any length) or `/faceless-explainer` (narrated, invented visuals). A storyboard request changes the review process, not the route. |
| Composition contract | `/hyperframes-core` | `data-*` timing, one paused timeline registered after build, determinism rules, sub-compositions, lint gotchas (no CSS transform on a GSAP-tweened node, no `<br>` in body text, unique ids). |
| Motion | `/hyperframes-animation` (`rules-index.md`, `adapters/gsap.md`) | `fromTo` seek-safety; **transform/paint-only** motion (width/height tweens are forbidden — use clip-path, scale, masks); `svg-path-draw`, `waterfall-entry`, `counting-dynamic-scale`, `particle-burst`. |
| Camera moves, reframes, 3D depth | `/hyperframes-keyframes` | Seek-safe keyframes for punch-ins and stack/tilt choreography. |
| Look and type | `/hyperframes-creative` (`house-style.md`, `video-composition.md`, `typography.md`, `visual-styles.md`, `design-spec.md`) | Design-spec precedence; video type sizes; dark-canvas adjustments; named styles (e.g. *Data Drift* for AI/data, *Swiss Pulse* for clinical, precise metrics). |
| Ready-made moves | `/hyperframes-registry` | `npx hyperframes catalog --query "<the move in plain English>"` **before** hand-building a transition, chart or reveal. |
| Sound (optional) | `/media-use`, `/hyperframes-audio` | SFX/BGM sourcing and mixing, if the brief wants sound. |
| Dev loop | `/hyperframes-cli` | `init`, `lint`, `check`, `snapshot`, `render`, `doctor`, `browser`. |

### Principles (the why behind every step)

1. **Data is content; styling is display.** Numbers, maps, permutations and images come
   from the actual computation. A display transform (colour ramp, stretch, darker
   substrate, resampling) is allowed only if the underlying values are untouched — and it
   is written down. A viewer of a method video cannot check your numbers, so you must.
2. **Introduce notation before using it.** If later beats say Φ(g, c), Δf or x̄_c, an early
   beat must show what g, c, Δf are *as objects* (a layer, a cell, a change), not as a
   glossary line.
3. **Show the operation, don't caption it.** "Masked", "restored", "summed" must be visible
   as something happening to the data (values replaced, layers merged). Small explanatory
   text is the first thing reviewers ask to remove.
4. **One object, one identity.** The thing that represents a channel, a location or a
   result stays the same element from the beat it appears to the end, morphing between
   roles. Swapping objects (crossfading A out and B in) is where viewers lose the thread
   and where visual "jumps" appear.
5. **Every effect names a method step.** A shockwave at the masking instant, sign-coloured
   sparks for a measured change, a scan line for "repeated at every position". If an
   effect cannot name its step, cut it.
6. **Explanations run slower than promos.** First pass of a repeated procedure slow, later
   passes faster; any number the viewer must read holds for about a second.

### Workflow

#### Phase 0 — Intake and provenance (before any HTML)

- Read every input fully: storyboard, motion direction, keyframes, the repo README,
  example outputs, the paper figure. Motion-direction text usually overrides a static
  storyboard where they disagree (a static grid of five rows may describe one row moving
  five times).
- Verify that packaged assets equal the repository's (`cmp` / hashes). Record it.
- **Read the README of every asset folder before reusing a file.** Files named like inputs
  (e.g. `channel_01.png`) may be outputs (attribution overlays). Using an output as an
  input is a scientific error that no reviewer will catch on screen.
- Find every placeholder the design admits to ("illustrative orders", "stand-in scores").
  Look for the deterministic source: a seeded sampler, a saved tensor, the original
  runtime. Re-run the original code (instrument, don't reimplement) and require exact
  agreement with the published result before using any value.
- Start `PROVENANCE.md`: on-screen element → source file → verification → display-only
  transforms. Keep a change log in it for every version.

If the network is restricted: vendor GSAP and fonts into the project (CDNs may be blocked
at render time); point the CLI at an installed Chromium with `HYPERFRAMES_BROWSER_PATH` if
`npx hyperframes browser ensure` cannot download; prefer WASM builds (e.g.
`onnxruntime-web`) over packages whose install step downloads native binaries.

#### Phase 1 — Intent and brief

Run the `/hyperframes` intent layer even when a design package exists — a short brief up
front saves whole render iterations later. Beyond the route's must-haves, settle these
explicitly, because each one triggered a full revision in practice:

- Length cap, and which part may grow (usually the computational middle).
- Light or dark canvas; one accent colour; whether a named style is wanted.
- **Terminology and notation**: "bands" vs "channels", symbol names, whether formulas
  appear at all. One term per concept, everywhere, titles included.
- Text tolerance: titles and labels only, or captions allowed?
- Which values must be legible on screen, and for how long.
- Sound: none, SFX only, or a bed.

Write `BRIEF.md`, and a `design.md` whose frontmatter tokens are the brand truth
(`/hyperframes-creative` → `design-spec.md`).

#### Phase 2 — Concept map: beats, notation, continuity, effects

Write four small tables before building; they are the real storyboard.

1. **Beat table** — time window, title, what is shown, what is learned, which data.
   Order beats as the method executes. A typical method film:
   *question → input and notation → one local operation → measurement → local result →
   repeat everywhere (the joint object) → aggregations / views → lockup.*
2. **Notation beat** — the first content beat defines every index the film uses, in the
   paper's own visual language when it has one (e.g. a stack of channel layers with a
   bracket for c, a shared grid with a bracket for g, one cell lit through all layers).
3. **Continuity map** — each persistent object and its role in every beat it lives in
   (chip → token → dot → tab → rule …). This is what decides the architecture.
4. **Effect map** — effect → beat → the method step it marks.

Show stills of the notation beat and one mid-film beat for approval before animating the
rest (`review-loop.md`).

#### Phase 3 — Visual system

- **Separate the data palette from the accent.** List every data hue (category colours,
  sign colours) on the colour wheel first; pick the accent hue far from all of them; never
  use the accent on a data mark. Category and sign colours are content — never restyle
  them for a theme; only darken/lighten *text* variants to pass contrast.
- **Typography in voices** (`typography.md`): one statement face (keep the design spec's
  family even if it is on the "overused" list — the spec wins); figures in the same family
  with `tnum`/`lnum`, a true minus (U+2212) and decimal alignment; mathematics typeset from
  TeX (see `references/build-patterns.md`). Check monospace candidates for dotted/slashed
  zeros before using them for scientific values.
- **Typesetting details**: no line-initial dash (end the line with it instead); en dash in
  compounds (Spectral–Spatial); true minus; caps labels with the `case` feature and
  positive tracking; display tracking slightly negative on light, neutral on dark.
- **Two-tone titles**: statement in ink, counterpart in accent, word-by-word masked
  arrivals. Keep titles on one line where they fit; shrink before wrapping.
- **Dark templates** (*Data Drift*, *Shadow Cut*): one step lighter weights, a little more
  line height, radial glows plus grain instead of full-screen linear gradients (banding),
  darken heatmap substrates rather than washing them toward white.
- Layout on a fixed margin grid; align panels to each other's edges; a footer rule can
  double as a progress line.

#### Phase 4 — Build architecture

- **One composition when objects persist across beats.** Sub-compositions cannot share
  DOM, so a film whose tokens morph from beat 1 to beat 7 lives in one `index.html` with
  one timeline. Accept the `composition_file_too_large` lint warning, or move only
  non-shared layers (background atmosphere) into sub-compositions.
- **Beat clock.** Express every time as `Tn + offset` from a handful of constants
  (`T1 … T7`, `END`). Retiming or inserting seconds becomes a one-line edit — the most
  frequently used change in review.
- **Seek-safe helper**: every tween is `fromTo` with explicit endpoints and
  `immediateRender: false`; initial states are `tl.set(..., 0)`; register the timeline
  last.
- **Rect morphs with clip-path**, not width/height: full-frame layers whose visible shape
  is `inset(top right bottom left round r)`; radii stay exact at any size.
- **Orthographic stacks** for "layers of a tensor": nest position/scale → `rotationX` →
  `rotation`, no perspective, so screen coordinates are computable for overlays.
- **Handoffs**: morph one element into its next role, or make sure the incoming element is
  above the outgoing one in paint order and identical in geometry at the swap frame.
- **Paths**: sequence regions so a moving object never crosses something else that is
  animating.
- **Deterministic FX**: seeded fields and hashed particle bursts drawn from a timeline
  proxy's `onUpdate`; no clocks, no unseeded random.
- **Check-friendly FX** (`hyperframes check` treats any `<canvas>` as an opaque occluder):
  small local canvases visible only inside their burst windows; `data-layout-ignore` on
  decorative layers; binary opacity on masked title words; `data-layout-allow-occlusion`
  only on the specific labels an effect intentionally crosses. `pointer-events:none` does
  not help — the audit restores hit testing.
- Prefix ids (a duplicate `id="fx"` once pointed a canvas lookup at a card).

Code for each pattern: `references/build-patterns.md`.

#### Phase 5 — Review loop

1. `npx hyperframes check` until 0 errors; read warnings; treat info-level transition
   overlaps as expected.
2. `npx hyperframes snapshot --at <settled times>,<transition times>` and inspect the
   contact sheet. Batch visual checks — each image inspected costs context.
3. Share stills (or a short draft render) for direction; render the full 60 fps file only
   when direction is agreed. Plan for render time (software GL ≈ 10–12 s of render per
   second of 60 fps video on 2 cores); run long renders in the background.
4. After every render: `ffprobe` frame count = duration × fps; decode frames at the changed
   moments and look at them; a passing check does not certify pixels.
5. Version every iteration (`film_v7.mp4`-style names, a source backup, one change-log line).

#### Phase 6 — Feedback you should pre-empt

These requests recur across method films; build the defaults in from the start.

| Typical request | Default that avoids it |
|---|---|
| "Slower here" (repeated procedure, masking, measurement) | First pass ≥ 0.25 s per step, later passes faster; numbers hold ≥ 1 s |
| "Remove the small text" | Explain by transformation; titles and labels only |
| "Make it cooler" | Pick a named dark style; add effects only from the effect map |
| "Not smooth / doesn't line up" at a handoff | Single-object morphs; check paint order; no crossing paths |
| "Explain concept X more intuitively" | Show X as an operation on the real data, before/after side by side |
| Wording / one-line titles / term changes | Settle terminology in the brief; size titles to fit one line |
| "Use the paper's figure style" | Reuse the paper's visual grammar in the notation beat and echo it at the end |

#### Phase 7 — Delivery

- Final encode with `--quality delivery` when the cut is locked; keep `looks` for review.
- Ship: the MP4, the project zip, `design.md`, `PROVENANCE.md`, the data/asset scripts,
  and a `README.md` describing beat structure, continuity, visual system, architecture,
  provenance and rebuild commands (`references/review-and-delivery.md` has a template).
- Remove assets from abandoned versions, then re-run `check` to prove nothing referenced
  them (asset names built in JS do not show up in a plain grep).

### Reference files

- `references/build-patterns.md` — code for the beat clock, seek-safe helper, clip-path
  morphs, orthographic stacks, TeX→SVG math, binary masked titles, seeded particle field,
  local spark canvases, count-ups.
- `references/review-and-delivery.md` — snapshot/render/verify commands, decoded-frame
  grids, PROVENANCE and README templates.
- `scripts/tex2svg.mjs` — build a `window.MATH` module of baseline-aligned SVG formulas
  from a JSON map of TeX strings (needs `mathjax-full@3`).

---

## Part 2 — references/build-patterns.md

*Build patterns for method explainers (HyperFrames + GSAP)*

Each pattern below is seek-safe (any frame renders from its time alone) and passes
`npx hyperframes check`. They assume one standalone composition with one paused timeline,
as described in `/hyperframes-core`. Read the matching HyperFrames reference when a
pattern touches its area.

### Contents

1. Beat clock and seek-safe helper
2. Clip-path rect morphs (tokens, bars, strips)
3. Orthographic stacks (layers of a tensor)
4. Math typeset from TeX (MathJax SVG)
5. Titles: two tones, per-word masked arrival, binary visibility
6. Count-ups and figures
7. Deterministic atmosphere: seeded particle field
8. Local spark canvases (check-friendly)
9. Light trace along a connector
10. Handoff rules

---

### 1. Beat clock and seek-safe helper

```js
const T1 = 0, T2 = 6.0, T3 = 8.8, T4 = 14.2, T5 = 20.6, T6 = 24.0, T7 = 28.7, END = 32.9;
// root: data-duration must equal END

const tl = gsap.timeline({ paused: true });
const to = (target, from, end, at, dur, ease = "power3.inOut") =>
  tl.fromTo(target, from, Object.assign({}, end, { duration: dur, ease, immediateRender: false }), at);
const fadeIn  = (t, at, d = 0.4, e = "sine.inOut") => to(t, { opacity: 0 }, { opacity: 1 }, at, d, e);
const leave   = (t, at, d = 0.32) => to(t, { opacity: 1 }, { opacity: 0 }, at, d, "power2.in");
const arrive  = (t, at, d = 0.7, dy = 16) => to(t, { opacity: 0, y: dy }, { opacity: 1, y: 0 }, at, d, "expo.out");

// initial states at t = 0 (never a page-load gsap.set)
tl.set(el, { x: 0, y: 0, scale: 1, transformOrigin: "50% 50%" }, 0);

// ... build every beat with T-relative times ...
window.__timelines["main"] = tl; // register last
```

Why: inserting a second into beat 3 is `T4..END += 1` plus `data-duration`. Chained
`fromTo` tweens whose `from` equals the previous `to` stay consistent under forward and
backward seeks.

### 2. Clip-path rect morphs

A full-frame layer whose visible area is a rounded rectangle. Morphing between any two
rectangles is a paint-only tween with exact corner radii (no width/height tweens, which
`/hyperframes-animation` forbids).

```js
const W = 1920, H = 1080;
const R = (x, y, w, h, r) => ({ x, y, w, h, r });
const clip = (q) => `inset(${q.y}px ${W - q.x - q.w}px ${H - q.y - q.h}px ${q.x}px round ${q.r}px)`;
const shrink = (q, d) => R(q.x + d, q.y + d, Math.max(0, q.w - 2 * d), Math.max(0, q.h - 2 * d), Math.max(0, q.r - d));

// a token = wrapper (for opacity / pop scale) + face (colour) + veil (masked state)
const wrap = el(parent, "layer", "opacity:0");
const face = el(wrap, "layer", `background:${colour}`);
const veil = el(wrap, "layer", "background:#101417;opacity:0"); // inset ring = "masked"
tl.set(face, { clipPath: clip(A) }, 0);
tl.set(veil, { clipPath: clip(shrink(A, 4)) }, 0);

const move = (a, b, at, d) => {
  to(face, { clipPath: clip(a) }, { clipPath: clip(b) }, at, d);
  to(veil, { clipPath: clip(shrink(a, 4)) }, { clipPath: clip(shrink(b, 4)) }, at, d);
};
// pop around the token's centre without touching its clip
to(wrap, { scale: 1.14, transformOrigin: `${b.x + b.w / 2}px ${b.y + b.h / 2}px` }, { scale: 1 }, at, 0.26, "back.out(2)");
```

A signed bar grows from a zero line by morphing `R(zero, y, 0, h, r)` →
`R(v >= 0 ? zero : zero - w, y, w, h, r)`; the same layer can later morph into a strip
segment or a tile footprint while its `backgroundColor` tweens.

### 3. Orthographic stacks

For "a tensor = layers" (channels, time steps, heads). GSAP composes `rotation` before
`rotationX` in one element, which gives the wrong shape, so nest three elements:

```js
const pos  = el(stack, "abs", `width:${S}px;height:${S}px;z-index:${20 - i}`); // top layer paints last
const tilt = el(pos, "layer");
const spin = el(tilt, "layer plate");           // the visible card (image, grid, outline)
tl.set(pos,  { x: cx - S / 2, y: cy(i) - S / 2, scale: 1, transformOrigin: "50% 50%" }, 0);
tl.set(tilt, { rotationX: 58, transformOrigin: "50% 50%" }, 0);
tl.set(spin, { rotation: 45, transformOrigin: "50% 50%" }, 0);

// exact screen position of a local point (u, v) — no perspective, so this is closed form
const proj = (u, v, i) => {
  const a = u - S / 2, b = v - S / 2, r = Math.SQRT1_2, k = Math.cos((58 * Math.PI) / 180);
  return { x: cx + (a - b) * r, y: cy(i) + (a + b) * r * k };
};
```

Draw outlines of one cell on every layer, and a dashed column through them, in an SVG
overlay above the stack using `proj` — they stay visible even where upper layers cover
lower ones. Flatten a stack (or a merged layer) by tweening `rotationX → 0`,
`rotation → 0` and `scale` together; compensate corner radius by `r_visual / scale`.

Use the same projection at the start (inputs) and at the end (an aggregation over the
stacked axis) so the film rhymes.

### 4. Math typeset from TeX

Build once with `scripts/tex2svg.mjs`; each formula becomes self-contained SVG paths, so
the render needs no math font.

```js
const MATH_SCALE = 1.12; // Computer Modern x-height vs a modern sans; tune per text face
const math = (key, px) => {
  const m = window.MATH[key], em = px * MATH_SCALE, [, y, w, h] = m.vb;
  return m.svg.replace("<svg ",
    `<svg width="${(w / 1000 * em).toFixed(2)}" height="${(h / 1000 * em).toFixed(2)}" ` +
    `style="vertical-align:${(-(h + y) / 1000 * em).toFixed(2)}px" `);
};
label.innerHTML = `Masked at ${math("g", 28)}`;
```

TeX conventions to keep: upright capital Greek (`\Phi`), italic variables, `\Delta f`,
subscripts via `c_1`, `\;` spacing around arrows. Use `currentColor` (MathJax default) so
the formula takes the label's colour.

### 5. Titles

```js
// build: one block per line, one masked span per word, tone per sentence
box.innerHTML = lines.map((line) => "<div>" + line.map(([text, tone]) =>
  text.split(" ").map((w) => `<span class="wm"><span class="wi ${tone}">${w}</span></span>`).join(" ")
).join(" ") + "</div>").join("");
// .wm { display:inline-block; overflow:hidden; vertical-align:top; padding:0 .04em .04em 0 }

const words = box.querySelectorAll(".wi");
tl.set(words, { yPercent: 118, opacity: 0 }, 0);
const titleIn = (at) => { tl.set(words, { opacity: 1 }, at);
  to(words, { yPercent: 118 }, { yPercent: 0, stagger: 0.065 }, at, 0.9, "expo.out"); };
const titleOut = (at) => { to(words, { yPercent: 0 }, { yPercent: -118, stagger: 0.02 }, at, 0.34, "power3.in");
  tl.set(words, { opacity: 0 }, at + 0.35 + 0.02 * words.length); };
```

Binary visibility around the masked whip stops the layout audit from reporting parked
words as occluded. Use block lines instead of `<br>`.

### 6. Count-ups and figures

```css
.fig { font-variant-numeric: tabular-nums lining-nums; font-feature-settings: "tnum" 1, "lnum" 1; }
```
```js
const fmt = (v, d) => (v < 0 ? "−" : "+") + Math.abs(v).toFixed(d); // true minus
const countUp = (node, value, d, at, dur) => { const s = { v: 0 };
  to(s, { v: 0 }, { v: value, onUpdate: () => (node.textContent = fmt(s.v, d)) }, at, dur, "power2.out"); };
```

Right-align value columns so decimals line up. Hold final values ≥ 1 s before anything
moves them.

### 7. Seeded particle field

```js
let seed = 163;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
const P = Array.from({ length: 90 }, () => ({ x: rnd() * W, y: rnd() * H, vx: (rnd() - .5) * 14,
  vy: -3 - rnd() * 9, r: .7 + rnd() * 1.7, a: .08 + rnd() * .32, f: .25 + rnd() * .7, p: rnd() * 6.283 }));
const draw = (t) => { ctx.clearRect(0, 0, W, H);
  for (const q of P) { const x = ((q.x + q.vx * t) % (W + 40) + W + 40) % (W + 40) - 20;
    const y = ((q.y + q.vy * t) % (H + 40) + H + 40) % (H + 40) - 20;
    ctx.globalAlpha = q.a * (.55 + .45 * Math.sin(q.p + t * q.f * 6.283));
    ctx.beginPath(); ctx.arc(x, y, q.r, 0, 6.283); ctx.fill(); } ctx.globalAlpha = 1; };
const clock = { t: 0 };
to(clock, { t: 0 }, { t: END, onUpdate: () => draw(clock.t) }, 0, END, "none");
draw(0);
```

Put the field canvas behind content with `data-layout-ignore` and `pointer-events:none`.

### 8. Local spark canvases

The layout audit treats every `<canvas>` as opaque, so a full-frame FX canvas over text
fails `check`. Give each burst site its own small canvas, visible only during its window:

```js
const pad = (id, x, y, w, h) => { const c = document.createElement("canvas");
  c.width = w; c.height = h; c.className = "abs";
  c.style.cssText = `left:${x}px;top:${y}px;pointer-events:none;opacity:0`;
  c.setAttribute("data-layout-ignore", ""); host.appendChild(c);
  PADS[id] = { c, ctx: c.getContext("2d"), x, y, w, h }; };
const hash = (a, b) => { const v = Math.sin(a * 12.9898 + b * 78.233) * 43758.5453; return v - Math.floor(v); };
// burst(pad, t0, x, y, colour, n, speed, life) → drawn each frame from the same clock as §7:
// angle_i = 2πi/n + jitter(hash), distance = speed·life·(1−(1−e)²)/2, gravity 46·e², alpha (1−e)^1.5
tl.set(PADS.mask.c, { opacity: 1 }, t0 - 0.02);
tl.set(PADS.mask.c, { opacity: 0 }, t0 + life + 0.02);
```

Colour sparks by meaning (e.g. the sign of a measured change), never by decoration.

### 9. Light trace along a connector

```js
// .comet { width:160px; height:6px; border-radius:3px;
//          background:linear-gradient(90deg, transparent, #ffc48c); box-shadow:0 0 18px 3px rgba(255,138,36,.55) }
const drawConnector = (line, head, len, at, dur) => {
  to(line, { strokeDashoffset: len }, { strokeDashoffset: 0 }, at, dur, "power2.inOut");
  to(head, { opacity: 0 }, { opacity: 1 }, at + dur - 0.06, 0.1, "none");
  to(comet, { x: x1 - 160, y: y - 3 }, { x: x2 - 140, y: y - 3 }, at, dur + 0.15, "power2.inOut");
  to(comet, { opacity: 0 }, { opacity: 1 }, at, (dur + .15) * .25, "none");
  to(comet, { opacity: 1 }, { opacity: 0 }, at + (dur + .15) * .7, (dur + .15) * .3, "none");
};
```

Only on connectors that name a start and an end (input → model → target).

### 10. Handoff rules

- Prefer **one element changing role** over two elements crossfading.
- If a swap is unavoidable, the incoming element must be **above** the outgoing one in
  paint order, identical in geometry and radius at the swap frame, and fully opaque before
  the outgoing one is hidden.
- When N objects aggregate into one (a sum, a merge), let them converge onto the position
  of the result, reveal the result **on the same transformed layer**, then animate that
  layer to its final pose.
- Sequence regions: start the next region's animation only after moving objects have left
  it.

---

## Part 3 — references/review-and-delivery.md

*Review and delivery*

### Commands (from the project folder)

```bash
# environment
npx hyperframes doctor --json | jq -e '.ok'             # ok=false is fine if only optional tools are missing
export HYPERFRAMES_BROWSER_PATH=/path/to/chrome-headless-shell   # when `browser ensure` cannot download

# fast loop
npx hyperframes lint
npx hyperframes check                                    # gate: 0 errors; read warnings
npx hyperframes snapshot --at 5.6,8.4,13.6,17.5          # settled frames + transition frames → contact-sheet.jpg

# renders
npx hyperframes render --quality draft --fps 30 --output review.mp4      # direction review
npx hyperframes render --quality looks --fps 60 --output film_vN.mp4     # full review cut
npx hyperframes render --quality delivery --fps 60 --output film_final.mp4

# verify an encode
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate,nb_frames -of compact film_vN.mp4
```

Long renders: start them in the background and poll the log for `Render complete`; a
render that dies with its parent process leaves nothing behind.

### Decoded-frame grid (look at the pixels you shipped)

```bash
i=0; for t in 9.9 12.6 16.2 27.4; do
  ffmpeg -v error -y -ss $t -i film_vN.mp4 -frames:v 1 -vf scale=800:-1 f$i.png; i=$((i+1)); done
ffmpeg -v error -y -i f0.png -i f1.png -i f2.png -i f3.png \
  -filter_complex "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack" grid.png
```

Pick times at the moments that changed in this version, plus one settled frame per beat.

### Reading `check` output

| Finding | Usual meaning | Action |
|---|---|---|
| `text_occluded` naming a `<canvas>` | the audit treats canvases as opaque | shrink the canvas to its burst area and show it only in its window |
| `text_occluded` on parked title words | words waiting outside their mask | binary `opacity` around the masked whip |
| `content_overlap` at a title change | two titles crossing mid-transition | expected (info) |
| `panel_out_of_canvas` during an entrance | an element sliding in from off-screen | expected (info) |
| contrast < 3:1 on a data-coloured number | the data hue is too dark/light for text | keep the mark's hue, use a darkened/lightened *text* variant |
| `composition_file_too_large` | single-file film with persistent objects | accept, or move non-shared layers to sub-compositions |
| `page_error` | a runtime exception (often a duplicate id) | fix first — later audits are meaningless until it is gone |

### PROVENANCE.md template

```markdown
# <Film> — data provenance and change log

## Sources
| On screen | Source | Verification |
|---|---|---|
| <values / maps> | <repo path> | <byte-identical / max abs diff 0 vs …> |
| <recovered placeholder> | <original runtime re-run, what was instrumented> | <exact agreement with …> |
| <display-only colour> | <how it was derived> | display only |

## Display choices
- <every transform that changes appearance but not values>

## vN — <one-line summary>
- <what changed and why; new beat clock if timings moved>
```

### README.md template (ships in the project zip)

1. One-paragraph summary + spec table (size, fps, frames, duration, audio, data source,
   run parameters, tool versions).
2. Archive contents (tree with one line per file).
3. Story structure — beat table: time, title, what is shown, what is learned.
4. Object continuity — each persistent object and its roles.
5. Visual system — design spec, data vs accent palettes, typography voices, layout grid,
   effect → meaning table.
6. Technical architecture — composition/timeline, beat clock, seek-safe helper, morph
   technique, stacks, deterministic FX, check-friendly construction.
7. Data and provenance (short table; point to PROVENANCE.md).
8. Rebuilding — data scripts, check/snapshot/render commands, environment notes,
   expected render time.
9. State at delivery (check result) and version history.

---

## Part 4 — scripts/tex2svg.js

```js
#!/usr/bin/env node
// Typeset TeX formulas into self-contained SVG for a HyperFrames composition.
//
//   npm install mathjax-full@3
//   node tex2svg.js formulas.json data/math.js [GLOBAL]
//
// formulas.json:  { "phi": "\\Phi(g,c)", "dfx": "\\Delta f", "g": "g" }
// output:         window.MATH = { phi: { tex, svg, vb: [x, y, w, h] }, ... }
//
// fontCache "none" inlines every glyph path, so the render needs no math font.
// MathJax's ex-based width/height/style are stripped; size each formula in px from the
// viewBox (1000 units = 1 em; y is minus the ascent, so depth = h + y). See the `math()`
// helper in references/build-patterns.md for baseline-aligned inline use.
"use strict";
const fs = require("fs");
const { mathjax } = require("mathjax-full/js/mathjax.js");
const { TeX } = require("mathjax-full/js/input/tex.js");
const { SVG } = require("mathjax-full/js/output/svg.js");
const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");
const { AllPackages } = require("mathjax-full/js/input/tex/AllPackages.js");

const [, , inFile, outFile, globalName = "MATH"] = process.argv;
if (!inFile || !outFile) {
  console.error("usage: node tex2svg.js formulas.json out.js [GLOBAL]");
  process.exit(2);
}
const formulas = JSON.parse(fs.readFileSync(inFile, "utf8"));

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const doc = mathjax.document("", {
  InputJax: new TeX({ packages: AllPackages }),
  OutputJax: new SVG({ fontCache: "none" }),
});

const out = {};
for (const [key, tex] of Object.entries(formulas)) {
  const node = doc.convert(tex, { display: false });
  let svg = adaptor.innerHTML(node);
  const m = svg.match(/viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"/);
  if (!m) throw new Error(`no viewBox for ${key}`);
  if (/data-mjx-error|merror/.test(svg)) throw new Error(`TeX error in ${key}: ${tex}`);
  svg = svg
    .replace(/ width="[^"]*"/, "")
    .replace(/ height="[^"]*"/, "")
    .replace(/ style="[^"]*"/, "")
    .replace(/ role="img"/, "")
    .replace(/ focusable="false"/, "");
  out[key] = { tex, svg, vb: m.slice(1).map(Number) };
  console.log(key.padEnd(10), tex.padEnd(28), "viewBox", out[key].vb.join(" "));
}
fs.writeFileSync(outFile, `window.${globalName} = ${JSON.stringify(out)};\n`);
console.log(`wrote ${Object.keys(out).length} formulas → ${outFile}`);
```
