import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.graph_objects as go
from pathlib import Path
from scipy.stats import poisson
from src.models.poisson_engine import PoissonPredictionEngine
from src.features.pipeline import FeaturePipeline
from src.features.squad_mapper import ExactRosterMapper

PROJECT_ROOT = Path(__file__).resolve().parent
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "blended_model_features.csv"
SQUAD_RATINGS_PATH = PROJECT_ROOT / "data" / "processed" / "exact_team_ratings.csv"


MIN_DISPLAY_CHANCE = 5.0
MAX_SCAN_GOALS = 10


def format_outcome_percents(home_p, draw_p, away_p):
    """Round to one decimal so displayed win/draw/loss always sums to 100.0%."""
    raw = [home_p * 100, draw_p * 100, away_p * 100]
    rounded = [round(value, 1) for value in raw]
    drift = round(100.0 - sum(rounded), 1)
    if drift:
        idx = raw.index(max(raw))
        rounded[idx] = round(rounded[idx] + drift, 1)
    return rounded


def build_joint_probs(lambda_h, lambda_a):
    return np.array([
        [poisson.pmf(h, lambda_h) * poisson.pmf(a, lambda_a) for a in range(MAX_SCAN_GOALS)]
        for h in range(MAX_SCAN_GOALS)
    ])


def goal_distribution_rows(lambda_val):
    rows = [
        {"Goals": k, "Chance %": poisson.pmf(k, lambda_val) * 100}
        for k in range(MAX_SCAN_GOALS)
        if poisson.pmf(k, lambda_val) * 100 >= MIN_DISPLAY_CHANCE
    ]
    if not rows:
        best_k = max(range(MAX_SCAN_GOALS), key=lambda k: poisson.pmf(k, lambda_val))
        rows = [{"Goals": best_k, "Chance %": poisson.pmf(best_k, lambda_val) * 100}]
    return rows


