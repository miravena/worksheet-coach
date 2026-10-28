"""Generate the MVP 1 test set: printed worksheets with filled-in answers and an answer key.

Each sheet has a planted mistake pattern (or none, as a control). Output per sheet:
  tests/worksheets/wsNN.png   the page as a student would hand it in (answers in blue)
  tests/worksheets/wsNN.json  the answer key: every problem, the written answer, the correct
                              answer, whether it is right, and the mistake tag

ws11..ws30 widen the set: adult-level topics, handwritten answers (tests/fonts, SIL OFL), two-column
and stacked layouts, an isolated slip, a blank answer, and for some sheets a phone-photo variant
  tests/worksheets/wsNN_photo.jpg   (named in the key's "photo" field)
Everything is seeded, so a re-run reproduces every file.

Run: python3 tests/make_testset.py
"""

import json
import math
import random
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).parent / "worksheets"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
HAND_DIR = Path(__file__).parent / "fonts"
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


def dstr(d):
    """Decimal -> plain string without trailing zeros: 500, 0.0005."""
    return format(d.normalize(), "f")


def calc(expr, left_to_right=False):
    """Value of an expression written with x and ÷. left_to_right=True is the planted mistake:
    brackets first, then every operator in the order written, ignoring precedence."""
    s = expr.replace("x", "*").replace("÷", "/")
    if not left_to_right:
        return round(eval(s, {"__builtins__": {}}, {}))  # only ever called on literals above
    while "(" in s:
        s = re.sub(r"\(([^()]*)\)", lambda m: str(calc(m.group(1), True)), s)
    toks = re.findall(r"\d+|[-+*/]", s)
    acc = Fraction(toks[0])
    for op, num in zip(toks[1::2], toks[2::2]):
        n = Fraction(num)
        acc = {"+": acc + n, "-": acc - n, "*": acc * n, "/": acc / n}[op]
    return int(acc)


def convert_always_divides(value, factor):
    """Divides by the factor whichever way the units go: 0.5 g to mg -> 0.0005."""
    return dstr(Decimal(value) / factor)


def simplify_once(n, d):
    """Cancels only the smallest prime of the common factor, so 12/18 stops at 6/9."""
    g = math.gcd(n, d)
    p = next(k for k in range(2, g + 1) if g % k == 0) if g > 1 else 1
    return f"{n // p}/{d // p}"


def additive_proportion(a, b, c):
    """a : b = c : x answered by adding the same amount to both terms: 2 : 5 = 6 : x -> 9."""
    return b + (c - a)


def swap_area_perimeter(kind, l, w):
    """Computes the other measure: asked for area gives 2(l + w), asked for perimeter gives l x w."""
    return 2 * (l + w) if kind == "area" else l * w


def round_down(n, place):
    """Always truncates instead of rounding: 3486 to the nearest 100 -> 3400."""
    return n // place * place


def digit_not_value(num, pos):
    """Writes the digit itself instead of its place value: the 7 in 4732 -> 7, not 700."""
    return int(str(num)[pos])


def place_value(num, pos):
    return int(str(num)[pos]) * 10 ** (len(str(num)) - pos - 1)


def sub_negative_as_minus(a, b):
    """Reads a - (-b) as a - b."""
    return a - abs(b) if b < 0 else a - b


def misaligned_sum(a, b):
    """Lines up the last digits instead of the decimal points: 3.5 + 1.25 -> 1.60."""
    places = max(len(x.split(".")[1]) if "." in x else 0 for x in (a, b))
    total = int(a.replace(".", "")) + int(b.replace(".", ""))
    s = str(total).zfill(places + 1)
    return s[:-places] + "." + s[-places:] if places else s


def frac_sub_across(a, b):
    """Subtracts numerators and denominators: 3/4 - 1/2 -> 2/2."""
    return f"{a.numerator - b.numerator}/{a.denominator - b.denominator}"


