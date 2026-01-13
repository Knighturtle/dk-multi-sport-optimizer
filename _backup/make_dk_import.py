#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Tuple

import pandas as pd


# ======== ユーティリティ ========

def read_csv_smart(path: str) -> pd.DataFrame:
    """
    pandas の自動判定が失敗しやすいケースに対してリトライする安全読み込み。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    # 1st: python engine + sep=None + utf-8-sig
    try:
        return pd.read_csv(p, engine="python", sep=None, encoding="utf-8-sig")
    except Exception:
        # 2nd: utf-8
        try:
            return pd.read_csv(p, engine="python", sep=None, encoding="utf-8")
        except Exception:
            # 3rd: comma 固定
            return pd.read_csv(p, engine="python", sep=",", encoding="utf-8-sig")


def read_slots_from_template(path: str) -> List[str]:
    """
    テンプレCSV（1行だけのヘッダー）からスロットを読み、BOMや 'OF.1' → 'OF' を正規化。
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        line = f.readline().strip()
    if not line:
        raise ValueError(f"template is empty: {path}")
    slots = [s.strip() for s in line.split(",") if s.strip()]
    return normalize_slots(slots)


def normalize_slots(slots: List[str]) -> List[str]:
    out = []
    for s in slots:
        s = s.strip().lstrip("\ufeff").upper()
        # pandas の重複列自動改名: OF, OF.1, OF.2 ...
        if s.startswith("OF"):
            s = "OF"
        out.append(s)
    return out


def detect_column(df: pd.DataFrame, candidates: List[str]) -> str:
    """
    列名候補のうち最初に見つかったものを返す（大文字小文字/空白/下線を無視）
    """
    canon = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    for want in candidates:
        key = want.lower().replace(" ", "").replace("_", "")
        if key in canon:
            return canon[key]
    raise KeyError(f"None of columns found: {candidates} in {list(df.columns)}")


def roster_to_set(roster: str) -> List[str]:
    """
    'SP/RP' などを分解して MLB の抽象ポジション集合にする。
    P は SP/RP をまとめて P とみなす。
    """
    if not isinstance(roster, str):
        return []
    parts = [p.strip().upper() for p in roster.split("/")]
    out = []
    for p in parts:
        if p in ("SP", "RP", "P"):
            out.append("P")
        elif p in ("C", "1B", "2B", "3B", "SS", "OF"):
            out.append(p)
        # その他（DH等）は無視
    # 重複除去
    return sorted(set(out))


def eligible(slot: str, roster_set: List[str]) -> bool:
    if slot == "P":
        return "P" in roster_set
    if slot == "OF":
        return "OF" in roster_set
    return slot in roster_set


# ======== メイン処理 ========

