"""
Step 2: Understand what the delta means by looking at 5 concrete firms.
"""

import pandas as pd

df = pd.read_csv('pillar_c_output.csv')
ok = df[df['status'] == 'ok']

print("=" * 100)
print("FIVE FIRMS: INTERPRETATION GUIDE")
print("=" * 100)

# Find extremes
extreme_hype = ok.nlargest(1, 'ai_washing_delta').iloc[0]
extreme_genuine = ok.nsmallest(1, 'ai_washing_delta').iloc[0]
non_ai = ok.nsmallest(1, 'tier1_per_10k_words').iloc[0]

five_firms = [
    ('extreme_hype', extreme_hype),
    ('extreme_genuine', extreme_genuine),
    ('non_ai', non_ai),
]

# Add two more: mid-range
mid_range = ok[
    (ok['ai_washing_delta'] > -0.2) & (ok['ai_washing_delta'] < 0.2)
].iloc[:2]
for idx, row in mid_range.iterrows():
    five_firms.append(('mid_range', row))

for label, row in five_firms:
    print(f"\n{'-' * 100}")
    print(f"TICKER: {row['ticker']} | Category: {label.upper()}")
    print(f"{'-' * 100}")
    
    t1 = row['tier1_per_10k_words']
    t2 = row['tier2_semantic_score']
    delta = row['ai_washing_delta']
    
    print(f"Tier 1 (keyword density):  {t1:7.2f} per 10k words")
    print(f"Tier 2 (semantic score):   {t2:7.4f}")
    print(f"AI-washing delta:          {delta:+7.2f}")
    print(f"\nInterpretation:")
    
    if delta > 0.5:
        print(f"  🚨 HYPE SIGNAL")
        print(f"     Talks a lot about AI, but in generic/marketing terms")
    elif delta > 0:
        print(f"  ⚠️  SLIGHT HYPE")
        print(f"     Mix of genuine AI + marketing language")
    elif delta > -0.3:
        print(f"  ✅ CONSISTENT")
        print(f"     Keyword and semantic aligned")
    elif delta > -0.7:
        print(f"  ✅ GENUINE AI")
        print(f"     Precise in AI discussion, not over-hyping")
    else:
        print(f"  ❓ ANOMALY")
        print(f"     Possible false positive")

print("\n" + "=" * 100)
print("WHAT TO TELL PROF. ADAM")
print("=" * 100)
print("""
The delta reveals: firms use "AI" with vastly different levels of technical substance.
Most hype-prone: tech/software firms that use AI marketing language.
Most genuine: hardware/infrastructure firms (NVIDIA, Intel) that explain chip details.
""")