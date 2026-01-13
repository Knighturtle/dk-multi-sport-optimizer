import pandas as pd

p = r"data/processed/players_with_proj_norm.csv"
df = pd.read_csv(p, encoding="utf-8")

# 互換用の列を追加（select_and_export が古い列名を探す可能性に対応）
df["exp_fp"] = df["expected_points"]
df["proj"]   = df["expected_points"]

df.to_csv(p, index=False, encoding="utf-8")
print("added alias columns to", p)
print(df.head().to_string(index=False))
