# Prototype (optional)

A small script that runs the design end to end:

1. **AI extraction** with the prompt from [../PROMPTS.md](../PROMPTS.md) ([extract.py](extract.py)).
2. **Code checks** for quotes, types and injected instructions ([extract.py](extract.py), [score.py](score.py)).
3. **Rule-based gates, scoring and ranking** from the admin config ([criteria.json](criteria.json), [score.py](score.py)).

## Run without an API key

```bash
python run.py --fixtures
```

This uses [fixtures/](fixtures/), which holds facts hand-extracted from the five samples. Evidence quotes are omitted because the brief asks that sample text is not committed. The output reproduces the scores and statuses in [../ranking.json](../ranking.json).

## Run with the model

```bash
pip install -r requirements.txt
cp .env.example .env          # add your key and model ID; .env is git-ignored
mkdir samples                 # git-ignored: put A.txt ... E.txt here (text of each sample proposal)
python run.py --samples samples
```

Both modes write two files:

- `out/ranking.json`
- `out/audit.json`, which records the criteria version and hash, model ID, file hashes, raw extractions, validation failures and the score breakdown.

## Files

| File | Role |
|---|---|
| `criteria.json` | What the admin screens would save: fields to extract, mandatory rules, weights, hard limits, version |
| `extract.py` | Builds the prompt from the criteria, calls the model at temperature 0, validates the schema, verifies quotes |
| `score.py` | Mandatory gates, hard limits, injection flag, relative scoring, ranking, reason text. No AI. |
| `run.py` | Wires the steps together and writes the audit file |
