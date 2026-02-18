# Synthetic Insurance Agency (Owner Cockpit Demo)

Deterministic, rule-based synthetic dataset generator for an independent insurance agency in Bozeman, MT.

This repo is designed for **repeatable demo-quality generation** across runs and across machines.

## What this generates

Required tables:

- `producers`
- `carriers`
- `commission_rules`
- `producer_quota`
- `leads`
- `quotes`
- `policies`
- `commission_transactions`

Schema details are documented in `data_dictionary.md`.

## Reproducibility

- Controlled by `company.random_seed` in `assumptions.yml`
- Rule-based generation and validation (no statistical cloning)
- Deterministic IDs and deterministic process flow

## Project layout

- `assumptions.yml` — business knobs and generation controls
- `generation_spec.md` — generation/validation specification
- `data_dictionary.md` — table-level documentation
- `src/schema.py` — table column definitions
- `src/generator.py` — synthetic data generation + export
- `src/validate.py` — integrity and logic checks
- `src/main.py` — CLI entrypoint
- `tests/test_smoke.py` — smoke-level repeatability and validation tests

## Quickstart

```bash
python3 src/main.py --assumptions assumptions.yml
```

### Useful flags

```bash
python3 src/main.py --help
python3 src/main.py --skip-export
python3 src/main.py --output-dir output
```

## Outputs

Generated locally under `output/`:

- `*.csv` (one per table)
- optional SQLite DB (`insurance_demo.db`) when enabled in assumptions

Generated outputs are intentionally gitignored.

## Validation

Validation checks include:

- foreign-key integrity
- date sequencing logic
- non-zero/positive commission and premium checks
- per-producer monthly quote capacity thresholds

Run generator + validation:

```bash
python3 src/main.py --assumptions assumptions.yml
```

Run smoke tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```
