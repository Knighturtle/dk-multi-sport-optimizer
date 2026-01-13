import pandas as pd, re
from collections import Counter

# DKのロスター（今エントリするスレートのCSV）
DK = pd.read_csv(r'.\data\raw\DKSalaries.csv', dtype=str, on_bad_lines='skip')
DK['ID'] = DK['ID'].astype(str)
DK['Salary'] = pd.to_numeric(DK.get('Salary', 0), errors='coerce')
DK['AvgPointsPerGame'] = pd.to_numeric(DK.get('AvgPointsPerGame', 0), errors='coerce').fillna(0)

# 期待スロット（MLB）
tmpl_slots = ['P','P','C','1B','2B','3B','SS','OF','OF','OF']

# あなたのラインナップ（縦長）
L = pd.read_csv(r'.\configs\lineups_long_clean.csv', dtype=str)
ids = L['player_id'].astype(str).str.extract(r'(\d+)')[0].dropna().tolist()

dk_ids = set(DK['ID'])
found   = [i for i in ids if i in dk_ids]
missing = [i for i in ids if i not in dk_ids]

print('lineup ids :', ids)
print('missing ids:', missing)

# 既にDKに存在する8人のポジションを消し込む
used = []
for i in found:
    rp = str(DK.loc[DK['ID']==i, 'Roster Position'].values[0])
    # 例: 'C/1B'のような複数可の表記に対応
    poss = rp.split('/')
    # テンプレに含まれるものを1つだけ使用済みにする
    for p in poss:
        if p in tmpl_slots:
            used.append(p); break

need = list(tmpl_slots)
for p in used:
    if p in need:
        need.remove(p)

print('need slots :', need)

# 欠けている各スロットの候補を提案
for slot in need:
    print(f'\\n-- suggestions for {slot} --')
    cand = DK[DK['Roster Position'].str.contains(slot, na=False)]
    # すでに選んだIDは除外
    cand = cand[~cand['ID'].isin(found)]
    out = cand[['Name','ID','Roster Position','TeamAbbrev','AvgPointsPerGame','Salary']]\
            .sort_values('AvgPointsPerGame', ascending=False).head(15)
    print(out.to_string(index=False))
