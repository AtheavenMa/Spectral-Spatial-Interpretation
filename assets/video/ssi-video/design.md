---
name: SSI · Data Drift (dark) · Ember accent
source: hyperframes-creative/references/visual-styles.md § 5 "Data Drift — Refik Anadol"
colors:
  primary: "#0a0a0a"          # canvas (Data Drift)
  surface: "#111518"          # glass panels / cards
  on-primary: "#e3e9ec"       # Data Drift #e0e0e0, tinted toward the accent
  soft: "#8b9aa2"
  accent: "#ff8a24"           # the one accent — v4: orange (hue ~28°), between sign-positive (~5°) and SWIR1 (~36°); never on data marks
  atmosphere-indigo: "#4f46e5" # cool counter-glow only — never on data
  # science palette, unchanged from SSI_15s_Motion_Direction.md
  band-blue: "#3277C8"
  band-green: "#27986F"
  band-red: "#DA5A58"
  band-nir: "#8062B5"
  band-swir1: "#D59A3F"
  band-swir2: "#A45B45"
  sign-positive: "#EE7667"
  sign-negative: "#4D91CA"
typography:
  headline:
    fontFamily: Inter Display
    fontWeight: 300
    letterSpacing: 0.01em
  label:
    fontFamily: Inter Display
    fontWeight: 500
  overline:
    fontFamily: Inter Display
    fontWeight: 500
    letterSpacing: 0.18em
  figures:
    fontFamily: Inter Display
    fontWeight: 500
    features: [tnum, lnum]
  math:
    renderer: MathJax 3 SVG (TeX)
rounded:
  sm: 8px
  md: 20px
  lg: 28px
motion:
  energy: moderate
  easing:
    entry: "sine.inOut / expo.out"
    exit: "power2.in"
    ambient: "sine.inOut"
  duration:
    entrance: 0.8
    hold: 2.5
    transition: 1.2
  atmosphere:
    - particle-field
    - light-traces
    - radial-glow
    - grain
---

## Overview
Data Drift adapted for a scientific explainer: weightless thin headlines on near-black,
light traces along data paths, a slow particle field, ember orange as the single accent.

## Do's and Don'ts
- Do keep the six band colours and the positive/negative sign colours exactly as specified;
  they are content, not decoration.
- Do keep the accent off data marks: it is never a bar, token, tick or map colour.
- Do tie every effect to a step of the method (mask shockwave, restoration sparks, scan laser, 3D stack before the sum).
- Don't use full-screen linear gradients (banding under H.264); radial glows + grain only.
