import pandas as pd

def validate_df(df: pd.DataFrame) -> None:
    """
    Validates that the DataFrame has the required columns and simple correctness.
    Raises ValueError if invalid.
    """
    required = ["player_id", "player_name", "position", "salary", "proj_points"]
    missing = [c for c in required if c not in df.columns]
    
    if missing:
        raise ValueError(f"Normalized data is missing columns: {missing}")
        
    if df.empty:
        raise ValueError("Data is empty after normalization.")
        
    # Check for meaningful data
    if (df["salary"] == 0).all():
        # Not strictly an error, but suspicious for DFS
        pass
