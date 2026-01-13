from pathlib import Path
import pandas as pd

def peek(p):
    p = Path(p)
    print("\n==>", p)
    if not p.exists():
        print("NOT FOUND"); return
    try:
        df = pd.read_csv(p, nrows=2)
        print("cols:", list(df.columns))
        print(df.head(2).to_string(index=False))
    except Exception as e:
        print("READ FAIL:", type(e).__name__, e)

for f in [r".\lineups_multi.csv",
          r".\data\raw\DKSalaries.csv",
          r".\data\processed\players_today.csv"]:
    peek(f)
