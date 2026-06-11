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


def is_group_stage_league(league_name: str) -> bool:
    league = (league_name or "").lower()
    if "world cup" not in league:
        return False
    return not any(marker in league for marker in KNOCKOUT_MARKERS)
