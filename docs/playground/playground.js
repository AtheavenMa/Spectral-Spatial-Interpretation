"use strict";

/* SSI Playground.
 * 57 Atlas sample IDs are selectable through compute-manifest.json. Numerical
 * explanations run only after the original tensor, fixed target and a verified
 * ONNX export are all available. A static Atlas PNG is never an inference input.
 */

const $ = id => document.getElementById(id);
const state = {
  registry: null,
  sample: null,
  modelInfo: null,
  context: null,
  model: null,
  meta: null,
  image: $("input"),
  x: null, mask: null, roi: [], channels: [],
  grid: 4, baseline: "mean", permutations: 1, seed: 0, band: -1,
  selectedCell: null, scope: "whole", result: null, running: false,
  generation: 0, loadTicket: 0, cache: new Map(), sessions: new Map(),
};
function setStatus(s, error=false) {
  $("status").textContent = s;
  $("status").classList.toggle("error",error);
}
function progress(s) { $("progress").textContent=s; }

function modelFor(record) {
  return state.registry.models.find(m=>m.id===record.model_id);
}
function recordsIn(dataset) {
  return state.registry.samples.filter(s=>s.dataset===dataset);
}
function selectedRecord() {
  return state.registry.samples.find(s=>s.id===$("sampleSelect").value);
}
function setReady(ready) {
  $("run").disabled = !ready || state.running;
  $("liveResults").hidden = !ready;
  $("pendingPanel").hidden = ready;
}

function updateControls() {
  const supported = state.modelInfo?.allowed_grids || [4,8,16];
  $("gridControls").querySelectorAll("button").forEach(b=>{
    b.disabled = !supported.includes(Number(b.dataset.grid));
    b.classList.toggle("selected",Number(b.dataset.grid)===state.grid);
    b.setAttribute("aria-pressed",String(Number(b.dataset.grid)===state.grid));
  });
  $("baselineControls").querySelectorAll("button").forEach(b=>{
    b.classList.toggle("selected",b.dataset.baseline===state.baseline);
    b.setAttribute("aria-pressed",String(b.dataset.baseline===state.baseline));
  });
  $("kControls").querySelectorAll("button").forEach(b=>{
    b.classList.toggle("selected",Number(b.dataset.k)===state.permutations);
    b.setAttribute("aria-pressed",String(Number(b.dataset.k)===state.permutations));
  });
  $("seed").value=String(state.seed);
}

function urlState() {
  const q=new URLSearchParams(location.search);
  if(state.registry && state.sample) {
    q.set("dataset",state.sample.dataset);
    q.set("sample",state.sample.id);
  }
  q.set("grid",String(state.grid));
  q.set("baseline",state.baseline);
  q.set("k",String(state.permutations));
  q.set("seed",String(state.seed));
  q.set("band",String(state.band));
  history.replaceState(null,"",location.pathname+"?"+q.toString());
}
function restoreParams() {
  const q=new URLSearchParams(location.search);
  const grid=Number(q.get("grid"));
  if(q.has("grid") && [4,8,16].includes(grid))state.grid=grid;
  const baseline=q.get("baseline");
  if(["mean","zero"].includes(baseline))state.baseline=baseline;
  const k=Number(q.get("k"));
  if([1,3,5].includes(k))state.permutations=k;
  const seed=Number(q.get("seed"));
  if(q.has("seed") && Number.isInteger(seed)&&seed>=0&&seed<=100000)state.seed=seed;
  const band=Number(q.get("band"));
  if(q.has("band")&&Number.isInteger(band)&&band>=-1)state.band=band;
}

function invalidate(alsoStatus=true) {
  state.generation++;
  state.result=null;
  state.selectedCell=null;
  state.scope="whole";
  $("empty").classList.remove("hidden");
  $("bandGrid").replaceChildren();
  $("bars").replaceChildren();
  $("save").disabled=true;
  $("copy").disabled=true;
  $("spatialTitle").textContent="(c) Spatial SSI";
  $("scale").textContent="";
  $("scope").textContent="Whole image";
  if(alsoStatus && state.context)
    setStatus(state.running?"Finishing the previous model batch…":"Ready. Run SSI to explore this image.");
  urlState();
}

