import pandas as pd

DST = r"data/processed/players_with_proj_norm.csv"
df = pd.read_csv(DST, encoding="utf-8")
# 互換エイリアスを追加（スクリプト側の探索名に合わせる）
df["exp_fp"] = df["expected_points"]
df["proj"]   = df["expected_points"]
df.to_csv(DST, index=False, encoding="utf-8")
print("added alias columns ->", DST)
print(df.head().to_string(index=False))