def dec_mul_short(a, b):
    """Multiplies the digits right but counts decimal places of only the longer factor:
    0.4 x 0.3 -> 1.2."""
    pa = len(a.split(".")[1]) if "." in a else 0
    pb = len(b.split(".")[1]) if "." in b else 0
    prod = int(a.replace(".", "")) * int(b.replace(".", ""))
    return dstr(Decimal(prod).scaleb(-max(pa, pb)))


def neg_times_neg_negative(a, b):
    """Thinks two negatives multiply to a negative: -5 x -6 -> -30."""
    return -abs(a * b) if a < 0 and b < 0 else a * b


def percent_one_digit(p):
    """Moves the decimal one place for single-digit percents: 8% -> 0.8."""
    return dstr(Decimal(p) / (10 if p < 10 else 100))


def exp_as_product(base, exp):
    """Multiplies base by exponent: 3^3 -> 9."""
    return base * exp


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
    s.extend(build_more_sheets())
    return s


# How each of ws11..ws30 is drawn. hand: handwriting font (None = the blue typeset answer of
# ws01..ws10); layout: list | cols (two columns, filled down) | stack (vertical arithmetic);
# wordy: question on its own line with an "Answer:" blank; photo: also write wsNN_photo.jpg.
STYLE = {
    "ws11": dict(layout="list", hand="kalam", photo=True),
    "ws12": dict(layout="list", hand="patrick", wordy=True, photo=True),
    "ws13": dict(layout="cols", hand="kalam", photo=True),
    "ws14": dict(layout="list", hand=None),
    "ws15": dict(layout="list", hand="patrick", wordy=True, photo=True),
    "ws16": dict(layout="list", hand="kalam", wordy=True),
    "ws17": dict(layout="list", hand="patrick", wordy=True),
    "ws18": dict(layout="list", hand="kalam", wordy=True, photo=True),
    "ws19": dict(layout="stack", hand="patrick", photo=True),
    "ws20": dict(layout="stack", hand="kalam", photo=True),
    "ws21": dict(layout="cols", hand="patrick", photo=True),
    "ws22": dict(layout="list", hand="kalam", photo=True),
    "ws23": dict(layout="list", hand="patrick", photo=True),
    "ws24": dict(layout="cols", hand="kalam", photo=True),
    "ws25": dict(layout="list", hand="patrick"),
    "ws26": dict(layout="list", hand=None),
    "ws27": dict(layout="list", hand="kalam", wordy=True, photo=True),
    "ws28": dict(layout="stack", hand="patrick", photo=True),
    "ws29": dict(layout="cols", hand="kalam", photo=True),
    "ws30": dict(layout="cols", hand=None, photo=True),
}


