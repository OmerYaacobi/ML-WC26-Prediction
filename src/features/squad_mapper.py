import json
import pandas as pd
from unidecode import unidecode
from thefuzz import process
from pathlib import Path
from src.data_ingestion.orchestrator import DataOrchestrator

class ExactRosterMapper:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
    def load_kaggle_database(self):
        """Loads Kaggle data and creates a clean, normalized name column for matching."""
        csv_path = self.raw_dir / "EAFC26-Men.csv"
        df = pd.read_csv(csv_path)
        
        # Strip accents from Kaggle names (e.g., Mbappé -> Mbappe) and lowercase them
        df["Match_Name"] = df["Name"].astype(str).apply(lambda x: unidecode(x).lower())
        return df

    def calculate_exact_squad_ratings(self, teams_dict):
        """Cross-references actual API rosters against Kaggle data using fuzzy matching."""
        kaggle_df = self.load_kaggle_database()

        nation_translation = {
            "USA": "United States",
            "Netherlands": "Holland",
            "South Korea": "Korea Republic",
        }
        
        exact_team_ratings = []

        print("\n--- Mapping Exact Squads to EA FC Ratings ---")
        for team_name, team_id in teams_dict.items():
            squad_file = self.raw_dir / f"squad_team_{team_id}.json"
            
            if not squad_file.exists():
                print(f"Squad missing for {team_name}, skipping.")
                continue
                
            with open(squad_file, "r") as f:
                squad_data = json.load(f)
                
            if not squad_data:
                continue
                
            # Filter Kaggle database to ONLY players from this specific nation
            # This makes matching 100x faster and more accurate
            search_nation = nation_translation.get(team_name, team_name)
            nation_df = kaggle_df[kaggle_df["Nation"] == search_nation]
            # if nation_df.empty:
                # print(f"Warning: No Kaggle players found for nation: {search_nation}")
                # continue

            nation_match_names = nation_df["Match_Name"].tolist()
            matched_ovr_scores = []
            
            # Loop through the actual humans called up to the squad
            for player_item in squad_data[0]["players"]:
                api_name = player_item["name"]
                
                # Clean API name (strip accents, lowercase)
                clean_api_name = unidecode(api_name).lower()
                
                # Use fuzzy matching to find the closest name in the Kaggle list
                # process.extractOne returns a tuple: (Best Match String, Confidence Score)
                best_match = process.extractOne(clean_api_name, nation_match_names)
                
                if best_match and best_match[1] > 75: # 75% confidence threshold
                    # Find the player's overall rating in the dataframe
                    player_ovr = nation_df[nation_df["Match_Name"] == best_match[0]]["OVR"].values[0]
                    matched_ovr_scores.append(player_ovr)
            
            # Calculate the team's true rating based ONLY on matched players
            if matched_ovr_scores:
                # Sort and take the top 11 matched players to represent the starting strength
                matched_ovr_scores.sort(reverse=True)
                top_11 = matched_ovr_scores[:11]
                
                team_true_ovr = sum(top_11) / len(top_11)
                exact_team_ratings.append({
                    "team": team_name,
                    "exact_squad_rating": round(team_true_ovr, 1),
                    "players_matched": len(matched_ovr_scores)
                })
                print(f"{team_name}: Matched {len(matched_ovr_scores)} players -> True Rating: {team_true_ovr:.1f}")
            else:
                fallback_ratings = {
                    "Qatar": 75.0,
                }
                fallback_ovr = fallback_ratings.get(team_name, 70.0) 
                
                exact_team_ratings.append({
                    "team": team_name,
                    "exact_squad_rating": fallback_ovr,
                    "players_matched": 0
                })
                print(f"{team_name}: 0 players found (Licensing constraint). Applied Imputed Rating: {fallback_ovr}")
        # Save the final exact ratings
        final_df = pd.DataFrame(exact_team_ratings)
        output_path = self.processed_dir / "exact_team_ratings.csv"
        final_df.to_csv(output_path, index=False)
        print(f"\n✅ Success! Exact mappings saved to {output_path}")

if __name__ == "__main__":
    mapper = ExactRosterMapper()
    # We use our orchestrator to grab the list of teams we need to map
    orchestrator = DataOrchestrator()
    teams = orchestrator.fetch_2026_world_cup_teams()
    
    mapper.calculate_exact_squad_ratings(teams)