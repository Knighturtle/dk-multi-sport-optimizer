# run.py — DK MLB: 取得→JOIN→フィルタ→最適化→検証→エクスポート を1本で実行
# 使い方例:
#   python run.py --salaries .\data\raw\DKSalaries.csv --proj .\data\raw\players_today.csv ^
#                 --name-map .\data\raw\name_map.csv --out .\data\processed\dk_import.csv ^
#                 --cap 50000 --filter-il-out --probable-pitchers

import os, sys, argparse, shutil, time, re
import pandas as pd

try:
    import pulp
except Exception:
    print("pulp が未インストールです。  python -m pip install pulp")
    sys.exit(1)

NEED = {"P":2, "C":1, "1B":1, "2B":1, "3B":1, "SS":1, "OF":3}
EXPORT_HEADER = ["P","P","C","1B","2B","3B","SS","OF","OF","OF"]

# ----------------- ユーティリティ -----------------
def pick_pos_col(df):
    if "Roster Position" in df.columns: return "Roster Position"
    if "Position" in df.columns: return "Position"
    return None

def norm_pos_list(pos_str):
    if pd.isna(pos_str): return []
    parts = []
    for p in str(pos_str).replace(" ", "").split("/"):
        p = p.upper()
        if p in {"SP","RP"}: p = "P"
        if p in {"P","C","1B","2B","3B","SS","OF"}:
            parts.append(p)
        elif p in {"C1B","C/1B"}:
            parts += ["C","1B"]
    return sorted(set(parts))

def load_salaries(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"DKSalaries が見つかりません: {path}")
    dk = pd.read_csv(path, dtype=str)
    pos_col = pick_pos_col(dk)
    if pos_col is None:
        raise ValueError("Position 列（Position / Roster Position）が見つかりません。")
    for need in ["ID","Salary"]:
        if need not in dk.columns:
            raise ValueError(f"DKSalaries に {need} 列が必要です。")
    dk["Salary"] = pd.to_numeric(dk["Salary"], errors="coerce").fillna(0).astype(int)
    # 既定の投影（フォールバック）
    if "AvgPointsPerGame" in dk.columns:
        dk["_proj"] = pd.to_numeric(dk["AvgPointsPerGame"], errors="coerce").fillna(0.0)
    elif "FPPG" in dk.columns:
        dk["_proj"] = pd.to_numeric(dk["FPPG"], errors="coerce").fillna(0.0)
    else:
        dk["_proj"] = 0.0
    dk["_pos_list"] = dk[pos_col].apply(norm_pos_list)
    dk["_pos_col"] = pos_col
    return dk

def apply_name_map(dk, name_map_path):
    if not name_map_path or not os.path.exists(name_map_path):
        return dk
    nm = pd.read_csv(name_map_path, dtype=str)  # dirty_name, clean_dk_id
    low = {c.lower():c for c in nm.columns}
    dn = low.get("dirty_name")
    cid = low.get("clean_dk_id")
    if not dn or not cid:
        return dk
    m = dict(zip(nm[dn].astype(str), nm[cid].astype(str)))
    # Name が dirty_name に一致する場合、ID を map の clean_dk_id に置換
    if "Name" in dk.columns:
        dk["ID"] = dk.apply(lambda r: m.get(str(r["Name"]), r["ID"]), axis=1)
    return dk

def merge_projection(dk, proj_path):
    if not proj_path or not os.path.exists(proj_path):
        return dk
    pj = pd.read_csv(proj_path, dtype=str)
    cols_lower = {c.lower(): c for c in pj.columns}
    pid = cols_lower.get("dk_id") or cols_lower.get("id") or cols_lower.get("player_id")
    pname = cols_lower.get("name")
    pproj = None
    for c in pj.columns:
        if re.search(r"(proj|projection|fp)", c, re.I):
            pproj = c; break
    if not pproj:
        return dk
    pj[pproj] = pd.to_numeric(pj[pproj], errors="coerce")
    if pid and "ID" in dk.columns:
        pj[pid] = pj[pid].astype(str)
        dk["ID"] = dk["ID"].astype(str)
        dk = dk.merge(pj[[pid, pproj]].rename(columns={pid:"ID", pproj:"_proj_ext"}), on="ID", how="left")
    elif pname and "Name" in dk.columns:
        dk = dk.merge(pj[[pname, pproj]].rename(columns={pname:"Name", pproj:"_proj_ext"}), on="Name", how="left")
    else:
        return dk
    dk["_proj"] = pd.to_numeric(dk["_proj_ext"], errors="coerce").fillna(dk["_proj"])
    return dk

def filter_status(dk, filter_il_out=False, probable_pitchers=False):
    df = dk.copy()
    # IL/OUT/NA/DTD/SUSP 除外
    if filter_il_out:
        bad = {"IL","O","OUT","NA","DTD","SUSP"}
        for col in ["Status","Injury Status","InjuryStatus","Injury Indicator"]:
            if col in df.columns:
                df = df[~df[col].fillna("").str.upper().isin(bad)]
    # 投手 Probable のみ
    if probable_pitchers:
        pos_col = df["_pos_col"].iloc[0]
        is_p = df[pos_col].fillna("").str.contains("P")
        prob_cols = [c for c in df.columns if "probable" in c.lower()]
        if prob_cols:
            pc = prob_cols[0]
            ok = df[pc].fillna("").astype(str).str.lower().isin(["y","yes","true","1"])
            df = pd.concat([df[~is_p], df[is_p & ok]], ignore_index=True)
        # 列が無い場合はスキップ（DK画面側で Remove Non Probables を使用想定）
    return df

