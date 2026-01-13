import pandas as pd, os

rank_path = r'rank_ev.csv'  # プロジェクト直下に出ているはず。場所が違えば修正
multi_path = r'data/processed/lineups_multi.csv'
out_path   = r'data/processed/lineups_long_for_export.csv'

rank = pd.read_csv(rank_path)
if 'lineup_id' not in rank.columns:
    raise SystemExit(f'rank_ev.csv に lineup_id 列がありません: {rank.columns.tolist()}')
keep_ids = pd.to_numeric(rank['lineup_id'], errors='coerce').dropna().astype(int).unique()

df = pd.read_csv(multi_path)
slot_cols_all = ['P','P.1','C','1B','2B','3B','SS','OF','OF.1','OF.2']
slot_cols = [c for c in slot_cols_all if c in df.columns]
if not slot_cols:
    raise SystemExit(f'lineups_multi.csv にスロット列が見つかりません: {df.columns.tolist()}')

long = df.melt(id_vars=['lineup_id'], value_vars=slot_cols,
               var_name='slot', value_name='player_id')
long['lineup_id'] = pd.to_numeric(long['lineup_id'], errors='coerce').astype('Int64')
long['player_id'] = pd.to_numeric(long['player_id'], errors='coerce').astype('Int64')

# rank_ev に載っている lineup_id のみに絞る（必要なら上位N件だけにしてもOK）
long = long[long['lineup_id'].isin(keep_ids)][['lineup_id','player_id']].dropna()

os.makedirs(os.path.dirname(out_path), exist_ok=True)
long.to_csv(out_path, index=False, encoding='utf-8-sig')
print('wrote', out_path, 'rows=', len(long), 'lineups=', long["lineup_id"].nunique())
