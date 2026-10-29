"""Run the triage pipeline on proposals A-E.

  python run.py --fixtures            # no API key needed: uses hand-extracted facts in fixtures/
  python run.py --samples ./samples   # calls the model on samples/A.txt ... E.txt (folder is git-ignored)

Writes out/ranking.json (same format as the submission) and out/audit.json (full breakdown).
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from score import score_batch, to_ranking_json

HERE = Path(__file__).parent


def load_env():
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fixtures", action="store_true")
    g.add_argument("--samples", type=Path)
    args = ap.parse_args()

    criteria_raw = (HERE / "criteria.json").read_text()
    criteria = json.loads(criteria_raw)
    extractions, sources, unverified = [], {}, {}

    if args.fixtures:
        for p in "ABCDE":
            extractions.append(json.loads((HERE / "fixtures" / f"{p}.json").read_text()))
    else:
        load_env()
        from extract import extract, verify_evidence
        for p in "ABCDE":
            text = (args.samples / f"{p}.txt").read_text()
            sources[p] = text
            ex = extract(criteria, p, text)
            ex["source_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            unverified[p] = verify_evidence(ex, text) + ex.get("schema_problems", [])
            extractions.append(ex)

    rows = score_batch(criteria, extractions, sources, unverified)
    ranking = to_ranking_json(rows, criteria)

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "ranking.json").write_text(json.dumps(ranking, indent=2))
    (out / "audit.json").write_text(json.dumps({
        "run_at": datetime.now(timezone.utc).isoformat(),
        "mode": "fixtures" if args.fixtures else "live",
        "model": os.environ.get("ANTHROPIC_MODEL"),
        "criteria_version": criteria["criteria_version"],
        "criteria_sha256": hashlib.sha256(criteria_raw.encode()).hexdigest(),
        "extractions": extractions,
        "scoring": rows,
    }, indent=2))
    print(json.dumps(ranking, indent=2))


if __name__ == "__main__":
    main()
