import pandas as pd
import csv
import json
from bs4 import BeautifulSoup
import re

def facts_to_csv(facts, filename):
    """Convert facts JSON to CSV format"""
    data, _ = _extract_facts_data(facts)
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    return df

def _extract_facts_data(facts):
    """Helper function to extract facts data into a list of dictionaries"""
    us_gaap_data = facts.get("facts", {}).get("us-gaap", {})
    
    data = []
    labels_dict = {}
    
    for metric, metric_data in us_gaap_data.items():
        label = metric_data.get("label", metric)
        labels_dict[metric] = label
        description = metric_data.get("description", "")
        units_data = metric_data.get("units", {})
        
        for unit_type, unit_values in units_data.items():
            for entry in unit_values:
                row = {
                    "metric": metric,
                    "label": label,
                    "description": description,
                    "unit": unit_type,
                    "value": entry.get("val"),
                    "filed": entry.get("filed"),
                    "fy": entry.get("fy"),
                    "fp": entry.get("fp"),
                    "form": entry.get("form"),
                    "start": entry.get("start"),
                    "end": entry.get("end"),
                    "accn": entry.get("accn")
                }
                data.append(row)
    
    return data, labels_dict

def facts_DF(ticker, headers=None):
    """Convert facts to a pandas DataFrame
    
    Note: headers parameter is kept for backward compatibility but not used
    """
    from fetch import get_facts
    
    facts = get_facts(ticker)
    data, labels_dict = _extract_facts_data(facts)
    df = pd.DataFrame(data)
    return df, labels_dict

def parse_sec_htm(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'lxml')
    sections = {}
    current_section = None
    section_tags = soup.find_all(lambda tag: tag.name in ['font', 'span', 'div', 'p', 'b'] and re.match(r'Item \d+\w?\.', tag.get_text(strip=True)))
    for tag in section_tags:
        section_name = tag.get_text(strip=True)
        sections[section_name] = ''
        next_tag = tag.next_sibling
        while next_tag and not (hasattr(next_tag, 'name') and re.match(r'Item \d+\w?\.', next_tag.get_text(strip=True) if next_tag.get_text() else '')):
            if hasattr(next_tag, 'get_text'):
                sections[section_name] += next_tag.get_text(strip=True) + '\n'
            next_tag = next_tag.next_sibling
    tables = []
    for table in soup.find_all('table'):
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th']) if td.get_text(strip=True)]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return {
        'sections': sections,
        'tables': tables
    }
