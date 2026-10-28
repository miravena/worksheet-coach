"""Write five practice problems aimed at the pattern, then check our own answer key (#12, #17).

Generated answer keys are where AI worksheets quietly go wrong, so the agent does not trust its
first draft. Every problem is solved again in a separate Muse Spark call that never sees the
draft answer. Agreement (compared in code: fractions, remainders, money, expressions) marks the
problem checked. On disagreement, a third call decides which answer is right; a problem whose
key was wrong is fixed or replaced, up to two rounds.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from . import answers, meta

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "instructions": {"type": "string"},
        "illustration": {"type": "string"},
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "answer": {"type": "string"},
                    "trap_answer": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["prompt", "answer", "trap_answer", "why"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "instructions", "illustration", "problems"],
    "additionalProperties": False,
}

DRAFT_PROMPT = """Write {n} new practice problems for an adult to give a learner.

Original worksheet: "{title}" ({subject}, {level}). Instructions on it: "{instructions}".
Examples of its problems: {examples}
The learner's mistake pattern: {pattern}
What the practice should target: {focus}

Rules:
- Same format, notation and difficulty as the original problems, so they fit the same page.
- Every problem must be one where the mistaken method gives a WRONG answer (so the practice
  actually exposes the habit). Put the answer the mistaken method would give in trap_answer.
  If there is no mistake pattern, trap_answer is "".
- Vary the numbers; start a little easier than the original and build up.
- prompt: the problem exactly as it should be printed (use / for fractions, x for times, ÷ for
  divide, ^ for powers). Word problems: one or two short sentences about adult, everyday contexts.
- answer: the correct final answer only, in the form the worksheet expects (e.g. "9 R2", "5/6",
  "x = 4", "$30").
- why: one short phrase on what this problem tests.
- title: "Practice: <topic>". instructions: one line, like the original's.
- illustration: one sentence describing a simple line drawing for the top of the sheet that shows
  the idea behind the right method (for example "ten unit cubes being bundled into one ten-rod").
  No text or digits in it, no people.
