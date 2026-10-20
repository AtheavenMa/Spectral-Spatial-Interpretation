"use strict";

const $ = (id) => document.getElementById(id);
const state = {
  catalog: null,
  result: null,
  grid: 8,
  baseline: "mean",
  channel: -1,
  cell: null,
  scoreMode: "global",
  busy: false,
  ticket: 0,
  jobId: null,
  showAllBands: false,
  hadQuery: false,
  pendingModel: null,
  pendingSample: null,
  pendingChannel: null,
  previewTicket: 0,
  pendingStart: null,
  pendingCancel: Promise.resolve(),
};

function status(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}

async function api(url, options) {
  const response = await fetch(url, options);
  let data;
  try { data = await response.json(); }
  catch (_) { throw new Error("The server returned an invalid response."); }
  if (!response.ok) throw new Error(data.detail || "Request failed.");
  return data;
}

function activeChoice(container, attr, value) {
  container.querySelectorAll("button").forEach((button) => {
    const active = button.dataset[attr] === String(value);
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

// Invalidate immediately when any result-affecting control changes.
// The cancellation chain also handles a POST that has not returned its job ID.
function invalidateRun() {
  state.ticket += 1;
  const activeJob = state.jobId;
  const pendingStart = state.pendingStart;
  state.jobId = null;
  state.busy = false;
  $("run").disabled = false;
  $("cancel").hidden = true;
  $("run").textContent = "▶  Run SSI";

  const cancellation = pendingStart
    ? pendingStart.then((job) => stopJob(job.job_id), () => {})
    : activeJob ? stopJob(activeJob) : Promise.resolve();
  state.pendingCancel = Promise.all([state.pendingCancel, cancellation]).then(() => {});
  return state.pendingCancel;
}

function markChanged() {
  invalidateRun();
  state.result = null;
  state.cell = null;
  $("mapEmpty").classList.remove("hidden");
  $("runMeta").textContent = "AWAITING RUN";
  $("bars").replaceChildren();
  $("stats").textContent = "";
  $("download").disabled = true;
  $("copyCommand").disabled = true;
  if (state.catalog) {
    syncControls();
    writeQuery();
  }
  status("Ready. Click Run SSI to compute attribution.");
}

function selected() {
  return state.catalog.models.find((model) => model.id === $("model").value);
}

function renderCatalog(catalog) {
  state.catalog = catalog;
  const models = $("model");
  models.replaceChildren();
  catalog.models.forEach((model) => {
    const item = document.createElement("option");
    item.value = model.id;
    item.textContent = model.label;
    models.append(item);
  });
  if (state.pendingModel && catalog.models.some((model) => model.id === state.pendingModel))
    models.value = state.pendingModel;
  renderSamples();
  const model = selected();
  if (!state.hadQuery) {
    state.grid = model.compute.default_grid;
    state.baseline = model.compute.default_baseline;
    $("method").value = model.compute.default_method;
    $("permutations").value = String(model.compute.default_permutations);
  }
  syncControls();
}

function renderSamples() {
  const chosen = state.catalog.models.find((model) => model.id === $("model").value);
  const select = $("sample");
  select.replaceChildren();
  chosen.samples.forEach((sample) => {
    const item = document.createElement("option");
    item.value = sample.id;
    item.textContent = sample.label;
    select.append(item);
  });
  if (state.pendingSample && chosen.samples.some((sample) => sample.id === state.pendingSample))
    select.value = state.pendingSample;
}

function syncControls() {
  const model = selected();
  const cap = Number(model.compute.permutation_cap[String(state.grid)]);
  $("permutations").max = String(cap);
  if (Number($("permutations").value) > cap) $("permutations").value = String(cap);
  $("permLabel").textContent = $("permutations").value;
  $("gridOptions").querySelectorAll("button").forEach((button) => {
    button.disabled = !model.grids.includes(Number(button.dataset.grid));
  });
  activeChoice($("gridOptions"), "grid", state.grid);
  activeChoice($("baselineOptions"), "baseline", state.baseline);
  const exact = $("method").querySelector('option[value="exact"]');
  exact.disabled = model.channels.length > 6;
  if (exact.disabled && $("method").value === "exact") $("method").value = "permutation";
  const preset = $("preset");
  const current = preset.value;
  preset.replaceChildren();
  model.compute.presets.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.label;
    option.dataset.grid = String(item.grid);
    option.dataset.permutations = String(item.permutations);
    preset.append(option);
  });
  const custom = document.createElement("option");
  custom.value = "custom";
  custom.textContent = "Custom";
  preset.append(custom);
  const match = model.compute.presets.find((item) =>
    item.grid === state.grid && item.permutations === Number($("permutations").value));
  preset.value = match ? match.id : "custom";
  if (!match && current === "custom") preset.value = "custom";
}

async function loadPreview() {
  const request = ++state.previewTicket;
  const model = $("model").value;
  const sample = $("sample").value;
  const q = new URLSearchParams({model_id: model, sample_id: sample});
  const image = await api("/api/preview?" + q.toString()).catch((error) => {
    // Ignore errors from a superseded preview as well as its returned pixels.
    if (request !== state.previewTicket) return null;
    throw error;
  });
  if (!image || request !== state.previewTicket || model !== $("model").value || sample !== $("sample").value) return;
  $("inputImage").src = image.input;
  $("gtImage").src = image.ground_truth;
  $("predImage").src = image.prediction;
  if (image.summary) $("previewMeta").textContent = image.summary;
  const captions = image.captions || {};
  if (captions.input) $("inputCaption").textContent = captions.input;
  if (captions.ground_truth) $("gtCaption").textContent = captions.ground_truth;
  if (captions.prediction) $("predCaption").textContent = captions.prediction;
}

function parameters() {
  return {
    model_id: $("model").value,
    sample_id: $("sample").value,
    grid: state.grid,
    baseline: state.baseline,
    method: $("method").value,
    permutations: Number($("permutations").value),
    seed: Number($("seed").value),
  };
}

function validate(params) {
  const model = selected();
  const cap = Number(model.compute.permutation_cap[String(params.grid)]);
  if (params.method === "exact" && model.channels.length > 6)
    return "Exact enumeration is only available for models with at most 6 channels.";
  if (params.grid === 16 && params.method === "exact")
    return "Exact enumeration is available on 4×4 and 8×8 grids.";
  if (params.permutations > cap)
    return "This model allows at most " + cap + " permutations on a " + params.grid + "×" + params.grid + " grid.";
  if (!Number.isInteger(params.seed) || params.seed < 0 || params.seed > 100000)
    return "Seed must be an integer between 0 and 100000.";
  return null;
}

function writeQuery() {
  if (!state.catalog) return;
  const params = new URLSearchParams({
    model: $("model").value,
    sample: $("sample").value,
    grid: String(state.grid),
    baseline: state.baseline,
    method: $("method").value,
    permutations: $("permutations").value,
    seed: $("seed").value,
    channel: String(state.channel),
  });
  history.replaceState(null, "", location.pathname + "?" + params.toString());
}

function showResult(result) {
  state.result = result;
  state.cell = null;
  state.scoreMode = "global";
  state.showAllBands = false;
  if (state.pendingChannel === null) state.channel = -1;
  else state.channel = state.pendingChannel;
  state.pendingChannel = null;
  setScoreMode("global");
  renderChannelButtons();
  renderMap();
  renderBars();
  $("mapEmpty").classList.add("hidden");
  $("runMeta").textContent = result.grid + " × " + result.grid + " · " + result.method.toUpperCase();
  $("stats").textContent = result.n_evaluations.toLocaleString() + " evaluations · local error " + Number(result.local_efficiency_error).toExponential(1);
  $("command").textContent = result.command;
  $("download").disabled = false;
  $("copyCommand").disabled = false;
  status("Computed · " + result.grid + "×" + result.grid + " grid · " + result.channels.length + " channels");
  writeQuery();
}

async function runSSI() {
  if (state.busy) return;
  const params = parameters();
  const error = validate(params);
  if (error) { status(error, true); return; }
  const mine = ++state.ticket;
  state.busy = true;
  $("run").disabled = true;
  $("cancel").hidden = false;
  $("run").textContent = "Computing SSI…";
  status("Running the real checkpoint on CPU…");
  try {
    // A new run never overtakes a prior cancelled run, even if the old POST
    // had not returned a job ID when settings changed.
    await state.pendingCancel;
    if (mine !== state.ticket) return;
    const starting = api("/api/jobs", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(params),
    });
    state.pendingStart = starting;
    let started;
    try {
      started = await starting;
    } finally {
      if (state.pendingStart === starting) state.pendingStart = null;
    }
    if (mine !== state.ticket) {
      await stopJob(started.job_id);
      return;
    }
    state.jobId = started.job_id;
    let job;
    for (;;) {
      job = await api("/api/jobs/" + started.job_id);
      if (mine !== state.ticket) return;
      if (job.status === "running") {
        status("Running · " + Number(job.evaluations).toLocaleString() + " evaluations");
        await new Promise((resolve) => setTimeout(resolve, 400));
        continue;
      }
      break;
    }
    if (job.status === "cancelled") { status("Cancelled."); return; }
    if (job.status !== "done") throw new Error(job.error || "Run failed.");
    showResult(job.result);
  } catch (exc) {
    if (mine === state.ticket) status(exc.message, true);
  } finally {
    if (mine === state.ticket) {
      state.busy = false;
      state.jobId = null;
      $("run").disabled = false;
      $("cancel").hidden = true;
      $("run").textContent = "▶  Run SSI";
    }
  }
}

