"""Outil 6 — Modèle de probabilité (Poisson).

Fiabilise le pourcentage de confiance de l'agent par un calcul objectif et
reproductible, indépendant du LLM. On modélise le nombre de buts de chaque
équipe par une loi de Poisson, dont la moyenne (lambda) est estimée à partir
des moyennes de buts marqués/encaissés récentes, avec un avantage du terrain.

Pur Python (module `math`) — aucune dépendance lourde (pas de numpy/scipy).
"""

import math

from langchain_core.tools import tool

from tools.providers import get_provider

HOME_ADVANTAGE = 1.15   # offensive bonus at home
AWAY_FACTOR = 0.95      # slight away penalty
MAX_GOALS = 8           # score grid 0..8 (the tail beyond is negligible)

# Shrinkage (regression to the mean): with few matches, a team's averages are
# pulled toward a neutral baseline so one lucky game can't make it look
# unbeatable. PRIOR_GOALS = typical goals per team per game; PRIOR_STRENGTH =
# how many "average" matches of prior to mix in.
PRIOR_GOALS = 1.3
PRIOR_STRENGTH = 2.5


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def _shrink(avg: float, n: int) -> float:
    """Pull a per-game average toward PRIOR_GOALS based on sample size n."""
    return (avg * n + PRIOR_GOALS * PRIOR_STRENGTH) / (n + PRIOR_STRENGTH)


def _lambdas(home: dict, away: dict) -> tuple[float, float]:
    """Estimate each team's expected goals (lambda), with sample-size shrinkage."""
    nh = home.get("matches_used", 5)
    na = away.get("matches_used", 5)
    h_scored = _shrink(home["avg_scored"], nh)
    h_conceded = _shrink(home["avg_conceded"], nh)
    a_scored = _shrink(away["avg_scored"], na)
    a_conceded = _shrink(away["avg_conceded"], na)
    lam_home = (h_scored + a_conceded) / 2 * HOME_ADVANTAGE
    lam_away = (a_scored + h_conceded) / 2 * AWAY_FACTOR
    # guard against lambda = 0 (degenerate probabilities)
    return max(lam_home, 0.2), max(lam_away, 0.2)


def match_probabilities(lam_home: float, lam_away: float) -> dict:
    """Probabilités 1/N/2 et score le plus probable à partir des lambdas."""
    p_home = p_draw = p_away = 0.0
    best_p, best_score = -1.0, (0, 0)
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = _poisson_pmf(i, lam_home) * _poisson_pmf(j, lam_away)
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
            if p > best_p:
                best_p, best_score = p, (i, j)
    total = p_home + p_draw + p_away  # normalise la troncature de la grille
    return {
        "p_home": p_home / total,
        "p_draw": p_draw / total,
        "p_away": p_away / total,
        "best_score": best_score,
    }


def estimate_match_probabilities(team_a: str, team_b: str) -> str:
    """Estimate match probabilities with a Poisson model.

    From the two teams' recent goal averages (with a home advantage for team A),
    computes the probability of an A win, a draw, a B win, and the most likely
    score. Use it to anchor/calibrate the final confidence percentage.

    Args:
        team_a: Home team.
        team_b: Away team.
    """
    provider = get_provider()
    home = provider.goal_averages(team_a)
    away = provider.goal_averages(team_b)
    if home is None or away is None:
        missing = [n for n, d in ((team_a, home), (team_b, away)) if d is None]
        return (
            f"Poisson model not possible: goal data unavailable for "
            f"{', '.join(missing)}."
        )

    lam_home, lam_away = _lambdas(home, away)
    r = match_probabilities(lam_home, lam_away)
    bs = r["best_score"]
    n_home = home.get("matches_used", 0)
    n_away = away.get("matches_used", 0)
    lines = [
        f"Probability model (Poisson) {home['name']} (home) vs {away['name']} (away):",
        f"- Expected goals: {home['name']} {lam_home:.2f} — {away['name']} {lam_away:.2f}",
        f"- P({home['name']} win) = {r['p_home']:.0%}",
        f"- P(draw) = {r['p_draw']:.0%}",
        f"- P({away['name']} win) = {r['p_away']:.0%}",
        f"- Most likely score: {bs[0]}-{bs[1]}",
        f"- Sample: {n_home} match(es) for {home['name']}, "
        f"{n_away} for {away['name']}.",
    ]
    if min(n_home, n_away) < 3:
        lines.append(
            "  ⚠️ Small sample: estimate is unreliable (limited data via the free "
            "API, common for national teams). Weight it down."
        )
    return "\n".join(lines)


probability_tool = tool(estimate_match_probabilities)
