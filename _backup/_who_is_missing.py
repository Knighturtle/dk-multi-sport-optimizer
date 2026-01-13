import pandas as pd

L  = pd.read_csv(r'.\configs\lineups_long_clean.csv', dtype=str)
DK = pd.read_csv(r'.\data\raw\DKSalaries.csv', dtype=str, on_bad_lines='skip')
PT = pd.read_csv(r'.\data\processed\players_today.csv', dtype=str, on_bad_lines='skip')

# 余計な文字を掃除しつつIDを取得
ids = L['player_id'].astype(str).str.extract(r'(\d+)')[0].dropna().tolist()

dk_ids = set(DK['ID'].astype(str))
pt_ids = set(PT['player_id'].astype(str)) if 'player_id' in PT.columns else set()

missing_in_dk = [i for i in ids if i not in dk_ids]
missing_in_pt = [i for i in ids if pt_ids and i not in pt_ids else False]

print('lineup ids:', ids)
print('missing IN DKSalaries.csv:', missing_in_dk)
if pt_ids:
    print('missing IN players_today.csv:', [i for i in ids if i not in pt_ids])

# 欠けているIDに名前が紐づくか（DK側）ざっと表示
if missing_in_dk:
    cols = [c for c in DK.columns if c.lower() in ('name','id','position','teamabbrev','avgpointspergame','game info','rostpos','position')]
    print('\\nDK candidates preview for missing ids (if any matched by ID):')
    print(DK[DK['ID'].astype(str).isin(missing_in_dk)][cols].head(50).to_string(index=False))
