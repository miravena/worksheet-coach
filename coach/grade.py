"""Grade each problem crop with Muse Spark (#8).

One call per crop, so the verdict for problem 3 cannot be confused with problem 4. Each call
returns an evidence record the adult can check: what the model read, the answer it worked out,
the verdict, and the reason.

When a Baseten key is set, Muse Spark Open (open weights) reads the written answer on the same
crop at the same time, without seeing Spark's reading. Code compares the two; if they differ the
problem is flagged so the adult checks the handwriting before trusting the verdict.
"""

from __future__ import annotations

from concurrent.futures import as_completed
from dataclasses import asdict, dataclass

from . import answers, meta
from .segment import Problem

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "problem_text": {"type": "string"},
        "written_answer": {"type": "string"},
        "correct_answer": {"type": "string"},
        "is_correct": {"type": "boolean"},
        "mistake": {"type": "string"},
        "explanation": {"type": "string"},
        "readable": {"type": "boolean"},
    },
    "required": ["problem_text", "written_answer", "correct_answer", "is_correct",
                 "mistake", "explanation", "readable"],
    "additionalProperties": False,
}

GRADE_PROMPT = """You are checking one problem cut from a completed math worksheet. The worksheet's
instructions are: "{instructions}".

1. problem_text: copy the printed problem exactly as shown (use / for fractions, ^ for powers).
2. written_answer: copy the handwritten or filled-in answer exactly as written, even if it is wrong.
   Use "" if the answer is blank.
3. correct_answer: solve the problem yourself, carefully, step by step in your head. Give it in the
   same form the worksheet expects.
4. is_correct: true only if the written answer is mathematically equal to the correct answer AND
   in the form the instructions ask for (lowest terms, rounded to a place, with units, as a
   decimal...). "6/9" is wrong when the instructions say "lowest terms".
5. mistake: if wrong, name the error in a few words (for example "forgot to carry the 1",
   "added the denominators"). If right, "".
6. explanation: one or two plain sentences for the adult checking the work: what went wrong, and
   how the written answer was probably produced. Call the person "the learner"; never guess a
   gender. If right, "".
7. readable: false if you cannot read the problem or the answer.

Handwriting: look closely for decimal points, minus signs, fraction bars and remainders ("R")
in the written answer; a missing decimal point changes the answer.
"""

READ_SCHEMA = {
    "type": "object",
    "properties": {"written_answer": {"type": "string"}},
    "required": ["written_answer"],
    "additionalProperties": False,
}

READ_PROMPT = """This is one problem cut from a completed math worksheet. Copy only the handwritten or
filled-in answer exactly as written, even if it is wrong. Use "" if the answer is blank. Use / for
fractions and ^ for powers. Look closely for decimal points, minus signs, fraction bars and
remainders ("R"). Do not solve the problem."""


@dataclass
class Verdict:
    index: int
    box: list[int]
    problem_text: str
    written_answer: str
    correct_answer: str
    is_correct: bool
    mistake: str
    explanation: str
    readable: bool
    seconds: float = 0.0
    usd: float = 0.0
    error: str = ""
    second_read: str | None = None  # Muse Spark Open's reading of the written answer
    reads_agree: bool | None = None  # None when there was no second reading

    def to_dict(self) -> dict:
        return asdict(self)


def _for_model(crop):
    """Small crops lose decimal points; upscale so the short side is at least 360 px."""
    from PIL import Image

    w, h = crop.size
    k = max(1.0, 360 / max(1, min(w, h)))
    return crop.resize((int(w * k), int(h * k)), Image.LANCZOS) if k > 1.01 else crop


def second_read(crop) -> str | None:
    """Muse Spark Open's own reading of the written answer, or None if it is off or failed."""
    if not meta.open_weights_available():
        return None
    try:
        out, _ = meta.open_chat([meta.user_msg(READ_PROMPT, crop)], schema=READ_SCHEMA,
                                schema_name="read", max_tokens=4000)
        return str(out["written_answer"])
    except Exception:
        return None  # Baseten down or out of credit: grade without the second reading


def grade_problem(p: Problem, instructions: str = "", effort: str = "low") -> Verdict:
    crop = _for_model(p.crop)
    with meta.Pool(max_workers=1) as ex:
        second = ex.submit(second_read, crop)
        try:
            out, st = meta.chat(
                [meta.user_msg(GRADE_PROMPT.format(instructions=instructions or "not given"), crop)],
                schema=GRADE_SCHEMA, schema_name="grade", effort=effort,
            )
            v = Verdict(p.index, p.box.as_list(), **out, seconds=round(st.seconds, 1), usd=round(st.usd, 5))
        except Exception as e:  # keep the sheet going; the adult sees which problem failed
            v = Verdict(p.index, p.box.as_list(), "", "", "", False, "", "", False, error=str(e)[:300])
        v.second_read = second.result()
    if v.second_read is not None and not v.error:
        v.reads_agree = answers.same_text(v.written_answer, v.second_read)
    return v


def grade_all(problems: list[Problem], instructions: str = "", effort: str = "low",
              workers: int = 6, on_done=None) -> list[Verdict]:
    """Grade every crop in parallel; `on_done(verdict)` fires as each one finishes."""
    with meta.Pool(max_workers=workers) as ex:
        futs = [ex.submit(grade_problem, p, instructions, effort) for p in problems]
        for f in as_completed(futs):
            if on_done:
                on_done(f.result())
        return [f.result() for f in futs]
