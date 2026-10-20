"""Headless browser smoke test against a running SSI Playground.

Requires: pip install playwright && python -m playwright install chromium
The app is expected at http://127.0.0.1:7860 unless SSI_LAB_URL overrides it.
"""
from pathlib import Path
import os

from playwright.sync_api import sync_playwright


BASE = os.getenv("SSI_LAB_URL", "http://127.0.0.1:7860")
OUT = Path(os.getenv("SSI_SCREENSHOT_DIR", "/tmp"))


def _computed(page, timeout=180000):
    page.wait_for_function(
        "() => document.getElementById('status').textContent.startsWith('Computed')",
        timeout=timeout,
    )


def _no_overflow(page):
    sizes = page.evaluate(
        "() => ({viewport: window.innerWidth, scroll: document.documentElement.scrollWidth})"
    )
    if sizes["scroll"] > sizes["viewport"] + 2:
        offenders = page.evaluate("""() => [...document.querySelectorAll('*')]
            .map(el => ({tag:el.tagName.toLowerCase(),id:el.id,cl:el.className?.toString().slice(0,60),
                         left:Math.round(el.getBoundingClientRect().left),
                         right:Math.round(el.getBoundingClientRect().right),
                         width:Math.round(el.getBoundingClientRect().width)}))
            .filter(x => x.right > window.innerWidth + 2 || x.left < -2)
            .sort((a,b) => b.right-a.right).slice(0,15)""")
        print("Horizontal overflow:", sizes, offenders, flush=True)
        page.screenshot(path=str(OUT / "ssi_playground_mobile.png"), full_page=True)
    assert sizes["scroll"] <= sizes["viewport"] + 2, sizes


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 950}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(BASE, wait_until="domcontentloaded")
        _computed(page)
        assert page.locator("#bars .bar-line").count() == 6
        assert page.locator(".visual-panel").count() == 3
        assert page.locator("#predImage").count() == 0
        assert page.locator("#spectralGrid .channel-card").count() == 6
        assert page.locator("#map").get_attribute("width") == "768"
        assert page.evaluate("() => state.targetMask !== null && state.targetMask.width === 128")
        assert page.locator("#inputImage").evaluate("(img) => img.naturalWidth") == 128
        # The map must be an interpolated overlay, not one flat color per cell.
        check = page.evaluate("""() => {
          const a = SSIAtlas.overlayPixels([[1, -1], [0.3, -0.7]], 64, 1, 1);
          return {left:a[(10*64+10)*4+3], right:a[(10*64+20)*4+3],
                  other:a[(10*64+20)*4]};
        }""")
        assert check["left"] != check["right"], check
        # Show/hide transparency without recomputing Shapley values.
        old_map = page.locator("#map").evaluate("(c) => c.toDataURL('image/png')")
        page.locator("#overlayOpacity").evaluate("(el) => { el.value = '0'; el.dispatchEvent(new Event('input', {bubbles:true})); }")
        clear_map = page.locator("#map").evaluate("(c) => c.toDataURL('image/png')")
        assert old_map != clear_map
        page.locator("#overlayOpacity").evaluate("(el) => { el.value = '68'; el.dispatchEvent(new Event('input', {bubbles:true})); }")
        assert "hidden" in (page.locator("#mapEmpty").get_attribute("class") or "")
        assert page.locator("#scaleNote").text_content()
        page.locator('button[data-grid="4"]').click()
        assert "Run SSI" in page.locator("#status").text_content()
        page.locator("#run").click()
        page.wait_for_function(
            "() => document.getElementById('runMeta').textContent.includes('4 × 4')",
            timeout=180000,
        )
        page.get_by_role("button", name="SWIR2", exact=True).click()
        assert "SWIR2 SSI" in page.locator("#resultTitle").text_content()
        page.locator("#map").click(position={"x": 90, "y": 90})
        assert "Cell (row " in page.locator("#scoreContext").text_content()
        assert "model=hls-unet" in page.url
        page.screenshot(path=str(OUT / "ssi_playground_hls_desktop.png"), full_page=True)

        # Emulate a delayed POST response: changing parameters before the job ID
        # arrives must cancel that late job and never paint its old attribution.
        page.evaluate("""() => {
          window.__realFetch = window.fetch;
          window.fetch = async (...args) => {
            const response = await window.__realFetch(...args);
            if (args[0] === '/api/jobs' && args[1]?.method === 'POST') {
              await new Promise((resolve) => setTimeout(resolve, 900));
            }
            return response;
          };
        }""")
        page.locator(".advanced summary").click()
        page.locator("#seed").fill("874")
        page.locator("#run").click()
        page.wait_for_function("() => state.pendingStart !== null", timeout=30000)
        page.locator('button[data-baseline="zero"]').click()
        assert "Run SSI" in page.locator("#status").text_content()
        assert not page.locator("#resultTitle").text_content().startswith("Blue attribution")
        page.locator("#run").click()
        _computed(page)
        assert page.evaluate("() => state.result.baseline") == "zero"
        assert page.evaluate("() => state.result.seed") == 874
        page.evaluate("() => { window.fetch = window.__realFetch; }")

        # Also interrupt a job that has already returned its ID and is running.
        # Use a non-cached 8×8 HLS request so it remains active long enough.
        page.locator('button[data-grid="8"]').click()
        page.locator("#seed").fill("875")
        page.locator('button[data-baseline="mean"]').click()
        page.locator("#run").click()
        page.wait_for_function("() => state.jobId !== null", timeout=30000)
        page.locator('button[data-baseline="zero"]').click()
        page.wait_for_timeout(700)
        assert page.evaluate("() => state.result === null")
        page.locator("#run").click()
        _computed(page)
        assert page.evaluate("() => state.result.baseline") == "zero"
        assert page.evaluate("() => state.result.seed") == 875

        page.locator("#model").select_option("cub-200")
        page.wait_for_function(
            "() => document.getElementById('inputImage').naturalWidth === 448",
            timeout=120000,
        )
        assert "True label" in page.locator("#gtCaption").text_content()
        page.locator("#run").click()
        _computed(page)
        assert page.locator("#bars .bar-line").count() == 3
        assert page.locator("#spectralGrid .channel-card").count() == 3
        assert page.evaluate("() => state.targetMask === null")

        page.locator("#model").select_option("eurosat")
        page.wait_for_function(
            "() => document.getElementById('previewMeta').textContent.includes('EuroSAT')",
            timeout=120000,
        )
        page.locator("#run").click()
        _computed(page)
        assert page.locator("#bars .bar-line").count() == 10

        page.locator("#model").select_option("paviau")
        page.wait_for_function(
            "() => document.getElementById('previewMeta').textContent.includes('103')",
            timeout=120000,
        )
        assert "Self-Blocking Bricks" in page.locator("#gtCaption").text_content()
        page.locator("#run").click()
        _computed(page)
        assert page.locator("#bandTools").is_visible()
        assert page.locator("#bars .bar-line").count() == 10
        assert page.locator("#spectralGrid .channel-card").count() == 6
        assert page.evaluate("() => state.targetMask !== null")
        page.locator("#bandSearch").fill("Band 012")
        page.wait_for_function("() => document.querySelectorAll('#bars .bar-line').length === 1")
        page.locator("#channels select").select_option(label="Band 012")
        assert "Band 012 SSI" in page.locator("#resultTitle").text_content()
        page.locator("#map").click(position={"x": 40, "y": 40})
        assert "Cell (row " in page.locator("#scoreContext").text_content()
        assert page.locator("#bars .bar-line").count() == 1
        assert "model=paviau" in page.url
        assert not errors, "Browser console errors: " + repr(errors)
        page.screenshot(path=str(OUT / "ssi_playground_desktop.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(450)
        _no_overflow(page)
        page.screenshot(path=str(OUT / "ssi_playground_mobile.png"), full_page=True)

        page.set_viewport_size({"width": 1920, "height": 1080})
        page.wait_for_timeout(200)
        _no_overflow(page)
        browser.close()
    print("SSI Playground browser interactions and responsive layout passed.")


if __name__ == "__main__":
    main()
