"""Grade each problem crop with Muse Spark (#8).

One call per crop, so the verdict for problem 3 cannot be confused with problem 4. Each call
returns an evidence record the adult can check: what the model read, the answer it worked out,
the verdict, and the reason.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

from . import meta
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
4. is_correct: true only if the written answer is mathematically equal to the correct answer.
5. mistake: if wrong, name the error in a few words (for example "forgot to carry the 1",
   "added the denominators"). If right, "".
6. explanation: one or two plain sentences for the adult checking the work: what went wrong, and
   how the written answer was probably produced. If right, "".
7. readable: false if you cannot read the problem or the answer.
"""


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

    def to_dict(self) -> dict:
        return asdict(self)


def grade_problem(p: Problem, instructions: str = "", effort: str = "low") -> Verdict:
    try:
        out, st = meta.chat(
            [meta.user_msg(GRADE_PROMPT.format(instructions=instructions or "not given"), p.crop)],
            schema=GRADE_SCHEMA, schema_name="grade", effort=effort,
        )
        return Verdict(p.index, p.box.as_list(), **out, seconds=round(st.seconds, 1), usd=round(st.usd, 5))
    except Exception as e:  # keep the sheet going; the adult sees which problem failed
        return Verdict(p.index, p.box.as_list(), "", "", "", False, "", "", False, error=str(e)[:300])


def grade_all(problems: list[Problem], instructions: str = "", effort: str = "low",
              workers: int = 6) -> list[Verdict]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda p: grade_problem(p, instructions, effort), problems))
