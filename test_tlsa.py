#!/usr/bin/env python3
"""
End-to-End Test Script for EDGAR Data Parse
Testing with TLSA (Tesla) stock ticker

This script tests:
1. CIK lookup for TLSA
2. Fetching company facts from SEC EDGAR
3. Parsing facts into DataFrame
4. Fetching company submissions
5. Downloading and parsing a recent SEC filing (HTM format)
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fetch import cik_ticker, get_facts, get_submission_data, download_filing, headers
from parse import facts_DF, facts_to_csv, parse_sec_htm

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def test_cik_lookup(ticker):
    """Test 1: CIK Lookup"""
    print_section(f"Test 1: CIK Lookup for {ticker}")
    
    try:
        cik_data = cik_ticker(ticker)
        print(f"✓ Successfully retrieved CIK data for {ticker}")
        print(f"  CIK: {cik_data['cik']}")
        print(f"  Company Name: {cik_data['name']}")
        return cik_data
    except Exception as e:
        print(f"✗ Failed to retrieve CIK data: {e}")
        return None

def test_get_facts(ticker):
    """Test 2: Fetch Company Facts"""
    print_section(f"Test 2: Fetch Company Facts for {ticker}")
    
    try:
        facts = get_facts(ticker)
        print(f"✓ Successfully fetched facts for {ticker}")
        
        # Display summary
        entity_name = facts.get('entityName', 'Unknown')
        cik = facts.get('cik', 'Unknown')
        
        print(f"  Entity Name: {entity_name}")
        print(f"  CIK: {cik}")
        
        # Count metrics
        us_gaap_count = len(facts.get('facts', {}).get('us-gaap', {}))
        dei_count = len(facts.get('facts', {}).get('dei', {}))
        
        print(f"  US-GAAP Metrics: {us_gaap_count}")
        print(f"  DEI Metrics: {dei_count}")
        
        # Save facts to file
        output_file = f"data/{ticker}_facts.json"
        with open(output_file, 'w') as f:
            json.dump(facts, f, indent=2)
        print(f"  Saved facts to: {output_file}")
        
        return facts
    except Exception as e:
        print(f"✗ Failed to fetch facts: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_parse_facts_to_dataframe(ticker):
    """Test 3: Parse Facts to DataFrame"""
    print_section(f"Test 3: Parse Facts to DataFrame for {ticker}")
    
    try:
        df, labels_dict = facts_DF(ticker, headers)
        print(f"✓ Successfully parsed facts to DataFrame")
        print(f"  DataFrame shape: {df.shape}")
        print(f"  Number of unique metrics: {df['metric'].nunique()}")
        print(f"  Number of labels: {len(labels_dict)}")
        
        # Show sample data
        print("\n  Sample data (first 5 rows):")
        print(df.head().to_string())
        
        # Save to CSV
        csv_file = f"data/{ticker}_facts.csv"
        df.to_csv(csv_file, index=False)
        print(f"\n  Saved DataFrame to: {csv_file}")
        
        return df, labels_dict
    except Exception as e:
        print(f"✗ Failed to parse facts: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_get_submissions(ticker):
    """Test 4: Fetch Company Submissions"""
    print_section(f"Test 4: Fetch Company Submissions for {ticker}")
    
    try:
        submissions = get_submission_data(ticker)
        print(f"✓ Successfully fetched submissions for {ticker}")
        
        # Display summary
        name = submissions.get('name', 'Unknown')
        cik = submissions.get('cik', 'Unknown')
        
        print(f"  Company: {name}")
        print(f"  CIK: {cik}")
        
        # Get recent filings
        filings = submissions.get('filings', {}).get('recent', {})
        accession_numbers = filings.get('accessionNumber', [])
        filing_dates = filings.get('filingDate', [])
        forms = filings.get('form', [])
        primary_docs = filings.get('primaryDocument', [])
        
        print(f"  Total recent filings: {len(accession_numbers)}")
        
        # Find recent 10-K or 10-Q
        recent_filing = None
        for i, form in enumerate(forms):
            if form in ['10-K', '10-Q'] and i < len(primary_docs):
                doc = primary_docs[i]
                if doc.endswith('.htm'):
                    recent_filing = {
                        'form': form,
                        'filingDate': filing_dates[i],
                        'accessionNumber': accession_numbers[i].replace('-', ''),
                        'primaryDocument': doc
                    }
                    break
        
        if recent_filing:
            print(f"\n  Recent {recent_filing['form']} filing found:")
            print(f"    Date: {recent_filing['filingDate']}")
            print(f"    Accession: {recent_filing['accessionNumber']}")
            print(f"    Document: {recent_filing['primaryDocument']}")
        else:
            print("\n  No recent 10-K or 10-Q HTM filing found in recent filings")
        
        # Save submissions to file
        output_file = f"data/{ticker}_submissions.json"
        with open(output_file, 'w') as f:
            json.dump(submissions, f, indent=2)
        print(f"\n  Saved submissions to: {output_file}")
        
        return submissions, recent_filing
    except Exception as e:
        print(f"✗ Failed to fetch submissions: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_download_and_parse_filing(ticker, filing_info, cik_data):
    """Test 5: Download and Parse SEC Filing"""
    print_section(f"Test 5: Download and Parse SEC Filing for {ticker}")
    
    if not filing_info:
        print("⚠ No filing info provided, skipping this test")
        return None
    
    try:
        # Construct URL
        cik = cik_data['cik']
        accession = filing_info['accessionNumber']
        doc = filing_info['primaryDocument']
        
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc}"
        print(f"  Downloading from: {url}")
        
        # Download filing
        save_path = f"data/{ticker}_{filing_info['form']}_{filing_info['filingDate']}.htm"
        download_filing(url, save_path)
        print(f"✓ Successfully downloaded filing to: {save_path}")
        
        # Parse filing
        print("\n  Parsing filing...")
        parsed_data = parse_sec_htm(save_path)
        
        sections = parsed_data.get('sections', {})
        tables = parsed_data.get('tables', [])
        
        print(f"✓ Successfully parsed filing")
        print(f"  Sections found: {len(sections)}")
        print(f"  Tables found: {len(tables)}")
        
        # Display section names
        if sections:
            print("\n  Section names:")
            for i, section_name in enumerate(list(sections.keys())[:10]):
                print(f"    {i+1}. {section_name}")
            if len(sections) > 10:
                print(f"    ... and {len(sections) - 10} more sections")
        
        # Display table info
        if tables:
            print("\n  Table information:")
            for i, table in enumerate(tables[:5]):
                print(f"    Table {i+1}: {len(table)} rows, {len(table[0]) if table else 0} columns")
            if len(tables) > 5:
                print(f"    ... and {len(tables) - 5} more tables")
        
        # Save parsed data
        output_file = f"data/{ticker}_{filing_info['form']}_{filing_info['filingDate']}_parsed.json"
        with open(output_file, 'w') as f:
            json.dump(parsed_data, f, indent=2)
        print(f"\n  Saved parsed data to: {output_file}")
        
        return parsed_data
    except Exception as e:
        print(f"✗ Failed to download/parse filing: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run all end-to-end tests"""
    ticker = "TLSA"
    
    print_section("EDGAR Data Parse - End-to-End Test")
    print(f"Testing with ticker: {ticker}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Track test results
    results = {
        'ticker': ticker,
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Test 1: CIK Lookup
    cik_data = test_cik_lookup(ticker)
    results['tests']['cik_lookup'] = cik_data is not None
    
    if not cik_data:
        print("\n⚠ Cannot proceed without CIK data")
        return
    
    # Test 2: Get Facts
    facts = test_get_facts(ticker)
    results['tests']['get_facts'] = facts is not None
    
    # Test 3: Parse Facts to DataFrame
    df, labels = test_parse_facts_to_dataframe(ticker)
    results['tests']['parse_facts'] = df is not None
    
    # Test 4: Get Submissions
    submissions, filing_info = test_get_submissions(ticker)
    results['tests']['get_submissions'] = submissions is not None
    
    # Test 5: Download and Parse Filing
    if filing_info:
        parsed_filing = test_download_and_parse_filing(ticker, filing_info, cik_data)
        results['tests']['parse_filing'] = parsed_filing is not None
    else:
        results['tests']['parse_filing'] = None
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for v in results['tests'].values() if v is True)
    total = sum(1 for v in results['tests'].values() if v is not None)
    
    print(f"Tests Passed: {passed}/{total}")
    print("\nDetailed Results:")
    for test_name, result in results['tests'].items():
        status = "✓ PASS" if result is True else ("✗ FAIL" if result is False else "⊘ SKIP")
        print(f"  {test_name}: {status}")
    
    # Save test results
    results_file = f"data/{ticker}_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nTest results saved to: {results_file}")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results

if __name__ == "__main__":
    main()
