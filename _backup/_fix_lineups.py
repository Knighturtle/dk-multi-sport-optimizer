import pandas as pd, re

# 元CSVを読み込み
df = pd.read_csv(r".\configs\lineups_long.csv", dtype=str)
df = df.rename(columns=lambda c: c.strip())

# 必要列だけ残す（なければ先頭2列を採用して名前付け）
cols = [c for c in df.columns if c.strip().lower() in ("lineup_id","player_id")]
df = df[cols] if len(cols)==2 else df.iloc[:, :2].set_axis(["lineup_id","player_id"], axis=1)

# 前処理
for c in ("lineup_id","player_id"):
    df[c] = df[c].astype(str).str.strip()

# "nan"／空値を除去
df = df.replace({"nan": None, "NaN": None, "": None})
df = df.dropna(subset=["lineup_id","player_id"])

# 数字だけ抽出（＝末尾の連続数字）
df["lineup_id"] = df["lineup_id"].str.extract(r"(\d+)$", expand=False)
df["player_id"] = df["player_id"].str.extract(r"(\d+)$", expand=False)

# もう一度 NaN を落としてから fullmatch
df = df.dropna(subset=["lineup_id","player_id"])
df = df[df["lineup_id"].str.fullmatch(r"\d+")]
df = df[df["player_id"].str.fullmatch(r"\d+")]

print("after clean group sizes:", df.groupby("lineup_id").size().to_dict())
df.to_csv(r".\configs\lineups_long_clean.csv", index=False)
