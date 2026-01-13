# make_submit.py
import pandas as pd

L   = r'data/processed/lineups_long_for_export.csv'
P   = r'data/processed/players_with_proj_norm.csv'
OUT = r'data/processed/submit_lineups.csv'

lineups = pd.read_csv(L, encoding='utf-8-sig')
players = pd.read_csv(P, encoding='utf-8-sig')

# join ミス防止のため型を揃える
for col in ('lineup_id', 'player_id'):
    if col in lineups.columns:
        lineups[col] = pd.to_numeric(lineups[col], errors='coerce')
    if col in players.columns:
        players[col] = pd.to_numeric(players[col], errors='coerce')

# 期待値に使う列名（必要なら 'exp_fp' に変更）
EP_COL = 'expected_points' if 'expected_points' in players.columns else 'exp_fp'

df = lineups.merge(players[['player_id', 'salary', EP_COL]],
                   on='player_id', how='left')

summary = (
    df.groupby('lineup_id')
      .agg(players=('player_id', lambda s: ', '.join(map(str, s.tolist()))),
           total_salary=('salary', 'sum'),
           total_exp_fp=(EP_COL, 'sum'))
      .reset_index()
)

summary.to_csv(OUT, index=False, encoding='utf-8-sig')
print(summary.head().to_string(index=False))