def goal_distribution_chart(team_name, lambda_val):
    chart_df = pd.DataFrame(goal_distribution_rows(lambda_val))
    return (
        alt.Chart(chart_df)
        .mark_bar(color="#4C78A8")
        .encode(
            x=alt.X("Goals:O", title="Goals scored", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Chance %:Q", title="Chance %", scale=alt.Scale(zero=True)),
            tooltip=[
                alt.Tooltip("Goals:O", title="Goals"),
                alt.Tooltip("Chance %:Q", title="Chance %", format=".1f"),
            ],
        )
        .properties(height=260, title=f"{team_name}  ·  xG {lambda_val:.2f}")
    )


def likely_scorelines_3d(home_team, away_team, joint_probs):
    scorelines = [
        (h, a, joint_probs[h, a] * 100)
        for h in range(joint_probs.shape[0])
        for a in range(joint_probs.shape[1])
        if joint_probs[h, a] * 100 >= MIN_DISPLAY_CHANCE
    ]
    if not scorelines:
        flat = [
            (h, a, joint_probs[h, a] * 100)
            for h in range(joint_probs.shape[0])
            for a in range(joint_probs.shape[1])
        ]
        scorelines = [max(flat, key=lambda item: item[2])]

    return go.Figure(
        data=[
            go.Scatter3d(
                x=[row[0] for row in scorelines],
                y=[row[1] for row in scorelines],
                z=[row[2] for row in scorelines],
                mode="markers+text",
                text=[f"{h}–{a}" for h, a, _ in scorelines],
                textposition="top center",
                marker={
                    "size": [max(10, chance * 2.5) for _, _, chance in scorelines],
                    "color": [chance for _, _, chance in scorelines],
                    "colorscale": "YlOrRd",
                    "showscale": True,
                    "colorbar": {"title": "Chance %"},
                    "line": {"width": 0.5, "color": "#333"},
                },
                hovertemplate=(
                    f"{home_team}: %{{x}} goals<br>"
                    f"{away_team}: %{{y}} goals<br>"
                    "Chance: %{z:.1f}%<extra></extra>"
                ),
            )
        ],
        layout={
            "height": 520,
            "margin": {"l": 0, "r": 0, "t": 30, "b": 0},
            "scene": {
                "xaxis": {"title": f"{home_team} goals", "dtick": 1, "tickmode": "linear"},
                "yaxis": {"title": f"{away_team} goals", "dtick": 1, "tickmode": "linear"},
                "zaxis": {"title": "Chance %"},
                "camera": {"eye": {"x": 1.6, "y": 1.6, "z": 1.1}},
            },
        },
    )


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
    st.header("⚽ Live Fixture Simulator")
    col1, col2 = st.columns(2)
    
    with col1:
        home_team = st.selectbox("Select Team A", teams, index=teams.index("Argentina") if "Argentina" in teams else 0)

    away_options = [team for team in teams if team != home_team]
    default_away = "Algeria" if "Algeria" in away_options else away_options[0]

    with col2:
        away_team = st.selectbox(
            "Select Team B",
            away_options,
            index=away_options.index(default_away),
        )

    st.caption(
        "This model treats both teams equally — no home-field advantage is applied. "
        "In the real 2026 World Cup, USA, Canada, and Mexico may benefit as hosts, "
        "but that effect is not included in these predictions."
    )

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

    home_pct, draw_pct, away_pct = format_outcome_percents(
        home_win_prob, draw_prob, away_win_prob
    )
    outcomes = [
        (f"{home_team} Win", home_pct),
        ("Draw", draw_pct),
        (f"{away_team} Win", away_pct),
    ]
    most_likely_label, most_likely_pct = max(outcomes, key=lambda item: item[1])

    st.subheader("📊 Match Projections")

    xg_help = (
        "Expected Goals (xG) is the average number of goals a team is predicted to score "
        "in this matchup. It blends historical form, squad strength, and market odds — "
        "it is an average, not a guarantee of how many goals they will actually score."
    )

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric(f"{home_team} Expected Goals (xG)", f"{lambda_h:.3f}", help=xg_help)
    m_col2.metric(
        "Most Likely Result",
        f"{most_likely_label}: {most_likely_pct:.1f}%",
        help="The match outcome (win or draw) with the highest probability according to the model.",
    )
    m_col3.metric(f"{away_team} Expected Goals (xG)", f"{lambda_a:.3f}", help=xg_help)

    with st.expander("What do these terms mean?"):
        st.markdown(
            """
**Expected Goals (xG)** — The *average* goals a team is expected to score in this specific
matchup. An xG of 2.0 does not mean they will score exactly 2; it means that if this
fixture were played many times, they would average 2 goals per game.

**Most Likely Result** — The win/draw/loss outcome with the highest probability. This can
differ from the most likely *exact scoreline* (shown below).

**Win / Draw %** — The chance each team wins or the match ends level, derived from a
Poisson score model. All three always sum to 100%.
            """
        )

    st.write(
        f"**{home_team} Win:** {home_pct:.1f}% | "
        f"**Draw:** {draw_pct:.1f}% | "
        f"**{away_team} Win:** {away_pct:.1f}%"
    )

    joint_probs = build_joint_probs(lambda_h, lambda_a)

    score_matrix = [
        {"home_goals": h, "away_goals": a, "probability": joint_probs[h, a]}
        for h in range(joint_probs.shape[0])
        for a in range(joint_probs.shape[1])
    ]
    top_scores = sorted(score_matrix, key=lambda x: x["probability"], reverse=True)[:3]

    st.write("---")
    st.subheader("🎯 Top 3 Most Likely Exact Scorelines")

    s_col1, s_col2, s_col3 = st.columns(3)
    cols = [s_col1, s_col2, s_col3]

    for index, item in enumerate(top_scores):
        with cols[index]:
            st.metric(
                label=f"#{index + 1} · {item['probability'] * 100:.2f}% chance",
                value=f"{item['home_goals']} – {item['away_goals']}",
            )
            st.caption(f"{home_team} vs {away_team}")

    st.write("---")
    st.subheader("📈 Probability Visualizations")
    st.caption(f"Only outcomes with at least {MIN_DISPLAY_CHANCE:.0f}% chance are shown below.")

    dist_col1, dist_col2 = st.columns(2)

    with dist_col1:
        st.altair_chart(goal_distribution_chart(home_team, lambda_h), use_container_width=True)

    with dist_col2:
        st.altair_chart(goal_distribution_chart(away_team, lambda_a), use_container_width=True)

    st.markdown(f"**Likely exact scorelines (≥ {MIN_DISPLAY_CHANCE:.0f}% chance)**")
    st.caption(
        f"3D view — X: {home_team} goals · Y: {away_team} goals · Height: chance %. "
        "Drag to rotate."
    )
    st.plotly_chart(
        likely_scorelines_3d(home_team, away_team, joint_probs),
        use_container_width=True,
    )

    st.caption(
        "xG is the *average* expected goals, not the single most likely goal count. "
        "For xG ≈ 2, scoring exactly 1 or 2 goals are nearly equally likely (~27% each). "
        "That is why a draw like 1–1 can edge out 2–1 — the weaker team scoring 1 is often "
        "more likely than scoring 0."
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