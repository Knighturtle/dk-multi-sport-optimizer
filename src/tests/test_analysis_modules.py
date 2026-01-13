import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))

from analysis.distribution import estimate_distribution_parameters
from analysis.correlation_model import calculate_lineup_correlation_score
from analysis.ev import calculate_ev

def test_distribution():
    print("Testing Distribution...")
    df = pd.DataFrame({
        "player_id": [1, 2],
        "_proj": [10.0, 50.0],
        "_salary": [3000, 10000]
    })
    
    out = estimate_distribution_parameters(df)
    
    assert "_stddev" in out.columns
    assert "_floor" in out.columns
    assert "_ceiling" in out.columns
    
    # Check default heuristic
    # StdDev = 0.25 * Proj
    assert abs(out.loc[0, "_stddev"] - 2.5) < 0.1
    # Ceiling = Proj + 1.5 * StdDev = 10 + 1.5*2.5 = 10 + 3.75 = 13.75
    assert abs(out.loc[0, "_ceiling"] - 13.75) < 0.1
    print("PASS: Distribution")

def test_ev():
    print("Testing EV...")
    df = pd.DataFrame({
        "player_id": [1],
        "_proj": [20.0],
        "_ceiling": [30.0],
        "_stddev": [5.0],
        "_ownership": [0.10],
    })
    
    settings = {
        "w_proj": 1.0,
        "w_ceil": 0.5,
        "w_std": 0.1,
        "w_chalk": 10.0, # Penalty 10 * own
        "w_lev": 1.0, # Bonus 1.0 * Proj / (Own+0.05)
    }
    
    out = calculate_ev(df, settings)
    
    # Manual Calc:
    # Term 1 (Proj): 20 * 1.0 = 20
    # Term 2 (Ceil): 30 * 0.5 = 15
    # Term 3 (Std): 5.0 * 0.1 = 0.5
    # Term 4 (Chalk): 0.10 * 10.0 = 1.0 (subtracted)
    # Term 5 (Lev): 1.0 * (20 / 0.15) = 133.33...
    
    # EV = 20 + 15 + 0.5 - 1.0 + 133.33 = 167.83
    
    ev = out.loc[0, "_ev"]
    print(f"Calculated EV: {ev}")
    assert ev > 100
    print("PASS: EV calculation")

def test_correlation_score():
    print("Testing Correlation Score...")
    # Mock lookup
    df_lookup = pd.DataFrame({
        "player_id": ["1", "2", "3"],
        "_team": ["LAL", "LAL", "GSW"]
    })
    
    lineup = [
        {"player_id": 1, "player_name": "A"},
        {"player_id": 2, "player_name": "B"}, # Stack with 1
        {"player_id": 3, "player_name": "C"}
    ]
    
    score = calculate_lineup_correlation_score(lineup, df_lookup)
    
    # 2 LAL players -> Count 2 
    # Logic: 2 * 0.1 = 0.2
    print(f"Corr Score: {score}")
    assert abs(score - 0.2) < 0.01
    print("PASS: Correlation")

if __name__ == "__main__":
    test_distribution()
    test_ev()
    test_correlation_score()
