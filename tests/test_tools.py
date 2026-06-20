"""Simple tests checking that each tool returns the expected data.

Run (from the project root):
    pytest -v
"""

from tools.history_tool import get_head_to_head
from tools.injury_tool import get_injuries
from tools.news_search_tool import search_team_news
from tools.stats_tool import get_team_stats
from tools.utils import find_team, known_teams, load_data


# --- Data / utilities -----------------------------------------------------

def test_load_data_has_teams():
    data = load_data()
    assert "teams" in data and "head_to_head" in data
    assert len(data["teams"]) >= 4


def test_find_team_exact_and_partial():
    teams = load_data()["teams"]
    assert find_team("Lyon Dragons", teams) == "Lyon Dragons"
    assert find_team("lyon", teams) == "Lyon Dragons"          # partial
    assert find_team("MARSEILLE", teams) == "Marseille Tigers"  # case-insensitive
    assert find_team("unknown team", teams) is None


# --- Tool 1: stats --------------------------------------------------------

def test_stats_known_team():
    res = get_team_stats("Lyon Dragons")
    assert "Lyon Dragons" in res
    assert "Form" in res
    assert "Goals scored" in res


def test_stats_accepts_partial_name():
    assert "Marseille Tigers" in get_team_stats("marseille")


def test_stats_unknown_team():
    res = get_team_stats("Real Madrid")
    assert "No team found" in res


# --- Tool 2: head-to-head -------------------------------------------------

def test_head_to_head_existing():
    res = get_head_to_head("Lyon Dragons", "Marseille Tigers")
    assert "Head-to-head" in res
    assert "Record" in res
    assert "-" in res  # at least one "X-Y" score


def test_head_to_head_same_team():
    res = get_head_to_head("lyon", "lyon")
    assert "same" in res.lower()


def test_head_to_head_unknown_team():
    res = get_head_to_head("lyon", "Barcelona")
    assert "no team found" in res.lower()


# --- Tool 3: injuries -----------------------------------------------------

def test_injuries_with_absences():
    res = get_injuries("Paris Eagles")
    assert "Paris Eagles" in res
    assert "key" in res  # this team has key absences in the data


def test_injuries_fully_fit():
    res = get_injuries("Bordeaux Wolves")
    assert "fully fit" in res.lower()


# --- Tool 4: news ---------------------------------------------------------

def test_news_known_team():
    res = search_team_news("Marseille Tigers")
    assert "Recent news" in res
    assert "Marseille Tigers" in res


def test_news_unknown_team():
    assert "No team found" in search_team_news("PSG")


# --- Global consistency ---------------------------------------------------

def test_all_tools_respond_for_each_team():
    for team in known_teams():
        assert team in get_team_stats(team)
        assert get_injuries(team)
        assert search_team_news(team)
