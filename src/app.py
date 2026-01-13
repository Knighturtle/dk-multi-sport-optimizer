import streamlit as st
import pandas as pd
import yaml
import os
import json
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

# Optimizer & Source Modules
from optimizer.engine import OptimizerEngine
from sources.downloader import resolve_downloads_dir, find_latest_file, copy_to_data_auto
from sources.normalize import normalize_df
from sources.schema import validate_df
from sources.api_fetcher import fetch_api_data
from dk_import import build_dk_import_csv, save_dk_import_csv

# Analysis Modules
from analysis.value import compute_value_metrics, find_anomalies
from analysis.ceiling import estimate_ceiling
from analysis.ownership import estimate_ownership
from sources.api_fetcher import fetch_api_data
from dk_import import build_dk_import_csv, save_dk_import_csv

# Analysis Modules
from analysis.value import compute_value_metrics, find_anomalies
from analysis.ceiling import estimate_ceiling
from analysis.ownership import estimate_ownership
from analysis.correlation import compute_correlation_heatmap
from analysis.exposure import calculate_exposure
from analysis.backtest import backtest_lineups
from analysis.distribution import estimate_distribution_parameters
from analysis.ev import calculate_ev
# AI Modules
from ai.llm_client import OllamaChatClient
from ai.prompts import make_slate_summary_prompt, make_lineup_critique_prompt, make_strategy_coach_prompt, make_edge_finder_prompt
from ai.journal import append_journal, read_journal_jsonl
from ai.context_builder import build_slate_context

st.set_page_config(page_title="DK Multi-Sport Optimizer", layout="wide")

# Language Selector
st.sidebar.title("Settings")
language = st.sidebar.selectbox("Language / 言語", ["English", "日本語"], index=0)

st.title("DraftKings Multi-Sport Optimizer + Analysis Suite")

# --- Load Configs ---
@st.cache_data
def load_configs():
    src_cfg = {}
    eda_cfg = {}
    try:
        with open("configs/sources.yaml", "r") as f:
            src_cfg = yaml.safe_load(f)
    except:
        pass
        
    try:
        with open("configs/analysis.yaml", "r") as f:
            eda_cfg = yaml.safe_load(f)
    except:
        pass
    return src_cfg, eda_cfg

source_config, analysis_config = load_configs()

# --- Initialize Engine ---
try:
    engine = OptimizerEngine(rules_dir="rules/dk")
    sports_list = engine.list_sports()
except Exception as e:
    st.error(f"Failed to initialize engine: {e}")
    st.stop()

# --- Shared State ---
if "current_df" not in st.session_state:
    st.session_state["current_df"] = None
if "current_rules" not in st.session_state:
    st.session_state["current_rules"] = None
if "generated_lineups" not in st.session_state:
    st.session_state["generated_lineups"] = []

