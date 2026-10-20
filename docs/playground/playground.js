"use strict";

/* SSI in the browser: real ONNX model, original normalized image, fixed ROI,
 * observed-context per-cell Shapley. No prerecorded attribution maps.
 * The JS sampler uses its own seeded RNG, so finite-K permutations need not
 * match the NumPy RNG for the same seed. Exact method definition matches SSI.
 */

const $ = (name) => document.getElementById(name);
const BANDS = ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"];
const ASSETS = "./assets/";
const ROOT_SOURCE = "https://github.com/AtheavenMa/Spectral-Spatial-Interpretation";

const state = {
  model: null, x: null, mask: null, meta: null, roi: [], image: $("input"),
  grid: 4, baseline: "mean", permutations: 1, seed: 0, band: -1,
  selectedCell: null, scope: "whole", result: null, running: false,
  generation: 0, cache: new Map(),
};

function setStatus(message, failure = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", failure);
}

function progress(message) { $("progress").textContent = message; }

function updateControls() {
  for (const button of $("gridControls").querySelectorAll("button")) {
    const selected = +button.dataset.grid === state.grid;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  }
  for (const button of $("baselineControls").querySelectorAll("button")) {
    const selected = button.dataset.baseline === state.baseline;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  }
  $("permutations").value = String(state.permutations);
  $("seed").value = String(state.seed);
}

function queryState() {
  const params = new URLSearchParams({
    grid: String(state.grid), baseline: state.baseline,
    k: String(state.permutations), seed: String(state.seed),
    band: String(state.band),
  });
  history.replaceState(null, "", location.pathname + "?" + params.toString());
}

function restoreQuery() {
  const query = new URLSearchParams(location.search);
  const g = Number(query.get("grid"));
  if ([4, 8, 16].includes(g)) state.grid = g;
  const baseline = query.get("baseline");
  if (["mean", "zero"].includes(baseline)) state.baseline = baseline;
  const k = +query.get("k");
  if ([1, 2, 3].includes(k)) state.permutations = k;
  const seed = +query.get("seed");
  if (query.has("seed") && Number.isInteger(seed) && seed >= 0 && seed <= 100000) state.seed = seed;
  const band = Number(query.get("band"));
  if (query.has("band") && Number.isInteger(band) && band >= -1 && band < 6) state.band = band;
  // 16x16 is an advanced, slower option. Every setting remains an actual run.
  updateControls();
}

function invalidate() {
  state.generation++;
  state.result = null;
  state.selectedCell = null;
  state.scope = "whole";
  $("empty").classList.remove("hidden");
  $("bandGrid").replaceChildren();
  $("bars").replaceChildren();
  $("stats").textContent = "";
  $("save").disabled = true;
  $("copy").disabled = true;
  $("spatialTitle").textContent = "(c) Spatial SSI";
  $("scale").textContent = "";
  $("scope").textContent = "WHOLE IMAGE";
  if (state.running) setStatus("Current computation is stopping after the active batch.");
  else if (state.model) setStatus("Ready. Run SSI with these parameters.");
  queryState();
}

function key() {
  return [state.grid, state.baseline, state.permutations, state.seed].join("|");
}

async function fetchBytes(name) {
  const r = await fetch(ASSETS + name, {cache: "force-cache"});
  if (!r.ok) throw new Error("Could not load " + name + " (HTTP " + r.status + ")");
  return r.arrayBuffer();
}

function waitFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 0)));
}

function paintTarget() {
  const c = $("groundTruth");
  const temp = document.createElement("canvas");
  temp.width = state.meta.width;
  temp.height = state.meta.height;
  const ctx = temp.getContext("2d");
  const rgba = ctx.createImageData(temp.width, temp.height);
  for (let i = 0; i < state.mask.length; i++) {
    const label = state.mask[i];
    const rgb = label === 1 ? [187, 66, 73] : label === 255 ?
      [192, 198, 201] : [245, 246, 245];
    rgba.data.set([...rgb, 255], i * 4);
  }
  ctx.putImageData(rgba, 0, 0);
  const dest = c.getContext("2d");
  dest.imageSmoothingEnabled = false;
  dest.drawImage(temp, 0, 0, c.width, c.height);
}

