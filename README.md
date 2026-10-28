# worksheet-coach

Take a photo of a finished worksheet. Find out which problems are wrong, why, and get a short
practice sheet aimed at the actual mistake. Not twenty more problems. The five that matter.

**Who it is for:** adults only (18+): tutors, parents, mentors, teachers, and adult students
checking their own work. It is never used by or aimed at children (see [docs/RULES.md](docs/RULES.md)).

Built for the [Meta Global AI Developer Hackathon](https://cerebralvalley.ai/e/meta-ai-developer-hackathon)
(indie track, theme "Build for Your World"), Oct 26 to Nov 4, 2026.

## How it works (plan)

1. **SAM 3.1** segments the page into single problems.
2. **Muse Spark** reads each crop, grades it, and explains the mistake in plain language.
3. Across all problems it looks for the pattern (forgetting to carry, place value,
   fraction denominators) and writes practice for that pattern.
4. **Muse Image** draws the picture and word problems so the practice sheet looks like the
   original. Output: a printable PDF and a 30-second summary for the person reviewing the work.

Why segment first: hand a whole page to a model and you lose which problem broke and why.
Per-problem crops keep that.

## Status

Day 1. Nothing to run yet. Work is tracked in GitHub Issues.

## Setup

```sh
cp .env.example .env      # add your Meta Model API key; .env is never committed
git config core.hooksPath .githooks
```

## License

MIT. See [LICENSE](LICENSE).
