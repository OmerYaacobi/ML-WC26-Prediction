"""Update FIFA World Cup rows in data/raw/results.csv when scores arrive.

Matches by home/away team (kickoff dates often differ from schedule placeholders).
For a full sync + model rebuild, run:

    python scripts/sync_group_results.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_group_results import collect_settled, update_results_csv

RESULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "results.csv"


def main() -> None:
    settled = collect_settled()
    n = update_results_csv(settled)
    if n:
        print(f"✅ Updated {n} FIFA World Cup score(s) in {RESULTS_PATH}")
        print("   Run: python scripts/sync_group_results.py  (to rebuild model ratings)")
    else:
        print("ℹ️  No new WC scores to write to results.csv")


if __name__ == "__main__":
    main()
