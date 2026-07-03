import json
import pandas as pd
from pathlib import Path

# Bookmaker / API spellings → model team names (docs/data.js keys)
ODDS_TEAM_ALIASES = {
    "USA": "United States",
    "Korea Republic": "South Korea",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Curaçao": "Curacao",
    "Czech Republic": "Czechia",
    "Cote d'Ivoire": "Ivory Coast",
    "Congo DR": "DR Congo",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
}


def _map_odds_team(name: str) -> str:
    return ODDS_TEAM_ALIASES.get(str(name), str(name))


class MarketOddsLoader:
    def __init__(self):
        self.raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
        self.group_odds_file = self.raw_dir / "market_odds_group_stage.json"
        self.knockout_odds_file = self.raw_dir / "market_odds_knockout.json"

    def _parse_match(self, match: dict, stage: str) -> list[dict]:
        home_team = _map_odds_team(match.get("home", ""))
        away_team = _map_odds_team(match.get("away", ""))
        bet365_markets = match.get("bookmakers", {}).get("Bet365", [])

        ml_market = next((m for m in bet365_markets if m.get("name") == "ML"), None)
        home_prob, away_prob = 0.33, 0.33
        if ml_market and ml_market.get("odds"):
            odds = ml_market["odds"][0]
            home_prob = 1 / float(odds.get("home", 3.0))
            away_prob = 1 / float(odds.get("away", 3.0))

        cs_market = next((m for m in bet365_markets if m.get("name") == "Correct Score"), None)
        home_proj_g, away_proj_g = 1.0, 1.0
        if cs_market and cs_market.get("odds"):
            best_cs = min(cs_market["odds"], key=lambda x: float(x.get("odds", 999)))
            favored_score = best_cs.get("label", "0-0")
            if "-" in favored_score:
                try:
                    hg, ag = favored_score.split("-")
                    home_proj_g = float(hg)
                    away_proj_g = float(ag)
                except ValueError:
                    pass

        ou_market = next((m for m in bet365_markets if m.get("name") == "Goals Over/Under"), None)
        over_25_prob = 0.5
        if ou_market and ou_market.get("odds"):
            for outcome in ou_market["odds"]:
                if outcome.get("hdp") == 2.5:
                    over_25_prob = 1 / float(outcome.get("over", 2.0))
                    break

        btts_market = next((m for m in bet365_markets if m.get("name") == "Both Teams To Score"), None)
        btts_prob = 0.5
        if btts_market and btts_market.get("odds"):
            btts_prob = 1 / float(btts_market["odds"][0].get("yes", 2.0))

        home_multiplier = round(0.7 + (home_prob * 0.6), 3)
        away_multiplier = round(0.7 + (away_prob * 0.6), 3)

        return [
            {
                "team": home_team,
                "market_active": home_multiplier,
                "market_win_prob": round(home_prob, 3),
                "market_proj_gf": home_proj_g,
                "market_proj_ga": away_proj_g,
                "market_btts_prob": round(btts_prob, 3),
                "market_over_25_prob": round(over_25_prob, 3),
                "odds_stage": stage,
            },
            {
                "team": away_team,
                "market_active": away_multiplier,
                "market_win_prob": round(away_prob, 3),
                "market_proj_gf": away_proj_g,
                "market_proj_ga": home_proj_g,
                "market_btts_prob": round(btts_prob, 3),
                "market_over_25_prob": round(over_25_prob, 3),
                "odds_stage": stage,
            },
        ]

    def _load_file(self, path: Path, stage: str) -> list[dict]:
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        records: list[dict] = []
        for match in raw_data:
            records.extend(self._parse_match(match, stage))
        return records

    def fetch_live_odds(self):
        """Reads cached group + knockout JSON; knockout lines override group for each team."""
        records = self._load_file(self.group_odds_file, "group")
        records.extend(self._load_file(self.knockout_odds_file, "knockout"))

        if not records:
            print("⚠️ MarketOddsLoader: no odds cache found (group or knockout).")
            return pd.DataFrame()

        df = pd.DataFrame(records).drop_duplicates(subset=["team"], keep="last")
        ko_teams = (df["odds_stage"] == "knockout").sum()
        print(
            f"✅ MarketOddsLoader: {len(df)} teams "
            f"({ko_teams} from knockout odds, rest from group stage)."
        )
        return df.set_index("team").drop(columns=["odds_stage"], errors="ignore")
