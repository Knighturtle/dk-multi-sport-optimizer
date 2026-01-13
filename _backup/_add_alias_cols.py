import pandas as pd
p = r"data/processed/players_with_proj_norm.csv"
df = pd.read_csv(p, encoding="utf-8")
df["exp_fp"] = df["expected_points"]
df["proj"]   = df["expected_points"]
df.to_csv(p, index=False, encoding="utf-8")
print("OK:", p)
print(df.head().to_string(index=False))
