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
from fixture_status import normalize_fixture
from wc26_bracket import lookup_bracket, merge_knockout_fixtures, ROUND_LABELS
from wc26_groups import (
    TEAM_TO_GROUP,
    is_group_stage_league,
    is_knockout_league,
    is_world_cup_league,
    normalize_team,
    parse_knockout_round,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "wc26_fixtures.json"
ARCHIVE_PATH = PROJECT_ROOT / "data" / "wc26_finished_archive.json"
BASE_URL = "https://api.odds-api.io/v3"
WC_LEAGUE_SLUG = "international-fifa-world-cup"
# Settled games vanish from /events; historical feed keeps results (max 31 days per request).
HISTORICAL_RANGES = (
    ("2026-06-11T00:00:00Z", "2026-07-11T23:59:59Z"),
    ("2026-07-12T00:00:00Z", "2026-07-20T23:59:59Z"),
)


def assign_matchdays(fixtures: list[dict]) -> None:
    """Within each group, earliest two kickoffs = MD1, next two = MD2, last two = MD3."""
    group_fixtures = [
        fx
        for fx in fixtures
        if fx.get("stage") != "knockout" and not lookup_bracket(fx.get("home", ""), fx.get("away", ""))
    ]
    by_group: dict[str, list[dict]] = defaultdict(list)
    for fx in group_fixtures:
        by_group[fx["group"]].append(fx)
    for fixtures_in_group in by_group.values():
        fixtures_in_group.sort(key=lambda f: f["kickoff"])
        for i, fx in enumerate(fixtures_in_group):
            fx["md"] = min(3, i // 2 + 1)


def parse_knockout_fixture(event: dict) -> dict | None:
    league = str(event.get("league", {}).get("name", ""))
    home = normalize_team(str(event.get("home", "")))
    away = normalize_team(str(event.get("away", "")))
    if not home or not away or home == away:
        return None
    bracket = lookup_bracket(home, away)
    if not (is_knockout_league(league) or (bracket and is_world_cup_league(league))):
        return None

    kickoff = event.get("date") or ""
    raw_status = event.get("status") or "pending"
    norm = normalize_fixture(raw_status, kickoff, event.get("scores"))
    ko_round = parse_knockout_round(league)
    if ko_round == "Knockout" and bracket:
        ko_round = ROUND_LABELS.get(bracket["round"], ko_round)

    return {
        "id": event.get("id"),
        "home": home,
        "away": away,
        "stage": "knockout",
        "round": ko_round,
        "bracketRound": bracket["round"] if bracket else None,
        "matchNo": bracket["matchNo"] if bracket else None,
        "kickoff": kickoff,
        "status": norm["status"],
        "homeScore": norm["homeScore"],
        "awayScore": norm["awayScore"],
        "bettable": norm["bettable"],
        "league": league,
    }


def parse_fixture(event: dict) -> dict | None:
    league = str(event.get("league", {}).get("name", ""))
    home = normalize_team(str(event.get("home", "")))
    away = normalize_team(str(event.get("away", "")))
    # API lists R32 under generic "FIFA World Cup" — detect via bracket pair.
    if home and away and lookup_bracket(home, away) and is_world_cup_league(league):
        return parse_knockout_fixture(event)
    if is_knockout_league(league):
        return parse_knockout_fixture(event)
    if not is_group_stage_league(league):
        return None
    if not home or not away or home == away:
        return None

    kickoff = event.get("date") or ""
    raw_status = event.get("status") or "pending"
    norm = normalize_fixture(raw_status, kickoff, event.get("scores"))

    return {
        "id": event.get("id"),
        "home": home,
        "away": away,
        "stage": "group",
        "group": TEAM_TO_GROUP[home],
        "kickoff": kickoff,
        "status": norm["status"],
        "homeScore": norm["homeScore"],
        "awayScore": norm["awayScore"],
        "bettable": norm["bettable"],
        "league": league,
    }


def fetch_events(api_key: str) -> list[dict]:
    """Fetch pending, live, and settled events; merge with the live-only feed."""
    by_id: dict[int, dict] = {}

    response = requests.get(
        f"{BASE_URL}/events",
        params={"sport": "football", "apiKey": api_key, "status": "pending,live,settled"},
        timeout=30,
    )
    response.raise_for_status()
    for event in response.json():
        eid = event.get("id")
        if eid is not None:
            by_id[eid] = event

    live_resp = requests.get(
        f"{BASE_URL}/events/live",
        params={"sport": "football", "apiKey": api_key},
        timeout=30,
    )
    live_resp.raise_for_status()
    for event in live_resp.json():
        eid = event.get("id")
        if eid is not None:
            by_id[eid] = event

    for event in fetch_historical_events(api_key):
        eid = event.get("id")
        if eid is not None:
            by_id[eid] = event

    return list(by_id.values())


def fetch_historical_events(api_key: str) -> list[dict]:
    """Fetch settled WC results dropped from the live /events feed."""
    by_id: dict[int, dict] = {}
    for date_from, date_to in HISTORICAL_RANGES:
        response = requests.get(
            f"{BASE_URL}/historical/events",
            params={
                "sport": "football",
                "apiKey": api_key,
                "league": WC_LEAGUE_SLUG,
                "from": date_from,
                "to": date_to,
            },
            timeout=30,
        )
        response.raise_for_status()
        for event in response.json():
            eid = event.get("id")
            if eid is not None:
                by_id[eid] = event
    return list(by_id.values())


def load_finished_archive() -> list[dict]:
    if not ARCHIVE_PATH.exists():
        return []
    try:
        data = json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))
        return [f for f in data.get("fixtures", []) if f.get("status") == "settled"]
    except (json.JSONDecodeError, OSError):
        return []


