import pandas as pd

def compute_correlation_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a simple pivot table of avg projection by Team vs Position.
    This helps visualize which teams have strong positions.
    """
    if df.empty or "_team" not in df.columns or "position" not in df.columns:
        return pd.DataFrame()
        
    # pivot: index=Team, columns=Pos, values=AvgProj
    # Filter only relevant columns to avoid type errors
    data = df[["_team", "position", "_proj"]].copy()
    
    # Standardize position (taking first if slash)
    data["main_pos"] = data["position"].apply(lambda x: str(x).split("/")[0])
    
    pivot = data.pivot_table(index="_team", columns="main_pos", values="_proj", aggfunc="mean").fillna(0)
    return pivot
