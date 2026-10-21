"""Generate an authentic SAR-style three-frame README preview from SSI HTML.

Run: python tools/render_tutorial_preview.py
The frames are actual Chromium captures, not generated illustrations.
"""
from __future__ import annotations

import base64
import io
import os
import re
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUT = ROOT / "assets" / "tour_preview.png"
SLIDES = (1, 4, 6)  # Cover, attribution, two views
TILE_SIZE = (640, 360)


def self_contained_html() -> str:
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    css = (DOCS / "tutorial.css").read_text(encoding="utf-8")
    js = (DOCS / "tutorial.js").read_text(encoding="utf-8")
    data = (DOCS / "assets/ssi-tour/result.json").read_text(encoding="utf-8")
    html = re.sub(r'<link[^>]+(?:fonts\.googleapis|fonts\.gstatic)\.com[^>]*>', '', html)
    html = html.replace('<link rel="stylesheet" href="./tutorial.css">', f'<style>{css}</style>')
    for name in ("input.png", "ground_truth.png", "spatial_ssi.png"):
        raw = (DOCS / "assets/ssi-tour" / name).read_bytes()
        src = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        html = html.replace(f'./assets/ssi-tour/{name}', src)
    old_fetch = "const response=await fetch('./assets/ssi-tour/result.json',{cache:'no-store'});"
    assert old_fetch in js, "Tutorial data loader changed"
    js = js.replace(old_fetch, "const response=new Response(JSON.stringify(window.__SSI_DATA__),{status:200});")
    html = html.replace('<script src="./tutorial.js"></script>',
                        f'<script>window.__SSI_DATA__={data};</script><script>{js}</script>')
    return html


def render() -> None:
    frames = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(self_contained_html(), wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('#jointMaps .joint-card').length === 6",
            timeout=15000,
        )
        for slide in SLIDES:
            page.keyboard.press(str(slide))
            page.wait_for_function(
                "n => document.querySelectorAll('.slide')[n-1].classList.contains('active')",
                arg=slide,
                timeout=5000,
            )
            page.wait_for_timeout(480)
            screenshot = Image.open(io.BytesIO(page.screenshot(type="png"))).convert("RGB")
            frames.append(screenshot.resize(TILE_SIZE, Image.Resampling.LANCZOS))
        browser.close()
        if errors:
            raise RuntimeError(f"Tutorial errors: {errors}")
    result = Image.new("RGB", (TILE_SIZE[0] * len(frames), TILE_SIZE[1]), "#F0ECE3")
    for i, frame in enumerate(frames):
        result.paste(frame, (i * TILE_SIZE[0], 0))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.save(OUTPUT, optimize=True)
    print(f"Rendered {OUTPUT}: {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    render()
