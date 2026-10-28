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
| 1:45 to 2:15 | Practice list, answer-key-checked badge, PDF preview, page 2 of the PDF | "Practice is where AI worksheets go wrong: the answer keys. So the agent doesn't trust its own draft. Every answer is solved again by a separate call that never sees the draft; if they disagree, a judge call settles it and the key gets fixed. Each problem also records the answer the habit would give, so the adult knows exactly what to watch for. Muse Image draws the sheet's illustration; the numbers are typeset in code, so no digit is ever misdrawn." |
| 2:15 to 2:35 | Accuracy table in the README, a second sample (nursing dosage or trades area/perimeter) | "We built a 30-sheet test set: handwriting, phone photos, two columns, stacked problems, GED, ASVAB and nursing math. Every sheet split correctly; 184 of 184 verdicts and written answers right." |
| 2:35 to 2:55 | 30-second summary on screen | "And the adult gets a 30-second summary: the score, the habit, one thing to try together." |
| 2:55 to 3:00 | Title card: worksheet-coach, repo URL, "Muse Spark · SAM 3.1 · Muse Image" | "worksheet-coach. Five problems that matter, not twenty more." |

Say plainly, somewhere in the video: it is for adults (18+), and it is a helper, not a grade.

## Form text (adapt to the actual fields)

**One line:** An agent that photographs a finished math worksheet, finds the one habit behind the
wrong answers, and writes self-checked practice that targets it, for the adult helping.

**Description:**
worksheet-coach is a multi-step agent for adults helping with math: parents, tutors, teachers,
and adult learners (GED, ASVAB, nursing dosage, trades math). Photograph a completed worksheet.
Muse Spark plans the page and SAM 3.1 gives pixel-accurate geometry for every number, so each
problem is graded on its own crop with evidence the adult can check. Muse Spark then finds the
single rule that reproduces every wrong answer, writes practice problems where that rule gives a
visibly wrong answer, and checks its own answer key with independent re-solves and a judge call
before anything is printed. Muse Image illustrates the printable sheet; numbers are typeset in
code. On a 30-sheet test set with handwriting and phone photos, it split every sheet correctly and
got 184/184 verdicts right.

**Which Meta model does what:**
- Muse Spark 1.3: plans the page layout, grades each problem crop (structured output), finds the
  pattern, drafts practice, re-solves and judges the answer key, writes the summary and the
  illustration idea.
- SAM 3.1: segments every number on the page; problem regions are tightened to its boxes.
- Muse Image 1.0: draws the practice sheet's illustration.

**Track:** indie. **Theme:** Build for Your World.

**Bonus prizes to opt into:** best agentic use case; community vote; most viral (needs the X post
link). Not best open-weights build unless Muse Spark Open is actually used (#17).

**Prior work:** none. Everything was built during the event in this repo.

## X post (draft)

> Your kid wrote 47 + 38 = 75 and 59 + 36 = 85. That's not two mistakes, it's one habit.
>
> I built worksheet-coach for @AIatMeta's hackathon: snap a worksheet, and an agent (Muse Spark
> + SAM 3.1 + Muse Image) finds the habit and writes 5 practice problems, with an answer key it
> checks itself.
>
> [video] [repo link]

Check the organizers' required hashtag or handle in the Discord before posting.
