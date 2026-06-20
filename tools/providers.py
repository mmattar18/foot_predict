"""Data-source abstraction layer.

Two providers expose the SAME interface (LLM-readable strings):

- `MockProvider`         : simulated data from `data/teams_mock.json` (offline).
- `FootballDataProvider` : real data from the football-data.org API.

The active provider is chosen by the DATA_SOURCE environment variable:
- "mock"          -> always simulated data;
- "football-data" -> always the real API;
- "auto" (default)-> real API if FOOTBALL_DATA_API_KEY is set, otherwise mock.

Note: football-data.org provides neither injuries nor news; for those two
dimensions the real provider explicitly tells the agent the data is missing.
"""

import os

from tools import football_data as fd
from tools.utils import find_team as find_mock_team
from tools.utils import known_teams, load_data

_FORM_LABEL = {"W": "Win", "D": "Draw", "L": "Loss"}


# --------------------------------------------------------------------------- #
# Provider: mock data                                                         #
# --------------------------------------------------------------------------- #

class MockProvider:
    name = "mock (simulated data)"

    def _team(self, team_name):
        teams = load_data()["teams"]
        key = find_mock_team(team_name, teams)
        return key, (teams[key] if key else None)

    def team_stats(self, team_name: str) -> str:
        key, t = self._team(team_name)
        if not key:
            return _unknown(team_name)
        form = " ".join(t["form_last_5"])
        points = sum(3 if r == "W" else 1 if r == "D" else 0 for r in t["form_last_5"])
        detail = ", ".join(_FORM_LABEL[r] for r in t["form_last_5"])
        return (
            f"Stats for {key}:\n"
            f"- League position: {t['league_position']}\n"
            f"- Form (last 5, oldest -> newest): {form} ({detail})\n"
            f"- Points from these 5 games: {points}/15\n"
            f"- Goals scored (last 5): {t['goals_scored_last_5']}\n"
            f"- Goals conceded (last 5): {t['goals_conceded_last_5']}\n"
            f"- Goal difference (last 5): "
            f"{t['goals_scored_last_5'] - t['goals_conceded_last_5']:+d}\n"
            f"- Home strength: {t['home_strength']:.0%}\n"
            f"- Away strength: {t['away_strength']:.0%}"
        )

    def head_to_head(self, team_a: str, team_b: str) -> str:
        data = load_data()
        teams = data["teams"]
        ka = find_mock_team(team_a, teams)
        kb = find_mock_team(team_b, teams)
        if not ka or not kb:
            missing = [n for n, k in ((team_a, ka), (team_b, kb)) if not k]
            return _unknown(", ".join(missing))
        if ka == kb:
            return "Invalid: both teams are the same."
        meetings = sorted(
            (m for m in data["head_to_head"] if {m["home"], m["away"]} == {ka, kb}),
            key=lambda m: m["date"], reverse=True,
        )
        if not meetings:
            return f"No recorded head-to-head meetings between {ka} and {kb}."
        wa = wb = draws = 0
        lines = []
        for m in meetings:
            g = _winner(m["home"], m["away"], m["score"])
            wa, wb, draws = (
                (wa + 1, wb, draws) if g == ka
                else (wa, wb + 1, draws) if g == kb
                else (wa, wb, draws + 1)
            )
            lines.append(f"- {m['date']}: {m['home']} {m['score']} {m['away']} (-> {g})")
        return (
            f"Head-to-head {ka} vs {kb} ({len(meetings)} match(es)):\n"
            + "\n".join(lines)
            + f"\n\nRecord: {ka} {wa} win(s), {kb} {wb} win(s), {draws} draw(s)."
        )

    def injuries(self, team_name: str) -> str:
        key, t = self._team(team_name)
        if not key:
            return _unknown(team_name)
        inj = t.get("injuries", [])
        if not inj:
            return f"{key}: no absences reported, squad fully fit."
        keys = sum(1 for i in inj if i.get("importance") == "key")
        lines = [
            f"- {i['player']} ({i['position']}): {i['status']} "
            f"— importance {i['importance']} — {i['reason']}"
            for i in inj
        ]
        return (
            f"Absences for {key} ({len(inj)} player(s), {keys} key player(s)):\n"
            + "\n".join(lines)
        )

    def news(self, team_name: str) -> str:
        key, t = self._team(team_name)
        if not key:
            return _unknown(team_name)
        news = t.get("news", [])
        if not news:
            return f"No recent news found for {key}."
        return f"Recent news on {key}:\n" + "\n".join(f"- {n}" for n in news)

    def upcoming(self, team_name: str) -> str:
        data = load_data()
        key = find_mock_team(team_name, data["teams"])
        if not key:
            return _unknown(team_name)
        matches = sorted(
            (m for m in data.get("upcoming", []) if key in (m["home"], m["away"])),
            key=lambda m: m["date"],
        )
        if not matches:
            return f"No upcoming matches scheduled for {key}."
        lines = [
            f"- {m['date']}: {m['home']} vs {m['away']} ({m.get('competition', '')})"
            for m in matches
        ]
        return f"Upcoming matches for {key}:\n" + "\n".join(lines)

    def goal_averages(self, team_name: str):
        key, t = self._team(team_name)
        if not key:
            return None
        n = len(t["form_last_5"]) or 1
        return {
            "name": key,
            "avg_scored": t["goals_scored_last_5"] / n,
            "avg_conceded": t["goals_conceded_last_5"] / n,
            "matches_used": n,
        }


