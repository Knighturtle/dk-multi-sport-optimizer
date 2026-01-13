import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from sources.normalize import normalize_df

def test_ownership_normalization():
    print("Testing Ownership Normalization...")
    
    # Mock DF simulating loaded CSV
    data = {
        "player_name": ["LeBron James", "Luka Doncic", "Nikola Jokic", "Role Player"],
        "player_id": [1, 2, 3, 4],
        "position": ["SF", "PG", "C", "PG"],
        "team": ["LAL", "DAL", "DEN", "LAL"],
        "salary": [9000, 10000, 11000, 3000],
        "ownership": ["25.5%", 35.0, 40.0, "1%"]
    }
    df = pd.DataFrame(data)
    
    mapping = {
        "player_id": ["player_id"],
        "player_name": ["player_name"],
        "position": ["position"],
        "team": ["team"],
        "salary": ["salary"],
        "ownership": ["ownership", "own%"]
    }
    
    norm = normalize_df(df, mapping, "none")
    
    print("Normalized DF columns:", norm.columns)
    print(norm[["player_name", "ownership"]])
    
    # Verify Conversions
    # LeBron: 25.5% -> 0.255
    lbj = norm.loc[norm["player_name"] == "LeBron James", "ownership"].iloc[0]
    assert 0.25 < lbj < 0.26, f"LeBron mismatch: {lbj}"
    
    # Luka: 35.0 -> 0.35 (Heuristic > 1.0 -> /100)
    luka = norm.loc[norm["player_name"] == "Luka Doncic", "ownership"].iloc[0]
    assert 0.34 < luka < 0.36, f"Luka mismatch: {luka}"
    
    # Jokic: 0.40 -> 0.40 (Heuristic <= 1.0 -> keep)
    jokic = norm.loc[norm["player_name"] == "Nikola Jokic", "ownership"].iloc[0]
    assert 0.39 < jokic < 0.41, f"Jokic mismatch: {jokic}"

    print("PASS: Ownership Normalization")

def test_engine_objective_mock():
    # Simple check if Pulp accepts the objective construction logic
    # (Without running full solver)
    print("Testing Engine Objective construction (Mock)...")
    pass

if __name__ == "__main__":
    test_ownership_normalization()
    test_engine_objective_mock()
