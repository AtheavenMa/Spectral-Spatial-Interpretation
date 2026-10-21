"""Verify empty initial state, click-to-add/remove orders and exact SSI totals."""
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
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(self_contained_html(), wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('#jointMaps .joint-card').length === 6")
        page.keyboard.press("4")
        assert page.locator("#playOrder").count() == 0
        chips = page.locator("#orderPills button")
        assert chips.count() == 5
        assert all(chips.nth(i).get_attribute("aria-pressed") == "false" for i in range(5))
        assert all(item["sum"] == 0 and len(item["cells"]) == 0 for item in totals(page))
        page.wait_for_timeout(1100)
        assert all(item["sum"] == 0 for item in totals(page)), "Autoplay is not allowed"

        chips.nth(2).click()
        first = totals(page)
        check_additive(first)
        assert all(len(item["cells"]) == 1 for item in first)
        assert chips.nth(2).get_attribute("aria-pressed") == "true"
        chips.nth(0).click()
        two = totals(page)
        check_additive(two)
        assert all(len(item["cells"]) == 2 for item in two)
        assert any(abs(two[i]["sum"] - first[i]["sum"]) > 1e-9 for i in range(6))

        chips.nth(2).click()
        single = totals(page)
        check_additive(single)
        assert all(len(item["cells"]) == 1 for item in single)
        chips.nth(0).click()
        assert all(item["sum"] == 0 and len(item["cells"]) == 0 for item in totals(page))

        for i in (4, 2, 0, 3, 1):
            chips.nth(i).click()
        final = totals(page)
        check_additive(final)
        expected = page.evaluate("() => window.__SSI_DATA__.attribution[9][11]")
        for row, val in zip(final, expected):
            assert len(row["cells"]) == 5
            assert math.isclose(row["sum"], val, abs_tol=1e-10), (row, val)

        chips.nth(3).click()
        assert all(len(item["cells"]) == 4 for item in totals(page))
        chips.nth(3).click()
        assert all(len(item["cells"]) == 5 for item in totals(page))
        page.keyboard.press("3")
        photo = page.locator("#photoInteractive")
        photo.click(position={"x": 125, "y": 120})
        page.keyboard.press("4")
        assert all(item["sum"] == 0 for item in totals(page)), "New cell must start empty"
        assert not errors, errors
        browser.close()
        print("Passed: no autoplay, empty initial state, arbitrary order click, add/remove, exact full totals, reset on cell change")

if __name__ == "__main__":
    main()
