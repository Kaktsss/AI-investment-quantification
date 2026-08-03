import pandas as pd
df = pd.read_csv('pillar_c_output.csv') 
ok = df[df['status'] == 'ok']
[print(f'{t:6s} | T1: {ok[ok["ticker"]==t]["tier1_per_10k_words"].values[0]:6.1f} | T2: {ok[ok["ticker"]==t]["tier2_semantic_score"].values[0]:5.3f}') for t in ['NVDA', 'MSFT', 'KO', 'BA', 'AMD']]