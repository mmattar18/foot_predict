"""Tests unitaires (hors-ligne) du client football-data.org.

On ne teste ici que la logique de parsing, sans appel réseau.
"""

from tools import football_data as fd


def _row(name):
    return {"team": {"id": hash(name) % 1000, "name": name}}


def test_all_total_rows_championnat():
    # Un championnat : un seul bloc TOTAL.
    data = {"standings": [{"type": "TOTAL", "table": [_row("Arsenal"), _row("Chelsea")]}]}
    rows = fd._all_total_rows(data)
    assert [r["team"]["name"] for r in rows] == ["Arsenal", "Chelsea"]


def test_all_total_rows_tournoi_a_groupes():
    # Une Coupe du Monde : un bloc TOTAL par groupe -> tout doit être agrégé.
    data = {
        "standings": [
            {"type": "TOTAL", "group": "Group A", "table": [_row("France"), _row("Mexico")]},
            {"type": "TOTAL", "group": "Group B", "table": [_row("Spain"), _row("Japan")]},
            # un bloc HOME ne doit pas être pris en compte
            {"type": "HOME", "group": "Group A", "table": [_row("IGNORE")]},
        ]
    }
    noms = [r["team"]["name"] for r in fd._all_total_rows(data)]
    assert noms == ["France", "Mexico", "Spain", "Japan"]
    assert "IGNORE" not in noms


def test_result_for_perspective_equipe():
    match = {
        "utcDate": "2026-03-01T20:00:00Z",
        "homeTeam": {"id": 1, "name": "France"},
        "awayTeam": {"id": 2, "name": "Spain"},
        "score": {"fullTime": {"home": 2, "away": 1}},
    }
    r = fd._result_for(match, team_id=1)
    assert r["res"] == "W" and r["gf"] == 2 and r["gc"] == 1
    r2 = fd._result_for(match, team_id=2)
    assert r2["res"] == "L" and r2["gf"] == 1 and r2["gc"] == 2


def test_result_for_match_non_joue():
    match = {
        "utcDate": "2026-08-01T20:00:00Z",
        "homeTeam": {"id": 1, "name": "A"},
        "awayTeam": {"id": 2, "name": "B"},
        "score": {"fullTime": {"home": None, "away": None}},
    }
    assert fd._result_for(match, 1) is None


def test_wc_dans_les_competitions():
    assert "WC" in fd.COMPETITION_NAMES
    assert "WC" in fd.DEFAULT_COMPETITIONS
