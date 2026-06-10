# WC26 Match Centre — World Cup Score Predictor

A Poisson-based match prediction engine for the **2026 FIFA World Cup**, presented as a sportsbook-style **Match Centre** web app. The model blends three signals — international match history (2022+), squad strength from player ratings, and live betting market odds — to estimate expected goals, win/draw/loss probabilities, fair betting odds, and the most likely exact scorelines.

## ⚡ The Match Centre web app (`webapp/`)

A zero-dependency static web app — the entire Poisson engine runs client-side in JavaScript (verified to match the Python engine to 6 decimal places). No server, no Python, no build step: host it anywhere (GitHub Pages works) or open it locally.

```bash
# serve locally
python3 -m http.server 8765 --directory webapp
# then open http://localhost:8765
```

**Features:**

- **Match Odds view** — pick any two of the 48 qualified teams (swap button included) and get:
  - xG for both teams, model pick, and a win/draw/win probability bar
  - **Markets with fair decimal odds** (1 ÷ probability, no margin): Match Result (1X2), Double Chance, Total Goals Over/Under 1.5 / 2.5 / 3.5, Both Teams To Score, and Correct Score (top 6)
  - Goal distribution charts for each team and an exact-scoreline probability heatmap
- **🧾 Bet Slip** — tap any odds button to build an accumulator across matches; see combined fair odds, the model's chance that all legs land, and the fair return for your stake. Persisted in `localStorage`. (For fun and analysis — not betting advice.)
- **Groups & Fixtures view** — all 12 groups as **projected tables** (expected points computed live from the engine, qualification spots highlighted), plus a fixture finder with group/matchday filters and one-tap "View odds" for any fixture.

After rebuilding model features, regenerate the app's data file:

```bash
python3 scripts/build_webapp_data.py   # writes webapp/data.js (stdlib only, no pip installs)
```

The original Streamlit dashboard (`app.py`) is still included and works as before.

