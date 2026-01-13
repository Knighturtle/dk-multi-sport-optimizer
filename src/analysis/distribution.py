import pandas as pd
import numpy as np

def estimate_distribution_parameters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Estimates Floor, Ceiling, and StdDev for each player.
    
    Logic:
    - StdDev (sigma) estimated heuristic based on position/salary or existing 'volatility'.
    - Floor = Proj - 1.0 * sigma (clipped at 0)
    - Ceiling = Proj + 1.0 * sigma (or use existing _ceiling if merged)
    - Uses columns '_proj', '_salary', '_positions'
    
    Returns df with added: '_floor', '_ceiling', '_stddev'
    """
    out = df.copy()
    
    # 1. Base Volatility (Sigma factor)
    # Heuristic: Higher salary players might vary more in abs terms, 
    # but some positions are more volatile (e.g. WR vs QB).
    # We can rely on settings or simple heuristics.
    # Default 25% of Proj as StdDev?
    
    if "_stddev" not in out.columns:
        # Default heuristic: 25% coeff of variation + varying by pos could be added later
        out["_stddev"] = out["_proj"] * 0.25
        # Ensure min stddev to avoid 0 variance issues
        out.loc[out["_stddev"] < 1.0, "_stddev"] = 1.0

    # 2. Ceiling
    # If _ceiling already exists (e.g. from prior simple calculation or import), prefer it?
    # Or overwrite with more robust stat method?
    # Let's respect imported ceiling if valid (significantly different from proj), else calc.
    # The simple ceiling module did: proj * (1+vol). 
    # Here we standardize: Ceiling = Proj + 2 * StdDev (approx 95% interval top)?
    # GPP Ceiling usually means "75th or 85th percentile".
    # Let's say Ceiling = Proj + 1.5 * StdDev for now.
    
    if "_ceiling" not in out.columns or out["_ceiling"].fillna(0).sum() == 0:
        out["_ceiling"] = out["_proj"] + (1.5 * out["_stddev"])
    
    # 3. Floor
    # Floor = Proj - 1.0 * StdDev
    out["_floor"] = out["_proj"] - (1.0 * out["_stddev"])
    out["_floor"] = out["_floor"].clip(lower=0.0)
    
    return out
