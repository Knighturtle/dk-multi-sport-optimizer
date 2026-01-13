import pandas as pd

def estimate_ceiling(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """
    Adds '_ceiling' column based on position volatility.
    ceiling = proj * (1 + volatility)
    """
    out = df.copy()
    
    default_vol = settings.get("default_volatility", 0.25)
    vol_map = settings.get("volatility_by_pos", {})
    
    def get_vol(pos_set):
        # pos_set is a set of strings like {'PG', 'SG'}
        # Return max volatility found for these positions
        if not pos_set:
            return default_vol
        
        vols = [vol_map.get(p, default_vol) for p in pos_set]
        return max(vols)

    # Use _positions (set) or position string
    if "_positions" in out.columns:
        out["_volatility"] = out["_positions"].apply(get_vol)
    else:
        # Fallback if _positions not ready (though engine fixes it, this might run before)
        out["_volatility"] = default_vol
        
    out["_ceiling"] = out["_proj"] * (1 + out["_volatility"])
    return out
