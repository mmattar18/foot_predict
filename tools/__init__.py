"""Outils (tools) de l'agent de prédiction sportive.

Chaque module expose :
- une fonction "pure" (testable, retourne une chaîne lisible par le LLM) ;
- un objet `*_tool` décoré pour LangGraph/LangChain.

Les données proviennent soit de `data/teams_mock.json` (mock), soit de l'API
football-data.org — voir `tools/providers.py`.
"""

from tools.history_tool import get_head_to_head, history_tool
from tools.injury_tool import get_injuries, injury_tool
from tools.news_search_tool import news_tool, search_team_news
from tools.probability_tool import estimate_match_probabilities, probability_tool
from tools.stats_tool import get_team_stats, stats_tool
from tools.upcoming_tool import get_upcoming_matches, upcoming_tool

ALL_TOOLS = [
    stats_tool,
    history_tool,
    injury_tool,
    news_tool,
    upcoming_tool,
    probability_tool,
]

__all__ = [
    "ALL_TOOLS",
    "stats_tool",
    "history_tool",
    "injury_tool",
    "news_tool",
    "upcoming_tool",
    "probability_tool",
    "get_team_stats",
    "get_head_to_head",
    "get_injuries",
    "search_team_news",
    "get_upcoming_matches",
    "estimate_match_probabilities",
]
