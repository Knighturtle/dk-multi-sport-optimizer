# pack_lineups.py
import argparse, pandas as pd, csv, sys

ap = argparse.ArgumentParser(description="Normalize to lineup_id,players (quoted).")
ap.add_argument("--src", required=True, help="input csv")
ap.add_argument("--out", required=True, help="output csv (lineup_id,players)")
ap.add_argument("--players-col", help="column that already has comma-separated player_ids")
ap.add_argument("--group-col", help="grouping column (e.g., lineup_id) when rows are long")
ap.add_argument("--id-col", default="player_id", help="player id column name for long format")
args = ap.parse_args()

# 文字列で読み込み（IDの先頭ゼロ保護）
df = pd.read_csv(args.src, dtype=str)

if args.players_col and args.players_col in df.columns:
    # すでに 'id1,id2,...' を持つ列があるケース
    out = df[["lineup_id", args.players_col]].copy() if "lineup_id" in df.columns else df[[args.players_col]].copy()
    if "lineup_id" not in out.columns:
        # lineup_id が無い場合は 1..N を採番
        out.insert(0, "lineup_id", pd.Series(range(1, len(out) + 1)))
    out.columns = ["lineup_id", "players"]

elif args.group_col and args.group_col in df.columns and args.id_col in df.columns:
    # 縦持ち（long）: lineup_id ごとに player_id をまとめるケース
    out = (
        df.groupby(args.group_col, sort=True)[args.id_col]
          .apply(lambda s: ",".join(str(x) for x in s.dropna().tolist()))
          .reset_index(name="players")
          .rename(columns={args.group_col: "lineup_id"})
    )

else:
    sys.exit("ERROR: provide --players-col OR both --group-col and --id-col present in CSV.")

# lineup_id を数値化し、欠損があれば 1..N で埋める
out["lineup_id"] = pd.to_numeric(out["lineup_id"], errors="coerce")
missing = out["lineup_id"].isna()
if missing.any():
    seq = pd.Series(range(1, len(out) + 1), index=out.index)
    out.loc[missing, "lineup_id"] = seq.loc[missing]
out["lineup_id"] = out["lineup_id"].astype(int)

# 2列だけにして、players は必ず引用符付きで保存
out = out[["lineup_id", "players"]]
out.to_csv(args.out, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8")
print(f"Wrote {args.out} with {len(out)} lineups")
