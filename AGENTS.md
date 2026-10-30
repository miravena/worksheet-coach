# Working in this repo

This is a **public** repo for a hackathon entry. These rules apply to people and AI assistants alike.

- **Commit straight to `main`.** It is a small team; fix forward. No force-push, no history rewrites.
- **Secrets never get committed.** Keys live in `.env` (gitignored). Hooks in `.githooks/` block
  key-shaped strings; enable them with `git config core.hooksPath .githooks`.
- **Cite GitHub issues only** (`#N`) in commits, code and docs. No private tracker ids; the
  pre-push hook blocks them.
- **No private material.** No real children's work, names or faces. No internal tooling paths.
- **AI assistance** is disclosed with a `Co-Authored-By:` trailer naming the model. No
  `Claude-Session:` lines (the pre-push hook blocks them).
- **Build fresh.** All project code is written in this repo during the event (from Oct 26, 12:00 PM ET).
  Never copy code from earlier projects, ours included. Open-source dependencies are fine; list them
  with their licenses in the README.
- **Rules:** read [docs/RULES.md](docs/RULES.md) before building anything that touches data,
  licenses or the submission.
- **Work state** (what is open, who owns it, when it is due) lives in GitHub Issues and milestones,
  not in docs.

## How we work

- **No pull requests.** Test the change locally, commit to `main`, push. One change per commit.
- **Test locally, cheapest first** (API calls cost real money):
  1. `python3 -m pytest tests/test_app.py`: web app with the pipeline stubbed, free.
  2. `REPLAY=1 python3 -m uvicorn app:app --port 8000`: click through the saved sample runs, free.
  3. `python3 tests/accuracy.py ws01 ws13`: a few real sheets, cents.
  4. `python3 tests/accuracy.py --photo --pattern`: the full test set, about $1.70. Run it when
     grading code changes, and once before submitting; then update every number in README,
     docs/SUBMISSION.md and video/ to match.
- **The demo video** (`video/`) is rebuilt once per batch of changes, not after each edit.
