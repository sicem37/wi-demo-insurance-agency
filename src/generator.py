from __future__ import annotations

import calendar
import csv
import json
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from schema import TABLES

FIRST_NAMES = ["Avery", "Parker", "Rowan", "Jordan", "Reese", "Taylor", "Morgan", "Casey", "Drew", "Hayden", "Dakota", "Skyler"]
LAST_NAMES = ["Henderson", "Peters", "Carlson", "Murray", "Fischer", "Ramos", "Ellis", "Bennett", "Mason", "Reed", "Owens", "Holt"]


def load_assumptions(path: str = "assumptions.yml") -> dict:
    """Load assumptions from YAML when available, else JSON-compatible YAML.

    This keeps the repo runnable in minimal environments while supporting
    native YAML when PyYAML is installed.
    """
    raw = Path(path).read_text(encoding="utf-8")

    try:
        import yaml  # type: ignore

        return yaml.safe_load(raw)
    except Exception:
        return json.loads(raw)


def month_starts(start_date: str, end_date: str) -> list[date]:
    s = datetime.fromisoformat(start_date).date().replace(day=1)
    e = datetime.fromisoformat(end_date).date().replace(day=1)
    out = []
    cur = s
    while cur <= e:
        out.append(cur)
        cur = date(cur.year + (cur.month == 12), 1 if cur.month == 12 else cur.month + 1, 1)
    return out


def pick_weighted(rng: random.Random, items: list[str], weights: list[float]) -> str:
    return rng.choices(items, weights=weights, k=1)[0]


def add_year(d: date) -> date:
    try:
        return d.replace(year=d.year + 1)
    except ValueError:
        return d + (date(d.year + 1, 3, 1) - date(d.year, 3, 1))


