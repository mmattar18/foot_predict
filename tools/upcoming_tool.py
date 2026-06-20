"""Tool 5 — A team's upcoming matches (schedule).

Source: the football-data.org API if configured, otherwise simulated data.
"""

from langchain_core.tools import tool

from tools.providers import get_provider


def get_upcoming_matches(team_name: str) -> str:
    """Get a team's upcoming scheduled matches.

    Useful to frame the context (busy schedule, must-win game, etc.).

    Args:
        team_name: Team name.
    """
    return get_provider().upcoming(team_name)


upcoming_tool = tool(get_upcoming_matches)
