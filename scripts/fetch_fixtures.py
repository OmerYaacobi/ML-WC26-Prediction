"""Fetch real WC26 group-stage fixtures + scores from odds-api.io.

Writes data/processed/wc26_fixtures.json. Run before publishing the web app:

    python scripts/fetch_fixtures.py
    python scripts/publish_fixtures.py

Requires ODDS_API_KEY in .env (same key as fetch_group_odds.py).
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wc26_groups import TEAM_TO_GROUP, is_group_stage_league, normalize_team

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "wc26_fixtures.json"
BASE_URL = "https://api.odds-api.io/v3"


def assign_matchdays(fixtures: list[dict]) -> None:
    """Within each group, earliest two kickoffs = MD1, next two = MD2, last two = MD3."""
    by_group: dict[str, list[dict]] = defaultdict(list)
    for fx in fixtures:
        by_group[fx["group"]].append(fx)
    for group_fixtures in by_group.values():
        group_fixtures.sort(key=lambda f: f["kickoff"])
        for i, fx in enumerate(group_fixtures):
            fx["md"] = min(3, i // 2 + 1)


def parse_fixture(event: dict) -> dict | None:
    league = str(event.get("league", {}).get("name", ""))
    if not is_group_stage_league(league):
        return None

    home = normalize_team(str(event.get("home", "")))
    away = normalize_team(str(event.get("away", "")))
    if not home or not away or home == away:
        return None

    kickoff = event.get("date") or ""
    status = (event.get("status") or "pending").lower()
    scores = event.get("scores")
    home_score = away_score = None
    if isinstance(scores, dict):
        ft = (scores.get("periods") or {}).get("ft")
        if isinstance(ft, dict):
            home_score = ft.get("home")
            away_score = ft.get("away")
        if home_score is None and scores.get("home") is not None:
            home_score = scores.get("home")
            away_score = scores.get("away")

    bettable = status == "pending"
    if kickoff and status == "pending":
        try:
            kickoff_dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            if kickoff_dt <= datetime.now(timezone.utc):
                bettable = False
        except ValueError:
            pass

    return {
        "id": event.get("id"),
        "home": home,
        "away": away,
        "group": TEAM_TO_GROUP[home],
        "kickoff": kickoff,
        "status": status,
        "homeScore": home_score,
        "awayScore": away_score,
        "bettable": bettable,
        "league": league,
    }


def fetch_events(api_key: str) -> list[dict]:
    response = requests.get(
        f"{BASE_URL}/events",
        params={"sport": "football", "apiKey": api_key},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def write_empty(reason: str) -> None:
    payload = {
        "source": "empty",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "fixtures": [],
        "note": reason,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"⚠️  {reason}")


def main() -> None:
    load_dotenv()
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        write_empty("ODDS_API_KEY not set — add it to GitHub Secrets or .env")
        sys.exit(1)

    print("📡 Fetching football events from odds-api.io...")
    try:
        events = fetch_events(api_key)
    except Exception as e:
        write_empty(f"API fetch failed: {e}")
        sys.exit(1)
    fixtures = []
    seen = set()

    for event in events:
        fx = parse_fixture(event)
        if not fx:
            continue
        key = (fx["home"], fx["away"], fx["kickoff"])
        if key in seen:
            continue
        seen.add(key)
        fixtures.append(fx)

    fixtures.sort(key=lambda f: (f["kickoff"], f["group"], f["home"]))
    assign_matchdays(fixtures)

    payload = {
        "source": "api" if fixtures else "empty",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "fixtures": fixtures,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✅ Saved {len(fixtures)} group-stage fixtures → {OUTPUT_PATH}")

    if fixtures:
        settled = sum(1 for f in fixtures if f["status"] == "settled")
        pending = sum(1 for f in fixtures if f["bettable"])
        print(f"   {settled} finished · {pending} open for betting")
    else:
        print("⚠️  No World Cup group-stage events in the feed yet.")
        print("   publish_fixtures.py will fall back to the model schedule until API lists them.")

    from update_results_csv import update_csv

    update_csv()


if __name__ == "__main__":
    main()
