import os
import json
import time
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def fetch_group_stage_safely():
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        print("❌ Error: ODDS_API_KEY not found.")
        return

    base_url = "https://api.odds-api.io/v3"
    raw_dir = Path(__file__).resolve().parent / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_file = raw_dir / "market_odds_group_stage.json"

    # ---------------------------------------------------------
    # STEP 0: Check the hard drive for existing data
    # ---------------------------------------------------------
    existing_data = []
    existing_ids = set()
    
    if output_file.exists():
        try:
            with open(output_file, "r") as f:
                existing_data = json.load(f)
                for item in existing_data:
                    # Some endpoints return lists, some return dicts. Safe extraction:
                    match_id = item.get("id") if isinstance(item, dict) else item[0].get("id")
                    if match_id:
                        existing_ids.add(match_id)
        except json.JSONDecodeError:
            pass

    if existing_ids:
        print(f"📂 Found {len(existing_ids)} matches already saved on your drive.")

    # ---------------------------------------------------------
    # STEP 1: Fetch ALL World Cup Events (Cost: 1 Request)
    # ---------------------------------------------------------
    print("📡 STEP 1: Querying active football events...")
    events_params = {"sport": "football", "apiKey": api_key}
    
    try:
        events_response = requests.get(f"{base_url}/events", params=events_params, timeout=15)
        events_response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch events list: {e}")
        return
        
    all_events = events_response.json()
    group_stage_events = []
    
    for event in all_events:
        league = str(event.get("league", {}).get("name", ""))
        home = str(event.get("home", ""))
        if "World Cup" in league and "W" not in home and "RU" not in home and "/" not in home:
             group_stage_events.append(event)
             
    group_stage_events = group_stage_events[:72]
    
    # Filter out the matches we already saved to the hard drive
    events_to_fetch = [e for e in group_stage_events if e.get("id") not in existing_ids]
    
    if not events_to_fetch:
        print("\n✅ All 72 group stage matches are already cached! You are done here.")
        return
        
    print(f"✅ Need to fetch odds for {len(events_to_fetch)} matches.")

    # ---------------------------------------------------------
    # STEP 2: Fetch odds 1-by-1 with a delay
    # ---------------------------------------------------------
    print("\n📡 STEP 2: Fetching odds match-by-match...")
    
    for i, event in enumerate(events_to_fetch, 1):
        event_id = event.get("id")
        home = event.get("home")
        away = event.get("away")
        
        print(f"[{i}/{len(events_to_fetch)}] Downloading {home} vs {away}...")
        
        odds_params = {
            "eventId": event_id,
            "bookmakers": "Bet365",
            "apiKey": api_key
        }
        
        try:
            # We give the server 15 seconds to reply to be super safe
            odds_response = requests.get(f"{base_url}/odds", params=odds_params, timeout=15)
            
            if odds_response.status_code == 429 or "exceeded" in odds_response.text:
                print("\n🛑 RATE LIMIT HIT! The script stopped safely.")
                print("Everything you downloaded so far is perfectly saved.")
                break

            if odds_response.status_code == 200:
                data = odds_response.json()
                
                # Tag the raw data with the event ID so we know we have it
                if isinstance(data, dict) and "id" not in data:
                    data["id"] = event_id
                elif isinstance(data, list) and len(data) > 0 and "id" not in data[0]:
                    data[0]["id"] = event_id

                existing_data.append(data)

                # SAVE IMMEDIATELY TO HARD DRIVE
                with open(output_file, "w") as f:
                    json.dump(existing_data, f, indent=4)
                    
            else:
                print(f"   ⚠️ API Error: {odds_response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ Network timeout. Skipping cleanly. Error: {e}")
            
        # The crucial pause so the server doesn't block us
        time.sleep(1.0) 

    print(f"\n✅ Run completed. {len(existing_data)} total matches safely saved to:")
    print(f"📁 {output_file}")

if __name__ == "__main__":
    fetch_group_stage_safely()