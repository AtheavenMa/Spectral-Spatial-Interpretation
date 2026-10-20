"""Render real SSI Playground output for HLS sample_0163 as video assets.

Recomputes the exact browser SSI (seeded JS permutation sampler) with
grid=16x16, K=5, mean baseline, seed=0. This is not a pre-rendered Atlas PNG.

From repository root:
  python -m pip install playwright Pillow numpy
  python -m playwright install chromium
  python tools/export_video_hls_0163.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs" / "playground"
OUT = ROOT / "assets" / "video" / "hls_burnscar_0163"
PORT = 8763
SAMPLE = "HLS_BurnScars/sample_0163"
URL = f"http://127.0.0.1:{PORT}/?sample=HLS_BurnScars%2Fsample_0163&grid=16&k=5&seed=0"
BANDS = ("Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2")
INK = "#1d2c39"
MUTED = "#647786"
RED = "#bd474d"
BLUE = "#347ba3"


def font(size: int, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def text(draw, xy, words, *, size=32, bold=False, color=INK):
    draw.text(xy, words, font=font(size, bold), fill=color)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def write_canvas(page, selector, destination):
    data = page.locator(selector).evaluate(
        "(canvas) => canvas.toDataURL('image/png').split(',')[1]"
    )
    destination.write_bytes(base64.b64decode(data))
    return destination


def chart(spectral):
    W, H = 1720, 850
    image = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(image)
    text(draw, (85, 60), "SPECTRAL CONTRIBUTIONS", size=47, bold=True)
    text(draw, (87, 126), "Sum of channel attribution across all 256 spatial cells", size=25, color=MUTED)
    x0, x1 = 160, 1570
    zero = 460
    draw.line((x0, zero, x1, zero), fill="#a9b6bf", width=3)
    max_abs = max(abs(v) for v in spectral) or 1
    axis = 270 / max_abs
    for i, (band, val) in enumerate(zip(BANDS, spectral)):
        x = x0 + (i + 0.5) * (x1 - x0) / len(BANDS)
        h = abs(val) * axis
        half = 43
        if val >= 0:
            y0, y1 = zero - h, zero
        else:
            y0, y1 = zero, zero + h
        draw.rounded_rectangle((int(x-half), int(y0), int(x+half), int(y1)),
                               radius=6, fill=RED if val >= 0 else BLUE)
        lab = f"{val:+.3f}"
        bb = draw.textbbox((0, 0), lab, font=font(26))
        tw = bb[2] - bb[0]
        pos = (x - tw/2, y0 - 41 if val >= 0 else y1 + 12)
        draw.text(pos, lab, font=font(26), fill=RED if val >= 0 else BLUE)
        name_bb = draw.textbbox((0, 0), band, font=font(28, True))
        draw.text((x-(name_bb[2]-name_bb[0])/2, 750), band, font=font(28, True), fill=INK)
    image.save(OUT/"spectral_contributions.png", optimize=True)


def panel(source, desired_width=700):
    im = Image.open(source).convert("RGB")
    return im.resize((desired_width, desired_width), Image.Resampling.LANCZOS)


def composite():
    bg = Image.new("RGB", (2500, 1940), "#ffffff")
    d = ImageDraw.Draw(bg)
    text(d, (125, 58), "ONE IMAGE. ONE JOINT EXPLANATION.", size=58, bold=True)
    text(d, (127, 131), "HLS Burn Scar  |  16 x 16 spatial cells  |  6 spectral channels", size=30, color=MUTED)
    positions = [(125, 242), (904, 242), (1683, 242)]
    titles = ["(a) INPUT IMAGE", "(b) GROUND TRUTH", "(c) SPATIAL SSI"]
    files = ["input.png", "ground_truth.png", "spatial_ssi.png"]
    for (x, y), title, fn in zip(positions, titles, files):
        text(d, (x, y-55), title, size=29, bold=True)
        bg.paste(panel(OUT/fn, 685), (x, y))
    text(d, (125, 1020), "(d) CHANNEL-WISE SPATIAL ATTRIBUTIONS", size=37, bold=True)
    for i, name in enumerate(BANDS):
        x = 125 + i * 374
        text(d, (x, 1090), name, size=27, bold=True)
        image = panel(OUT/f"channel_{i+1:02d}_{name.lower()}.png", 339)
        bg.paste(image, (x, 1136))
    text(d, (125, 1580), "(e) GLOBAL SPECTRAL CONTRIBUTIONS", size=37, bold=True)
    contribution = Image.open(OUT/"spectral_contributions.png").convert("RGB")
    crop = contribution.crop((125, 220, 1590, 815))
    crop.thumbnail((2210, 285), Image.Resampling.LANCZOS)
    bg.paste(crop, (125, 1630))
    bg.save(OUT/"ssi_explanation_overview.png", optimize=True)


def summaries(result, mask, inp, meta):
    attrib = np.asarray(result["attribution"], dtype=np.float64)
    spatial = np.asarray(result["spatial"], dtype=np.float64)
    spectral = np.asarray(result["spectral"], dtype=np.float64)
    assert attrib.shape == (16, 16, 6)
    assert np.allclose(attrib.sum(axis=2), spatial, atol=1e-6)
    assert np.allclose(attrib.sum(axis=(0, 1)), spectral, atol=1e-6)
    assert result["baseline"] == "mean"
    assert result["method"] == "permutation"
    assert result["permutations"] == 5
    assert result["seed"] == 0 and result["grid"] == 16
    target = mask == 1
    assert int(target.sum()) == meta["region_pixels"]
    mask_cells = target.reshape(16, 8, 16, 8).mean(axis=(1, 3))
    positive = np.clip(spatial, 0, None)
    neg = np.clip(-spatial, 0, None)
    positive_at_target = float((positive * mask_cells).sum() / positive.sum()) if positive.sum() else None
    negative_at_target = float((neg * mask_cells).sum() / neg.sum()) if neg.sum() else None
    top = np.argsort(-np.abs(spatial.reshape(-1)))[:16]
    top_cells = [{"row":int(k//16)+1,"col":int(k%16)+1,
                  "ssi":float(spatial.reshape(-1)[k]),
                  "target_fraction":float(mask_cells.reshape(-1)[k])} for k in top]
    band_info = sorted([
        {"name":band, "index":i, "spectral_total":float(spectral[i]),
         "absolute_magnitude":float(abs(spectral[i])),
         "mean_ssi_on_target_cells":float(
             (attrib[:, :, i] * mask_cells).sum()/max(mask_cells.sum(),1e-12)),
         "mean_ssi_outside_target_cells":float(
             (attrib[:, :, i] * (1-mask_cells)).sum()/max((1-mask_cells).sum(),1e-12)),
         "mean_normalized_input_on_target":float(inp[i][target].mean()),
         "mean_normalized_input_elsewhere":float(inp[i][~target].mean())}
        for i,band in enumerate(BANDS)
    ], key=lambda o: -o["absolute_magnitude"])
    return {
        "sample_id":SAMPLE,
        "parameters":{"grid":16,"baseline":"mean","permutations":5,"seed":0},
        "target":"Mean burn-class logit over the fixed GT burn region",
        "ground_truth_target_pixels":int(target.sum()),
        "full_target_logit":float(result["full_value"]),
        "evaluations":int(result["n_evaluations"]),
        "max_local_efficiency_error":float(result["local_efficiency_error"]),
        "spectral_ranking_by_absolute_total":band_info,
        "spatial_attribution_sum":float(spatial.sum()),
        "spectral_attribution_sum":float(spectral.sum()),
        "top_16_spatial_cells_by_absolute_attribution":top_cells,
        "positive_spatial_ssi_weighted_fraction_inside_GT":positive_at_target,
        "negative_spatial_ssi_weighted_fraction_inside_GT":negative_at_target,
        "target_area_fraction":float(target.mean()),
        "notes":[
            "SSI scores are effects on the fixed burn-class model logit, not raw band reflectance or pixel-wise prediction probabilities.",
            "The sum of spectral totals is the sum of all local full-context cell contrasts, not a guarantee of global input-to-baseline score decomposition.",
            "The GT mask fixes the evaluation region; the model input is the original six-band image.",
            "Interpolation affects only video overlay pixels, not attribution values.",
            "K=5 is a sampled estimator and may give different values from the paper's K=10 and from Python's NumPy sampler at the same numeric seed."
        ],
        "provenance":{
            "checkpoint_sha256":meta["original_checkpoint_sha256"],
            "sample_sha256":meta["original_sample_sha256"],
            "source_png":"examples/HLS_BurnScars/sample_0163.png",
            "runtime":"original SSIComputeRuntime.explain ONNX browser code",
        },
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1",
         "--directory", str(SITE)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    try:
        for _ in range(60):
            try:
                urlopen(f"http://127.0.0.1:{PORT}/", timeout=2).close()
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("local static web server failed to start")
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            page=browser.new_page(viewport={"width": 1600, "height": 1000})
            page.set_default_timeout(390000)
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(URL,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_function(
                "() => state.result?.sample_id === 'HLS_BurnScars/sample_0163' "
                "&& state.result.grid === 16 && state.result.permutations === 5 "
                "&& state.result.baseline === 'mean' && !state.running",
                timeout=390000
            )
            assert not errors, errors
            result=page.evaluate("() => state.result")
            selected=page.evaluate("() => ({id:state.sample.id,meta:state.meta})")
            assert selected["id"]==SAMPLE
            meta=selected["meta"]
            assert abs(result["full_value"]-meta["reference_full_score"])<.025
            (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
            write_canvas(page, "#groundTruth", OUT/"ground_truth.png")
            write_canvas(page, "#spatial", OUT/"spatial_ssi.png")
            for i,name in enumerate(BANDS):
                write_canvas(page, f"#bandGrid .channel-card[data-band='{i}'] canvas",
                            OUT/f"channel_{i+1:02d}_{name.lower()}.png")
            page.screenshot(path=str(OUT/"playground_screenshot.png"),full_page=True)
            browser.close()

        dirname=SITE/"assets"/"samples"/"HLS_BurnScars"/"sample_0163"
        rgb=Image.open(dirname/"rgb.webp").convert("RGB")
        rgb.resize((768,768),Image.Resampling.LANCZOS).save(OUT/"input.png",optimize=True)
        mask=np.frombuffer((dirname/"mask.u8").read_bytes(),dtype=np.uint8).reshape(128,128)
        inp=np.frombuffer((dirname/"x.f32").read_bytes(),dtype="<f4").reshape(6,128,128)
        analysis=summaries(result,mask,inp,meta)
        (OUT/"analysis.json").write_text(json.dumps(analysis,indent=2,allow_nan=False)+"\n")
        chart(result["spectral"])
        composite()
        files = sorted([f for f in OUT.iterdir() if f.is_file()])
        manifest = {
            "title":"SSI HLS Burn Scar sample_0163 / Grid16 / Mean baseline / K5 / seed0",
            "sample_id":SAMPLE,
            "paper":"https://arxiv.org/abs/2610.21114",
            "model_file":"docs/playground/assets/hls_unet.onnx",
            "source_asset_folder":"docs/playground/assets/samples/HLS_BurnScars/sample_0163",
            "files":{f.name:{"size":f.stat().st_size,"sha256":digest(f)} for f in files},
        }
        (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        print(json.dumps({"full_logit":analysis["full_target_logit"],
                          "channels":analysis["spectral_ranking_by_absolute_total"],
                          "positive_fraction_in_gt":analysis["positive_spatial_ssi_weighted_fraction_inside_GT"],
                          "gt_area_fraction":analysis["target_area_fraction"],
                          "files":[f.name for f in OUT.iterdir()]},indent=2),flush=True)
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__=="__main__":
    main()
