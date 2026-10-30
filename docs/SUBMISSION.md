# Submission kit: video script, form text, X post

Drafts for #15 (video) and #19 (submit). Check every claim against the latest
`python3 tests/accuracy.py --photo --pattern` run before submitting, and re-read the submit form
fields (#2): the form may ask for things not listed here.

## The video

Built by script from a real live run, no hand editing (`video/`, see its README):
narration lines and the picture plan are in `video/shots.json`; `narrate.py` voices them with
Kokoro TTS (AI voice, af_heart); `record.py` films a live run of sample #13 in the browser;
`cards.py` makes the accuracy and title cards; `assemble.py` cuts the picture to the voice,
burns in captions (the video must make sense muted, as on X) and labels the live run, with
its speed-up, on screen. v1 (2026-10-29) runs 2:26.

Rules it follows (docs/RULES.md): only the generated test sheets; nothing on screen but the
app; it says it is for adults and a helper, not a grade, and that everything shown was built
during the hackathon; the title card credits the AI narration.

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
- Muse Spark Open (open weights, `meta-models/muse-spark-open-1026` on Baseten), two independent
  checks by a different model: (1) a second reading of every handwritten answer, made on the same
  crop without seeing Spark's reading; if the readings differ the problem is flagged for the adult
  (on the 30-sheet test the two readers agreed on 184 of 184 answers); (2) re-solving every practice answer without seeing the draft key, before anything
  is printed. Under a cent per worksheet.

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
