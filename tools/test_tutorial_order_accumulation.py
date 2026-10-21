"""Verify Play adds only the chosen order, preserving unplayed orders and exact totals."""
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
        page.wait_for_function(
            "() => document.querySelectorAll('#jointMaps .joint-card').length === 6")
        page.keyboard.press("4")
        chips = page.locator("#orderPills button")
        play = page.locator("#playOrder")
        assert chips.count() == 5
        assert play.count() == 1 and play.is_disabled() and play.is_visible()
        play_bounds = play.bounding_box()
        chip_bounds = chips.nth(4).bounding_box()
        assert play_bounds and chip_bounds
        assert play_bounds["x"] > chip_bounds["x"] + chip_bounds["width"]
        assert abs(play_bounds["y"] - chip_bounds["y"]) < 32
        assert all(item["sum"] == 0 for item in totals(page))
        page.wait_for_timeout(800)
        assert all(item["sum"] == 0 for item in totals(page)), "No auto selection or autoplay"

        def select(p):
            chips.nth(p).click()
            assert play.is_enabled()

        def play_selected(expected_total):
            play.click()
            page.wait_for_function(
                "(n) => document.querySelector('#stepProgress').textContent.startsWith(n+' / 5 orders added') && !document.querySelector('#playOrder').disabled",
                arg=expected_total,
                timeout=12000)
            rows = totals(page)
            check_additive(rows)
            return rows

        # Selecting a chip alone never changes the result.
        select(2)
        assert all(item["sum"] == 0 for item in totals(page))
        row1=play_selected(1)
        assert all(len(item["cells"]) == 1 for item in row1)
        assert all(chips.nth(i).get_attribute("aria-pressed") == ("true" if i==2 else "false") for i in range(5))

        # Select order 1, but do not play: nothing else gets added.
        select(0)
        row_no_play=totals(page)
        assert all(math.isclose(a["sum"],b["sum"],abs_tol=1e-11)
                   for a,b in zip(row_no_play,row1))
        row2=play_selected(2)
        assert all(len(item["cells"]) == 2 for item in row2)
        assert any(abs(a["sum"]-b["sum"])>1e-9 for a,b in zip(row2,row1))

        # Replaying the selected order replaces it rather than double-counting.
        replay=play_selected(2)
        assert all(math.isclose(a["sum"],b["sum"],abs_tol=1e-11)
                   for a,b in zip(replay,row2))

        # Clicking a completed focused order removes it.
        chips.nth(0).click()
        one_left=totals(page)
        assert all(len(item["cells"]) == 1 for item in one_left)
        assert all(math.isclose(a["sum"],b["sum"],abs_tol=1e-11)
                   for a,b in zip(one_left,row1))

        # Only Play on a chosen order can include it again.
        for order,count in ((4,2),(1,3),(3,4),(0,5)):
            select(order)
            assert sum(len(r["cells"]) for r in totals(page))==(count-1)*6
            play_selected(count)
        expected=page.evaluate("() => window.__SSI_DATA__.attribution[9][11]")
        final=totals(page)
        assert all(len(row["cells"])==5 for row in final)
        for row,val in zip(final,expected):
            assert math.isclose(row["sum"],val,abs_tol=1e-10),(row,val)

        # Selecting a different spatial cell resets to the empty initial state.
        page.keyboard.press("3")
        page.locator("#photoInteractive").click(position={"x":125,"y":120})
        page.keyboard.press("4")
        assert play.is_disabled()
        assert all(row["sum"]==0 for row in totals(page))
        assert not errors, errors
        browser.close()
        print("Passed: no autoplay; selection doesn't add; Play affects one order; partial, replay, remove and final SSI totals; cell reset")

if __name__=="__main__":
    main()
