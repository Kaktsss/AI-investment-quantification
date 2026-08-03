# Quick check
import pandas as pd
df = pd.read_csv('pillar_c_output.csv')
print(f'Total rows: {len(df)}')
print(f'XOM rows: {len(df[df["ticker"] == "XOM"])}')
if len(df[df['ticker'] == 'XOM']) > 0:
    print(df[df['ticker'] == 'XOM'].to_string())