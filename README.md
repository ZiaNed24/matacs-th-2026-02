# MATACS-TH-2026-02: AI Proposal Triage Design

| | |
|---|---|
| **Name** | Zia Ul Haq |
| **Reference** | MATACS-TH-2026-02 |
| **Time actually spent** | About 60 minutes |

## Files

| File | What it is |
|---|---|
| [WRITEUP.md](WRITEUP.md) | Answers to the five questions, plus assumptions |
| [diagram/process-flow.png](diagram/process-flow.png) | Process flow from upload to ranked output, showing AI steps, rule steps, human checkpoints and the audit log |
| [PROMPTS.md](PROMPTS.md) | The extraction prompt, exactly as sent |
| [ranking.json](ranking.json) | Expected ranking of proposals A–E |
| [prototype/](prototype/) | Optional script: AI extraction, then rule-based scoring ([prototype/README.md](prototype/README.md)) |

## Design in one paragraph

AI reads, code decides, a person approves.

1. **AI extraction.** One AI call per proposal turns the PDF text into facts listed in the admin's criteria. Every fact comes with an exact quote from the proposal. The call also reports any text that tries to instruct the AI.
2. **Code checks.** Code confirms each quote really appears in the proposal.
3. **Rules.** Rules apply the mandatory checks, the budget and the 16-week limit. They then compute the weighted score and the rank.
4. **Human review.** Anything uncertain is **flagged** for a person instead of being guessed. A person makes the award.

## Result on the sample set

| Proposal | Status | Score | Why |
|---|---|---|---|
| A | ranked #1 | 96.0 | Most experience, fastest schedule, complete team plan |
| E | ranked #2 | 83.7 | Best warranty, least experience |
| C | flagged | (75.8 provisional) | Contains instructions telling automated reviewers to rank it first |
| D | flagged | (68.2 provisional) | No committed schedule, so the 16-week limit can't be checked |
| B | ineligible | n/a | Bidder holds no electrical licence (subcontractor "to be confirmed") |

## How I used AI tools

I used Claude (Anthropic) to draft most of this submission: the write-up, the extraction prompt, the diagram and the prototype. I then reviewed it and decided what to keep. One change I made: Claude scored experience relative to the best bid, so the strongest bidder always got 100. I changed this to a fixed scale set by the admin (15 or more installs = 100). With the relative method, adding one new bid would change every other bid's score even though their proposals had not changed. A fixed scale keeps scores stable and easier to explain.
