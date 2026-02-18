# Data Dictionary — Summit Ridge Independent Insurance (Bozeman, MT)

This synthetic dataset is purpose-built for an **Owner Cockpit** insurance-agency command center.
All tables are generated from `assumptions.yml` using a deterministic random seed.

## Grain and Relationship Overview

- **producers**: one row per producer.
- **carriers**: one row per carrier.
- **commission_rules**: one row per `(lob, is_new_business)` commission rule.
- **producer_quota**: one row per `(producer_id, month)` quota target.
- **leads**: one row per lead event (includes controlled duplicate rows).
- **quotes**: one row per quoted lead that reached quote stage.
- **policies**: one row per bound-and-issued policy record, including renewal book baseline.
- **commission_transactions**: one row per commission movement (earned/projected/chargeback/bonus).

### Entity relationship highlights

- `leads.producer_id -> producers.producer_id`
- `quotes.lead_id -> leads.lead_id`
- `quotes.producer_id -> producers.producer_id`
- `quotes.carrier_id -> carriers.carrier_id`
- `policies.quote_id -> quotes.quote_id` for new business (nullable for seeded renewal baseline)
- `policies.producer_id -> producers.producer_id`
- `policies.carrier_id -> carriers.carrier_id`
- `commission_transactions.policy_id -> policies.policy_id` (nullable for monthly bonus txn)
- `commission_transactions.producer_id -> producers.producer_id`

## Table Specifications

## `producers`
| Column | Type | Description |
|---|---|---|
| producer_id | TEXT (PK) | Deterministic producer key (`PROD0001...`). |
| name | TEXT | Synthetic person name. |
| tenure_bucket | TEXT | One of `0-1`, `1-3`, `3-7`, `7+`. |
| role_type | TEXT | `producer` or `senior_producer`. |

## `carriers`
| Column | Type | Description |
|---|---|---|
| carrier_id | TEXT (PK) | Deterministic carrier key (`CAR001...`). |
| carrier_name | TEXT | Carrier display name. |

## `commission_rules`
| Column | Type | Description |
|---|---|---|
| lob | TEXT | LOB: `Personal Auto`, `Home`, `Umbrella`, `Small Commercial`. |
| is_new_business | INTEGER | 1 if new business, 0 if renewal. |
| commission_rate | REAL | Decimal commission rate (e.g., 0.12 = 12%). |

## `producer_quota`
| Column | Type | Description |
|---|---|---|
| producer_id | TEXT | FK to producer. |
| month | DATE (`YYYY-MM-01`) | Quota month anchor. |
| quota_new_business_commission | REAL | Monthly new-business commission quota in USD. |

## `leads`
| Column | Type | Description |
|---|---|---|
| lead_id | TEXT (PK-like) | Deterministic lead key (`LEAD...`) with intentional 1–2% duplicates. |
| created_date | DATE | Lead creation date. |
| source | TEXT nullable | Marketing/referral source. 2–3% intentionally missing. |
| lob_interest | TEXT | Requested line of business. |
| producer_id | TEXT | Assigned producer owner. |

## `quotes`
| Column | Type | Description |
|---|---|---|
| quote_id | TEXT (PK) | Deterministic quote key (`Q...`). |
| lead_id | TEXT | FK to lead. |
| producer_id | TEXT | Producing agent. |
| carrier_id | TEXT | Quoted carrier. |
| lob | TEXT | Line of business quoted. |
| quoted_premium | REAL | Annual quoted premium. |
| created_date | DATE | Inherited lead create date. |
| quoted_date | DATE nullable | Quote timestamp (1–4% missing, even for some bound records). |
| status | TEXT | `Quoted`, `Bound`, `Issued`, or `Lost`. |
| status_date | DATE | Date quote entered current status. |

## `policies`
| Column | Type | Description |
|---|---|---|
| policy_id | TEXT (PK) | Deterministic policy key (`POL...`). |
| quote_id | TEXT nullable | Source quote for new business; null for seeded baseline renewals. |
| producer_id | TEXT | Writing/servicing producer. |
| carrier_id | TEXT | Bound carrier. |
| lob | TEXT | Policy line of business. |
| is_new_business | INTEGER | 1=new business, 0=renewal policy event. |
| effective_date | DATE | Policy effective date. |
| expiration_date | DATE | Policy expiration date (typically +1 year). |
| annual_premium | REAL | Written annual premium. |
| status | TEXT | `Active`, `Renewed`, `Cancelled`, `Lapsed`. |

## `commission_transactions`
| Column | Type | Description |
|---|---|---|
| txn_id | TEXT (PK) | Deterministic transaction key (`TXN...`). |
| policy_id | TEXT nullable | Related policy (null for bonus txn). |
| producer_id | TEXT | Producer credited/debited. |
| txn_date | DATE | Commission transaction date. |
| txn_type | TEXT | `earned`, `projected`, `chargeback`, `bonus`. |
| amount | REAL | Positive/negative USD amount. |

## Demo KPI Coverage

This model supports:
- New business commission vs quota (MTD/YTD) via `commission_transactions` (`earned`) joined to `producer_quota`.
- Total commission earned vs projected via `txn_type` split.
- Producer leaderboard using producer-level aggregation and quote close rates (`quotes`: Bound+Issued / total quoted).
- Pipeline coverage 30/60/90 via open quotes and weighted expected commission.
- Renewal retention by month + LOB using renewal policy events and outcomes.
- Carrier concentration using premium and commission share by `carrier_id`.

## Controlled Mess Included

- 2–3% missing `leads.source`.
- Source naming drift in selected campaign names.
- 1–2% duplicated lead IDs.
- Some `quotes.quoted_date` null despite advanced status.
- Early cancel chargebacks (2–4%) inside 60 days of effective date.
