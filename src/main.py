import argparse
from fetch import cik_ticker, get_facts, headers, download_filing
from parse import facts_DF, parse_sec_htm
from ai_summarize import summarize_dataframe
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=False)
    parser.add_argument("--url", required=False, help="URL of the SEC HTM filing to process")
    parser.add_argument("--action", choices=["fetch", "parse", "summarize", "process_htm"], default="summarize")
    args = parser.parse_args()

    if args.action == "process_htm":
        if not args.url:
            parser.error("--url is required for process_htm action")
        filename = args.url.split('/')[-1]
        save_path = f"data/{filename}"
        download_filing(args.url, save_path)
        parsed_data = parse_sec_htm(save_path)
        output_path = f"data/{filename.replace('.htm', '')}_parsed.json"
        with open(output_path, 'w') as f:
            json.dump(parsed_data, f, indent=4)
        print(f"Parsed data saved to {output_path}")
        return

    if not args.ticker:
        parser.error("--ticker is required for actions fetch, parse, summarize")

    cik = cik_ticker(args.ticker)
    if args.action in ["fetch", "parse", "summarize"]:
        facts = get_facts(args.ticker)
    if args.action in ["parse", "summarize"]:
        df, _ = facts_DF(args.ticker, headers)
    if args.action == "summarize":
        summary = summarize_dataframe(df, "Provide a summary for financial analysis")
        print(summary)

if __name__ == "__main__":
    main()
