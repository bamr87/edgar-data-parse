import requests
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from dotenv import load_dotenv

load_dotenv()

headers = {"User-Agent": os.getenv("USER_AGENT_EMAIL"), "Accept-Encoding": "gzip, deflate"}

logging.basicConfig(level=logging.INFO)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def cik_ticker(ticker):
    ticker = ticker.upper().replace(".", "-")
    response = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
    if response.status_code == 429:
        raise Exception("Rate limit exceeded")
    response.raise_for_status()
    ticker_json = response.json()
    for company in ticker_json.values():
        if company["ticker"] == ticker:
            return {"cik": str(company["cik_str"]).zfill(10), "name": str(company["title"])}
    raise ValueError(f"Ticker {ticker} not found")

# Add other fetch functions similarly, e.g., get_submission_data, get_facts, download_file
# Ensure all requests handle 429 and use retries

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def download_filing(url, save_path):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            raise Exception("Rate limit exceeded")
        response.raise_for_status()
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logging.info(f"Downloaded filing from {url} to {save_path}")
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")
        raise
