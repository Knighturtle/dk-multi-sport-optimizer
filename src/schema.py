# src/schema.py
COLUMNS = [
    "player_id","name","team","opp","positions","salary","proj_points",
    "site","sport","game_id","slate_id","status"
]
POS_SEP = "|"

def coerce_positions(x):
    if x is None or x == "":
        return []
    if isinstance(x, list):
        return x
    return [p.strip() for p in str(x).split(POS_SEP) if p.strip()]
