"""Normalize odds-api.io fixture status, scores, and bettable flag."""
from __future__ import annotations

from datetime import datetime, timezone

FINISHED_STATUSES = frozenset({"settled", "finished", "completed", "ended", "closed", "ft"})
LIVE_STATUSES = frozenset({"live", "inprogress", "in_progress", "1h", "2h", "ht"})


def parse_kickoff(kickoff: str) -> datetime | None:
    if not kickoff:
        return None
    try:
        return datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_scores(scores: dict | None) -> tuple[int | None, int | None, bool]:
    """Return (home, away, has_full_time).

    Only ``periods.ft`` counts as full time. Top-level home/away are live/current
    scores and must NOT mark a match as finished (API sends 0-0 before kickoff).
    """
    if not isinstance(scores, dict):
        return None, None, False

    ft = (scores.get("periods") or {}).get("ft")
    if isinstance(ft, dict) and ft.get("home") is not None and ft.get("away") is not None:
        return int(ft["home"]), int(ft["away"]), True

    home = scores.get("home")
    away = scores.get("away")
    if home is not None and away is not None:
        return int(home), int(away), False

    return None, None, False


def extract_ko_decisive_scores(scores: dict | None) -> tuple[int | None, int | None]:
    """Decisive KO scoreline — includes extra time / penalties when provided."""
    if not isinstance(scores, dict):
        return None, None

    periods = scores.get("periods") or {}
    ft = periods.get("ft") or {}
    top_h, top_a = scores.get("home"), scores.get("away")
    ft_h, ft_a = ft.get("home"), ft.get("away")

    if top_h is not None and top_a is not None and ft_h is not None and ft_a is not None:
        if int(top_h) != int(ft_h) or int(top_a) != int(ft_a):
            return int(top_h), int(top_a)

    for key in ("ap", "ot"):
        period = periods.get(key)
        if isinstance(period, dict) and period.get("home") is not None and period.get("away") is not None:
            ph, pa = int(period["home"]), int(period["away"])
            if ph != pa:
                return ph, pa

    if ft_h is not None and ft_a is not None:
        return int(ft_h), int(ft_a)
    if top_h is not None and top_a is not None:
        return int(top_h), int(top_a)
    return None, None


def normalize_fixture(raw_status: str, kickoff: str, scores: dict | None, *, knockout: bool = False) -> dict:
    """Map API event fields → {status, homeScore, awayScore, bettable}."""
    status = (raw_status or "pending").lower()
    home_score, away_score, has_ft = extract_scores(scores)
    kickoff_dt = parse_kickoff(kickoff)
    kickoff_passed = bool(kickoff_dt and kickoff_dt <= datetime.now(timezone.utc))

    if status == "cancelled":
        return {
            "status": "cancelled",
            "homeScore": home_score,
            "awayScore": away_score,
            "bettable": False,
        }

    if status in FINISHED_STATUSES or has_ft:
        result = {
            "status": "settled",
            "homeScore": home_score,
            "awayScore": away_score,
            "bettable": False,
        }
        if knockout:
            khs, kas = extract_ko_decisive_scores(scores)
            if khs is not None and kas is not None:
                result["homeScore"] = khs
                result["awayScore"] = kas
        return result

    if status in LIVE_STATUSES or kickoff_passed:
        return {
            "status": "live",
            "homeScore": home_score,
            "awayScore": away_score,
            "bettable": False,
        }

    return {
        "status": "pending",
        "homeScore": None,
        "awayScore": None,
        "bettable": True,
    }


def is_finished(fx: dict) -> bool:
    if fx.get("status") == "cancelled":
        return False
    return fx.get("status") == "settled" and fx.get("homeScore") is not None and fx.get("awayScore") is not None
