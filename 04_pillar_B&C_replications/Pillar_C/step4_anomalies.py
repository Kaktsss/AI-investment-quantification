"""
Step 4: Identify and understand anomalies.
"""

import pandas as pd

df = pd.read_csv('pillar_c_output.csv')
ok = df[df['status'] == 'ok']

print("=" * 100)
print("ANOMALY DETECTION: Low Tier1, Normal/High Tier2")
print("=" * 100)

# Anomalies: Tier1 in bottom quartile, but Tier2 above median
q1_low = ok['tier1_per_10k_words'].quantile(0.25)
q2_median = ok['tier2_semantic_score'].median()

anomalies = ok[
    (ok['tier1_per_10k_words'] < q1_low) & 
    (ok['tier2_semantic_score'] > q2_median)
].sort_values('tier2_semantic_score', ascending=False)

print(f"\nCriteria: Tier1 < {q1_low:.2f} AND Tier2 > {q2_median:.4f}")
print(f"Found {len(anomalies)} anomalies:\n")

for idx, row in anomalies.iterrows():
    print(f"Ticker: {row['ticker']}")
    print(f"  Tier1 (keywords):     {row['tier1_per_10k_words']:7.2f}  (very low)")
    print(f"  Tier2 (semantic):     {row['tier2_semantic_score']:7.4f}  (unexpectedly high)")
    print(f"  Interpretation:       This firm barely mentions 'AI', but the few chunks")
    print(f"                        with 'AI' (or co-occurring words) happen to match")
    print(f"                        the baseline corpus semantically.")
    print()

print("=" * 100)
print("RECOMMENDATION")
print("=" * 100)
print("""
These anomalies suggest: Tier 2 (semantic scoring) can give high scores to 
low-keyword chunks if they happen to use similar words to technical AI discourse.

For S&P 500 production: Enable Tier1 gating (only embed chunks with ≥1 keyword)
to reduce these false positives.
""")