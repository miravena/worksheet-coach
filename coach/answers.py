"""Compare two answers to a math problem the way a careful adult would.

`same(a, b)` returns True, False, or None (could not decide in code; ask a model). Handles
integers, decimals, fractions and mixed numbers, money, percents, "x = 5", remainders
("9 R2"), and simple algebraic expressions ("-x + 3" vs "3 - x").
"""

from __future__ import annotations

import re
from fractions import Fraction

try:
    import sympy
except ImportError:  # sympy is optional; expressions then fall back to the model
    sympy = None


def _clean(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/")
    s = s.replace("$", "").replace(",", "").replace(" ", " ")
    s = re.sub(r"^[a-z]\s*=\s*", "", s)  # "x = 5" -> "5"
    s = s.rstrip(".").strip()
    return s


def _remainder(s: str):
    m = re.fullmatch(r"(-?\d+)\s*(?:r|rem|remainder)\s*(\d+)", s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _number(s: str):
    s = s.replace(" ", "")
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    try:
        v = Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None
    return v / 100 if pct else v


def _mixed(s: str):
    m = re.fullmatch(r"(-?)(\d+)\s+(\d+)/(\d+)", s)
    if not m:
        return None
    sign = -1 if m.group(1) else 1
    return sign * (int(m.group(2)) + Fraction(int(m.group(3)), int(m.group(4))))


def value(s: str):
    s = _clean(s)
    if not s:
        return None
    r = _remainder(s)
    if r:
        return ("R", r)
    mx = _mixed(s)
    if mx is not None:
        return mx
    return _number(s)


def same(a: str, b: str) -> bool | None:
    ca, cb = _clean(a), _clean(b)
    if ca == cb:
        return True
    va, vb = value(a), value(b)
    if va is not None and vb is not None:
        return va == vb
    if sympy is not None and ca and cb:
        try:
            ea = sympy.sympify(ca.replace("^", "**"), evaluate=True)
            eb = sympy.sympify(cb.replace("^", "**"), evaluate=True)
            return bool(sympy.simplify(ea - eb) == 0)
        except Exception:
            return None
    return None
