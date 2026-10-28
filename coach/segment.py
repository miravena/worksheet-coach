"""Cut a worksheet photo into one crop per problem (#7).

Two Meta models split the job, the way Meta's segmentation guide suggests: Muse Spark reads the
page and plans the layout (which problems exist, their printed numbers, roughly where each one
sits, across columns and stacked layouts), and SAM 3.1 supplies pixel-accurate geometry for
every "number" on the page ("math problem" itself returns zero matches). Each planned region is
tightened to the SAM boxes inside it. Both calls run in parallel.

If Spark's plan fails, SAM's number boxes are grouped into problems by rows and columns alone.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from PIL import Image

from . import meta

BOX_RE = re.compile(
    r"(\d+)<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)(?:;c=([\d.]+))?\|>"
)


@dataclass
class Box:
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float = 1.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def h(self) -> int:
        return self.y2 - self.y1

    def as_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass
class Problem:
    index: int
    box: Box
    crop: Image.Image
    parts: list[Box] = field(default_factory=list)


@dataclass
class Segmentation:
    problems: list[Problem]
    numbers: list[Box]
    method: str  # "spark+sam", "spark", or "sam-only"
    size: tuple[int, int]
    steps: list[dict] = field(default_factory=list)


def parse_boxes(text: str) -> list[Box]:
    return [Box(int(a), int(b), int(c), int(d), float(conf) if conf else 1.0)
            for _id, a, b, c, d, _w, _h, conf in BOX_RE.findall(text)]


def _union(boxes: list[Box]) -> Box:
    return Box(min(b.x1 for b in boxes), min(b.y1 for b in boxes),
               max(b.x2 for b in boxes), max(b.y2 for b in boxes))


def group_numbers(numbers: list[Box], width: int) -> list[list[Box]]:
    """Group number boxes into problems: rows by vertical gap, then columns by wide x gaps."""
    if not numbers:
        return []
    med_h = statistics.median(b.h for b in numbers) or 1
    nums = sorted(numbers, key=lambda b: b.cy)
    rows: list[list[Box]] = [[nums[0]]]
    for b in nums[1:]:
        prev = rows[-1]
        bottom = max(p.y2 for p in prev)
        if b.y1 - bottom > 0.9 * med_h:
            rows.append([b])
        else:
            prev.append(b)
    groups: list[list[Box]] = []
    col_gap = 0.18 * width
    for row in rows:
        row = sorted(row, key=lambda b: b.x1)
        cur = [row[0]]
        for b in row[1:]:
            if b.x1 - max(p.x2 for p in cur) > col_gap:
                groups.append(cur)
                cur = [b]
            else:
                cur.append(b)
        groups.append(cur)
    return groups


def _crop(img: Image.Image, box: Box, pad_x: int, pad_y: int) -> tuple[Box, Image.Image]:
    W, H = img.size
    b = Box(max(0, box.x1 - pad_x), max(0, box.y1 - pad_y),
            min(W, box.x2 + pad_x), min(H, box.y2 + pad_y))
    return b, img.crop((b.x1, b.y1, b.x2, b.y2))


LAYOUT_SCHEMA = {
    "type": "object",
    "properties": {
        "columns": {"type": "integer"},
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "integer"},
                    "x1": {"type": "integer"}, "y1": {"type": "integer"},
                    "x2": {"type": "integer"}, "y2": {"type": "integer"},
                },
                "required": ["label", "x1", "y1", "x2", "y2"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["columns", "problems"],
    "additionalProperties": False,
}

LAYOUT_PROMPT = (
    "This is a photo of a completed worksheet. Find every numbered problem. For each, give its "
    "printed problem number (label) and a bounding box that covers the whole problem: the problem "
    "number, the printed problem (all rows if it is written vertically or stacked) and the "
    "learner's written answer and any working. Coordinates are integers on a 0-1000 grid over the "
    "image (x across, y down): top-left x1,y1 and bottom-right x2,y2. Boxes must not overlap. The "
    "page may have several columns; say how many. Skip the title, the name/date line and the "
    "instructions."
)


def spark_layout(img: Image.Image) -> tuple[list[tuple[int, Box]], int, meta.CallStats]:
    """Muse Spark plans the page: (printed label, box in pixels) per problem, and column count."""
    out, st = meta.chat([meta.user_msg(LAYOUT_PROMPT, img)], schema=LAYOUT_SCHEMA,
                        schema_name="layout", effort="medium", max_tokens=16000)
    W, H = img.size
    plan = []
    for p in out["problems"]:
        b = Box(int(p["x1"] * W / 1000), int(p["y1"] * H / 1000),
                int(p["x2"] * W / 1000), int(p["y2"] * H / 1000))
        if b.x2 > b.x1 and b.y2 > b.y1:
            plan.append((int(p["label"]), b))
    plan.sort(key=lambda t: t[0])
    return plan, int(out["columns"]), st


def _inside(b: Box, region: Box, slack: int) -> bool:
    cx, cy = (b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2
    return (region.x1 - slack <= cx <= region.x2 + slack) and (region.y1 - slack <= cy <= region.y2 + slack)


def refine(region: Box, numbers: list[Box], slack: int) -> tuple[Box, list[Box]]:
    """Grow Spark's region to cover every SAM number whose center falls in it (plus slack)."""
    parts = [b for b in numbers if _inside(b, region, slack)]
    if not parts:
        return region, []
    u = _union(parts + [region])
    return u, parts


