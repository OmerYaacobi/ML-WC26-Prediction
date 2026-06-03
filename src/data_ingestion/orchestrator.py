import json
import time
import pandas as pd
from pathlib import Path
from src.data_ingestion.api_client import FootballAPIClient

class DataOrchestrator:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.api_client = FootballAPIClient()
        
        # The Official 48-Team 2026 Universe
        self.tournament_teams = [
            "Mexico", "South Africa", "South Korea", "Czechia", 
            "Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland",
            "Brazil", "Morocco", "Haiti", "Scotland",
            "United States", "Paraguay", "Australia", "Turkey",
            "Germany", "Curacao", "Ivory Coast", "Ecuador",
            "Netherlands", "Japan", "Sweden", "Tunisia",
            "Belgium", "Egypt", "Iran", "New Zealand",
            "Spain", "Cape Verde", "Saudi Arabia", "Uruguay",
            "France", "Senegal", "Iraq", "Norway",
            "Argentina", "Algeria", "Austria", "Jordan",
            "Portugal", "DR Congo", "Uzbekistan", "Colombia",
            "England", "Croatia", "Ghana", "Panama"
        ]

    def get_downloaded_team_names(self):
        """Scans downloaded JSON files to see which teams we already have."""
        downloaded = []
        for file_path in self.raw_dir.glob("squad_team_*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    if data and isinstance(data, list):
                        downloaded.append(data[0]["team"]["name"])
            except Exception:
                continue
        return downloaded

    def fetch_all_48_squads(self):
        print("\n--- Hunting Down All 48 Squads ---")
        downloaded_teams = self.get_downloaded_team_names()

        for team_name in self.tournament_teams:
            # Handle API-Sports naming quirks for the search engine
            api_search_name = team_name
            if team_name == "United States": api_search_name = "USA"
            if team_name == "Ivory Coast": api_search_name = "Ivory Coast"
            if team_name == "Czechia": api_search_name = "Czech Republic"
            if team_name == "Bosnia and Herzegovina": api_search_name = "Bosnia"
            if team_name == "DR Congo": api_search_name = "Congo DR"
            
            if team_name in downloaded_teams or api_search_name in downloaded_teams:
                print(f"Skipping {team_name}... (Already downloaded)")
                continue

            print(f"Hunting for missing team ID: {team_name}...")
            team_id = self.api_client.search_team_id(api_search_name)
            
            # RATE LIMIT FIX 1: Pause after the search API call
            time.sleep(6.5) 

            if team_id:
                print(f"Found ID: {team_id}. Syncing roster...")
                self.api_client.get_team_squad(team_id)
                
                # RATE LIMIT FIX 2: Pause after the squad download API call
                time.sleep(6.5)
            else:
                print(f"⚠️ Failed to find API ID for {team_name}.")

    def compute_fc26_team_ratings(self):
        csv_path = self.raw_dir / "EAFC26-Men.csv"
        if not csv_path.exists():
            print(f"Warning: {csv_path.name} not found. Run kaggle_client.py first.")
            return

        print("\n--- Aggregating EA FC 26 Player Ratings ---")
        df = pd.read_csv(csv_path)

        top_players = df.sort_values(by="OVR", ascending=False).groupby("Nation").head(26)

        team_stats = top_players.groupby("Nation").agg(
            fifa_overall_rating=("OVR", "mean")
        ).reset_index()

        attack_positions = ["ST", "CF", "LW", "RW", "LS", "RS"]
        midfield_positions = ["CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM"]
        defense_positions = ["CB", "LB", "RB", "LWB", "RWB"]

        df_att = top_players[top_players["Position"].isin(attack_positions)].groupby("Nation")["OVR"].mean()
        df_mid = top_players[top_players["Position"].isin(midfield_positions)].groupby("Nation")["OVR"].mean()
        df_def = top_players[top_players["Position"].isin(defense_positions)].groupby("Nation")["OVR"].mean()

        team_stats["fifa_attack"] = team_stats["Nation"].map(df_att)
        team_stats["fifa_midfield"] = team_stats["Nation"].map(df_mid)
        team_stats["fifa_defense"] = team_stats["Nation"].map(df_def)

        team_stats.rename(columns={"Nation": "team"}, inplace=True)
        team_stats = team_stats.round(1)

        output_path = self.raw_dir / "fifa_team_ratings.csv"
        team_stats.to_csv(output_path, index=False)
        print(f"Successfully generated automated ratings table at {output_path}")

    def run_pipeline(self):
        self.fetch_all_48_squads()
        self.compute_fc26_team_ratings()
        print("\nPipeline complete! Clean data structures ready for feature extraction.")

if __name__ == "__main__":
    orchestrator = DataOrchestrator()
    orchestrator.run_pipeline()