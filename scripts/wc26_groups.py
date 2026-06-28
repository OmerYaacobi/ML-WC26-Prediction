"""Official 2026 World Cup group draw — shared by web app, fetch scripts, and CLI."""

GROUPS = {
    "Group A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "Group B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "Group C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "Group D": ["United States", "Paraguay", "Australia", "Turkey"],
    "Group E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "Group F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "Group G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "Group H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "Group I": ["France", "Senegal", "Iraq", "Norway"],
    "Group J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "Group K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "Group L": ["England", "Croatia", "Ghana", "Panama"],
}

# odds-api.io / bookmaker spellings → internal model names (docs/data.js keys)
API_TEAM_ALIASES = {
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Turkey": "Turkey",
    "Curaçao": "Curacao",
    "Curacao": "Curacao",
    "USA": "United States",
    "United States": "United States",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "Czech Republic": "Czechia",
    "Czechia": "Czechia",
    "Cote d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "Congo DR": "DR Congo",
    "DR Congo": "DR Congo",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
}

TEAM_TO_GROUP = {team: group for group, teams in GROUPS.items() for team in teams}
ALL_TEAMS = set(TEAM_TO_GROUP)

KNOCKOUT_MARKERS = (
    "round of",
    "quarter",
    "semi",
    "final",
    "third place",
    "knockout",
    "playoff",
    "play-off",
    "last 16",
    "last 32",
)


def normalize_team(name: str) -> str | None:
    if not name:
        return None
    clean = name.strip()
    mapped = API_TEAM_ALIASES.get(clean, clean)
    return mapped if mapped in ALL_TEAMS else None


# Internal model names → results.csv spellings
CSV_TEAM_NAMES = {
    "Curacao": "Curaçao",
    "Czechia": "Czech Republic",
    "Turkey": "Turkey",
    "United States": "United States",
    "South Korea": "South Korea",
    "Ivory Coast": "Ivory Coast",
    "DR Congo": "DR Congo",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
}


def to_csv_team(name: str) -> str:
    return CSV_TEAM_NAMES.get(name, name)


# results.csv spellings → internal model names
CSV_TO_MODEL = {v: k for k, v in CSV_TEAM_NAMES.items()}


def from_csv_team(name: str) -> str:
    return CSV_TO_MODEL.get(name, name)


def is_world_cup_league(league_name: str) -> bool:
    return "world cup" in (league_name or "").lower()


def is_group_stage_league(league_name: str) -> bool:
    if not is_world_cup_league(league_name):
        return False
    return not any(marker in league_name.lower() for marker in KNOCKOUT_MARKERS)


def is_knockout_league(league_name: str) -> bool:
    if not is_world_cup_league(league_name):
        return False
    return any(marker in league_name.lower() for marker in KNOCKOUT_MARKERS)


def parse_knockout_round(league_name: str) -> str | None:
    league = (league_name or "").lower()
    if "round of 32" in league or "round of thirty-two" in league:
        return "Round of 32"
    if "round of 16" in league or "round of sixteen" in league:
        return "Round of 16"
    if "quarter" in league:
        return "Quarter-finals"
    if "semi" in league:
        return "Semi-finals"
    if "third place" in league or "3rd place" in league:
        return "Third place"
    if "final" in league:
        return "Final"
    return "Knockout"
