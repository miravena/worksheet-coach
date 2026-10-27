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
| Nov 4 to Nov 8 | Judging |
| Nov 9 | Live finals, winners announced |
| ~Nov 10 | Bonus prizes (community vote, most viral, and others) announced |

## Event links (all but the livestream need the Cerebral Valley login)

| What | Where |
|---|---|
| Event details, problem statements, schedule | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details |
| Hackathon Discord (join instructions inside) | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/discord |
| Livestream (kickoff, workshops) | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/live |
| Submit | https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit |

- The kickoff (Oct 26, 12:00 PM ET) was recorded. The replay is an embed-only Vimeo video that
  plays only on the Cerebral Valley site, so watch it there while logged in.
- Next scheduled stream: Oct 27, 12:00 PM ET.
- **Credits:** each participant claims their own $150 through the form linked in the event
  announcements, by Nov 4, 9:00 PM ET. Credits arrive in batches (check the Billing page). A credit
  card must be on the account to make calls; set a Spend Limit at $150 to avoid charges.

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
- Judges look at a **working demo** and a **demo video**.

## Judging (indie and startup)

| Criterion | Weight | What it means for us |
|---|---|---|
| Impact | 30% | Who benefits, how much it matters, could people really use it, fits a theme |
| Use of Meta AI tooling | 25% | Go beyond a basic integration; surface unexpected capabilities |
| Technical depth and execution | 20% | Sound engineering, refined, real craft |
| Demo | 25% | Working, impressive, holds up live; quality of the demo video |

## Prizes

- Indie: $150K, $100K, $75K, $50K, $25K. Startup: $250K, $150K, $75K, $50K, $25K.
- Bonus awards up to $50K total. They do not reduce track prizes.
- Payment in USD via Cerebral Valley (Tremendous). Winners need a signed waiver and Official Rules
  plus a W-9 (US) or W-8BEN, and pay their own taxes and fees.

## Models and credits

- Build with Meta AI products: Muse Spark, Muse Wonder, Muse Image, Glimmer, SAM 3 / 3.1 via the
  Meta Model API, plus Meta open-weights models. Muse Code is offered as a coding agent.
- $150 Meta Model API credits for accepted participants, valid for the 10-day window. Read the
  Credit Terms before claiming.
- Partner credits for select participants: Baseten $100 + 2M TPM, Modal $100, Fireworks $25.

## Meta Model API terms (read 2026-10-27)

Sources: [Meta Model API Terms of Service](https://dev.meta.ai/legal/terms-of-service) (updated
2026-10-09), [Acceptable Use Policy](https://dev.meta.ai/legal/acceptable-use-policy),
[models](https://dev.meta.ai/docs/models.md), [geographic use](https://dev.meta.ai/legal/geographic-use-policy).

- **Age, section 10.1:** "You and your End Users must be at least 18 years of age to use the Services
  and Integrated Products" and "you will not create Integrated Products targeted at individuals under
  the age of 18." **This shapes our product** (see the open issue on it): the only user is the parent,
  every screen and output is addressed to the parent, and no child ever uses the app.
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
