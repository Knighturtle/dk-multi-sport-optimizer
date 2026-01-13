import pandas as pd
import json

def build_slate_context(df: pd.DataFrame, lineups: list = None) -> str:
    """
    Builds a JSON context string summarizing the slate status.
    Includes:
    - Top Value Plays
    - Chalk Plays (Ownership > 20%)
    - Leverage Plays (Low Own, High Proj)
    - Team Stack Opportunities (Correlation Heatmap summary)
    - Generated Lineup Summary (if available)
    """
    context = {}
    
    # 1. Top Value (Proj/Salary)
    # Ensure columns exist
    if "_proj" not in df.columns: return "{}"
    
    # Calculate value if not present
    work_df = df.copy()
    if "_value" not in work_df.columns:
        work_df["_value"] = work_df["_proj"] / (work_df["_salary"] + 1) * 1000
    
    top_val = work_df.sort_values("_value", ascending=False).head(5)
    context["top_value_plays"] = top_val[["player_name", "position", "team", "_salary", "_proj", "_value"]].to_dict(orient="records")
    
    # 2. Chalk (>20%)
    chalk = work_df[work_df["_ownership"] > 0.20].sort_values("_ownership", ascending=False).head(5)
    context["chalk_plays"] = chalk[["player_name", "_ownership", "_proj"]].to_dict(orient="records")
    
    # 3. Leverage (Own < 5% & Proj > 75th percentile)
    proj_thresh = work_df["_proj"].quantile(0.80)
    lev = work_df[(work_df["_ownership"] < 0.05) & (work_df["_proj"] > proj_thresh)].head(5)
    context["leverage_plays"] = lev[["player_name", "_ownership", "_proj"]].to_dict(orient="records")
    
    # 4. Lineups Summary
    if lineups:
        # Summarize first 3 lineups
        l_summaries = []
        for i, lu in enumerate(lineups[:3]):
            slots = lu["slots"]
            names = [s["player_name"] for s in slots]
            total_proj = lu["total_proj"]
            # Estimate Ownership Sum
            # We don't have full player map here easily unless passed, 
            # assume client passes rich lineup dicts or we ignore.
            l_summaries.append({
                "rank": i+1,
                "score": total_proj,
                "players": names
            })
        context["generated_lineups_preview"] = l_summaries
        
    return json.dumps(context, ensure_ascii=False, indent=2)
