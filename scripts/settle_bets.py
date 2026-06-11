"""Grade open bets when fixtures finish (run after fetch_fixtures.py).

Settlement needs Firebase Admin credentials — not runnable from the browser.

Setup (one-time):
  1. Firebase Console → Project settings → Service accounts → Generate new private key
  2. Save as firebase-service-account.json (gitignored) OR set GOOGLE_APPLICATION_CREDENTIALS

Run manually or via GitHub Action cron:
    python scripts/fetch_fixtures.py
    python scripts/settle_bets.py

Without Firebase credentials this script only prints what would be settled.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_PATH = PROJECT_ROOT / "data" / "processed" / "wc26_fixtures.json"


def load_results() -> dict[tuple[str, str], dict]:
    if not FIXTURES_PATH.exists():
        return {}
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    out = {}
    for fx in data.get("fixtures", []):
        if fx.get("status") != "settled":
            continue
        hs, aws = fx.get("homeScore"), fx.get("awayScore")
        if hs is None or aws is None:
            continue
        out[(fx["home"], fx["away"])] = {
            "homeScore": int(hs),
            "awayScore": int(aws),
            "id": fx.get("id"),
        }
    return out


def grade_outcome(outcome: str, hs: int, aws: int) -> bool | None:
    total = hs + aws
    if outcome == "draw":
        return hs == aws
    if outcome == "home":
        return hs > aws
    if outcome == "away":
        return aws > hs
    if outcome == "1X":
        return hs >= aws
    if outcome == "X2":
        return aws >= hs
    if outcome == "12":
        return hs != aws
    if outcome.startswith("over_"):
        line = float(outcome.split("_", 1)[1])
        return total > line
    if outcome.startswith("under_"):
        line = float(outcome.split("_", 1)[1])
        return total < line
    if outcome == "btts_yes":
        return hs >= 1 and aws >= 1
    if outcome == "btts_no":
        return not (hs >= 1 and aws >= 1)
    if outcome.startswith("cs_"):
        _, gh, ga = outcome.split("_")
        return hs == int(gh) and aws == int(ga)
    return None


def grade_bet(picks: list[dict], results: dict) -> tuple[str, list[bool | None]]:
    legs = []
    for p in picks:
        home, away = p.get("home"), p.get("away")
        if not home or not away:
            match = p.get("match", "")
            if " vs " in match:
                home, away = [x.strip() for x in match.split(" vs ", 1)]
        key = (home, away)
        if key not in results:
            legs.append(None)
            continue
        r = results[key]
        outcome = p.get("outcome")
        if outcome:
            legs.append(grade_outcome(outcome, r["homeScore"], r["awayScore"]))
        else:
            legs.append(None)
    if any(x is None for x in legs):
        return "open", legs
    if all(legs):
        return "won", legs
    return "lost", legs


def settle_firestore(results: dict) -> int:
    cred_path = PROJECT_ROOT / "firebase-service-account.json"
    if not cred_path.exists():
        print("ℹ️  No firebase-service-account.json — dry run only.")
        return 0

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print("ℹ️  Install firebase-admin to settle: pip install firebase-admin")
        return 0

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))

    db = firestore.client()
    settled = 0
    users = db.collection("users").stream()
    for doc in users:
        data = doc.to_dict() or {}
        bets = data.get("bets") or []
        tokens = data.get("tokens", 0)
        changed = False
        for bet in bets:
            if bet.get("status") != "open":
                continue
            status, _ = grade_bet(bet.get("picks", []), results)
            if status == "open":
                continue
            bet["status"] = status
            if status == "won":
                tokens += int(bet.get("potential", 0))
            changed = True
            settled += 1
        if changed:
            doc.reference.update({"bets": bets, "tokens": tokens})
    return settled


def main() -> None:
    results = load_results()
    print(f"📊 {len(results)} finished fixtures with scores")
    if not results:
        print("Nothing to settle yet.")
        return

    n = settle_firestore(results)
    if n:
        print(f"✅ Settled {n} bets in Firestore")
    else:
        print("Dry run complete — configure Firebase Admin to push payouts.")


if __name__ == "__main__":
    main()
