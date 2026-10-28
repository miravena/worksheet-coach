"""The 30-second summary for the adult reviewing the work (#13)."""

from __future__ import annotations

from . import meta

SUMMARY_PROMPT = """Write a summary of about 70 words for an adult (a parent, tutor or teacher, or an
adult learner reviewing their own work) who has 30 seconds. Plain words, no jargon, no
headings, no praise inflation, no judgments about the person, only about the work. Call the person "the learner"; never
guess a gender or use he/she.

Sheet: "{title}" ({subject}, {level}). Score: {correct} of {total} right.
Pattern: {pattern}. {explanation}
Practice written: {practice}

Say: the score, the one habit behind the wrong answers (or that there was none), one concrete
thing to try when working the practice together (for example "say the carry out loud"), and that
the practice sheet targets exactly that. If confidence is low, say what to double-check.
Confidence: {confidence}."""


def summarize(header: dict, verdicts, pattern: dict, practice: dict | None) -> str:
    graded = [v for v in verdicts if not v.error]
    prompt = SUMMARY_PROMPT.format(
        title=header.get("title", ""), subject=header.get("subject", ""), level=header.get("level", ""),
        correct=sum(v.is_correct for v in graded), total=len(verdicts),
        pattern=pattern.get("pattern", ""), explanation=pattern.get("explanation", ""),
        practice=f"{len(practice['problems'])} problems" if practice else "none",
        confidence=pattern.get("confidence", "medium"))
    text, _ = meta.chat([{"role": "user", "content": prompt}], effort="low", max_tokens=6000)
    return text