function renderChannelButtons() {
  const target = $("channels");
  target.replaceChildren();
  if (!state.result) return;
  if (state.result.channels.length > 8) {
    const spatial = document.createElement("button");
    spatial.type = "button";
    spatial.textContent = "Spatial";
    spatial.className = state.channel === -1 ? "active" : "";
    spatial.setAttribute("aria-pressed", String(state.channel === -1));
    spatial.addEventListener("click", () => {
      state.channel = -1;
      renderChannelButtons();
      renderMap();
      writeQuery();
    });
    const select = document.createElement("select");
    select.setAttribute("aria-label", "Spectral channel");
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "One channel";
    select.append(placeholder);
    const query = ($("bandSearch").value || "").trim().toLowerCase();
    state.result.channels.forEach((label, index) => {
      if (query && !label.toLowerCase().includes(query) && index !== state.channel) return;
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = label;
      select.append(option);
    });
    select.value = state.channel >= 0 ? String(state.channel) : "";
    select.addEventListener("change", () => {
      state.channel = select.value === "" ? -1 : Number(select.value);
      renderChannelButtons();
      renderMap();
      writeQuery();
    });
    target.append(spatial, select);
    return;
  }
  const choices = [{label: "Spatial", index: -1}].concat(
    state.result.channels.map((label, index) => ({label, index}))
  );
  choices.forEach((choice) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = choice.label;
    button.className = choice.index === state.channel ? "active" : "";
    button.setAttribute("aria-pressed", String(choice.index === state.channel));
    button.addEventListener("click", () => {
      state.channel = choice.index;
      renderChannelButtons();
      renderMap();
      writeQuery();
    });
    target.append(button);
  });
}

