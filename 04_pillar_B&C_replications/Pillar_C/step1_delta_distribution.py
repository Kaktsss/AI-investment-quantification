"""
Step 1: Understand the ai_washing_delta distribution.

This tells us: how many companies show signs of "AI-washing" (positive delta)
vs. genuine AI engagement (negative delta)?
"""

import pandas as pd
import numpy as np

df = pd.read_csv('pillar_c_output.csv')
ok = df[df['status'] == 'ok']

print("=" * 80)
print("DISTRIBUTION OF ai_washing_delta (all 34 firms)")
print("=" * 80)

print("\nStatistics:")
print(ok['ai_washing_delta'].describe())

print("\n" + "=" * 80)
print("CATEGORIES (by delta)")
print("=" * 80)

positive = ok[ok['ai_washing_delta'] > 0.3]
neutral = ok[(ok['ai_washing_delta'] >= -0.3) & (ok['ai_washing_delta'] <= 0.3)]
negative = ok[ok['ai_washing_delta'] < -0.3]

print(f"\nPositive delta (> +0.3): {len(positive)} firms — AI-WASHING GYANÚ")
print(f"  (Sok AI-szó, de kevésbé technikai)")
if len(positive) > 0:
    print(positive[['ticker', 'tier1_per_10k_words', 'tier2_semantic_score', 'ai_washing_delta']].sort_values('ai_washing_delta', ascending=False).to_string(index=False))

print(f"\nNeutral delta (-0.3 ... +0.3): {len(neutral)} firms — KONZISZTENS")
print(f"  (Keyword és semantika összhangban)")
if len(neutral) > 0:
    print(neutral[['ticker', 'tier1_per_10k_words', 'tier2_semantic_score', 'ai_washing_delta']].sort_values('ai_washing_delta', ascending=False).to_string(index=False))

print(f"\nNegative delta (< -0.3): {len(negative)} firms — VALÓDI AI")
print(f"  (Kevés AI-szó, DE amit mond technikai, vagy alacsony-alacsony koncisztens)")
if len(negative) > 0:
    print(negative[['ticker', 'tier1_per_10k_words', 'tier2_semantic_score', 'ai_washing_delta']].sort_values('ai_washing_delta', ascending=True).to_string(index=False))

print("\n" + "=" * 80)
print("SUMMARY FOR PROF. ADAM")
print("=" * 80)
print(f"""
Total firms analyzed: {len(ok)}
- Possible AI-washing (delta > +0.3): {len(positive)} firms ({100*len(positive)/len(ok):.1f}%)
- Consistent (delta -0.3 to +0.3): {len(neutral)} firms ({100*len(neutral)/len(ok):.1f}%)
- Genuine AI engagement (delta < -0.3): {len(negative)} firms ({100*len(negative)/len(ok):.1f}%)

Key finding:
Tier 1 (keyword density) and Tier 2 (semantic substance) are NOT perfectly aligned.
This suggests that some firms use AI terminology without deep technical substance,
while others (less keyword-heavy) are more precise in their AI discussion.
""")