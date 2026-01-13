# adapters/dk/common.py
from pathlib import Path
import pandas as pd
from src.schema import COLUMNS, POS_SEP

# DraftKings（クラシック）の列名マッピング
DK_COLS = {
    "Name": "name",
    "ID": "player_id",
    "TeamAbbrev": "team",
    "Roster Position": "positions",
    "Salary": "salary",
    "AvgPointsPerGame": "proj_points",
    # "Opponent": "opp",  # 無ければ空でOK
}

def _read_csv_utf8(path: Path) -> pd.DataFrame:
    """Windows環境での文字化け対策：UTF-8優先で安全に読む。"""
    for enc in ("utf-8", "utf-8-sig", "cp932", "cp1252"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    # 最後はエンコーディング自動判別（失敗時はそのままエラー）
    return pd.read_csv(path, encoding_errors="ignore")

def load_and_normalize(raw_csv: Path, sport: str) -> pd.DataFrame:
    df = _read_csv_utf8(raw_csv)

    out = pd.DataFrame()
    for src, dst in DK_COLS.items():
        out[dst] = df[src] if src in df.columns else None

    # "PG/SG" → "PG|SG" に統一
    out["positions"] = (
        out["positions"]
        .fillna("")
        .astype(str)
        .str.replace("/", ",", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", POS_SEP, regex=False)
    )

    out["salary"] = pd.to_numeric(out["salary"], errors="coerce")
    out["proj_points"] = pd.to_numeric(out["proj_points"], errors="coerce").fillna(0.0)

    # 追加の共通列
    out["site"], out["sport"] = "dk", sport
    out["game_id"], out["slate_id"], out["status"], out["opp"] = "", "", "", ""

    # 必須列を保証
    for c in COLUMNS:
        if c not in out.columns:
            out[c] = ""
    return out[COLUMNS]
