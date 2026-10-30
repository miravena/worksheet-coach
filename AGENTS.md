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