function scaleValues() {
  const r = state.result;
  if (state.channel === -1)
    return Math.max(1e-12, ...r.spatial.flat().map((n) => Math.abs(n)));
  return Math.max(1e-12, ...r.attribution.flat(2).map((n) => Math.abs(n)));
}

function ramp(value, max) {
  const t = Math.min(1, Math.abs(value) / max);
  const mid = [235, 233, 228];
  const end = value >= 0 ? [184, 78, 56] : [68, 126, 156];
  const c = mid.map((m, i) => Math.round(m + t * (end[i] - m)));
  return "rgb(" + c.join(",") + ")";
}

function renderMap() {
  if (!state.result) return;
  const r = state.result;
  const canvas = $("map");
  const ctx = canvas.getContext("2d");
  const grid = r.grid;
  const size = canvas.width / grid;
  const max = scaleValues();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let y = 0; y < grid; y++) {
    for (let x = 0; x < grid; x++) {
      const v = state.channel === -1 ? r.spatial[y][x] : r.attribution[y][x][state.channel];
      ctx.fillStyle = ramp(v, max);
      ctx.fillRect(Math.round(x * size), Math.round(y * size),
                   Math.ceil((x + 1) * size) - Math.round(x * size),
                   Math.ceil((y + 1) * size) - Math.round(y * size));
    }
  }
  ctx.strokeStyle = "rgba(255,255,255,.24)";
  ctx.lineWidth = 1;
  for (let n = 1; n < grid; n++) {
    const p = Math.round(n * size) + 0.5;
    ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, 512); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(512, p); ctx.stroke();
  }
  if (state.cell) {
    ctx.strokeStyle = "#1c2644"; ctx.lineWidth = Math.max(2, 9 / grid);
    ctx.strokeRect(state.cell.x * size + 1, state.cell.y * size + 1, size - 2, size - 2);
  }
  $("resultTitle").textContent = state.channel === -1 ? "Spatial attribution" : r.channels[state.channel] + " attribution";
  $("resultSub").textContent = state.channel === -1 ? "Sum across spectral channels" : "Signed contribution per spatial cell";
  const range = "−" + max.toFixed(3) + " to +" + max.toFixed(3);
  $("scaleNote").textContent = state.channel === -1
    ? "Spatial sum · " + range
    : "Channels share one scale · " + range;
}