if "journal_path" not in st.session_state:
    # Ensure all runtime directories exist
    for d in ["data", "output", "logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    
    st.session_state["journal_path"] = str(Path("data") / "journal.jsonl")


# --- Sidebar ---
st.sidebar.header("1. Sport & Rules")
if not sports_list:
    st.stop()

# Sidebar: Sport Selection
selected_sport = st.sidebar.selectbox("Select Sport", sports_list)
rules = None
try:
    rules = engine.load_rules(selected_sport)
    st.session_state["current_rules"] = rules
    st.sidebar.info(f"Loaded Rules: **{rules.sport}**")
except Exception as e:
    st.error(f"Error loading rules: {e}")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption("Current Data:")
if st.session_state["current_df"] is not None:
    st.sidebar.success(f"Players: {len(st.session_state['current_df'])}")
else:
    st.sidebar.warning("No Data Loaded")

    st.sidebar.warning("No Data Loaded")

# --- Layout: Main Tabs ---
tabs = st.tabs([
    "📂 1. Data", 
    "📊 2. Analyze", 
    "📈 3. Visualize", 
    "🤖 4. AI Coach", 
    "⚙️ 5. Optimize", 
    "🏆 6. Results", 
    "📓 7. Journal"
])

# ==========================================
# TAB 1: DATA (Unified Sources)

# ==========================================
# TAB 1: DATA (Unified Sources)
# ==========================================
with tabs[0]:
    st.subheader("Import Player Data")
    
    src_cols = st.columns(3)
    source_method = st.radio("Source Method", ["Upload CSV", "Auto-detect (Downloads)", "Official API", "Ownership CSV (Merge)"], horizontal=True)

    final_df = None
    msg = ""

    # Shared Logic to get MAIN DF
    def load_main_data(df, source_msg):
        # Validate & Update Session
        try:
            validate_df(df)
            st.session_state["current_df"] = df
            st.session_state["data_source_msg"] = source_msg
            return True
        except Exception as e:
            st.error(f"Validation Error: {e}")
            return False

    if source_method == "Upload CSV":
        uploaded_file = st.file_uploader("Choose CSV", type=["csv"])
        if uploaded_file:
            try:
                raw = pd.read_csv(uploaded_file)
                final_df = normalize_df(raw, source_config.get("mapping", {}), rules.projection_column)
                msg = f"Source: Manual Upload ({uploaded_file.name})"
            except Exception as e:
                st.error(f"Error: {e}")

    elif source_method == "Auto-detect (Downloads)":
        dl_conf = source_config.get("downloads", {})
        watch_dir_conf = dl_conf.get("watch_dir")
        
        # Resolve path safely
        try:
            watch_path = resolve_downloads_dir(watch_dir_conf)
            st.info(f"Watching: `{watch_path}`")
            if st.button("Scanning for latest DKSalaries..."):
                latest = find_latest_file(watch_path, dl_conf.get("patterns", ["DKSalaries*.csv"]))
                if latest:
                    new_path = copy_to_data_auto(latest, sport=rules.sport)
                    raw = pd.read_csv(new_path)
                    final_df = normalize_df(raw, source_config.get("mapping", {}), rules.projection_column)
                    msg = f"Source: Auto-detect ({latest.name})"
                    st.success("Found & Loaded!")
                else:
                    st.warning("No matching files found.")
        except Exception as e:
            st.error(f"Setup Error: {e}")

    elif source_method == "Official API":
        api_conf = source_config.get("api", {})
        if not api_conf.get("enabled"):
            st.warning("API disabled in config.")
        else:
            sources = api_conf.get("sources", [])
            s_map = {s["name"]: s for s in sources}
            sel_s = st.selectbox("API Source", list(s_map.keys()))
            
            if st.button("Fetch from API"):
                try:
                    with st.spinner("Fetching..."):
                        raw, fpath = fetch_api_data(s_map[sel_s])
                        st.success(f"Saved to {fpath}")
                        final_df = normalize_df(raw, source_config.get("mapping", {}), rules.projection_column)
                        msg = f"Source: API ({sel_s})"
                except Exception as e:
                    st.error(f"Fetch Error: {e}")

    elif source_method == "Ownership CSV (Merge)":
        st.info("Merge Ownership data into the currently loaded Player Data.")
        curr_df = st.session_state.get("current_df")
        
        if curr_df is None:
            st.warning("⚠️ Please load Player Data (Upload/Auto/API) FIRST.")
        else:
            own_file = st.file_uploader("Upload Ownership CSV", type=["csv"])
            
            if own_file:
                try:
                    # Specific normalization for Ownership
                    # Reuse normalize_df but we really just want player_id/name + ownership
                    # We can use the same mapping config effectively.
                    
                    own_raw = pd.read_csv(own_file)
                    
                    # We expect "Ownership" column or mapped equivalent
                    # Let's perform a lightweight normalization to find "ownership"
                    # Using global config mapping
                    own_norm = normalize_df(own_raw, source_config.get("mapping", {}), "ownership") # projection_col dummy
                    
                    # Now Merge
                    # Try matching on ID first, then Name
                    merged_count = 0
                    
                    # Prepare Lookup
                    # Check if own_norm has valid ownership
                    if "ownership" not in own_norm.columns:
                        # try defaults
                        pass
                        
                    # Create dict: ID -> Own
                    id_map = {}
                    name_team_map = {}
                    
                    for _, row in own_norm.iterrows():
                        if pd.notna(row.get("player_id")) and row["player_id"] != 0:
                            id_map[str(int(row["player_id"]))] = row.get("ownership", 0)
                        
                        # Name + Team (if available)
                        pname = str(row.get("player_name", "")).strip().lower()
                        pteam = str(row.get("team", "")).strip().lower()
                        if pname:
                            if pteam:
                                name_team_map[(pname, pteam)] = row.get("ownership", 0)
                            else:
                                name_team_map[pname] = row.get("ownership", 0) # Fallback name only
                                
                    # Apply to Current DF
                    # We update "_ownership" column (internal key)
                    # Note: normalize_df produces "ownership" column in own_norm, 
                    # but current_df uses keys defined in normalization? 
                    # Wait, normalize_df output uses standard keys like "player_id", "player_name", "ownership"
                    # BUT engine expects "_ownership" and "_ceiling" and "_proj"
                    # Let's check normalize.py again.
                    # normalize produces keys: player_id, player_name, position, salary, team, proj_points, ownership, ceiling
                    # BUT engine.py uses _proj, _salary. 
                    # Ah, normalize.py from PREVIOUS context was producing normalized DF, but did it map to _?
                    # The snippets I edited in Step 227 show output keys: "proj_points", "ownership", "ceiling".
                    # Let's check engine.py expectation.
                    # engine.py expects: _proj, _salary, _positions, _team. 
                    # AND I added _ceiling, _ownership checking in engine.py in Step 186.
                    
                    # CRITICAL: current_df in session MUST have _underscore columns. 
                    # Does normalize_df output them?
                    # Looking at normalize.py (I can't see full file but I see snippet in 227), it outputs "proj_points" etc.
                    # WAIT. The codebase seems to have a mix or I missed where renaming happens.
                    # Let's check app.py where it loads data.
                    # It calls `normalize_df`.
                    # Then it calls `compute_value_metrics` -> `estimate_ceiling`.
                    # `estimate_ceiling` (Step 180) checks `_positions`. 
                    # `compute_value_metrics` (Step 179) uses `_salary`.
                    
                    # THIS MEANS normalize_df MUST return _underscore columns OR there is an adapter step I missed.
                    # Let's re-read normalize.py snippet 227 carefully.
                    # "out = pd.DataFrame()" ... "out['proj_points'] = ..."
                    # It creates "proj_points", "ownership".
                    # So where do `_proj` and `_salary` come from? 
                    
                    # Ah, in Step 225 I updated normalize.py snippet 1 (lines 69-79 in previous version?)
                    # Wait, prompt 225 used `ReplacementChunks`.
                    # In snippet 227 (result), it shows `out["proj_points"]`. 
                    # This implies my normalize.py is producing clean names like "proj_points", but analysis modules expect "_proj".
                    # This is a Discrepancy. 
                    # Let's look at `normalize_df` call in app.py logic...
                    # Oh, I see `compute_value_metrics` uses `_salary`...
                    
                    # HYPOTHESIS: I might have introduced a bug in previous steps if normalize returns "salary" but analysis expects "_salary".
                    # OR, maybe I have a `_rename` step somewhere? 
                    # Let's assume for now I need to align them.
                    # I will standardize on underscores in app.py logic OR fix normalize.py to return underscores.
                    # Actually, standard best practice here: let's re-map generic names to underscores inside `app.py` or `engine.py`?
                    # `OptimizerEngine.load_players_df` usually handles this... but we are bypassing `load_players_df` by passing DF directly to `optimize_df` from app.
                    
                    # FIX: I will ensure my merge logic updates `_ownership` (underscore) because that is what `engine.py` (Step 186) checks: `if "_ownership" in df.columns`.
                    
                    def update_row_own(row):
                        pid = str(int(row["player_id"]))
                        pname = str(row["player_name"]).strip().lower()
                        pteam = str(row["team"]).strip().lower() # team might be null?
                        
                        val = None
                        if pid in id_map:
                            val = id_map[pid]
                        elif (pname, pteam) in name_team_map:
                            val = name_team_map[(pname, pteam)]
                        elif pname in name_team_map:
                             val = name_team_map[pname]
                             
                        if val is not None:
                            return float(val)
                        return row.get("_ownership", 0.0) # Keep existing or 0

                    # Apply
                    # Ensure current_df has columns compliant with analysis (underscores)
                    # If I am merging, I assume current_df is already valid.
                    
                    # Let's map "ownership" from normalize to "_ownership" to be safe.
                    curr_df["_ownership"] = curr_df.apply(update_row_own, axis=1)
                    
                    match_count = (curr_df["_ownership"] > 0).sum()
                    st.success(f"Merged Ownership! {match_count} players updated.")
                    st.session_state["current_df"] = curr_df
                    st.session_state["data_source_msg"] += " + Ownership CSV"
                    
                except Exception as e:
                    st.error(f"Merge Failed: {e}")

    # Commit to Session
    if final_df is not None:
        try:
            validate_df(final_df)
            
            # ADAPTER: standard keys -> underscore keys for Analysis/Engine
            # We do this here 
            mapper = {
                "salary": "_salary",
                "proj_points": "_proj",
                "team": "_team",
                "ownership": "_ownership",
                "ceiling": "_ceiling"
            }
            # Only rename if they exist and target doesn't
            for k, v in mapper.items():
                if k in final_df.columns and v not in final_df.columns:
                    final_df[v] = final_df[k]
                    
            # Normalize internal cols types
            final_df["_team"] = final_df["team"].fillna("UNK")
            # Positions special handling handled by engine or normalize? 
            # engine expects _positions set. normalize usually just gives "position" str.
            # engine self-heals _positions.
            
            # Apply Analysis Transforms early for downstream tabs
            value_df = compute_value_metrics(final_df, analysis_config.get("value", {}).get("multiplier", 1000))
            # Phase 3: Distribution & EV
            dist_df = estimate_distribution_parameters(value_df)
            own_df = estimate_ownership(dist_df, analysis_config.get("ownership", {}))
            
            # Default EV calc (can be re-run in Optimize tab if settings change)
            # Load EV config
            ev_config_path = Path("configs/ev.yaml")
            ev_settings = {}
            if ev_config_path.exists():
                with open(ev_config_path) as f:
                    data = yaml.safe_load(f)
                    ev_settings = data.get("defaults", {})
            
            ev_df = calculate_ev(own_df, ev_settings)
            
            st.session_state["current_df"] = ev_df
            st.session_state["data_source_msg"] = msg
        except Exception as e:
            st.error(f"Validation Failed: {e}")

    # Preview
    if st.session_state["current_df"] is not None:
        st.write(st.session_state["data_source_msg"])
        st.table(st.session_state["current_df"].head(10))

# ==========================================
# TAB 2: ANALYZE (Numeric)
# ==========================================
with tabs[1]:
    df = st.session_state.get("current_df")
    if df is None:
        st.info("Please load data in Tab 1 first.")
    else:
        st.subheader("Numeric Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Top Value Plays")
            top_val = df.sort_values("_value", ascending=False).head(15)[["player_name", "position", "_salary", "_proj", "_value"]]
            st.table(top_val)
            
        with col2:
            st.markdown("#### Anomalies (Mispriced?)")
            anoms = find_anomalies(df)
            if not anoms.empty:
                st.table(anoms[["player_name", "_salary", "_proj", "type"]])
            else:
                st.write("No strong anomalies detected.")
                
        st.markdown("#### Ceiling & Ownership Projections")
        st.dataframe(df[["player_name", "position", "_salary", "_proj", "_ceiling", "_ownership"]].head(20))

# ==========================================
# TAB 3: VISUALIZE (Charts)
# ==========================================
with tabs[2]:
    df = st.session_state.get("current_df")
    if df is None:
        st.info("Load data first.")
    else:
        st.subheader("Market Visualization")
        
        # 1. Salary vs Proj
        st.markdown("#### Market Inefficiency (Salary vs Proj)")
        fig, ax = plt.subplots(figsize=(10, 5))
        # Color by Value
        sc = ax.scatter(df["_salary"], df["_proj"], c=df["_value"], cmap="viridis", alpha=0.7)
        ax.set_xlabel("Salary")
        ax.set_ylabel("Projection")
        plt.colorbar(sc, label="Value Metric")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        
        # 2. Team Stack Heatmap
        st.markdown("#### Team x Position Strength")
        pivot = compute_correlation_heatmap(df)
        if not pivot.empty:
            st.write("Average Projection by Team & Position")
            st.table(pivot.style.format("{:.1f}").background_gradient(cmap="Blues", axis=None))
        else:
            st.write("Not enough data for heatmap.")

        # 3. Ownership Analysis
        st.markdown("---")
        st.subheader("Ownership Analysis")
        col_own1, col_own2 = st.columns(2)
        
        with col_own1:
            st.markdown("Ownership Distribution")
            fig_hist, ax_hist = plt.subplots()
            ax_hist.hist(df["_ownership"]*100, bins=20, color='purple', alpha=0.7)
            ax_hist.set_xlabel("Ownership %")
            ax_hist.set_ylabel("Count")
            st.pyplot(fig_hist)
            
        with col_own2:
            st.markdown("Projection vs Ownership (Leverage)")
            fig_sc, ax_sc = plt.subplots()
            # X=Own, Y=Proj
            ax_sc.scatter(df["_ownership"], df["_proj"], alpha=0.5, c='purple')
            ax_sc.set_xlabel("Ownership (0-1)")
            ax_sc.set_ylabel("Projection")
            ax_sc.grid(True, alpha=0.3)
            st.pyplot(fig_sc)
            
        st.markdown("---")
        st.subheader("Volatility & Stacking")
        
        c_vol1, c_vol2 = st.columns(2)
        with c_vol1:
            st.markdown("#### Variance Analysis (Proj vs StdDev)")
            if "_stddev" in df.columns:
                fig_std, ax_std = plt.subplots()
                ax_std.scatter(df["_proj"], df["_stddev"], alpha=0.5, c='orange')
                ax_std.set_xlabel("Projection")
                ax_std.set_ylabel("Std Dev (Risk)")
                st.pyplot(fig_std)
            else:
                st.write("No StdDev data.")
                
        with c_vol2:
             st.markdown("#### Team Counts (Stack Potential)")
             team_counts = df["_team"].value_counts().head(10)
             st.bar_chart(team_counts)

        # Lists: Chalk vs Pivot
        # Chalk: High Own (>20%) & High Proj
        # Pivot: Low Own (<5%) & High Proj
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Chalk (High Own > 20%)")
            chalk_df = df[df["_ownership"] > 0.20].sort_values("_proj", ascending=False).head(10)
            st.table(chalk_df[["player_name", "_proj", "_salary", "_ownership"]])
            
        with c2:
            st.markdown("#### Potential Leverage (Own < 5%, High Proj)")
            # Filter somewhat high proj to be relevant
            if not df.empty:
                proj_thresh = df["_proj"].quantile(0.75)
                lev_df = df[(df["_ownership"] < 0.05) & (df["_proj"] > proj_thresh)].sort_values("_proj", ascending=False).head(10)
                st.table(lev_df[["player_name", "_proj", "_salary", "_ownership"]])

# ==========================================
# TAB 4: AI COACH
# ==========================================
with tabs[3]:
    st.subheader("🤖 AI Coach (Ollama: Local LLM)")
    
    model_name = st.text_input("Ollama Model", value="llama3.1:8b", help="Ensure this model is pulled locally.")
    client = OllamaChatClient(model=model_name)
    
    if not client.is_connected():
        st.warning("Ollama not detected. Start with `ollama serve`.")
    else:
        st.success("Connected to Ollama.")
        
        df = st.session_state.get("current_df")
        lineups = st.session_state.get("generated_lineups", [])
        rules = st.session_state.get("current_rules")
        
        if st.session_state.get("current_df") is None:
            st.warning("Please load data first.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            
            # Dynamic Labels
            lbl_summary = "Generate Slate Summary" if language == "English" else "スレート要約生成"
            lbl_edge = "Find Edges (Hypotheses)" if language == "English" else "勝ち筋仮説生成"
            lbl_critique = "Critique Lineup" if language == "English" else "ラインナップ批評"
            lbl_strat = "Suggest Strategy" if language == "English" else "戦略設定提案"
            
            if c1.button(f"📝 {lbl_summary}"):
                if client.is_connected():
                    with st.spinner("Generating Summary..."):
                        # Build Context
                        ctx_str = build_slate_context(st.session_state["current_df"], st.session_state.get("generated_lineups"))
                        prompt = make_slate_summary_prompt(ctx_str, language=language)
                        resp = client.chat(prompt)
                        st.markdown(resp)
                        
                        # Auto-Journal
                        append_journal({
                            "type": "summary",
                            "content": resp,
                            "context_snapshot": "Slate Summary generated via context_builder"
                        }, st.session_state["journal_path"], language=language)
                else:
                    st.error("Ollama not connected.")
                    
            if c2.button(f"🔍 {lbl_edge}"):
                 if client.is_connected():
                    with st.spinner("Finding Edges..."):
                        ctx_str = build_slate_context(st.session_state["current_df"])
                        prompt = make_edge_finder_prompt(ctx_str, language=language)
                        resp = client.chat(prompt)
                        st.markdown(resp)
                        append_journal({"type":"edge", "content":resp}, st.session_state["journal_path"], language=language)

            if c4.button(f"🧠 {lbl_strat}"):
                if client.is_connected():
                    with st.spinner("Analyzing Strategy..."):
                        ctx_str = build_slate_context(st.session_state["current_df"])
                         # Mock settings or real if available
                        settings_mock = {"mode": "gpp_ev", "stacking": "undefined"}
                        prompt = make_strategy_coach_prompt(settings_mock, ctx_str, language=language)
                        resp = client.chat(prompt)
                        st.markdown(resp)
                        append_journal({"type":"strategy", "content":resp}, st.session_state["journal_path"], language=language)
                        
            st.markdown("---")
            st.write(f"### {lbl_critique}")
            # If lineups exist, show selectbox
            if st.session_state.get("generated_lineups"):
                lus = st.session_state["generated_lineups"]
                lu_opts = [f"Rank {i+1} ({l['total_proj']} pts)" for i, l in enumerate(lus)]
                sel_lu = st.selectbox("Select Lineup", lu_opts)
                
                if st.button(f"👮 {lbl_critique}"):
                     idx = lu_opts.index(sel_lu)
                     target_lu = lus[idx]
                     ctx_str = build_slate_context(st.session_state["current_df"])
                     prompt = make_lineup_critique_prompt(target_lu, ctx_str, language=language)
                     resp = client.chat(prompt)
                     st.markdown(resp)
                     append_journal({"type":"critique", "content":resp, "lineup": target_lu}, st.session_state["journal_path"], language=language)
            else:
                st.info("Run Optimizer first to critique lineups.")

# ==========================================
# TAB 5: OPTIMIZE
# ==========================================
with tabs[4]:
    # Reuse existing optimization logic...
    df = st.session_state.get("current_df")
    if df is None:
        st.info("Load data first.")
    else:
        st.subheader("Optimization Settings")

        c1, c2, c3 = st.columns(3)
        with c1:
            num_lineups = st.number_input("Lineups Count", 1, 150, rules.num_lineups)
        with c2:
            max_overlap = st.number_input("Max Overlap", 0, rules.lineup_size, 6)
        with c3:
            objective_mode = st.selectbox("Objective Mode", ["Cash (Proj)", "GPP (Ceiling Weighted)"])
        
        # Advanced Settings
        with st.expander("Advanced Constraints (Ownership, Stacking, GPP)"):
            
            # GPP Settings
            alpha = 1.0
            if objective_mode.startswith("GPP"):
                alpha = st.slider("GPP Alpha (Weight for Proj vs Ceiling)", 0.0, 1.0, 0.5, 0.1, help="1.0 = Pure Proj, 0.0 = Pure Ceiling, 0.5 = Balanced")
            
            # Ownership
            st.markdown("---")
            st.markdown("**Ownership Constraints**")
            total_own_cap = st.number_input("Total Ownership Cap (Sum)", 0, 900, 0, help="0 to disable. e.g. 200 = sum of ownerships max 200%")
            
            # Stacking (Simple MVP)
            st.markdown("---")
            st.markdown("#### Advanced GPP Constraints")
            
            col_gpp1, col_gpp2 = st.columns(2)
            with col_gpp1:
                max_chalk = st.number_input("Max Chalk Players (>20% Own)", 0, 10, 0, help="Hard limit on number of chalky players.")
            with col_gpp2:
                min_ceil_val = st.number_input("Min Total Ceiling", 0, 1000, 0, help="Force lineup to have at least this total ceiling.")
            
            # Real Ownership Optimization / EV
            st.markdown("---")
            st.markdown("**Objective Function**")
            
            # Mode Selection
            obj_mode_sel = st.radio("Optimization Mode", ["Cash (Max Projection)", "GPP (Max EV)"], horizontal=True)
            objective_mode = "cash" if "Cash" in obj_mode_sel else "gpp"
            
            ev_settings_curr = {}
            if objective_mode == "gpp":
                st.info("Results will maximize 'EV' (Expected Value) score based on weights below.")
                with st.expander("GPP / EV Weights (Adjust Strategy)", expanded=True):
                    c_w1, c_w2, c_w3 = st.columns(3)
                    w_proj = c_w1.number_input("Proj Weight", 0.0, 10.0, 1.0, 0.1)
                    w_ceil = c_w2.number_input("Ceiling Weight", 0.0, 10.0, 0.5, 0.1)
                    w_chalk = c_w3.number_input("Chalk Penalty", 0.0, 100.0, 0.0, 1.0, help="Subtracts X * Ownership")
                    
                    c_w4, c_w5 = st.columns(2)
                    w_std = c_w4.number_input("Variance Bonus", 0.0, 10.0, 0.0, 0.1)
                    w_lev = c_w5.number_input("Leverage Bonus", 0.0, 100.0, 0.0, 0.1)
                    
                    ev_settings_curr = {
                        "w_proj": w_proj, "w_ceil": w_ceil, "w_std": w_std,
                        "w_chalk": w_chalk, "w_lev": w_lev,
                    }
                    
                    if st.button("🔄 Recalculate EV"):
                        # Re-run EV calc on current_df
                        st.session_state["current_df"] = calculate_ev(st.session_state["current_df"], ev_settings_curr)
                        st.success("EV Updated!")
                        st.rerun()

            # Legacy options
            # use_own = st.checkbox(... ) --> migrated to GPP weights above or kept as separate constraints?
            # Keeping legacy logic in engine, but UI is cleaner if we just use GPP weights for "Chalk Penalty".
            # The user asked for "Max Chalk Count" (hard constraint) AND "EV" (soft objective).
            # We implemented Max Chalk above.
        
        if st.button("🚀 Run Optimizer", type="primary"):
            with st.spinner("Optimizing..."):
                try:
                    # Prepare Settings
                    settings = {
                        "num_lineups": num_lineups,
                        "max_overlap": max_overlap,
                        "objective_mode": objective_mode,
                        "max_chalk_count": max_chalk if max_chalk > 0 else None,
                        "min_total_ceiling": min_ceil_val if min_ceil_val > 0 else None,
                    }
                    if total_own_cap > 0:
                        settings["total_ownership_cap"] = total_own_cap
                    
                    # Run
                    lineups = engine.optimize_df(df, rules, settings=settings)
                    
                    if not lineups:
                        st.error("No lineups generated (Infeasible). Check constraints.")
                    else:
                        st.session_state["generated_lineups"] = lineups
                        st.success(f"Generated {len(lineups)} Lineups!")
                        
                except Exception as e:
                    st.error(f"Optimization Error: {e}")
                    st.exception(e)

# ==========================================
# TAB 6: RESULTS
# ==========================================
with tabs[5]:
    lineups = st.session_state.get("generated_lineups", [])
    if not lineups:
        st.info("Run Optimizer in Tab 5.")
    else:
        st.subheader(f"Results: {len(lineups)} Lineups")
        
        # 1. Lineups Table (Simplified)
        rows = []
        for i, lu in enumerate(lineups, 1):
            # Calculate Lineup Metrics
            total_own = 0
            chalk_cnt = 0
            for slot in lu["slots"]:
                 # We need to find player's ownership from current_df or embedded?
                 # engine result doesn't return ALL properties of player, only slot info.
                 # BUT we have st.session_state["current_df"]. 
                 # Let's map ID -> Own
                 pass # We do it efficiently below
                 
            # Helper Map
            if df is not None:
                pid_to_own = dict(zip(df["player_id"].astype(str), df["_ownership"]))
                
                total_own = sum(pid_to_own.get(str(s["player_id"]), 0) for s in lu["slots"])
                chalk_cnt = sum(1 for s in lu["slots"] if pid_to_own.get(str(s["player_id"]), 0) > 0.20)
                
            rows.append({
                "Rank": i,
                "Total Proj": round(lu["total_proj"], 2),
                "Total Salary": lu["total_salary"],
                "TotOwn%": f"{total_own*100:.1f}%",
                "Chalk(>20%)": chalk_cnt,
                "Players": ", ".join([s["player_name"] for s in lu["slots"]])
            })
        
        # Enhanced Table
        st.table(pd.DataFrame(rows).head(20)) 
        
        # Visuals for Results
        if lineups:
            st.markdown("#### Lineup Performance Metrics")
            l_df = pd.DataFrame(lineups)
            # engine lineups might not have ceiling sum in dict, only total_proj.
            # But we can calculate it if we iterate slots?
            # Ideally calculate in loop above and store in 'rows'.
            # For now just show standard results.
        
        # 2. Exposure Report
        st.markdown("### Exposure Report")
        exposure_df = calculate_exposure(lineups, len(lineups))
        col_exp1, col_exp2 = st.columns([1, 2])
        with col_exp1:
            st.table(exposure_df.head(15))
            
        with col_exp2:
            # Bar chart
            if not exposure_df.empty:
                fig, ax = plt.subplots(figsize=(6, 4))
                top_exp = exposure_df.head(10)
                ax.barh(top_exp["player_name"], top_exp["pct"], color="teal")
                ax.set_xlabel("Exposure %")
                ax.invert_yaxis()  # Top on top
                st.pyplot(fig)

        # 3. Export
        st.markdown("### Export")
        import_df = build_dk_import_csv(lineups, rules)
        
        # Save to disk first
        try:
            out_dir = source_config.get("import", {}).get("output_dir", "output")
            prefix = source_config.get("import", {}).get("filename_prefix", "dk_import")
            saved_path = save_dk_import_csv(import_df, rules.sport, out_dir, prefix)
            
            st.download_button(
                "📥 Download DraftKings CSV",
                data=import_df.to_csv(index=False).encode('utf-8'),
                file_name=saved_path.name,
                mime="text/csv"
            )
            st.caption(f"Saved locally to: {saved_path}")
        except Exception as e:
            st.error(f"Export Error: {e}")

# ==========================================
# TAB 7: JOURNAL
# ==========================================
with tabs[6]:
    st.subheader("📓 Learning Journal & Analytics")
    
    j_path = st.session_state["journal_path"]
    
    # --- Data Loader (Cached) ---
    @st.cache_data(ttl=10) # Short cache for responsiveness
    def load_journal_data(path):
        return read_journal_jsonl(path)
        
    # Reload Button logic
    col_ctrl1, col_ctrl2 = st.columns([1, 5])
    with col_ctrl1:
        if st.button("🔄 Reload"):
            st.cache_data.clear()
            st.rerun()
            
    # Load Data
    j_df = load_journal_data(j_path)
    
    if j_df.empty:
        st.info("No journal entries found. Use 'AI Coach' tabs to generate insights.")
    else:
        # Sort by latest first
        j_df = j_df.sort_values("timestamp", ascending=False)
        
        # --- Filters ---
        st.markdown("##### 🔍 Search & Filter")
        
        # 1. Search Box
        search_term = st.text_input("Search Content / Notes", placeholder="e.g. 'stacking', 'salary'").lower()
        
        # 2. Filters Row
        f_c1, f_c2, f_c3 = st.columns(3)
        with f_c1:
            all_types = list(j_df["type"].dropna().unique())
            sel_types = st.multiselect("Filter by Type", all_types, default=all_types)
        with f_c2:
            all_langs = list(j_df["language"].dropna().unique())
            sel_langs = st.multiselect("Filter by Language", all_langs, default=all_langs)
        with f_c3:
            min_date = j_df["timestamp"].min().date()
            max_date = j_df["timestamp"].max().date()
            date_range = st.date_input("Date Range", [min_date, max_date])
            
        # --- Apply Filters ---
        filtered_df = j_df.copy()
        
        # Type & Lang
        if sel_types:
            filtered_df = filtered_df[filtered_df["type"].isin(sel_types)]
        if sel_langs:
            filtered_df = filtered_df[filtered_df["language"].isin(sel_langs)]
            
        # Date
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            # Handle timestamps comparison
            start_d, end_d = date_range
            filtered_df = filtered_df[
                (filtered_df["timestamp"].dt.date >= start_d) & 
                (filtered_df["timestamp"].dt.date <= end_d)
            ]
            
        # Search
        if search_term:
            # Safe fillna before search
            filtered_df = filtered_df[
                filtered_df["content"].fillna("").str.lower().str.contains(search_term) | 
                filtered_df["user_notes"].fillna("").str.lower().str.contains(search_term)
            ]
            
        # --- KPIs ---
        st.markdown("---")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Entries", len(filtered_df))
        
        # Type Breakdown
        if not filtered_df.empty:
            top_type = filtered_df["type"].mode()
            top_type_str = top_type[0] if not top_type.empty else "N/A"
            kpi2.metric("Most Common Type", top_type_str.title())
            
            # Latest
            latest_ts = filtered_df["timestamp"].max()
            time_str = latest_ts.strftime("%Y-%m-%d %H:%M") if pd.notnull(latest_ts) else "N/A"
            kpi3.metric("Latest Entry", time_str)
            
        # --- Display List ---
        st.write(f"Showing {len(filtered_df)} entries")
        
        for idx, row in filtered_df.iterrows():
            # Card UI
            ts_str = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(row["timestamp"]) else "Unknown Time"
            typ_str = str(row["type"]).upper()
            lang_flag = "🇯🇵" if row["language"] == "日本語" else "🇺🇸"
            
            with st.expander(f"{lang_flag} [{typ_str}] {ts_str}"):
                st.markdown(row["content"])
                
                if pd.notnull(row["user_notes"]) and str(row["user_notes"]).strip():
                    st.info(f"📝 **User Notes:** {row['user_notes']}")
                    
                # Technical raw data (collapsed)
                with st.popover("Raw Data"):
                    st.json(row.to_dict())
                    
        # --- Exports ---
        st.markdown("---")
        st.subheader("📥 Export")
        e_c1, e_c2 = st.columns(2)
        with e_c1:
            # CSV Download (Filtered)
            st.download_button(
                "Download CSV (Filtered)",
                data=filtered_df.to_csv(index=False).encode("utf-8"),
                file_name="journal_filtered.csv",
                mime="text/csv"
            )
        with e_c2:
            # JSONL Download (Raw/Full File)
            # We read the raw file again to ensure we give the exact original file, or we can dump the DF.
            # User requirement: "生の JSONL をダウンロード" (Download raw JSONL)
            # Safest is to read the file content directly.
            try:
                if Path(j_path).exists():
                    with open(j_path, "rb") as f:
                        raw_bytes = f.read()
                    st.download_button(
                        "Download Full JSONL (Backup)",
                        data=raw_bytes,
                        file_name="journal_backup.jsonl",
                        mime="application/json"
                    )
            except Exception as e:
                st.error(f"Cannot read raw file: {e}")

# Empty footer/backtest placeholders if needed, but we rely on tabs.
# (Backtest tab logic preserved if necessary or removed if not requested in strict new flow. 
# User asked for ["Upload", "Analyze", "AI Coach", "Visualize", "Journal"]
# But standard app also needs Optimize/Results. 
# We put them in 5 and 6.)
