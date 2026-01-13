import os, pandas as pd, numpy as np

LINUPS = r'data/processed/lineups_multi.csv'
PLAYRS = r'data/processed/players_with_proj.csv'
OUT    = LINUPS  # そのまま上書き。別にしたいなら r'data/processed/lineups_multi_with_exp.csv'

if not os.path.exists(LINUPS):
    raise FileNotFoundError(LINUPS)
if not os.path.exists(PLAYRS):
    raise FileNotFoundError(PLAYRS)

lineups = pd.read_csv(LINUPS)
players = pd.read_csv(PLAYRS)

# players 側の推定列名（違えば下2行を実名に変えてOK）
id_col   = next((c for c in ['player_id','id','PID'] if c in players.columns), None)
proj_col = next((c for c in ['expected_points','proj','projection','fp','points'] if c in players.columns), None)
if not id_col or not proj_col:
    raise SystemExit(f'players_with_proj.csv の列が見つかりません: {players.columns.tolist()}')

# id -> proj の辞書
pmap = dict(zip(pd.to_numeric(players[id_col], errors='coerce').astype('Int64'), 
                pd.to_numeric(players[proj_col], errors='coerce').fillna(0.0)))

# lineups 側のスロット列（存在するものだけ）
slot_cols_all = ['P','P.1','C','1B','2B','3B','SS','OF','OF.1','OF.2']
slot_cols = [c for c in slot_cols_all if c in lineups.columns]
if not slot_cols:
    raise SystemExit(f'lineups_multi.csv にスロット列が見つかりません: {lineups.columns.tolist()}')

def row_total(r):
    s = 0.0
    for c in slot_cols:
        try:
            key = int(r[c])
        except Exception:
            key = pd.NA
        s += float(pmap.get(key, 0.0))
    return s

lineups['total_exp_fp'] = lineups.apply(row_total, axis=1)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
lineups.to_csv(OUT, index=False, encoding='utf-8-sig')

print(f'added total_exp_fp to {OUT}')
print('slots used =', slot_cols)
print(lineups.head(2).to_string(index=False))
