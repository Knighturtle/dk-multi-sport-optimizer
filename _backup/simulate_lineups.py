# simulate_lineups.py
# ------------------------------------------------------------
# ラインナップごとのスコア分布を簡易モンテカルロで推定し、
# EV / p90 / Sharpe-like 指標でランキング CSV を出力する。
# 必要ファイル : lineups_multi.csv（各行=選手、lineup_id, exp_fp を含む）
# 出力        : rank_ev.csv / rank_p90.csv / rank_sharpe.csv
# ------------------------------------------------------------

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd


# ===== デフォルト設定 =====
DEFAULT_INPUT = "lineups_multi.csv"
DEFAULT_SEED = 2025
DEFAULT_SIM = 20000
# プレイヤー単位の標準偏差のスケール： sigma_i ≈ RISK_MULT * sqrt(max(mu_i, 0.1))
DEFAULT_RISK_MULT = 0.35


def load_lineups(path: Path) -> pd.DataFrame:
    """lineups_multi.csv を読み込む（存在チェック付き）"""
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(
            f"[error] 入力ファイルが見つかりません: {path} "
            f"(先に run_pipeline.py を実行して lineups_multi.csv を作成してください)"
        )
    df = pd.read_csv(path)
    # 必須列のチェック
    need = {"lineup_id"}
    if not need.issubset(df.columns):
        raise ValueError(f"[error] {path} に必須列が不足しています。必要: {need}, 実際: {set(df.columns)}")
    return df


def pick_score_column(df: pd.DataFrame) -> str:
    """
    スコア列を選ぶ。優先順位: exp_fp → total_exp_fp
    exp_fp が無い場合は total_exp_fp を使用し、均等割りで擬似 mu_i を作る。
    """
    if "exp_fp" in df.columns:
        return "exp_fp"
    if "total_exp_fp" in df.columns:
        return "total_exp_fp"
    raise ValueError(
        "[error] lineups_multi.csv に exp_fp も total_exp_fp も見つかりません。"
        "先に run_pipeline.py を実行してください。"
    )


def simulate_lineup(
    mu: np.ndarray,
    rng: np.random.Generator,
    n_sim: int,
    risk_mult: float,
) -> dict:
    """
    1 ラインナップの総 FP を n_sim 回サンプリングし、EV/STD/p90 を返す。
    mu: 各選手の期待 FP（>=0）
    """
    # 標準偏差の素朴なモデル：sigma_i ≈ risk_mult * sqrt(max(mu_i, 0.1))
    sigma = risk_mult * np.sqrt(np.maximum(mu, 0.1))

    # 正規 + 0下限クリップでサンプル
    draws = rng.normal(loc=mu, scale=sigma, size=(n_sim, mu.size))
    draws = np.clip(draws, 0.0, None)
    total = draws.sum(axis=1)

    ev = float(total.mean())
    std = float(total.std(ddof=1))
    p90 = float(np.quantile(total, 0.90))

    return {
        "ev": ev,
        "std": std,
        "p90": p90,
        "sharpe_like": ev / (std + 1e-9),
    }


def build_rankings(
    df: pd.DataFrame,
    score_col: str,
    n_sim: int,
    seed: int,
    risk_mult: float,
) -> pd.DataFrame:
    """
    lineup_id ごとにシミュレーションし、指標をまとめて返す。
    """
    rng = np.random.default_rng(seed)

    results = []
    for lid, g in df.groupby("lineup_id", sort=False):
        # mu の作り方
        if score_col == "exp_fp":
            mu = g["exp_fp"].astype(float).clip(lower=0.0).to_numpy()
        else:
            # total_exp_fp の場合は、人数で均等割（簡易）
            total = float(g["total_exp_fp"].iloc[0])
            n = max(int(g.shape[0]), 1)
            mu = np.full(n, max(total / n, 0.0), dtype=float)

        stats = simulate_lineup(mu, rng, n_sim=n_sim, risk_mult=risk_mult)
        results.append(
            {
                "lineup_id": lid,
                "players": ", ".join(
                    f"{n} ({int(s)})"
                    for n, s in zip(
                        g.get("player_name", pd.Series(["?"] * len(g))),
                        g.get("salary", pd.Series([0] * len(g))),
                    )
                ),
                "total_salary": float(g.get("total_salary", pd.Series([0])).iloc[0])
                if "total_salary" in g.columns
                else 0.0,
                **stats,
            }
        )

    res = pd.DataFrame(results)
    return res


def save_rank_files(res: pd.DataFrame) -> None:
    """ランキング 3種を CSV 保存し、コンソールにも上位を出力"""
    res_ev = res.sort_values("ev", ascending=False)
    res_p90 = res.sort_values("p90", ascending=False)
    res_sh = res.sort_values("sharpe_like", ascending=False)

    res_ev.to_csv("rank_ev.csv", index=False)
    res_p90.to_csv("rank_p90.csv", index=False)
    res_sh.to_csv("rank_sharpe.csv", index=False)

    print("\n[Top 5 by EV]")
    print(res_ev.head(5).to_string(index=False))
    print("\n[Top 5 by p90]（GPP向けの上振れ重視）")
    print(res_p90.head(5).to_string(index=False))
    print("\n[Top 5 by Sharpe-like]（キャッシュ向け）")
    print(res_sh.head(5).to_string(index=False))
    print('\nSaved: "rank_ev.csv", "rank_p90.csv", "rank_sharpe.csv"')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default=DEFAULT_INPUT,
                    help="lineups_multi.csv のパス")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--n-sim", type=int, default=DEFAULT_SIM)
    ap.add_argument("--risk", type=float, default=DEFAULT_RISK_MULT,
                    help="プレイヤー標準偏差の係数（大きくすると分散が大きくなる）")
    args = ap.parse_args()

    path = Path(args.input)
    print(f"[info] input: {path.resolve()}")

    df = load_lineups(path)
    score_col = pick_score_column(df)
    print(f"[info] use score_col: {score_col}")

    res = build_rankings(
        df=df,
        score_col=score_col,
        n_sim=args.n_sim,
        seed=args.seed,
        risk_mult=args.risk,
    )
    save_rank_files(res)


if __name__ == "__main__":
    main()
