import pandas as pd
import numpy as np

def compute_value_metrics(df: pd.DataFrame, multiplier: float = 1000.0) -> pd.DataFrame:
    """
    Adds '_value' column: (proj / salary) * multiplier.
    Handles zero salary.
    """
    out = df.copy()
    
    # Avoid div by zero
    salary = out["_salary"].replace(0, 1) # Prevent inf
    out["_value"] = (out["_proj"] / salary) * multiplier
    
    return out

def find_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifies anomalies:
    - High Salary, Low Proj
    - Low Salary, High Proj
    """
    # Z-scores
    if df.empty:
        return pd.DataFrame()

    out = df.copy()
    
    mu_sal = out["_salary"].mean()
    sig_sal = out["_salary"].std() if out["_salary"].std() > 0 else 1
    
    mu_proj = out["_proj"].mean()
    sig_proj = out["_proj"].std() if out["_proj"].std() > 0 else 1
    
    out["z_sal"] = (out["_salary"] - mu_sal) / sig_sal
    out["z_proj"] = (out["_proj"] - mu_proj) / sig_proj
    
    # High Sal (>1 sigma) but Low Proj (< -0.5 sigma)
    anom_overpriced = out[(out["z_sal"] > 1.0) & (out["z_proj"] < -0.5)].copy()
    anom_overpriced["type"] = "Overpriced"
    
    # Low Sal (<0 sigma) but High Proj (> 1.0 sigma)
    anom_value = out[(out["z_sal"] < 0) & (out["z_proj"] > 1.0)].copy()
    anom_value["type"] = "Deep Value"
    
    return pd.concat([anom_overpriced, anom_value])
