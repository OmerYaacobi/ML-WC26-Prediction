"""Official WC26 knockout bracket — combination 67 (post group stage).

Kickoffs converted from FIFA host-city local times to UTC.
"""

from __future__ import annotations

ROUND_LABELS = {
    "r32": "Round of 32",
    "r16": "Round of 16",
    "qf": "Quarter-finals",
    "sf": "Semi-finals",
    "final": "Final",
}

BRACKET_ROUNDS = [
    {"id": "r32", "label": "Round of 32", "short": "R32"},
    {"id": "r16", "label": "Round of 16", "short": "R16"},
    {"id": "qf", "label": "Quarter-finals", "short": "QF"},
    {"id": "sf", "label": "Semi-finals", "short": "SF"},
    {"id": "final", "label": "Final", "short": "Final"},
]

# matchNo, round, home, away, kickoff (UTC), venue — home/away None when TBD
BRACKET_MATCHES: list[dict] = [
    # Round of 32
    {"matchNo": 73, "round": "r32", "home": "South Africa", "away": "Canada", "kickoff": "2026-06-28T19:00:00Z", "venue": "SoFi Stadium, Inglewood"},
    {"matchNo": 76, "round": "r32", "home": "Brazil", "away": "Japan", "kickoff": "2026-06-29T17:00:00Z", "venue": "NRG Stadium, Houston"},
    {"matchNo": 74, "round": "r32", "home": "Germany", "away": "Paraguay", "kickoff": "2026-06-29T20:30:00Z", "venue": "Gillette Stadium, Foxborough"},
    {"matchNo": 75, "round": "r32", "home": "Netherlands", "away": "Morocco", "kickoff": "2026-06-30T01:00:00Z", "venue": "Estadio BBVA, Monterrey"},
    {"matchNo": 78, "round": "r32", "home": "Ivory Coast", "away": "Norway", "kickoff": "2026-06-30T17:00:00Z", "venue": "AT&T Stadium, Arlington"},
    {"matchNo": 77, "round": "r32", "home": "France", "away": "Sweden", "kickoff": "2026-06-30T21:00:00Z", "venue": "MetLife Stadium, East Rutherford"},
    {"matchNo": 79, "round": "r32", "home": "Mexico", "away": "Ecuador", "kickoff": "2026-07-01T01:00:00Z", "venue": "Estadio Azteca, Mexico City"},
    {"matchNo": 80, "round": "r32", "home": "England", "away": "DR Congo", "kickoff": "2026-07-01T16:00:00Z", "venue": "Mercedes-Benz Stadium, Atlanta"},
    {"matchNo": 82, "round": "r32", "home": "Belgium", "away": "Senegal", "kickoff": "2026-07-01T20:00:00Z", "venue": "Lumen Field, Seattle"},
    {"matchNo": 81, "round": "r32", "home": "United States", "away": "Bosnia and Herzegovina", "kickoff": "2026-07-02T00:00:00Z", "venue": "Levi's Stadium, Santa Clara"},
    {"matchNo": 84, "round": "r32", "home": "Spain", "away": "Austria", "kickoff": "2026-07-02T19:00:00Z", "venue": "SoFi Stadium, Inglewood"},
    {"matchNo": 83, "round": "r32", "home": "Portugal", "away": "Croatia", "kickoff": "2026-07-02T23:00:00Z", "venue": "BMO Field, Toronto"},
    {"matchNo": 85, "round": "r32", "home": "Switzerland", "away": "Algeria", "kickoff": "2026-07-03T03:00:00Z", "venue": "BC Place, Vancouver"},
    {"matchNo": 88, "round": "r32", "home": "Australia", "away": "Egypt", "kickoff": "2026-07-03T18:00:00Z", "venue": "AT&T Stadium, Arlington"},
    {"matchNo": 86, "round": "r32", "home": "Argentina", "away": "Cape Verde", "kickoff": "2026-07-03T22:00:00Z", "venue": "Hard Rock Stadium, Miami Gardens"},
    {"matchNo": 87, "round": "r32", "home": "Colombia", "away": "Ghana", "kickoff": "2026-07-04T01:30:00Z", "venue": "Arrowhead Stadium, Kansas City"},
    # Round of 16
    {"matchNo": 90, "round": "r16", "homeLabel": "W73", "awayLabel": "W75", "kickoff": "2026-07-04T17:00:00Z", "venue": "NRG Stadium, Houston"},
    {"matchNo": 89, "round": "r16", "homeLabel": "W74", "awayLabel": "W77", "kickoff": "2026-07-04T21:00:00Z", "venue": "Lincoln Financial Field, Philadelphia"},
    {"matchNo": 91, "round": "r16", "homeLabel": "W76", "awayLabel": "W78", "kickoff": "2026-07-05T20:00:00Z", "venue": "MetLife Stadium, East Rutherford"},
    {"matchNo": 92, "round": "r16", "homeLabel": "W79", "awayLabel": "W80", "kickoff": "2026-07-06T00:00:00Z", "venue": "Estadio Azteca, Mexico City"},
    {"matchNo": 93, "round": "r16", "homeLabel": "W83", "awayLabel": "W84", "kickoff": "2026-07-06T19:00:00Z", "venue": "AT&T Stadium, Arlington"},
    {"matchNo": 94, "round": "r16", "homeLabel": "W81", "awayLabel": "W82", "kickoff": "2026-07-07T00:00:00Z", "venue": "Lumen Field, Seattle"},
    {"matchNo": 95, "round": "r16", "homeLabel": "W86", "awayLabel": "W88", "kickoff": "2026-07-07T16:00:00Z", "venue": "Mercedes-Benz Stadium, Atlanta"},
    {"matchNo": 96, "round": "r16", "homeLabel": "W85", "awayLabel": "W87", "kickoff": "2026-07-07T20:00:00Z", "venue": "BC Place, Vancouver"},
    # Quarter-finals
    {"matchNo": 97, "round": "qf", "homeLabel": "W89", "awayLabel": "W90", "kickoff": "2026-07-09T20:00:00Z", "venue": "Gillette Stadium, Foxborough"},
    {"matchNo": 98, "round": "qf", "homeLabel": "W93", "awayLabel": "W94", "kickoff": "2026-07-10T19:00:00Z", "venue": "SoFi Stadium, Inglewood"},
    {"matchNo": 99, "round": "qf", "homeLabel": "W91", "awayLabel": "W92", "kickoff": "2026-07-11T21:00:00Z", "venue": "Hard Rock Stadium, Miami Gardens"},
    {"matchNo": 100, "round": "qf", "homeLabel": "W95", "awayLabel": "W96", "kickoff": "2026-07-12T01:00:00Z", "venue": "Arrowhead Stadium, Kansas City"},
    # Semi-finals
    {"matchNo": 101, "round": "sf", "homeLabel": "W97", "awayLabel": "W98", "kickoff": "2026-07-14T19:00:00Z", "venue": "AT&T Stadium, Arlington"},
    {"matchNo": 102, "round": "sf", "homeLabel": "W99", "awayLabel": "W100", "kickoff": "2026-07-15T19:00:00Z", "venue": "Mercedes-Benz Stadium, Atlanta"},
    # Final week
    {"matchNo": 103, "round": "final", "homeLabel": "L101", "awayLabel": "L102", "kickoff": "2026-07-18T21:00:00Z", "venue": "Hard Rock Stadium, Miami Gardens", "tag": "3rd place"},
    {"matchNo": 104, "round": "final", "homeLabel": "W101", "awayLabel": "W102", "kickoff": "2026-07-19T19:00:00Z", "venue": "MetLife Stadium, East Rutherford", "tag": "Final"},
]

