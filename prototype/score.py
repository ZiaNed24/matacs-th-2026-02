"""Rule-based scoring. No AI in this file.

Input : criteria.json (admin config) + one extraction JSON per proposal.
Output: ranking list (same shape as ../ranking.json) + a full breakdown for the audit log.

Same inputs always give the same output: this file is plain arithmetic.
"""
import json
import re

# Phrases that suggest a proposal is talking to the reviewer or the AI instead of describing the bid.
# This is a backstop for the AI's own "embedded_instructions" field, not the only check.
INJECTION_PATTERNS = [
    r"automated (review|system)", r"ignore (all|previous|the above)", r"rank (it|this|us) first",
    r"full marks", r"pre-?approved", r"system prompt", r"as an ai",
]


def _value(ex, key):
    f = ex["fields"].get(key)
    return None if f is None else f.get("value")


def _relative(values, v, higher_is_better):
    """Best value in the batch gets 100. Others are scaled against it. Missing -> 0."""
    present = [x for x in values if x is not None]
    if v is None or not present:
        return 0.0
    if higher_is_better:
        best = max(present)
        return 100.0 * v / best if best else 0.0
    best = min(present)
    return 100.0 * best / v if v else 0.0


def _criterion_score(rule, ex, pool):
    m = rule["method"]
    if m in ("higher_is_better", "lower_is_better"):
        vals = [_value(p, rule["field"]) for p in pool]
        return _relative(vals, _value(ex, rule["field"]), m == "higher_is_better")
    if m == "fixed_scale":
        # Admin-defined scale: score depends only on this bid, so adding a bid never changes it.
        v = _value(ex, rule["field"])
        return 0.0 if v is None else min(v / rule["full_marks_at"], 1.0) * 100.0
    if m == "average_of":
        parts = [_criterion_score(r, ex, pool) for r in rule["parts"]]
        return sum(parts) / len(parts)
    if m == "checklist":
        hits = [bool(_value(ex, f)) for f in rule["fields"]]
        return 100.0 * sum(hits) / len(hits)
    raise ValueError(f"unknown method {m}")


def _mandatory(rule, ex):
    """Returns True (pass), False (fail) or None (cannot tell -> human)."""
    results = []
    for key in rule.get("all_true", []):
        results.append(_value(ex, key))
    for key, minimum in rule.get("min", {}).items():
        v = _value(ex, key)
        results.append(None if v is None else v >= minimum)
    if any(r is False for r in results):
        return False
    if any(r is None for r in results):
        return None
    return True


def injection_hits(ex, source_text=None):
    hits = list(ex.get("embedded_instructions", []))
    if source_text:
        for pat in INJECTION_PATTERNS:
            for m in re.finditer(pat, source_text, re.I):
                hits.append({"location": f"char {m.start()}", "summary": f"pattern '{pat}' matched"})
    return hits


def score_batch(criteria, extractions, sources=None, unverified=None):
    sources = sources or {}
    unverified = unverified or {}
    limits = criteria["project_constraints"]
    rows = {}

    # 1) Mandatory gates and hard project limits
    for ex in extractions:
        pid = ex["proposal"]
        row = {"proposal": pid, "status": "ranked", "issues": [], "gates": {}, "criteria": {}}
        for c in criteria["criteria"]:
            if c["type"] != "mandatory":
                continue
            res = _mandatory(c["rule"], ex)
            row["gates"][c["id"]] = res
            if res is False:
                row["status"] = "ineligible"
                row["issues"].append(f"fails mandatory: {c['name']}")
            elif res is None and row["status"] != "ineligible":
                row["status"] = "flagged"
                row["issues"].append(f"cannot confirm mandatory: {c['name']}")
        for lim in criteria["hard_limits"]:
            v = _value(ex, lim["field"])
            cap = limits[lim["max_from"]]
            if v is None:
                if row["status"] == "ranked":
                    row["status"] = "flagged"
                row["issues"].append(f"{lim['field']} not committed (limit {cap})")
            elif v > cap:
                row["status"] = "ineligible"
                row["issues"].append(f"{lim['field']} {v} exceeds limit {cap}")
        inj = injection_hits(ex, sources.get(pid))
        if inj:
            if row["status"] != "ineligible":
                row["status"] = "flagged"
            row["issues"].append("contains instructions aimed at the reviewer/AI: " + "; ".join(h["summary"].rstrip(".") for h in inj))
        if unverified.get(pid):
            if row["status"] == "ranked":
                row["status"] = "flagged"
            row["issues"].append("evidence not found in source for: " + ", ".join(unverified[pid]))
        start = _value(ex, "installs_period_start_year")
        window_start = limits["evaluation_year"] - limits["experience_window_years"]
        if start is not None and start < window_start:
            row["issues"].append(f"note: experience period starts {start}; some installs may be older than {limits['experience_window_years']} years")
        rows[pid] = row

    # 2) Weighted scoring. The comparison pool = everyone who is not ineligible.
    pool = [ex for ex in extractions if rows[ex["proposal"]]["status"] != "ineligible"]
    for ex in pool:
        row = rows[ex["proposal"]]
        total = 0.0
        for c in criteria["criteria"]:
            if c["type"] != "weighted":
                continue
            s = _criterion_score(c["rule"], ex, pool)
            row["criteria"][c["id"]] = round(s, 1)
            total += s * c["weight"] / 100.0
        row["total"] = round(total, 1)

    # 3) Rank the clean ones; flagged keep a provisional score for the reviewer only.
    ranked = sorted([r for r in rows.values() if r["status"] == "ranked"],
                    key=lambda r: (-r["total"], r["proposal"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return list(rows.values())


def reason(row, criteria):
    names = {c["id"]: c["name"] for c in criteria["criteria"]}
    if row["status"] == "ineligible":
        return "Ineligible: " + "; ".join(i for i in row["issues"] if not i.startswith("note")) + "."
    if row["status"] == "flagged":
        return ("Held for human review: " + "; ".join(i for i in row["issues"] if not i.startswith("note"))
                + f". Provisional score {row['total']} if cleared.")
    crit = row["criteria"]
    best = sorted(crit, key=lambda k: -crit[k])[:2]
    weak = min(crit, key=lambda k: crit[k])
    return (f"Passes all mandatory checks; strongest on {names[best[0]].lower()} ({crit[best[0]]}) and "
            f"{names[best[1]].lower()} ({crit[best[1]]}), weakest on {names[weak].lower()} ({crit[weak]}).")


def to_ranking_json(rows, criteria):
    order = {"ranked": 0, "flagged": 1, "ineligible": 2}
    rows = sorted(rows, key=lambda r: (order[r["status"]], r.get("rank") or 99, r["proposal"]))
    return [{
        "proposal": r["proposal"],
        "rank": r.get("rank"),
        "status": r["status"],
        "score": r["total"] if r["status"] == "ranked" else None,
        "reason": reason(r, criteria),
    } for r in rows]
