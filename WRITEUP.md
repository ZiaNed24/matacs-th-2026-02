# Write-up: AI Proposal Triage Design

**The idea in one line:** AI reads, code decides, a person approves. The AI only turns each PDF into facts, each with a quote from the proposal. Rules from the admin's criteria score and rank. A person reviews exceptions and awards.

See the [process-flow diagram](diagram/process-flow.png) and the [sample ranking](ranking.json).

## 1. AI vs. rules

| Step | Done by | Why |
|---|---|---|
| Pull facts from free text (price, weeks, licence, warranty, who leads the team) | **AI** | Bidders word things differently ("past four years"); reading varied language is AI's strength. |
| Detect text that tries to instruct the reviewer or AI | **AI** + keyword scan | AI catches reworded attempts. The keyword scan is a backstop that can't be talked out of the check. |
| Check quotes exist, check types | Code | Has to be exact. |
| Mandatory pass/fail, budget ceiling, 16-week limit | Rules | Compliance must give the same answer every time and be easy to defend. |
| Weighted scores, rank, reason text | Rules | Arithmetic on the admin's weights. An AI "score out of 10" would drift between runs and be hard to explain. |
| Final award | Human | It is the accountable decision. |

**Where I drew the line:** AI handles *understanding language*. Anything that is a *decision* or *arithmetic* stays in code.

**Scoring** ([criteria.json](prototype/criteria.json)), using scales the admin sets:

- Experience: fixed scale, 15 or more installs = 100. The score depends only on that bid.
- Price: lowest eligible price ÷ this price.
- Timeline: shortest weeks ÷ these weeks.
- Warranty: average of panel and workmanship, each scored relative to the best.
- Team: 4-item checklist (named lead, crew, safety plan, monitoring plan).

## 2. Consistency and explainability

- **Repeatable:** scoring is deterministic code, so the same facts always give the same ranking.
- **Controlled extraction:** the AI runs at temperature 0, with a pinned model and a versioned prompt.
- **Ranked twice?** Same result. Extractions are cached per file hash, so re-ranking does not call the AI again. A deliberate re-extraction that changes a field flags that field.
- **Unsupported values:** any value without a matching quote is flagged, never scored.
- **Explainable:** for each proposal the reviewer sees:
  - each criterion's score and weight;
  - the fact used (e.g. "12 weeks");
  - its source quote, which can be clicked to jump to it in the PDF;
  - any flags.

  The one-line reason is generated from this breakdown, so it cannot contradict the numbers.

## 3. Human in the loop

- **Admin:** owns the criteria. Each change creates a new version.
- **Reviewer:** must open every *flagged* and *ineligible* proposal before the list is finalised.
- **Corrections:** the reviewer can correct a fact (e.g. enter D's schedule once confirmed). Code then re-scores; the AI is not called again.
- **Overrides:** a status or position can be overridden, with a mandatory written reason.
- **Award:** a person picks the winner. The tool only recommends.
- **Audit log** (append-only):
  - file hashes, criteria version, prompt version, model ID;
  - raw AI output and validation results;
  - all scores;
  - every correction or override, with who, when, old value, new value and why;
  - the final award.

  Any result can be replayed from the log.

## 4. Changing criteria

- Criteria are **versioned**, never edited in place. Each run records the version it used.
- Saving a new version leaves old results untouched (they are the audit record) and marks them **"scored under v1, v2 available"**.
- **Weight or threshold change:** stored facts are re-scored instantly, at no AI cost.
- **New or reworded criterion:** only the new fields are extracted by AI.
- The reviewer sees a before/after comparison and confirms. One ranking never mixes versions.
- After an award, changes apply only to new batches.

## 5. Risks

| Risk | Guard |
|---|---|
| **Wrong extraction** | Type check and quote check. A warning when OCR quality is poor. The reviewer sees each fact next to its quote. |
| **Made-up facts** | Every fact needs a quote. A quote not found in the text marks the fact unverified and flags the proposal. Missing information becomes null, never a guess. |
| **Manipulation** (C) | Proposal text is wrapped as untrusted data. The model reports instructions instead of obeying them, and the keyword scan checks again. Scoring is code, so a fooled model cannot change ranks; it could only change facts, which still need valid quotes. Flagged proposals need a human decision. |
| **Vague bids** (B, D) | "To be confirmed" never counts as compliance. A missing licence or timeline means ineligible or flagged. |
| **Bias** | The AI extracts facts and never judges quality. Rules see facts, not polish or brand names. Overrides are logged for review. |
| **Relative scoring** | Price, timeline and warranty are relative, so a new bid can shift them. Rankings are compared only within one batch, and the pool is logged. Experience already uses a fixed scale, and the admin can switch the others too. |
| **Cost / outage** | One small call per proposal, cached, and no AI on re-score. If the AI is down, facts can be entered manually and the same rules apply. |
| **Over-trust** | Labelled "recommendation"; award needs human sign-off. |

## Assumptions

- The "last 5 years" window is checked at year level as of 2026. C's stated period starts in 2020, so the reviewer should confirm it.
- A subcontractor "to be confirmed" does not meet "licence held by the bidder", so B is ineligible.
- A missing schedule means flagged, not ineligible, so D is flagged.
- Weekly progress reports do not count as performance monitoring.
- "Assigned at kickoff" does not count as a named lead.
