import streamlit as st
import pandas as pd
import math
from pathlib import Path
from src.models.poisson_engine import PoissonPredictionEngine
from src.features.pipeline import FeaturePipeline
from src.features.squad_mapper import ExactRosterMapper

PROJECT_ROOT = Path(__file__).resolve().parent
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "blended_model_features.csv"
SQUAD_RATINGS_PATH = PROJECT_ROOT / "data" / "processed" / "exact_team_ratings.csv"


@st.cache_data(show_spinner=False)
def load_features():
    if not SQUAD_RATINGS_PATH.exists():
        eafc_path = PROJECT_ROOT / "data" / "raw" / "EAFC26-Men.csv"
        if not eafc_path.exists():
            raise FileNotFoundError(
                f"Missing `{eafc_path.relative_to(PROJECT_ROOT)}`. "
                "Add the EA FC player ratings CSV to `data/raw/` and restart."
            )
        ExactRosterMapper().calculate_exact_squad_ratings()

    if not FEATURES_PATH.exists():
        FeaturePipeline().run_blender_pipeline()

    return pd.read_csv(FEATURES_PATH).set_index("team")


st.set_page_config(page_title="World Cup Predictor Engine", layout="wide")

st.title("🏆 World Cup Poisson Prediction Engine")
st.caption("Calibrated Performance Modeling via Team Metrics and Market Power")

# --- MULTI-PAGE SETUP VIA TABS ---
tab1, tab2 = st.tabs(["🔮 Match Simulator", "📅 Tournament Groups & Schedule"])

try:
    with st.spinner("Building feature matrix (first run only)..."):
        df_features = load_features()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"Failed to build the feature matrix: {e}")
    st.stop()

teams = sorted(df_features.index.tolist())

# ==========================================
# TAB 1: THE MATCH SIMULATOR
# ==========================================
with tab1:
    # Sidebar Configuration for Weights
    st.sidebar.header("🎯 Model Hyperparameters")
    w_hist = st.sidebar.slider("History Weight", 0.0, 1.0, 0.250, step=0.005)
    w_squad = st.sidebar.slider("Squad Weight", 0.0, 1.0, 0.550, step=0.005)
    w_market = st.sidebar.slider("Market Weight", 0.0, 1.0, 0.300, step=0.005)
    
    total_w = w_hist + w_squad + w_market
    st.sidebar.write(f"Total Weight Sum: `{total_w:.3f}`")
    
    st.header("⚽ Live Fixture Simulator")
    col1, col2 = st.columns(2)
    
    with col1:
        home_team = st.selectbox("Select Home / Team A", teams, index=teams.index("Argentina") if "Argentina" in teams else 0)
    with col2:
        away_team = st.selectbox("Select Away / Team B", teams, index=teams.index("Algeria") if "Algeria" in teams else 1)
        
    if home_team == away_team:
        st.warning("Please select two different international teams to run the matrix simulation.")
    else:
        engine = PoissonPredictionEngine()
        
        home_stats = df_features.loc[home_team].to_dict()
        away_stats = df_features.loc[away_team].to_dict()
        
        results = engine.calculate_match_probabilities(home_stats, away_stats)
        lambda_h, lambda_a = results["lambdas"]
        
        if "1x2_probs" in results:
            probs = results["1x2_probs"]
        elif "probabilities" in results:
            probs = results["probabilities"]
        else:
            st.error("⚠️ Could not find the probability keys in your poisson_engine.py.")
            st.stop()

        if isinstance(probs, (tuple, list)):
            home_win_prob = probs[0]
            draw_prob = probs[1]
            away_win_prob = probs[2]
        else:
            home_win_prob = probs.get("home_win", 0.0)
            draw_prob = probs.get("draw", 0.0)
            away_win_prob = probs.get("away_win", 0.0)
            
        st.subheader("📊 Match Projections")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric(f"{home_team} Expected Goals (xG)", f"{lambda_h:.3f}")
        m_col2.metric("Predicted Match Result Probability", f"Draw: {draw_prob*100:.1f}%")
        m_col3.metric(f"{away_team} Expected Goals (xG)", f"{lambda_a:.3f}")
        
        st.progress(int(home_win_prob * 100))
        st.write(f"**{home_team} Win:** {home_win_prob*100:.1f}% | **Draw:** {draw_prob*100:.1f}% | **{away_team} Win:** {away_win_prob*100:.1f}%")

        def poisson_probability(lmbda, k):
            return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

        score_matrix = []
        for h_goals in range(6):
            for a_goals in range(6):
                p_h = poisson_probability(lambda_h, h_goals)
                p_a = poisson_probability(lambda_a, a_goals)
                exact_score_prob = p_h * p_a
                score_matrix.append({
                    "scoreline": f"{home_team} {h_goals} - {a_goals} {away_team}",
                    "probability": exact_score_prob
                })

        top_scores = sorted(score_matrix, key=lambda x: x["probability"], reverse=True)[:3]

        st.write("---")
        st.subheader("🎯 Top 3 Most Likely Exact Scorelines")
        
        s_col1, s_col2, s_col3 = st.columns(3)
        cols = [s_col1, s_col2, s_col3]
        
        for index, item in enumerate(top_scores):
            cols[index].metric(
                label=f"Rank {index + 1} Scoreline",
                value=item["scoreline"],
                delta=f"{item['probability'] * 100:.2f}% Probability",
                delta_color="normal"
            )

