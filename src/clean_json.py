"""Remove null-valued fields from each record in erp-clients.json."""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_JSON = DATA_DIR / "erp-clients.json"
OUTPUT_JSON = DATA_DIR / "erp-clients-clean.json"


def clean(input_path: Path = INPUT_JSON, output_path: Path = OUTPUT_JSON):
    with open(input_path, encoding="utf-8") as f:
        records = json.load(f)

    cleaned = [
        {k: v for k, v in record.items() if v is not None}
        for record in records
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    orig_fields = sum(len(r) for r in records)
    clean_fields = sum(len(r) for r in cleaned)
    print(f"Records: {len(cleaned)}")
    print(f"Fields: {orig_fields} → {clean_fields} (removed {orig_fields - clean_fields} nulls)")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INPUT_JSON
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT_JSON
    clean(input_path, output_path)
