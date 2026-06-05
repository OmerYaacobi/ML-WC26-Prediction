import json
import pandas as pd
from pathlib import Path

class MarketOddsLoader:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.odds_file = self.raw_dir / "market_odds_group_stage.json"

    def fetch_live_odds(self):
        """Reads the cached JSON, extracts ML, Correct Score, Over/Under, and BTTS."""
        if not self.odds_file.exists():
            print("⚠️ MarketOddsLoader: JSON file not found.")
            return pd.DataFrame()

        with open(self.odds_file, "r") as f:
            raw_data = json.load(f)

        market_records = []

        for match in raw_data:
            home_team = match.get("home")
            away_team = match.get("away")
            bet365_markets = match.get("bookmakers", {}).get("Bet365", [])
            
            # --- 1. MONEYLINE (Win Probability) ---
            ml_market = next((m for m in bet365_markets if m.get("name") == "ML"), None)
            home_prob, away_prob = 0.33, 0.33
            if ml_market and ml_market.get("odds"):
                odds = ml_market["odds"][0]
                home_prob = 1 / float(odds.get("home", 3.0))
                away_prob = 1 / float(odds.get("away", 3.0))

            # --- 2. CORRECT SCORE (Most Likely Scoreline) ---
            cs_market = next((m for m in bet365_markets if m.get("name") == "Correct Score"), None)
            home_proj_g, away_proj_g = 1.0, 1.0 # Fallbacks
            
            if cs_market and cs_market.get("odds"):
                # Find the exact score label with the lowest odds (highest probability)
                best_cs = min(cs_market["odds"], key=lambda x: float(x.get("odds", 999)))
                favored_score = best_cs.get("label", "0-0")
                
                # Extract the goals from the string (e.g. "1-0" -> 1 and 0)
                if "-" in favored_score:
                    try:
                        hg, ag = favored_score.split("-")
                        home_proj_g = float(hg)
                        away_proj_g = float(ag)
                    except ValueError:
                        pass

            # --- 3. OVER/UNDER 2.5 GOALS (Match Tempo) ---
            ou_market = next((m for m in bet365_markets if m.get("name") == "Goals Over/Under"), None)
            over_25_prob = 0.5
            if ou_market and ou_market.get("odds"):
                for outcome in ou_market["odds"]:
                    if outcome.get("hdp") == 2.5: # Standard 2.5 goal line
                        over_25_prob = 1 / float(outcome.get("over", 2.0))
                        break

            # --- 4. BOTH TEAMS TO SCORE (Clean Sheet Tracker) ---
            btts_market = next((m for m in bet365_markets if m.get("name") == "Both Teams To Score"), None)
            btts_prob = 0.5
            if btts_market and btts_market.get("odds"):
                btts_prob = 1 / float(btts_market["odds"][0].get("yes", 2.0))

            # Generate the unified multiplier (Base strength)
            home_multiplier = round(0.7 + (home_prob * 0.6), 3)
            away_multiplier = round(0.7 + (away_prob * 0.6), 3)

            # Build rich feature rows for both teams
            market_records.append({
                "team": home_team, 
                "market_active": home_multiplier,
                "market_win_prob": round(home_prob, 3),
                "market_proj_gf": home_proj_g,
                "market_proj_ga": away_proj_g,
                "market_btts_prob": round(btts_prob, 3),
                "market_over_25_prob": round(over_25_prob, 3)
            })

            market_records.append({
                "team": away_team, 
                "market_active": away_multiplier,
                "market_win_prob": round(away_prob, 3),
                "market_proj_gf": away_proj_g,
                "market_proj_ga": home_proj_g,  # Away GA is Home GF
                "market_btts_prob": round(btts_prob, 3),
                "market_over_25_prob": round(over_25_prob, 3)
            })

        df = pd.DataFrame(market_records).drop_duplicates(subset=["team"])
        print(f"✅ MarketOddsLoader: Extracted Advanced Market Matrix for {len(df)} teams.")
        return df.set_index("team")