function targetRegionObject() {
  return {
    width: state.meta.width, height: state.meta.height,
    data: Uint8Array.from(state.mask, (v) => v === 1 ? 1 : 0),
  };
}

async function initialize() {
  restoreQuery();
  setStatus("Loading the original HLS image, model and input…");
  if (!window.ort || !window.SSIAtlas) {
    setStatus("The browser inference library could not load. Check your internet connection.", true);
    return;
  }
  try {
    const [metaR, inputB, maskB] = await Promise.all([
      fetch(ASSETS + "hls_meta.json"),
      fetchBytes("hls_input.f32"),
      fetchBytes("hls_mask.u8"),
    ]);
    if (!metaR.ok) throw new Error("Could not load real model metadata.");
    const meta = await metaR.json();
    if (meta.version !== 1 || meta.width !== 128 || meta.height !== 128 ||
        meta.channels.join() !== BANDS.join())
      throw new Error("Unexpected asset schema or channel order.");
    const pixels = meta.width * meta.height;
    const input = new Float32Array(inputB);
    const mask = new Uint8Array(maskB);
    if (input.length !== 6 * pixels || mask.length !== pixels ||
        !input.every(Number.isFinite))
      throw new Error("The bundled model input has an unexpected shape.");

    state.meta = meta; state.x = input; state.mask = mask;
    state.roi = Array.from(mask.keys()).filter((i) => mask[i] === 1);
    if (!state.roi.length || state.roi.length !== meta.region_pixels)
      throw new Error("The fixed target region does not match the exported model.");
    state.image.src = ASSETS + "hls_rgb.webp";
    await state.image.decode();
    paintTarget();

    setStatus("Initializing browser CPU inference…");
    ort.env.wasm.wasmPaths = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.21.0/dist/";
    ort.env.wasm.numThreads = 1;
    const modelBytes = await fetchBytes("hls_unet.onnx");
    state.model = await ort.InferenceSession.create(modelBytes, {
      executionProviders: ["wasm"],
      graphOptimizationLevel: "all",
    });
    setStatus("Model ready. Computing real SSI…");
    await run();
  } catch (error) {
    setStatus("Could not start the real model: " + error.message, true);
    progress("SEE SOURCE CODE FOR LOCAL PYTHON ALTERNATIVE");
    $("run").disabled = true;
    console.error(error);
  }
}

function seededPermutation(rng) {
  const order = [0, 1, 2, 3, 4, 5];
  for (let j = order.length - 1; j > 0; j--) {
    const index = Math.floor(rng() * (j + 1));
    [order[j], order[index]] = [order[index], order[j]];
  }
  return order;
}

function rngFromSeed(seed) {
  // Small deterministic xorshift32. Independent of NumPy's default generator.
  let x = ((seed | 0) ^ 0x9e3779b9) >>> 0;
  if (!x) x = 0xa541316c;
  return () => {
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    return (x >>> 0) / 4294967296;
  };
}

function makeBatch(bitMasks, cell, config) {
  const {width, height} = state.meta;
  const plane = width * height;
  const grid = config.grid;
  const cellWidth = width / grid, cellHeight = height / grid;
  const col = cell % grid, row = Math.floor(cell / grid);
  const x0 = col * cellWidth, y0 = row * cellHeight;
  const values = config.baseline === "mean" ?
    state.meta.baseline_mean : state.meta.baseline_zero;
  const B = bitMasks.length;
  const input = new Float32Array(B * 6 * plane);
  for (let k = 0; k < B; k++) {
    const sample = input.subarray(k * 6 * plane, (k + 1) * 6 * plane);
    sample.set(state.x);
    const maskBits = bitMasks[k];
    for (let channel = 0; channel < 6; channel++) {
      if (maskBits & (1 << channel)) continue;
      const start = channel * plane;
      for (let y = y0; y < y0 + cellHeight; y++) {
        sample.fill(values[channel], start + y * width + x0,
                    start + y * width + x0 + cellWidth);
      }
    }
  }
  return input;
}

