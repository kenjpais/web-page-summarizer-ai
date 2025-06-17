import os
import requests
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup


def load_html(source):
    if os.path.isfile(source):
        with open(source, "r", encoding="utf-8") as f:
            return f.read()
    response = requests.get(source)
    response.raise_for_status()
    return response.text


def parse_html(source):
    html = load_html(source)
    soup = BeautifulSoup(html, "html.parser")

    return soup


def parse_tables(soup):
    tables = soup.find_all("table")
    for i, table in enumerate(tables, start=1):
        try:
            table_html = StringIO(str(table))
            df = pd.read_html(table_html)[0]
            print(f"\nTable {i}:")
            print(df.to_string(index=False))
        except Exception as e:
            print(f"Skipping table {i} due to error: {e}")
            continue
