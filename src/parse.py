import pandas as pd
import csv
import json
from bs4 import BeautifulSoup
import re

def facts_to_csv(facts, filename):
    us_gaap_data = facts["facts"]["us-gaap"]
    data = []
    # ... (extracted logic from notebook cell 20)
    # Implement the CSV writing as in the notebook

def facts_DF(ticker, headers):
    # ... (extracted from notebook cell 30)
    # Return df and labels_dict

def parse_sec_htm(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, 'lxml')
    sections = {}
    current_section = None
    section_tags = soup.find_all(lambda tag: tag.name in ['font', 'span', 'div', 'p', 'b'] and re.match(r'Item \\d+\\w?\\.', tag.get_text(strip=True)))
    for tag in section_tags:
        section_name = tag.get_text(strip=True)
        sections[section_name] = ''
        next_tag = tag.next_sibling
        while next_tag and not (hasattr(next_tag, 'name') and re.match(r'Item \\d+\\w?\\.', next_tag.get_text(strip=True) if next_tag.get_text() else '')):
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
