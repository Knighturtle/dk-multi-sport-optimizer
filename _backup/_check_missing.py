import pandas as pd

tmpl = pd.read_csv(r".\data\raw\dk_template_mlb.csv", header=None)[0].tolist()
L = pd.read_csv(r".\configs\lineups_long_clean.csv", dtype=str)
D = pd.read_csv(r".\data\raw\DKSalaries.csv", dtype=str)
P = pd.read_csv(r".\data\processed\players_today.csv", dtype=str)

dk_pos_col = "Roster Position" if "Roster Position" in D.columns else "Position"
id_col = "ID" if "ID" in D.columns else "Id"
pid_col = "player_id" if "player_id" in P.columns else P.columns[0]

L = L.dropna(subset=["lineup_id","player_id"])
L["player_id"] = L["player_id"].str.extract(r"(\d+)$")[0]
sel = set(L[L["lineup_id"]=="1"]["player_id"])   # 例：lineup_id=1 をチェック

# 既存選手のポジション内訳
pos_of = (D.set_index(id_col)[dk_pos_col]
            .reindex(list(sel))
            .dropna())
print("selected IDs:", sorted(sel))
print("selected positions:", pos_of.to_dict())

# 必要スロット
need = tmpl.copy()
# 既に埋まっているスロットを消化（複数ポジションも考慮）
for pid,pos in pos_of.items():
    assigned = False
    for i,slot in enumerate(need):
        if (slot in pos.split("/")) and (not assigned):
            need.pop(i); assigned=True
            break
print("missing slots:", need)

# 候補（players_today かつ DKSalaries に居て、まだ選ばれてないID）
allow = set(P[pid_col]).intersection(set(D[id_col])) - sel
cand = (D[D[id_col].isin(allow)][[id_col, dk_pos_col, "Salary", "AvgPointsPerGame"]]
          .copy())
cand["Salary"] = pd.to_numeric(cand["Salary"], errors="coerce")
cand["AvgPointsPerGame"] = pd.to_numeric(cand["AvgPointsPerGame"], errors="coerce")

for slot in need:
    c = cand[cand[dk_pos_col].str.contains(rf"(^|/){slot}($|/)", na=False)]
    print(f"\n=== candidates for {slot} ===")
    print(c.sort_values(["AvgPointsPerGame","Salary"], ascending=[False,False])
            .head(10)
            .to_string(index=False))
