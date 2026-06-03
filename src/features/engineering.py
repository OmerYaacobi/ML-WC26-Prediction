import json
import pandas as pd
from pathlib import Path

class FeatureEngineer:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.exact_ratings_path = self.processed_dir / "exact_team_ratings.csv"
        
    def extract_match_history(self):
        """Scans ALL fixture JSON files in the raw directory and aggregates historical goals."""
        
        # NEW: Find every file that starts with 'fixtures_'
        fixture_files = list(self.raw_dir.glob("fixtures_*.json"))
        
        if not fixture_files:
            raise FileNotFoundError("No fixture files found. Run the orchestrator/api_client first.")
            
        print(f"Aggregating data across {len(fixture_files)} tournaments...")
        team_stats = {}
        
        for file_path in fixture_files:
            with open(file_path, "r") as f:
                fixtures = json.load(f)
                
            for item in fixtures:
                status = item["fixture"]["status"]["short"]
                if status not in ["FT", "AET", "PEN"]:
                    continue
                    
                home_team = item["teams"]["home"]["name"]
                away_team = item["teams"]["away"]["name"]
                
                home_goals = item["score"]["extratime"]["home"] if item["score"]["extratime"]["home"] is not None else item["score"]["fulltime"]["home"]
                away_goals = item["score"]["extratime"]["away"] if item["score"]["extratime"]["away"] is not None else item["score"]["fulltime"]["away"]
                
                for team in [home_team, away_team]:
                    if team not in team_stats:
                        team_stats[team] = {"games": 0, "scored": 0, "conceded": 0}
                        
                team_stats[home_team]["games"] += 1
                team_stats[home_team]["scored"] += home_goals
                team_stats[home_team]["conceded"] += away_goals
                
                team_stats[away_team]["games"] += 1
                team_stats[away_team]["scored"] += away_goals
                team_stats[away_team]["conceded"] += home_goals
                
        return pd.DataFrame.from_dict(team_stats, orient="index").reset_index().rename(columns={"index": "team"})

    def calculate_poisson_metrics(self, df):
        print("\n--- Calculating Poisson Modifiers ---")
        total_games = df["games"].sum() / 2  
        total_goals = df["scored"].sum()
        global_avg_goals_per_game = total_goals / (total_games * 2) 
        
        print(f"Global Average: {global_avg_goals_per_game:.2f} goals per team per game")

        df["avg_scored"] = df["scored"] / df["games"]
        df["avg_conceded"] = df["conceded"] / df["games"]
        
        df["attack_strength"] = (df["avg_scored"] / global_avg_goals_per_game).round(3)
        df["defense_weakness"] = (df["avg_conceded"] / global_avg_goals_per_game).round(3)
        
        return df[["team", "games", "attack_strength", "defense_weakness"]]

    def merge_with_squad_ratings(self, historical_df):
        if not self.exact_ratings_path.exists():
            print("Warning: exact_team_ratings.csv missing.")
            return historical_df
            
        print("\n--- Fusing History with Modern Squad Data ---")
        squad_df = pd.read_csv(self.exact_ratings_path)
        
        # 1. Standardize API match fixture names to match our Official Universe
        api_name_fixes = {
            "USA": "United States",
            "Cote D Ivoire": "Ivory Coast",
            "Czech Republic": "Czechia",
            "Congo DR": "DR Congo",
            "Bosnia": "Bosnia and Herzegovina"
        }
        historical_df["team"] = historical_df["team"].replace(api_name_fixes)
        
        # 2. Merge the historical stats with the squad ratings on team name
        final_model_df = pd.merge(squad_df, historical_df, on="team", how="left")
        
        # 3. IMPUTATION: Fill missing historical stats for teams that didn't play in our JSONs
        # 1.0 means exactly "average" in our Poisson math
        final_model_df["games"] = final_model_df["games"].fillna(0)
        final_model_df["attack_strength"] = final_model_df["attack_strength"].fillna(1.0)
        final_model_df["defense_weakness"] = final_model_df["defense_weakness"].fillna(1.0)
        
        # Clean squad metrics just in case
        final_model_df["exact_squad_rating"] = final_model_df["exact_squad_rating"].fillna(70.0)
        final_model_df["players_matched"] = final_model_df["players_matched"].fillna(0)
        
        # 4. Save out to CSV
        output_path = self.processed_dir / "final_model_features.csv"
        final_model_df.to_csv(output_path, index=False)
        print(f"✅ Success! Master training matrix saved to {output_path} ({len(final_model_df)} teams)")
        
        return final_model_df
if __name__ == "__main__":
    engineer = FeatureEngineer()
    historical_data = engineer.extract_match_history()
    poisson_metrics = engineer.calculate_poisson_metrics(historical_data)
    engineer.merge_with_squad_ratings(poisson_metrics)