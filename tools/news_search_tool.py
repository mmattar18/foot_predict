"""Tool 4 — Search for recent qualitative information.

Morale, coach statements, squad momentum. Backed by mock data here.
football-data.org does not provide this kind of information: for a real web
search, plug in Tavily/DuckDuckGo/SerpAPI (same signature).
"""

from langchain_core.tools import tool

from tools.providers import get_provider


def search_team_news(team_name: str) -> str:
    """Search for recent qualitative information about a team.

    Returns non-numeric context: squad morale, coach statements, recent
    momentum, possible tensions.

    Args:
        team_name: Team name.
    """
    return get_provider().news(team_name)


news_tool = tool(search_team_news)
