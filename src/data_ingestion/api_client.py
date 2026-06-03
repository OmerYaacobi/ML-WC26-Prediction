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
    client = FootballAPIClient()
    
    # 1. Fetch 2022 World Cup
    client.get_historical_fixtures(league_id=1, season=2022)
    
    # 2. Fetch 2024 Euros (League 4)
    client.get_historical_fixtures(league_id=4, season=2024)
    
    # 3. Fetch 2024 Copa América (League 9)
    client.get_historical_fixtures(league_id=9, season=2024)