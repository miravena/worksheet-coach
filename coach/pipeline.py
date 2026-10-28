"""The agent loop, end to end: read the sheet, segment, grade, find the pattern, write practice,
check the practice answer key, summarize. Each step reports to `on_step` so the web page can show
the agent working live (#16).
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from PIL import Image

from . import grade, meta, segment

StepFn = Callable[[dict], None]

HEADER_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "instructions": {"type": "string"},
        "subject": {"type": "string"},
        "level": {"type": "string"},
        "is_worksheet": {"type": "boolean"},
    },
    "required": ["title", "instructions", "subject", "level", "is_worksheet"],
    "additionalProperties": False,
}


def read_header(img: Image.Image) -> tuple[dict, meta.CallStats]:
    msg = meta.user_msg(
        "This should be a photo of a completed worksheet. Read the title and the instructions "
        "exactly as printed (\"\" if none). subject: the topic in a few words (for example "
        "\"two-digit addition\"). level: the likely level (for example \"grade 2\", \"algebra 1\", "
        "\"adult GED\"). is_worksheet: false if this is not a worksheet with problems on it.",
        img,
    )
    return meta.chat([msg], schema=HEADER_SCHEMA, schema_name="header", effort="low")


def run(img: Image.Image, on_step: StepFn | None = None, *, practice: bool = True,
        regrade_failures: bool = True) -> dict:
    # Imported here so the pipeline still runs while these modules are being built.
    from . import pattern as pattern_mod
    from . import practice as practice_mod
    from . import summary as summary_mod

    t0 = time.time()
    spent0 = meta.LEDGER.total
    steps: list[dict] = []

    def step(model: str, action: str, **extra) -> None:
        s = {"t": round(time.time() - t0, 1), "model": model, "action": action, **extra}
        steps.append(s)
        if on_step:
            on_step(s)

    img = img.convert("RGB")
    step("code", "photo received", size=list(img.size))

    # Reading the header and segmenting are independent; run them side by side.
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_header = ex.submit(read_header, img)
        f_seg = ex.submit(segment.segment_page, img)
        header, st = f_header.result()
        seg = f_seg.result()
    step(meta.SPARK, f'read the sheet: "{header["title"]}" ({header["subject"]}, {header["level"]})',
         seconds=round(st.seconds, 1))
    for s in seg.steps:
        step(s["model"], s["action"], **{k: v for k, v in s.items() if k not in ("model", "action")})
    step("code", "boxes ready", kind="boxes",
         numbers=[b.as_list() for b in seg.numbers],
         problems=[p.box.as_list() for p in seg.problems], size=list(seg.size))

    verdicts = grade.grade_all(seg.problems, header["instructions"])
    if regrade_failures:
        failed = [p for p, v in zip(seg.problems, verdicts) if v.error]
        if failed:
            step("code", f"Meta API dropped {len(failed)} call(s); retrying those problems")
            redo = {v.index: v for v in grade.grade_all(failed, header["instructions"])}
            verdicts = [redo.get(v.index, v) for v in verdicts]
    for v in verdicts:
        step(meta.SPARK, f"problem {v.index}: " + ("could not grade" if v.error else
             ("correct" if v.is_correct else f"wrong: {v.mistake}")),
             kind="verdict", verdict=v.to_dict())

    pat = pattern_mod.find_pattern(header, verdicts)
    step(meta.SPARK, f'pattern: {pat["pattern"]}', kind="pattern", pattern=pat)

    prac = None
    if practice:
        prac = practice_mod.make_practice(header, verdicts, pat, on_step=step)

    summ = summary_mod.summarize(header, verdicts, pat, prac)
    step(meta.SPARK, "wrote the 30-second summary", kind="summary")

    wrong = [v for v in verdicts if not v.is_correct and not v.error]
    return {
        "header": header,
        "size": list(seg.size),
        "segmentation": {"method": seg.method,
                         "numbers": [b.as_list() for b in seg.numbers],
                         "problems": [p.box.as_list() for p in seg.problems]},
        "verdicts": [v.to_dict() for v in verdicts],
        "score": {"correct": sum(v.is_correct for v in verdicts), "total": len(verdicts),
                  "wrong": len(wrong), "errors": sum(bool(v.error) for v in verdicts)},
        "pattern": pat,
        "practice": prac,
        "summary": summ,
        "steps": steps,
        "seconds": round(time.time() - t0, 1),
        "usd": round(meta.LEDGER.total - spent0, 4),
    }
