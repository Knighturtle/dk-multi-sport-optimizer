import pandas as pd

L = pd.read_csv(r".\configs\lineups_long_clean.csv", dtype=str)
D = pd.read_csv(r".\data\raw\DKSalaries.csv", dtype=str)
P = pd.read_csv(r".\data\processed\players_today.csv", dtype=str)

id_col = "ID" if "ID" in D.columns else D.columns[0]
dk_pos = "Roster Position" if "Roster Position" in D.columns else "Position"
pid_col = "player_id" if "player_id" in P.columns else P.columns[0]

L["player_id"] = L["player_id"].str.extract(r"(\d+)$")[0]
ids = set(L["player_id"])

print("NOT IN DKSalaries:", sorted(ids - set(D[id_col])))
print("NOT IN players_today:", sorted(ids - set(P[pid_col])))

sel = L[L["lineup_id"]=="1"]["player_id"].tolist()  # lineup 1 をチェック
pos = (D.set_index(id_col)[dk_pos].reindex(sel).to_dict())
print("selected positions:", pos)

tmpl = pd.read_csv(r".\data\raw\dk_template_mlb.csv", header=None)[0].tolist()
need = tmpl[:]
for pid in sel:
    r = pos.get(pid, "")
    if not isinstance(r, str): 
        continue
    # 選手の複数ポジションを順に消化
    done=False
    for i,slot in enumerate(need):
        if slot in r.split("/") and not done:
            need.pop(i); done=True
            break
print("missing slots:", need)