**Streamlit version (legacy, hosted):**
👉 **[https://ml-wc26-prediction-jp4sc9qrqyrzsqfjtebesl.streamlit.app/](https://ml-wc26-prediction-jp4sc9qrqyrzsqfjtebesl.streamlit.app/)**

---

## What it does

| Output | Description |
|--------|-------------|
| Expected goals (xG) | Poisson λ for each team in a fixture |
| 1X2 probabilities | Win, draw, and loss chances |
| Exact scorelines | Top likely results with confidence |
| Visualizations | Goal distributions and 3D scoreline chart |
| Group stage view | All 12 groups, fixtures, and matchday filters |

Each team gets an **attack strength** and **defense weakness** score, blended from history, squad quality, and market power. Those feed into independent Poisson distributions, combined into a full score matrix.

**Current calibrated weights** (in `pipeline.py` / `poisson_engine.py`):

| Parameter | Value |
|-----------|-------|
| History weight | 0.200 |
| Squad weight | 0.430 |
| Market power | 0.330 |
| `GLOBAL_BASE_XG` | 2.240 |

Validated against Bet365 correct-score odds: **±0.236 goals MAE** (6-fold cross-validation).

---

## Try it now

1. Go to the **[live Streamlit app](https://ml-wc26-prediction-jp4sc9qrqyrzsqfjtebesl.streamlit.app/)**
2. Open the **Match Simulator** tab
3. Select **Team A** and **Team B**
4. Review xG, outcome probabilities, top scorelines, and charts

The **Groups & Schedule** tab shows the full 2026 group stage draw and fixtures.

---

## How the model works

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Match History  │   │  Squad Ratings  │   │  Market Odds    │
│  (results.csv)  │   │  (EA FC players)│   │  (Bet365 JSON)  │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │   Feature Pipeline   │
                    │  attack_strength     │
                    │  defense_weakness    │
                    │  squad_rating        │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Poisson Engine      │
                    │  λ = base × att ×    │
                    │      def × squad_mod │
                    └──────────┬───────────┘
                               ▼
              xG · 1X2 probs · exact scorelines
```

For each match:

```
λ_A = GLOBAL_BASE × attack_A × defense_B × (squad_A / squad_B)
λ_B = GLOBAL_BASE × attack_B × defense_A × (squad_B / squad_A)
```

Goal counts are modeled as independent Poisson random variables. Summing the joint probability grid gives win, draw, and loss chances.

The model treats both teams symmetrically — **no home-field advantage** is applied.

---

## Run locally (developers)

Want to modify the model, rebuild features, or run the CLI? Clone the repo:

```bash
git clone https://github.com/OmerYaacobi/ML-WC26-Prediction.git
cd ML-WC26-Prediction

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Data setup

Pre-built feature files are committed for the live app. To rebuild from scratch, add raw data under `data/raw/`:

| File | Purpose |
|------|---------|
| `results.csv` | International match results since **2022** ([Kaggle dataset](https://www.kaggle.com/datasets/patateriedata/international-football-results-from-1872-to-2024)) |
| `EAFC26-Men.csv` | Player ratings for squad strength |
| `market_odds_group_stage.json` | Optional — fetch with `python fetch_group_odds.py` (needs `ODDS_API_KEY` in `.env`) |

Build features:

```bash
python -m src.features.squad_mapper
python -m src.features.pipeline
```

### Local dashboard & CLI

```bash
streamlit run app.py
```

```bash
python -m src.main --teamA Brazil --teamB France
python -m src.main --rebuild --teamA Argentina --teamB Germany
```

---

## Project structure

```
world-cup-score-predictor/
├── webapp/                     # ⚡ Match Centre — static sportsbook-style web app
│   ├── index.html
│   ├── style.css
│   ├── app.js                  # Client-side Poisson engine + UI
│   └── data.js                 # Generated team ratings (see scripts/)
├── scripts/
│   └── build_webapp_data.py    # Regenerate webapp/data.js from processed features
├── app.py                      # Streamlit dashboard (legacy, deployed to Streamlit Cloud)
├── fetch_group_odds.py         # Download & cache Bet365 group-stage odds
├── requirements.txt
├── data/
│   ├── raw/                    # Source datasets (not committed)
│   └── processed/              # Pre-built feature CSVs for cloud deploy
├── notebooks/
│   └── 01_exploratory_data_analysis.ipynb
└── src/
    ├── main.py                 # CLI entry point
    ├── data_layers/
    │   ├── history_loader.py   # Parse match results → attack/defense
    │   ├── squad_loader.py     # Load processed squad ratings
    │   └── market_loader.py    # Parse cached betting odds JSON
    ├── features/
    │   ├── squad_mapper.py     # Map players → team squad ratings
    │   └── pipeline.py         # Blend layers → feature matrix
    ├── models/
    │   ├── poisson_engine.py   # Core prediction math
    │   ├── optimize_weights.py # Tune weights (matches evaluate_cv)
    │   └── evaluate_cv.py      # Cross-validate against market xG
    ├── simulations/
    │   └── group_simulator.py  # Monte Carlo group-stage simulation
    └── validation/
        └── betting_comparator.py
```

---

## Advanced usage

**Optimize blend weights** against market correct-score targets:

```bash
python -m src.models.optimize_weights
```

**Cross-validate** model xG against Bet365 implied scorelines:

```bash
python -m src.models.evaluate_cv
```

**Simulate group stages** (Monte Carlo):

```bash
python -m src.simulations.group_simulator
```

---

## Requirements

- Python 3.10+
- See `requirements.txt` (pandas, scipy, scikit-learn, streamlit, plotly, altair, etc.)

---

## Notes

- Predictions are statistical estimates, not guarantees. Use for analysis and fun — not as betting advice.
- Team names must match the 48-team 2026 tournament roster (e.g. `Czechia`, `Ivory Coast`, `DR Congo`).
- Raw data files are excluded from version control; the live app uses committed processed feature CSVs.
- To update the deployed app after changing weights, re-run the pipeline and push the updated `data/processed/blended_model_features.csv`.

---

## License

Personal / educational project. Check individual dataset licenses (Kaggle, odds API) before redistributing data.