async function scoreBatch(inputs, count) {
  const {width, height} = state.meta;
  const tensor = new ort.Tensor("float32", inputs, [count, 6, height, width]);
  const outputs = await state.model.run({image: tensor});
  const logits = outputs.logits ?? outputs[state.model.outputNames[0]];
  if (!logits || logits.dims[0] !== count || logits.dims[1] !== 2)
    throw new Error("The ONNX model returned an unexpected output.");
  const plane = width * height;
  const values = [];
  for (let n = 0; n < count; n++) {
    let sum = 0;
    const start = (2 * n + 1) * plane;
    for (const index of state.roi) sum += logits.data[start + index];
    values.push(sum / state.roi.length);
  }
  return values;
}

async function compute(config, runId) {
  const cells = config.grid * config.grid;
  const channels = 6;
  const all = (1 << channels) - 1;
  const rng = rngFromSeed(config.seed);
  const result = {
    model_id: "hls-unet", sample_id: "hls-burn-scar",
    grid: config.grid, baseline: config.baseline,
    method: "permutation", permutations: config.permutations, seed: config.seed,
    channels: BANDS,
    attribution: Array.from({length: config.grid}, () =>
      Array.from({length: config.grid}, () => new Array(channels).fill(0))),
    spatial: Array.from({length: config.grid}, () => new Array(config.grid).fill(0)),
    spectral: new Array(channels).fill(0),
    full_value: 0, n_evaluations: 0, local_efficiency_error: 0,
    provenance: {
      checkpoint_sha256: state.meta.original_checkpoint_sha256,
      sample_sha256: state.meta.original_sample_sha256,
      target: state.meta.target,
      browser_model_format: "ONNX",
      algorithm: "SSI observed-context permutation Shapley",
      sampler: "xorshift32 and Fisher-Yates; NumPy uses a different seeded order",
    },
  };
  const original = await scoreBatch(state.x.slice(), 1);
  result.full_value = original[0];
  result.n_evaluations++;
  if (Math.abs(original[0] - state.meta.onnx_full_score) > 0.02)
    throw new Error("The loaded model does not match the recorded unmasked score.");

  for (let g = 0; g < cells; g++) {
    if (runId !== state.generation) return null;
    const orders = [];
    const needed = new Set([0]);
    for (let k = 0; k < config.permutations; k++) {
      const order = seededPermutation(rng);
      orders.push(order);
      let bits = 0;
      needed.add(bits);
      for (const ch of order) {bits |= 1 << ch; needed.add(bits);}
    }
    const scores = new Map([[all, original[0]]]);
    const queue = [...needed].filter(bits => bits !== all).sort((a, b) => a - b);
    for (let j = 0; j < queue.length; j += 8) {
      if (runId !== state.generation) return null;
      const group = queue.slice(j, j + 8);
      const input = makeBatch(group, g, config);
      const resultScores = await scoreBatch(input, group.length);
      for (let n = 0; n < group.length; n++) scores.set(group[n], resultScores[n]);
      result.n_evaluations += group.length;
    }
    const row = Math.floor(g / config.grid), col = g % config.grid;
    let cellTotal = 0;
    for (const order of orders) {
      let bits = 0;
      for (const channel of order) {
        const next = bits | (1 << channel);
        const marginal = (scores.get(next) - scores.get(bits)) / config.permutations;
        result.attribution[row][col][channel] += marginal;
        cellTotal += marginal;
        bits = next;
      }
    }
    result.spatial[row][col] = cellTotal;
    for (let channel = 0; channel < channels; channel++) {
      result.spectral[channel] += result.attribution[row][col][channel];
    }
    result.local_efficiency_error = Math.max(
      result.local_efficiency_error,
      Math.abs(cellTotal - (original[0] - scores.get(0)))
    );
    progress("CELL " + (g + 1) + " / " + cells + " · " +
             result.n_evaluations + " MODEL SCORES");
    if (g % 2 === 0) {
      setStatus("Computing real SSI · cell " + (g + 1) + " of " + cells);
      await waitFrame();
    }
  }
  return result;
}

