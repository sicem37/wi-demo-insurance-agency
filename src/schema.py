from __future__ import annotations

TABLES = {
    "producers": [
        "producer_id",
        "name",
        "tenure_bucket",
        "role_type",
    ],
    "carriers": [
        "carrier_id",
        "carrier_name",
    ],
    "commission_rules": [
        "lob",
        "is_new_business",
        "commission_rate",
    ],
    "producer_quota": [
        "producer_id",
        "month",
        "quota_new_business_commission",
    ],
    "leads": [
        "lead_id",
        "created_date",
        "source",
        "lob_interest",
        "producer_id",
    ],
    "quotes": [
        "quote_id",
        "lead_id",
        "producer_id",
        "carrier_id",
        "lob",
        "quoted_premium",
        "created_date",
        "quoted_date",
        "status",
        "status_date",
    ],
    "policies": [
        "policy_id",
        "quote_id",
        "producer_id",
        "carrier_id",
        "lob",
        "is_new_business",
        "effective_date",
        "expiration_date",
        "annual_premium",
        "status",
    ],
    "commission_transactions": [
        "txn_id",
        "policy_id",
        "producer_id",
        "txn_date",
        "txn_type",
        "amount",
    ],
}
