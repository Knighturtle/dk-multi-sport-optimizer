import pandas as pd

L = pd.read_csv(r".\configs\lineups_long_clean.csv", dtype=str)
D = pd.read_csv(r".\data\raw\DKSalaries.csv", dtype=str)
P = pd.read_csv(r".\data\processed\players_today.csv", dtype=str)

id_col = "ID" if "ID" in D.columns else D.columns[0]
dk_pos = "Roster Position" if "Roster Position" in D.columns else "Position"
pid_col = "player_id" if "player_id" in P.columns else P.columns[0]

L["player_id"] = L["player_id"].str.extract(r"(\d+)$")[0]
sel = set(L[L["lineup_id"]=="1"]["player_id"])

both = set(D[id_col]).intersection(set(P[pid_col])) - sel

cand = D[D[id_col].isin(both)][[id_col, dk_pos, "Salary", "AvgPointsPerGame"]].copy()
for c in ["Salary","AvgPointsPerGame"]:
    cand[c] = pd.to_numeric(cand[c], errors="coerce")

slot = input("不足している枠を入力 (例: P / C / 1B / 2B / 3B / SS / OF): ").strip().upper()
f = cand[cand[dk_pos].str.contains(rf"(^|/){slot}($|/)", na=False)]
print(f"\n=== candidates for {slot} ===")
print(f.sort_values(['AvgPointsPerGame','Salary'], ascending=[False,False])
        .head(20).to_string(index=False))
