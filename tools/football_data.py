"""Client pour l'API gratuite football-data.org (v4).

Inscription + clé gratuite : https://www.football-data.org/client/register
Authentification : en-tête HTTP `X-Auth-Token: <clé>`.

Plan gratuit : ~10 requêtes/minute et un sous-ensemble de compétitions
(Premier League, Liga, Serie A, Bundesliga, Ligue 1, etc.). Pour respecter ce
quota, toutes les réponses sont mises en cache sur disque (`.cache/`) avec une
durée de vie (TTL).

Ce module ne renvoie que des structures de données (dicts). La mise en forme
lisible est faite par `FootballDataProvider` dans `tools/providers.py`.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://api.football-data.org/v4"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "football_data"

# Compétitions scannées pour retrouver une équipe par son nom (plan gratuit).
# WC (Coupe du Monde) ajoute les sélections nationales.
DEFAULT_COMPETITIONS = ["PL", "PD", "SA", "BL1", "FL1", "DED", "PPL", "ELC", "WC"]


class FootballDataError(Exception):
    """Error from the API or network (human-readable message for the agent)."""


# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #

def api_key() -> str:
    return os.getenv("FOOTBALL_DATA_API_KEY", "").strip()


def is_configured() -> bool:
    return bool(api_key())


def competitions() -> list[str]:
    raw = os.getenv("FOOTBALL_DATA_COMPETITIONS", "").strip()
    if raw:
        return [c.strip().upper() for c in raw.split(",") if c.strip()]
    return DEFAULT_COMPETITIONS


# Human-readable competition labels (free tier) for the UI.
COMPETITION_NAMES = {
    "WC": "FIFA World Cup — national teams",
    "PL": "Premier League (England)",
    "PD": "La Liga (Spain)",
    "SA": "Serie A (Italy)",
    "BL1": "Bundesliga (Germany)",
    "FL1": "Ligue 1 (France)",
    "DED": "Eredivisie (Netherlands)",
    "PPL": "Primeira Liga (Portugal)",
    "ELC": "Championship (England D2)",
}


def list_teams(competition: str) -> list[str]:
    """Sorted, de-duplicated list of a competition's teams.

    Handles both a league (a single TOTAL block) and a group tournament such
    as the World Cup (one TOTAL block per group).
    """
    data = _get(f"{BASE_URL}/competitions/{competition}/standings", ttl=3600)
    return sorted({row["team"]["name"] for row in _all_total_rows(data)})


# --------------------------------------------------------------------------- #
# Couche HTTP + cache disque                                                  #
# --------------------------------------------------------------------------- #

def _cache_path(url: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha1(url.encode()).hexdigest()}.json"


def _get(url: str, ttl: int = 600) -> dict:
    """GET avec cache disque (TTL en secondes). Lève FootballDataError."""
    cp = _cache_path(url)
    if cp.exists() and (time.time() - cp.stat().st_mtime) < ttl:
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass  # cache corrompu : on refait l'appel

    key = api_key()
    if not key:
        raise FootballDataError(
            "FOOTBALL_DATA_API_KEY is missing. Sign up at football-data.org and "
            "set the key in .env."
        )

    req = urllib.request.Request(url, headers={"X-Auth-Token": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise FootballDataError(
                "Rate limit reached (10/min on the free tier). Try again in a "
                "minute."
            ) from exc
        if exc.code == 403:
            raise FootballDataError(
                "Restricted resource on the free tier (HTTP 403) — this "
                "competition/data is not available for free."
            ) from exc
        if exc.code in (400, 404):
            raise FootballDataError(
                f"Resource not found on the API (HTTP {exc.code})."
            ) from exc
        raise FootballDataError(f"HTTP {exc.code} error from football-data.org.") from exc
    except urllib.error.URLError as exc:
        raise FootballDataError(f"Network error: {exc.reason}.") from exc

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        cp.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass  # cache best-effort
    return data


# --------------------------------------------------------------------------- #
# Helpers de parsing                                                          #
# --------------------------------------------------------------------------- #

def _all_total_rows(standings_data: dict) -> list[dict]:
    """Toutes les lignes des blocs TOTAL (un championnat = 1 bloc ; un tournoi
    à groupes comme la Coupe du Monde = un bloc par groupe)."""
    rows = []
    for s in standings_data.get("standings", []):
        if s.get("type") == "TOTAL":
            rows.extend(s.get("table", []))
    return rows


def _result_for(match: dict, team_id: int) -> dict | None:
    """Interprète un match du point de vue de `team_id`. None si non joué."""
    ft = match.get("score", {}).get("fullTime", {})
    gh, ga = ft.get("home"), ft.get("away")
    if gh is None or ga is None:
        return None
    is_home = match["homeTeam"]["id"] == team_id
    gf, gc = (gh, ga) if is_home else (ga, gh)
    res = "W" if gf > gc else "D" if gf == gc else "L"
    return {
        "date": match["utcDate"][:10],
        "res": res,
        "gf": gf,
        "gc": gc,
        "is_home": is_home,
        "home_name": match["homeTeam"]["name"],
        "away_name": match["awayTeam"]["name"],
        "score": f"{gh}-{ga}",
    }


# --------------------------------------------------------------------------- #
# Recherche d'équipe + endpoints                                             #
# --------------------------------------------------------------------------- #

def find_team(name: str) -> dict | None:
    """Cherche une équipe par nom dans les compétitions configurées.

    Retourne {"id", "name", "competition", "row"} ou None. `row` est la ligne
    du classement TOTAL (position, points, buts, forme...).
    """
    if not is_configured():
        raise FootballDataError(
            "FOOTBALL_DATA_API_KEY is missing. Sign up at football-data.org and "
            "set the key in .env (or use DATA_SOURCE=mock)."
        )
    name_l = name.strip().lower()
    if not name_l:
        return None

    partial = None
    for comp in competitions():
        try:
            data = _get(f"{BASE_URL}/competitions/{comp}/standings", ttl=3600)
        except FootballDataError:
            continue
        for row in _all_total_rows(data):
            t = row["team"]
            exact = [t.get("name", ""), t.get("shortName") or "", t.get("tla") or ""]
            if any(name_l == n.lower() for n in exact if n):
                return {"id": t["id"], "name": t["name"], "competition": comp, "row": row}
            if partial is None:
                for n in (t.get("name", ""), t.get("shortName") or ""):
                    if n and name_l in n.lower():
                        partial = {
                            "id": t["id"], "name": t["name"],
                            "competition": comp, "row": row,
                        }
    return partial


def _finished_matches(team_id: int, days_back: int = 730) -> list[dict]:
    # Sans plage de dates, l'API se limite à la saison courante (vide en
    # intersaison). On remonte explicitement sur ~2 ans (au-delà, l'endpoint
    # renvoie HTTP 400 sur le plan gratuit).
    import datetime as _dt

    today = _dt.date.today()
    frm = (today - _dt.timedelta(days=days_back)).isoformat()
    url = (
        f"{BASE_URL}/teams/{team_id}/matches?status=FINISHED"
        f"&dateFrom={frm}&dateTo={today.isoformat()}"
    )
    matches = _get(url, ttl=3600).get("matches", [])
    matches.sort(key=lambda m: m.get("utcDate", ""))
    return matches


def recent_results(team_id: int, limit: int = 5) -> list[dict]:
    """Les `limit` derniers résultats (ordre chronologique : ancien -> récent)."""
    parsed = [r for m in _finished_matches(team_id) if (r := _result_for(m, team_id))]
    return parsed[-limit:]


def scheduled_matches(team_id: int, limit: int = 5) -> list[dict]:
    url = f"{BASE_URL}/teams/{team_id}/matches?status=SCHEDULED"
    matches = _get(url, ttl=600).get("matches", [])
    matches.sort(key=lambda m: m.get("utcDate", ""))
    return matches[:limit]


def head_to_head_matches(team_a_id: int, team_b_id: int, limit: int = 10) -> list[dict]:
    """Confrontations directes (matchs terminés) entre deux équipes."""
    meetings = [
        m
        for m in _finished_matches(team_a_id)
        if team_b_id in (m["homeTeam"]["id"], m["awayTeam"]["id"])
    ]
    meetings.sort(key=lambda m: m.get("utcDate", ""), reverse=True)
    return meetings[:limit]


# --------------------------------------------------------------------------- #
# Fonctions de haut niveau (dicts prêts à mettre en forme)                    #
# --------------------------------------------------------------------------- #

def get_team_stats(name: str) -> dict | None:
    ft = find_team(name)
    if ft is None:
        return None
    row = ft["row"]
    recent = recent_results(ft["id"], 5)
    form = [c for c in (row.get("form") or "").split(",") if c]
    if not form:  # some competitions don't expose the "form" field
        form = [r["res"] for r in recent]
    return {
        "name": ft["name"],
        "competition": ft["competition"],
        "position": row.get("position"),
        "played": row.get("playedGames"),
        "points": row.get("points"),
        "season_goals_for": row.get("goalsFor"),
        "season_goals_against": row.get("goalsAgainst"),
        "form": form,
        "goals_scored_last_5": sum(r["gf"] for r in recent),
        "goals_conceded_last_5": sum(r["gc"] for r in recent),
        "recent": recent,
    }


def get_goal_averages(name: str) -> dict | None:
    ft = find_team(name)
    if ft is None:
        return None
    recent = recent_results(ft["id"], 5)
    if not recent:
        return None
    n = len(recent)
    return {
        "name": ft["name"],
        "avg_scored": sum(r["gf"] for r in recent) / n,
        "avg_conceded": sum(r["gc"] for r in recent) / n,
        "matches_used": n,
    }
