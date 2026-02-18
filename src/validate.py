from __future__ import annotations

from datetime import datetime


def validate_tables(tables: dict[str, list[dict]]) -> dict[str, int]:
    results = {"fk_violations": 0, "date_logic_violations": 0, "invoice_math_violations": 0, "capacity_violations": 0}

    producer_ids = {r["producer_id"] for r in tables["producers"]}
    carrier_ids = {r["carrier_id"] for r in tables["carriers"]}
    lead_ids = {r["lead_id"] for r in tables["leads"]}
    quote_ids = {r["quote_id"] for r in tables["quotes"]}
    policy_ids = {r["policy_id"] for r in tables["policies"]}

    for l in tables["leads"]:
        if l["producer_id"] not in producer_ids:
            results["fk_violations"] += 1
    for q in tables["quotes"]:
        if q["lead_id"] not in lead_ids or q["producer_id"] not in producer_ids or q["carrier_id"] not in carrier_ids:
            results["fk_violations"] += 1
    for p in tables["policies"]:
        if p["producer_id"] not in producer_ids or p["carrier_id"] not in carrier_ids:
            results["fk_violations"] += 1
        if p["quote_id"] and p["quote_id"] not in quote_ids:
            results["fk_violations"] += 1
    for t in tables["commission_transactions"]:
        if t["producer_id"] not in producer_ids:
            results["fk_violations"] += 1
        if t["policy_id"] and t["policy_id"] not in policy_ids:
            results["fk_violations"] += 1

    for q in tables["quotes"]:
        created = datetime.fromisoformat(q["created_date"]).date()
        status = datetime.fromisoformat(q["status_date"]).date()
        if status < created:
            results["date_logic_violations"] += 1
        if q["quoted_date"]:
            quoted = datetime.fromisoformat(q["quoted_date"]).date()
            if quoted < created:
                results["date_logic_violations"] += 1

    for p in tables["policies"]:
        eff = datetime.fromisoformat(p["effective_date"]).date()
        exp = datetime.fromisoformat(p["expiration_date"]).date()
        if exp <= eff:
            results["date_logic_violations"] += 1
        if float(p["annual_premium"]) <= 0:
            results["invoice_math_violations"] += 1

    for t in tables["commission_transactions"]:
        if float(t["amount"]) == 0:
            results["invoice_math_violations"] += 1

    quote_counts = {}
    for q in tables["quotes"]:
        key = (q["producer_id"], q["created_date"][:7])
        quote_counts[key] = quote_counts.get(key, 0) + 1
    results["capacity_violations"] = sum(1 for _, c in quote_counts.items() if c > 58)

    return results
