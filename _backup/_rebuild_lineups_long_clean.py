import os, pandas as pd

ROOT = r'.'
RANK = os.path.join(ROOT, 'rank_ev.csv')                  # rank_ev.csv の場所。別の場所にあるなら修正
MULTI= os.path.join(ROOT, 'data/processed/lineups_multi.csv')
OUT  = os.path.join(ROOT, 'data/processed/lineups_long_for_export.csv')

def clean(s:str) -> str:
    if not isinstance(s, str): s = str(s)
    # BOM やゼロ幅スペース等を削る
    bad = dict.fromkeys(map(ord, '\ufeff\u200b\u200c\u200d'))
    return s.translate(bad).strip()

# rank_ev から lineup_id を取得
if not os.path.exists(RANK):
    raise SystemExit(f'not found: {RANK}')
rank = pd.read_csv(RANK, encoding='utf-8-sig')
rank.columns = [clean(c) for c in rank.columns]
if 'lineup_id' not in rank.columns:
    raise SystemExit(f'rank_ev.csv に lineup_id 列がありません: {rank.columns.tolist()}')
keep_ids = pd.to_numeric(rank['lineup_id'], errors='coerce').dropna().astype(int).unique()

# lineups_multi を読み込み → スロット列を melt して縦持ちへ
if not os.path.exists(MULTI):
    raise SystemExit(f'not found: {MULTI}')
df = pd.read_csv(MULTI, encoding='utf-8-sig')
df.columns = [clean(c) for c in df.columns]

slot_all = ['P','P.1','C','1B','2B','3B','SS','OF','OF.1','OF.2']
slots = [c for c in slot_all if c in df.columns]
if not slots: raise SystemExit(f'lineups_multi.csv にスロット列が見つかりません: {df.columns.tolist()}')
if 'lineup_id' not in df.columns:
    raise SystemExit(f'lineups_multi.csv に lineup_id 列がありません: {df.columns.tolist()}')

long = df.melt(id_vars=['lineup_id'], value_vars=slots, var_name='slot', value_name='player_id')
long['lineup_id'] = pd.to_numeric(long['lineup_id'], errors='coerce').astype('Int64')
long['player_id'] = pd.to_numeric(long['player_id'], errors='coerce').astype('Int64')
long = long.dropna(subset=['lineup_id','player_id']).astype({'lineup_id':'int64','player_id':'int64'})

# rank_ev に載ってる lineup_id のみに絞る（必要なら上位N件にするなど調整可）
long = long[long['lineup_id'].isin(keep_ids)][['lineup_id','player_id']]

# BOMなし UTF-8 で保存
os.makedirs(os.path.dirname(OUT), exist_ok=True)
long.to_csv(OUT, index=False, encoding='utf-8')

# 直後に読み直して列名を表示（検証用）
check = pd.read_csv(OUT, encoding='utf-8')
print('wrote:', OUT, 'rows=', len(check), 'lineups=', check["lineup_id"].nunique())
print('columns:', list(check.columns))
print(check.head().to_string(index=False))
