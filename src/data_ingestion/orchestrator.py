import json
import time
import pandas as pd
from pathlib import Path
from src.data_ingestion.api_client import FootballAPIClient

class DataOrchestrator:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.api_client = FootballAPIClient()
        
    def fetch_2026_world_cup_teams(self):
        print("Fetching World Cup fixture framework (Using 2022 proxy for free tier)...")
        # We check if we already have the fixtures so we don't waste API calls
        fixture_file = self.raw_dir / "fixtures_league_1_2022.json"
        if not fixture_file.exists():
            self.api_client.get_historical_fixtures(league_id=1, season=2022)
            
        with open(fixture_file, "r") as f:
            fixtures = json.load(f)
            
        teams = {}
        for item in fixtures:
            home = item["teams"]["home"]
            away = item["teams"]["away"]
            teams[home["name"]] = home["id"]
            teams[away["name"]] = away["id"]
            
        print(f"Successfully identified {len(teams)} proxy teams.")
        return teams

    def download_squads_for_teams(self, teams_dict):
        print("\n--- Downloading Squad Rosters (with Rate Limiting) ---")
        for team_name, team_id in teams_dict.items():
            # CACHE CHECK: If we already have this file, skip the API call!
            squad_file = self.raw_dir / f"squad_team_{team_id}.json"
            if squad_file.exists():
                print(f"Skipping {team_name}... (Already downloaded)")
                continue
                
            print(f"Syncing roster for {team_name}...")
            self.api_client.get_team_squad(team_id)
            
            # RATE LIMITER: Pause for 7 seconds to respect the 10 req/min limit
            print("Pausing for 7 seconds to respect API limits...")
            time.sleep(7)

    def compute_fc26_team_ratings(self):
        csv_path = self.raw_dir / "EAFC26-Men.csv"
        if not csv_path.exists():
            print(f"Warning: {csv_path.name} not found. Run kaggle_client.py first.")
            return

        print("\n--- Aggregating EA FC 26 Player Ratings ---")
        df = pd.read_csv(csv_path)

        # FIX: The column name in this specific Kaggle dataset is 'Nation', not 'Nationality'
        top_players = df.sort_values(by="OVR", ascending=False).groupby("Nation").head(26)

        # Calculate general overall rating per country
        team_stats = top_players.groupby("Nation").agg(
            fifa_overall_rating=("OVR", "mean")
        ).reset_index()

        # Map positional ratings
        attack_positions = ["ST", "CF", "LW", "RW", "LS", "RS"]
        midfield_positions = ["CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM"]
        defense_positions = ["CB", "LB", "RB", "LWB", "RWB"]

        df_att = top_players[top_players["Position"].isin(attack_positions)].groupby("Nation")["OVR"].mean()
        df_mid = top_players[top_players["Position"].isin(midfield_positions)].groupby("Nation")["OVR"].mean()
        df_def = top_players[top_players["Position"].isin(defense_positions)].groupby("Nation")["OVR"].mean()

        # Merge positional components back together
        team_stats["fifa_attack"] = team_stats["Nation"].map(df_att)
        team_stats["fifa_midfield"] = team_stats["Nation"].map(df_mid)
        team_stats["fifa_defense"] = team_stats["Nation"].map(df_def)

        # Clean column naming conventions
        team_stats.rename(columns={"Nation": "team"}, inplace=True)
        team_stats = team_stats.round(1)

        # Save out
        output_path = self.raw_dir / "fifa_team_ratings.csv"
        team_stats.to_csv(output_path, index=False)
        print(f"Successfully generated automated ratings table at {output_path}")

    def run_pipeline(self):
        teams = self.fetch_2026_world_cup_teams()
        self.download_squads_for_teams(teams)
        self.compute_fc26_team_ratings()
        print("\nPipeline complete! Clean data structures ready for feature extraction.")

if __name__ == "__main__":
    orchestrator = DataOrchestrator()
    orchestrator.run_pipeline()