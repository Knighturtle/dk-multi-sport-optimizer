# src/optimizer.py
from typing import List, Dict, Any
import pulp

def solve_lineup(players: List[Dict[str, Any]],
                 slots: List[Dict[str, Any]],
                 cap: float,
                 team_limits: Dict[str, Any] | None = None):
    """2次元割当モデルで最適ラインナップを解く"""
    print(f"[opt] 2D assignment, P={len(players)}, S={len(slots)}")

    P = range(len(players))
    S = range(len(slots))

    allows = [set(s["allows"]) for s in slots]
    pos    = [set(p["pos"])    for p in players]
    salary = [float(p["salary"]) for p in players]
    proj   = [float(p["proj"])   for p in players]
    team   = [p.get("team", "")  for p in players]

    # 変数 y[p,s] = プレイヤーpをスロットsに割り当てるか
    y = pulp.LpVariable.dicts("y", (list(P), list(S)), lowBound=0, upBound=1, cat="Binary")

    m = pulp.LpProblem("dfs_lineup", pulp.LpMaximize)

    # 目的：期待FPの合計を最大化
    m += pulp.lpSum(proj[p] * pulp.lpSum(y[p][s] for s in S) for p in P)

    # 給与上限
    m += pulp.lpSum(salary[p] * pulp.lpSum(y[p][s] for s in S) for p in P) <= cap

    # 各スロットにちょうど1人
    for s in S:
        m += pulp.lpSum(y[p][s] for p in P) == 1

    # 同一プレイヤーは最大1スロット
    for p in P:
        m += pulp.lpSum(y[p][s] for s in S) <= 1

    # ポジション適合
    for p in P:
        for s in S:
            if pos[p].isdisjoint(allows[s]):
                m += y[p][s] == 0

    # チーム上限制約（任意）
    if team_limits and team_limits.get("max_from_one_team"):
        k = int(team_limits["max_from_one_team"])
        teams: Dict[str, list[int]] = {}
        for i, t in enumerate(team):
            teams.setdefault(t, []).append(i)
        for t, plist in teams.items():
            m += pulp.lpSum(y[p][s] for p in plist for s in S) <= k

    status = m.solve(pulp.PULP_CBC_CMD(msg=False))
    print(f"[opt] status = {pulp.LpStatus[status]}")
    if status != pulp.LpStatusOptimal:
        return None

    # 解の抽出（スロット順に並べる）
    chosen: list[Dict[str, Any] | None] = [None] * len(list(S))
    for s in S:
        for p in P:
            if y[p][s].value() > 0.5:
                chosen[s] = players[p]
                break
    return chosen