# ==========================================
# TAB 2: TOURNAMENT GROUPS & FIXTURES
# ==========================================
with tab2:
    st.header("🌍 Official 2026 World Cup Group Stage")
    
    groups = {
        "Group A": ["Mexico", "South Africa", "South Korea", "Czechia"],
        "Group B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
        "Group C": ["Brazil", "Morocco", "Haiti", "Scotland"],
        "Group D": ["United States", "Paraguay", "Australia", "Türkiye"],
        "Group E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
        "Group F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
        "Group G": ["Belgium", "Egypt", "Iran", "New Zealand"],
        "Group H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
        "Group I": ["France", "Senegal", "Iraq", "Norway"],
        "Group J": ["Argentina", "Algeria", "Austria", "Jordan"],
        "Group K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
        "Group L": ["England", "Croatia", "Ghana", "Panama"]
    }

    # Generate complete list of fixtures programmatically
    schedule_data = []
    for group_name, team_list in groups.items():
        # Round-robin pairings mapped out by tournament matchday conventions
        fixtures = [
            {"matchday": "Matchday 1", "home": team_list[0], "away": team_list[1]},
            {"matchday": "Matchday 1", "home": team_list[2], "away": team_list[3]},
            {"matchday": "Matchday 2", "home": team_list[0], "away": team_list[2]},
            {"matchday": "Matchday 2", "home": team_list[3], "away": team_list[1]},
            {"matchday": "Matchday 3", "home": team_list[3], "away": team_list[0]},
            {"matchday": "Matchday 3", "home": team_list[1], "away": team_list[2]},
        ]
        for f in fixtures:
            schedule_data.append({
                "Group": group_name,
                "Matchday": f["matchday"],
                "Fixture": f"{f['home']} vs {f['away']}"
            })
            
    df_schedule = pd.DataFrame(schedule_data)

    # UI Layout: Left split for Group View, Right split for Schedule search
    layout_col1, layout_col2 = st.columns([1, 1])
    
    with layout_col1:
        st.subheader("📋 Group Alignment")
        grid_cols = st.columns(2)
        for index, (group_name, team_list) in enumerate(groups.items()):
            with grid_cols[index % 2]:
                st.markdown(f"**{group_name}**")
                for team in team_list:
                    st.write(f"• {team}")
                st.write("")

    with layout_col2:
        st.subheader("📅 Group Stage Fixture Finder")
        
        # Interactive filters so your friend can search by group or matchday
        filter_group = st.selectbox("Filter Schedule by Group", ["All Groups"] + list(groups.keys()))
        filter_md = st.radio("Filter by Matchday", ["All Matchdays", "Matchday 1", "Matchday 2", "Matchday 3"], horizontal=True)
        
        df_filtered = df_schedule.copy()
        if filter_group != "All Groups":
            df_filtered = df_filtered[df_filtered["Group"] == filter_group]
        if filter_md != "All Matchdays":
            df_filtered = df_filtered[df_filtered["Matchday"] == filter_md]
            
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)