def build_import(
    slots: List[str],
    dk_csv: str,
    lineups_csv: str,
    players_csv: str,
    cap: int,
) -> Tuple[pd.DataFrame, Dict[str, int], int]:
    """
    DKのPlayers List + 自前のlineups + salary から、DK IMPORT 形式を生成。
    戻り値: (出力DataFrame, {'pos':スキップ数, 'cap':スキップ数}, id_overlap数)
    """
    # DK (Players List)
    dk = read_csv_smart(dk_csv)
    id_col = detect_column(dk, ["ID", "Player ID", "player_id", "PlayerID"])
    # Salary はあれば拾う（無い場合は players.csv を優先で使う）
    salary_cols = [c for c in dk.columns if c.lower() in ("salary", "sal")]
    dk_salary_col = salary_cols[0] if salary_cols else None

    roster_col = detect_column(
        dk, ["Roster Position", "Roster_Position", "Roster", "roster"]
    )

    dk = dk.copy()
    dk["player_id"] = dk[id_col].astype(str).str.strip()
    dk["roster_set"] = dk[roster_col].apply(roster_to_set)

    dk_salary_map = {}
    if dk_salary_col:
        dk_salary_map = (
            dk[["player_id", dk_salary_col]]
            .rename(columns={dk_salary_col: "salary"})
            .assign(salary=lambda d: pd.to_numeric(d["salary"], errors="coerce").fillna(0).astype(int))
            .set_index("player_id")["salary"]
            .to_dict()
        )

    # players_today.csv （salaryの正）
    p = read_csv_smart(players_csv)
    p.columns = [c.strip().lstrip("\ufeff") for c in p.columns]
    pid_col = detect_column(p, ["player_id", "Player ID", "ID"])
    sal_col = detect_column(p, ["salary", "Salary"])
    p = p[[pid_col, sal_col]].copy()
    p["player_id"] = p[pid_col].astype(str).str.strip()
    p["salary"] = pd.to_numeric(p[sal_col], errors="coerce").fillna(0).astype(int)
    salary_map = p.set_index("player_id")["salary"].to_dict()

    # salary なければ DK の salary で補完
    for k, v in dk_salary_map.items():
        if k not in salary_map or salary_map[k] == 0:
            salary_map[k] = int(v)

    # lineups
    L = read_csv_smart(lineups_csv)
    L.columns = [c.strip().lstrip("\ufeff") for c in L.columns]
    lid_col = detect_column(L, ["lineup_id", "lineupid"])
    lpid_col = detect_column(L, ["player_id", "playerid", "Player ID"])
    exp_col = next((c for c in L.columns if c.lower() in ("exp_fp", "expfp", "fpts", "proj", "projection")), None)
    if exp_col is None:
        L["__exp__"] = 0.0
        exp_col = "__exp__"

    L["lineup_id"] = L[lid_col]
    L["player_id"] = L[lpid_col].astype(str).str.strip()
    L["exp"] = pd.to_numeric(L[exp_col], errors="coerce").fillna(0.0)

    # roster_map
    roster_map = dict(zip(dk["player_id"], dk["roster_set"]))

    # ID overlap
    id_overlap = len(set(L["player_id"]) & set(dk["player_id"]))

    # 生成
    skip_pos = 0
    skip_cap = 0
    out_rows = []

    # スロット充足を安定させるため、固定系（C,SS,1B,2B,3B）を優先
    fixed_order = [s for s in ["C", "SS", "1B", "2B", "3B"] if s in slots]
    order = fixed_order + [s for s in slots if s not in fixed_order]

    for lid, g in L.groupby("lineup_id", sort=False):
        cand_ids = list(
            g.sort_values("exp", ascending=False)["player_id"]
        )

        used = set()
        total_salary = 0
        row = {s: "" for s in slots}

        for slot in order:
            if row[slot]:
                continue
            placed = False
            for pid in cand_ids:
                if pid in used:
                    continue
                rset = roster_map.get(pid, [])
                if not eligible(slot, rset):
                    continue
                sal = int(salary_map.get(pid, 0))
                if total_salary + sal > cap:
                    continue
                row[slot] = pid
                used.add(pid)
                total_salary += sal
                placed = True
                break
            if not placed:
                skip_pos += 1
                row = None
                break

        if row is None:
            continue
        if total_salary > cap:
            skip_cap += 1
            continue

        # DK IMPORT はスロット列だけ
        out_rows.append([row[s] for s in slots])

    out_df = pd.DataFrame(out_rows, columns=slots)
    stats = {"pos": skip_pos, "cap": skip_cap}
    return out_df, stats, id_overlap


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Build DraftKings import CSV from lineups & players."
    )
    ap.add_argument("--template", help="DK template CSV (one-line header)")
    ap.add_argument("--slots", help="Slots CSV (e.g. 'P,P,C,1B,2B,3B,SS,OF,OF,OF')")
    ap.add_argument("--dk", required=True, help="DK Players List CSV (DKSalaries.csv)")
    ap.add_argument("--lineups", required=True, help="lineups_multi.csv")
    ap.add_argument("--players", required=True, help="players_today.csv (salary)")
    ap.add_argument("--cap", type=int, default=50000)
    ap.add_argument("--out", default="dk_import.csv")
    return ap.parse_args()


def main():
    args = parse_args()

    # スロット決定
    if args.slots:
        slots = normalize_slots([s for s in args.slots.split(",") if s.strip()])
    elif args.template:
        slots = read_slots_from_template(args.template)
    else:
        print("[error] --template か --slots のどちらかが必要です", file=sys.stderr)
        sys.exit(2)

    # 実処理
    out_df, stats, overlap = build_import(
        slots=slots,
        dk_csv=args.dk,
        lineups_csv=args.lineups,
        players_csv=args.players,
        cap=args.cap,
    )

    out_df.to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"[ok] wrote {args.out}  rows:{len(out_df)} (skipped: pos={stats['pos']}, cap={stats['cap']})")
    print(f"[info] ID overlap (lineups vs DK): {overlap}")
    print(f"[info] template slots: {slots}")


if __name__ == "__main__":
    main()
