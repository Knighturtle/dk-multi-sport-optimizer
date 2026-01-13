import pandas as pd
DK = pd.read_csv(r'.\data\raw\DKSalaries.csv', dtype=str, on_bad_lines='skip')
print(DK[['Name','ID','Roster Position','TeamAbbrev']].head(30).to_string(index=False))