# --------------------------------------------------------------------------- #
# Provider: football-data.org API                                             #
# --------------------------------------------------------------------------- #

class FootballDataProvider:
    name = "football-data.org (real API)"

    def team_stats(self, team_name: str) -> str:
        try:
            s = fd.get_team_stats(team_name)
        except fd.FootballDataError as e:
            return f"[football-data.org] {e}"
        if s is None:
            return _not_found_api(team_name)
        form = " ".join(s["form"]) if s["form"] else "n/a"
        lines = [f"Stats for {s['name']} ({s['competition']}, real data):"]
        played = s.get("played") or 0
        if played > 0:
            lines.append(
                f"- League position: {s['position']} "
                f"({s['points']} pts in {played} games)"
            )
            lines.append(
                f"- Season goals: {s['season_goals_for']} scored / "
                f"{s['season_goals_against']} conceded"
            )
        else:
            lines.append(
                "- League season not started yet (off-season): analysis based on "
                "the form and goals of the last 5 games played."
            )
        n_recent = len(s.get("recent", []))
        lines.append(f"- Form (last {n_recent} played): {form}")
        lines.append(f"- Goals scored (last {n_recent}): {s['goals_scored_last_5']}")
        lines.append(f"- Goals conceded (last {n_recent}): {s['goals_conceded_last_5']}")
        if n_recent < 5:
            lines.append(
                f"- ⚠️ Only {n_recent} recent match(es) available via the API "
                "(limited free-tier coverage)."
            )
        return "\n".join(lines)

    def head_to_head(self, team_a: str, team_b: str) -> str:
        try:
            fa = fd.find_team(team_a)
            fb = fd.find_team(team_b)
            if not fa or not fb:
                missing = [n for n, f in ((team_a, fa), (team_b, fb)) if not f]
                return _not_found_api(", ".join(missing))
            if fa["id"] == fb["id"]:
                return "Invalid: both teams are the same."
            meetings = fd.head_to_head_matches(fa["id"], fb["id"], limit=10)
        except fd.FootballDataError as e:
            return f"[football-data.org] {e}"
        if not meetings:
            return f"No head-to-head meetings found between {fa['name']} and {fb['name']}."
        wa = wb = draws = 0
        lines = []
        for m in meetings:
            r = fd._result_for(m, fa["id"])
            if r is None:
                continue
            if r["res"] == "W":
                wa += 1
                g = fa["name"]
            elif r["res"] == "L":
                wb += 1
                g = fb["name"]
            else:
                draws += 1
                g = "Draw"
            lines.append(
                f"- {r['date']}: {r['home_name']} {r['score']} {r['away_name']} (-> {g})"
            )
        return (
            f"Head-to-head {fa['name']} vs {fb['name']} "
            f"({len(lines)} match(es), real data):\n" + "\n".join(lines)
            + f"\n\nRecord: {fa['name']} {wa} win(s), "
            f"{fb['name']} {wb} win(s), {draws} draw(s)."
        )

    def injuries(self, team_name: str) -> str:
        return (
            "Not available: the football-data.org API (free tier) does not provide "
            "injuries/absences. Treat this as missing data, or plug in another "
            "source."
        )

    def news(self, team_name: str) -> str:
        return (
            "Not available: the football-data.org API does not provide qualitative "
            "news. Plug in a real web search (Tavily/SerpAPI) if needed."
        )

    def upcoming(self, team_name: str) -> str:
        try:
            ft = fd.find_team(team_name)
            if not ft:
                return _not_found_api(team_name)
            matches = fd.scheduled_matches(ft["id"], limit=5)
        except fd.FootballDataError as e:
            return f"[football-data.org] {e}"
        if not matches:
            return f"No upcoming matches scheduled for {ft['name']}."
        lines = [
            f"- {m['utcDate'][:10]}: {m['homeTeam']['name']} vs "
            f"{m['awayTeam']['name']} ({m.get('competition', {}).get('name', '')})"
            for m in matches
        ]
        return f"Upcoming matches for {ft['name']} (real data):\n" + "\n".join(lines)

    def goal_averages(self, team_name: str):
        try:
            return fd.get_goal_averages(team_name)
        except fd.FootballDataError:
            return None


# --------------------------------------------------------------------------- #
# Helpers + provider selection                                                #
# --------------------------------------------------------------------------- #

def _unknown(name: str) -> str:
    return (
        f"No team found for '{name}'. "
        f"Available teams (mock): {', '.join(known_teams())}."
    )


def _not_found_api(name: str) -> str:
    return (
        f"Team '{name}' not found in the searched competitions "
        f"({', '.join(fd.competitions())}). Try the full official name "
        f"(e.g. 'Arsenal FC', 'Real Madrid CF')."
    )


def _winner(home: str, away: str, score: str) -> str:
    try:
        gh, ga = (int(x) for x in score.split("-"))
    except ValueError:
        return "?"
    return home if gh > ga else away if ga > gh else "Draw"


def get_provider():
    src = os.getenv("DATA_SOURCE", "auto").strip().lower()
    if src == "mock":
        return MockProvider()
    if src in ("football-data", "football_data", "api"):
        return FootballDataProvider()
    return FootballDataProvider() if fd.is_configured() else MockProvider()


def data_source_name() -> str:
    return get_provider().name
