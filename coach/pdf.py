"""Printable practice sheet in the original worksheet's style (#12).

Muse Image draws the illustration at the top of the sheet. The problems and answers are typeset
in code, never by the image model, because image models still garble digits and a practice
sheet with a misprinted number is worse than none. Page 2 is the answer key for the adult,
including the answer the mistaken habit would produce, so it is easy to spot when it comes back.
"""

from __future__ import annotations

import io
import textwrap
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import meta

OUT = meta.ROOT / "out" / "practice"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
W, H = 1700, 2200  # US Letter at 200 dpi, like the test sheets
INK = (20, 20, 20)
GREY = (110, 110, 110)
M = 110  # margin


def _font(name: str, size: int):
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default(size)


TITLE = _font("DejaVuSerif-Bold.ttf", 64)
TEXT = _font("DejaVuSans.ttf", 34)
SMALL = _font("DejaVuSans.ttf", 28)
BOLD = _font("DejaVuSans-Bold.ttf", 34)
PROBLEM = _font("DejaVuSansMono.ttf", 52)


def illustration(header: dict, pattern: dict, practice: dict) -> tuple[Image.Image | None, str]:
    idea = practice.get("illustration") or (
        f"a simple visual model of {pattern.get('skill') or header.get('subject', 'the math skill')}")
    prompt = (f"Simple black line-art illustration for the top of a printable math practice worksheet: "
              f"{idea.rstrip('.')}. Coloring-book style: clean black outlines of recognizable objects, "
              f"white background, no shading. No text, no letters, no digits, no people. "
              f"Friendly and calm, suited to a home printer.")
    try:
        data, _ = meta.generate_image(prompt, size="1536x512")
        return Image.open(io.BytesIO(data)).convert("RGB"), prompt
    except Exception:
        return None, prompt


def _page_header(d: ImageDraw.ImageDraw, title: str, y: int) -> int:
    d.text((M, y), title, font=TITLE, fill=INK)
    y += 110
    d.text((M, y), "Name:", font=TEXT, fill=INK)
    d.line((M + 115, y + 40, M + 520, y + 40), fill=INK, width=3)
    d.text((M + 570, y), "Date:", font=TEXT, fill=INK)
    d.line((M + 670, y + 40, M + 870, y + 40), fill=INK, width=3)
    return y + 80


def _wrap(d, text, font, width_px):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width_px:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(header: dict, pattern: dict, practice: dict, art: Image.Image | None) -> list[Image.Image]:
    # Page 1: the practice sheet.
    p1 = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(p1)
    y = _page_header(d, practice.get("title") or "Practice", 80)
    if art is not None:
        a = art.copy()
        a.thumbnail((W - 2 * M, 330))
        p1.paste(a, ((W - a.width) // 2, y))
        y += a.height + 20
    d.text((M, y), practice.get("instructions") or header.get("instructions") or "", font=TEXT, fill=INK)
    y += 50
    d.line((M, y, W - M, y), fill=INK, width=3)
    y += 50
    probs = practice.get("problems", [])
    long_text = any(len(p["prompt"]) > 34 for p in probs)
    gap = (H - 160 - y) // max(1, len(probs))
    for i, p in enumerate(probs, 1):
        if long_text:
            lines = _wrap(d, f"{i}. {p['prompt']}", TEXT, W - 2 * M)
            for j, line in enumerate(lines[:3]):
                d.text((M, y + j * 46), line, font=TEXT, fill=INK)
            ay = y + min(3, len(lines)) * 46 + 30
            d.text((M + 40, ay), "Answer:", font=TEXT, fill=INK)
            d.line((M + 190, ay + 40, M + 700, ay + 40), fill=INK, width=2)
        else:
            label = f"{i}. {p['prompt'].rstrip()}"
            if not label.endswith("=") and not any(c in p["prompt"] for c in "=?:"):
                label += " ="
            d.text((M, y), label, font=PROBLEM, fill=INK)
            x = M + d.textlength(label, font=PROBLEM) + 30
            d.line((x, y + 62, x + 340, y + 62), fill=INK, width=2)
        y += gap
    d.text((M, H - 90), "worksheet-coach · practice written for one pattern, answer key checked twice",
           font=SMALL, fill=GREY)

    # Page 2: the answer key and notes for the adult.
    p2 = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(p2)
    d.text((M, 80), "Answer key (for the adult)", font=TITLE, fill=INK)
    y = 200
    for line in _wrap(d, f"Pattern: {pattern.get('pattern', '')}.", BOLD, W - 2 * M):
        d.text((M, y), line, font=BOLD, fill=INK)
        y += 46
    for line in _wrap(d, pattern.get("explanation", ""), TEXT, W - 2 * M):
        d.text((M, y), line, font=TEXT, fill=INK)
        y += 46
    y += 30
    d.line((M, y, W - M, y), fill=INK, width=3)
    y += 40
    for i, p in enumerate(probs, 1):
        d.text((M, y), f"{i}. {p['prompt']}", font=BOLD, fill=INK)
        y += 50
        d.text((M + 40, y), f"Answer: {p['answer']}", font=TEXT, fill=INK)
        y += 46
        if p.get("trap_answer"):
            d.text((M + 40, y), f"If you see {p['trap_answer']}, that is the habit again.", font=TEXT, fill=GREY)
            y += 46
        note = "checked by an independent solve" if p.get("checked") else "NOT verified: check this one yourself"
        if p.get("fixed_from"):
            note = f"first draft said {p['fixed_from']}; the check caught it and corrected the key"
        d.text((M + 40, y), note, font=SMALL, fill=GREY)
        y += 70
    two = ("by two different models (Muse Spark and the open-weights Muse Spark Open)"
           if any(p.get("solver") == meta.SPARK_OPEN for p in practice.get("problems", []))
           else "by separate model calls")
    d.text((M, H - 130), textwrap.fill(
        f"AI can make mistakes. Every answer above was solved twice {two}; "
        "anything marked NOT verified needs your eye.", 90), font=SMALL, fill=GREY)
    return [p1, p2]


def practice_pdf(header: dict, pattern: dict, practice: dict, *, with_art: bool = True) -> dict:
    art, art_prompt = illustration(header, pattern, practice) if with_art else (None, "")
    pages = render(header, pattern, practice, art)
    OUT.mkdir(parents=True, exist_ok=True)
    name = f"practice-{uuid.uuid4().hex[:10]}"
    pdf_path = OUT / f"{name}.pdf"
    pages[0].save(pdf_path, "PDF", resolution=200, save_all=True, append_images=pages[1:])
    pages[0].save(OUT / f"{name}.png")
    return {"pdf_url": f"/files/practice/{name}.pdf", "png_url": f"/files/practice/{name}.png",
            "art": art is not None, "art_prompt": art_prompt}
