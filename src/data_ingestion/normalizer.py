import json
import pandas as pd
from pathlib import Path

class DataNormalizer:
    def __init__(self):
        # Dynamically lock onto project directories
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.processed_dir = Path(__file__).resolve().parents[2] / "data" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def parse_api_sports_fixtures(self, file_path, tournament_name):
        """Parses the deeply nested JSON structure from API-Sports into a clean table."""
        with open(file_path, "r") as f:
            raw_data = json.load(f)
            
        normalized_matches = []
        
        for item in raw_data:
            # Skip matches that haven't been played yet or don't have full-time scores
            if item["fixture"]["status"]["short"] != "FT" and item["fixture"]["status"]["short"] != "AET":
                continue
                
            match_info = {
                "match_id": f"{tournament_name.lower().replace(' ', '_')}_{item['fixture']['id']}",
                "date": item["fixture"]["date"][:10], # Keep just YYYY-MM-DD
                "tournament": tournament_name,
                "home_team": item["teams"]["home"]["name"],
                "away_team": item["teams"]["away"]["name"],
                "home_score": item["goals"]["home"],
                "away_score": item["goals"]["away"],
                "source": "api-sports"
            }
            normalized_matches.append(match_info)
            
        return pd.DataFrame(normalized_matches)

    def compile_all_sources(self):
        """Finds all raw files, normalizes them, and glues them into one giant training table."""
        all_dfs = []
        
        # Mapping files to our tournament naming system
        target_files = [
            ("fixtures_league_1_2022.json", "World Cup"),
            ("fixtures_league_4_2024.json", "Euros"),
            ("fixtures_league_9_2024.json", "Copa America")
        ]
        
        for filename, tournament in target_files:
            file_path = self.raw_dir / filename
            if file_path.exists():
                print(f"Normalizing {filename}...")
                df = self.parse_api_sports_fixtures(file_path, tournament)
                all_dfs.append(df)
            else:
                print(f"Warning: {filename} not found. Skipping.")
                
        if all_dfs:
            # Combine all matches into one unified master DataFrame
            master_df = pd.concat(all_dfs, ignore_index=True)
            
            # Save out to data/processed for our ML models to use
            output_path = self.processed_dir / "normalized_matches.csv"
            master_df.to_csv(output_path, index=False)
            print(f"Success! Saved {len(master_df)} normalized matches to {output_path}")
        else:
            print("No data files were processed.")

if __name__ == "__main__":
    normalizer = DataNormalizer()
    normalizer.compile_all_sources()
