"""Tool 1 — A team's recent statistics.

Recent form, goals scored/conceded and league position. The source (mock data
or the real football-data.org API) is chosen automatically by the `providers`
layer.
"""

from langchain_core.tools import tool

from tools.providers import get_provider


def get_team_stats(team_name: str) -> str:
    """Get a football team's recent statistics.

    Returns the form over the last games, goals scored/conceded and league
    position. Source: the football-data.org API if configured, otherwise
    simulated data.

    Args:
        team_name: Team name (e.g. "Arsenal FC", "Lyon Dragons", "lyon").
    """
    return get_provider().team_stats(team_name)


stats_tool = tool(get_team_stats)