async function run() {
  if (!state.model || state.running) return;
  const params = {
    grid: state.grid, baseline: state.baseline,
    permutations: state.permutations, seed: state.seed,
  };
  if (state.cache.has(key())) {
    state.result = state.cache.get(key());
    renderResult();
    setStatus("Computed from this browser session's numerical cache.");
    return;
  }
  state.running = true;
  $("run").disabled = true;
  $("stop").hidden = false;
  const generation = ++state.generation;
  setStatus("Computing real SSI from the bundled checkpoint…");
  try {
    const explanation = await compute(params, generation);
    if (explanation && generation === state.generation) {
      state.cache.set([params.grid,params.baseline,params.permutations,params.seed].join("|"), explanation);
      state.result = explanation;
      renderResult();
      setStatus("Computed. Change a parameter to explore another explanation.");
      progress(explanation.n_evaluations + " MODEL SCORES · REAL INFERENCE");
    }
  } catch (error) {
    if (generation === state.generation) {
      setStatus("The model could not compute this setting: " + error.message, true);
      progress("NO RESULT WAS SUBSTITUTED");
      console.error(error);
    }
  } finally {
    state.running = false;
    $("run").disabled = false;
    $("stop").hidden = true;
  }
}

function matrix(channel) {
  if (channel === -1) return state.result.spatial;
  return state.result.attribution.map(row => row.map(cell => cell[channel]));
}

function scale(channel) {
  if (channel === -1) return SSIAtlas.signedLimit(state.result.spatial);
  let largest = 1e-12;
  for (const row of state.result.attribution)
    for (const cell of row)
      for (const value of cell) largest = Math.max(largest, Math.abs(value));
  return largest;
}

function opacity() { return Number($("opacity").value) / 100; }

function paintSpatial() {
  if (!state.result) return;
  const limit = scale(state.band);
  SSIAtlas.paint($("spatial"), state.image, matrix(state.band), limit,
                 opacity(), targetRegionObject(), state.selectedCell);
  $("spatialTitle").textContent = state.band === -1 ?
    "(c) Spatial SSI" : "(c) " + BANDS[state.band] + " SSI";
  $("scale").textContent = "SHARED SIGNED SCALE · ±" + limit.toPrecision(3);
}

function renderBands() {
  const container = $("bandGrid");
  container.replaceChildren();
  if (!state.result) return;
  const max = scale(0);
  for (let i = 0; i < 6; i++) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "channel-card" + (state.band === i ? " selected" : "");
    card.setAttribute("aria-label", "View " + BANDS[i] + " SSI overlaid on image");
    card.dataset.band = String(i);
    const label = document.createElement("span");
    label.className = "channel-label";
    label.textContent = BANDS[i];
    const frame = document.createElement("span");
    frame.className = "channel-image";
    const canvas = document.createElement("canvas");
    canvas.width = 320; canvas.height = 320;
    frame.appendChild(canvas);
    const number = document.createElement("span");
    number.className = "channel-magnitude " +
      (state.result.spectral[i] >= 0 ? "positive" : "negative");
    number.textContent = (state.result.spectral[i] >= 0 ? "+" : "") +
      state.result.spectral[i].toFixed(3);
    card.append(label, frame, number);
    card.addEventListener("click", () => {
      state.band = state.band === i ? -1 : i;
      paintSpatial();
      renderBands();
      queryState();
    });
    container.appendChild(card);
    SSIAtlas.paint(canvas, state.image, matrix(i), max, opacity(), targetRegionObject(), null);
  }
}

function renderBars() {
  const container = $("bars");
  container.replaceChildren();
  if (!state.result) return;
  const local = state.scope === "cell" && state.selectedCell;
  const values = local ?
    state.result.attribution[state.selectedCell.y][state.selectedCell.x] :
    state.result.spectral;
  const max = Math.max(1e-10, ...values.map(Math.abs));
  for (let i = 0; i < 6; i++) {
    const val = values[i];
    const line = document.createElement("div"); line.className = "bar";
    const label = document.createElement("label"); label.textContent = BANDS[i];
    const bar = document.createElement("div"); bar.className = "track";
    const fill = document.createElement("span"); fill.className = "fill";
    const pct = 50 * Math.abs(val) / max;
    fill.style.left = (val >= 0 ? 50 : 50 - pct) + "%";
    fill.style.width = pct + "%";
    fill.style.backgroundColor = val >= 0 ? "#bd474d" : "#347ba3";
    const number = document.createElement("span"); number.className = "number-value";
    number.textContent = (val >= 0 ? "+" : "") + val.toFixed(3);
    bar.append(fill);line.append(label,bar,number);container.append(line);
  }
  $("scope").textContent = local ?
    "ROW " + (state.selectedCell.y + 1) + " · COL " + (state.selectedCell.x + 1) : "WHOLE IMAGE";
  $("cellInfo").textContent = local ?
    "Selected spatial cell · six signed spectral contributions." :
    "Click the SSI image above to inspect a spatial cell.";
  $("whole").classList.toggle("selected",!local);
  $("selected").classList.toggle("selected",!!local);
}