def build_more_sheets():
    s = []

    exprs = ["3 + 4 x 2", "20 - 4 x 3", "7 x 3 + 2", "8 + 12 ÷ 4", "(4 + 2) x 5", "9 - 6 ÷ 3"]
    s.append(sheet("ws11", "Order of Operations (ASVAB practice)", "Work out each one.",
        "adult: ASVAB", "works left to right, ignoring multiplication and division first",
        [(f"{e} =", calc(e), calc(e, True), "ignores order of operations") for e in exprs]))

    items = [("0.5", "g", "mg", 1000, True), ("2", "L", "mL", 1000, True),
             ("250", "mg", "g", 1000, False), ("1.5", "kg", "g", 1000, True),
             ("750", "mcg", "mg", 1000, False), ("3", "g", "mg", 1000, True)]
    s.append(sheet("ws12", "Metric Conversions (nursing dosage practice)",
        "Convert. Write the number only.", "adult: nursing",
        "divides by 1000 even when converting to a smaller unit (which needs multiplying)",
        [(f"Convert {v} {a} to {b}.", dstr(Decimal(v) * f if small else Decimal(v) / f),
          convert_always_divides(v, f), "moves the decimal the wrong way")
         for v, a, b, f, small in items]))

    items = [(5, -3), (-4, -6), (-3, 5), (7, -2), (8, 3), (-1, -9)]
    s.append(sheet("ws13", "Subtracting Negative Numbers", "Subtract.", "adult: pre-algebra",
        "treats subtracting a negative as subtracting a positive",
        [(f"{a} - ({b}) =" if b < 0 else f"{a} - {b} =", a - b, sub_negative_as_minus(a, b),
          "subtracting a negative") for a, b in items]))

    fr = [(12, 18), (10, 15), (8, 12), (15, 45), (14, 21), (24, 36)]
    s.append(sheet("ws14", "Simplifying Fractions", "Write each fraction in lowest terms.",
        "grade 6", "stops after cancelling one small factor instead of the greatest common factor",
        [(f"Simplify {n}/{d} =", frac(Fraction(n, d)), simplify_once(n, d), "stops simplifying early")
         for n, d in fr]))

    items = [(2, 5, 6), (3, 4, 6), (4, 6, 10), (5, 2, 15), (2, 3, 4), (3, 5, 12)]
    s.append(sheet("ws15", "Ratio and Proportion (ASVAB practice)", "Solve each proportion for x.",
        "adult: ASVAB", "adds the same amount to both sides instead of scaling by a factor",
        [(f"Solve: {a} : {b} = {c} : x", frac(Fraction(b * c, a)),
          additive_proportion(a, b, c) if c != 2 * a else frac(Fraction(b * c, a)),
          "additive instead of multiplicative") for a, b, c in items]))

    items = [("area", 8, 5), ("perimeter", 9, 4), ("area", 12, 3), ("perimeter", 7, 7),
             ("area", 6, 6), ("perimeter", 10, 3)]
    probs = []
    for i, (kind, l, w) in enumerate(items):
        unit = "sq ft" if kind == "area" else "ft"
        right = l * w if kind == "area" else 2 * (l + w)
        mixed = swap_area_perimeter(kind, l, w)
        got = right if i in (3, 5) else mixed  # two of six answered correctly
        probs.append((f"A floor is {l} ft by {w} ft. What is its {kind}?", f"{right} {unit}",
                      f"{got} {unit}", "area and perimeter swapped"))
    s.append(sheet("ws16", "Area and Perimeter (trades math)", "Answer with units.",
        "adult: GED", "computes perimeter when asked for area, and area when asked for perimeter",
        probs))

    items = [(3486, 100), (2718, 10), (45672, 1000), (5230, 100), (8904, 10), (1951, 100)]
    names = {10: "ten", 100: "hundred", 1000: "thousand"}
    s.append(sheet("ws17", "Rounding Whole Numbers", "Round to the place named.", "grade 4",
        "always rounds down instead of to the nearest",
        [(f"Round {n} to the nearest {names[pl]}.", (n + pl // 2) // pl * pl, round_down(n, pl),
          "rounds down only") for n, pl in items]))

    items = [(4732, 1), (5081, 2), (3905, 3), (81463, 2), (1278, 3), (9027, 0)]
    s.append(sheet("ws18", "Place Value", "Write the value of the digit named.", "grade 4",
        "gives the digit itself instead of its place value",
        [(f"What is the value of the {str(n)[i]} in {n}?", place_value(n, i), digit_not_value(n, i),
          "digit instead of value") for n, i in items]))

    pairs = [(347, 285), (418, 256), (529, 143), (275, 318), (604, 127), (382, 459)]
    s.append(sheet("ws19", "Three-Digit Addition (stacked)", "Add.", "grade 3", None,
        [(f"{a} + {b} =", a + b, a + b, None) for a, b in pairs]))

    pairs = [(503, 278), (842, 365), (716, 248), (675, 423), (931, 467), (824, 511)]
    s.append(sheet("ws20", "Three-Digit Subtraction (stacked)", "Subtract.", "grade 3",
        "subtracts the smaller digit from the larger instead of borrowing",
        [(f"{a} - {b} =", a - b, sub_smaller_from_larger(a, b), "no borrowing") for a, b in pairs]))

    ex = [("9 x 6", 54), ("56 ÷ 7", 8), ("8 x 8", 64), ("45 ÷ 9", 5), ("7 x 6", 42),
          ("72 ÷ 8", 9), ("12 x 4", 48), ("81 ÷ 9", 9)]
    s.append(sheet("ws21", "Mixed Facts (two columns)", "Multiply or divide.", "grade 4", None,
        [(f"{p} =", c, c, None) for p, c in ex]))

    ex = [("6 x 8", 48, 48), ("7 x 9", 63, 63), ("4 x 7", 28, 27), ("5 x 9", 45, 45),
          ("8 x 8", 64, 64), ("3 x 9", 27, 27)]
    s.append(sheet("ws22", "Multiplication Facts, one slip", "Multiply.", "grade 3", None,
        [(f"{p} =", c, w, "careless slip") for p, c, w in ex]))

    ex = [("1.9", "0.45"), ("8.25", "0.5"), ("3.2", "4.1"), ("2.5", "0.25"), ("6.04", "3.9"),
          ("1.5", "2.5")]
    probs = []
    for i, (a, b) in enumerate(ex):
        right = str(Decimal(a) + Decimal(b))
        if i == 3:
            probs.append((f"{a} + {b} =", right, "", "left blank"))
        else:
            probs.append((f"{a} + {b} =", right, misaligned_sum(a, b), "decimal alignment"))
    s.append(sheet("ws23", "Adding Decimals, one left blank", "Add.", "grade 5",
        "lines up the last digits instead of the decimal points", probs))

    pairs = [(Fraction(3, 4), Fraction(1, 2)), (Fraction(5, 6), Fraction(1, 3)),
             (Fraction(7, 8), Fraction(3, 8)), (Fraction(7, 8), Fraction(1, 4)),
             (Fraction(4, 5), Fraction(1, 2)), (Fraction(5, 6), Fraction(1, 6))]
    probs = []
    for a, b in pairs:
        right = frac(a - b)
        written = right if a.denominator == b.denominator else frac_sub_across(a, b)
        probs.append((f"{frac(a)} - {frac(b)} =", right, written, "subtracts denominators"))
    s.append(sheet("ws24", "Subtracting Fractions", "Subtract. Simplify if you can.", "grade 5",
        "subtracts the denominators when they differ", probs))

    pairs = [("0.4", "0.3"), ("1.2", "0.5"), ("0.06", "0.3"), ("4", "0.25"), ("3.5", "0.2"),
             ("0.8", "0.8")]
    s.append(sheet("ws25", "Multiplying Decimals", "Multiply.", "grade 6",
        "counts the decimal places of one factor instead of both",
        [(f"{a} x {b} =", dstr(Decimal(a) * Decimal(b)), dec_mul_short(a, b), "decimal places")
         for a, b in pairs]))

    pairs = [(-3, 4), (-5, -6), (-8, -2), (7, -3), (-4, -9), (6, -5)]
    s.append(sheet("ws26", "Multiplying Integers (ASVAB practice)", "Multiply.", "adult: ASVAB",
        "answers negative times negative as a negative",
        [(f"{a} x {b} =", a * b, neg_times_neg_negative(a, b), "negative times negative")
         for a, b in pairs]))

    items = [(154, "lb", "kg", 70), (110, "lb", "kg", 50), (88, "lb", "kg", 40),
             (30, "kg", "lb", 66), (45, "kg", "lb", 99), (176, "lb", "kg", 80)]
    probs = []
    for v, a, b, right in items:
        written = dstr(Decimal(v) * Decimal("2.2")) if a == "lb" else right
        probs.append((f"Convert {v} {a} to {b}. (1 kg = 2.2 lb)", right, written,
                      "multiplies instead of dividing"))
    s.append(sheet("ws27", "Weight Conversions (nursing practice)", "Write the number only.",
        "adult: nursing", "multiplies by 2.2 when changing pounds to kilograms", probs))

    pairs = [(46, 3), (78, 6), (59, 4), (34, 2), (87, 5), (65, 7)]
    s.append(sheet("ws28", "Multiply by One Digit (stacked)", "Multiply.", "grade 4",
        "forgets to add the carried digit",
        [(f"{a} x {b} =", a * b, mul_forget_carry(a, b), "forgets carried digit") for a, b in pairs]))

    ps = [35, 8, 62, 5, 90, 3]
    s.append(sheet("ws29", "Percent to Decimal (GED practice)", "Write each percent as a decimal.",
        "adult: GED", "moves the decimal one place for one-digit percents (8% -> 0.8)",
        [(f"{p}% =", dstr(Decimal(p) / 100), percent_one_digit(p), "percent to decimal")
         for p in ps]))

    bases = [(4, 2), (3, 3), (5, 2), (2, 4), (2, 2), (10, 2), (6, 2), (2, 3)]
    s.append(sheet("ws30", "Exponents", "Work out each power.", "adult: pre-algebra",
        "multiplies the base by the exponent",
        [(f"{b}^{e} =", b ** e, exp_as_product(b, e), "exponent as multiplication")
         for b, e in bases]))

    for sh in s:
        if STYLE[sh["id"]].get("photo"):
            sh["photo"] = f"{sh['id']}_photo.jpg"
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


# --- handwriting, layouts and phone photos (ws11..ws30) ----------------------------------

HAND_FONTS = {"kalam": "Kalam-Regular.ttf", "patrick": "PatrickHand-Regular.ttf"}
INKS = {"kalam": (28, 52, 150), "patrick": (40, 40, 52)}  # blue biro / dark pen
_CHARW = ImageFont.truetype(str(FONT_DIR / "DejaVuSansMono.ttf"), 52).getlength("0")


def hand_layout(text, hand, size, rng):
    """Per-character jitter: size, tilt, baseline wobble, spacing. Returns (items, width)."""
    f = ImageFont.truetype(str(HAND_DIR / HAND_FONTS[hand]), size)
    items, x = [], 0.0
    for ch in text:
        sz = int(size * rng.uniform(0.9, 1.1))
        fc = ImageFont.truetype(str(HAND_DIR / HAND_FONTS[hand]), sz)
        items.append((ch, fc, x, rng.uniform(-6, 6), rng.uniform(-5, 5)))
        x += f.getlength(ch) * rng.uniform(0.92, 1.06)
    return items, x


def put_hand(img, x, base, text, hand, rng, size=66, anchor="l", ink=None):
    """Writes text like a pen would: every glyph slightly different, slightly off the line."""
    if not text:
        return
    items, width = hand_layout(text, hand, size, rng)
    x0 = x - width if anchor == "r" else x
    ink = ink or INKS[hand]
    drift = rng.uniform(-0.03, 0.03)  # the line of writing runs a little uphill or downhill
    for ch, fc, dx, tilt, dy in items:
        if ch == " ":
            continue
        tile = Image.new("L", (size * 2, size * 2), 0)
        ImageDraw.Draw(tile).text((size // 2, int(size * 1.3)), ch, font=fc, fill=255,
                                  anchor="ls", stroke_width=1)
        tile = tile.rotate(tilt, resample=Image.BICUBIC)
        px = int(x0 + dx - size // 2)
        py = int(base + dy + drift * dx - size * 1.3)
        img.paste(Image.new("RGB", tile.size, ink), (px, py), tile)


def put_answer(img, d, x, base, text, st, rng, anchor="l"):
    """The student's answer: handwriting, or the blue typeset italic used by ws01..ws10."""
    if st["hand"]:
        put_hand(img, x, base, text, st["hand"], rng, anchor=anchor)
    elif text:
        d.text((x, base), text, font=ANSWER, fill=PEN, anchor="l" + "s" if anchor == "l" else "rs")


def draw_sheet(sh, st):
    """ws11..ws30: same header as draw(), plus handwriting and the list / cols / stack layouts."""
    rng = random.Random(int(sh["id"][2:]))
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((120, 110), sh["title"], font=TITLE if len(sh["title"]) < 30 else font("DejaVuSerif-Bold.ttf", 52),
           fill=INK)
    d.text((120, 210), "Name: ____________________     Date: __________", font=TEXT, fill=INK)
    d.text((120, 290), sh["instructions"], font=TEXT, fill=INK)
    d.line((120, 350, W - 120, 350), fill=INK, width=3)
    probs = sh["problems"]

    if st["layout"] == "list":
        y = 420
        for p in probs:
            if st.get("wordy"):
                d.text((120, y), f"{p['n']}.", font=TEXT, fill=INK)
                d.text((190, y), p["prompt"], font=TEXT, fill=INK)
                d.text((190, y + 70), "Answer:", font=TEXT, fill=INK)
                d.line((360, y + 104, 960, y + 104), fill=INK, width=2)
                put_answer(img, d, 380, y + 98, p["written_answer"], st, rng)
                y += 260
            else:
                d.text((120, y), f"{p['n']}.", font=PROBLEM, fill=INK)
                d.text((220, y), p["prompt"], font=PROBLEM, fill=INK)
                x = 220 + d.textlength(p["prompt"] + " ", font=PROBLEM)
                d.line((x, y + 64, x + 380, y + 64), fill=INK, width=2)
                put_answer(img, d, x + 20, y + 58, p["written_answer"], st, rng)
                y += 250
    elif st["layout"] == "cols":
        small = font("DejaVuSansMono.ttf", 46)
        rows = math.ceil(len(probs) / 2)
        for i, p in enumerate(probs):
            col, row = divmod(i, rows)
            x0, y = (120, 860)[col], 430 + row * 250
            d.text((x0, y), f"{p['n']}.", font=small, fill=INK)
            d.text((x0 + 80, y), p["prompt"], font=small, fill=INK)
            x = x0 + 80 + d.textlength(p["prompt"] + " ", font=small)
            d.line((x, y + 58, x + 190, y + 58), fill=INK, width=2)
            put_answer(img, d, x + 14, y + 52, p["written_answer"], st, rng)
    else:  # stack: number over number, operator at the left, answer under the line
        for i, p in enumerate(probs):
            a, op, b = re.match(r"(\d+) ([-+x]) (\d+) =", p["prompt"]).groups()
            col, row = i % 3, i // 3
            x0, y0 = 120 + col * 500, 430 + row * 560
            width = max(len(a), len(b)) + 2
            xr = x0 + 100 + width * _CHARW
            d.text((x0, y0), f"{p['n']}.", font=TEXT, fill=INK)
            d.text((xr, y0), a, font=PROBLEM, fill=INK, anchor="ra")
            d.text((xr, y0 + 80), b, font=PROBLEM, fill=INK, anchor="ra")
            d.text((xr - (max(len(a), len(b)) + 1) * _CHARW, y0 + 80), op, font=PROBLEM, fill=INK)
            d.line((xr - width * _CHARW, y0 + 160, xr, y0 + 160), fill=INK, width=3)
            put_answer(img, d, xr - 4, y0 + 245, p["written_answer"], st, rng, anchor="r")
    return img


def _persp_coeffs(dst, src):
    """Coefficients for Image.transform(PERSPECTIVE): output corner dst[i] samples input src[i]."""
    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -x * u, -y * u, u])
        rows.append([0, 0, 0, x, y, 1, -x * v, -y * v, v])
    n = 8
    for c in range(n):  # Gauss-Jordan with partial pivoting
        piv = max(range(c, n), key=lambda r: abs(rows[r][c]))
        rows[c], rows[piv] = rows[piv], rows[c]
        rows[c] = [v / rows[c][c] for v in rows[c]]
        for r in range(n):
            if r != c:
                f = rows[r][c]
                rows[r] = [a - f * b for a, b in zip(rows[r], rows[c])]
    return [rows[i][n] for i in range(n)]


def photo_of(page, seed):
    """What a phone camera would hand the app: the page on a dark desk, a few degrees off square,
    uneven light, a soft shadow, a little blur and sensor noise, saved as a ~70 quality JPEG."""
    rng = random.Random(seed * 7919)
    pw, ph = page.size
    cw, ch = int(pw * 1.35), int(ph * 1.3)
    base = (rng.randint(48, 70), rng.randint(42, 62), rng.randint(36, 56))
    desk = Image.new("RGB", (cw, ch), base)
    dd = ImageDraw.Draw(desk)
    for _ in range(70):  # faint grain lines so the desk is not a flat colour
        y = rng.randint(0, ch)
        k = rng.randint(-9, 9)
        dd.line((0, y, cw, y + rng.randint(-40, 40)),
                fill=(base[0] + k, base[1] + k, base[2] + k), width=rng.randint(2, 9))
    desk = desk.filter(ImageFilter.GaussianBlur(3))
    ox, oy = (cw - pw) // 2, (ch - ph) // 2
    shadow = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(shadow).rectangle((ox + 16, oy + 22, ox + pw + 16, oy + ph + 22), fill=150)
    desk.paste(Image.new("RGB", (cw, ch), (0, 0, 0)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(26)))
    tint = (rng.randint(246, 254), rng.randint(242, 250), rng.randint(228, 242))  # warm paper
    desk.paste(ImageChops.multiply(page, Image.new("RGB", page.size, tint)), (ox, oy))

    # perspective warp: rotate a couple of degrees and pull the corners by a few percent
    ang = math.radians(rng.uniform(-2.5, 2.5))
    jit = 0.022 * pw
    src = [(0, 0), (cw, 0), (cw, ch), (0, ch)]
    dst = []
    for (x, y) in src:
        rx, ry = x - cw / 2, y - ch / 2
        dst.append((cw / 2 + rx * math.cos(ang) - ry * math.sin(ang) + rng.uniform(-jit, jit),
                    ch / 2 + rx * math.sin(ang) + ry * math.cos(ang) + rng.uniform(-jit, jit)))
    warped = desk.transform((cw, ch), Image.PERSPECTIVE, _persp_coeffs(dst, src), Image.BICUBIC,
                            fillcolor=base)
    mx, my = int(pw * 0.08), int(ph * 0.06)
    box = (ox - mx, oy - my, ox + pw + mx, oy + ph + my)
    shot = warped.crop(box)
    scale = 2000 / max(shot.size)
    shot = shot.resize((round(shot.width * scale), round(shot.height * scale)), Image.LANCZOS)

    # uneven light: a gradient across the page plus a soft shadow blob, like a hand or a lamp
    w, h = shot.size
    gw, gh = w // 10, h // 10
    th = rng.uniform(0, 2 * math.pi)
    lo = rng.uniform(0.62, 0.80)
    cx, cy = math.cos(th), math.sin(th)
    span = abs(cx) * gw + abs(cy) * gh
    light = Image.new("L", (gw, gh))
    light.putdata([int(255 * (1 - (1 - lo) * (((x - gw / 2) * cx + (y - gh / 2) * cy) / span + 0.5)))
                   for y in range(gh) for x in range(gw)])
    blob = Image.new("L", (gw, gh), 255)
    bx, by = rng.randint(0, gw), rng.randint(0, gh)
    r = rng.randint(gw // 5, gw // 3)
    ImageDraw.Draw(blob).ellipse((bx - r, by - r * 1.4, bx + r, by + r * 1.4), fill=rng.randint(150, 195))
    light = ImageChops.multiply(light, blob.filter(ImageFilter.GaussianBlur(r / 2)))
    light = light.resize((w, h), Image.BICUBIC).convert("RGB")
    shot = ImageChops.multiply(shot, light)
    shot = shot.filter(ImageFilter.GaussianBlur(rng.uniform(0.9, 1.4)))
    noise = Image.frombytes("RGB", (w, h), rng.randbytes(w * h * 3)).point(lambda v: 128 + (v - 128) // 8)
    return ImageChops.add(shot, noise, 1.0, -128)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for sh in build_sheets():
        st = STYLE.get(sh["id"])
        page = draw_sheet(sh, st) if st else draw(sh)
        page.save(OUT / f"{sh['id']}.png")
        if sh.get("photo"):
            photo_of(page, int(sh["id"][2:])).save(OUT / sh["photo"], "JPEG", quality=70)
        (OUT / f"{sh['id']}.json").write_text(json.dumps(sh, indent=2, ensure_ascii=False) + "\n")
        wrong = sum(not p["is_correct"] for p in sh["problems"])
        print(f"{sh['id']}  {wrong}/{len(sh['problems'])} wrong  {sh['pattern'] or ('control: all correct' if not wrong else 'isolated slip, no pattern')}")


if __name__ == "__main__":
    main()
