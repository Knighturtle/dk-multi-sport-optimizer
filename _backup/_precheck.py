import pandas as pd

DK = pd.read_csv(r'.\data\raw\DKSalaries.csv', dtype=str)
imp = pd.read_csv(r'.\data\processed\dk_import.csv', header=None)

# 1行しかない場合にも対応：行数で取り分け
row = imp.iloc[1] if len(imp) > 1 else imp.iloc[0]

# 数値だけをIDとして抽出（'P','C'などのポジション名を除外）
vals = [str(x) for x in row.dropna().tolist()]
ids  = [v for v in vals if v.isdigit()]

print('IDs in import:', ids)
missing = [i for i in ids if i not in set(DK['ID'].astype(str))]
print('Missing in this slate:', missing)
