import pandas as pd
from typing import Dict, List, Any

def normalize_df(df: pd.DataFrame, config_mapping: Dict[str, List[str]], projection_col: str) -> pd.DataFrame:
    """
    Normalizes a raw DataFrame into the standard internal format.
    
    Standard Columns:
    - player_id (str)
    - player_name (str)
    - position (str)
    - salary (int)
    - team (str)
    - proj_points (float)
    - ownership (float)
    - ceiling (float)
    """
    # Create working copy
    out = pd.DataFrame()
    cols = df.columns
    
    # Helper to find first matching column
    def find_col(possible_names):
        for name in possible_names:
            # Case-insensitive check
            match = next((c for c in cols if str(c).lower() == str(name).lower()), None)
            if match:
                return match
        return None

    # 1. Player ID
    c_id = find_col(config_mapping.get("player_id", []))
    if c_id:
        out["player_id"] = df[c_id].astype(str).str.strip()
    else:
        # Critical failure if no ID
        # Alternatively, generate ID? No, optimizer needs ID.
        raise ValueError("Missing 'player_id' column (checked variations in config)")

    # 2. Player Name
    c_name = find_col(config_mapping.get("player_name", []))
    if c_name:
        out["player_name"] = df[c_name].astype(str).str.strip()
    else:
        out["player_name"] = "Unknown"

    # 3. Position
    c_pos = find_col(config_mapping.get("position", []))
    if c_pos:
        out["position"] = df[c_pos].astype(str).str.strip()
    else:
        # Critical failure?
        raise ValueError("Missing 'position' column")

    # 4. Salary
    c_salary = find_col(config_mapping.get("salary", []))
    if c_salary:
        out["salary"] = pd.to_numeric(df[c_salary], errors="coerce").fillna(0).astype(int)
    else:
        out["salary"] = 0

    # 5. Team
    c_team = find_col(config_mapping.get("team", []))
    if c_team:
        out["team"] = df[c_team].astype(str).str.strip().str.upper()
    else:
        out["team"] = ""

    # 6. Projections
    # Priority: The explicit 'projection_col' arg -> then the mapping config
    # Often the user provides a specific CSV with "MyProj".
    # We should look for projection_col FIRST.
    
    found_proj_col = None
    # 1. Exact match for rule-defined col
    if projection_col in df.columns:
        found_proj_col = projection_col
    else:
        # 2. Mapping list
        found_proj_col = find_col(config_mapping.get("projection", []) + [projection_col])
    
    if found_proj_col:
        out["proj_points"] = pd.to_numeric(df[found_proj_col], errors="coerce").fillna(0.0)
    else:
        # Warn or default to 0?
        # Optimizer expects projections.
        # Let's default to 0 but maybe the user entered data without proj.
        out["proj_points"] = 0.0

    # 7. Ownership
    c_own = find_col(config_mapping.get("ownership", []))
    if c_own:
        # Check if string with %
        if df[c_own].dtype == object:
            temp_own = df[c_own].astype(str).str.replace("%", "", regex=False)
        else:
            temp_own = df[c_own]
        
        out["ownership"] = pd.to_numeric(temp_own, errors='coerce')
        
        # Heuristic: if max > 1.0, assume it's 0-100 scale
        if out["ownership"].max() > 1.0:
            out["ownership"] = out["ownership"] / 100.0
            
        out["ownership"] = out["ownership"].fillna(0.0)
    else:
        out["ownership"] = 0.0

    # 8. Ceiling
    c_ceiling = find_col(config_mapping.get("ceiling", []))
    if c_ceiling:
        out["ceiling"] = pd.to_numeric(df[c_ceiling], errors='coerce').fillna(out["proj_points"])
    else:
        out["ceiling"] = out["proj_points"] # Default to projection if not found

    # Handle Duplicates
    # If same player_id exists, take the last one (or max proj?)
    # Simple strategy: Max projection (if multiple entries, usually one is better or correction)
    # But DraftKings ID should be unique per slate.
    out = out.sort_values("proj_points", ascending=False).drop_duplicates("player_id", keep="first")
    
    # Filter invalid records (no salary, empty ID)
    out = out[out["player_id"] != "nan"]
    out = out[out["player_id"] != ""]
    
    return out.reset_index(drop=True)
