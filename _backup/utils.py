"""utils stub"""
# src/utils.py
from pathlib import Path
import pandas as pd

# YAML を読むのに必要
try:
    import yaml
except ImportError:
    yaml = None  # 未インストールでも落ちないように（後でチェック）

def read_yaml(path) -> dict:
    """YAML を辞書で返す"""
    if yaml is None:
        raise ImportError(
            "PyYAML が必要です。`pip install pyyaml` を実行してください。"
        )
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def read_players_csv(path):
    """プレイヤー CSV を pandas.DataFrame で返す"""
    return pd.read_csv(path)

__all__ = ["read_yaml", "read_players_csv"]