def generate_all(assumptions: dict) -> dict[str, list[dict]]:
    rng = random.Random(assumptions["company"]["random_seed"])

    producers = []
    tenures = ["0-1", "1-3", "3-7", "7+"]
    t_weights = [0.24, 0.31, 0.27, 0.18]
    for i in range(1, assumptions["scale"]["producers_count"] + 1):
        tenure = pick_weighted(rng, tenures, t_weights)
        producers.append({
            "producer_id": f"PROD{i:04d}",
            "name": f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[(i * 2) % len(LAST_NAMES)]}",
            "tenure_bucket": tenure,
            "role_type": "senior_producer" if tenure in {"3-7", "7+"} and rng.random() < 0.5 else "producer",
        })

    carriers = [{"carrier_id": f"CAR{i:03d}", "carrier_name": c["carrier_name"]} for i, c in enumerate(assumptions["carriers"], 1)]
    carrier_by_name = {c["carrier_name"]: c["carrier_id"] for c in carriers}

    commission_rules = []
    for lob in assumptions["lines_of_business"]:
        commission_rules.append({"lob": lob["code"], "is_new_business": 1, "commission_rate": lob["commission_new"]})
        commission_rules.append({"lob": lob["code"], "is_new_business": 0, "commission_rate": lob["commission_renewal"]})

    months = month_starts(assumptions["simulation"]["start_date"], assumptions["simulation"]["end_date"])
    tenure_mult = assumptions["compensation"]["quota"]["tenure_multiplier"]
    base_quota = assumptions["compensation"]["quota"]["base_monthly_new_business_commission"]
    producer_quota = []
    for p in producers:
        for m in months:
            season = 1.1 if m.month in (4, 5, 6) else 0.95 if m.month in (11, 12, 1) else 1.0
            producer_quota.append({
                "producer_id": p["producer_id"],
                "month": m.isoformat(),
                "quota_new_business_commission": round(base_quota * tenure_mult[p["tenure_bucket"]] * season * rng.uniform(0.94, 1.06), 2),
            })

    leads, quotes, policies = [], [], []
    lob_names = [l["code"] for l in assumptions["lines_of_business"]]
    lob_weights = [l["mix_weight"] for l in assumptions["lines_of_business"]]
    lob_cfg = {l["code"]: l for l in assumptions["lines_of_business"]}

    src_names = [s["name"] for s in assumptions["lead_generation"]["sources"]]
    src_weights = [s["weight"] for s in assumptions["lead_generation"]["sources"]]
    src_drift = assumptions["lead_generation"]["source_drift_variants"]

    month_key = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

    capacity = {}
    used = {}
    for p in producers:
        for m in months:
            k = (p["producer_id"], m.isoformat())
            capacity[k] = rng.randint(assumptions["operational_constraints"]["producer_monthly_capacity"]["quotes_min"], assumptions["operational_constraints"]["producer_monthly_capacity"]["quotes_max"])
            used[k] = 0

    lead_id = quote_id = policy_id = 1
    for m in months:
        season = assumptions["lead_generation"]["seasonality"][month_key[m.month - 1]]
        n_leads = round(assumptions["lead_generation"]["base_monthly_leads"] * season * rng.uniform(0.88, 1.14))
        peak = m.month in (3, 4, 5, 6)
        for _ in range(int(n_leads)):
            day = rng.randint(1, min(28, calendar.monthrange(m.year, m.month)[1]))
            created = date(m.year, m.month, day)
            producer_id = pick_weighted(rng, [p["producer_id"] for p in producers], [1] * len(producers))
            lob = pick_weighted(rng, lob_names, lob_weights)
            source = pick_weighted(rng, src_names, src_weights)
            if source in src_drift and rng.random() < 0.18:
                source = rng.choice(src_drift[source])
            if rng.random() < assumptions["scale"]["missing_source_rate"]:
                source = ""
            lead = {
                "lead_id": f"LEAD{lead_id:07d}",
                "created_date": created.isoformat(),
                "source": source,
                "lob_interest": lob,
                "producer_id": producer_id,
            }
            leads.append(lead)

            l2q = assumptions["pipeline"]["stage_probabilities"]["lead_to_quote_peak" if peak else "lead_to_quote_offpeak"]
            mk = date(m.year, m.month, 1).isoformat()
            if rng.random() < l2q and used[(producer_id, mk)] < capacity[(producer_id, mk)]:
                used[(producer_id, mk)] += 1
                lcfg = lob_cfg[lob]
                quoted = max(120.0, rng.gauss(lcfg["avg_annual_premium"], lcfg["premium_stddev"]))
                qd = created + timedelta(days=rng.randint(0, 12))
                sd = qd + timedelta(days=rng.randint(1, 21))

                bind_rate = lcfg["quote_to_bind_rate_peak" if peak else "quote_to_bind_rate_offpeak"]
                if rng.random() < bind_rate:
                    status = "Bound" if rng.random() < 0.35 else "Issued"
                elif rng.random() < assumptions["pipeline"]["stage_probabilities"]["quote_loss_probability"]:
                    status = "Lost"
                else:
                    status = "Quoted"

                carrier_name = pick_weighted(rng, [c["carrier_name"] for c in assumptions["carriers"]], [c["appetite_weights"][lob] for c in assumptions["carriers"]])
                quote = {
                    "quote_id": f"Q{quote_id:07d}",
                    "lead_id": lead["lead_id"],
                    "producer_id": producer_id,
                    "carrier_id": carrier_by_name[carrier_name],
                    "lob": lob,
                    "quoted_premium": round(quoted, 2),
                    "created_date": created.isoformat(),
                    "quoted_date": "" if rng.random() < assumptions["scale"]["quote_missing_quoted_date_rate"] else qd.isoformat(),
                    "status": status,
                    "status_date": sd.isoformat(),
                }
                quotes.append(quote)

                if status in {"Bound", "Issued"}:
                    eff = sd + timedelta(days=rng.randint(1, 10))
                    exp = add_year(eff)
                    policies.append({
                        "policy_id": f"POL{policy_id:08d}",
                        "quote_id": quote["quote_id"],
                        "producer_id": producer_id,
                        "carrier_id": quote["carrier_id"],
                        "lob": lob,
                        "is_new_business": 1,
                        "effective_date": eff.isoformat(),
                        "expiration_date": exp.isoformat(),
                        "annual_premium": round(quoted * rng.uniform(0.96, 1.04), 2),
                        "status": "Active",
                    })
                    policy_id += 1
                quote_id += 1
            lead_id += 1

    # duplicate lead rows (controlled mess)
    dup_count = round(len(leads) * assumptions["scale"]["lead_duplicate_rate"])
    for _ in range(int(dup_count)):
        leads.append(dict(rng.choice(leads)))

    # baseline renewal policies
    baseline_target = assumptions["scale"]["baseline_active_policies"]
    to_add = max(0, baseline_target - len(policies))
    for _ in range(to_add):
        lob = pick_weighted(rng, lob_names, lob_weights)
        lcfg = lob_cfg[lob]
        exp = date(rng.randint(2023, 2026), rng.randint(1, 12), rng.randint(1, 28))
        eff = date(exp.year - 1, exp.month, exp.day)
        policies.append({
            "policy_id": f"POL{policy_id:08d}",
            "quote_id": "",
            "producer_id": pick_weighted(rng, [p["producer_id"] for p in producers], [1] * len(producers)),
            "carrier_id": rng.choice(carriers)["carrier_id"],
            "lob": lob,
            "is_new_business": 0,
            "effective_date": eff.isoformat(),
            "expiration_date": exp.isoformat(),
            "annual_premium": round(max(120.0, rng.gauss(lcfg["avg_annual_premium"], lcfg["premium_stddev"])), 2),
            "status": "Active",
        })
        policy_id += 1

    # commission txns
    rule_map = {(r["lob"], r["is_new_business"]): r["commission_rate"] for r in commission_rules}
    txns = []
    txn_id = 1
    for p in policies:
        rate = rule_map[(p["lob"], p["is_new_business"])]
        base = round(float(p["annual_premium"]) * rate, 2)
        eff = datetime.fromisoformat(p["effective_date"]).date()
        txns.append({"txn_id": f"TXN{txn_id:09d}", "policy_id": p["policy_id"], "producer_id": p["producer_id"], "txn_date": (eff + timedelta(days=rng.randint(0, 5))).isoformat(), "txn_type": "earned", "amount": base})
        txn_id += 1
        txns.append({"txn_id": f"TXN{txn_id:09d}", "policy_id": p["policy_id"], "producer_id": p["producer_id"], "txn_date": (eff - timedelta(days=12)).isoformat(), "txn_type": "projected", "amount": round(base * rng.uniform(0.92, 1.03), 2)})
        txn_id += 1
        if p["is_new_business"] == 1 and rng.random() < assumptions["scale"]["early_cancel_chargeback_rate"]:
            txns.append({"txn_id": f"TXN{txn_id:09d}", "policy_id": p["policy_id"], "producer_id": p["producer_id"], "txn_date": (eff + timedelta(days=rng.randint(15, 59))).isoformat(), "txn_type": "chargeback", "amount": round(-base * rng.uniform(0.5, 1.0), 2)})
            txn_id += 1

    # monthly bonus from new business earned
    tier = sorted(assumptions["compensation"]["monthly_bonus_tiers"], key=lambda x: x["threshold_new_business_commission"])
    policy_new = {p["policy_id"]: p["is_new_business"] for p in policies}
    monthly = {}
    for t in txns:
        if t["txn_type"] != "earned" or policy_new.get(t["policy_id"], 0) != 1:
            continue
        key = (t["producer_id"], t["txn_date"][:7])
        monthly[key] = monthly.get(key, 0.0) + float(t["amount"])
    for (producer_id, ym), amt in monthly.items():
        bonus = 0.0
        for r in tier:
            if amt >= r["threshold_new_business_commission"]:
                bonus = r["bonus_amount"]
        if bonus > 0:
            txns.append({"txn_id": f"TXN{txn_id:09d}", "policy_id": "", "producer_id": producer_id, "txn_date": f"{ym}-28", "txn_type": "bonus", "amount": bonus})
            txn_id += 1

    return {
        "producers": producers,
        "carriers": carriers,
        "commission_rules": commission_rules,
        "producer_quota": producer_quota,
        "leads": leads,
        "quotes": quotes,
        "policies": policies,
        "commission_transactions": txns,
    }


def export_tables(tables: dict[str, list[dict]], assumptions: dict) -> None:
    out = Path(assumptions["simulation"]["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    for t, rows in tables.items():
        with open(out / f"{t}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=TABLES[t])
            w.writeheader()
            for r in rows:
                w.writerow(r)

    if assumptions["simulation"].get("export_sqlite"):
        conn = sqlite3.connect(assumptions["simulation"]["sqlite_path"])
        cur = conn.cursor()
        for t, cols in TABLES.items():
            cur.execute(f"DROP TABLE IF EXISTS {t}")
            cur.execute(f"CREATE TABLE {t} ({', '.join([c + ' TEXT' for c in cols])})")
            for r in tables[t]:
                cur.execute(f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})", [r.get(c, "") for c in cols])
        conn.commit()
        conn.close()
