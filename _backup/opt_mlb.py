print("opt_mlb.py is here and runnable.")
# opt_mlb.py — DraftKings MLB Classic 10枠 最適化（pulp使用）
# 入力: .\data\raw\DKSalaries.csv   出力: .\data\processed\dk_import.csv

import os
import pandas as pd

try:
    import pulp
except ImportError:
    raise SystemExit("pulp が見つかりません。先に `python -m pip install pulp` を実行してください。")

RAW_DK = r".\data\raw\DKSalaries.csv"
OUT_CSV = r".\data\processed\dk_import.csv"
CAP = 50000

# 必要枠
NEED = {"P": 2, "C": 1, "1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3}
ORDER = ["P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"]  # 書き出し順

def read_dk(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"DKSalariesが見つかりません: {path}")
    dk = pd.read_csv(path, dtype=str)
    # 列名ゆれ対応
    pos_col = "Roster Position" if "Roster Position" in dk.columns else \
              ("Position" if "Position" in dk.columns else None)
    if pos_col is None:
        raise ValueError("DKSalaries に Position / Roster Position 列がありません。")
    id_col = "ID" if "ID" in dk.columns else ("Id" if "Id" in dk.columns else None)
    if id_col is None:
        raise ValueError("DKSalaries に ID 列がありません。")
    proj_col = "AvgPointsPerGame" if "AvgPointsPerGame" in dk.columns else None
    if proj_col is None:
        raise ValueError("DKSalaries に AvgPointsPerGame 列がありません。")

    dk["_id"] = dk[id_col].astype(str)
    dk["_pos_raw"] = dk[pos_col].astype(str)
    dk["_salary"] = pd.to_numeric(dk["Salary"], errors="coerce").fillna(0).astype(int)
    dk["_proj"] = pd.to_numeric(dk[proj_col], errors="coerce").fillna(0.0)

    # 位置の正規化（"C/1B" のような兼任に対応）
    def norm_positions(s: str):
        parts = []
        for p in s.replace(" ", "").split("/"):
            p = p.upper()
            if p in {"P","C","1B","2B","3B","SS","OF"}:
                parts.append(p)
            elif p in {"C1B","C/1B"}:
                parts += ["C","1B"]
            # それ以外は無視
        return sorted(set(parts))
    dk["_pos_list"] = dk["_pos_raw"].map(norm_positions)
    # 有効なポジションを持つ＆サラリー>0 のみ残す
    dk = dk[(dk["_pos_list"].map(len)>0) & (dk["_salary"]>0)].copy()
    return dk

def optimize(dk: pd.DataFrame):
    prob = pulp.LpProblem("DK_MLB_Optimize", pulp.LpMaximize)

    # y[i,p] = その選手iをポジションpで起用するか
    y = {}
    for i, row in dk.iterrows():
        for p in row["_pos_list"]:
            y[(i,p)] = pulp.LpVariable(f"y_{i}_{p}", lowBound=0, upBound=1, cat="Binary")

    # 目的関数: プロジェクション最大化
    prob += pulp.lpSum(y[(i,p)] * dk.loc[i, "_proj"]
                       for (i,p) in y.keys())

    # 各選手は最大1枠
    for i, row in dk.iterrows():
        prob += pulp.lpSum(y[(i,p)] for p in row["_pos_list"]) <= 1

    # ポジション充足（ちょうど必要人数）
    for p, req in NEED.items():
        prob += pulp.lpSum(y[(i,p)] for (i,pp) in y.keys() if pp==p) == req

    # サラリー制約
    prob += pulp.lpSum(y[(i,p)] * dk.loc[i, "_salary"]
                       for (i,p) in y.keys()) <= CAP

    # 解く
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[prob.status] != "Optimal":
        raise RuntimeError(f"最適解が得られませんでした: {pulp.LpStatus[prob.status]}")

    # 採用選手を抽出（どのポジションで使ったかも）
    chosen = []
    for (i,p), var in y.items():
        if var.value() >= 0.99:
            chosen.append((p, dk.loc[i, "_id"], dk.loc[i, "Name"], dk.loc[i, "_salary"], dk.loc[i, "_proj"]))
    return chosen

def build_row_by_order(chosen):
    # chosen: list of (pos, id, name, salary, proj)
    # ORDER順にIDを並べる（Pは2人、OFは3人）
    by_pos = {}
    for p, pid, *_ in chosen:
        by_pos.setdefault(p, []).append(pid)

    ids_in_order = []
    for slot in ORDER:
        if not by_pos.get(slot):
            raise RuntimeError(f"ポジション {slot} が埋まりませんでした。")
        ids_in_order.append(by_pos[slot].pop(0))
    return ids_in_order

def main():
    dk = read_dk(RAW_DK)
    chosen = optimize(dk)
    ids_in_order = build_row_by_order(chosen)

    # 出力（ヘッダー＋ID行）
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    header = ",".join(ORDER)
    row = ",".join(ids_in_order)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(header + "\n")
        f.write(row + "\n")

    # 画面にも確認表示
    total_sal = sum(s for _,_,_,s,_ in chosen)
    total_proj = sum(p for *_, p in chosen)
    print("=== OPTIMAL LINEUP (by AvgPointsPerGame) ===")
    for p, pid, name, sal, prj in sorted(chosen, key=lambda x: ORDER.index(x[0])):
        print(f"{p:>2}  {pid:<8}  {name:<24}  ${sal:<5}  proj:{prj:>5.2f}")
    print(f"Total Salary: ${total_sal} / {CAP}   Total Proj: {total_proj:.2f}")
    print(f"[ok] wrote {OUT_CSV}")

if __name__ == "__main__":
    main()
