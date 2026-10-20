"use strict";

/* Generic browser SSI inference adapter.
 *
 * Given one verified ONNX model, its original CxHxW float32 input, fixed
 * classification target or segmentation ROI, baseline vectors, and grid
 * parameters, calculate original observed-context SSI. This module does not
 * load or substitute any Visual Atlas PNG when computing an explanation.
 *
 * Supports arbitrary channel counts using Uint8Array membership masks;
 * no 32-bit bitwise coalition masks or six-channel assumptions.
 */
(function (root) {
  const range = (n) => Array.from({length:n},(_,i)=>i);
  function rngFromSeed(seed) {
    let x = ((seed | 0) ^ 0x9e3779b9) >>> 0;
    if (!x) x = 0xa541316c;
    return () => {
      x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
      return (x >>> 0) / 4294967296;
    };
  }
  function shuffled(n, rng) {
    const order = range(n);
    for (let k = n - 1; k > 0; k--) {
      const j = Math.floor(rng() * (k+1));
      [order[k],order[j]] = [order[j],order[k]];
    }
    return order;
  }

  function validate(ctx, cfg) {
    const m = ctx.meta;
    if (!ctx.session || !ctx.tensor || !m) throw new Error("Model and original image are not ready.");
    const c = m.channels.length, w = m.width, h = m.height;
    if (!Number.isInteger(c) || c < 1 || ctx.tensor.length !== c*h*w)
      throw new Error("The model input tensor does not match its channel metadata.");
    if (![cfg.grid,cfg.permutations,cfg.seed].every(Number.isInteger) ||
        cfg.grid < 1 || cfg.permutations < 1 || cfg.seed < 0 || cfg.seed > 100000)
      throw new Error("Invalid SSI grid or estimator settings.");
    if (w%cfg.grid || h%cfg.grid)
      throw new Error("Grid size must evenly divide the original image dimensions.");
    const v = cfg.baseline === "mean" ? m.baseline_mean :
              cfg.baseline === "zero" ? m.baseline_zero : null;
    if (!v || v.length !== c || v.some(x=>!Number.isFinite(x)))
      throw new Error("A verified per-channel baseline is missing.");
    if (!Number.isInteger(m.target_class) || m.target_class < 0 ||
        m.target_class >= ctx.model.n_classes)
      throw new Error("The fixed target class is invalid for this checkpoint.");
    if (ctx.model.kind === "segmentation" && (!ctx.roi || !ctx.roi.length))
      throw new Error("The original fixed ground-truth target region is missing.");
  }

  function maskedTensor(ctx, masks, cell, cfg) {
    const {width:w,height:h,channels} = ctx.meta;
    const c = channels.length, plane = w*h, grid = cfg.grid;
    const cellWidth = w/grid, cellHeight = h/grid;
    const col = cell%grid, row = Math.floor(cell/grid);
    const baseline = cfg.baseline === "mean" ? ctx.meta.baseline_mean : ctx.meta.baseline_zero;
    const data = new Float32Array(masks.length * c*plane);
    for(let k=0;k<masks.length;k++) {
      const out = data.subarray(k*c*plane,(k+1)*c*plane);
      out.set(ctx.tensor);
      const mask = masks[k];
      for(let band=0;band<c;band++) {
        if(mask[band]) continue;
        const offset=band*plane;
        for(let y=row*cellHeight;y<(row+1)*cellHeight;y++) {
          const begin=offset+y*w+col*cellWidth;
          out.fill(baseline[band],begin,begin+cellWidth);
        }
      }
    }
    return data;
  }

  async function score(ctx, batch, size) {
    const {width,height,channels} = ctx.meta;
    const inpName = ctx.model.input_name || ctx.session.inputNames[0];
    const outName = ctx.model.output_name || ctx.session.outputNames[0];
    const x = new ort.Tensor("float32",batch,[size,channels.length,height,width]);
    const outputs = await ctx.session.run({[inpName]:x});
    const logits = outputs[outName];
    if (!logits) throw new Error("The ONNX output tensor is missing: "+outName);
    const target = ctx.meta.target_class;
    const cls = ctx.model.n_classes;
    let scores=new Float64Array(size);
    if(ctx.model.kind==="classification") {
      if(logits.dims.length!==2 || logits.dims[0]!==size ||
         logits.dims[1]!==cls) throw new Error("Expected class logits shaped [batch,classes].");
      for(let k=0;k<size;k++) scores[k] = logits.data[k*cls+target];
    } else {
      if(logits.dims.length!==4 || logits.dims[0]!==size ||
         logits.dims[1]!==cls || logits.dims[2]!==height ||
         logits.dims[3]!==width)
         throw new Error("Expected segmentation logits shaped [batch,classes,H,W].");
      const plane=height*width;
      for(let k=0;k<size;k++) {
        let sum=0;
        const offset=(k*cls+target)*plane;
        for(const pixel of ctx.roi) sum+=logits.data[offset+pixel];
        scores[k]=sum/ctx.roi.length;
      }
    }
    if(scores.some(v=>!Number.isFinite(v))) throw new Error("Non-finite model score.");
    return scores;
  }

  function buildPaths(c,n,rng) {
    const paths=[],unique=new Map();
    const add=(bits)=>{
      const key = Array.from(bits).join("");
      if(!unique.has(key)) unique.set(key,bits.slice());
      return key;
    };
    for(let k=0;k<n;k++) {
      const order=shuffled(c,rng);
      const bits=new Uint8Array(c);
      const keys=[add(bits)];
      for(const band of order){bits[band]=1;keys.push(add(bits));}
      paths.push({order,keys});
    }
    return {paths,unique};
  }

  async function explain(ctx,cfg,options={}) {
    validate(ctx,cfg);
    const c=ctx.meta.channels.length,grid=cfg.grid,cells=grid*grid;
    const check=options.cancelled || (()=>false);
    const onProgress=options.progress || (()=>{});
    const rng=rngFromSeed(cfg.seed);
    const attr=Array.from({length:grid},()=>
      Array.from({length:grid},()=>new Array(c).fill(0)));
    const spatial=Array.from({length:grid},()=>new Array(grid).fill(0));
    const spectral=new Array(c).fill(0);
    if(check())return null;
    const full=Number((await score(ctx,ctx.tensor.slice(),1))[0]);
    if(ctx.meta.reference_full_score!==undefined && ctx.meta.reference_full_score!==null &&
       Math.abs(ctx.meta.reference_full_score-full)>Math.max(0.025,Math.abs(full)*.002))
      throw new Error("Unperturbed model output differs from the verified reference.");
    let evaluations=1,maximumError=0;
    for(let g=0;g<cells;g++) {
      if(check())return null;
      const {paths,unique}=buildPaths(c,cfg.permutations,rng);
      const all="1".repeat(c);
      const scores=new Map([[all,full]]);
      const candidates=[...unique].filter(([key])=>key!==all);
      const batchSize=ctx.model.batch_size || (c>32?4:8);
      for(let start=0;start<candidates.length;start+=batchSize) {
        if(check())return null;
        const batch=candidates.slice(start,start+batchSize);
        const input=maskedTensor(ctx,batch.map(([,bits])=>bits),g,cfg);
        const results=await score(ctx,input,batch.length);
        for(let j=0;j<batch.length;j++)scores.set(batch[j][0],results[j]);
        evaluations+=batch.length;
      }
      let sum=0;
      for(const {order,keys} of paths) {
        for(let k=0;k<c;k++) {
          const delta=(scores.get(keys[k+1])-scores.get(keys[k]))/cfg.permutations;
          attr[Math.floor(g/grid)][g%grid][order[k]]+=delta;
          sum+=delta;
        }
      }
      const row=Math.floor(g/grid),col=g%grid;
      spatial[row][col]=sum;
      for(let band=0;band<c;band++)spectral[band]+=attr[row][col][band];
      const contrast=full-scores.get("0".repeat(c));
      maximumError=Math.max(maximumError,Math.abs(sum-contrast));
      onProgress(g+1,cells,evaluations);
      if(g%2===0) await new Promise(r=>requestAnimationFrame(()=>setTimeout(r,0)));
    }
    return {
      model_id:ctx.model.id,sample_id:ctx.sample.id,
      grid,baseline:cfg.baseline,method:"permutation",permutations:cfg.permutations,seed:cfg.seed,
      channels:ctx.meta.channels,
      attribution:attr,spatial,spectral,
      full_value:full,n_evaluations:evaluations,
      local_efficiency_error:maximumError,
      provenance:{
        checkpoint_sha256:ctx.meta.original_checkpoint_sha256||ctx.model.checkpoint_sha256||null,
        sample_sha256:ctx.meta.original_sample_sha256||null,
        target:ctx.meta.target||ctx.model.target_kind,
        browser_model_format:"ONNX",sampler:"xorshift32 / Fisher-Yates"
      }
    };
  }
  root.SSIComputeRuntime = {explain,score,validate,maskedTensor,buildPaths};
})(window);
