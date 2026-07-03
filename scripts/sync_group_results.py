"""Sync WC26 group + knockout scores into results.csv and rebuild model ratings.

Sources (merged, later wins on conflict):
  1. odds-api.io historical feed (Jun 11 – Jul 20)
  2. data/processed/wc26_fixtures.json
  3. docs/fixtures.json
  4. data/wc26_finished_archive.json
  5. Manual fallbacks for API gaps

Then recomputes blended features and docs/data.js.

    python scripts/sync_group_results.py
    python scripts/sync_group_results.py --no-rebuild   # CSV only
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wc26_bracket import lookup_bracket
from wc26_groups import (
    is_group_stage_league,
    is_knockout_league,
    is_world_cup_league,
    normalize_team,
    to_csv_team,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = PROJECT_ROOT / "data" / "raw" / "results.csv"
FIXTURES_PATH = PROJECT_ROOT / "data" / "processed" / "wc26_fixtures.json"
DOCS_FIXTURES_PATH = PROJECT_ROOT / "docs" / "fixtures.json"
ARCHIVE_PATH = PROJECT_ROOT / "data" / "wc26_finished_archive.json"
HISTORICAL_URL = "https://api.odds-api.io/v3/historical/events"
COLUMNS = ["date", "home_team", "away_team", "home_score", "away_score", "tournament", "city", "country", "neutral"]

# Verified group-stage results not returned by odds-api.io historical feed
MANUAL_GROUP_RESULTS: list[dict] = [
    {"date": "2026-06-22", "home": "France", "away": "Iraq", "home_score": 3, "away_score": 0, "stage": "group"},
    {"date": "2026-06-24", "home": "Canada", "away": "Switzerland", "home_score": 1, "away_score": 2, "stage": "group"},
    {"date": "2026-06-24", "home": "Mexico", "away": "Czech Republic", "home_score": 3, "away_score": 0, "stage": "group"},
    {"date": "2026-06-25", "home": "United States", "away": "Turkey", "home_score": 2, "away_score": 3, "stage": "group"},
    {"date": "2026-06-27", "home": "Algeria", "away": "Austria", "home_score": 3, "away_score": 3, "stage": "group"},
    {"date": "2026-06-27", "home": "Jordan", "away": "Argentina", "home_score": 1, "away_score": 3, "stage": "group"},
]

HISTORICAL_RANGES = (
    ("2026-06-11T00:00:00Z", "2026-07-11T23:59:59Z"),
    ("2026-07-12T00:00:00Z", "2026-07-20T23:59:59Z"),
)


def _is_bracket_knockout(home: str, away: str) -> bool:
    return lookup_bracket(home, away) is not None


def kickoff_date(iso: str) -> str:
    return (iso or "")[:10]


def _score_row(fx: dict, home: str, away: str, stage: str) -> dict | None:
    hs, aws = fx.get("homeScore"), fx.get("awayScore")
    if hs is None or aws is None:
        return None
    return {
        "date": kickoff_date(fx.get("kickoff", "")),
        "home": to_csv_team(home),
        "away": to_csv_team(away),
        "home_score": int(hs),
        "away_score": int(aws),
        "stage": stage,
    }


def parse_fixture_row(fx: dict, *, knockout: bool = False) -> dict | None:
    if fx.get("status") != "settled":
        return None
    home = normalize_team(str(fx.get("home", "")))
    away = normalize_team(str(fx.get("away", "")))
    if not home or not away:
        return None
    is_ko = fx.get("stage") == "knockout" or bool(fx.get("bracketRound")) or _is_bracket_knockout(home, away)
    if knockout and not is_ko:
        return None
    if not knockout and is_ko:
        return None
    stage = "knockout" if is_ko else "group"
    return _score_row(fx, home, away, stage)


def parse_api_event(event: dict) -> dict | None:
    league = str(event.get("league", {}).get("name", ""))
    if not is_group_stage_league(league):
        return None
    if event.get("status") != "settled":
        return None
    scores = event.get("scores") or {}
    ft = (scores.get("periods") or {}).get("ft") or scores
    hs, aws = ft.get("home"), ft.get("away")
    if hs is None or aws is None:
        return None
    home = normalize_team(str(event.get("home", "")))
    away = normalize_team(str(event.get("away", "")))
    if not home or not away or _is_bracket_knockout(home, away):
        return None
    return {
        "date": kickoff_date(event.get("date", "")),
        "home": to_csv_team(home),
        "away": to_csv_team(away),
        "home_score": int(hs),
        "away_score": int(aws),
        "stage": "group",
    }


def parse_knockout_api_event(event: dict) -> dict | None:
    league = str(event.get("league", {}).get("name", ""))
    if not is_world_cup_league(league):
        return None
    if event.get("status") != "settled":
        return None
    scores = event.get("scores") or {}
    ft = (scores.get("periods") or {}).get("ft") or scores
    hs, aws = ft.get("home"), ft.get("away")
    if hs is None or aws is None:
        return None
    home = normalize_team(str(event.get("home", "")))
    away = normalize_team(str(event.get("away", "")))
    if not home or not away:
        return None
    if not (is_knockout_league(league) or _is_bracket_knockout(home, away)):
        return None
    return {
        "date": kickoff_date(event.get("date", "")),
        "home": to_csv_team(home),
        "away": to_csv_team(away),
        "home_score": int(hs),
        "away_score": int(aws),
        "stage": "knockout",
    }


def load_json_fixtures(path: Path, *, knockout: bool = False) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    fixtures = data.get("fixtures", data if isinstance(data, list) else [])
    out = []
    for fx in fixtures:
        row = parse_fixture_row(fx, knockout=knockout)
        if row:
            out.append(row)
    return out


def fetch_historical(api_key: str) -> tuple[list[dict], list[dict]]:
    group_rows: list[dict] = []
    ko_rows: list[dict] = []
    seen: set[int] = set()
    try:
        for date_from, date_to in HISTORICAL_RANGES:
            response = requests.get(
                HISTORICAL_URL,
                params={
                    "sport": "football",
                    "apiKey": api_key,
                    "league": "international-fifa-world-cup",
                    "from": date_from,
                    "to": date_to,
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                continue
            for event in payload:
                eid = event.get("id")
                if eid in seen:
                    continue
                seen.add(eid)
                if row := parse_api_event(event):
                    group_rows.append(row)
                elif row := parse_knockout_api_event(event):
                    ko_rows.append(row)
        return group_rows, ko_rows
    except Exception as exc:
        print(f"⚠️  Historical API unavailable ({exc})")
        return [], []


def lookup_settled(settled: dict[tuple[str, str], dict], home: str, away: str) -> dict | None:
    """Match results.csv home/away even when API stored the reverse fixture."""
    if (home, away) in settled:
        return settled[(home, away)]
    rev = settled.get((away, home))
    if not rev:
        return None
    return {
        **rev,
        "home": home,
        "away": away,
        "home_score": rev["away_score"],
        "away_score": rev["home_score"],
    }


def collect_settled() -> dict[tuple[str, str], dict]:
    load_dotenv()
    api_key = os.getenv("ODDS_API_KEY")

    merged: dict[tuple[str, str], dict] = {}
    sources: list[tuple[str, list[dict]]] = [
        ("manual fallback", MANUAL_GROUP_RESULTS),
        ("archive (group)", load_json_fixtures(ARCHIVE_PATH, knockout=False)),
        ("archive (knockout)", load_json_fixtures(ARCHIVE_PATH, knockout=True)),
        ("processed fixtures (group)", load_json_fixtures(FIXTURES_PATH, knockout=False)),
        ("processed fixtures (knockout)", load_json_fixtures(FIXTURES_PATH, knockout=True)),
        ("published fixtures (group)", load_json_fixtures(DOCS_FIXTURES_PATH, knockout=False)),
        ("published fixtures (knockout)", load_json_fixtures(DOCS_FIXTURES_PATH, knockout=True)),
    ]
    if api_key:
        group_hist, ko_hist = fetch_historical(api_key)
        sources.append(("historical API (group)", group_hist))
        sources.append(("historical API (knockout)", ko_hist))

    for label, rows in sources:
        for row in rows:
            key = (row["home"], row["away"])
            merged[key] = row
        if rows:
            print(f"   {label}: {len(rows)} settled games")

    return merged


def _wc26_pairs(rows: list[dict]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in rows:
        if row.get("tournament") != "FIFA World Cup":
            continue
        if str(row.get("date", "")) < "2026-06-01":
            continue
        pairs.add((row["home_team"], row["away_team"]))
        pairs.add((row["away_team"], row["home_team"]))
    return pairs


def update_results_csv(settled: dict[tuple[str, str], dict]) -> tuple[int, int]:
    if not RESULTS_PATH.exists() or not settled:
        return 0, 0

    with open(RESULTS_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    updated = 0
    for row in rows:
        if row.get("tournament") != "FIFA World Cup":
            continue
        match = lookup_settled(settled, row["home_team"], row["away_team"])
        if not match:
            continue
        new_hs, new_as = str(match["home_score"]), str(match["away_score"])
        old_hs, old_as = str(row.get("home_score", "")), str(row.get("away_score", ""))
        if old_hs == new_hs and old_as == new_as and (not match.get("date") or row.get("date") == match["date"]):
            continue
        row["home_score"] = new_hs
        row["away_score"] = new_as
        if match.get("date"):
            row["date"] = match["date"]
        updated += 1

    existing_pairs = _wc26_pairs(rows)
    appended = 0
    for (home, away), match in settled.items():
        if (home, away) in existing_pairs or (away, home) in existing_pairs:
            continue
        rows.append(
            {
                "date": match.get("date", ""),
                "home_team": home,
                "away_team": away,
                "home_score": str(match["home_score"]),
                "away_score": str(match["away_score"]),
                "tournament": "FIFA World Cup",
                "city": "",
                "country": "",
                "neutral": "True",
            }
        )
        existing_pairs.add((home, away))
        existing_pairs.add((away, home))
        appended += 1

    if updated or appended:
        with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    return updated, appended


def rebuild_model() -> None:
    subprocess.run([sys.executable, "-m", "src.features.pipeline"], cwd=PROJECT_ROOT, check=True)
    subprocess.run([sys.executable, "scripts/build_webapp_data.py"], cwd=PROJECT_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync WC26 results into the rating engine")
    parser.add_argument("--no-rebuild", action="store_true", help="Only update results.csv")
    args = parser.parse_args()

    print("📥 Collecting settled WC26 group + knockout results...")
    settled = collect_settled()
    group_n = sum(1 for r in settled.values() if r.get("stage") == "group")
    ko_n = sum(1 for r in settled.values() if r.get("stage") == "knockout")
    print(f"   → {len(settled)} unique matches ({group_n} group, {ko_n} knockout)")

    updated, appended = update_results_csv(settled)
    if updated or appended:
        parts = []
        if updated:
            parts.append(f"updated {updated}")
        if appended:
            parts.append(f"appended {appended} new")
        print(f"✅ {', '.join(parts)} FIFA World Cup row(s) in {RESULTS_PATH}")
    else:
        print("ℹ️  results.csv already up to date")

    import pandas as pd

    if RESULTS_PATH.exists():
        wc = pd.read_csv(RESULTS_PATH)
        wc26 = wc[(wc["tournament"] == "FIFA World Cup") & (wc["date"] >= "2026-06-01")]
        missing = wc26[wc26["home_score"].isna()][["date", "home_team", "away_team"]]
        if not missing.empty:
            print(f"⚠️  {len(missing)} WC26 game(s) still awaiting scores in results.csv:")
            for _, row in missing.drop_duplicates().iterrows():
                print(f"      {row['date']}  {row['home_team']} vs {row['away_team']}")

    if args.no_rebuild:
        return

    print("🔧 Rebuilding blended model features + docs/data.js...")
    rebuild_model()
    print("✅ Model engine updated with latest WC26 results")


if __name__ == "__main__":
    main()
