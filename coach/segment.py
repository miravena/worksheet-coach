"""Cut a worksheet photo into one crop per problem (#7).

SAM 3.1 does not know what a "math problem" is (that prompt returns zero matches), but it
reliably finds every "number" on the page. We group those number boxes into problems: rows
first (vertical gaps), then columns within a row (wide horizontal gaps). If SAM finds too
little, Muse Spark is asked for the problem boxes directly.
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
    method: str  # "sam" or "spark-fallback"
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


SPARK_BOXES_SCHEMA = {
    "type": "object",
    "properties": {
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "integer"},
                    "x1": {"type": "number"}, "y1": {"type": "number"},
                    "x2": {"type": "number"}, "y2": {"type": "number"},
                },
                "required": ["number", "x1", "y1", "x2", "y2"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["problems"],
    "additionalProperties": False,
}


def spark_boxes(img: Image.Image) -> tuple[list[Box], meta.CallStats]:
    """Fallback: ask Muse Spark for one box per problem, as fractions of the page."""
    msg = meta.user_msg(
        "This is a photo of a completed worksheet. Return one bounding box per numbered problem, "
        "covering the printed problem and the written answer. Give coordinates as fractions of the "
        "image width and height (0 to 1), top-left x1,y1 and bottom-right x2,y2. Skip the title, "
        "name/date line and instructions.",
        img,
    )
    out, st = meta.chat([msg], schema=SPARK_BOXES_SCHEMA, schema_name="problem_boxes", effort="low")
    W, H = img.size
    boxes = [Box(int(p["x1"] * W), int(p["y1"] * H), int(p["x2"] * W), int(p["y2"] * H))
             for p in sorted(out["problems"], key=lambda p: p["number"])]
    return boxes, st


def segment_page(img: Image.Image, *, min_problems: int = 2) -> Segmentation:
    img = img.convert("RGB")
    W, H = img.size
    steps: list[dict] = []
    raw, st = meta.segment(img, "number")
    numbers = [b for b in parse_boxes(raw) if b.conf >= 0.3]
    steps.append({"model": meta.SAM, "action": f'segment prompt "number": {len(numbers)} numbers found',
                  "seconds": round(st.seconds, 1), "usd": st.usd})
    groups = group_numbers(numbers, W)
    # Drop lone single-character groups far from the rest (page numbers, dates).
    groups = [g for g in groups if len(g) >= 2]
    method = "sam"
    if len(groups) >= min_problems:
        med_h = statistics.median(b.h for b in numbers)
        problems = []
        for i, g in enumerate(groups, 1):
            u = _union(g)
            # Extend right a little so the answer line and any trailing work are in the crop.
            u = Box(u.x1, u.y1, min(W, u.x2 + int(1.5 * med_h)), u.y2)
            box, crop = _crop(img, u, int(0.6 * med_h), int(0.6 * med_h))
            problems.append(Problem(i, box, crop, parts=g))
        steps.append({"model": "code", "action": f"grouped numbers into {len(problems)} problems"})
    else:
        boxes, st2 = spark_boxes(img)
        method = "spark-fallback"
        steps.append({"model": meta.SPARK, "action": f"SAM found too few problems; Spark boxed {len(boxes)}",
                      "seconds": round(st2.seconds, 1), "usd": round(st2.usd, 5)})
        problems = []
        for i, b in enumerate(boxes, 1):
            box, crop = _crop(img, b, 12, 12)
            problems.append(Problem(i, box, crop))
    return Segmentation(problems, numbers, method, (W, H), steps)
