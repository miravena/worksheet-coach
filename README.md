# worksheet-coach

Take a photo of a finished math worksheet. An agent finds which problems are wrong, works out
the **one habit** behind the wrong answers, and writes a short practice sheet aimed at that
habit, with an answer key it has checked against itself. Not twenty more problems. The five
that matter.

**Who it is for:** adults only (18+): tutors, parents, mentors, teachers, and adult learners
checking their own work (GED, nursing dosage math, trades math). It is never used by or aimed at
children (see [docs/RULES.md](docs/RULES.md)).

Built for the [Meta Global AI Developer Hackathon](https://cerebralvalley.ai/e/meta-ai-developer-hackathon)
(indie track, theme "Build for Your World"), Oct 26 to Nov 4, 2026.

## Why

A wrong answer on its own tells you little. "47 + 38 = 75" and "59 + 36 = 85" are the same
mistake: the ten is never carried. An adult with ten minutes at the kitchen table needs to know
*that*, not see red marks, and needs practice where the habit gives a visibly wrong answer.
Answer checkers grade; they do not find the habit, and AI-written practice sheets can quietly
ship wrong answer keys.

## What the agent does

| Step | Model | What happens |
|---|---|---|
| 1. Read the sheet | **Muse Spark 1.3** | Title, instructions, subject and level, in parallel with step 2 |
| 2. Cut it into problems | **Muse Spark 1.3 + SAM 3.1** | Spark plans the page: every problem, its printed number, and roughly where it sits, across columns and stacked layouts. In parallel, SAM segments every `number` on the page with pixel-accurate boxes, and each planned region is tightened to SAM's geometry (Meta's guide suggests this pairing: Spark decides what to segment, SAM gives the pixels). If Spark's plan fails, SAM's boxes are grouped into problems on their own |
| 3. Grade each crop | **Muse Spark 1.3 + Muse Spark Open** | One call per problem, structured output: what it read, what was written, the correct answer, verdict, the mistake and how the wrong answer was produced. Calls the API dropped are retried. At the same time Meta's open-weights **Muse Spark Open** (on Baseten) reads the written answer on the same crop without seeing Spark's reading; if the two readings differ, the problem is flagged so the adult checks the handwriting first |
| 4. Find the pattern | **Muse Spark 1.3** | Looks across all problems, right and wrong, and must show the wrong method reproduces each written answer |
| 5. Write practice | **Muse Spark 1.3** | Drafts 7 problems in the same format. Each records the answer the habit would give, so the habit cannot hide |
| 6. Check its own answer key | **Muse Spark Open** (open weights, on Baseten) | Every answer is solved again by a *different* model, Meta's open-weights Muse Spark Open, which never sees the draft, so agreement is a real second opinion (falls back to a separate Muse Spark 1.3 call when no Baseten key is set). Code compares them (fractions, remainders, money, `x = 5`, algebra via SymPy). Disagreements go to a judge call; wrong keys are corrected or replaced, up to two rounds |
| 7. Printable sheet | **Muse Image 1.0** | Draws the illustration for the top of the sheet from an idea Spark wrote. Problems and answers are typeset in code, so no digit is ever misdrawn. Page 2 is the answer key for the adult |
| 8. Summary | **Muse Spark 1.3** | 30 seconds of reading for the adult: score, the habit, one thing to try together |

The web page shows every step live: SAM's boxes drawn on the photo, each problem turning green
or red as its verdict lands, and a step trace naming the model behind each step.

**Why segment first:** hand a whole page to a model and you lose which problem broke and why.
Per-problem crops keep the evidence attached to the problem, and the adult can check it.

## How well it works

`python3 tests/accuracy.py --photo --pattern` runs the test set and prints the score. The set is
30 generated worksheets with planted mistakes and answer keys (`tests/worksheets/`): school and
adult topics (GED, ASVAB, nursing dosage and trades math), 17 with handwritten answers, 15 as
phone-photo versions (tilt, shadow, blur, JPEG), two-column and stacked layouts, three
all-correct controls, one isolated slip and one blank answer. Run of 2026-10-30, using the
phone photo wherever a sheet has one:

| Measure | Score |
|---|---|
| Sheets split into the right problems | 30/30 |
| Right/wrong verdicts matching the answer key | 184/184 |
| Written answers read correctly | 184/184 |
| Written answers read the same by both readers (Muse Spark 1.3 and Muse Spark Open) | 184/184 |
| Planted habit found (judged by a separate Spark call) | 28/30 |

No misread went unflagged: when both readers agreed, they were right. (The run before had one
difference, spacing only, `-2x + 5` against `-2x+5`; readings are now compared ignoring spaces.)

The two pattern misses, checked by hand, are both the judge call being too strict: on ws13 the
agent wrote "subtracts a negative instead of adding its opposite" for the planted "treats
subtracting a negative as subtracting a positive", and on ws27 "multiplies by 2.2 for every
conversion" for the planted "multiplies by 2.2 when changing pounds to kilograms" (the sheet's
kilograms-to-pounds problems are right, because there multiplying is correct). The run before
missed ws15 and ws25 the same way, so which sheets the judge rejects varies. In earlier runs ws02
sometimes misses: "subtracts the smaller digit from the larger" and "borrows but does not reduce
the tens" give identical answers on all six problems, so that sheet cannot tell them apart.

