"""Generate the MVP 1 test set: printed worksheets with filled-in answers and an answer key.

Each sheet has a planted mistake pattern (or none, as a control). Output per sheet:
  tests/worksheets/wsNN.png   the page as a student would hand it in (answers in blue)
  tests/worksheets/wsNN.json  the answer key: every problem, the written answer, the correct
                              answer, whether it is right, and the mistake tag

Run: python3 tests/make_testset.py
"""

import json
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "worksheets"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
W, H = 1700, 2200  # US Letter at 200 dpi
INK = (20, 20, 20)
PEN = (25, 60, 170)


def font(name, size):
    try:
        return ImageFont.truetype(str(FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default(size)


TITLE = font("DejaVuSerif-Bold.ttf", 64)
TEXT = font("DejaVuSans.ttf", 34)
PROBLEM = font("DejaVuSansMono.ttf", 52)
ANSWER = font("DejaVuSans-Oblique.ttf", 56)


# --- planted mistakes -------------------------------------------------------------------

def add_no_carry(a, b):
    """Adds column by column and drops every carry: 47 + 38 -> 75."""
    da, db = str(a)[::-1], str(b)[::-1]
    digits = []
    for i in range(max(len(da), len(db))):
        x = int(da[i]) if i < len(da) else 0
        y = int(db[i]) if i < len(db) else 0
        digits.append(str((x + y) % 10))
    return int("".join(reversed(digits)))


def sub_smaller_from_larger(a, b):
    """Subtracts the smaller digit from the larger in each column, never borrows: 52 - 37 -> 25."""
    da, db = str(a)[::-1], str(b)[::-1].ljust(len(str(a)), "0")
    digits = [str(abs(int(x) - int(y))) for x, y in zip(da, db)]
    return int("".join(reversed(digits)))


def mul_forget_carry(a, b):
    """Multi-digit by one digit, forgets to add the carried digit: 46 x 3 -> 128."""
    digits, da = [], str(a)[::-1]
    for i, d in enumerate(da):
        p = int(d) * b
        digits.append(str(p) if i == len(da) - 1 else str(p % 10))
    return int("".join(reversed(digits)))


def frac_add_across(a, b):
    """Adds numerators and denominators: 1/2 + 1/3 -> 2/5."""
    return f"{a.numerator + b.numerator}/{a.denominator + b.denominator}"


def frac(x):
    return f"{x.numerator}/{x.denominator}" if x.denominator != 1 else str(x.numerator)


# --- sheets -------------------------------------------------------------------------------

def sheet(sid, title, instructions, level, pattern, problems):
    """problems: list of (prompt, correct, written, mistake_tag_or_None)."""
    return {
        "id": sid,
        "title": title,
        "instructions": instructions,
        "level": level,
        "pattern": pattern,
        "problems": [
            {
                "n": i + 1,
                "prompt": p,
                "correct_answer": str(c),
                "written_answer": str(w),
                "is_correct": str(c) == str(w),
                "mistake": m if str(c) != str(w) else None,
            }
            for i, (p, c, w, m) in enumerate(problems)
        ],
    }


def build_sheets():
    s = []

    pairs = [(47, 38), (25, 13), (68, 27), (34, 52), (59, 36), (71, 18)]
    s.append(sheet("ws01", "Two-Digit Addition", "Add.", "grade 2", "forgets to carry",
        [(f"{a} + {b} =", a + b, add_no_carry(a, b), "forgets to carry") for a, b in pairs]))

    pairs = [(52, 37), (86, 41), (73, 28), (64, 19), (95, 53), (81, 46)]
    s.append(sheet("ws02", "Two-Digit Subtraction", "Subtract.", "grade 2",
        "subtracts the smaller digit from the larger instead of borrowing",
        [(f"{a} - {b} =", a - b, sub_smaller_from_larger(a, b), "no borrowing") for a, b in pairs]))

    pairs = [(6, 7), (8, 4), (9, 3), (7, 7), (5, 8), (4, 9)]
    s.append(sheet("ws03", "Multiplication Facts", "Multiply.", "grade 3", None,
        [(f"{a} x {b} =", a * b, a * b, None) for a, b in pairs]))

    pairs = [(46, 3), (27, 4), (58, 2), (31, 3), (63, 5), (19, 6)]
    s.append(sheet("ws04", "Multiply by One Digit", "Multiply.", "grade 4",
        "forgets to add the carried digit",
        [(f"{a} x {b} =", a * b, mul_forget_carry(a, b), "forgets carried digit") for a, b in pairs]))

    pairs = [(Fraction(1, 2), Fraction(1, 3)), (Fraction(1, 4), Fraction(2, 4)),
             (Fraction(2, 5), Fraction(1, 3)), (Fraction(1, 6), Fraction(1, 2)),
             (Fraction(3, 8), Fraction(1, 8)), (Fraction(1, 3), Fraction(1, 4))]
    probs = []
    for a, b in pairs:
        right = frac(a + b)
        # Same-denominator problems are answered correctly; the mistake shows when they differ.
        written = right if a.denominator == b.denominator else frac_add_across(a, b)
        probs.append((f"{frac(a)} + {frac(b)} =", right, written, "adds denominators"))
    s.append(sheet("ws05", "Adding Fractions", "Add. Simplify if you can.", "grade 5",
        "adds the denominators when they differ", probs))

    items = [("3.5 + 1.25", "4.75", "1.60"), ("2.4 + 0.36", "2.76", "0.60"),
             ("6.1 + 2.3", "8.4", "8.4"), ("0.75 + 1.5", "2.25", "0.90"),
             ("4.08 + 1.2", "5.28", "4.20"), ("7.5 + 0.5", "8.0", "8.0")]
    s.append(sheet("ws06", "Adding Decimals", "Add.", "grade 5",
        "lines up the last digits instead of the decimal points",
        [(f"{p} =", c, w, "decimal alignment") for p, c, w in items]))

    items = [("47 ÷ 5", "9 R2", "9 R2"), ("38 ÷ 4", "9 R2", "8 R6"), ("59 ÷ 6", "9 R5", "8 R11"),
             ("26 ÷ 3", "8 R2", "8 R2"), ("74 ÷ 8", "9 R2", "8 R10"), ("33 ÷ 7", "4 R5", "4 R5")]
    s.append(sheet("ws07", "Division with Remainders", "Divide. Write the remainder.", "grade 4",
        "leaves a remainder bigger than the divisor",
        [(f"{p} =", c, w, "remainder too big") for p, c, w in items]))

    items = [("x + 7 = 12", "5", "5"), ("x - 4 = 9", "13", "5"), ("3x + 5 = 20", "5", "8.33"),
             ("2x - 6 = 10", "8", "2"), ("x + 11 = 4", "-7", "-7"), ("5x - 15 = 0", "3", "-3")]
    s.append(sheet("ws08", "Solving Linear Equations", "Solve for x.", "adult: algebra",
        "keeps the sign of a term when moving it across the equals sign",
        [(p, c, w, "sign error moving a term") for p, c, w in items]))

    items = [("-(x - 3)", "-x + 3", "-x - 3"), ("2(x + 4)", "2x + 8", "2x + 8"),
             ("-3(2x - 1)", "-6x + 3", "-6x - 1"), ("-(4 - x)", "-4 + x", "-4 - x"),
             ("5(x - 2)", "5x - 10", "5x - 10"), ("-2(x + 5)", "-2x - 10", "-2x + 5")]
    s.append(sheet("ws09", "Distributing a Negative", "Expand.", "adult: algebra",
        "distributes a negative to the first term only",
        [(p, c, w, "negative not distributed") for p, c, w in items]))

    items = [("A $40 shirt is 25% off. Sale price?", "$30", "$30"),
             ("Rent goes from $800 to $880. Percent increase?", "10%", "9.1%"),
             ("A price drops from $50 to $40. Percent decrease?", "20%", "25%"),
             ("What is 15% of $60?", "$9", "$9"),
             ("Pay rises from $20/h to $25/h. Percent increase?", "25%", "20%"),
             ("Sales fall from 200 to 150. Percent decrease?", "25%", "33.3%")]
    s.append(sheet("ws10", "Percent Change (GED practice)", "Answer each question.",
        "adult: GED", "divides the change by the new value instead of the original",
        [(p, c, w, "wrong base for percent change") for p, c, w in items]))
    return s


# --- drawing ------------------------------------------------------------------------------

def draw(sh):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((120, 110), sh["title"], font=TITLE, fill=INK)
    d.text((120, 210), "Name: ____________________     Date: __________", font=TEXT, fill=INK)
    d.text((120, 290), sh["instructions"], font=TEXT, fill=INK)
    d.line((120, 350, W - 120, 350), fill=INK, width=3)

    wordy = max(len(p["prompt"]) for p in sh["problems"]) > 24
    y = 420
    for p in sh["problems"]:
        label = f"{p['n']}."
        if wordy:
            d.text((120, y), label, font=TEXT, fill=INK)
            d.text((190, y), p["prompt"], font=TEXT, fill=INK)
            d.text((190, y + 70), "Answer:", font=TEXT, fill=INK)
            d.text((360, y + 55), p["written_answer"], font=ANSWER, fill=PEN)
            y += 260
        else:
            d.text((120, y), label, font=PROBLEM, fill=INK)
            d.text((220, y), p["prompt"], font=PROBLEM, fill=INK)
            x = 220 + d.textlength(p["prompt"] + " ", font=PROBLEM)
            d.line((x, y + 64, x + 380, y + 64), fill=INK, width=2)
            d.text((x + 20, y - 4), p["written_answer"], font=ANSWER, fill=PEN)
            y += 250
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for sh in build_sheets():
        draw(sh).save(OUT / f"{sh['id']}.png")
        (OUT / f"{sh['id']}.json").write_text(json.dumps(sh, indent=2, ensure_ascii=False) + "\n")
        wrong = sum(not p["is_correct"] for p in sh["problems"])
        print(f"{sh['id']}  {wrong}/{len(sh['problems'])} wrong  {sh['pattern'] or 'control: all correct'}")


if __name__ == "__main__":
    main()
