import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def build_dk_import_csv(lineups: List[Dict[str, Any]], rules: Any) -> pd.DataFrame:
    """
    Converts optimized lineups into a DraftKings Import compatible DataFrame.
    
    Format usually requires columns like:
    - PG, SG, SF, PF, C, G, F, UTIL (for NBA)
    - CP, 1B, 2B, 3B, SS, OF, OF, OF (for MLB)
    - etc.
    
    The engine returns lineups with 'slots' list.
    We need to pivot this.
    """
    
    # Determine the columns based on Rules
    # Multi-count slots need to be expanded like OF -> [OF, OF, OF] or [OF1, OF2...] ?
    # DraftKings standard behavior:
    # If there are multiple slots of same name, the header in CSV usually repeats? 
    # NO, standard pandas to_csv with duplicate keys is tricky.
    # Actually DK import templates usually have specific headers.
    # BUT! The widely accepted "Generic" format or recent DK format:
    # They often accept just a list of Player IDs if the headers match the game mode.
    # 
    # Let's rely on the strategy:
    # 1. Expand slots from rules into a flat list of headers.
    #    e.g. if rules say {slot: OF, count: 3}, we expect 3 distinct columns.
    #    Since we can't have duplicate column names in DataFrame effectively, 
    #    we usually name them OF, OF.1, OF.2 or similar, 
    #    OR we assume the user just needs the IDs in the correct order.
    #
    #    Wait, DK template often just uses "Position" as header (like PG, SG...) 
    #    If multiple, it simply has multiple columns named 'OF'. 
    #    Pandas can handle duplicate columns if we build it as a list of dicts 
    #    and then `pd.DataFrame(data, columns=headers)`.
    
    # 1. Build list of headers from rules
    headers = []
    # rules.slots is list of SlotRule(name, eligible, count)
    for s in rules.slots:
        for _ in range(s.count):
            headers.append(s.name)
            
    # 2. Build rows
    rows = []
    
    for lu in lineups:
        # lu['slots'] is a list of dicts: {slot, player_id, ...}
        # We need to map these to the headers.
        # The engine output `slots` list is ALREADY ordered by the logic in engine:
        # "Build ordered slot list: preserve YAML slot order"
        # So we can just iterate them in order.
        
        row_data = []
        # engine output order matches rules order?
        # engine.py:
        #   instance_order = [sname for ...] # sname is "PG__1", "SG__1"
        #   loops sname in instance_order
        # This instance_order was built from `rules.slots` order.
        # So the `lu['slots']` list is exactly in the order of `headers`.
        
        for slot_info in lu["slots"]:
            pid = slot_info["player_id"]
            row_data.append(pid)
            
        rows.append(row_data)
        
    # Create DF with duplicate columns
    # We can pass data as list of lists, and columns as list of strings
    df = pd.DataFrame(rows, columns=headers)
    
    # Add metadata if helpful (though Import might reject extra cols)
    # Usually users copy-paste or upload the file. 
    # Extra columns like "Fpts", "Salary" are good for analysis but might break import if strict.
    # We will exclude them from the primary output or include them at the end.
    # Let's keep strictly ID columns for safety, or check instructions.
    # Prompt says: "汎用として「slot名ごとに player_id を並べる」方式でまず出す"
    # "Lineup Number, Total Salary..." can be separate or ignored.
    # Let's stick to just the slot columns for the Import file.
    
    return df

def save_dk_import_csv(df: pd.DataFrame, sport: str, output_dir: str = "output", prefix: str = "dk_import") -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{sport}_{timestamp}.csv"
    path = out_dir / filename
    
    df.to_csv(path, index=False)
    return path
