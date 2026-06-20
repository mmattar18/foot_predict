"""Tool 3 — A team's injuries and key absences.

Available only with mock data: football-data.org does not provide injuries on
the free tier (the real provider says so explicitly).
"""

from langchain_core.tools import tool

from tools.providers import get_provider


def get_injuries(team_name: str) -> str:
    """Get a team's injuries and absences (suspensions, ruled out).

    For each absent player, reports position, status and importance (key or
    rotation), to assess the impact on the upcoming match.

    Args:
        team_name: Team name.
    """
    return get_provider().injuries(team_name)


injury_tool = tool(get_injuries)
