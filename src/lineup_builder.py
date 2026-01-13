# -*- coding: utf-8 -*-
r"""DraftKings MLB lineup builder — minimal reliable version

前提:
- ルール: rules/dk/mlb.yaml で `roster_slots: { slots: [...] }` 形式
- CSV: data/dk_salaries.csv（DraftKings Classic）
  必須列: Position, Name, ID, Roster Position, Salary, TeamAbbrev, AvgPointsPerGame
使い方:
  python -m src.lineup_builder --in ".\data\dk_salaries.csv" --rules "rules/dk/mlb.yaml" --out "output/MLB/submit_lineups.csv"
"""

from __future__ import annotations

import argparse
import os
import random
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml


# =============================================================================
# 1) フレキシブルCSVローダ（インライン化：import問題を完全回避）
# =============================================================================
_ATTEMPTS = [
    dict(encoding="utf-8-sig", sep=","),   # DraftKings標準
    dict(encoding="utf-16",    sep="\t"),  # Excel Unicode Text
    dict(encoding="utf-8-sig", sep=";"),   # セミコロン想定
    dict(encoding="latin1",    sep=","),   # 予備
]

def read_flexible_csv(path: str) -> pd.DataFrame:
    abspath = os.path.abspath(path)
    if not os.path.exists(abspath):
        raise FileNotFoundError(f"CSV not found: {abspath}")
    size = os.path.getsize(abspath)
    if size == 0:
        raise ValueError(f"CSV is empty: {abspath}")

    last_err = None
    for kw in _ATTEMPTS:
        try:
            df = pd.read_csv(abspath, **kw)
            if df.shape[1] <= 1:
                raise ValueError("Parsed <=1 columns; likely wrong separator/encoding")
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            last_err = e
    raise ValueError(f"CSVの区切り/エンコーディングを判別できません: {path} (last error: {last_err})")


# =============================================================================
# 2) ルールの読み込み・正規化
# =============================================================================
def load_rules(rules_yaml: str) -> dict:
    p = Path(rules_yaml).resolve()
    if not p.exists():
        raise FileNotFoundError(f"rules yaml not found: {p}")

    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    # ← ここを必ず入れる（無ければ MLB を既定に）
    sport = (data.get("sport") or "MLB").upper()

    slots = (data.get("roster_slots") or {}).get("slots") or data.get("positions") or []
    if not isinstance(slots, list) or not slots:
        raise ValueError("rules_yaml の 'roster_slots/slots' が空です。")

    salary_cap  = int(data.get("salary_cap", 50000))
    num_lineups = int(data.get("num_lineups", 1))
    team_limits = data.get("team_limits", {}) or {}
    max_from_team = int(team_limits.get("max_from_team", 5))
    min_teams     = int(team_limits.get("min_teams", 2))
    proj_col = data.get("projection_column") or data.get("projections") or "AvgPointsPerGame"

    expanded_slots, normalized = [], []
    for s in slots:
        cnt = s.get("count")
        if cnt is None and s.get("min") is not None and s.get("max") is not None and int(s["min"]) == int(s["max"]):
            cnt = int(s["min"])
        normalized.append({"slot": s["slot"], "eligible": list(s["eligible"]), "count": int(cnt or 1)})
        expanded_slots.extend([s["slot"]] * int(cnt or 1))

    return {
        "salary_cap": salary_cap,
        "num_lineups": max(1, num_lineups),
        "max_from_team": max_from_team,
        "min_teams": min_teams,
        "projection_column": proj_col,
        "expanded_slots": expanded_slots,
        "slots": normalized,
        "sport": sport,   # ← 忘れずに返す
    }



# =============================================================================
# 3) CSV 前処理
# =============================================================================
REQUIRED_COLS = {"Position", "Name", "ID", "Roster Position", "Salary", "TeamAbbrev"}

def load_pool(csv_path: str, proj_col: str, sport: str) -> pd.DataFrame:
    df = read_flexible_csv(csv_path)
    df.columns = [str(c).strip() for c in df.columns]
    ...
    # ▼ ここから置き換え
    # まずは共通で大文字＆トリム
    df["Roster Position"] = df["Roster Position"].astype(str).str.strip().str.upper()

    if sport == "MLB":
        # MLBだけの正規化（SP/RP→P、1B/C→C/1B）
        def norm_mlb(x: str) -> str:
            x = x.replace("SP", "P").replace("RP", "P")
            if x in {"1B", "C"}:
                return "C/1B"
            return x
        df["Roster Position"] = df["Roster Position"].map(norm_mlb)

    # 斜線区切りの複合ポジ（例: "PG/SG", "2B/SS" など）を行展開して扱いやすく
    df = df.assign(_rp_list=df["Roster Position"].str.split("/")).explode("_rp_list")
    df["Roster Position"] = df["_rp_list"].str.strip()
    df = df.drop(columns=["_rp_list"])
    # ▲ ここまで

    # 以降は既存の列選択・重複除去など
    use_cols = ["Position", "Roster Position", "Name", "ID", "TeamAbbrev", "Salary", proj_col]
    df = df[use_cols].copy().rename(columns={proj_col: "__PROJ__"})
    df = df.drop_duplicates(subset=["ID","Roster Position"]).reset_index(drop=True)
    return df


