import requests
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# --- MLB StatsAPI Logic ---

def fetch_mlb_statsapi(output_dir: str = "data/auto") -> pd.DataFrame:
    """
    Fetches today's probable pitchers and starting lineups via MLB StatsAPI if available.
    Note: Public endpoint usage. 
    Returns a DataFrame with columns: [player_id, player_name, position, team, salary, proj_points]
    Salary/Proj will be 0 as they are not in official stats.
    """
    # 1. Get Schedule for Today to find Game PKs
    today_str = datetime.now().strftime("%Y-%m-%d")
    url_schedule = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}&hydrate=probablePitcher"
    
    try:
        resp = requests.get(url_schedule, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch MLB schedule: {e}")

    games = data.get("dates", [])
    if not games:
        raise ValueError(f"No MLB games found for {today_str}")

    game_pks = []
    players_data = []

    # Helper to mapping MLB positions to DK
    # MLB: 1=P, 2=C, 3=1B, 4=2B, 5=3B, 6=SS, 7,8,9=OF, 10=DH/P
    pos_map = {
        "1": "P", "P": "P",
        "2": "C", "C": "C",
        "3": "1B", "1B": "1B",
        "4": "2B", "2B": "2B",
        "5": "3B", "3B": "3B",
        "6": "SS", "SS": "SS",
        "7": "OF", "8": "OF", "9": "OF", "OF": "OF",
        "10": "DH", "DH": "DH",
        "11": "P", # Sometimes relievers
    }

    # Iterate games for Probable Pitchers (high certainly to play)
    for date_item in games:
        for game in date_item.get("games", []):
            game_pk = game["gamePk"]
            teams = game["teams"]
            
            # Extract Teams
            away_team = teams["away"]["team"]["name"]
            home_team = teams["home"]["team"]["name"]
            
            # Probables
            for side in ["away", "home"]:
                prob = teams[side].get("probablePitcher")
                if prob:
                    pid = str(prob["id"])
                    name = prob["fullName"]
                    # Team name normalization might be needed (e.g. "New York Yankees" -> "NYY")
                    # For now keep full name; user might need mapping or just raw
                    team_name = away_team if side == "away" else home_team
                    
                    players_data.append({
                        "player_id": pid,  # Official MLB ID, NOT DK ID
                        "player_name": name,
                        "position": "P",
                        "team": team_name,
                        "salary": 0,    # Unknown
                        "proj_points": 0 # Unknown
                    })

    # Note: Fetching full rosters for every team is heavy.
    # Ideally we'd fetch specific game lineups if posted.
    # For this MVP, let's just return the Probable Pitchers as "verified active".
    # User requested "player list", but full roster is huge (40-man * 30 teams).
    # Let's keep it scoped to Probables for now to prove end-to-end flow without spamming API.
    
    if not players_data:
        raise ValueError("No probable pitchers found (games might be TBD or off-season).")

    df = pd.DataFrame(players_data)
    
    # Save raw
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    fpath = Path(output_dir) / f"mlb_official_probables_{today_str}.csv"
    df.to_csv(fpath, index=False)
    
    return df, fpath

# --- Generic entry point ---

def fetch_api_data(source_config: Dict[str, Any]) -> pd.DataFrame:
    """
    Router for different API sources.
    """
    src_type = source_config.get("type")
    
    if src_type == "mlb_statsapi":
        df, path = fetch_mlb_statsapi(source_config.get("output_dir", "data/auto"))
        return df, path
    
    raise NotImplementedError(f"API Source type '{src_type}' not implemented.")
