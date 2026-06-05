import pandas as pd
from pathlib import Path

class HistoryDataLoader:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.csv_path = self.raw_dir / "results.csv"

    def load_historical_metrics(self):
        """
        Parses thousands of real international matches from the Kaggle dataset
        and computes normalized attack and defense metrics for every country.
        """
        print("📊 HistoryDataLoader: Parsing Kaggle international results matrix...")
        
        if not self.csv_path.exists():
            print(f"⚠️  Warning: results.csv not found at {self.csv_path}")
            print("💡 Please download 'results.csv' from Kaggle and place it in your data/raw/ folder.")
            return pd.DataFrame(columns=["team", "hist_attack", "hist_defense"])

        # Load raw dataset
        df = pd.read_csv(self.csv_path)

        # Convert date and filter for the last 2 years of modern international football
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] >= "2024-01-01"].copy()

        if df.empty:
            print("⚠️  Warning: No matches found matching the date criteria.")
            return pd.DataFrame(columns=["team", "hist_attack", "hist_defense"])

        # 1. Compute global tournament averages (the baselines)
        avg_home_goals = df["home_score"].mean()
        avg_away_goals = df["away_score"].mean()

        # 2. Compute Home Stats per team
        home_stats = df.groupby("home_team").agg(
            home_goals_scored=("home_score", "mean"),
            home_goals_conceded=("away_score", "mean"),
            home_games=("home_score", "count")
        )

        # 3. Compute Away Stats per team
        away_stats = df.groupby("away_team").agg(
            away_goals_scored=("away_score", "mean"),
            away_goals_conceded=("home_score", "mean"),
            away_games=("away_score", "count")
        )

        # Combine home and away records into a single unified matrix
        all_teams = sorted(list(set(df["home_team"].unique()).union(set(df["away_team"].unique()))))
        
        metrics_list = []
        for team in all_teams:
            h_record = home_stats.loc[team] if team in home_stats.index else None
            a_record = away_stats.loc[team] if team in away_stats.index else None

            # Weighted averages based on number of games played home vs away
            total_games = (h_record["home_games"] if h_record is not None else 0) + \
                          (a_record["away_games"] if a_record is not None else 0)
            
            if total_games == 0:
                continue

            # Calculate raw scoring/conceding averages
            h_gf = h_record["home_goals_scored"] if h_record is not None else 0
            a_gf = a_record["away_goals_scored"] if a_record is not None else 0
            actual_avg_scored = ((h_gf * (h_record["home_games"] if h_record is not None else 0)) + \
                                 (a_gf * (a_record["away_games"] if a_record is not None else 0))) / total_games

            h_ga = h_record["home_goals_conceded"] if h_record is not None else 0
            a_ga = a_record["away_goals_conceded"] if a_record is not None else 0
            actual_avg_conceded = ((h_ga * (h_record["home_games"] if h_record is not None else 0)) + \
                                   (a_ga * (a_record["away_games"] if a_record is not None else 0))) / total_games

            # 4. Normalize against global baselines to find true structural strength
            # If a team scores more than the average team, their attack strength will be > 1.0
            hist_attack = actual_avg_scored / ((avg_home_goals + avg_away_goals) / 2)
            hist_defense = actual_avg_conceded / ((avg_home_goals + avg_away_goals) / 2)

            metrics_list.append({
                "team": team,
                "hist_attack": round(hist_attack, 4),
                "hist_defense": round(hist_defense, 4)
            })

        print(f"✅ HistoryDataLoader: Successfully processed metrics for {len(metrics_list)} international teams.")
        return pd.DataFrame(metrics_list)

if __name__ == "__main__":
    loader = HistoryDataLoader()
    df_test = loader.load_historical_metrics()
    if not df_test.empty:
        print(df_test.head(10))