"""

SOLVE_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "correct_answer": {"type": "string"},
        "a_is_correct": {"type": "boolean"},
        "b_is_correct": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["correct_answer", "a_is_correct", "b_is_correct", "reason"],
    "additionalProperties": False,
}


def solve(prompt: str, instructions: str) -> str:
    out, _ = meta.chat(
        [{"role": "user", "content":
          f'Solve this worksheet problem. Instructions: "{instructions}". Problem: {prompt}\n'
          "Work it out carefully, then give only the final answer in the form a worksheet answer "
          'key would use (e.g. "9 R2", "5/6", "x = 4", "$30").'}],
        schema=SOLVE_SCHEMA, schema_name="solve", effort="low", max_tokens=12000)
    return out["answer"]


def judge(prompt: str, instructions: str, a: str, b: str) -> dict:
    out, _ = meta.chat(
        [{"role": "user", "content":
          f'Worksheet problem: {prompt}\nInstructions: "{instructions}"\n'
          f"Two answer keys disagree. A: {a!r}. B: {b!r}.\n"
          "Solve it yourself step by step, then say which (if either) is correct."}],
        schema=JUDGE_SCHEMA, schema_name="judge", effort="high", max_tokens=16000)
    return out


def _check_one(p: dict, instructions: str) -> dict:
    """Solve independently, compare, and settle disagreements. Mutates and returns p."""
    try:
        independent = solve(p["prompt"], instructions)
    except Exception as e:
        p.update(checked=False, check_note=f"check failed: {str(e)[:120]}")
        return p
    p["independent_answer"] = independent
    agree = answers.same(p["answer"], independent)
    if agree:
        p.update(checked=True, check_note="independent solve agrees")
        return p
    try:
        j = judge(p["prompt"], instructions, p["answer"], independent)
    except Exception as e:
        p.update(checked=False, check_note=f"judge failed: {str(e)[:120]}")
        return p
    if j["a_is_correct"] and not j["b_is_correct"]:
        p.update(checked=True, check_note="independent solve disagreed; judge confirmed the key")
    elif j["b_is_correct"] or answers.same(j["correct_answer"], independent):
        p.update(checked=True, fixed_from=p["answer"], answer=independent,
                 check_note=f"key was wrong ({p['answer']}); corrected to {independent}: {j['reason']}")
    else:
        p.update(checked=False, check_note=f"no agreement: {j['reason']}")
    # A trap answer equal to the right answer means the problem does not expose the habit.
    if p.get("trap_answer") and answers.same(p["trap_answer"], p["answer"]):
        p["checked"] = False
        p["check_note"] = "mistaken method gives the right answer here; does not test the habit"
    return p


def make_practice(header: dict, verdicts, pattern: dict, *, n: int = 5, on_step=None) -> dict:
    def step(model, action, **kw):
        if on_step:
            on_step(model, action, **kw)

    examples = "; ".join(
        f"{v.problem_text} -> {v.correct_answer}" for v in verdicts if not v.error)[:900]
    focus = pattern.get("practice_focus") or pattern.get("skill") or ""
    draft, st = meta.chat(
        [{"role": "user", "content": DRAFT_PROMPT.format(
            n=n + 2, title=header.get("title", ""), subject=header.get("subject", ""),
            level=header.get("level", ""), instructions=header.get("instructions", ""),
            examples=examples, pattern=pattern.get("pattern", ""), focus=focus)}],
        schema=DRAFT_SCHEMA, schema_name="practice", effort="medium", max_tokens=16000)
    step(meta.SPARK, f"drafted {len(draft['problems'])} practice problems aimed at the pattern",
         seconds=round(st.seconds, 1))

    instructions = draft.get("instructions") or header.get("instructions", "")
    pool = draft["problems"]
    rounds = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        checked = list(ex.map(lambda p: _check_one(dict(p), instructions), pool))
    for p in checked:
        if p.get("fixed_from"):
            step(meta.SPARK, f"caught a wrong answer key: {p['prompt']} is {p['answer']}, "
                             f"not {p['fixed_from']}", kind="selfcheck", item=p)
    good = [p for p in checked if p.get("checked")]
    while len(good) < n and rounds < 2:
        rounds += 1
        need = n - len(good)
        step(meta.SPARK, f"{need} problem(s) failed the check; writing replacements")
        more, _ = meta.chat(
            [{"role": "user", "content": DRAFT_PROMPT.format(
                n=need + 1, title=header.get("title", ""), subject=header.get("subject", ""),
                level=header.get("level", ""), instructions=instructions, examples=examples,
                pattern=pattern.get("pattern", ""), focus=focus)
              + "\nDo not repeat these: " + "; ".join(p["prompt"] for p in checked)}],
            schema=DRAFT_SCHEMA, schema_name="practice", effort="medium", max_tokens=16000)
        with ThreadPoolExecutor(max_workers=6) as ex:
            extra = list(ex.map(lambda p: _check_one(dict(p), instructions), more["problems"]))
        checked += extra
        good += [p for p in extra if p.get("checked")]

    final = good[:n]
    if len(final) < n:  # still short: fill with unchecked ones, clearly marked
        final += [p for p in checked if not p.get("checked")][: n - len(final)]
    fixed = sum(1 for p in checked if p.get("fixed_from"))
    step(meta.SPARK, f"answer key checked: {sum(1 for p in final if p.get('checked'))}/{len(final)} "
                     f"verified independently" + (f", {fixed} wrong key(s) caught and fixed" if fixed else ""),
         kind="practice", practice={"problems": final})
    return {
        "title": draft.get("title") or f"Practice: {header.get('subject', '')}",
        "illustration": draft.get("illustration", ""),
        "instructions": instructions,
        "problems": final,
        "drafted": len(checked),
        "keys_fixed": fixed,
        "rounds": rounds,
    }
