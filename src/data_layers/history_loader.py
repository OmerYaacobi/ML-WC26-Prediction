import pandas as pd
from pathlib import Path

# WC26 group games are the freshest signal — weight each match this many times
# vs a typical 2022+ international (so 72 group games materially move ratings).
WC26_GROUP_WEIGHT = 8.0

# results.csv spellings → model team names (must match squad_loader / wc26_groups)
CSV_TO_MODEL = {
    "Curaçao": "Curacao",
    "Czech Republic": "Czechia",
    "Turkey": "Turkey",
    "United States": "United States",
    "South Korea": "South Korea",
    "Ivory Coast": "Ivory Coast",
    "DR Congo": "DR Congo",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
}


def _map_team(name: str) -> str:
    return CSV_TO_MODEL.get(str(name), str(name))


def _row_weight(row) -> float:
    if row.get("tournament") == "FIFA World Cup" and str(row["date"]) >= "2026-06-11":
        return WC26_GROUP_WEIGHT
    return 1.0


class HistoryDataLoader:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.csv_path = self.raw_dir / "results.csv"

    def load_historical_metrics(self):
        """
        Parses international matches from results.csv (2022+) and computes
        normalized attack/defense metrics. WC26 group-stage results are up-weighted.
        """
        print("📊 HistoryDataLoader: Parsing international results matrix...")

        if not self.csv_path.exists():
            print(f"⚠️  Warning: results.csv not found at {self.csv_path}")
            return pd.DataFrame(columns=["team", "hist_attack", "hist_defense"])

        df = pd.read_csv(self.csv_path)
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] >= "2022-01-01"].copy()

        for col in ("home_score", "away_score"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["home_score", "away_score"])

        if df.empty:
            print("⚠️  Warning: No scored matches found matching the date criteria.")
            return pd.DataFrame(columns=["team", "hist_attack", "hist_defense"])

        df["home_team"] = df["home_team"].map(_map_team)
        df["away_team"] = df["away_team"].map(_map_team)
        df["_weight"] = df.apply(_row_weight, axis=1)

        wc26_n = int(((df["tournament"] == "FIFA World Cup") & (df["date"] >= "2026-06-11")).sum())
        print(f"   Using {len(df)} scored matches since 2022 ({wc26_n} WC26 group games ×{WC26_GROUP_WEIGHT:.0f} weight)")

        avg_home_goals = df["home_score"].mean()
        avg_away_goals = df["away_score"].mean()
        global_avg = (avg_home_goals + avg_away_goals) / 2

        home = df.groupby("home_team").apply(
            lambda g: pd.Series(
                {
                    "goals_scored": (g["home_score"] * g["_weight"]).sum() / g["_weight"].sum(),
                    "goals_conceded": (g["away_score"] * g["_weight"]).sum() / g["_weight"].sum(),
                    "games": len(g),
                }
            ),
            include_groups=False,
        )
        away = df.groupby("away_team").apply(
            lambda g: pd.Series(
                {
                    "goals_scored": (g["away_score"] * g["_weight"]).sum() / g["_weight"].sum(),
                    "goals_conceded": (g["home_score"] * g["_weight"]).sum() / g["_weight"].sum(),
                    "games": len(g),
                }
            ),
            include_groups=False,
        )

        all_teams = sorted(set(home.index).union(set(away.index)))
        metrics_list = []
        for team in all_teams:
            h = home.loc[team] if team in home.index else None
            a = away.loc[team] if team in away.index else None
            h_games = float(h["games"]) if h is not None else 0.0
            a_games = float(a["games"]) if a is not None else 0.0
            total_games = h_games + a_games
            if total_games == 0:
                continue

            avg_scored = ((h["goals_scored"] * h_games if h is not None else 0) + (a["goals_scored"] * a_games if a is not None else 0)) / total_games
            avg_conceded = ((h["goals_conceded"] * h_games if h is not None else 0) + (a["goals_conceded"] * a_games if a is not None else 0)) / total_games

            metrics_list.append(
                {
                    "team": team,
                    "hist_attack": round(avg_scored / global_avg, 4),
                    "hist_defense": round(avg_conceded / global_avg, 4),
                }
            )

        print(f"✅ HistoryDataLoader: Processed metrics for {len(metrics_list)} teams.")
        return pd.DataFrame(metrics_list)


if __name__ == "__main__":
    loader = HistoryDataLoader()
    df_test = loader.load_historical_metrics()
    if not df_test.empty:
        print(df_test.head(10))
