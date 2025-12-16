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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_facts(ticker):
    """Fetch company facts from SEC EDGAR API"""
    cik_data = cik_ticker(ticker)
    cik = cik_data["cik"]
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    response = requests.get(url, headers=headers)
    if response.status_code == 429:
        raise Exception("Rate limit exceeded")
    response.raise_for_status()
    facts = response.json()
    logging.info(f"Fetched facts for {ticker} (CIK: {cik})")
    return facts

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_submission_data(ticker):
    """Fetch company submission data from SEC EDGAR API"""
    cik_data = cik_ticker(ticker)
    cik = cik_data["cik"]
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers=headers)
    if response.status_code == 429:
        raise Exception("Rate limit exceeded")
    response.raise_for_status()
    submissions = response.json()
    logging.info(f"Fetched submissions for {ticker} (CIK: {cik})")
    return submissions

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
