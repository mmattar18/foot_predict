"""Tests for the "upcoming matches" tool (mock mode)."""

from tools.upcoming_tool import get_upcoming_matches


def test_upcoming_known_team():
    res = get_upcoming_matches("Lyon Dragons")
    assert "Upcoming matches" in res
    assert "Lyon Dragons" in res


def test_upcoming_partial_name():
    assert "Marseille Tigers" in get_upcoming_matches("marseille")


def test_upcoming_unknown_team():
    assert "No team found" in get_upcoming_matches("Chelsea")
