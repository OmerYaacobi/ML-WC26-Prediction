import pandas as pd
from pathlib import Path

class FeatureEngineer:
    def __init__(self):
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.input_path = self.processed_dir / "normalized_matches.csv"
        
    def load_data(self):
        if not self.input_path.exists():
            raise FileNotFoundError(f"Normalized data not found at {self.input_path}. Run the normalizer first.")
        return pd.read_csv(self.input_path)

    def calculate_global_baselines(self, df):
        """Calculates the average goals scored by home and away teams across the entire dataset."""
        avg_home_goals = df["home_score"].mean()
        avg_away_goals = df["away_score"].mean()
        return avg_home_goals, avg_away_goals

    def build_team_profiles(self):
        """
        Computes the relative Attack and Defense ratings for every team.
        Saves a master team_profiles.csv lookup table.
        """
        df = self.load_data()
        avg_home_g, avg_away_g = self.calculate_global_baselines(df)
        
        print(f"Global Baselines -> Avg Home Goals: {avg_home_g:.2f}, Avg Away Goals: {avg_away_g:.2f}")

        # 1. Calculate Home stats per team
        home_stats = df.groupby("home_team").agg(
            home_games_played=("match_id", "count"),
            home_goals_scored=("home_score", "sum"),
            home_goals_conceded=("away_score", "sum")
        ).reset_index().rename(columns={"home_team": "team"})

        # 2. Calculate Away stats per team
        away_stats = df.groupby("away_team").agg(
            away_games_played=("match_id", "count"),
            away_goals_scored=("away_score", "sum"),
            away_goals_conceded=("home_score", "sum")
        ).reset_index().rename(columns={"away_team": "team"})

        # Merge home and away metrics together
        profiles = pd.merge(home_stats, away_stats, on="team", how="outer").fillna(0)

        # Calculate totals
        profiles["total_games"] = profiles["home_games_played"] + profiles["away_games_played"]
        
        # Prevent division by zero for teams with incomplete data
        profiles = profiles[profiles["total_games"] > 0].copy()

        # 3. Compute relative Attack and Defense Strengths
        # Attack = (Avg goals scored by team) / (Global avg goals scored in that slot)
        profiles["home_attack"] = (profiles["home_goals_scored"] / profiles["home_games_played"]) / avg_home_g
        profiles["away_attack"] = (profiles["away_goals_scored"] / profiles["away_games_played"]) / avg_away_g

        # Defense = (Avg goals conceded by team) / (Global avg goals conceded in that slot)
        profiles["home_defense"] = (profiles["home_goals_conceded"] / profiles["home_games_played"]) / avg_away_g
        profiles["away_defense"] = (profiles["away_goals_conceded"] / profiles["away_games_played"]) / avg_home_g

        # Clean up the dataframe to keep just what our ML model needs
        columns_to_keep = ["team", "total_games", "home_attack", "away_attack", "home_defense", "away_defense"]
        profiles = profiles[columns_to_keep].round(3)

        # Save out profiles to disk
        output_path = self.processed_dir / "team_profiles.csv"
        profiles.to_csv(output_path, index=False)
        print(f"Successfully generated profiles for {len(profiles)} teams at {output_path}")
        
        return profiles

if __name__ == "__main__":
    engineer = FeatureEngineer()
    engineer.build_team_profiles()