function renderBars() {
  const r = state.result;
  if (!r) return;
  const local = state.scoreMode === "cell" && state.cell;
  const values = local ? r.attribution[state.cell.y][state.cell.x] : r.spectral;
  const many = r.channels.length > 8;
  $("bandTools").hidden = !many;
  $("bandMode").textContent = state.showAllBands ? "Top 10" : "All bands";
  let rows = values.map((value, index) => ({value, index, name: r.channels[index]}));
  const query = ($("bandSearch").value || "").trim().toLowerCase();
  if (query) rows = rows.filter((row) => row.name.toLowerCase().includes(query));
  if (many && !state.showAllBands && !query) {
    rows.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
    rows = rows.slice(0, 10);
  }
  const scale = Math.max(1e-12, ...values.map((v) => Math.abs(v)));
  const container = $("bars");
  container.replaceChildren();
  rows.forEach((row) => {
    const v = row.value;
    const name = row.name;
    const index = row.index;
    const line = document.createElement("div"); line.className = "bar-line";
    const label = document.createElement("span"); label.className = "bar-label"; label.textContent = name;
    const track = document.createElement("div"); track.className = "bar-track";
    const fill = document.createElement("div"); fill.className = "bar-value";
    const percentage = 50 * Math.abs(v) / scale;
    fill.style.left = (v >= 0 ? 50 : 50 - percentage) + "%";
    fill.style.width = percentage + "%";
    fill.style.background = v >= 0 ? "#b84e38" : "#447e9c";
    track.append(fill);
    const number = document.createElement("span"); number.className = "bar-number";
    number.textContent = (v >= 0 ? "+" : "") + v.toFixed(3);
    line.append(label, track, number);
    container.append(line);
  });
  const scope = local ?
    "Cell (row " + (state.cell.y + 1) + ", col " + (state.cell.x + 1) + ")" :
    "Sum over spatial cells";
  const sampling = many && r.method === "permutation"
    ? " · " + r.permutations + " sampled " + (r.permutations === 1 ? "order" : "orders")
    : "";
  $("scoreContext").textContent = scope + sampling;
  $("cellHint").textContent = state.cell ?
    "Selected cell: row " + (state.cell.y + 1) + ", column " + (state.cell.x + 1) :
    "Click any cell on the map to inspect its " + r.channels.length + " channels.";
}

function setScoreMode(mode) {
  state.scoreMode = mode;
  $("globalBtn").classList.toggle("selected", mode === "global");
  $("cellBtn").classList.toggle("selected", mode === "cell");
  $("globalBtn").setAttribute("aria-pressed", String(mode === "global"));
  $("cellBtn").setAttribute("aria-pressed", String(mode === "cell"));
  renderBars();
}

function restoreQuery() {
  const query = new URLSearchParams(location.search);
  state.pendingModel = query.get("model");
  state.pendingSample = query.get("sample");
  state.hadQuery = ["grid", "permutations", "baseline", "method"].some((key) => query.has(key));
  const grid = Number(query.get("grid"));
  if ([4, 8, 16].includes(grid)) state.grid = grid;
  const baseline = query.get("baseline");
  if (["mean", "zero"].includes(baseline)) state.baseline = baseline;
  const method = query.get("method");
  if (["auto", "permutation", "exact"].includes(method)) $("method").value = method;
  const permutations = Number(query.get("permutations"));
  if (query.has("permutations") && Number.isInteger(permutations) && permutations >= 1 && permutations <= 20)
    $("permutations").value = String(permutations);
  const seed = Number(query.get("seed"));
  if (query.has("seed") && Number.isInteger(seed) && seed >= 0 && seed <= 100000)
    $("seed").value = String(seed);
  const channel = Number(query.get("channel"));
  if (query.has("channel") && Number.isInteger(channel) && channel >= -1)
    state.pendingChannel = channel;
}