# =============================================================================
# 4) ラインナップ構築（シンプル貪欲）
# =============================================================================
def build_one(pool: pd.DataFrame, expanded_slots: List[str], cap: int,
              max_team: int, min_teams: int, rng: random.Random) -> Optional[List[dict]]:
    # スロット別候補
    by_pos: Dict[str, pd.DataFrame] = {}
    for rp in sorted(pool["Roster Position"].unique()):
        by_pos[rp] = pool[pool["Roster Position"] == rp].copy()

    all_df = pool.copy()
    chosen: List[dict] = []
    used = set()
    team_cnt: Dict[str, int] = {}
    salary = 0

    order = expanded_slots[:]
    rng.shuffle(order)

    for slot in order:
                # ❶ 候補抽出（UTIL は全員、それ以外は該当ポジ）
        cands = all_df if slot == "UTIL" else by_pos.get(slot, pd.DataFrame())
        if cands.empty:
            return None

        # 未使用のみ
        cands = cands[~cands["ID"].isin(used)].copy()
        if cands.empty:
            return None

        # ❷ まず「残りサラリー」「チーム上限」で前処理フィルタ
        remaining = cap - salary
        cands = cands[cands["Salary"] <= remaining]
        if cands.empty:
            return None

        if team_cnt:
            full_teams = [t for (t, cnt) in team_cnt.items() if cnt >= max_team]
            if full_teams:
                cands = cands[~cands["TeamAbbrev"].isin(full_teams)]
                if cands.empty:
                    return None

        # ❸ スコアで並べる（純投影と値段比のハイブリッド）
        cands = cands.assign(_ratio=cands["__PROJ__"] / cands["Salary"].clip(lower=1))
        cands = cands.sort_values(["__PROJ__", "_ratio"], ascending=False)

        # ❹ 上位を広めに見てランダムに試す
        head = min(1000, len(cands))          # ← 200 → 1000 に拡張
        idxs = list(range(head))
        rng.shuffle(idxs)

        picked = None
        for i in idxs:
            row = cands.iloc[i]
            team = str(row["TeamAbbrev"])
            sal  = int(row["Salary"])
            if salary + sal > cap:
                continue
            if team_cnt.get(team, 0) + 1 > max_team:
                continue
            picked = {
                "Slot": slot,
                "Name": str(row["Name"]),
                "ID": str(row["ID"]),
                "TeamAbbrev": team,
                "Salary": sal,
                "Proj": float(row["__PROJ__"]),
            }
            break

        if picked is None:
            return None


        chosen.append(picked)
        used.add(picked["ID"])
        team_cnt[picked["TeamAbbrev"]] = team_cnt.get(picked["TeamAbbrev"], 0) + 1
        salary += picked["Salary"]

    if len({c["TeamAbbrev"] for c in chosen}) < min_teams:
        return None
    return chosen


def build_many(pool: pd.DataFrame, rules: dict, seed: Optional[int]) -> List[List[dict]]:
    rng = random.Random(seed)
    want = rules["num_lineups"]
    cap = rules["salary_cap"]
    max_team = rules["max_from_team"]
    min_teams = rules["min_teams"]
    slots = rules["expanded_slots"]

    outs: List[List[dict]] = []
    best: Optional[List[dict]] = None
    best_proj = -1.0

    for _ in range(max(4000, 800 * want)):
        lu = build_one(pool, slots, cap, max_team, min_teams, rng)
        if lu:
            outs.append(lu)
            s = sum(p["Proj"] for p in lu)
            if s > best_proj:
                best_proj, best = s, lu
            if len(outs) >= want:
                break

    if not outs and best:
        outs = [best]
    if not outs:
        raise ValueError("ラインナップを生成できませんでした。ルール/入力を確認してください。")
    return outs


# =============================================================================
# 5) 出力
# =============================================================================
def export_lineups(lus: List[List[dict]], out_csv: str) -> None:
    rows = []
    for i, lu in enumerate(lus, 1):
        for p in lu:
            rows.append({"Lineup": i, **p})
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[OK] wrote {out_path}  ({len(lus)} lineup(s))")


# =============================================================================
# 6) CLI
# =============================================================================
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True)
    ap.add_argument("--rules", dest="rules_yaml", required=True)
    ap.add_argument("--out", dest="out_csv", required=True)
    ap.add_argument("--seed", dest="seed", type=int, default=None)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    rules = load_rules(args.rules_yaml)

    # ここに一時的に追加（デバッグ用）
    print("rules keys:", rules.keys())

    pool  = load_pool(args.in_csv, rules["projection_column"], rules.get("sport", "MLB"))
    print("cols:", list(pool.rename(columns={"__PROJ__": rules["projection_column"]}).columns))
    print(pool["Roster Position"].value_counts())

    lus = build_many(pool, rules, seed=args.seed)
    export_lineups(lus, args.out_csv)




if __name__ == "__main__":
    main()
