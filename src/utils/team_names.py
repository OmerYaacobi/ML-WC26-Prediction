"""Canonical team-name aliases shared by the model, odds loaders, and CV.

Bookmaker feeds, odds-api.io, and results.csv do not spell every nation the
same way the feature matrix does (the keys in docs/data.js). Map every known
variant onto that internal name before a lookup, or the team is skipped or
left on default market values.
"""

from __future__ import annotations

# External spelling → internal model name.
TEAM_ALIASES = {
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
    "Côte d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "Congo DR": "DR Congo",
    "DR Congo": "DR Congo",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "IR Iran": "Iran",
    "Iran": "Iran",
}


def canonical_team(name: str) -> str:
    """Return the internal model name for a results.csv or API team string."""
    cleaned = str(name or "").strip()
    return TEAM_ALIASES.get(cleaned, cleaned)
