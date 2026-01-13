import pandas as pd, os

SRC = r"data/processed/players_with_proj.csv"
DST = r"data/processed/players_with_proj_norm.csv"

if not os.path.exists(SRC):
    raise SystemExit(f"not found: {SRC}")

df = pd.read_csv(SRC, encoding="utf-8-sig")
df.columns = [str(c).strip() for c in df.columns]

# 列名候補
id_cands   = ["player_id","id","pid","PID"]
proj_cands = ["expected_points","proj","projection","fp","points","fpts","proj_fp"]
sal_cands  = ["salary","SAL","sal"]

id_col   = next((c for c in id_cands   if c in df.columns), None)
proj_col = next((c for c in proj_cands if c in df.columns), None)
sal_col  = next((c for c in sal_cands  if c in df.columns), None)

if not id_col:
    raise SystemExit(f"id列が見つかりません。columns={df.columns.tolist()}")

cols = [id_col]
rename = {id_col: "player_id"}

if proj_col:
    cols.append(proj_col); rename[proj_col] = "expected_points"
if sal_col:
    cols.append(sal_col); rename[sal_col] = "salary"

out = df[cols].rename(columns=rename).copy()

# 型整形
out["player_id"] = pd.to_numeric(out["player_id"], errors="coerce")
if "expected_points" in out.columns:
    out["expected_points"] = pd.to_numeric(out["expected_points"], errors="coerce").fillna(0.0)
else:
    out["expected_points"] = 0.0

if "salary" in out.columns:
    out["salary"] = pd.to_numeric(out["salary"], errors="coerce").fillna(0)
# なければ列は作らない（スクリプトが必須なら 0 を入れても可）

out = out.dropna(subset=["player_id"]).astype({"player_id":"int64"})
out.to_csv(DST, index=False, encoding="utf-8")

print("wrote", DST, "rows=", len(out))
print(out.head().to_string(index=False))