def sanity_check_supply(df):
    """必要人数を満たせるだけの供給があるか（ざっくり）"""
    pos_count = {p:0 for p in NEED}
    for lst in df["_pos_list"]:
        for p in NEED:
            if p in lst:
                pos_count[p]+=1
    lacking = [p for p,c in pos_count.items() if c < NEED[p]]
    return lacking

def optimize(df, cap):
    use = df.copy()
    use = use[(use["_pos_list"].map(len)>0) & (use["Salary"]>0)].reset_index(drop=True)
    if use.empty:
        raise RuntimeError("候補選手が0です。CSV/フィルタを確認してください。")
    lacking = sanity_check_supply(use)
    if lacking:
        raise RuntimeError(f"供給不足: {lacking} に必要人数が満たせません。フィルタを緩める/CSVを取り直す。")
    # ---- MILP ----
    prob = pulp.LpProblem("dk_mlb_opt", pulp.LpMaximize)
    y = {}
    for i,r in use.iterrows():
        for p in r["_pos_list"]:
            if p in NEED:
                y[(i,p)] = pulp.LpVariable(f"y_{i}_{p}", 0, 1, cat="Binary")
    # 各選手は最大1枠
    for i,r in use.iterrows():
        prob += pulp.lpSum(y[(i,p)] for p in r["_pos_list"] if (i,p) in y) <= 1
    # 各ポジション人数
    for p, req in NEED.items():
        prob += pulp.lpSum(y[(i,pp)] for (i,pp) in y if pp==p) == req
    # サラリー
    prob += pulp.lpSum(y[(i,p)] * int(use.loc[i, "Salary"]) for (i,p) in y) <= int(cap)
    # 目的：投影最大
    prob += pulp.lpSum(y[(i,p)] * float(use.loc[i, "_proj"]) for (i,p) in y)
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"最適解が見つかりません（{pulp.LpStatus[status]}）。供給や制約を見直してください。")
    chosen = {p:[] for p in NEED}
    total_sal = 0; total_proj = 0.0
    for (i,p), var in y.items():
        if var.value() >= 0.99:
            chosen[p].append(i)
            total_sal += int(use.loc[i, "Salary"])
            total_proj += float(use.loc[i, "_proj"])
    return use, chosen, total_sal, total_proj

def export_import_csv(use, chosen, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # ORDER通りにIDを並べる
    by_pos = {p: chosen[p][:] for p in chosen}
    ids_in_order = []
    for slot in EXPORT_HEADER:
        idx = by_pos[slot].pop()  # 1人取り出し
        ids_in_order.append(str(use.loc[idx, "ID"]))
    pd.DataFrame([ids_in_order], columns=EXPORT_HEADER).to_csv(out_path, index=False, encoding="utf-8-sig")
    return ids_in_order

def validate(ids_in_order, cap, total_sal, chosen):
    assert len(ids_in_order)==10, "IDの数が10ではありません"
    assert total_sal <= cap, "サラリー上限超過です"
    for p, req in NEED.items():
        assert len(chosen[p])==req, f"{p} の人数が {len(chosen[p])}（必要 {req}）"

def archive(inputs, out_csv, do_archive):
    if not do_archive: return
    ts = time.strftime("%Y%m%d_%H%M%S")
    arc = os.path.join("archive", ts)
    os.makedirs(arc, exist_ok=True)
    for p in inputs:
        if p and os.path.exists(p):
            shutil.copy2(p, os.path.join(arc, os.path.basename(p)))
    if out_csv and os.path.exists(out_csv):
        shutil.copy2(out_csv, os.path.join(arc, os.path.basename(out_csv)))
    print(f"[archived] {arc}")

# ----------------- メイン -----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salaries", required=True, help="DKSalaries.csv")
    ap.add_argument("--proj", default=None, help="players_today.csv 等（dk_id/name + proj）")
    ap.add_argument("--name-map", default=None, help="name_map.csv（dirty_name, clean_dk_id）")
    ap.add_argument("--out", default=r".\data\processed\dk_import.csv")
    ap.add_argument("--cap", type=int, default=50000)
    ap.add_argument("--filter-il-out", action="store_true")
    ap.add_argument("--probable-pitchers", action="store_true")
    ap.add_argument("--archive", action="store_true")
    args = ap.parse_args()

    dk = load_salaries(args.salaries)
    dk = apply_name_map(dk, args.name_map)
    dk = merge_projection(dk, args.proj)
    dk = filter_status(dk, filter_il_out=args.filter_il_out, probable_pitchers=args.probable_pitchers)

    use, chosen, total_sal, total_proj = optimize(dk, args.cap)
    ids_in_order = export_import_csv(use, chosen, args.out)
    validate(ids_in_order, args.cap, total_sal, chosen)

    # 画面表示
    print("\n=== OPTIMAL LINEUP (by projection) ===")
    pos_col = use["_pos_col"].iloc[0]
    # 表示用にスロット順で並べ替え
    order = EXPORT_HEADER[:]
    disp = []
    by_pos = {p: chosen[p][:] for p in chosen}
    for slot in order:
        i = by_pos[slot].pop()
        r = use.loc[i]
        name = r.get("Name", r.get("Player", r["ID"]))
        print(f"{slot:>2}  {name:<24}  ${int(r['Salary']):>5}  proj:{float(r['_proj']):>5.2f}  pos:{'/'.join(r['_pos_list'])}")
    print(f"---------------------------------------------")
    print(f"Total Salary: ${total_sal} / {args.cap}  |  Total Proj: {total_proj:.2f}")
    print(f"[ok] wrote {args.out}")

    archive([args.salaries, args.proj, args.name_map], args.out, args.archive)

if __name__ == "__main__":
    main()
