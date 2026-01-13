# make_lineups_multi.py
import argparse
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="rank_ev.csv のパス")
    ap.add_argument("--out", required=True, help="出力 lineups_multi.csv のパス")
    ap.add_argument("--top", type=int, default=150, help="上位 n 行だけ出力")
    ap.add_argument("--sort_by", default=None, help="必要なら 'ev' や 'sharpe_like' で降順ソート")
    args = ap.parse_args()

    df = pd.read_csv(args.src)

    # 必須列チェック
    need = ["lineup_id", "players", "total_salary"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise SystemExit(f"missing columns in {args.src}: {miss}")

    if args.sort_by and args.sort_by in df.columns:
        df = df.sort_values(args.sort_by, ascending=False)

    out = df[need].head(args.top).copy()
    out["total_salary"] = (
        pd.to_numeric(out["total_salary"], errors="coerce").fillna(0).astype(int)
    )

    out.to_csv(args.out, index=False, encoding="utf-8")
    print(f"[ok] wrote {args.out} rows:{len(out)}")

if __name__ == "__main__":
    main()
