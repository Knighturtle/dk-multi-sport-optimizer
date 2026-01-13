import pandas as pd
dk  = pd.read_csv(r".\data\raw\DKSalaries.csv", dtype=str)
imp = pd.read_csv(r".\data\processed\dk_import.csv", dtype=str)

ids = imp.iloc[0].tolist()  # 9??ID
dk_ids = set(dk["ID"].astype(str))

missing = [x for x in ids if x not in dk_ids]
print("CSV IDs:", ids)
print("Missing in DKSalaries:", missing)
print("Duplicate count:", 9 - len(set(ids)))