function listGroups() {
  const target=$("datasetSelect");
  target.replaceChildren();
  for(const m of state.registry.models) {
    const opt=document.createElement("option");
    opt.value=m.dataset;opt.textContent=m.name;
    target.append(opt);
  }
}

function listSamples(dataset, preferred=null) {
  const records=recordsIn(dataset), target=$("sampleSelect");
  target.replaceChildren();
  for(const rec of records) {
    const opt=document.createElement("option");
    opt.value=rec.id;
    opt.textContent=rec.label;
    target.append(opt);
  }
  const choice=records.find(s=>s.id===preferred)||records[0];
  if(choice)target.value=choice.id;
  return choice;
}

async function bytes(path) {
  const url=path.startsWith("http")?path:"./"+path.replace(/^\.\//,"");
  const response=await fetch(url,{cache:"force-cache"});
  if(!response.ok)throw new Error("Missing verified asset: "+path);
  return await response.arrayBuffer();
}
async function decodeImage(path) {
  const img=state.image;
  img.src=path.startsWith("http")?path:"./"+path.replace(/^\.\//,"");
  await img.decode();
}
function paintTarget() {
  const canvas=$("groundTruth"),dst=canvas.getContext("2d");
  dst.clearRect(0,0,canvas.width,canvas.height);
  if(!state.mask) {
    $("groundTitle").textContent="(b) Target class";
    dst.drawImage(state.image,0,0,canvas.width,canvas.height);
    dst.fillStyle="#ffffffeb";
    dst.fillRect(0,0,canvas.width,57);
    dst.fillStyle="#243b4b";
    dst.font="600 23px system-ui";
    const label=state.meta.target_name||("Class "+state.meta.target_class);
    dst.fillText(label.slice(0,35),16,37);
    return;
  }
  $("groundTitle").textContent="(b) Ground Truth";
  const tmp=document.createElement("canvas");
  tmp.width=state.meta.width;tmp.height=state.meta.height;
  const ctx=tmp.getContext("2d"),pixels=ctx.createImageData(tmp.width,tmp.height);
  const target=state.meta.target_class;
  for(let i=0;i<state.mask.length;i++) {
    const label=state.mask[i];
    const color=label===target?[187,66,73]:label===255?
      [192,198,201]:[245,246,245];
    pixels.data.set([...color,255],i*4);
  }
  ctx.putImageData(pixels,0,0);
  dst.imageSmoothingEnabled=false;
  dst.drawImage(tmp,0,0,canvas.width,canvas.height);
}
function targetRegionObject() {
  if(!state.mask)return null;
  return {
    width:state.meta.width,height:state.meta.height,
    data:Uint8Array.from(state.mask,v=>v===state.meta.target_class?1:0)
  };
}

function showPending(record,model) {
  setReady(false);
  $("run").disabled=true;
  $("sampleState").textContent=record.python_source?
    "Model input exists locally":"Original input needed";
  $("pendingTitle").textContent=model.name+" · "+record.label;
  $("pendingText").textContent=record.python_source?
    "This sample has a Python input; its browser model export is still being prepared.":
    "The original multispectral input and fixed target are needed to compute SSI for this image.";
  const png=record.image_url;
  $("pendingImage").src=png||"";
  $("pendingImage").hidden=!png;
  $("pendingSource").hidden=!png;
  if(png)$("pendingSource").href=png;
  setStatus("This Atlas image is selectable. Its verified compute assets are pending.");
  progress("");
}

async function loadModel(model) {
  if(!window.ort)throw new Error("The browser inference library is not available.");
  if(state.sessions.has(model.id))return state.sessions.get(model.id);
  const promise=(async()=>{
    ort.env.wasm.wasmPaths="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.21.0/dist/";
    ort.env.wasm.numThreads=1;
    const payload=await bytes(model.onnx);
    return await ort.InferenceSession.create(payload,{
      executionProviders:["wasm"],graphOptimizationLevel:"all"
    });
  })();
  state.sessions.set(model.id,promise);
  try{return await promise;}catch(e){state.sessions.delete(model.id);throw e;}
}

async function loadReadySample(record,model,ticket) {
  const files=record.files;
  if(!files || !files.metadata || !files.tensor || !files.rgb)
    throw new Error("The original input assets are incomplete.");
  const metadataResponse=await fetch("./"+files.metadata);
  if(!metadataResponse.ok)throw new Error("The input metadata is missing.");
  const rawMeta=await metadataResponse.json();
  const meta={...rawMeta,
    target_class:rawMeta.target_class??record.target_class,
    target_name:rawMeta.target_name||record.label,
  };
  const [tensorBuffer,maskBuffer]=await Promise.all([
    bytes(files.tensor),files.mask?bytes(files.mask):Promise.resolve(null)
  ]);
  if(ticket!==state.loadTicket)return;
  const tensor=new Float32Array(tensorBuffer);
  const channels=meta.channels;
  const plane=meta.width*meta.height;
  if(!Array.isArray(channels)||channels.length!==model.n_channels||
     tensor.length!==plane*model.n_channels || !tensor.every(Number.isFinite))
     throw new Error("Input tensor and channel order are inconsistent.");
  const mask=maskBuffer?new Uint8Array(maskBuffer):null;
  if(model.kind==="segmentation" && (!mask||mask.length!==plane))
     throw new Error("The fixed segmentation target is missing.");
  if(!Number.isInteger(meta.target_class))throw new Error("The fixed target class is missing.");
  const roi=mask?Array.from(mask.keys()).filter(i=>mask[i]===meta.target_class):[];
  if(model.kind==="segmentation" && !roi.length)
    throw new Error("The fixed target region is empty.");

  state.meta=meta;state.x=tensor;state.mask=mask;state.roi=roi;
  state.channels=channels.slice();
  await decodeImage(files.rgb);
  if(ticket!==state.loadTicket)return;
  if(state.image.naturalWidth!==meta.width ||
     state.image.naturalHeight!==meta.height)
     throw new Error("RGB preview does not align with the model input.");

  state.model=await loadModel(model);
  if(ticket!==state.loadTicket)return;
  state.context={
    session:state.model,model,
    sample:record,meta,tensor,roi,
  };
  setReady(true);
  $("sampleState").textContent="Ready to run";
  $("pendingPanel").hidden=true;
  $("liveResults").hidden=false;
  paintTarget();
  $("run").disabled=false;
  setStatus("Ready. Compute SSI on "+record.label+".");
  progress("");
  await run();
}

async function chooseSample(sampleId,automaticRun=true) {
  if(!state.registry)return;
  const record=state.registry.samples.find(r=>r.id===sampleId);
  if(!record)return;
  const model=modelFor(record);
  ++state.loadTicket;
  const ticket=state.loadTicket;
  state.modelInfo=model;
  state.sample=record;
  state.context=null;
  state.band=-1;
  invalidate(false);
  $("datasetSelect").value=record.dataset;
  listSamples(record.dataset,record.id);
  if(!model.allowed_grids.includes(state.grid))state.grid=model.allowed_grids[0];
  updateControls();
  urlState();
  if(record.status!=="ready"||model.onnx_state!=="verified"){
    showPending(record,model);
    return;
  }
  $("sampleState").textContent="Loading…";
  $("run").disabled=true;
  setStatus("Loading the real model and image…");
  try{
    await loadReadySample(record,model,ticket);
  } catch(error){
    if(ticket!==state.loadTicket)return;
    state.context=null;state.model=null;
    showPending(record,model);
    setStatus("Cannot run this sample: "+error.message,true);
    console.error(error);
  }
}

async function initialize() {
  restoreParams();
  updateControls();
  try{
    const response=await fetch("./compute-manifest.json");
    if(!response.ok)throw new Error("The model and image registry is unavailable.");
    const manifest=await response.json();
    if(manifest.schema_version!==1||manifest.gallery_count!==57||
       manifest.samples.filter(s=>s.image_url).length!==57)
       throw new Error("The image registry has an unexpected version or count.");
    state.registry=manifest;
    listGroups();
    const params=new URLSearchParams(location.search);
    const chosen=manifest.samples.find(s=>s.id===params.get("sample"))||manifest.samples[0];
    $("datasetSelect").value=chosen.dataset;
    listSamples(chosen.dataset,chosen.id);
    if(params.get("view")!=="atlas")await chooseSample(chosen.id);
  }catch(error){
    setStatus("Cannot load the image registry: "+error.message,true);
    $("run").disabled=true;
  }
}

function cacheKey() {
  return [state.sample?.id,state.modelInfo?.id,state.grid,state.baseline,
          state.permutations,state.seed].join("|");
}
async function run() {
  if(!state.context||state.running||state.sample.status!=="ready")return;
  const params={grid:state.grid,baseline:state.baseline,
                permutations:state.permutations,seed:state.seed};
  const hash=cacheKey();
  if(state.cache.has(hash)) {
    state.result=state.cache.get(hash);
    renderResult();
    setStatus("Explanation ready.");
    return;
  }
  state.running=true;$("run").disabled=true;$("stop").hidden=false;
  const generation=++state.generation;
  const ctx=state.context;
  setStatus("Computing SSI…");
  try{
    if(!window.SSIComputeRuntime)throw new Error("The SSI model adapter did not load.");
    const result=await SSIComputeRuntime.explain(ctx,params,{
      cancelled:()=>generation!==state.generation,
      progress:(done,total)=>{
        if(generation===state.generation)progress(Math.round(done/total*100)+"%");
      }
    });
    if(result&&generation===state.generation&&state.context===ctx) {
      state.result=result;
      if(state.cache.size>=24)state.cache.delete(state.cache.keys().next().value);
      state.cache.set(hash,result);
      renderResult();
      setStatus("Explanation ready. Change a parameter to explore.");
      progress("");
    }
  }catch(error){
    if(generation===state.generation){
      setStatus("Could not compute SSI: "+error.message,true);
      progress("");
      console.error(error);
    }
  }finally{
    state.running=false;
    $("stop").hidden=true;
    $("run").disabled=!state.context;
  }
}

function matrix(band) {
  return band===-1?state.result.spatial:
    state.result.attribution.map(row=>row.map(cell=>cell[band]));
}
function limit(band) {
  if(band===-1)return SSIAtlas.signedLimit(state.result.spatial);
  let max=1e-12;
  for(const row of state.result.attribution)
    for(const cell of row)
      for(const score of cell)max=Math.max(max,Math.abs(score));
  return max;
}
function opacity() {return Number($("opacity").value)/100;}
function paintSpatial() {
  if(!state.result)return;
  if(state.band>=state.channels.length)state.band=-1;
  const max=limit(state.band);
  SSIAtlas.paint($("spatial"),state.image,matrix(state.band),
                 max,opacity(),targetRegionObject(),state.selectedCell);
  $("spatialTitle").textContent=state.band===-1?"(c) Spatial SSI":
    "(c) "+state.channels[state.band]+" SSI";
  $("scale").textContent="±"+max.toPrecision(3);
}
function chosenScores() {
  return (state.scope==="cell"&&state.selectedCell)?
    state.result.attribution[state.selectedCell.y][state.selectedCell.x]:
    state.result.spectral;
}

function renderBands() {
  const root=$("bandGrid");
  root.replaceChildren();
  if(!state.result)return;
  const values=chosenScores();
  const c=state.channels.length;
  let displayed=Array.from({length:c},(_,i)=>i);
  if(c>6)displayed.sort((a,b)=>Math.abs(values[b])-Math.abs(values[a])||a-b);
  displayed=displayed.slice(0,6);
  if(state.band>=0&&!displayed.includes(state.band)){
    if(displayed.length===6)displayed[5]=state.band;
    else displayed.push(state.band);
  }
  const chooser=$("bandPicker");
  chooser.hidden=c<=8;
  if(c>8){
    const select=$("bandSelect");
    const current=select.value;
    select.replaceChildren();
    const option=document.createElement("option");
    option.textContent="Spatial sum";option.value="-1";select.append(option);
    state.channels.forEach((name,i)=>{
      const opt=document.createElement("option");
      opt.value=String(i);opt.textContent=name;select.append(opt);
    });
    select.value=String(state.band);
  }
  const max=limit(0);
  displayed.forEach(i=>{
    const card=document.createElement("button");
    card.type="button";card.className="channel-card"+(state.band===i?" selected":"");
    card.dataset.band=String(i);
    card.setAttribute("aria-label","View "+state.channels[i]+" SSI overlaid on original image");
    const label=document.createElement("span");
    label.className="channel-label";label.textContent=state.channels[i];
    const frame=document.createElement("span");frame.className="channel-image";
    const canvas=document.createElement("canvas");
    canvas.width=320;canvas.height=320;frame.append(canvas);
    const value=document.createElement("span");
    value.className="channel-magnitude "+(values[i]>=0?"positive":"negative");
    value.textContent=(values[i]>=0?"+":"")+values[i].toFixed(3);
    card.append(label,frame,value);
    card.addEventListener("click",()=>{
      state.band=state.band===i?-1:i;paintSpatial();renderBands();urlState();
    });
    root.append(card);
    SSIAtlas.paint(canvas,state.image,matrix(i),max,opacity(),targetRegionObject(),null);
  });
}

function renderBars() {
  const container=$("bars");container.replaceChildren();
  if(!state.result)return;
  const values=chosenScores(),c=state.channels.length;
  const indices=Array.from({length:c},(_,i)=>i);
  if(c>10)indices.sort((a,b)=>Math.abs(values[b])-Math.abs(values[a])||a-b);
  const shown=indices.slice(0,c>10?10:c);
  const max=Math.max(1e-10,...values.map(v=>Math.abs(v)));
  shown.forEach(i=>{
    const val=values[i];
    const row=document.createElement("button");
    row.type="button";row.className="bar";
    row.title="View "+state.channels[i]+" SSI map";
    row.setAttribute("aria-label","Show "+state.channels[i]+" attribution");
    const name=document.createElement("span");
    name.className="bar-label";name.textContent=state.channels[i];
    const track=document.createElement("div");track.className="track";
    const fill=document.createElement("span");fill.className="fill";
    const percent=50*Math.abs(val)/max;
    fill.style.left=(val>=0?50:50-percent)+"%";
    fill.style.width=percent+"%";
    fill.style.background=val>=0?"#bd474d":"#347ba3";
    const score=document.createElement("span");score.className="number-value";
    score.textContent=(val>=0?"+":"")+val.toFixed(3);
    track.append(fill);row.append(name,track,score);container.append(row);
    row.addEventListener("click",()=>{
      state.band=i;paintSpatial();renderBands();urlState();
    });
  });
  const local=state.scope==="cell"&&state.selectedCell;
  $("scope").textContent=local?"Row "+(state.selectedCell.y+1)+", col "+(state.selectedCell.x+1):
    c>10?"Top 10 · whole image":"Whole image";
  $("cellInfo").textContent=local?"Local channel contributions in the selected cell.":
    "Click the SSI image above to inspect a spatial cell.";
  $("whole").classList.toggle("selected",!local);
  $("selected").classList.toggle("selected",!!local);
}
function renderResult() {
  if(!state.result)return;
  $("empty").classList.add("hidden");
  paintSpatial();renderBands();renderBars();
  $("save").disabled=false;$("copy").disabled=false;
  urlState();
}
function pickCell(event) {
  if(!state.result)return;
  const rect=$("spatial").getBoundingClientRect();
  const grid=state.result.grid;
  state.selectedCell={
    x:Math.max(0,Math.min(grid-1,Math.floor((event.clientX-rect.left)*grid/rect.width))),
    y:Math.max(0,Math.min(grid-1,Math.floor((event.clientY-rect.top)*grid/rect.height)))
  };
  state.scope="cell";paintSpatial();renderBars();renderBands();
}
function reproduceCommand() {
  const r=state.result,rec=state.sample,model=state.modelInfo;
  const ckpt=model.checkpoint_repo_path||"/path/to/checkpoint.pt";
  const input=rec.python_source||"/path/to/original_sample.npz";
  return "python -m lab.cli atlas --family "+model.id+
    " --checkpoint "+ckpt+" --image "+input+
    " --grid "+r.grid+" --baseline "+r.baseline+
    " --method permutation --permutations "+r.permutations+
    " --seed "+r.seed+" --output outputs/ssi_atlas";
}

function setup() {
  $("datasetSelect").addEventListener("change",()=>{
    const record=listSamples($("datasetSelect").value);
    if(record)chooseSample(record.id);
  });
  $("sampleSelect").addEventListener("change",()=>chooseSample($("sampleSelect").value));
  $("gridControls").querySelectorAll("button").forEach(b=>
    b.addEventListener("click",()=>{
      if(b.disabled)return;
      state.grid=Number(b.dataset.grid);updateControls();invalidate();
    }));
  $("baselineControls").querySelectorAll("button").forEach(b=>
    b.addEventListener("click",()=>{
      state.baseline=b.dataset.baseline;updateControls();invalidate();
    }));
  $("kControls").querySelectorAll("button").forEach(b=>
    b.addEventListener("click",()=>{
      state.permutations=Number(b.dataset.k);updateControls();invalidate();
    }));
  $("seed").addEventListener("input",()=>{
    const v=Number($("seed").value);
    if(Number.isInteger(v)&&v>=0&&v<=100000){state.seed=v;invalidate();}
  });
  $("opacity").addEventListener("input",()=>{
    if(state.result){paintSpatial();renderBands();}
  });
  $("bandSelect").addEventListener("change",()=>{
    state.band=Number($("bandSelect").value);paintSpatial();renderBands();urlState();
  });
  $("run").addEventListener("click",run);
  $("stop").addEventListener("click",()=>{
    invalidate(false);setStatus("Stopping after the current model batch…");
  });
  $("spatial").addEventListener("click",pickCell);
  $("spatial").addEventListener("keydown",event=>{
    if(!state.result)return;
    const moves={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};
    const delta=moves[event.key];
    if(!delta)return;
    event.preventDefault();
    if(!state.selectedCell)state.selectedCell={x:0,y:0};
    state.selectedCell={
      x:Math.min(state.grid-1,Math.max(0,state.selectedCell.x+delta[0])),
      y:Math.min(state.grid-1,Math.max(0,state.selectedCell.y+delta[1]))
    };
    state.scope="cell";paintSpatial();renderBars();renderBands();
  });
  $("whole").addEventListener("click",()=>{state.scope="whole";renderBars();renderBands();});
  $("selected").addEventListener("click",()=>{
    if(!state.selectedCell)state.selectedCell={x:0,y:0};
    state.scope="cell";paintSpatial();renderBars();renderBands();
  });
  $("save").addEventListener("click",()=>{
    if(!state.result)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(state.result,null,2)],
                                           {type:"application/json"}));
    const anchor=document.createElement("a");
    anchor.href=url;
    anchor.download="ssi_"+state.sample.id.replace(/\W+/g,"_")+"_"+state.grid+"x"+state.grid+".json";
    anchor.click();URL.revokeObjectURL(url);
  });
  $("copy").addEventListener("click",async()=>{
    if(!state.result)return;
    const command=reproduceCommand();
    try{await navigator.clipboard.writeText(command);setStatus("Python command copied.");}
    catch(_){setStatus(command);}
  });
  window.addEventListener("ssi-select-example",event=>{
    const id=event.detail?.id;
    if(!id)return;
    if(!state.registry){window.__ssiPendingExample=id;return;}
    chooseSample(id);
  });
}
setup();
window.addEventListener("load",async()=>{
  await initialize();
  if(window.__ssiPendingExample)await chooseSample(window.__ssiPendingExample);
});
window.addEventListener("ssi-open-compute",async()=>{
  if(!state.registry)await initialize();
  else if(state.sample && state.sample.status==="ready" && !state.context)
    await chooseSample(state.sample.id);
});
