"""
Fetch current S&P 500 constituents from WRDS CRSP.

CRSP stores S&P 500 membership in crsp.msp500list (permno, start, ending).
Tickers live in crsp.dsenames. We join the two on permno.

Logic:
  1. From msp500list: permnos currently in the index
     (ending date is the latest/max, i.e., still a member)
  2. From dsenames: map those permnos to their most recent ticker
"""

import wrds
import pandas as pd
from pathlib import Path

WRDS_USERNAME = "feketema"
OUTPUT_PATH = Path("sp500_tickers.csv")

print("=" * 80)
print("Fetching current S&P 500 constituents from WRDS CRSP")
print("=" * 80)

print("\n[1/4] Connecting to WRDS...")
conn = wrds.Connection(wrds_username=WRDS_USERNAME)
print("Connected.")

# Step 1: Get permnos currently in the S&P 500
print("\n[2/4] Getting current S&P 500 permnos from msp500list...")
query_members = """
    SELECT permno, start, ending
    FROM crsp.msp500list
    WHERE ending = (SELECT MAX(ending) FROM crsp.msp500list)
    ORDER BY permno
"""
members = conn.raw_sql(query_members)
print(f"Found {len(members)} current members (as of ending date {members['ending'].iloc[0]})")

permno_list = tuple(int(p) for p in members['permno'].tolist())

# Step 2: Map permnos to tickers via dsenames (most recent name per permno)
print("\n[3/4] Mapping permnos to tickers via dsenames...")
query_tickers = f"""
    SELECT DISTINCT ON (permno) permno, ticker, comnam, namedt, nameendt
    FROM crsp.dsenames
    WHERE permno IN {permno_list}
    ORDER BY permno, namedt DESC
"""
ticker_map = conn.raw_sql(query_tickers)
print(f"Mapped {len(ticker_map)} permnos to tickers")

# Clean up
tickers = ticker_map[['ticker', 'permno', 'comnam']].copy()
tickers['ticker'] = tickers['ticker'].str.strip().str.upper()
tickers = tickers.dropna(subset=['ticker'])
tickers = tickers[tickers['ticker'] != '']
tickers = tickers.drop_duplicates(subset=['ticker'])

# Step 3: Save
print("\n[4/4] Saving to CSV...")
tickers[['ticker']].to_csv(OUTPUT_PATH, index=False)
print(f"Saved {len(tickers)} tickers to {OUTPUT_PATH}")

# Verification
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)
print(f"\nTotal tickers: {len(tickers)}")
print(f"\nFirst 10:")
print(tickers[['ticker', 'comnam']].head(10).to_string(index=False))
print(f"\nLast 10:")
print(tickers[['ticker', 'comnam']].tail(10).to_string(index=False))

print("\n" + "=" * 80)
print("NEXT STEP")
print("=" * 80)
print(f"  python pipeline_runner.py --input {OUTPUT_PATH} --output sp500_output_latest.csv --max-filings 1")

conn.close()