# -*- coding: utf-8 -*-
"""
大量のラインナップを自動生成 → long 形式に書き出し → submit_lineups.csv を作成
前提:
  - 入力: data/processed/players_with_proj_norm.csv
      必須列: player_id, salary, expected_points
  - 出力:
      data/processed/lineups_long_for_export.csv
      data/processed/submit_lineups.csv
メモ:
  いまのデータ構成ではポジション列がないので、
  まずは「CAP内で重複なし9人」のシンプルなラインナップを大量生成します。
"""

import random
from itertools import combinations
from typing import List, Tuple, Set
import numpy as np
import pandas as pd
from pathlib import Path

# --------------------
# パラメータ
# --------------------
SLOTS = 9                 # 1ラインナップの人数（MLBなら9）
CAP = 50000               # 給与上限
N_LINEUPS_TARGET = 1000   # 生成したいラインナップ数の目標
MAX_TRIES = 200000        # 試行回数(増やすと精度↑だが時間↑)

# ファイルパス
ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
PLAYERS_CSV = PROCESSED / "players_with_proj_norm.csv"
LONG_OUT = PROCESSED / "lineups_long_for_export.csv"
SUBMIT_OUT = PROCESSED / "submit_lineups.csv"

# --------------------
# データ読み込み
# --------------------
dfp = pd.read_csv(PLAYERS_CSV, encoding="utf-8-sig")
need_cols = {"player_id", "salary", "expected_points"}
missing = need_cols - set(dfp.columns)
if missing:
    raise ValueError(f"players_with_proj_norm.csv に必要列がありません: {missing}")

# 型整形（保険）
dfp["player_id"] = pd.to_numeric(dfp["player_id"], errors="coerce").astype("Int64")
dfp["salary"] = pd.to_numeric(dfp["salary"], errors="coerce").fillna(0).astype(int)
dfp["expected_points"] = pd.to_numeric(dfp["expected_points"], errors="coerce").fillna(0.0)

# 明らかに異常な行は落とす
dfp = dfp.dropna(subset=["player_id"])
dfp = dfp[dfp["salary"] > 0].copy()
dfp = dfp.reset_index(drop=True)

players = dfp[["player_id", "salary", "expected_points"]].values.tolist()

# --------------------
# ラインナップ生成のヘルパ
# --------------------
def try_build_lineup(players_arr: np.ndarray, cap: int, slots: int) -> Tuple[List[int], int, float]:
    """
    ランダムな順序で走査して、CAP内でSLOTS名選ぶ簡易貪欲。
    """
    order = np.random.permutation(len(players_arr))
    picked = []
    total_sal = 0
    total_fp = 0.0

    for idx in order:
        pid, sal, fp = players_arr[idx]
        if pid in picked:
            continue
        if len(picked) >= slots:
            break
        if total_sal + sal <= cap:
            picked.append(int(pid))
            total_sal += int(sal)
            total_fp += float(fp)
        # slots揃ったら終了
        if len(picked) == slots:
            break

    if len(picked) == slots:
        return picked, total_sal, total_fp
    return [], 0, 0.0

def lineup_signature(pids: List[int]) -> Tuple[int, ...]:
    """重複判定用のソート済タプル"""
    return tuple(sorted(pids))

# --------------------
# 大量生成
# --------------------
players_np = dfp[["player_id", "salary", "expected_points"]].to_numpy()
seen: Set[Tuple[int, ...]] = set()
lineups: List[Tuple[List[int], int, float]] = []

best_fp = -1.0
best_lineup = None

for t in range(MAX_TRIES):
    pids, sal, fp = try_build_lineup(players_np, CAP, SLOTS)
    if not pids:
        continue
    sig = lineup_signature(pids)
    if sig in seen:
        continue
    seen.add(sig)
    lineups.append((pids, sal, fp))

    if fp > best_fp:
        best_fp = fp
        best_lineup = (pids, sal, fp)

    if len(lineups) >= N_LINEUPS_TARGET:
        break

# 1件も作れない場合
if not lineups:
    raise RuntimeError("有効なラインナップが作れませんでした。CAP や SLOTS、データの salary を見直してください。")

# スコア順に並べて上位を使う（安全のため上位N_LINEUPS_TARGET件に切る）
lineups.sort(key=lambda x: x[2], reverse=True)
lineups = lineups[:N_LINEUPS_TARGET]

print(f"[info] 生成ラインナップ数: {len(lineups)} / 試行: {MAX_TRIES}")

# --------------------
# long形式を書き出し
# --------------------
records = []
for i, (pids, sal, fp) in enumerate(lineups, start=1):
    for pid in pids:
        records.append({"lineup_id": i, "player_id": pid})

long_df = pd.DataFrame(records)
long_df.to_csv(LONG_OUT, index=False, encoding="utf-8-sig")
print(f"[info] write: {LONG_OUT}")

# --------------------
# submit_lineups.csv を作る（あなたの既存パイプと揃える）
# --------------------
# longを wide に要約
sum_df = (
    long_df.merge(dfp[["player_id", "salary", "expected_points"]], on="player_id", how="left")
           .groupby("lineup_id", as_index=False)
           .agg(players=("player_id", lambda s: ",".join(map(str, s))),
                total_salary=("salary", "sum"),
                total_exp_fp=("expected_points", "sum"))
)

# DraftKings 風の並び（既にあなたの環境がこの列名で回っているので踏襲）
sum_df = sum_df[["lineup_id", "players", "total_salary", "total_exp_fp"]]
sum_df.sort_values("total_exp_fp", ascending=False, inplace=True)
sum_df.to_csv(SUBMIT_OUT, index=False, encoding="utf-8-sig")
print(f"[info] write: {SUBMIT_OUT}")

# 先頭を表示（デバッグ）
print(sum_df.head().to_string(index=False))
