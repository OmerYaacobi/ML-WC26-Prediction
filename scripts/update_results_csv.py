"""Update FIFA World Cup rows in data/raw/results.csv when scores arrive.

Matches existing schedule rows (NA,NA placeholders) — does not append duplicates.
Called automatically at the end of fetch_fixtures.py.

Rebuilding model features from updated results is optional and manual:

    python src/features/pipeline.py
    python scripts/build_webapp_data.py
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wc26_groups import to_csv_team

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_PATH = PROJECT_ROOT / "data" / "processed" / "wc26_fixtures.json"
RESULTS_PATH = PROJECT_ROOT / "data" / "raw" / "results.csv"
COLUMNS = ["date", "home_team", "away_team", "home_score", "away_score", "tournament", "city", "country", "neutral"]


def kickoff_date(iso: str) -> str:
    if not iso:
        return ""
    return iso[:10]


def load_settled() -> list[dict]:
    if not FIXTURES_PATH.exists():
        return []
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    out = []
    for fx in data.get("fixtures", []):
        if fx.get("status") != "settled":
            continue
        hs, aws = fx.get("homeScore"), fx.get("awayScore")
        if hs is None or aws is None:
            continue
        out.append(
            {
                "date": kickoff_date(fx.get("kickoff", "")),
                "home": to_csv_team(fx["home"]),
                "away": to_csv_team(fx["away"]),
                "home_score": int(hs),
                "away_score": int(aws),
            }
        )
    return out


def update_csv(settled: list[dict]) -> int:
    if not RESULTS_PATH.exists() or not settled:
        return 0

    with open(RESULTS_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    lookup = {(s["date"], s["home"], s["away"]): s for s in settled}
    updated = 0

    for row in rows:
        if row.get("tournament") != "FIFA World Cup":
            continue
        key = (row["date"], row["home_team"], row["away_team"])
        if key not in lookup:
            continue
        hs = row.get("home_score", "")
        if hs not in ("NA", "", "nan", None):
            continue
        match = lookup[key]
        row["home_score"] = str(match["home_score"])
        row["away_score"] = str(match["away_score"])
        updated += 1

    if updated:
        with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    return updated


def main() -> None:
    settled = load_settled()
    n = update_csv(settled)
    if n:
        print(f"✅ Updated {n} FIFA World Cup score(s) in {RESULTS_PATH}")
    else:
        print("ℹ️  No new WC scores to write to results.csv")


if __name__ == "__main__":
    main()
