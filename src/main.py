"""
CLI entrypoint (run from repo root: ``python src/main.py`` or ``cd src && python main.py``).
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure ``src`` is on path when invoked from repo root
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fetch import cik_ticker, download_filing, get_facts  # noqa: E402
from parse import facts_DF, parse_sec_htm  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=False)
    parser.add_argument(
        "--url",
        required=False,
        help="URL of the SEC HTM filing to process",
    )
    parser.add_argument(
        "--action",
        choices=["fetch", "parse", "summarize", "process_htm"],
        default="process_htm",
    )
    args = parser.parse_args()

    if args.action == "process_htm":
        if not args.url:
            parser.error("--url is required for process_htm action")
        filename = args.url.rstrip("/").split("/")[-1]
        data_dir = _SRC.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        save_path = data_dir / filename
        download_filing(args.url, str(save_path))
        parsed_data = parse_sec_htm(save_path)
        output_path = data_dir / f"{filename.replace('.htm', '').replace('.txt', '')}_parsed.json"
        output_path.write_text(json.dumps(parsed_data, indent=2), encoding="utf-8")
        print(f"Parsed data saved to {output_path}")
        return

    if not args.ticker:
        parser.error("--ticker is required for actions fetch, parse, summarize")

    if args.action == "fetch":
        facts = get_facts(args.ticker)
        out = _SRC.parent / "data" / f"{args.ticker.upper()}_companyfacts.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(facts, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
        return

    df, labels = facts_DF(args.ticker, None)
    if args.action == "parse":
        csvp = _SRC.parent / "data" / f"{args.ticker.upper()}_facts.csv"
        csvp.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csvp, index=False)
        print(f"Wrote {csvp} ({labels})")
        return

    if args.action == "summarize":
        try:
            from ai_summarize import summarize_dataframe
        except ImportError:
            print("Install langchain/openai for summarize action.")
            return
        summary = summarize_dataframe(df, "Provide a summary for financial analysis")
        print(summary)


if __name__ == "__main__":
    main()
