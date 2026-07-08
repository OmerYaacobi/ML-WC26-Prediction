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


def _rebuild_pair_lookup(matches: list[dict]) -> dict[tuple[str, str], dict]:
    lookup: dict[tuple[str, str], dict] = {}
    for match in matches:
        h, a = match.get("home"), match.get("away")
        if h and a:
            lookup[(h, a)] = match
            lookup[(a, h)] = match
    return lookup


def fixture_winner_loser(fx: dict) -> tuple[str, str] | None:
    """Return (winner, loser) for a settled knockout fixture."""
    if fx.get("status") != "settled":
        return None
    home, away = fx.get("home"), fx.get("away")
    hs, aws = fx.get("homeScore"), fx.get("awayScore")
    if not home or not away or hs is None or aws is None:
        return None
    if hs == aws:
        return None
    return (home, away) if hs > aws else (away, home)


def _fixture_for_match(match: dict, fixtures: list[dict], by_match_no: dict[int, dict]) -> dict | None:
    mno = match["matchNo"]
    if mno in by_match_no:
        return by_match_no[mno]
    home, away = match.get("home"), match.get("away")
    if not home or not away:
        return None
    for fx in fixtures:
        if fx.get("home") == home and fx.get("away") == away:
            return fx
        if fx.get("home") == away and fx.get("away") == home:
            return fx
    return None


def advance_bracket(fixtures: list[dict]) -> list[dict]:
    """Fill W/L slots from settled results — e.g. W83 → Portugal after M83 finishes."""
    import copy

    advanced = copy.deepcopy(BRACKET_MATCHES)
    slots: dict[str, str] = {}
    by_match_no: dict[int, dict] = {}
    for fx in fixtures:
        mno = fx.get("matchNo")
        if mno is not None:
            by_match_no[int(mno)] = fx

    for match in sorted(advanced, key=lambda m: m["matchNo"]):
        mno = match["matchNo"]

        # Resolve this tie's teams from earlier-round winners BEFORE looking up
        # its fixture — later rounds (R16+) carry no matchNo when the API lists
        # them under the generic league, so they can only be matched by team name
        # once home/away are filled in.
        if not match.get("home") and match.get("homeLabel"):
            resolved = slots.get(match["homeLabel"])
            if resolved:
                match["home"] = resolved
        if not match.get("away") and match.get("awayLabel"):
            resolved = slots.get(match["awayLabel"])
            if resolved:
                match["away"] = resolved

        fx = _fixture_for_match(match, fixtures, by_match_no)

        if fx and fx.get("status") == "settled":
            result = fixture_winner_loser(fx)
            if result:
                winner, loser = result
                slots[f"W{mno}"] = winner
                slots[f"L{mno}"] = loser
                match["homeScore"] = fx.get("homeScore")
                match["awayScore"] = fx.get("awayScore")
                match["status"] = "settled"
            elif match.get("home") and match.get("away"):
                match["status"] = fx.get("status", "settled")
                match["homeScore"] = fx.get("homeScore")
                match["awayScore"] = fx.get("awayScore")
        elif fx:
            match["status"] = fx.get("status", match.get("status", "pending"))
            match["homeScore"] = fx.get("homeScore")
            match["awayScore"] = fx.get("awayScore")
            match["kickoff"] = fx.get("kickoff", match.get("kickoff"))
            if fx.get("id") is not None:
                match["id"] = fx["id"]

    return advanced


def lookup_bracket(home: str, away: str, matches: list[dict] | None = None) -> dict | None:
    if matches is not None:
        return _rebuild_pair_lookup(matches).get((home, away))
    return BRACKET_BY_PAIR.get((home, away))


def bracket_to_fixture(match: dict, api: dict | None = None) -> dict | None:
    """Build a fixture row from bracket data.

    ``advance_bracket`` is the source of truth for status/score: it attributes
    each result to its tie (by matchNo, then team pair) and stamps the match.
    The raw API row is only used to backfill metadata, because R16+ results
    arrive under the generic league and get misclassified as group fixtures —
    so we can't rely on ``api['stage']`` to decide whether to trust them.
    """
    home = match.get("home")
    away = match.get("away")
    if not home or not away:
        return None

    api = api or {}
    status = match.get("status") or api.get("status") or "pending"
    home_score = match.get("homeScore")
    if home_score is None:
        home_score = api.get("homeScore")
    away_score = match.get("awayScore")
    if away_score is None:
        away_score = api.get("awayScore")

    return {
        "id": match.get("id") or api.get("id") or f"bracket-{match['matchNo']}",
        "matchNo": match["matchNo"],
        "home": home,
        "away": away,
        "stage": "knockout",
        "round": ROUND_LABELS[match["round"]],
        "bracketRound": match["round"],
        "kickoff": match.get("kickoff") or api.get("kickoff"),
        "status": status,
        "homeScore": home_score,
        "awayScore": away_score,
        "bettable": False if status == "settled" else api.get("bettable", True),
        "league": api.get("league") or "International - FIFA World Cup",
        "venue": match.get("venue", ""),
    }


def merge_knockout_fixtures(fixtures: list[dict], bracket_matches: list[dict] | None = None) -> list[dict]:
    """Ensure all known knockout ties exist; overlay API data when available."""
    matches = bracket_matches or advance_bracket(fixtures)
    pair_lookup = _rebuild_pair_lookup(matches)
    by_pair = {(f["home"], f["away"]): f for f in fixtures if f.get("home") and f.get("away")}
    merged = [
        f
        for f in fixtures
        if f.get("stage") != "knockout" and not pair_lookup.get((f.get("home", ""), f.get("away", "")))
    ]

    for match in matches:
        home, away = match.get("home"), match.get("away")
        if not home or not away:
            continue
        api = by_pair.get((home, away)) or by_pair.get((away, home))
        fx = bracket_to_fixture(match, api)
        if fx:
            merged.append(fx)

    merged.sort(key=lambda f: (f.get("kickoff") or "", f.get("stage", ""), f.get("group", ""), f.get("matchNo", 0)))
    return merged


def write_bracket_js(path, bracket_matches: list[dict] | None = None) -> None:
    import json
    from pathlib import Path

    matches = bracket_matches or BRACKET_MATCHES
    # Strip internal keys before publishing to the browser.
    public = []
    for m in matches:
        row = {k: v for k, v in m.items() if not k.startswith("_") and k not in ("status", "homeScore", "awayScore")}
        public.append(row)

    payload = (
        "// Auto-generated by scripts/wc26_bracket.py — do not edit by hand.\n"
        f"const WC26_BRACKET_ROUNDS = {json.dumps(BRACKET_ROUNDS, indent=2)};\n\n"
        f"const WC26_BRACKET_MATCHES = {json.dumps(public, indent=2, ensure_ascii=False)};\n"
    )
    Path(path).write_text(payload, encoding="utf-8")
