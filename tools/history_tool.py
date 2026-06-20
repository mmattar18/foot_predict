"""Tool 2 — Head-to-head history between two teams."""

from langchain_core.tools import tool

from tools.providers import get_provider


def get_head_to_head(team_a: str, team_b: str) -> str:
    """Get the head-to-head history between two teams.

    Returns the latest matches between the two teams with scores and a record
    (wins on each side, draws). Source: the football-data.org API if
    configured, otherwise simulated data.

    Args:
        team_a: First team.
        team_b: Second team.
    """
    return get_provider().head_to_head(team_a, team_b)


history_tool = tool(get_head_to_head)
