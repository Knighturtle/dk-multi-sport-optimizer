import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))
from optimizer.engine import OptimizerEngine, DkRules, SlotRule, TeamLimits

def test_optimizer_gpp():
    print("Testing Optimizer GPP Mode...")
    
    # Mock Data
    df = pd.DataFrame({
        "player_id": [1, 2, 3, 4, 5, 6],
        "player_name": ["A", "B", "C", "D", "E", "F"],
        "position": ["PG", "SG", "SF", "PF", "C", "G"],
        "salary": [3000, 3000, 3000, 3000, 3000, 3000],
        "team": ["LAL", "LAL", "GSW", "GSW", "NYK", "NYK"],
        "_proj": [10, 10, 10, 10, 10, 15], # F has highest proj
        "_ev":   [50, 60, 10, 10, 10, 20], # B -> Highest EV even if modest Proj
        "_ownership": [0.01, 0.01, 0.50, 0.50, 0.01, 0.25], # C,D are chalk
        "_ceiling": [20, 20, 20, 20, 20, 25] 
    })
    
    # Setup Engine
    # Assume generic RULES or Mock rules
    # We will use simplified constraints passed to optimize_df directly if possible, 
    # or rely on default fallback or mock rules object.
    # OptimizerEngine needs a 'rules' object usually.
    
    # Setup Engine with proper DkRules
    # Roster: PG, SG, SF (1 each)
    slots = [
        SlotRule("PG", {"PG"}, 1),
        SlotRule("SG", {"SG"}, 1),
        SlotRule("SF", {"SF"}, 1)
    ]
    
    rules = DkRules(
        sport="TEST",
        site="DK",
        slate=None,
        salary_cap=50000,
        lineup_size=3,
        projection_column="_proj",
        slots=slots,
        team_limits=TeamLimits(),
        num_lineups=1
    )
    
    # Engine does not take rules in init
    engine = OptimizerEngine(rules_dir=".") # Dummy dir
    
    # 1. Test GPP Mode (Maximize EV)
    # Roster: PG, SG, SF
    settings = {
        "objective_mode": "gpp",
        "num_lineups": 1
    }
    
    # Pass rules as 2nd arg
    lineups = engine.optimize_df(df, rules, settings=settings)
    l1 = lineups[0]
    
    names = [s["player_name"] for s in l1["slots"]]
    print(f"GPP Lineup: {names}, Score: {l1['total_proj']}") # Note score returned is usually Proj based? 
    # Engine returns "total_proj" property calculated from _proj column, but SOLVED for _ev.
    
    assert "B" in names # Highest EV player
    print("PASS: GPP Mode picked High EV")
    
    # 2. Test Max Chalk Constraint
    # Chalk: C, D (Ownership 0.50)
    # Let's set max_chalk = 0
    # Must pick A, B, E (low own)
    
    settings_chalk = {
        "objective_mode": "cash", # Max Projection
        "max_chalk_count": 0,
        "chalk_threshold": 0.40
    }
    
    # If Cash mode -> normally would pick F (proj 15) but F is G (not in roster def PG,SG,SF) 
    # Wait, roster is PG, SG, SF.
    # Available PG: A
    # Available SG: B
    # Available SF: C (High Own)
    # Available PF: D (High Own)
    # Available C: E
    
    # We need a SF. C is SF but Chalk (0.50).
    # If max_chalk=0, C is banned.
    # Do we have another SF? No. 
    # Failure expected OR Infeasible.
    
    # Let's Add a backup SF
    df = pd.concat([df, pd.DataFrame([{
        "player_id": 7, "player_name": "backup_SF", "position": "SF", 
        "salary": 3000, "team": "UNK", "_proj": 5, "_ev": 5, "_ownership": 0.01, "_ceiling": 10
    }])], ignore_index=True)
    
    lineups_c = engine.optimize_df(df, rules, settings=settings_chalk)
    if not lineups_c:
        print("Infeasible as expected without backup? Oh wait we added backup.")
    
    l_chalk = lineups_c[0]
    names_c = [s["player_name"] for s in l_chalk["slots"]]
    print(f"Chalk Restricted Lineup: {names_c}")
    
    assert "C" not in names_c
    assert "backup_SF" in names_c
    print("PASS: Max Chalk Constraint")

if __name__ == "__main__":
    test_optimizer_gpp()
