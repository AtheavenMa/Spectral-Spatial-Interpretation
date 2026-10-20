"""Headless Chromium test of the standalone SSI browser compute path.

It starts a local static HTTP server; there is no Python model/API backend.
All SSI coalition scores are produced by the real exported HLS ONNX network
inside the browser. The test checks the original full-target score, one actual
attribution run, grid/baseline changes, alpha overlay and mobile layout.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PORT = 8750
SITE = os.getenv("SSI_WEB_URL", f"http://127.0.0.1:{PORT}/")
SCREENS = Path(os.getenv("SSI_WEB_SCREENSHOT_DIR", "/tmp"))


def await_computation(page, timeout=240000):
    page.wait_for_function(
        "() => state.result !== null && !state.running",
        timeout=timeout,
    )


def assert_no_overflow(page):
    widths = page.evaluate("""() => ({
      viewport:innerWidth, document:document.documentElement.scrollWidth,
      rightmost:[...document.querySelectorAll('*')].reduce(
        (m,el)=>Math.max(m,el.getBoundingClientRect().right),0)
    })""")
    assert widths["document"] <= widths["viewport"] + 2, widths


def check(site):
    SCREENS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(site, wait_until="domcontentloaded", timeout=30000)
        await_computation(page)
        data = page.evaluate("""() => ({
          full:state.result.full_value,
          reference:state.meta.reference_full_score,
          n:state.result.n_evaluations,
          err:state.result.local_efficiency_error,
          grid:state.result.grid,
          target:state.roi.length,
          native:document.getElementById('input').naturalWidth
        })""")
        assert data["grid"] == 4, data
        assert data["target"] > 0, data
        assert data["native"] == 128, data
        assert data["n"] >= 97, data
        assert abs(data["full"] - data["reference"]) < 0.02, data
        assert data["err"] < 1e-3, data
        assert page.locator(".channel-card").count() == 6
        assert page.locator("#bars .bar").count() == 6
        assert page.locator("#bandPicker").is_hidden()
        assert page.locator("#pendingPanel").is_hidden()
        assert page.evaluate("() => state.registry.gallery_count") == 57
        assert page.locator("#datasetSelect option").count() == 6
        assert page.locator("#sampleSelect option").count() == 11
        assert page.locator("#sampleSelect").input_value() == "hls-bundled"
        assert page.locator("#pendingPanel").is_hidden()
        assert page.evaluate("() => SSIComputeRuntime.buildPaths(270, 1, () => 0.4).unique.size") == 271
        # Test the generic classifier adapter with a deterministic 13-channel
        # linear score, independently of the HLS ONNX checkpoint.
        simulated = page.evaluate("""async () => {
          const C=13, H=4, W=4, plane=H*W;
          const input=new Float32Array(C*plane);
          for(let band=0;band<C;band++)
            input.fill(band+1,band*plane,(band+1)*plane);
          const session={
            inputNames:['image'],outputNames:['logits'],
            run:async feeds=>{
              const tensor=feeds.image,B=tensor.dims[0];
              const scores=new Float32Array(B*2);
              for(let batch=0;batch<B;batch++){
                let sum=0;
                for(let i=0;i<C*plane;i++)
                  sum+=tensor.data[batch*C*plane+i];
                scores[batch*2+1]=sum/plane;
              }
              return {logits:{dims:[B,2],data:scores}};
            },
          };
          const meta={width:W,height:H,channels:Array.from(
            {length:C},(_,i)=>'Band '+(i+1)),target_class:1,
            baseline_mean:Array(C).fill(0),baseline_zero:Array(C).fill(0)};
          const fake={session,tensor:input,meta,model:{
            id:'unit-test-13',kind:'classification',n_classes:2,
            batch_size:8,input_name:'image',output_name:'logits'
          },sample:{id:'unit-test-input'}};
          const output=await SSIComputeRuntime.explain(fake,{
            grid:2,permutations:3,baseline:'mean',seed:5});
          return {spectral:output.spectral,error:output.local_efficiency_error,
                  n:output.n_evaluations};
        }""")
        assert simulated["n"] > 0
        assert simulated["error"] < 1e-4
        for i, value in enumerate(simulated["spectral"]):
            assert abs(value - (i + 1)) < 1e-4, (i, value)

        assert page.locator("#permutations").count() == 0
        assert page.locator("#kControls button").count() == 3
        assert page.locator(".site-bar").text_content().find("OpenSAE") < 0

        initial = page.locator("#spatial").evaluate("(c) => c.toDataURL()")
        page.locator("#opacity").evaluate(
            "(n) => {n.value = '0';n.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        transparent = page.locator("#spatial").evaluate("(c) => c.toDataURL()")
        assert initial != transparent
        page.locator("#opacity").evaluate(
            "(n) => {n.value = '68';n.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        page.locator(".channel-card[data-band='5']").click()
        assert "SWIR2 SSI" in page.locator("#spatialTitle").text_content()
        page.locator("#spatial").click(position={"x": 100, "y": 100})
        assert "row" in page.locator("#scope").text_content().lower()
        page.screenshot(path=str(SCREENS / "ssi_web_desktop.png"), full_page=True)

        # Permutations are direct buttons, not an awkward native OS select menu.
        page.locator("button[data-k='3']").click()
        assert page.evaluate("() => state.permutations") == 3
        assert page.locator("button[data-k='3']").get_attribute("aria-pressed") == "true"
        page.locator("button[data-k='5']").click()
        assert page.evaluate("() => state.permutations") == 5
        page.locator("button[data-k='1']").click()
        assert page.evaluate("() => state.permutations") == 1

        page.locator("button[data-grid='8']").click()
        assert page.evaluate("() => state.result === null")
        page.locator("#run").click()
        await_computation(page)
        grid8 = page.evaluate("() => ({g:state.result.grid,err:state.result.local_efficiency_error})")
        assert grid8["g"] == 8 and grid8["err"] < 1e-3, grid8

        page.locator("button[data-grid='4']").click()
        page.locator("button[data-baseline='zero']").click()
        page.locator("#run").click()
        await_computation(page)
        changed = page.evaluate("() => ({baseline:state.result.baseline,full:state.result.full_value})")
        assert changed["baseline"] == "zero"
        assert abs(changed["full"] - data["full"]) < 1e-3

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(250)
        assert_no_overflow(page)
        page.screenshot(path=str(SCREENS / "ssi_web_mobile.png"), full_page=True)
        assert not errors, errors

        # Browse the entire 57-figure research Atlas within the same HTML app.
        gallery = browser.new_page(viewport={"width": 1320, "height": 860})
        gallery.goto(site.split("?")[0] + "?view=atlas&dataset=EuroSAT", wait_until="domcontentloaded")
        gallery.wait_for_function(
            "() => document.querySelectorAll('#datasetFilters button').length === 6"
        )
        assert gallery.locator("#computeView").is_hidden()
        assert gallery.locator("#atlasGallery .atlas-tile").count() == 10
        for dataset, expected in (("CUB_200",10),("HLS_BurnScars",10),
                                  ("PaviaU",10),("Salinas",10),("WHU_Hi_LongKou",7)):
            gallery.locator("#datasetFilters button").filter(
                has_text={"CUB_200":"CUB-200","HLS_BurnScars":"HLS Burn Scars",
                          "PaviaU":"Pavia University","Salinas":"Salinas",
                          "WHU_Hi_LongKou":"WHU-Hi-LongKou"}[dataset]
            ).click()
            assert gallery.locator("#atlasGallery .atlas-tile").count() == expected
        gallery.wait_for_function(
            "() => document.querySelector('#atlasGallery img')?.naturalWidth > 0",
            timeout=60000,
        )
        gallery.evaluate("""async () => {
          const first = [...document.querySelectorAll('#atlasGallery img')].slice(0,3);
          await Promise.all(first.map(img => img.decode()));
        }""")
        gallery.screenshot(path=str(SCREENS / "ssi_web_gallery.png"), full_page=True)
        gallery.locator("#atlasGallery .atlas-tile").first.click()
        assert gallery.locator("#atlasDialog").evaluate("(x)=>x.open")
        assert gallery.locator("#atlasFullLink").get_attribute("href").endswith(".png")
        gallery.locator("#atlasUseSample").click()
        assert not gallery.locator("#atlasDialog").evaluate("(x)=>x.open")
        gallery.wait_for_function(
            """() => state.sample?.id === 'WHU_Hi_LongKou/sample_0000'
              && state.context && state.x && state.x.length === 270*32*32
              && state.meta.channels.length === 270""",
            timeout=120000,
        )
        assert gallery.locator("#pendingPanel").is_hidden()
        assert gallery.locator("#sampleSelect option").count() == 7
        # The 270-band run is real and is stopped here so the test can return
        # to HLS without waiting for every cell.
        gallery.evaluate("() => document.getElementById('stop').click()")
        gallery.wait_for_function("() => !state.running", timeout=180000)
        gallery.locator("#datasetSelect").select_option("HLS_BurnScars", timeout=120000)
        gallery.locator("#sampleSelect").select_option("hls-bundled", timeout=120000)
        await_computation(gallery)
        assert gallery.locator("#run").is_enabled()
        assert gallery.locator("#pendingPanel").is_hidden()
        gallery.close()
        browser.close()
        print({"site": site, "full_score": data["full"],
               "region_pixels": data["target"], "first_evaluations": data["n"],
               "grid8": grid8, "zero_baseline": changed})


def main():
    server = None
    try:
        if not os.getenv("SSI_WEB_URL"):
            server = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(PORT),
                 "--bind", "127.0.0.1", "--directory", str(ROOT / "docs" / "playground")],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
            )
            for _ in range(40):
                try:
                    urlopen(SITE, timeout=1).close()
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Static SSI HTML server did not start")
        check(SITE)
    finally:
        if server:
            server.terminate()
            server.wait(timeout=4)


if __name__ == "__main__":
    main()
