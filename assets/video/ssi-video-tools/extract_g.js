// Instrumented run of the ORIGINAL SSI browser runtime (docs/playground/compute-runtime.js).
// The only change to the runtime source is exporting its own seeded sampler (rngFromSeed),
// so the exact permutation orders it drew for each cell can be read back.
// 1) re-runs the full explain() and compares with assets/video/hls_burnscar_0163/result.json
// 2) replays the sampler to cell g and scores each restoration step with the runtime's own
//    maskedTensor() + score(), giving the real per-step marginal changes Δf.
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const REPO = process.argv[2];
const OUT = process.argv[3];
const PG = path.join(REPO, "docs/playground");
const SAMPLE = path.join(PG, "assets/samples/HLS_BurnScars/sample_0163");
const ROW = 9, COL = 11; // 0-indexed == (row 10, column 12)

globalThis.window = globalThis;
globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 0);
const ort = require("onnxruntime-web");
ort.env.wasm.numThreads = 1;
globalThis.ort = ort;

let src = fs.readFileSync(path.join(PG, "compute-runtime.js"), "utf8");
const exportLine = "root.SSIComputeRuntime = {explain,score,validate,maskedTensor,buildPaths};";
if (!src.includes(exportLine)) throw new Error("runtime export line changed; refusing to patch");
src = src.replace(exportLine, "root.SSIComputeRuntime = {explain,score,validate,maskedTensor,buildPaths,rngFromSeed};");
vm.runInThisContext(src, { filename: "compute-runtime.js" });
const RT = globalThis.SSIComputeRuntime;

(async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(PG, "compute-manifest.json"), "utf8"));
  const model = manifest.models.find((m) => m.id === "hls-unet");
  const meta = JSON.parse(fs.readFileSync(path.join(SAMPLE, "meta.json"), "utf8"));
  const buf = fs.readFileSync(path.join(SAMPLE, "x.f32"));
  const tensor = new Float32Array(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  const mask = new Uint8Array(fs.readFileSync(path.join(SAMPLE, "mask.u8")));
  const roi = Array.from(mask.keys()).filter((i) => mask[i] === meta.target_class);
  if (roi.length !== meta.region_pixels) throw new Error("ROI size mismatch");
  const onnx = fs.readFileSync(path.join(PG, model.onnx));
  const session = await ort.InferenceSession.create(onnx, { executionProviders: ["wasm"] });
  const ctx = { session, model, sample: { id: meta.sample_id }, meta, tensor, roi };
  const cfg = { grid: 16, baseline: "mean", permutations: 5, seed: 0 };

  // ---- 1. full re-run of the original explain() ----
  const t0 = Date.now();
  const res = await RT.explain(ctx, cfg, {});
  const ref = JSON.parse(fs.readFileSync(path.join(REPO, "assets/video/hls_burnscar_0163/result.json"), "utf8"));
  let maxDiff = 0;
  for (let r = 0; r < 16; r++) for (let c = 0; c < 16; c++) for (let b = 0; b < 6; b++)
    maxDiff = Math.max(maxDiff, Math.abs(res.attribution[r][c][b] - ref.attribution[r][c][b]));

  // ---- 2. replay the sampler to cell g ----
  const rng = RT.rngFromSeed(cfg.seed);
  const gIndex = ROW * 16 + COL;
  let paths = null;
  for (let g = 0; g <= gIndex; g++) paths = RT.buildPaths(6, cfg.permutations, rng).paths;
  const keyToBits = (k) => Uint8Array.from(k.split(""), Number);
  const unique = [...new Set(paths.flatMap((p) => p.keys))];
  const scores = new Map();
  const allKey = "111111";
  const fullScore = (await RT.score(ctx, tensor.slice(), 1))[0];
  scores.set(allKey, fullScore);
  for (const k of unique) {
    if (k === allKey) continue;
    const input = RT.maskedTensor(ctx, [keyToBits(k)], gIndex, cfg);
    scores.set(k, (await RT.score(ctx, input, 1))[0]);
  }
  const orders = paths.map((p) => ({
    order: p.order, // band indices in restoration order
    steps: p.order.map((band, k) => ({ band, delta: scores.get(p.keys[k + 1]) - scores.get(p.keys[k]) })),
  }));
  const phiG = new Array(6).fill(0);
  for (const o of orders) for (const s of o.steps) phiG[s.band] += s.delta / cfg.permutations;
  let gDiff = 0;
  for (let b = 0; b < 6; b++) gDiff = Math.max(gDiff, Math.abs(phiG[b] - ref.attribution[ROW][COL][b]));

  const out = {
    sample: meta.sample_id, cell: { row1: ROW + 1, col1: COL + 1, index0: gIndex },
    channels: meta.channels,
    full_score: fullScore,
    baseline_cell_score: scores.get("000000"),
    orders,
    phi_g_reconstructed: phiG,
    phi_g_result_json: ref.attribution[ROW][COL],
    checks: {
      full_rerun_max_abs_diff_vs_result_json: maxDiff,
      full_rerun_evaluations: res.n_evaluations,
      result_json_evaluations: ref.n_evaluations,
      cell_g_max_abs_diff_vs_result_json: gDiff,
      full_rerun_seconds: (Date.now() - t0) / 1000,
    },
  };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out.checks));
  for (const o of orders)
    console.log(o.steps.map((s) => `${meta.channels[s.band]}:${s.delta >= 0 ? "+" : ""}${s.delta.toFixed(5)}`).join("  "));
})().catch((e) => { console.error(e); process.exit(1); });