function renderResult() {
  if (!state.result) return;
  $("empty").classList.add("hidden");
  paintSpatial();
  renderBands();
  renderBars();
  $("stats").textContent = state.result.n_evaluations + " MODEL SCORES · " +
    "LOCAL EFFICIENCY ERROR " + state.result.local_efficiency_error.toExponential(1);
  $("save").disabled = false;
  $("copy").disabled = false;
  queryState();
}

function selectCell(event) {
  if (!state.result) return;
  const rect = $("spatial").getBoundingClientRect();
  state.selectedCell = {
    x: Math.max(0, Math.min(state.grid - 1, Math.floor((event.clientX - rect.left) * state.grid / rect.width))),
    y: Math.max(0, Math.min(state.grid - 1, Math.floor((event.clientY - rect.top) * state.grid / rect.height))),
  };
  state.scope = "cell";
  paintSpatial();renderBars();
}

function setup() {
  for (const button of $("gridControls").querySelectorAll("button")) {
    button.addEventListener("click", () => {
      state.grid = Number(button.dataset.grid);
      updateControls();invalidate();
    });
  }
  for (const button of $("baselineControls").querySelectorAll("button")) {
    button.addEventListener("click", () => {
      state.baseline = button.dataset.baseline;
      updateControls();invalidate();
    });
  }
  $("permutations").addEventListener("change", () => {
    state.permutations = Number($("permutations").value);invalidate();
  });
  $("seed").addEventListener("input", () => {
    const value = Number($("seed").value);
    if (!Number.isInteger(value) || value < 0 || value > 100000) return;
    state.seed = value;invalidate();
  });
  $("opacity").addEventListener("input", () => {
    if (state.result) {paintSpatial();renderBands();}
  });
  $("run").addEventListener("click", run);
  $("stop").addEventListener("click", () => {
    state.generation++;
    setStatus("Stopping after the current model batch…");
    invalidate();
  });
  $("spatial").addEventListener("click", selectCell);
  $("spatial").addEventListener("keydown", event => {
    if (!state.result) return;
    const delta = {
      ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1],
    }[event.key];
    if (!delta) return;
    event.preventDefault();
    if (!state.selectedCell) state.selectedCell={x:0,y:0};
    state.selectedCell = {
      x: Math.max(0, Math.min(state.grid-1, state.selectedCell.x + delta[0])),
      y: Math.max(0, Math.min(state.grid-1, state.selectedCell.y + delta[1])),
    };
    state.scope = "cell";paintSpatial();renderBars();
  });
  $("whole").addEventListener("click", () => {
    state.scope="whole";renderBars();
  });
  $("selected").addEventListener("click", () => {
    if (!state.selectedCell) state.selectedCell={x:0,y:0};
    state.scope="cell";paintSpatial();renderBars();
  });
  $("save").addEventListener("click", () => {
    if (!state.result) return;
    const text = JSON.stringify(state.result, null, 2);
    const url = URL.createObjectURL(new Blob([text], {type:"application/json"}));
    const a=document.createElement("a");a.href=url;
    a.download="ssi_hls_"+state.result.grid+"x"+state.result.grid+"_k"+state.result.permutations+".json";
    a.click();URL.revokeObjectURL(url);
  });
  $("copy").addEventListener("click", async () => {
    if (!state.result) return;
    const r=state.result;
    const cmd="python -m lab.cli explain --model-id hls-unet --sample-id hls-burn-scar"+
      " --grid "+r.grid+" --baseline "+r.baseline+" --method permutation"+
      " --permutations "+r.permutations+" --seed "+r.seed;
    try {
      await navigator.clipboard.writeText(cmd);
      setStatus("Python reproduction command copied. Browser permutations use a different seeded RNG.");
    } catch (_) {
      setStatus(cmd);
    }
  });
}
setup();
window.addEventListener("load", initialize);
