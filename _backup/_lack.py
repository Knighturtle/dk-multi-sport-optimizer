import pandas as pd
from collections import Counter

tmpl = pd.read_csv(r".\data\raw\dk_template_mlb.csv", header=None)[0].tolist()
L = pd.read_csv(r".\configs\lineups_long_clean.csv", dtype=str)
D = pd.read_csv(r".\data\raw\DKSalaries.csv", dtype=str)
P = pd.read_csv(r".\data\processed\players_today.csv", dtype=str)

id_col = "ID" if "ID" in D.columns else D.columns[0]
dk_pos = "Roster Position" if "Roster Position" in D.columns else "Position"
pid_col = "player_id" if "player_id" in P.columns else P.columns[0]

L["player_id"] = L["player_id"].str.extract(r"(\d+)$")[0]
sel = L[L["lineup_id"]=="1"]["player_id"].tolist()

# 必要数（テンプレの個数）
need_cnt = Counter(tmpl)

# 実際に使えているポジション数（NaNは無視）
pos_map = D.set_index(id_col)[dk_pos]
use_cnt = Counter()
for pid in sel:
    r = pos_map.get(pid)
    if isinstance(r, str):
        # その選手の複数ポジション（例 "SS/OF"）を全部保持
        use_cnt.update([r])  # ここでは “文字列丸ごと” ではなく…
        for p in r.split("/"):  # 実際のスロットへの適合でカウント
            use_cnt[p] += 0  # プレースホルダ（下の差分計算に備える）

# 差分（不足）を計算
have = Counter()
for pid in sel:
    r = pos_map.get(pid)
    if isinstance(r, str):
        # 1人につき1スロットしか消費できない → “貪欲に” テンプレを消費
        used = False
        for p in r.split("/"):
            if need_cnt[p] - have[p] > 0:
                have[p] += 1
                used = True
                break
        # どれにも当てはまらなかった選手は余剰（スロット充足に寄与していない）

lack = {k: need_cnt[k]-have[k] for k in need_cnt if need_cnt[k]-have[k] > 0}
print("required :", dict(need_cnt))
print("assigned :", dict(have))
print("lack     :", lack)
print("invalid ids (not in both):",
      sorted(set(sel) - set(D[id_col]).intersection(set(P[pid_col]))))
