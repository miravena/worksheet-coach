"""Still frames for the video: accuracy card, title card, a second sample's results (#15).

    python video/cards.py http://localhost:8001 out/video
The URL is an app started with REPLAY=1, so the second sample costs nothing.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

STYLE = """<style>
body { margin: 0; width: 1920px; height: 1080px; display: flex; align-items: center;
       justify-content: center; background: #1f6f6b; color: #fff;
       font-family: 'DejaVu Sans', sans-serif; }
.box { width: 1500px; padding-bottom: 170px; }
h1 { font-size: 96px; margin: 0 0 24px; letter-spacing: -1px; }
h2 { font-size: 54px; margin: 0 0 48px; font-weight: 400; }
p { font-size: 40px; margin: 12px 0; opacity: .92; }
table { border-collapse: collapse; width: 100%; font-size: 46px; }
td { padding: 22px 8px; border-bottom: 2px solid rgba(255,255,255,.25); }
td.n { text-align: right; font-weight: 700; font-size: 58px; }
small { font-size: 32px; opacity: .8; }
</style>"""

ACCURACY = STYLE + """<div class="box"><h2>30-sheet test set: handwriting, phone photos,
two columns, stacked problems, GED, ASVAB, nursing and trades math</h2>
<table>
<tr><td>Sheets split into the right problems</td><td class="n">30/30</td></tr>
<tr><td>Right/wrong verdicts matching the answer key</td><td class="n">184/184</td></tr>
<tr><td>Written answers read correctly</td><td class="n">184/184</td></tr>
<tr><td>Both readers agree (Muse Spark + Muse Spark Open)</td><td class="n">184/184</td></tr>
</table>
<p><small>python3 tests/accuracy.py --photo --pattern · run of Oct 29, 2026 · the one
reader difference was spacing only</small></p></div>"""

TITLE = STYLE + """<div class="box"><h1>worksheet-coach</h1>
<h2>Five problems that matter, not twenty more.</h2>
<p>Muse Spark · SAM 3.1 · Muse Image · Muse Spark Open (open weights, on Baseten)</p>
<p>github.com/miravena/worksheet-coach</p>
<p><small>For adults (18+). A helper, not a grade. Built during the Meta Global AI Developer
Hackathon. Narration: Kokoro TTS (AI voice).</small></p></div>"""


def main(url: str, out: Path) -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        for name, html in (("card-accuracy", ACCURACY), ("card-title", TITLE)):
            pg.set_content(html)
            pg.screenshot(path=str(out / f"{name}.png"))
        pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
        pg.goto(url)
        pg.locator("#sample-buttons button", has_text="#12 ").click()
        pg.wait_for_selector("#results:not([hidden])", timeout=120000)
        pg.locator("#score-card").scroll_into_view_if_needed()
        pg.evaluate("window.scrollTo(0, document.querySelector('#score-card').getBoundingClientRect().top + scrollY - 16)")
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(out / "card-ws12.png"))
        b.close()


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
