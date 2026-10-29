# Submission kit: video script, form text, X post

Drafts for #15 (video) and #19 (submit). Check every claim against the latest
`python3 tests/accuracy.py --photo --pattern` run before submitting, and re-read the submit form
fields (#2): the form may ask for things not listed here.

## Recording setup

- Start the app in replay mode so the video never depends on the Meta API being up:
  `REPLAY=1 python3 -m uvicorn app:app --port 8000`. Replays are recorded live runs of the sample
  sheets (`out/cache/`, made by running each sample once without `REPLAY`). Say on screen that
  the trace is a recorded run, sped up; then show one real live run (any uploaded photo) at
  normal speed, cut down in the edit.
- Browser at 1280 px wide, nothing else on screen: no other tabs, terminals, or private tools
  (docs/RULES.md: anything shown is licensed to the organizers).
- Use only the generated test sheets or a sheet you filled in yourself. No real learner's work.

## 3-minute video script

| Time | Picture | Voiceover |
|---|---|---|
| 0:00 to 0:20 | A filled-in worksheet on a table, phone taking a photo | "You're helping someone with math: your kid's homework, a GED student, a nurse studying dosage math. You see the red marks. You don't see *why*. 47 plus 38 is 75; 59 plus 36 is 85. Those aren't two mistakes. They're one habit: the ten never gets carried." |
| 0:20 to 0:35 | App start page, pick the two-column phone photo (Subtracting Negative Numbers) | "worksheet-coach is an agent for the adult in the room. Take a photo; it finds the habit behind the wrong answers and writes the five practice problems that fix it." |
| 0:35 to 1:20 | Live view: boxes appear, problems turn red and green, trace scrolls | "Muse Spark reads the page and plans it: six problems, two columns. At the same time SAM 3.1 finds every number on the page with pixel-accurate boxes, and the agent snaps each problem to that geometry. Then Muse Spark grades each problem on its own crop, so every verdict keeps its evidence: what it read, what was written, what's right." |
| 1:20 to 1:45 | Pattern card and evidence cards | "Then it looks across the whole sheet. Four wrong answers, one rule: subtracting a negative is treated as subtracting. It checks the rule by re-running it on every wrong problem: it reproduces each written answer exactly." |
| 1:45 to 2:15 | Practice list, answer-key-checked badge, PDF preview, page 2 of the PDF | "Practice is where AI worksheets go wrong: the answer keys. So the agent doesn't trust its own draft. Every answer is solved again by a different model, Meta's open-weights Muse Spark Open on Baseten, which never sees the draft; if they disagree, a judge call settles it and the key gets fixed. Each problem also records the answer the habit would give, so the adult knows exactly what to watch for. Muse Image draws the sheet's illustration; the numbers are typeset in code, so no digit is ever misdrawn." |
| 2:15 to 2:35 | Accuracy table in the README, a second sample (nursing dosage or trades area/perimeter) | "We built a 30-sheet test set: handwriting, phone photos, two columns, stacked problems, GED, ASVAB and nursing math. Every sheet split correctly; 184 of 184 verdicts and written answers right." |
| 2:35 to 2:55 | 30-second summary on screen | "And the adult gets a 30-second summary: the score, the habit, one thing to try together." |
| 2:55 to 3:00 | Title card: worksheet-coach, repo URL, "Muse Spark · SAM 3.1 · Muse Image · Muse Spark Open" | "worksheet-coach. Five problems that matter, not twenty more." |

Say plainly, somewhere in the video: it is for adults (18+), and it is a helper, not a grade.

## Form fields and answers

The submit form, as seen on 2026-10-29 (#2). Fields marked * are required. There is no field for
a live demo URL, no bonus-prize checkboxes and no prior-work question: the open-weights bonus is
flagged by the judges in round one, and most viral only needs the X link.

| Field | Answer |
|---|---|
| Team Name * | The founder picks it (for example "worksheet-coach") |
| Team Members | Pre-filled from the Cerebral Valley account; check that it lists exactly the people who built it |
| Track * | Indie developer |
| Problem statement * | Build for Your World |
| X post link (most viral) | The link to the posted X post (draft below); post it before submitting |
| Project Description * | Below |
| Public GitHub Repository * | https://github.com/miravena/worksheet-coach |
| 3-Minute Demo Video * | The YouTube link (upload as Unlisted or Public; check it plays in a private window) |
| Use of Meta products * | Below |
| Why Meta's models matter * | Below |
| Partner feedback (Fireworks, Modal, Baseten) | Baseten (#17); below |
| How likely to build with Meta Model API * | The founder's own answer |
| Overall opinion of Meta Model API * | The founder's own answer |

**Project Description:**
worksheet-coach is a multi-step agent for adults helping with math: parents, tutors, teachers,
and adult learners (GED, ASVAB, nursing dosage, trades math). Take a photo of a finished
worksheet. A wrong answer on its own says little: "47 + 38 = 75" and "59 + 36 = 85" are one habit,
the ten never carried. The agent grades every problem with evidence the adult can check, finds
the single habit that reproduces every wrong answer, and writes a short practice sheet where that
habit gives a visibly wrong answer, with an answer key it checks before anything is printed. Not
twenty more problems: the five that matter. On a 30-sheet test set with handwriting and phone
photos it split every sheet correctly and got 184 of 184 verdicts right. Built entirely during
the event; it is for adults (18+) and is a helper, not a grade.

**Describe your use of Meta products:**
- Muse Spark 1.3 (Standard mode): reads the page and plans it (every problem, its number and
  where it sits, across columns and stacked layouts); grades each problem on its own crop with
  structured output; finds the habit across the sheet and shows it reproduces each wrong answer;
  drafts practice that records the answer the habit would give; judges answer-key disagreements;
  writes the 30-second summary and the illustration idea.
- SAM 3.1: segments every number on the page in parallel with Spark's plan; each planned problem
  is tightened to SAM's pixel boxes (Spark decides what to segment, SAM gives the geometry).
- Muse Image 1.0: draws the printable sheet's illustration; problems and answers are typeset in
  code so no digit is misdrawn.
- Muse Spark Open (open weights, `meta-models/muse-spark-open-1026` on Baseten): re-solves every
  practice answer without seeing the draft, a second opinion from a different model. On
  2026-10-29, 15 of 15 practice answers on three sheets were checked this way, about $0.0003 each.

**Why are Meta's models important to your solution?**
The product only works if a model can read a phone photo of handwriting, plan an irregular page,
and reason about *how* a wrong answer was produced, not just that it is wrong. Muse Spark does
the reading, planning and reasoning with structured output, so every step is checkable in code.
SAM 3.1 adds what a language model cannot: exact pixel geometry, so each problem is graded on
its own crop and the evidence stays attached to it. Muse Image makes the sheet something you
want to print. Together they let one agent go from a photo to a checked practice sheet in a
couple of minutes for about ten cents.

**Partner feedback (Baseten):** what worked, what was hard, in the founder's words. Facts: the
key worked first time and calls take about a second; strict `json_schema` output made the model
write whitespace until its token limit, so we ask for JSON in the prompt instead; and the Baseten docs name `meta-models/muse-spark-open` while the hackathon needs
`meta-models/muse-spark-open-1026`.

**The two opinion questions** are the founder's own. Facts that may help: during the first days
about half of calls failed with `model_not_found` and the app had to retry; on 2026-10-29, 12 of
12 calls succeeded first try in about a second each. Billing has no hard cap, so the app enforces
its own.

## X post (draft)

> Your kid wrote 47 + 38 = 75 and 59 + 36 = 85. That's not two mistakes, it's one habit.
>
> I built worksheet-coach for @AIatMeta's hackathon: snap a worksheet, and an agent (Muse Spark
> + SAM 3.1 + Muse Image) finds the habit and writes 5 practice problems, with an answer key it
> checks itself.
>
> [video] [repo link]

Check the organizers' required hashtag or handle in the Discord before posting.
