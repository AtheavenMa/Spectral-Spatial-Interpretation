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
        assert "ROW" in page.locator("#scope").text_content()
        page.screenshot(path=str(SCREENS / "ssi_web_desktop.png"), full_page=True)

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
