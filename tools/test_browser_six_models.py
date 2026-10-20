"""Validate one genuine ONNX/SSI calculation per registered model in Chromium.

Runs a one-cell / one-permutation attribution on real original inputs. This
cost-conscious test verifies all six ONNX model families without spending
minutes on every full-resolution interactive 4x4 grid. The separate browser
smoke tests the actual user interface at its default 4x4 setting.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8751
LIVE = os.getenv("SSI_WEB_URL")
BASE = LIVE or f"http://127.0.0.1:{PORT}/"
EXPECTED = (
    "cub-200", "eurosat", "hls-unet",
    "paviau", "salinas", "whu-hi-longkou",
)

MODEL_EVAL = r"""async ({modelId}) => {
  const model=state.registry.models.find(m=>m.id===modelId);
  const sample=state.registry.samples.find(
    s=>s.model_id===modelId && s.image_url && s.status==='ready'
  );
  if(!model || !sample)throw new Error('Missing ready input for '+modelId);
  if(model.onnx_state!=='verified')throw new Error('Unverified ONNX model '+modelId);
  const fetchMeta=await fetch('./'+sample.files.metadata);
  if(!fetchMeta.ok)throw new Error('Original sample metadata unavailable');
  const meta=await fetchMeta.json();
  const tensor=new Float32Array(await bytes(sample.files.tensor));
  const mask=sample.files.mask ? new Uint8Array(await bytes(sample.files.mask)) : null;
  const roi=mask?Array.from(mask.keys()).filter(i=>mask[i]===meta.target_class):[];
  if(meta.sample_id!==sample.id || meta.model_id!==model.id)
    throw new Error('Source provenance identity mismatch');
  if(meta.channels.length!==model.n_channels)
    throw new Error('Channel dimension mismatch');
  if(tensor.length!==model.n_channels*meta.width*meta.height)
    throw new Error('Input tensor size mismatch');
  if(model.kind==='segmentation' && !roi.length)
    throw new Error('Missing fixed target region');
  const session=await loadModel(model);
  const result=await SSIComputeRuntime.explain(
    {model,sample,meta,tensor,roi,session},
    {grid:1,permutations:1,baseline:'mean',seed:0},
  );
  if(!result || !Number.isFinite(result.full_value))
    throw new Error('No real SSI attribution generated');
  if(result.channels.length!==model.n_channels)
    throw new Error('Wrong attribution channels');
  if(result.n_evaluations<model.n_channels+1)
    throw new Error('The original model was not evaluated for each channel');
  if(result.local_efficiency_error>0.0001)
    throw new Error('Local Shapley efficiency failed: '+result.local_efficiency_error);
  return {
    id:sample.id,model:modelId,channels:model.n_channels,
    scored:result.n_evaluations,full_score:result.full_value,
    reference:meta.reference_full_score,
    local_error:result.local_efficiency_error
  };
}"""


def check(url):
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(300000)
        errors=[]
        page.on("pageerror", lambda exc:errors.append(str(exc)))
        page.goto(url.split("?")[0]+"?view=atlas",wait_until="domcontentloaded")
        page.wait_for_function("() => state.registry?.gallery_count === 57",timeout=30000)
        for model_id in EXPECTED:
            item=page.evaluate(MODEL_EVAL,{"modelId":model_id})
            assert abs(item["full_score"]-item["reference"])<max(
                0.025,abs(item["reference"])*0.002
            ),item
            results.append(item)
            print(item,flush=True)
        assert len(results)==6
        assert not errors,errors
        browser.close()
    return results


def main():
    server=None
    try:
        if not LIVE:
            server=subprocess.Popen(
                [sys.executable,"-m","http.server",str(PORT),"--bind","127.0.0.1",
                 "--directory",str(ROOT/"docs"/"playground")],
                stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,
            )
            for _ in range(60):
                try:
                    urlopen(BASE,timeout=1).close()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("The static test server did not start")
        check(BASE)
    finally:
        if server:
            server.terminate()
            server.wait(timeout=5)


if __name__=="__main__":
    main()
