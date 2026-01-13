import pandas as pd

# ファイル読込（文字列として）
L = pd.read_csv(r".\configs\lineups_long.csv", dtype=str)            # lineup_id,player_id（縦持ち）
P = pd.read_csv(r".\data\processed\players_today.csv", dtype=str)    # さっき作った players_today.csv
D = pd.read_csv(r".\data\raw\DKSalaries.csv", dtype=str)             # DK からDLした当日のCSV

# DKのポジション列名を推定
pos_col = 'Roster Position' if 'Roster Position' in D.columns else ('Position' if 'Position' in D.columns else None)
print("pos_col =", pos_col)
print("DK positions =", sorted(D[pos_col].dropna().unique().tolist())[:20] if pos_col else "N/A")

# DKのID列名を推定
dk_id_col = 'ID' if 'ID' in D.columns else ('Id' if 'Id' in D.columns else D.columns[0])

# players_today のID列名（保険）
p_id_col = 'player_id' if 'player_id' in P.columns else P.columns[0]

# ID集合
ls = set(L['player_id'].astype(str))
ps = set(P[p_id_col].astype(str))
ds = set(D[dk_id_col].astype(str))

print("missing in players_today:", sorted(ls - ps)[:10])  # lineups にあるのに players_today にないID
print("missing in DKSalaries   :", sorted(ls - ds)[:10])  # lineups にあるのに DK にないID

# 各ラインナップの人数
print("group sizes:", L.groupby('lineup_id').size().to_dict())
