import pandas as pd

def calculate_ev(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """
    Calculates '_ev' (Expected Value) score for GPP.
    EV = w1*Proj + w2*Ceiling + w3*StdDev - w4*ChalkPenalty + w5*LeverageBonus
    """
    out = df.copy()
    
    w_proj = settings.get("w_proj", 1.0)
    w_ceil = settings.get("w_ceil", 0.5)
    w_std = settings.get("w_std", 0.0) # Bonus for volatility?
    w_chalk = settings.get("w_chalk", 0.0) # Penalty for high own
    w_lev = settings.get("w_lev", 0.0)
    
    # Ensure columns exist (distribution.py should run before this)
    if "_ceiling" not in out.columns:
        out["_ceiling"] = out["_proj"] # Fallback
    if "_stddev" not in out.columns:
        out["_stddev"] = 0.0
    if "_ownership" not in out.columns:
        out["_ownership"] = 0.0
        
    chalk_thresh = float(settings.get("chalk_threshold", 0.20))
    
    # Chalk Penalty: if own > thresh, penalty proportional to own
    # or just linear penalty on ownership?
    # Simple: - w_chalk * ownership
    chalk_term = out["_ownership"] * w_chalk
    
    # Leverage Bonus: High Proj but Low Own?
    # Heuristic: Value * (1 - ownership)
    # Or discrete bonus?
    # Let's use: w_lev * (Proj / (Ownership + 0.05)) --- "Leverage Score"
    # Avoiding div by zero
    leverage_term = w_lev * (out["_proj"] / (out["_ownership"] + 0.05))
    
    out["_ev"] = (w_proj * out["_proj"]) + \
                 (w_ceil * out["_ceiling"]) + \
                 (w_std * out["_stddev"]) - \
                 chalk_term + \
                 leverage_term
                 
    return out
