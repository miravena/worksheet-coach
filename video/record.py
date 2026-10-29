"""Screen-record one run of the web app with Playwright, noting when each moment happens (#15).

    python video/record.py http://localhost:8000 ws13 out/video
Writes out/video/screen.webm (1920x1080) and out/video/marks.json (seconds from the start of
the recording). Start the app without REPLAY for a live run, or with REPLAY=1 for a saved one.
"""

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SCROLL_JS = """([sel, ms, offset]) => new Promise(done => {
  const el = sel ? document.querySelector(sel) : null;
  const y0 = window.scrollY;
  const y1 = el ? el.getBoundingClientRect().top + y0 - offset : offset;
  const t0 = performance.now();
  function step(t) {
    const k = Math.min(1, (t - t0) / ms), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    window.scrollTo(0, y0 + (y1 - y0) * e);
    k < 1 ? requestAnimationFrame(step) : done();
  }
  requestAnimationFrame(step);
})"""


def main(url: str, sample: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    marks: dict[str, float] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Playwright films CSS pixels, so device_scale_factor does not sharpen the video. Film at
        # 1920x1080 and zoom the page 1.5x instead: the 1280x720 layout, drawn at full resolution.
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080},
                                  record_video_dir=str(out / "raw"),
                                  record_video_size={"width": 1920, "height": 1080})
        ctx.add_init_script("document.addEventListener('DOMContentLoaded', () => "
                            "{ document.documentElement.style.zoom = '1.5'; });")
        page = ctx.new_page()
        t0 = time.monotonic()

        def mark(name: str) -> None:
            marks[name] = round(time.monotonic() - t0, 2)
            print(f"{name:<14} {marks[name]:6.1f}s", flush=True)

        def scroll(sel: str | None, ms: int = 1200, offset: int = 16) -> None:
            page.evaluate(SCROLL_JS, [sel, ms, offset])

        page.goto(url)
        page.wait_for_selector("#sample-buttons button")
        page.wait_for_timeout(800)
        mark("start")
        buttons = page.locator("#sample-buttons button")
        label = sample.replace("ws", "#") + " "  # chips read "#13 Subtracting Negative Numbers"
        target = next(buttons.nth(i) for i in range(buttons.count())
                      if buttons.nth(i).inner_text().startswith(label))
        target.scroll_into_view_if_needed()
        target.hover()
        page.wait_for_timeout(2500)
        target.click()
        mark("click")
        page.wait_for_selector("#live:not([hidden])")
        scroll("#live", 800)
        mark("live")
        page.wait_for_function("document.querySelectorAll('#overlay rect, #overlay polygon').length > 0",
                               timeout=300000)
        mark("boxes")
        page.wait_for_selector("#results:not([hidden])", timeout=600000)
        mark("results")
        page.wait_for_timeout(1500)
        scroll("#score-card", 1500)
        mark("pattern")
        page.wait_for_timeout(4000)
        scroll("#evidence", 1500, 60)
        mark("evidence")
        for _ in range(4):
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollBy({top: 260, behavior: 'smooth'})")
        page.wait_for_timeout(1500)
        scroll("#practice-card", 1500)
        mark("practice")
        page.wait_for_timeout(5000)
        scroll("#sheet-preview", 2000, 40)
        mark("sheet")
        page.wait_for_timeout(6000)
        scroll("#summary-wrap", 1800, 40)
        mark("summary")
        page.wait_for_timeout(8000)
        mark("end")
        video = page.video
        ctx.close()
        browser.close()
        Path(video.path()).replace(out / "screen.webm")
    (out / "marks.json").write_text(json.dumps(marks, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
