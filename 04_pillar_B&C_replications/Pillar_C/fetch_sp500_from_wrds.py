"""
Fetch S&P 500 constituents from WRDS CRSP and create a CSV for Pillar C.

This script queries the CRSP database to get all firms in the S&P 500 index
(identified by the 'SP500' designation in CRSP), extracts their tickers,
and saves them to a CSV file suitable for pipeline_runner.py input.

Method:
  - Query CRSP.MSF (Monthly Security File) or CRSP.DSENAMES (Daily Security Names)
  - Filter for index='SP500' (S&P 500 indicator)
  - Get most recent date to ensure current constituents
  - Extract unique tickers
  - Save to sp500_tickers.csv
"""

import wrds
import pandas as pd
from pathlib import Path

# Setup
WRDS_USERNAME = "feketema"
OUTPUT_PATH = Path("sp500_tickers.csv")

print("=" * 80)
print("Fetching S&P 500 constituents from WRDS CRSP")
print("=" * 80)

# Connect to WRDS
print("\n[1/4] Connecting to WRDS...")
try:
    conn = wrds.Connection(wrds_username=WRDS_USERNAME)
    print("✅ Connected to WRDS")
except Exception as e:
    print(f"❌ Failed to connect to WRDS: {e}")
    exit(1)

# Query CRSP for S&P 500 constituents
print("\n[2/4] Querying CRSP for S&P 500 constituents...")
print("      (This may take 30-60 seconds)")

try:
    # Query CRSP.DSENAMES for firms currently in SP500 index
    # Using daily security names to get the most recent constituents
    query = """
    SELECT DISTINCT ticker, ncusip, comnam
    FROM crsp.dsenames
    WHERE sp500ind = 'S'
      AND date = (SELECT MAX(date) FROM crsp.dsenames WHERE sp500ind = 'S')
    ORDER BY ticker
    """
    
    sp500_df = conn.raw_sql(query)
    print(f"✅ Fetched {len(sp500_df)} S&P 500 constituents")
    
except Exception as e:
    print(f"❌ Query failed: {e}")
    print("   Trying alternative query (historical S&P 500)...")
    
    try:
        # Fallback: Get firms that were in S&P 500 in the last year
        query_fallback = """
        SELECT DISTINCT ticker, ncusip, comnam
        FROM crsp.dsenames
        WHERE sp500ind = 'S'
          AND date >= (SELECT MAX(date) - 365 FROM crsp.dsenames)
        ORDER BY ticker
        """
        sp500_df = conn.raw_sql(query_fallback)
        print(f"✅ Fetched {len(sp500_df)} constituents (fallback query)")
        
    except Exception as e2:
        print(f"❌ Fallback query also failed: {e2}")
        exit(1)

# Prepare output
print("\n[3/4] Preparing output...")

# Extract ticker column
tickers = sp500_df[['ticker']].copy()
tickers.columns = ['ticker']
tickers['ticker'] = tickers['ticker'].str.strip().str.upper()

# Remove any NaNs
tickers = tickers.dropna()

print(f"✅ Extracted {len(tickers)} unique tickers")

# Save to CSV
print("\n[4/4] Saving to CSV...")
try:
    tickers.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved to {OUTPUT_PATH}")
except Exception as e:
    print(f"❌ Failed to save: {e}")
    exit(1)

# Verification
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)
print(f"\nTotal tickers: {len(tickers)}")
print(f"\nFirst 10 tickers:")
print(tickers.head(10).to_string(index=False))
print(f"\nLast 10 tickers:")
print(tickers.tail(10).to_string(index=False))

# Check for duplicates
if tickers.duplicated().sum() > 0:
    print(f"\n⚠️  Found {tickers.duplicated().sum()} duplicates (removed)")
    tickers = tickers.drop_duplicates()
    tickers.to_csv(OUTPUT_PATH, index=False)

print("\n" + "=" * 80)
print("✅ READY FOR PIPELINE_RUNNER.PY")
print("=" * 80)
print(f"\nNext step:")
print(f"  python pipeline_runner.py --input {OUTPUT_PATH} --output sp500_output_latest.csv --max-filings 1")
print()

# Disconnect
conn.close()