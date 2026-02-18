from __future__ import annotations

import argparse
import json

from generator import export_tables, generate_all, load_assumptions
from validate import validate_tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic insurance-agency dataset.")
    parser.add_argument("--assumptions", default="assumptions.yml", help="Path to assumptions YAML/JSON file.")
    parser.add_argument("--skip-export", action="store_true", help="Generate + validate but do not write CSV/SQLite outputs.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional override for simulation.output_dir from assumptions.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    assumptions = load_assumptions(args.assumptions)

    if args.output_dir:
        assumptions.setdefault("simulation", {})["output_dir"] = args.output_dir

    tables = generate_all(assumptions)
    checks = validate_tables(tables)

    if not args.skip_export:
        export_tables(tables, assumptions)

    print("Generated tables:")
    for name, rows in tables.items():
        print(f"- {name}: {len(rows):,} rows")

    print("\nValidation summary:")
    print(json.dumps(checks, indent=2))

    if any(v > 0 for v in checks.values()):
        raise SystemExit(f"Validation failed: {checks}")

    print("\nAll validation checks passed.")
