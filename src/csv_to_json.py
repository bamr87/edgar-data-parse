"""Convert erp-clients.csv to JSON format with proper type coercion."""

import csv
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_CSV = DATA_DIR / "erp-clients.csv"
OUTPUT_JSON = DATA_DIR / "erp-clients.json"

BOOLEAN_FIELDS = {
    "Controlled State",
    "eBonding Enabled",
    "Contract On Hold",
    "Contract Extended",
    "Supported By Partner",
    "Multisite Access",
    "Automated Admin Requests Enabled",
    "FDA",
    "Licensed Site",
    "Has Contract",
    "Monthly Backup Report",
    "Archived Only",
}

INTEGER_FIELDS = {
    "Internal Object ID",
    "O3 Version",
}


def coerce_value(key: str, value: str):
    """Convert string values to appropriate Python/JSON types."""
    if value == "":
        return None

    if key in BOOLEAN_FIELDS:
        return value.lower() == "true"

    if key in INTEGER_FIELDS:
        try:
            return int(value)
        except ValueError:
            return value

    return value


def convert(input_path: Path = INPUT_CSV, output_path: Path = OUTPUT_JSON):
    with open(input_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        records = []
        for row in reader:
            record = {key: coerce_value(key, val) for key, val in row.items()}
            records.append(record)

    with open(output_path, "w", encoding="utf-8") as jsonfile:
        json.dump(records, jsonfile, indent=2, ensure_ascii=False)

    print(f"Converted {len(records)} records → {output_path}")


if __name__ == "__main__":
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INPUT_CSV
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT_JSON
    convert(input_path, output_path)
