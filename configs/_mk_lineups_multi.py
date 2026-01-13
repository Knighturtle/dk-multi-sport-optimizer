import pandas as pd, os
p = r'data/processed/dk_import.csv'
q = r'data/processed/lineups_multi.csv'
os.makedirs('data/processed', exist_ok=True)
df = pd.read_csv(p)
if 'lineup_id' not in df.columns:
    df.insert(0, 'lineup_id', range(1, len(df)+1))
df.to_csv(q, index=False, encoding='utf-8-sig')
print('wrote', q, 'rows=', len(df))
