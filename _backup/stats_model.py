"""stats_model stub"""
from __future__ import annotations
import pandas as pd

__all__ = ["enrich_expectations"]

def _first_col(df: pd.DataFrame, names: list[str]) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None

def enrich_expectations(players: pd.DataFrame, out_col: str = "expected_fp") -> pd.DataFrame:
    """
    予測指標列 `expected_fp` を用意する（無ければ近似で作成）。
    既に同名列があればそのまま返す。
    """
    df = players.copy()
    if out_col in df.columns:
        return df

    base = _first_col(df, ["proj", "Proj", "FPPG", "avgPointsPerGame", "AvgPointsPerGame"])
    if base is not None:
        df[out_col] = pd.to_numeric(df[base], errors="coerce").fillna(0.0)
    else:
        df[out_col] = 0.0
    return df
