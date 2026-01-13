# python_simulate_lineups.py
import pandas as pd
import numpy as np

LINEUPS = "lineups_multi.csv"   # ルート直下にある場合

df = pd.read_csv(LINEUPS)

# lineup_id ごとの EV（=exp_fp 合計）、p90（95%分位）、Sharpe-like（EV/σ）
ev = df.groupby("lineup_id")["exp_fp"].sum().rename("ev")
p90 = df.groupby("lineup_id")["exp_fp"].quantile(0.95).rename("p90")

res = pd.concat([ev, p90], axis=1)
res["sharpe_like"] = res["ev"] / (res["ev"].std(ddof=1) + 1e-9)

# ランク別に保存
res.sort_values("ev", ascending=False).to_csv("rank_ev.csv", index=False)
res.sort_values("p90", ascending=False).to_csv("rank_p90.csv", index=False)
res.sort_values("sharpe_like", ascending=False).to_csv("rank_sharpe.csv", index=False)

print("[done] saved: rank_ev.csv, rank_p90.csv, rank_sharpe.csv")