async function stopJob(jobId) {
  try { await api("/api/jobs/" + jobId, {method: "DELETE"}); }
  catch (_) { return; } // The worker may already have finished.
  // Cancellation is cooperative: wait until the worker releases the slot.
  for (let attempt = 0; attempt < 80; attempt++) {
    try {
      const job = await api("/api/jobs/" + jobId);
      if (job.status !== "running") return;
    } catch (_) { return; }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  // Subsequent starts will report the genuine server-busy state.
}

async function abandonRun() {
  return invalidateRun();
}

function setupEvents() {
  $("gridOptions").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.grid = Number(button.dataset.grid);
      syncControls();
      markChanged();
    });
  });
  $("baselineOptions").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.baseline = button.dataset.baseline;
      activeChoice($("baselineOptions"), "baseline", state.baseline);
      markChanged();
    });
  });
  $("method").addEventListener("change", markChanged);
  // A typed seed immediately invalidates the previous attribution; don't
  // defer cancellation until the input loses focus.
  $("seed").addEventListener("input", markChanged);
  $("permutations").addEventListener("input", () => {
    $("permLabel").textContent = $("permutations").value;
    markChanged();
  });
  $("model").addEventListener("change", async () => {
    invalidateRun();
    state.hadQuery = false;
    state.channel = -1;
    const model = selected();
    state.grid = model.compute.default_grid;
    state.baseline = model.compute.default_baseline;
    $("method").value = model.compute.default_method;
    $("permutations").value = String(model.compute.default_permutations);
    renderSamples();
    syncControls();
    markChanged();
    try { await loadPreview(); } catch (exc) { status(exc.message, true); }
  });
  $("sample").addEventListener("change", async () => {
    markChanged();
    try { await loadPreview(); } catch (exc) { status(exc.message, true); }
  });
  $("preset").addEventListener("change", () => {
    if ($("preset").value === "custom") return;
    const option = $("preset").selectedOptions[0];
    state.grid = Number(option.dataset.grid);
    $("permutations").value = option.dataset.permutations;
    syncControls();
    markChanged();
  });
  $("bandSearch").addEventListener("input", () => {
    renderBars();
    renderChannelButtons();
  });
  $("bandMode").addEventListener("click", () => {
    state.showAllBands = !state.showAllBands;
    renderBars();
  });
  $("cancel").addEventListener("click", async () => {
    await abandonRun();
    status("Cancelled.");
  });
  $("run").addEventListener("click", runSSI);
  $("globalBtn").addEventListener("click", () => setScoreMode("global"));
  $("cellBtn").addEventListener("click", () => setScoreMode("cell"));
  $("map").addEventListener("click", (event) => {
    if (!state.result) return;
    const bounds = $("map").getBoundingClientRect();
    const x = Math.min(state.result.grid - 1, Math.max(0,
      Math.floor((event.clientX - bounds.left) * state.result.grid / bounds.width)));
    const y = Math.min(state.result.grid - 1, Math.max(0,
      Math.floor((event.clientY - bounds.top) * state.result.grid / bounds.height)));
    state.cell = {x, y};
    setScoreMode("cell");
    renderMap();
    $("map").focus();
  });
  $("map").addEventListener("keydown", (event) => {
    if (!state.result || !state.cell) return;
    const step = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[event.key];
    if (!step) return;
    event.preventDefault();
    state.cell = {
      x: Math.min(state.result.grid - 1, Math.max(0, state.cell.x + step[0])),
      y: Math.min(state.result.grid - 1, Math.max(0, state.cell.y + step[1])),
    };
    setScoreMode("cell");
    renderMap();
  });
  $("download").addEventListener("click", () => {
    if (!state.result) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(state.result, null, 2)], {type:"application/json"}));
    const anchor = document.createElement("a"); anchor.href = url;
    anchor.download = "ssi_" + state.result.sample_id + "_grid" + state.result.grid + ".json";
    anchor.click(); URL.revokeObjectURL(url);
  });
  $("copyCommand").addEventListener("click", async () => {
    if (!state.result) return;
    try {
      await navigator.clipboard.writeText(state.result.command);
      status("Reproduction command copied.");
    } catch (_) {
      document.querySelector(".more").open = true;
      status("Copy from the reproduction panel below.");
    }
  });
}

async function init() {
  setupEvents();
  restoreQuery();
  try {
    const catalog = await api("/api/catalog");
    if (!catalog.models.length) throw new Error("No models are available.");
    renderCatalog(catalog);
    status("Loading the selected model and input…");
    await loadPreview();
    await runSSI();
  } catch (exc) { status(exc.message, true); }
}
init();
