# convert_players_csv.py
# DK/FD の Players List CSV → 共通形式 players_today.csv (player_id, player_name, salary)

from __future__ import annotations
import argparse, pandas as pd

MAPS = {
    "dk": {  # DraftKings
        "id":    ["ID","Id","Player ID","PlayerID"],
        "name":  ["Name","Player","Player Name"],
        "salary":["Salary","Sal","DK Salary"],
    },
    "fd": {  # FanDuel
        "id":    ["Id","ID","PlayerID","Player Id"],
        "name":  ["Name","Player","Nickname"],
        "salary":["Salary","Sal","FD Salary"],
    },
}

def pick(df: pd.DataFrame, keys: list[str]) -> str|None:
    low = {c.lower(): c for c in df.columns}
    for k in keys:
        if k.lower() in low:
            return low[k.lower()]
    return None

def main():
    ap = argparse.ArgumentParser(description="Players CSV → players_today.csv")
    ap.add_argument("--site", choices=["dk","fd"], required=True)
    ap.add_argument("--input", required=True, help="ダウンロードした Players CSV のパス")
    ap.add_argument("--out", default="data/processed/players_today.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.input, engine="python", sep=None)  # 区切り自動検出
    m = MAPS[args.site]

    idc  = pick(df, m["id"])
    name = pick(df, m["name"])
    sal  = pick(df, m["salary"])
    if not (idc and name and sal):
        raise SystemExit(f"必要列が見つかりません。検出結果: id={idc}, name={name}, salary={sal}")

    out = (df.rename(columns={idc:"player_id", name:"player_name", sal:"salary"})
             [["player_id","player_name","salary"]].copy())
    out["player_id"]   = out["player_id"].astype(str).str.strip()
    out["player_name"] = out["player_name"].astype(str).str.strip()
    out["salary"]      = pd.to_numeric(out["salary"], errors="coerce").fillna(0).astype(int)
    out.to_csv(args.out, index=False, encoding="utf-8-sig")

    gt0 = (out["salary"] > 0).sum()
    print(f"[ok] wrote {args.out}  (salary>0: {gt0}/{len(out)})")

if __name__ == "__main__":
    main()