def save_finished_archive(fixtures: list[dict]) -> None:
    settled = [f for f in fixtures if f.get("status") == "settled"]
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PATH.write_text(json.dumps({"fixtures": settled}, indent=2), encoding="utf-8")


def merge_retained_finished(new_fixtures: list[dict], retained_sources: list[list[dict]]) -> list[dict]:
    """Keep finished games when the API drops them from the feed."""
    by_pair = {(f["home"], f["away"]): f for f in new_fixtures}
    extra: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for source in retained_sources:
        for fx in source:
            if fx.get("status") != "settled":
                continue
            pair = (fx["home"], fx["away"])
            if pair in by_pair or pair in seen:
                continue
            seen.add(pair)
            extra.append(fx)
            by_pair[pair] = fx

    if not extra:
        return new_fixtures

    merged = new_fixtures + extra
    merged.sort(key=lambda f: (f.get("kickoff") or "", f.get("group", ""), f.get("home", "")))
    return merged


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

    print("📡 Fetching football events from odds-api.io (live + historical)...")
    previous_fixtures: list[dict] = []
    if OUTPUT_PATH.exists():
        try:
            previous_fixtures = json.loads(OUTPUT_PATH.read_text(encoding="utf-8")).get("fixtures", [])
        except (json.JSONDecodeError, OSError):
            previous_fixtures = []

    try:
        events = fetch_events(api_key)
    except Exception as e:
        if previous_fixtures:
            print(f"⚠️  API fetch failed ({e}) — keeping {len(previous_fixtures)} cached fixtures")
            fixtures = merge_knockout_fixtures(previous_fixtures)
            assign_matchdays(fixtures)
            payload = {
                "source": "api",
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "fixtures": fixtures,
                "note": f"stale: {e}",
            }
            OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return
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

    fixtures = merge_retained_finished(fixtures, [previous_fixtures, load_finished_archive()])
    fixtures = merge_knockout_fixtures(fixtures)
    fixtures.sort(key=lambda f: (f.get("kickoff") or "", f.get("stage", ""), f.get("group", ""), f.get("round", ""), f.get("home", "")))
    assign_matchdays(fixtures)
    save_finished_archive(fixtures)

    payload = {
        "source": "api" if fixtures else "empty",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "fixtures": fixtures,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✅ Saved {len(fixtures)} fixtures → {OUTPUT_PATH}")
    group_n = sum(1 for f in fixtures if f.get("stage") != "knockout")
    ko_n = len(fixtures) - group_n

    if fixtures:
        settled = sum(1 for f in fixtures if f["status"] == "settled")
        pending = sum(1 for f in fixtures if f["bettable"])
        print(f"   {settled} finished · {pending} open for betting · {group_n} group · {ko_n} knockout")
    else:
        print("⚠️  No World Cup group-stage events in the feed yet.")
        print("   publish_fixtures.py will fall back to the model schedule until API lists them.")

    from update_results_csv import main as update_results_main

    update_results_main()


if __name__ == "__main__":
    main()
