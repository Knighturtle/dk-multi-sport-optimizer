# select_and_export.py — robust版: players結合に失敗しても lineups の salary で集計して出力
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
import pandas as pd

def info(m): print(f"[info] {m}")
def warn(m): print(f"[warn] {m}")
def err(m):  print(f"[error] {m}", file=sys.stderr)

def read_csv_safely(p: Path) -> pd.DataFrame:
    if not p.exists(): raise FileNotFoundError(f"CSVが見つかりません: {p}")
    try:
        return pd.read_csv(p, engine="python", sep=None)
    except Exception:
        for enc in ("utf-8-sig","cp932","cp1252"):
            try: return pd.read_csv(p, encoding=enc)
            except Exception: pass
    return pd.read_csv(p, errors="ignore")

def pick_strict(cols, keys):  # 小文字完全一致のみ
    low = {c.lower(): c for c in cols}
    for k in keys:
        if k in low: return low[k]
    return None

def pid_digits(x) -> str:  # P-0023 / p23 / 0023 / 23 -> '0023'
    return re.sub(r"\D", "", str(x).strip())

def normalize_lineups(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    lineup_col = pick_strict(cols, ["lineup_id","lineup"])
    pid_col    = pick_strict(cols, ["player_id"])
    fp_col     = pick_strict(cols, ["exp_fp","match_id_exp_fp","proj_fp","fpts"])
    name_col   = pick_strict(cols, ["player_name","name"])   # ← lineupsにあれば保持
    sal_col    = pick_strict(cols, ["salary"])               # ← lineupsにあれば保持

    rename = {}
    if lineup_col: rename[lineup_col] = "lineup_id"
    if pid_col:    rename[pid_col]    = "player_id"
    if fp_col:     rename[fp_col]     = "exp_fp"
    if name_col:   rename[name_col]   = "player_name_lineups"
    if sal_col:    rename[sal_col]    = "salary_lineups"

    out = df.rename(columns=rename).copy()
    if "lineup_id" not in out.columns: raise ValueError("lineups に lineup_id がありません")
    if "player_id" not in out.columns: raise ValueError("lineups に player_id がありません")
    if "exp_fp" not in out.columns: out["exp_fp"] = 0.0

    out["lineup_id"] = pd.to_numeric(out["lineup_id"], errors="coerce").astype("Int64")
    out["player_id"] = out["player_id"].astype(str).str.strip()
    out["exp_fp"]    = pd.to_numeric(out["exp_fp"], errors="coerce").fillna(0.0)

    # 数字キーを作成
    out["pid_num"]   = out["player_id"].apply(pid_digits)

    # lineups内の名前/給与があれば整形
    if "player_name_lineups" in out.columns:
        out["player_name_lineups"] = out["player_name_lineups"].astype(str).str.strip()
    if "salary_lineups" in out.columns:
        out["salary_lineups"] = pd.to_numeric(out["salary_lineups"], errors="coerce")
    return out

def normalize_players(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    id_col   = pick_strict(cols, ["player_id"])
    sal_col  = pick_strict(cols, ["salary"])
    name_col = pick_strict(cols, ["player_name","name"])

    rename = {}
    if id_col:   rename[id_col]   = "player_id"
    if sal_col:  rename[sal_col]  = "salary"
    if name_col: rename[name_col] = "player_name"

    out = df.rename(columns=rename).copy()
    if "player_id" not in out.columns or "salary" not in out.columns:
        raise ValueError("players CSV に必須列 (player_id, salary) がありません")
    if "player_name" not in out.columns:
        out["player_name"] = out["player_id"].astype(str)

    out["player_id"]   = out["player_id"].astype(str).str.strip()
    out["player_name"] = out["player_name"].astype(str).str.strip()
    out["salary"]      = pd.to_numeric(out["salary"], errors="coerce")
    out["pid_num"]     = out["player_id"].apply(pid_digits)
    return out

# ===== 集計＆保存（フォールバック強化版） =====
def aggregate_and_save(df: pd.DataFrame, out_path: Path):
    # 名前カラムを用意
    if "player_name" not in df.columns:
        if "player_name_lineups" in df.columns:
            df["player_name"] = df["player_name_lineups"].astype(str)
        else:
            df["player_name"] = df["player_id"].astype(str)

    # まず per-player salary 合計
    sal_series = pd.to_numeric(df.get("salary", 0), errors="coerce").fillna(0)

    # すべて 0 なら lineups 側の total_salary を使う（あれば）
    use_total_from_lineups = False
    if (sal_series == 0).all():
        if "total_salary" in df.columns:
            ts = pd.to_numeric(df["total_salary"], errors="coerce").fillna(0)
            if (ts > 0).any():
                use_total_from_lineups = True
        if not use_total_from_lineups:
            # デバッグ用にサンプルを出力して止める
            df.head(50)[["lineup_id","player_id","player_name"] +
                        ([c for c in ["salary","salary_lineups","total_salary"] if c in df.columns]) ] \
              .to_csv("debug_missing_players.csv", index=False, encoding="utf-8-sig")
            raise SystemExit("全ラインナップの total_salary が 0 です。lineups の salary/total_salary 列に値が入っていません。debug_missing_players.csv を確認してください。")

    # 集計（FutureWarning回避: group_keys=False を明示）
    if use_total_from_lineups:
        # total_salary は lineup 内で同じ値が繰り返される可能性があるので first を使う
        grouped = df.groupby("lineup_id", group_keys=False)
        summary = grouped.apply(lambda g: pd.Series({
            "players": ", ".join(g["player_name"].astype(str)),
            "total_salary": int(pd.to_numeric(g["total_salary"], errors="coerce").fillna(0).iloc[0]),
            "total_exp_fp": float(pd.to_numeric(g["exp_fp"], errors="coerce").fillna(0).sum()),
        })).reset_index()
    else:
        grouped = df.groupby("lineup_id", group_keys=False)
        summary = grouped.apply(lambda g: pd.Series({
            "players": ", ".join(g["player_name"].astype(str)),
            "total_salary": int(pd.to_numeric(g["salary"], errors="coerce").fillna(0).sum()),
            "total_exp_fp": float(pd.to_numeric(g["exp_fp"], errors="coerce").fillna(0).sum()),
        })).reset_index()

    if (summary["total_salary"] == 0).all():
        raise SystemExit("全ラインナップの total_salary が 0 のため停止。入力CSVの salary/total_salary を確認してください。")

    summary = summary.sort_values("total_exp_fp", ascending=False).reset_index(drop=True)
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")
    info(f"Saved: {out_path.name}")
    print(summary.head(10).to_string(
        index=False,
        formatters={"total_salary": "{:,}".format, "total_exp_fp": "{:.4f}".format},
    ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lineups", type=Path, default=Path("lineups_multi.csv"))
    ap.add_argument("--players", type=Path, default=Path("data/processed/players_today.csv"))
    ap.add_argument("--out",     type=Path, default=Path("submit_lineups.csv"))
    args = ap.parse_args()

    # 読み込み
    info(f"reading lineups: {args.lineups.resolve()}")
    lineups_raw = read_csv_safely(args.lineups)
    lineups = normalize_lineups(lineups_raw)

    info(f"reading players: {args.players.resolve()}")
    players_raw = read_csv_safely(args.players)
    players = normalize_players(players_raw)

    # まず players から給与を付ける（数字IDで結合）
    merged = lineups.merge(players[["pid_num","player_name","salary"]],
                           on="pid_num", how="left", validate="many_to_one")

    missing = merged["salary"].isna().sum()

    if missing > 0:
        # フォールバック: lineups 側 salary を使用
        if "salary_lineups" in merged.columns and merged["salary_lineups"].notna().any():
            warn(f"players から {missing} 件の salary が付かないため、lineups の salary を使用します。")
            # playersのsalaryがNaNの行だけ置き換え
            merged["salary"] = merged["salary"].fillna(merged["salary_lineups"])
            # 名前も無ければlineups名で補完
            if "player_name" not in merged.columns or merged["player_name"].isna().any():
                if "player_name" not in merged.columns:
                    merged["player_name"] = merged.get("player_name_lineups", merged["player_id"])
                else:
                    merged["player_name"] = merged["player_name"].fillna(
                        merged.get("player_name_lineups", merged["player_id"])
                    )

            # まだ欠損が残るか確認
            still = merged["salary"].isna().sum()
            if still > 0:
                merged.loc[merged["salary"].isna(), ["player_id","pid_num","player_name_lineups"]]\
                      .drop_duplicates().to_csv("debug_missing_players.csv", index=False, encoding="utf-8-sig")
                raise SystemExit(f"lineups フォールバック後も salary 欠損={still}。debug_missing_players.csv を確認してください。")
            # 集計して保存
            return aggregate_and_save(merged, args.out)
        else:
            # lineups側にsalaryが無い/全部NaN
            merged.loc[merged["salary"].isna(), ["player_id","pid_num"]]\
                  .drop_duplicates().to_csv("debug_missing_players.csv", index=False, encoding="utf-8-sig")
            raise SystemExit(f"players 結合失敗 & lineups に salary が無いため停止。欠損={missing}")

    # 結合成功時
    aggregate_and_save(merged, args.out)

if __name__ == "__main__":
    main()
