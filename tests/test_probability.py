"""Tests for the Poisson probability model and its tool."""

import math

from tools.probability_tool import (
    _poisson_pmf,
    estimate_match_probabilities,
    match_probabilities,
)


def test_poisson_pmf_sums_to_one():
    # The total mass of a Poisson distribution over 0..40 should approach 1.
    total = sum(_poisson_pmf(k, 1.7) for k in range(40))
    assert math.isclose(total, 1.0, rel_tol=1e-6)


def test_probabilities_normalized():
    r = match_probabilities(1.6, 1.1)
    assert math.isclose(r["p_home"] + r["p_draw"] + r["p_away"], 1.0, rel_tol=1e-9)
    assert all(0.0 <= r[k] <= 1.0 for k in ("p_home", "p_draw", "p_away"))


def test_stronger_attack_more_likely():
    # A team that scores far more should have a higher win probability.
    strong = match_probabilities(2.4, 0.6)
    assert strong["p_home"] > strong["p_away"]
    assert strong["best_score"][0] >= strong["best_score"][1]


def test_tool_on_mock_teams():
    # Marseille (14 scored / 3 conceded) should dominate Rennes (5 / 11).
    res = estimate_match_probabilities("Marseille Tigers", "Rennes Falcons")
    assert "Poisson" in res
    assert "win)" in res
    assert "%" in res


def test_tool_unknown_team():
    res = estimate_match_probabilities("lyon", "Real Madrid")
    assert "not possible" in res.lower()
