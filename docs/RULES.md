# Hackathon rules: what we must get right

Source: the event page and the "Hackathon Terms & Conditions (Official Rules) and Event Waiver"
at https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver, read 2026-10-26.
The organizers may change the terms; recheck that page before submitting.

## Dates (ET)

| When | What |
|---|---|
| Oct 26, 12:00 PM | Hackathon starts (kickoff livestream) |
| Oct 27 to Nov 4 | Workshops from Meta and partners, office hours on Discord |
| **Nov 4, 9:00 PM** | **Submission deadline** |
| Nov 5 to Nov 8 | First round of judging |
| Nov 9 | Closing ceremony: judges watch the top 5 videos per track live and rank them |
| Nov 16 | Community vote winner announced in Discord |

Weekday mornings (ET): Meta office hours in the Discord office-hours channel. Discord also has partner
channels and support bots you can @ for rules questions.

## Event links (all but the livestream need the Cerebral Valley login)

| What | Where |
|---|---|
| Event details, problem statements, schedule | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details |
| Hackathon Discord (join instructions inside) | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/discord |
| Livestream (kickoff, workshops) | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/live |
| Submit | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit |

- Recordings of the kickoff (Oct 26) and of the workshop "Agents 101: Build a Multimodal AI Agent"
  Part 1 (Oct 27) are shared as links in the hackathon Discord announcements. Part 2 is Oct 28,
  12:00 PM ET, on the livestream page.
- The workshop needs Muse Code signed in and a working Model API key, and uses about $7 in tokens.
  Its repo (github.com/meta-models/legal-agent-workshop) has no license: learn from it, never copy
  its code into this repo.
- **Credits:** each participant claims their own $150 through the form linked in the event
  announcements, by Nov 4, 9:00 PM ET. Credits arrive in batches (check the Billing page). A credit
  card must pass Meta's check (a temporary hold of about $20) or the account shows "Account
  restricted" and the credits cannot be used.
