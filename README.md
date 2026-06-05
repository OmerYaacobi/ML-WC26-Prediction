# World Cup Score Predictor

A Poisson-based match prediction engine for the **2026 FIFA World Cup**. The model blends three signals — recent international match history, squad strength from player ratings, and live betting market odds — to estimate expected goals, win/draw/loss probabilities, and the most likely exact scorelines.

Includes a **Streamlit dashboard** for interactive simulations and a **CLI** for quick terminal predictions.

---

## What it does

| Output | Description |
|--------|-------------|
| Expected goals (xG) | Poisson λ for each team in a fixture |
| 1X2 probabilities | Home win, draw, and away win chances |
| Exact scorelines | Top likely results (e.g. 1–0, 2–1) with confidence |
| Group stage view | All 12 groups, fixtures, and matchday filters |

The core idea: each team gets an **attack strength** and **defense weakness** score, blended from history, squad quality, and market power. Those feed into independent Poisson distributions for home and away goals, which are combined into a full score matrix.

**Default blend weights** (tunable in the dashboard):

- History — 25%
- Squad — 55%
- Market — 30%

---

## Quick start

### 1. Clone and install

```bash
git clone <your-repo-url>
cd world-cup-score-predictor

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your data

Create the `data/` folders and place the required files:

```
data/
├── raw/
│   ├── results.csv              # International match results (Kaggle)
│   ├── EAFC26-Men.csv           # Player ratings (Kaggle / EA FC dataset)
│   ├── market_odds_group_stage.json   # Optional: fetch via script below
│   └── squad_team_*.json        # Optional: per-team squad files from API
└── processed/                   # Generated automatically by the pipeline
    ├── exact_team_ratings.csv
    └── blended_model_features.csv
```

**`results.csv`** — International football results. Used to compute attack/defense metrics from matches since 2024.  
Download from Kaggle (e.g. [International Football Results](https://www.kaggle.com/datasets/patateriedata/international-football-results-from-1872-to-2024)) and save to `data/raw/results.csv`.

**`EAFC26-Men.csv`** — Player overall ratings used to build squad strength for all 48 World Cup teams.

### 3. (Optional) Fetch live betting odds

Create a `.env` file in the project root:

```env
ODDS_API_KEY=your_key_here
```

Then run:

```bash
python fetch_group_odds.py
```

This caches Bet365 odds for group-stage fixtures into `data/raw/market_odds_group_stage.json`. The script resumes safely if interrupted and skips already-downloaded matches.

### 4. Build features

**Step A** — Compute squad ratings from player data:

```bash
python -m src.features.squad_mapper
```

**Step B** — Blend all data layers into the model feature matrix:

```bash
python -m src.features.pipeline
```

This writes `data/processed/blended_model_features.csv`.

### 5. Run predictions

**Interactive dashboard:**

```bash
streamlit run app.py
```

Open the Match Simulator tab, pick two teams, and explore xG, outcome probabilities, and top scorelines. The Groups & Schedule tab shows the full 2026 group stage draw.

**Command line:**

```bash
python -m src.main --teamA Brazil --teamB France
```

Force a feature rebuild from source data:

```bash
python -m src.main --rebuild --teamA Argentina --teamB Germany
```

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

For each match, expected goals are:

```
λ_home = GLOBAL_BASE × attack_home × defense_away × (squad_home / squad_away)
λ_away = GLOBAL_BASE × attack_away × defense_home × (squad_away / squad_home)
```

Goal counts are modeled as independent Poisson random variables. Summing the joint probability grid gives win, draw, and loss chances.

---

## Project structure

```
world-cup-score-predictor/
├── app.py                      # Streamlit dashboard
├── fetch_group_odds.py         # Download & cache Bet365 group-stage odds
├── requirements.txt
├── data/
│   ├── raw/                    # Source datasets (not committed)
│   └── processed/              # Generated feature files
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
    │   ├── optimize_weights.py # Tune history/squad/market weights
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
- See `requirements.txt` for full dependency list (pandas, scipy, scikit-learn, streamlit, etc.)

---

## Notes

- Predictions are statistical estimates, not guarantees. Use for analysis and fun — not as betting advice.
- Team names must match the 48-team 2026 tournament roster (e.g. `Czechia`, `Ivory Coast`, `DR Congo`).
- If `blended_model_features.csv` is missing, the dashboard and CLI will prompt you to run the feature pipeline first.
- Raw data files are intentionally excluded from version control. Each developer needs to supply their own datasets and API keys.

---

## License

Personal / educational project. Check individual dataset licenses (Kaggle, odds API) before redistributing data.
