import pandas as pd

lineups = pd.read_csv(r"data/processed/lineups_long_for_export.csv")
players = pd.read_csv(r"data/processed/players_with_proj_norm.csv")

# 数値化して結合
lineups["player_id"] = pd.to_numeric(lineups["player_id"], errors="coerce")
players["player_id"] = pd.to_numeric(players["player_id"], errors="coerce")

m = lineups.merge(players[["player_id","expected_points"]], on="player_id", how="left")

print("merge rows:", len(m), "  null expected_points:", m["expected_points"].isna().sum())
print(m.head().to_string(index=False))

# ラインナップごとの合計
tot = m.groupby("lineup_id", as_index=False)["expected_points"].sum().rename(columns={"expected_points":"sum_ep"})
print("\nlineup sums head:\n", tot.head().to_string(index=False))
