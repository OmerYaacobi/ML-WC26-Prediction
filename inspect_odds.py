import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def test_single_match():
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        print("❌ Error: ODDS_API_KEY not found in your .env file.")
        return

    base_url = "https://api.odds-api.io/v3"
    
    # ---------------------------------------------------------
    # STEP 1: Find the specific Mexico vs South Africa match
    # ---------------------------------------------------------
    print("📡 STEP 1: Searching for the Mexico vs South Africa event...")
    events_params = {
        "sport": "football",
        "apiKey": api_key
    }
    
    events_response = requests.get(f"{base_url}/events", params=events_params, timeout=10)
    
    if events_response.status_code != 200:
        print(f"❌ Events API Error: {events_response.text}")
        return
        
    all_events = events_response.json()
    target_event_id = None
    
    # Search for our specific match
    for event in all_events:
        home = event.get("home", "")
        away = event.get("away", "")
        
        if ("Mexico" in home or "Mexico" in away) and ("South Africa" in home or "South Africa" in away):
            target_event_id = event.get("id")
            print(f"✅ Found the match! Event ID: {target_event_id}")
            break

    if not target_event_id:
        print("⚠️ Could not find the Mexico vs South Africa match in the current live feed.")
        print("Let's just grab the very first football match in the list instead to test your keys.")
        target_event_id = all_events[0].get("id")
        print(f"Fallback Event ID: {target_event_id} ({all_events[0].get('home')} vs {all_events[0].get('away')})")

    # ---------------------------------------------------------
    # STEP 2: Fetch the odds for JUST that single match
    # ---------------------------------------------------------
    print("\n📡 STEP 2: Fetching Bet365 & DraftKings odds for this match...")
    print("=" * 70)
    
    odds_params = {
        "eventId": target_event_id,
        "bookmakers": "Bet365,DraftKings", # Using your exact dashboard selections!
        "apiKey": api_key
    }
    
    odds_response = requests.get(f"{base_url}/odds", params=odds_params, timeout=10)
    
    if odds_response.status_code == 200:
        odds_data = odds_response.json()
        
        # Print the raw JSON response beautifully so we can see exactly what the server gave us
        print("🔍 RAW API RESPONSE:")
        print(json.dumps(odds_data, indent=4))
        print("=" * 70)
        
    else:
        print(f"❌ Odds API Error ({odds_response.status_code}):")
        print(odds_response.text)

if __name__ == "__main__":
    test_single_match()