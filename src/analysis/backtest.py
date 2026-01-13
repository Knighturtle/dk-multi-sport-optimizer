import pandas as pd
from typing import List, Dict, Any

def backtest_lineups(lineups: List[Dict[str, Any]], df_actual: pd.DataFrame, actual_col: str) -> pd.DataFrame:
    """
    Compares generated lineups against actual scores.
    Returns DataFrame: [lineup_index, proj_total, actual_total, diff]
    """
    # Map pid -> actual
    # Assume df_actual has player_id or we match by name?
    # Ideally logic uses player_id.
    
    # Check ID column
    if "player_id" not in df_actual.columns or actual_col not in df_actual.columns:
        return pd.DataFrame()
        
    id_map = dict(zip(df_actual["player_id"].astype(str), pd.to_numeric(df_actual[actual_col], errors='coerce').fillna(0)))
    
    rows = []
    for i, lu in enumerate(lineups, 1):
        total_act = 0
        hits = 0 # players with >0 pts
        
        for slot in lu["slots"]:
            pid = slot["player_id"]
            act = id_map.get(str(pid), 0)
            total_act += act
            if act > 0:
                hits += 1
                
        diff = total_act - lu["total_proj"]
        
        rows.append({
            "Lineup": i,
            "Proj": lu["total_proj"],
            "Actual": total_act,
            "Diff": diff,
            "Hits": hits
        })
        
    return pd.DataFrame(rows)
