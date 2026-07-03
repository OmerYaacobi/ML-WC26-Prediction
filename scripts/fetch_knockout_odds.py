"""Fetch Bet365 odds for WC26 knockout fixtures via odds-api.io.

Incremental cache in data/raw/market_odds_knockout.json.
Re-fetches pending (upcoming) matches on each run so pre-match lines stay fresh.

    python scripts/fetch_knockout_odds.py
    python scripts/fetch_knockout_odds.py --no-refresh   # only fetch new events
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wc26_bracket import lookup_bracket
from wc26_groups import is_world_cup_league, normalize_team

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://api.odds-api.io/v3"
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "market_odds_knockout.json"


def _load_cache() -> tuple[list[dict], dict[str, dict]]:
    if not OUTPUT_FILE.exists():
        return [], {}
    try:
        data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], {}
    by_id: dict[str, dict] = {}
    for item in data:
        eid = str(item.get("id", ""))
        if eid:
            by_id[eid] = item
    return data, by_id


def _save_cache(data: list[dict]) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _is_knockout_event(event: dict) -> bool:
    league = str(event.get("league", {}).get("name", ""))
    if not is_world_cup_league(league):
        return False
    home = normalize_team(str(event.get("home", "")))
    away = normalize_team(str(event.get("away", "")))
    if not home or not away:
        return False
    return lookup_bracket(home, away) is not None


def _fetch_odds(api_key: str, event_id: str) -> dict | None:
    try:
        response = requests.get(
            f"{BASE_URL}/odds",
            params={"eventId": event_id, "bookmakers": "Bet365", "apiKey": api_key},
            timeout=15,
        )
        if response.status_code == 429 or "exceeded" in response.text:
            print("🛑 Rate limit hit — stopping (partial cache saved).")
            return None
        if response.status_code != 200:
            print(f"   ⚠️ API {response.status_code}: {response.text[:120]}")
            return None
        data = response.json()
        if isinstance(data, dict) and "id" not in data:
            data["id"] = event_id
        return data
    except requests.RequestException as exc:
        print(f"   ⚠️ Network error: {exc}")
        return None


def fetch_knockout_odds(*, refresh_pending: bool = True) -> int:
    load_dotenv()
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        print("❌ ODDS_API_KEY not set")
        return 0

    print("📡 Listing football events for WC26 knockout...")
    try:
        response = requests.get(
            f"{BASE_URL}/events",
            params={"sport": "football", "apiKey": api_key},
            timeout=15,
        )
        response.raise_for_status()
        all_events = response.json()
    except Exception as exc:
        print(f"❌ Failed to list events: {exc}")
        return 0

    ko_events = [e for e in all_events if _is_knockout_event(e)]
    print(f"   Found {len(ko_events)} knockout bracket matches on the book")

    cached_list, cached_by_id = _load_cache()
    fetched = 0

    for i, event in enumerate(ko_events, 1):
        event_id = str(event.get("id", ""))
        home = event.get("home")
        away = event.get("away")
        status = event.get("status", "pending")
        in_cache = event_id in cached_by_id

        if in_cache and not refresh_pending:
            continue
        if in_cache and refresh_pending and status == "settled":
            continue

        label = "refresh" if in_cache else "new"
        print(f"[{i}/{len(ko_events)}] {label}: {home} vs {away} (id={event_id})...")
        odds = _fetch_odds(api_key, event_id)
        if odds is None:
            break

        if in_cache:
            for idx, item in enumerate(cached_list):
                if str(item.get("id", "")) == event_id:
                    cached_list[idx] = odds
                    break
        else:
            cached_list.append(odds)

        cached_by_id[event_id] = odds
        _save_cache(cached_list)
        fetched += 1
        time.sleep(1.0)

    print(f"\n✅ {len(cached_list)} knockout matches cached ({fetched} fetched this run)")
    print(f"📁 {OUTPUT_FILE}")
    return fetched


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Bet365 odds for WC26 knockout fixtures")
    parser.add_argument("--no-refresh", action="store_true", help="Skip re-fetching pending matches")
    args = parser.parse_args()
    fetch_knockout_odds(refresh_pending=not args.no_refresh)


if __name__ == "__main__":
    main()
