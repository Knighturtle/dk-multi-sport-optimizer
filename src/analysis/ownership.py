import pandas as pd

def estimate_ownership(df: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """
    Proxy ownership estimation.
    Adds '_ownership' column (0.0 to 1.0).
    """
    out = df.copy()
    
    # Weights
    w = settings.get("weights", {})
    w_val = w.get("value_rank", 0.4)
    w_proj = w.get("proj_rank", 0.3)
    w_sal = w.get("salary_zscore", 0.2)
    
    # Calculate Ranks (higher is better for ownership)
    # Value Rank: (proj/salary)
    # Avoid 0 salary divide
    sal_safe = out["_salary"].replace(0, 1)
    val = out["_proj"] / sal_safe
    out["rnk_val"] = val.rank(pct=True) # 0..1
    
    # Proj Rank
    out["rnk_proj"] = out["_proj"].rank(pct=True)
    
    # Salary Z-Score (People like playing stars?)
    # or inverse? Usually people pay up for stars.
    mu = out["_salary"].mean()
    sig = out["_salary"].std() if out["_salary"].std() > 0 else 1
    out["z_sal"] = ((out["_salary"] - mu) / sig).clip(-2, 2)
    # Normalize z_sal to 0..1 roughly
    out["norm_sal"] = (out["z_sal"] + 2) / 4
    
    # Simple score
    score = (
        (w_val * out["rnk_val"]) +
        (w_proj * out["rnk_proj"]) +
        (w_sal * out["norm_sal"])
    )
    
    # Scale score to reasonable ownership % 
    # e.g. base + score * scaler
    base_own = settings.get("base_ownership", 0.01)
    max_own = settings.get("max_ownership", 0.50)
    
    # Normalize score 0..1
    if score.max() > score.min():
        score_norm = (score - score.min()) / (score.max() - score.min())
    else:
        score_norm = 0
        
    out["_ownership"] = base_own + (score_norm * (max_own - base_own))
    
    return out
