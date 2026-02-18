# Insurance Agency Lite Demo — Generation Spec

## Reproducibility
- Deterministic seed is defined at `company.random_seed` in `assumptions.yml`.
- Generator uses Python's seeded `random.Random(...)` and no external nondeterministic source.

## Recommended Dataset Scale
- Producers: **22** (within required 18–25)
- Baseline active renewal policies: **2,640** (within required 1,800–3,500)
- Typical monthly lead volume:
  - Off-peak: **55–90**
  - Peak (Mar–Jun): **95–160**
- Typical monthly quotes: **60–200** depending on season and producer capacity
- Typical monthly new bound policies: **25–90** depending on seasonality + conversion

## Table Schema (minimum set)
1. `producers(producer_id, name, tenure_bucket, role_type)`
2. `carriers(carrier_id, carrier_name)`
3. `commission_rules(lob, is_new_business, commission_rate)`
4. `producer_quota(producer_id, month, quota_new_business_commission)`
5. `leads(lead_id, created_date, source, lob_interest, producer_id)`
6. `quotes(quote_id, lead_id, producer_id, carrier_id, lob, quoted_premium, created_date, quoted_date, status, status_date)`
7. `policies(policy_id, quote_id, producer_id, carrier_id, lob, is_new_business, effective_date, expiration_date, annual_premium, status)`
8. `commission_transactions(txn_id, policy_id, producer_id, txn_date, txn_type, amount)`

## Generation Logic
- **Producer generation**:
  - Tenure buckets sampled with realistic mix.
  - Role type inferred from tenure (more seniors in longer tenure buckets).
- **Carrier mix**:
  - Each carrier has LOB-specific appetite weights.
  - Carrier assigned by weighted random choice per quote/policy LOB.
- **Lead generation**:
  - Monthly leads follow seasonal multipliers.
  - Source sampled from weighted channel mix with naming drift variants.
  - 2–3% of lead source is intentionally null.
  - 1–2% duplicate lead IDs are injected after base generation.
- **Pipeline progression**:
  - Stage flow: Lead → Quoted → Bound/Issued (+ Lost/Quoted open).
  - Lead→Quote conversion varies by peak vs off-peak months.
  - LOB-specific Quote→Bind rates enforce realistic product behavior.
  - Producer quote capacity caps monthly throughput.
  - 1–4% quotes have missing `quoted_date` even when progressed.
- **Policy issuance**:
  - New business policies created from bound/issued quotes.
  - Effective and expiration dates maintain valid temporal ordering.
  - Baseline renewal book is seeded independently for stability.
- **Commission & compensation**:
  - Commission rates vary by LOB and new vs renewal.
  - Earned and projected txn rows generated per policy.
  - Chargebacks are applied to 2–4% of new business inside 60 days.
  - Monthly bonus tier transaction generated from new-business earned commission.

## Validation Rules
- **Foreign keys**:
  - All relationship keys must resolve (except documented nullable keys for seeded renewals/bonus rows).
- **Date logic**:
  - Quote/status dates cannot precede lead creation.
  - Policy expiration must be after effective date.
- **Invoice/commission math**:
  - Premiums must be positive.
  - Commission transaction amounts cannot be zero.
- **Capacity limits**:
  - Quote counts per producer/month must not exceed configured max capacity.

## Output Artifacts
- CSV output per table under `output/` (generated locally, not committed).
- Optional SQLite output at `output/insurance_demo.db` (generated locally, not committed).
- `output/.gitkeep` is the only tracked file in `output/`.
- Validation summary printed at runtime; non-zero violations fail execution.

## Execution
- Generate + validate + export: `python3 src/main.py --assumptions assumptions.yml`
- Validate only (no file output): `python3 src/main.py --assumptions assumptions.yml --skip-export`
- Override output directory: `python3 src/main.py --assumptions assumptions.yml --output-dir output`