def _sam_numbers(img: Image.Image) -> tuple[list[Box], meta.CallStats | None, str]:
    try:
        raw, st = meta.segment(img, "number")
        return [b for b in parse_boxes(raw) if b.conf >= 0.3], st, ""
    except Exception as e:  # SAM down: Spark's plan alone still works
        return [], None, str(e)[:120]


def _sam_only(img: Image.Image, numbers: list[Box]) -> list[Problem]:
    W, _ = img.size
    groups = [g for g in group_numbers(numbers, W) if len(g) >= 2]
    if not groups:
        return []
    med_h = statistics.median(b.h for b in numbers)
    problems = []
    for i, g in enumerate(groups, 1):
        u = _union(g)
        u = Box(u.x1, u.y1, min(W, u.x2 + int(1.5 * med_h)), u.y2)
        box, crop = _crop(img, u, int(0.6 * med_h), int(0.6 * med_h))
        problems.append(Problem(i, box, crop, parts=g))
    return problems


def segment_page(img: Image.Image) -> Segmentation:
    img = img.convert("RGB")
    W, H = img.size
    steps: list[dict] = []
    with meta.Pool(max_workers=2) as ex:
        f_plan = ex.submit(spark_layout, img)
        f_sam = ex.submit(_sam_numbers, img)
        numbers, st_sam, sam_err = f_sam.result()
        try:
            plan, columns, st_plan = f_plan.result()
            plan_err = ""
        except Exception as e:
            plan, columns, st_plan, plan_err = [], 0, None, str(e)[:120]

    if st_plan is not None:
        steps.append({"model": meta.SPARK,
                      "action": f"planned the page: {len(plan)} problems in {columns} column(s)",
                      "seconds": round(st_plan.seconds, 1), "usd": round(st_plan.usd, 5)})
    steps.append({"model": meta.SAM,
                  "action": (f'segment prompt "number": {len(numbers)} numbers found' if not sam_err
                             else f"SAM unavailable ({sam_err})"),
                  **({"seconds": round(st_sam.seconds, 1), "usd": st_sam.usd} if st_sam else {})})

    if plan:
        pad = int(0.012 * max(W, H))
        problems = []
        for label, region in plan:
            box, parts = refine(region, numbers, slack=pad)
            box, crop = _crop(img, box, pad, pad)
            problems.append(Problem(label, box, crop, parts=parts))
        snapped = sum(1 for p in problems if p.parts)
        method = "spark+sam" if snapped else "spark"
        steps.append({"model": "code",
                      "action": f"tightened {snapped} of {len(problems)} problem boxes to SAM's number geometry"})
    else:
        problems = _sam_only(img, numbers)
        method = "sam-only"
        steps.append({"model": "code", "action": f"Spark plan unavailable ({plan_err}); grouped SAM numbers "
                                                 f"into {len(problems)} problems"})
    return Segmentation(problems, numbers, method, (W, H), steps)
