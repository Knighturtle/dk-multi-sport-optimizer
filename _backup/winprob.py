from __future__ import annotations
import pandas as pd

__all__ = ["estimate_win_prob", "override_pwin_with_odds"]

def estimate_win_prob(
    players: pd.DataFrame,
    odds_col: str = "odds",        # アメリカンオッズの列があれば使う
    out_col: str = "p_win"         # 勝率を書き出す列
) -> pd.DataFrame:
    """
    オッズ列(アメリカン表記)があれば勝率をざっくり推定して `out_col` に入れる。
    なければ 0.5 を入れるだけの安全動作。
    """
    df = players.copy()
    if out_col not in df:
        df[out_col] = 0.5

    if odds_col in df:
        o = pd.to_numeric(df[odds_col], errors="coerce")
        p = pd.Series(index=df.index, dtype=float)
        pos = o > 0
        neg = o < 0
        # American odds -> implied prob
        p[pos] = 100 / (o[pos] + 100)
        p[neg] = (-o[neg]) / ((-o[neg]) + 100)
        df[out_col] = p.fillna(df[out_col])
    return df

def override_pwin_with_odds(
    players: pd.DataFrame,
    odds: pd.DataFrame | None = None,
    team_col: str = "TeamAbbrev",
    odds_team_col: str = "team",
    odds_p_col: str = "p_win",
    out_col: str = "p_win",
) -> pd.DataFrame:
    """
    外部のオッズDataFrameで `players[out_col]` を上書きする。
    `odds` が None/空なら何もしない。
    """
    if odds is None or odds.empty:
        return players
    merged = players.merge(
        odds[[odds_team_col, odds_p_col]],
        how="left", left_on=team_col, right_on=odds_team_col
    )
    merged = merged.drop(columns=[odds_team_col]).rename(columns={odds_p_col: out_col})
    return merged
