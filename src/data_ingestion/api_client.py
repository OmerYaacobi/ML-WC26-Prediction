import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from the .env file
load_dotenv()

class FootballAPIClient:
    """
    A client to interact with the API-Sports Football API.
    Handles authentication, request execution, and raw data storage.
    """
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self):
        self.api_key = os.getenv("API_SPORTS_KEY")
        if not self.api_key:
            raise ValueError("API_SPORTS_KEY not found in environment variables.")
        
        self.headers = {
            "x-apisports-key": self.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        
        # Ensure the raw data directory exists
        self.raw_data_dir = Path("data/raw")
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    def _make_request(self, endpoint, params=None):
        """Internal method to handle the GET requests and error handling."""
        url = f"{self.BASE_URL}/{endpoint}"
        print(f"Fetching data from: {endpoint}...")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # API-Sports usually returns errors inside the JSON response itself
            if data.get("errors"):
                print(f"API Error: {data['errors']}")
                return None
                
            return data["response"]
            
        except requests.exceptions.RequestException as e:
            print(f"HTTP Request failed: {e}")
            return None

    def get_historical_fixtures(self, league_id, season, save_to_disk=True):
        """
        Fetches all fixtures and results for a specific league and season.
        World Cup is usually league_id 1.
        """
        params = {
            "league": league_id,
            "season": season
        }
        
        data = self._make_request("fixtures", params=params)
        
        if data and save_to_disk:
            filename = self.raw_data_dir / f"fixtures_league_{league_id}_{season}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
            print(f"Successfully saved {len(data)} fixtures to {filename}")
            
        return data
    
    def search_team_id(self, team_name):
        """Searches the API for a specific national team to get their ID."""
        params = {"search": team_name}
        data = self._make_request("teams", params=params)
        
        if data:
            # Ensure we only grab the 'National' team to avoid local clubs with similar names
            for item in data:
                if item["team"]["national"] == True:
                    return item["team"]["id"]
                    
        print(f"Could not find a national team ID for '{team_name}'")
        return None
    
    def get_team_squad(self, team_id):
        """Fetches the current roster/squad for a specific team."""
        params = {"team": team_id}
        data = self._make_request("players/squads", params=params)
        
        if data:
            filename = self.raw_data_dir / f"squad_team_{team_id}.json"
            with open(filename, "w") as f:
                import json
                json.dump(data, f, indent=4)
            print(f"Saved squad data for Team {team_id}")
        return data

    def get_fixture_injuries(self, fixture_id):
        """Fetches the list of injured/unavailable players for a specific match."""
        params = {"fixture": fixture_id}
        data = self._make_request("injuries", params=params)
        
        if data:
            filename = self.raw_data_dir / f"injuries_fixture_{fixture_id}.json"
            with open(filename, "w") as f:
                import json
                json.dump(data, f, indent=4)
        return data

if __name__ == "__main__":
    import time  # Imported locally here so you don't have to scroll to the top
    
    client = FootballAPIClient()
    
    print("🚀 Starting Main Data Ingestion Script...\n")
    
    # 1. Fetch Core Historical Tournaments
    print("--- Fetching Major Tournaments ---")
    client.get_historical_fixtures(league_id=1, season=2022) # 2022 WC
    time.sleep(6.5)
    
    client.get_historical_fixtures(league_id=4, season=2024) # 2024 Euros
    time.sleep(6.5)
    
    client.get_historical_fixtures(league_id=9, season=2024) # 2024 Copa América
    time.sleep(6.5)

    # 2. Fetch All 2026 World Cup Qualifier Regions
    print("\n--- Fetching 2026 World Cup Qualifiers ---")
    qualifier_leagues = {
        "CONMEBOL": {"id": 30, "season": 2023},  # South America started in 2023
        "CONCACAF": {"id": 31, "season": 2024},  # North/Central America
        "UEFA": {"id": 32, "season": 2025},      # Europe 
        "CAF": {"id": 33, "season": 2023},       # Africa
        "AFC": {"id": 34, "season": 2023},       # Asia
        "OFC": {"id": 35, "season": 2024}        # Oceania
    }

    for region, config in qualifier_leagues.items():
        print(f"Syncing qualifier data for {region}...")
        client.get_historical_fixtures(league_id=config["id"], season=config["season"])
        
        # Pause to safeguard against 429 rate limit errors
        print("Waiting 6.5 seconds...")
        time.sleep(6.5)

    print("\n✅ All historical match assets successfully downloaded to data/raw/")