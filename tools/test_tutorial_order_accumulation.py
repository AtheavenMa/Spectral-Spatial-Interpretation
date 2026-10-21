"""Verify clickable order subsets, add/remove and five-order playback in the SSI tutorial."""
from __future__ import annotations

import math
import os
from playwright.sync_api import sync_playwright
from render_tutorial_preview import self_contained_html

def totals(page):
    return page.locator(".live-effect-row").evaluate_all(
        """nodes => nodes.map(node => ({
            sum: Number(node.dataset.total),
            cells: [...node.querySelectorAll('.live-effect-slot[data-value]')]
                    .map(el => Number(el.dataset.value))
        }))"""
    )

def check_additive(rows):
    assert len(rows) == 6
    for item in rows:
        assert math.isclose(item["sum"], sum(item["cells"]), abs_tol=1e-11)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None,
            args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(self_contained_html(), wait_until="domcontentloaded")
        page.wait_for_function("() => document.querySelectorAll('#jointMaps .joint-card').length === 6")
        page.keyboard.press("4")
        assert all(item["sum"] == 0 for item in totals(page))
        chips=page.locator("#orderPills button")
        chips.nth(0).click()
        first=totals(page)
        check_additive(first)
        assert all(len(item["cells"]) == 1 for item in first)
        chips.nth(2).click()
        two=totals(page)
        check_additive(two)
        assert all(len(item["cells"]) == 2 for item in two)
        assert any(abs(two[i]["sum"] - first[i]["sum"]) > 1e-9 for i in range(6))
        chips.nth(0).click()
        one=totals(page)
        check_additive(one)
        assert all(len(item["cells"]) == 1 for item in one)
        chips.nth(2).click()
        assert all(item["sum"] == 0 for item in totals(page))
        page.locator("#playOrder").click()
        page.wait_for_function(
            "() => document.querySelector('#stepProgress').textContent.includes('5 / 5 orders added')",
            timeout=26000
        )
        final=totals(page)
        check_additive(final)
        expected=page.evaluate("() => window.__SSI_DATA__.attribution[9][11]")
        for a,b in zip(final,expected):
            assert len(a["cells"])==5
            assert math.isclose(a["sum"],b,rel_tol=0,abs_tol=1e-10), (a,b)
        assert not errors, errors
        browser.close()
        print("Passed: empty sum, add, remove, noncontiguous subset, five-order playback, exact final SSI")

if __name__=="__main__":
    main()
