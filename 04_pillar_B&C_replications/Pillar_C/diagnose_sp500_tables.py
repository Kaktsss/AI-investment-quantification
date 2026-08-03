"""
Diagnostic: find the correct CRSP table for S&P 500 constituents.

The 'sp500ind' column doesn't exist in dsenames. CRSP stores S&P 500
membership in a dedicated table. This script checks the candidates.
"""

import wrds

WRDS_USERNAME = "feketema"

conn = wrds.Connection(wrds_username=WRDS_USERNAME)
print("Connected.\n")

# Candidate tables for S&P 500 membership
candidates = [
    ("crsp", "dsp500list"),
    ("crsp", "msp500list"),
    ("crsp", "dsp500"),
]

for schema, table in candidates:
    print("=" * 70)
    print(f"Checking: {schema}.{table}")
    print("=" * 70)
    try:
        # Get column names via a tiny query
        df = conn.raw_sql(f"SELECT * FROM {schema}.{table} LIMIT 3")
        print(f"✅ EXISTS. Columns: {list(df.columns)}")
        print(df.to_string(index=False))
    except Exception as e:
        print(f"❌ Not accessible: {str(e)[:120]}")
    print()

conn.close()