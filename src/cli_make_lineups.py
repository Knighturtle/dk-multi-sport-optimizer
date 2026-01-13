import argparse
from pathlib import Path
from adapters.dk.common import load_and_normalize
from src.lineup_builder import build_many

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, choices=["dk"])
    ap.add_argument("--sport", required=True, help="Sport key (e.g., mlb, nba, nfl, nhl, soccer, etc.)")
    ap.add_argument("--raw_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--rules_yaml", help="Override rules path (optional)")
    a = ap.parse_args()

    rules = Path(a.rules_yaml) if a.rules_yaml else (ROOT / f"rules/{a.site}/{a.sport}.yaml")
    if not rules.exists():
        raise SystemExit(f"[error] rules file not found: {rules}")

    df = load_and_normalize(Path(a.raw_csv), sport=a.sport)
    norm_csv = ROOT / "data" / "processed" / "players_normalized.csv"
    norm_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(norm_csv, index=False)

    out_csv = Path(a.out_csv); out_csv.parent.mkdir(parents=True, exist_ok=True)
    build_many(norm_csv, rules, out_csv, seed=a.seed)

if __name__ == "__main__":
    main()
