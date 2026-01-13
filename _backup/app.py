# app.py
import io
from pathlib import Path
import streamlit as st
import pandas as pd

from adapters.dk.common import load_and_normalize
from src.lineup_builder import build_many

ROOT = Path(__file__).resolve().parent
RULES_DIR = ROOT / "rules" / "dk"

SPORT_GUESS = [
    ("mlb", {"P","C","1B","2B","3B","SS","OF"}),
    ("nba", {"PG","SG","SF","PF","C"}),
    ("nfl", {"QB","RB","WR","TE","DST"}),
    ("nhl", {"C","W","D","G"}),
    ("soccer", {"GK","D","M","F"}),
]

def guess_sport_from_positions(positions: set[str]) -> str | None:
    positions_upper = {p.upper() for p in positions}
    for sport, signature in SPORT_GUESS:
        if positions_upper & signature:
            # 代表的ポジションが1つでも含まれていたら候補に
            if signature.issubset(positions_upper) or len(positions_upper & signature) >= 2:
                return sport
    return None

st.set_page_config(page_title="Lineup Builder", layout="wide")
st.title("Universal Lineup Builder (DK)")

col1, col2, col3 = st.columns(3)
site = col1.selectbox("Site", ["dk"], index=0)
sport_mode = col2.selectbox("Sport", ["auto","mlb","nba","nfl","nhl","soccer","golf","nas","mma","ten","cfl","cbb","esports_lol"])
seed = col3.number_input("Seed", min_value=1, value=1337, step=1)

uploaded = st.file_uploader("Upload DKSalaries.csv", type=["csv"])
n_lineups = st.slider("Number of lineups", 1, 150, 50, 1)
team_limit = st.number_input("Max from one team (optional; 0 = use YAML)", min_value=0, max_value=10, value=0)

rules_override = st.file_uploader("Override rules YAML (optional)", type=["yaml","yml"])
run_btn = st.button("Build lineups", type="primary", disabled=uploaded is None)

log = st.container()

def pick_rules_path(sport_key: str) -> Path:
    path = RULES_DIR / f"{sport_key}.yaml"
    if not path.exists():
        st.error(f"Rules file not found: {path}")
        st.stop()
    return path

if run_btn and uploaded is not None:
    # 1) CSV を pandas で読む（Streamlit のアップロードはメモリ上なので一度保存しなくてもOK）
    raw_df = pd.read_csv(uploaded)

    # 2) スポーツ自動判定（必要なら）
    if sport_mode == "auto":
        # Roster Position 列から全ポジション集合
        pos_col = raw_df.get("Roster Position") or raw_df.get("RosterPosition") or raw_df.get("Roster_Position")
        if pos_col is None:
            st.error("CSV に 'Roster Position' 列が見つかりません。")
            st.stop()
        all_pos = set()
        for s in pos_col.astype(str).fillna(""):
            for p in s.split("/"):
                p = p.strip().upper()
                if p:
                    all_pos.add(p)
        guessed = guess_sport_from_positions(all_pos) or "mlb"
        sport = st.session_state.setdefault("sport_selected", guessed)
        st.info(f"Detected sport: **{guessed}** （必要ならプルダウンで変更してください）")
    else:
        sport = sport_mode

    # 3) 正規化（既存アダプタを利用）
    with log:
        st.write("**[step] normalize salaries**")
    norm_df = load_and_normalize(io.StringIO(raw_df.to_csv(index=False)), sport=sport)

    # 4) ルールの決定（override があればそれを使う）
    if rules_override is not None:
        rules_path = ROOT / "_tmp_uploaded_rules.yaml"
        rules_path.write_bytes(rules_override.getbuffer())
    else:
        rules_path = pick_rules_path(sport)

    # 5) 一時CSVに書き出して build_many を呼ぶ
    data_dir = ROOT / "data" / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)
    norm_csv = data_dir / "players_normalized.csv"
    out_csv = data_dir / "submit_lineups.csv"
    norm_df.to_csv(norm_csv, index=False)

    # 6) YAML 内の世代数やチーム上限を上書きしたい場合は、簡易的に patch できる
    #    → 今回は build_many をそのまま呼び、n_lineups/limit は YAML に任せる。
    #    もし UI の値を反映したいなら、rules_path を一時コピーして yaml.safe_load / 書き戻しすればOK。

    with log:
        st.write("**[step] optimize**")
    build_many(norm_csv, rules_path, out_csv, seed=seed)

    # 7) 結果表示
    res_df = pd.read_csv(out_csv)
    st.success(f"Generated {len(res_df)} lineups")
    st.dataframe(res_df.head(20), use_container_width=True)

    st.download_button(
        label="Download submit_lineups.csv",
        data=out_csv.read_bytes(),
        file_name="submit_lineups.csv",
        mime="text/csv",
    )
