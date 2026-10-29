"""The second reader and answer comparison, with the model calls stubbed (#17)."""

import pytest
from PIL import Image

from coach import answers, grade, meta
from coach.segment import Box, Problem

GRADED = {"problem_text": "5 - (-3) =", "written_answer": "2", "correct_answer": "8",
          "is_correct": False, "mistake": "m", "explanation": "e", "readable": True}


@pytest.mark.parametrize("a,b,want", [
    ("-2x + 5", "-2x+5", True), ("3x - 2", "3x-2", True), ("2(x+1)", "2x+2", True),
    ("-2x + 5", "-2x - 5", False), ("5/6", "10/12", True), ("9 R2", "9 R3", False),
])
def test_same_values(a, b, want):
    assert bool(answers.same(a, b)) is want


def test_same_text_keeps_form():
    assert answers.same_text("-2x + 5", "-2X+5")
    assert not answers.same_text("10/12", "5/6")  # equal values, different handwriting


def problem():
    return Problem(1, Box(0, 0, 40, 30), Image.new("RGB", (40, 30), "white"))


@pytest.fixture
def spark(monkeypatch):
    monkeypatch.setattr(meta, "chat", lambda *a, **k: (dict(GRADED), meta.CallStats("s", 0.1, 0.0, 1, 0, 0)))


def test_no_baseten_key_means_no_second_read(spark, monkeypatch):
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
    v = grade.grade_problem(problem())
    assert v.second_read is None and v.reads_agree is None


@pytest.mark.parametrize("read,agree", [("2", True), ("2 ", True), ("7", False)])
def test_second_read_flags_disagreement(spark, monkeypatch, read, agree):
    monkeypatch.setenv("BASETEN_API_KEY", "test")
    monkeypatch.setattr(meta, "open_chat", lambda *a, **k: ({"written_answer": read}, None))
    v = grade.grade_problem(problem())
    assert v.second_read == read and v.reads_agree is agree


def test_baseten_failure_still_grades(spark, monkeypatch):
    monkeypatch.setenv("BASETEN_API_KEY", "test")

    def down(*a, **k):
        raise meta.MetaAPIError("HTTP 503")

    monkeypatch.setattr(meta, "open_chat", down)
    v = grade.grade_problem(problem())
    assert v.written_answer == "2" and v.reads_agree is None
