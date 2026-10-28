"""Find the mistake pattern across every problem on the sheet (#11).

Grading one problem says what went wrong there. The pattern says what the learner is actually
doing: "adds the denominators" on four of six problems is one misconception, not four slips.
"""

from __future__ import annotations

from . import meta

PATTERN_SCHEMA = {
    "type": "object",
    "properties": {
        "all_correct": {"type": "boolean"},
        "pattern": {"type": "string"},
        "skill": {"type": "string"},
        "explanation": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "integer"}},
        "isolated_slips": {"type": "array", "items": {"type": "integer"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "practice_focus": {"type": "string"},
    },
    "required": ["all_correct", "pattern", "skill", "explanation", "evidence",
                 "isolated_slips", "confidence", "practice_focus"],
    "additionalProperties": False,
}

PATTERN_PROMPT = """Below is the graded work from one worksheet ("{title}", {subject}, {level}).
Each problem shows what was printed, what the learner wrote, the correct answer, and the grader's
note.

{rows}

Look across ALL problems, wrong and right, and find the single misconception that explains the
most wrong answers. State it as one mechanical rule the learner follows, general enough to cover
every wrong answer it can (for example "keeps a term's sign when moving it across the equals
sign" covers both "x - 4 = 9 -> 5" and "3x + 5 = 20 -> 25/3", where "subtracts instead of adds"
covers only the first). Check it: apply the rule to each wrong problem and confirm it produces
exactly the written answer; if one is left over, look for a more general rule before calling it a
slip. Right answers matter too: they show what the learner already does well (for example,
additions with no carrying come out right).

Always call the person "the learner". Never guess a gender or use he/she/him/her.

- all_correct: true if every problem is right.
- pattern: the misconception in under 15 words, phrased as what the learner does
  (for example "adds across without carrying the ten"). If all correct: "no mistakes". If only
  one problem is wrong and its wrong answer does not follow a wrong method (a recall slip, a
  miscopied digit): "one slip, no pattern". If the wrong answers show a habit that works in two
  directions (for example swapping two formulas), name both directions.
- skill: the skill to practise, in a few words.
- explanation: two or three plain sentences for the adult: the pattern, which problems show it,
  and why the right answers do not (for example "the ones he got right did not need carrying").
- evidence: problem numbers the pattern explains.
- isolated_slips: wrong problems the pattern does NOT explain.
- confidence: high if the wrong method reproduces every written answer it claims.
- practice_focus: what five practice problems should target. If all correct, a sensible next step
  up in difficulty.
"""


def find_pattern(header: dict, verdicts) -> dict:
    rows = []
    for v in verdicts:
        if v.error:
            rows.append(f"Problem {v.index}: could not be graded.")
            continue
        rows.append(
            f"Problem {v.index}: printed {v.problem_text!r}; wrote {v.written_answer!r}; "
            f"correct {v.correct_answer!r}; " + ("RIGHT" if v.is_correct else f"WRONG ({v.mistake})")
        )
    prompt = PATTERN_PROMPT.format(title=header.get("title", ""), subject=header.get("subject", ""),
                                   level=header.get("level", ""), rows="\n".join(rows))
    out, st = meta.chat([{"role": "user", "content": prompt}], schema=PATTERN_SCHEMA,
                        schema_name="pattern", effort="high", max_tokens=24000)
    out["seconds"] = round(st.seconds, 1)
    out["usd"] = round(st.usd, 5)
    return out