- **Billing is pay-as-you-go with no hard cap.** Meta's "Spend Limit" only sends one email alert
  (https://dev.meta.ai/help/billing/spend-limit-alert); usage past the credits is charged to the
  card. So the app enforces its own hard spend cap, and the public demo is guarded against abuse.
- API keys never expire and the last key cannot be deleted; rotate by creating a new key first.

## Build fresh: no code from before the hackathon

The founder confirmed on 2026-10-27 that the entry must be built fresh during the event, starting at
the kickoff (Oct 26, 12:00 PM ET). The Official Rules also require it to be our own original work.

- Every line of project code is written inside the event window, in this repo. The repo's first commit
  is 2026-10-26 17:35 ET, after kickoff.
- **No copying from earlier projects**, including our own: not from ForeverYours, not from an older
  worksheet generator, not from any other private repo. Write it again here instead.
- Third-party open-source libraries, models and tools are allowed if their licenses are followed and
  the project builds on top of them. Record each one in the README with its license.
- Assets (worksheets, images, voice) are made during the event or clearly licensed for reuse.

## Submission

- Submit through Cerebral Valley: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit
  (requires login; the form fields are not visible publicly, so check them early).
- One track per project. We are in the **indie developer** track (individuals or teams of up to 4;
  a team's Representative submits and names every member).
- What to submit (kickoff, Oct 26): the **3-minute demo video** (a major part of judging; produce it
  well, with a good voiceover: the problem, what we built, the product working) and the **public
  GitHub repo** (judges review it).
- The form (seen 2026-10-29, fields in [SUBMISSION.md](SUBMISSION.md)) has no bonus-prize
  checkboxes: most viral needs the link to our X post in its own field; the open-weights and
  creative bonuses are flagged by the judges in round one. It has no live-demo URL field and no
  prior-work question; we have no prior work anyway (everything is built fresh, below).

### How judging works (kickoff)

1. **Pass/fail:** does the project fit a theme and use Meta AI products? Say plainly which Meta
   model does what.
2. **Score 0 to 10** by Meta judges against the rubric below.
3. **Finals (Nov 9):** the top 5 per track are shown on the live stream; judges watch each 3-minute
   video, give feedback, and rank first to fifth.

### Ideas the organizers said to avoid

"Simple chat wrappers, simple RAG apps, image analyzers, or medical advice generators." Pitch and
build worksheet-coach as a multi-step agent (segment, grade, find the pattern, generate practice,
check the answer key), never as a photo analyzer. The pattern and the generated practice sheet are
required, not polish.

## Judging (indie and startup)

| Criterion | Weight | What it means for us |
|---|---|---|
| Impact | 30% | Who benefits, how much it matters, could people really use it, fits a theme |
| Use of Meta AI tooling | 25% | Go beyond a basic integration; surface unexpected capabilities |
| Technical depth and execution | 20% | Sound engineering, refined, real craft |
| Demo | 25% | Working, impressive, holds up live; quality of the demo video |

## Prizes

- Indie: $150K, $100K, $75K, $50K, $25K. Startup: $250K, $150K, $75K, $50K, $25K.
- Bonus awards up to $50K total. They do not reduce track prizes: most viral (post on X), best build
  on Meta open weights (Muse Glimmer or Muse Spark Open), community vote (project gallery), best
  agentic use case ($5K), best creative build ($5K).
- Payment in USD via Cerebral Valley (Tremendous). Winners need a signed waiver and Official Rules
  plus a W-9 (US) or W-8BEN, and pay their own taxes and fees.

## Models and credits

- Build with Meta AI products: Muse Spark, Muse Wonder, Muse Image, Glimmer, SAM 3 / 3.1 via the
  Meta Model API, plus Meta open-weights models. Muse Code is offered as a coding agent.
- $150 Meta Model API credits for accepted participants, valid for the 10-day window. Read the
  Credit Terms before claiming.
- Partner credits for select participants: Baseten $100 + 2M TPM, Modal $100 (first 1,000 teams),
  Fireworks $25. Partners choose who gets them. All credit forms are on the event details page (the
  info icon on the event); credits go out in batches, and Baseten emails selected builders.
- Baseten, Modal and Fireworks are Meta's named partners for hosting Muse Spark Open and Muse
  Glimmer.

## Meta Model API terms (read 2026-10-27)

Sources: [Meta Model API Terms of Service](https://dev.meta.ai/legal/terms-of-service) (updated
2026-10-09), [Acceptable Use Policy](https://dev.meta.ai/legal/acceptable-use-policy),
[models](https://dev.meta.ai/docs/models.md), [geographic use](https://dev.meta.ai/legal/geographic-use-policy).

- **Age, section 10.1:** "You and your End Users must be at least 18 years of age to use the Services
  and Integrated Products" and "you will not create Integrated Products targeted at individuals under
  the age of 18." **This shapes our product** (see the open issue on it): users are adults only (18+):
  tutors, parents, mentors, teachers, and adult students reviewing their own work. Every screen and
  output is addressed to that adult user, and no child ever uses the app.
- **Standard vs Contributor:** Standard models (`muse-spark-1.3`, etc.) do not train on our content
  (5.1). `*-contributor` models may train on it (6.1) and must not get personal data (6.2).
  **Use Standard models only.**
- We own our inputs and outputs (4.1).
- AUP: no emotion recognition in education; no evaluating people on personal traits; do not rely on
  outputs for decisions affecting someone's rights, health or safety; disclose known limitations to
  users; no likeness of real, identifiable people without consent.

Models we plan to use (IDs from the models page, base URL `https://api.meta.ai/v1`):
`sam-3.1` (Responses API, image or video plus text prompt), `muse-spark-1.3` (image input),
`muse-image-1.0` (`/v1/images/generations`, `/v1/images/edits`).

## Ownership, licensing, privacy

- We keep ownership, but the submission is licensed to Meta and partners **perpetually,
  irrevocably, royalty-free, for any purpose**. Anything shared during the event (ideas, pitches,
  screen shares, chat) is non-confidential and licensed the same way.
- The submission must be our own original work, solely owned by us, infringing nobody's rights.
  Open source is allowed if its license is followed and we build on top of it.
- Anything recorded (name, voice, likeness, screen shares, chat) may be used by the organizers forever.

What this means in practice:
- Do not show or submit anything we want to keep proprietary.
- Never screen-share private tooling, internal dashboards, other repos, or keys.
- Use only worksheets we wrote ourselves or that are clearly licensed for reuse. No real children's
  work and no children's faces or names, in the demo or the repo.
- Check the license of every dependency, model and asset before it goes in.
