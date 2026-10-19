"""Headless browser smoke test against a running SSI Playground.

Requires: pip install playwright && python -m playwright install chromium
The app is expected at http://127.0.0.1:7860 unless SSI_LAB_URL overrides it.
"""
from pathlib import Path
import os

from playwright.sync_api import sync_playwright


BASE = os.getenv("SSI_LAB_URL", "http://127.0.0.1:7860")
OUT = Path(os.getenv("SSI_SCREENSHOT_DIR", "/tmp"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 950}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.getElementById('status').textContent.startsWith('Computed')",
            timeout=120000,
        )
        assert page.locator("#bars .bar-line").count() == 6
        assert page.locator("#inputImage").evaluate("(img) => img.naturalWidth") == 128
        assert page.locator("#gtImage").evaluate("(img) => img.naturalWidth") == 128
        assert page.locator("#predImage").evaluate("(img) => img.naturalWidth") == 128
        assert "hidden" in (page.locator("#mapEmpty").get_attribute("class") or "")
        page.locator('button[data-grid="4"]').click()
        assert "Run SSI" in page.locator("#status").text_content()
        page.locator("#run").click()
        page.wait_for_function(
            "() => document.getElementById('runMeta').textContent.includes('4 × 4')",
            timeout=120000,
        )
        page.get_by_role("button", name="SWIR2", exact=True).click()
        assert "SWIR2 attribution" in page.locator("#resultTitle").text_content()
        page.locator("#map").click(position={"x": 90, "y": 90})
        assert "Cell (row " in page.locator("#scoreContext").text_content()
        assert page.locator("#bars .bar-line").count() == 6
        assert not errors, "Browser console errors: " + repr(errors)
        page.screenshot(path=str(OUT / "ssi_playground_desktop.png"), full_page=True)

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(450)
        sizes = page.evaluate(
            "() => ({viewport: window.innerWidth, scroll: document.documentElement.scrollWidth})"
        )
        assert sizes["scroll"] <= sizes["viewport"] + 2, sizes
        page.screenshot(path=str(OUT / "ssi_playground_mobile.png"), full_page=True)
        browser.close()
    print("SSI Playground browser interactions and responsive layout passed.")


if __name__ == "__main__":
    main()
