import json
import pandas as pd
from unidecode import unidecode
from thefuzz import process
from pathlib import Path

class ExactRosterMapper:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        
        # 1. The Official 48-Team 2026 Universe 
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

        # 2. Translation Dictionary for Database Mismatches
        self.nation_translation = {
            "Netherlands": "Holland",
            "South Korea": "Korea Republic",
            "United States": "United States",
            "Czechia": "Czech Republic",
            "Ivory Coast": "Côte d'Ivoire",
            "DR Congo": "Congo DR",
            "Cape Verde": "Cape Verde Islands",
            "Curacao": "Curaçao"
        }
        
    def load_kaggle_database(self):
        csv_path = self.raw_dir / "EAFC26-Men.csv"
        df = pd.read_csv(csv_path)
        df["Match_Name"] = df["Name"].astype(str).apply(lambda x: unidecode(x).lower())
        return df

    def find_local_squad_file(self, team_name):
        """Scans downloaded files to find a team's squad without needing their API ID."""
        for file_path in self.raw_dir.glob("squad_team_*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    if data and isinstance(data, list) and data[0]["team"]["name"] == team_name:
                        return file_path
            except Exception:
                continue
        return None

    def calculate_exact_squad_ratings(self):
        kaggle_df = self.load_kaggle_database()
        exact_team_ratings = []
        
        print(f"\n--- Locking Universe to {len(self.tournament_teams)} Official Teams ---")
        
        for team_name in self.tournament_teams:
            search_nation = self.nation_translation.get(team_name, team_name)
            nation_df = kaggle_df[kaggle_df["Nation"] == search_nation]
            
            squad_file = self.find_local_squad_file(team_name)
            
            # Scenario A: We have the API Squad AND the Kaggle Data
            if squad_file and not nation_df.empty:
                with open(squad_file, "r") as f:
                    squad_data = json.load(f)
                    
                nation_match_names = nation_df["Match_Name"].tolist()
                matched_ovr_scores = []
                
                for player_item in squad_data[0]["players"]:
                    clean_api_name = unidecode(player_item["name"]).lower()
                    best_match = process.extractOne(clean_api_name, nation_match_names)
                    
                    if best_match and best_match[1] > 75: 
                        player_ovr = nation_df[nation_df["Match_Name"] == best_match[0]]["OVR"].values[0]
                        matched_ovr_scores.append(player_ovr)
                        
                if matched_ovr_scores:
                    matched_ovr_scores.sort(reverse=True)
                    top_11 = sum(matched_ovr_scores[:11]) / len(matched_ovr_scores[:11])
                    exact_team_ratings.append({
                        "team": team_name,
                        "exact_squad_rating": round(top_11, 1),
                        "players_matched": len(matched_ovr_scores)
                    })
                    print(f"{team_name}: Matched {len(matched_ovr_scores)} players -> True Rating: {top_11:.1f}")
                    continue

            # Scenario B: Missing API Squad (Use Kaggle Baseline directly to save quota)
            if not nation_df.empty:
                top_11_kaggle = nation_df.sort_values(by="OVR", ascending=False).head(11)["OVR"].mean()
                exact_team_ratings.append({
                    "team": team_name,
                    "exact_squad_rating": round(top_11_kaggle, 1),
                    "players_matched": 0 
                })
                print(f"{team_name}: API Squad missing. Used Kaggle Base Rating -> {top_11_kaggle:.1f}")
            else:
                # Scenario C: Absolute Imputation (e.g., Qatar)
                fallback_ovr = 73.0 if team_name == "Qatar" else 70.0
                exact_team_ratings.append({
                    "team": team_name,
                    "exact_squad_rating": fallback_ovr,
                    "players_matched": 0
                })
                print(f"{team_name}: 0 players found. Applied Imputed Rating -> {fallback_ovr}")

        final_df = pd.DataFrame(exact_team_ratings)
        output_path = self.processed_dir / "exact_team_ratings.csv"
        final_df.to_csv(output_path, index=False)
        print(f"\n✅ Universe Locked! Exact mappings saved to {output_path}")

if __name__ == "__main__":
    mapper = ExactRosterMapper()
    mapper.calculate_exact_squad_ratings()