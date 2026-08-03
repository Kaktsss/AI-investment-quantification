"""
Step 3: Visualize Tier 1 vs Tier 2 to show the "hype" phenomenon.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv('pillar_c_output.csv')
ok = df[df['status'] == 'ok']

# Create a scatter plot
fig, ax = plt.subplots(figsize=(12, 8))

# Color by delta sign
colors = []
for delta in ok['ai_washing_delta']:
    if delta > 0.5:
        colors.append('red')  # Hype
    elif delta > 0:
        colors.append('orange')  # Slight hype
    elif delta > -0.3:
        colors.append('gray')  # Neutral
    else:
        colors.append('green')  # Genuine

ax.scatter(ok['tier1_per_10k_words'], ok['tier2_semantic_score'], 
           c=colors, s=200, alpha=0.6, edgecolors='black', linewidth=0.5)

# Add labels for notable firms
notable = ['MSFT', 'NVDA', 'AMD', 'KO', 'BA', 'ADBE', 'GOOGL', 'META', 'TSLA', 'INTC']
for ticker, t1, t2 in zip(ok['ticker'], ok['tier1_per_10k_words'], ok['tier2_semantic_score']):
    if ticker in notable:
        ax.annotate(ticker, (t1, t2), fontsize=9, fontweight='bold', 
                   xytext=(5, 5), textcoords='offset points')

ax.set_xlabel('Tier 1: AI Keyword Density (per 10k words)', fontsize=12, fontweight='bold')
ax.set_ylabel('Tier 2: Semantic Score (0-1 range)', fontsize=12, fontweight='bold')
ax.set_title('AI Engagement: Keyword Density vs. Semantic Substance\n(Color = Hype Signal)', 
            fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

# Add legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='red', edgecolor='black', label='Hype (Δ > +0.5)'),
    Patch(facecolor='orange', edgecolor='black', label='Slight hype (0 < Δ ≤ +0.5)'),
    Patch(facecolor='gray', edgecolor='black', label='Consistent (-0.3 ≤ Δ ≤ 0)'),
    Patch(facecolor='green', edgecolor='black', label='Genuine (Δ < -0.3)'),
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

plt.tight_layout()
plt.savefig('pillar_c_hype_scatter.png', dpi=150, bbox_inches='tight')
print("✅ Saved: pillar_c_hype_scatter.png")
print("\nPlot interpretation:")
print("- RED (upper-left): Talk a lot, but not technical = HYPE")
print("- GREEN (lower-right): Talk precise = GENUINE")
print("- GRAY (diagonal): Balanced")