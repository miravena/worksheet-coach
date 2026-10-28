"""Run the test set through the agent and print a score (#10).

For every sheet in tests/worksheets/: does segmentation find the right number of problems, does
each verdict (right/wrong) match the answer key, and was the written answer read correctly.
With --pattern it also finds the pattern and asks Muse Spark whether it names the planted one.

Run:  python3 tests/accuracy.py                 # all sheets, segment + grade
      python3 tests/accuracy.py ws01 ws05       # some sheets
      python3 tests/accuracy.py --pattern       # also score the pattern
      python3 tests/accuracy.py --photo ws11    # use the phone-photo variant where a sheet has one
A change that lowers the score gets reverted.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from coach import answers, grade, meta, pattern, segment  # noqa: E402

SHEETS = Path(__file__).parent / "worksheets"
OUT = Path(__file__).resolve().parent.parent / "out" / "accuracy"

MATCH_SCHEMA = {
    "type": "object",
    "properties": {"same": {"type": "boolean"}},
    "required": ["same"],
    "additionalProperties": False,
}


def pattern_matches(found: str, planted: str | None) -> bool:
    if not planted:
        f = found.strip().lower()
        return f in ("no mistakes", "none", "") or "no pattern" in f
    out, _ = meta.chat([{"role": "user", "content":
                         "A math teacher wrote description A of a learner's habit. An agent wrote "
                         "description B from the same worksheet. Would the teacher agree B names the "
                         "same wrong procedure, even if worded differently, more specific, or more "
                         "general? Answer false if B names a different procedure or only part of a "
                         f"two-way habit.\nA: {planted}\nB: {found}"}],
                       schema=MATCH_SCHEMA, schema_name="match", effort="low")
    return bool(out["same"])


def run_sheet(ws: str, with_pattern: bool, photo: bool = False) -> dict:
    key = json.loads((SHEETS / f"{ws}.json").read_text())
    img = Image.open(SHEETS / ((key.get("photo") if photo else None) or f"{ws}.png"))
    t0 = time.time()
    seg = segment.segment_page(img)
    verdicts = grade.grade_all(seg.problems, key.get("instructions", ""))
    failed = [p for p, v in zip(seg.problems, verdicts) if v.error]
    if failed:
        redo = {v.index: v for v in grade.grade_all(failed, key.get("instructions", ""))}
        verdicts = [redo.get(v.index, v) for v in verdicts]
    rows = []
    for k in key["problems"]:
        v = next((v for v in verdicts if v.index == k["n"]), None)
        if v is None or v.error:
            rows.append({"n": k["n"], "verdict_ok": False, "read_ok": False,
                         "error": v.error if v else "no crop"})
            continue
        rows.append({
            "n": k["n"],
            "verdict_ok": v.is_correct == k["is_correct"],
            "read_ok": bool(answers.same(v.written_answer, k["written_answer"])),
            "pred": v.is_correct, "truth": k["is_correct"],
            "read": v.written_answer, "written": k["written_answer"],
            "mistake": v.mistake,
        })
    res = {
        "sheet": ws, "title": key["title"], "method": seg.method,
        "found": len(seg.problems), "expected": len(key["problems"]),
        "verdicts_ok": sum(r["verdict_ok"] for r in rows), "reads_ok": sum(r["read_ok"] for r in rows),
        "n": len(rows), "rows": rows,
    }
    if with_pattern:
        pat = pattern.find_pattern({"title": key["title"], "subject": key["title"],
                                    "level": key.get("level", "")}, verdicts)
        res["pattern_found"] = pat["pattern"]
        res["pattern_planted"] = key.get("pattern")
        res["pattern_ok"] = pattern_matches(pat["pattern"], key.get("pattern"))
    res["seconds"] = round(time.time() - t0, 1)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheets", nargs="*")
    ap.add_argument("--pattern", action="store_true")
    ap.add_argument("--photo", action="store_true", help="use wsNN_photo.jpg when the key names one")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    sheets = a.sheets or sorted(p.stem for p in SHEETS.glob("ws*.json"))
    spent0 = meta.LEDGER.total
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(lambda s: run_sheet(s, a.pattern, a.photo), sheets))

    print(f"{'sheet':<6} {'title':<28} {'split':>7} {'verdicts':>9} {'reads':>7}  pattern")
    for r in results:
        pat = ""
        if "pattern_ok" in r:
            pat = ("OK  " if r["pattern_ok"] else "MISS") + f" {r['pattern_found']}"
        split = f"{r['found']}/{r['expected']}"
        print(f"{r['sheet']:<6} {r['title'][:28]:<28} {split:>7} "
              f"{r['verdicts_ok']:>4}/{r['n']:<4} {r['reads_ok']:>3}/{r['n']:<3}  {pat}")
        for row in r["rows"]:
            if not row["verdict_ok"]:
                print(f"         problem {row['n']}: {row}")
    tot = sum(r["n"] for r in results)
    v_ok = sum(r["verdicts_ok"] for r in results)
    rd_ok = sum(r["reads_ok"] for r in results)
    split_ok = sum(r["found"] == r["expected"] for r in results)
    print(f"\nSPLIT  {split_ok}/{len(results)} sheets   VERDICTS {v_ok}/{tot} = {100*v_ok/tot:.1f}%   "
          f"READS {rd_ok}/{tot} = {100*rd_ok/tot:.1f}%", end="")
    if a.pattern:
        p_ok = sum(r.get("pattern_ok", False) for r in results)
        print(f"   PATTERN {p_ok}/{len(results)}", end="")
    print(f"   cost ${meta.LEDGER.total - spent0:.3f}")
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (OUT / f"{stamp}.json").write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
