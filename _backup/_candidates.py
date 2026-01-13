import pandas as pd

tmpl = pd.read_csv(r".\data\raw\dk_template_mlb.csv", header=None)[0].tolist()
L = pd.read_csv(r".\configs\lineups_long_clean.csv", dtype=str)
D = pd.read_csv(r".\data\raw\DKSalaries.csv", dtype=str)
P = pd.read_csv(r".\data\processed\players_today.csv", dtype=str)

id_col = "ID" if "ID" in D.columns else D.columns[0]
dk_pos = "Roster Position" if "Roster Position" in D.columns else "Position"
pid_col = "player_id" if "player_id" in P.columns else P.columns[0]

L["player_id"] = L["player_id"].str.extract(r"(\d+)$")[0]
sel = set(L[L["lineup_id"]=="1"]["player_id"])   # 1番のラインナップ対象

allow = set(P[pid_col]).intersection(set(D[id_col])) - sel
cand = (D[D[id_col].isin(allow)][[id_col, dk_pos, "Salary", "AvgPointsPerGame"]].copy())
for c in ["Salary","AvgPointsPerGame"]:
    cand[c] = pd.to_numeric(cand[c], errors="coerce")

# 現在の選手のポジションでテンプレを消費
pos_now = (D.set_index(id_col)[dk_pos].reindex(list(sel)).dropna())
need = tmpl[:]
for r in pos_now:
    done=False
    for i,slot in enumerate(need):
        if slot in r.split("/") and not done:
            need.pop(i); done=True; break

print("missing slots:", need)

# 各枠の上位候補を表示
for slot in need:
    c = cand[cand[dk_pos].str.contains(rf"(^|/){slot}($|/)", na=False)]
    print(f"\n=== candidates for {slot} ===")
    print(c.sort_values(["AvgPointsPerGame","Salary"], ascending=[False,False])
            .head(10).to_string(index=False))
