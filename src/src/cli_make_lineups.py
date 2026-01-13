import argparse
from pathlib import Path
from adapters.dk.common import load_and_normalize
from lineup_builder import build_many

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, choices=["dk"])
    ap.add_argument("--sport", required=True, choices=["nba","nfl","mlb","soccer"])
    ap.add_argument("--raw_csv", required=True)
    ap.add_argument("--out_csv", default=str(ROOT/"data/processed/submit_lineups.csv"))
    ap.add_argument("--seed", type=int, default=1337)
    a = ap.parse_args()

    raw = (ROOT / a.raw_csv).resolve()
    norm = ROOT / "data/processed/players_normalized.csv"
    rules = ROOT / f"rules/{a.site}/{a.sport}.yaml"
    out  = Path(a.out_csv)

    df = load_and_normalize(raw, sport=a.sport)
    norm.parent.mkdir(parents=True, exist_ok=True); df.to_csv(norm, index=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    build_many(norm, rules, out, seed=a.seed)

if __name__ == "__main__":
    main()
