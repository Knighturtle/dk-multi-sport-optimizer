import pandas as pd
from typing import List, Dict, Any

def calculate_exposure(lineups: List[Dict[str, Any]], total_lineups: int) -> pd.DataFrame:
    """
    Returns DataFrame with player exposure stats.
    cols: player_name, exposure_count, exposure_pct
    """
    if not lineups:
        return pd.DataFrame()
        
    counts = {}
    names = {}
    
    for lu in lineups:
        for p in lu["slots"]:
            pid = p["player_id"]
            counts[pid] = counts.get(pid, 0) + 1
            names[pid] = p["player_name"]
            
    rows = []
    for pid, count in counts.items():
        rows.append({
            "player_id": pid,
            "player_name": names[pid],
            "count": count,
            "pct": (count / total_lineups) * 100
        })
        
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("pct", ascending=False)
    return df