BRACKET_BY_PAIR: dict[tuple[str, str], dict] = {}
BRACKET_BY_MATCH_NO: dict[int, dict] = {}
for _m in BRACKET_MATCHES:
    BRACKET_BY_MATCH_NO[_m["matchNo"]] = _m
    h, a = _m.get("home"), _m.get("away")
    if h and a:
        BRACKET_BY_PAIR[(h, a)] = _m
        BRACKET_BY_PAIR[(a, h)] = _m


def lookup_bracket(home: str, away: str) -> dict | None:
    return BRACKET_BY_PAIR.get((home, away))


def bracket_to_fixture(match: dict, api: dict | None = None) -> dict | None:
    """Build a fixture row from bracket data, optionally overlaid with API scores."""
    home = match.get("home")
    away = match.get("away")
    if not home or not away:
        return None

    base = {
        "id": f"bracket-{match['matchNo']}",
        "matchNo": match["matchNo"],
        "home": home,
        "away": away,
        "stage": "knockout",
        "round": ROUND_LABELS[match["round"]],
        "bracketRound": match["round"],
        "kickoff": match["kickoff"],
        "status": "pending",
        "homeScore": None,
        "awayScore": None,
        "bettable": True,
        "league": "International - FIFA World Cup",
        "venue": match.get("venue", ""),
    }
    if api and (api.get("stage") == "knockout" or lookup_bracket(home, away)):
        for key in ("id", "kickoff", "status", "homeScore", "awayScore", "bettable", "league"):
            if api.get(key) is not None:
                base[key] = api[key]
    return base


def merge_knockout_fixtures(fixtures: list[dict]) -> list[dict]:
    """Ensure all known knockout ties exist; overlay API data when available."""
    by_pair = {(f["home"], f["away"]): f for f in fixtures if f.get("home") and f.get("away")}
    merged = [f for f in fixtures if f.get("stage") != "knockout" and not lookup_bracket(f.get("home", ""), f.get("away", ""))]

    for match in BRACKET_MATCHES:
        home, away = match.get("home"), match.get("away")
        if not home or not away:
            continue
        api = by_pair.get((home, away)) or by_pair.get((away, home))
        fx = bracket_to_fixture(match, api)
        if fx:
            merged.append(fx)

    merged.sort(key=lambda f: (f.get("kickoff") or "", f.get("stage", ""), f.get("group", ""), f.get("matchNo", 0)))
    return merged


def write_bracket_js(path) -> None:
    import json
    from pathlib import Path

    payload = (
        "// Auto-generated by scripts/wc26_bracket.py — do not edit by hand.\n"
        f"const WC26_BRACKET_ROUNDS = {json.dumps(BRACKET_ROUNDS, indent=2)};\n\n"
        f"const WC26_BRACKET_MATCHES = {json.dumps(BRACKET_MATCHES, indent=2, ensure_ascii=False)};\n"
    )
    Path(path).write_text(payload, encoding="utf-8")