Cost: about $0.07 to $0.10 per worksheet at list prices (Spark tokens including reasoning, one
SAM image, one Muse Image), plus under a cent on Baseten for Muse Spark Open (the full 30-sheet
test used $0.18 there), 1 to 3 minutes per sheet depending on how the Meta API is responding.

**Known limitations:** the test sheets are generated, so real handwriting and real phone
photos may be harder than the scores above. The agent can misread handwriting; every verdict
shows what it read so the adult can check before acting on it. It is a helper for an adult, not a
grade.

## Run it

Needs Python 3.10+. Without a Meta Model API key the app still runs: the sample sheets replay
saved live runs (`samples/replay/`, every step, verdict and the printable sheet), and only
uploads need a key.

```sh
pip install -r requirements.txt
cp .env.example .env              # add META_MODEL_API_KEY; .env is never committed
git config core.hooksPath .githooks
python3 -m uvicorn app:app --port 8000
# open http://localhost:8000, upload a photo or pick a sample sheet
```

Settings (environment or `.env`):

| Variable | Default | What it does |
|---|---|---|
| `SPEND_CAP_USD` | 60 | Hard cap on estimated spend. Meta's spend limit only sends an email, so the app refuses new calls past this |
| `BASETEN_API_KEY` | unset | Turns on Muse Spark Open: the second handwriting reader and the answer-key check |
| `BASETEN_CAP_USD` | 60 | Separate hard cap for Baseten spend (estimated) |
| `RUNS_PER_IP_PER_HOUR` | 5 | Abuse guard for a public demo |
| `MAX_CONCURRENT_RUNS` | 2 | Runs at once |
| `RUN_COST_ESTIMATE` | 0.30 | Spend assumed per run when checking the cap |
| `DEMO_TOKEN` | unset | If set, runs need `?token=` |
| `REPLAY` | unset | `1` replays a saved run of a sample sheet instead of calling the API; on by default when no key is set |

Command line: `python3 tests/accuracy.py ws01 ws05` scores some sheets;
`python3 -m pytest tests/test_app.py` tests the web app with the pipeline stubbed.

## Code map

| Path | What |
|---|---|
| `coach/meta.py` | Meta Model API client: retries, spend ledger and hard cap |
| `coach/segment.py` | SAM 3.1 segmentation and grouping into problems; Spark fallback |
| `coach/grade.py` | Per-problem grading with an evidence record; the Muse Spark Open second reader |
| `coach/pattern.py` | The pattern across the sheet |
| `coach/practice.py` | Practice drafting and the answer-key self-check |
| `coach/answers.py` | Answer equality in code |
| `coach/pdf.py` | Printable sheet with the Muse Image illustration |
| `coach/summary.py` | The 30-second summary |
| `coach/pipeline.py` | The agent loop, reporting each step |
| `app.py`, `web/` | Web app: upload, live view (Server-Sent Events), results |
| `samples/replay/` | Saved live runs of the eight sample sheets, with their printable sheets, for running without a key |
| `tests/` | Test set generator, accuracy script, web app tests |
| `video/` | Builds the demo video from a live run: AI narration, browser recording, captions |

## Meta models used

`muse-spark-1.3` (Standard mode, so our content is not used for training), `sam-3.1`,
`muse-image-1.0`, all through the Meta Model API. No Contributor-mode models. Plus Meta's
open-weights Muse Spark Open (`meta-models/muse-spark-open-1026`, the hackathon build), served by
Baseten's OpenAI-compatible Model API (`BASETEN_API_KEY` in `.env`), for two independent checks:
a second reading of every handwritten answer, and re-solving every practice answer. It is asked
for JSON in the prompt; strict `json_schema` output made it write whitespace until its token
limit.

## Dependencies and licenses

| Dependency | License |
|---|---|
| [FastAPI](https://github.com/fastapi/fastapi) | MIT |
| [Uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause |
| [python-multipart](https://github.com/Kludex/python-multipart) | Apache-2.0 |
| [Requests](https://github.com/psf/requests) | Apache-2.0 |
| [Pillow](https://github.com/python-pillow/Pillow) | MIT-CMU (HPND) |
| [SymPy](https://github.com/sympy/sympy) | BSD-3-Clause |
| DejaVu fonts (system package, not bundled) | Bitstream Vera license, public domain changes |
| [Kalam](https://github.com/google/fonts/tree/main/ofl/kalam) (Indian Type Foundry), test sheets only, `tests/fonts/` | SIL OFL 1.1 |
| [Patrick Hand](https://github.com/google/fonts/tree/main/ofl/patrickhand) (Patrick Wagesreiter), test sheets only, `tests/fonts/` | SIL OFL 1.1 |
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) voice via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), demo video narration only | Apache-2.0 / MIT |
| [Playwright](https://github.com/microsoft/playwright-python), demo video recording only | Apache-2.0 |
| FFmpeg and Poppler `pdftoppm`, demo video only (run as programs, not bundled) | GPL |

All project code was written during the hackathon, in this repo. The test worksheets are
generated by `tests/make_testset.py`; no real learner's work is used anywhere.

## License

MIT. See [LICENSE](LICENSE).
