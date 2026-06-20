"""Streamlit interface on top of the explainable sports-prediction agent.

Run with:
    streamlit run app.py

Features:
- pick the competition + both teams (dynamic selectboxes);
- "Predict" button;
- agent reasoning step by step inside collapsible sections;
- final prediction + bar chart of probabilities (Poisson);
- mock / real-API toggle in the sidebar (demo possible without an API key);
- password gate to protect your free-tier API quota.
"""

import os

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="AI Football Predictor", page_icon="⚽", layout="centered")


# --------------------------------------------------------------------------- #
# Secrets + password gate                                                     #
# --------------------------------------------------------------------------- #

def _load_secrets_into_env() -> None:
    """Load secrets: `.env` locally, then `st.secrets` on Streamlit Cloud.
    A value already present in the environment is not overwritten."""
    load_dotenv()
    for key in (
        "GROQ_API_KEY", "GROQ_MODEL", "FOOTBALL_DATA_API_KEY",
        "FOOTBALL_DATA_COMPETITIONS", "APP_PASSWORD", "DAILY_PREDICTION_LIMIT",
    ):
        if not os.getenv(key):
            try:
                value = st.secrets[key]
            except Exception:  # noqa: BLE001 — no secrets file locally
                value = None
            if value:
                os.environ[key] = str(value)


def _check_password() -> bool:
    """Shared-password gate (APP_PASSWORD). Without a configured password,
    access is open (handy locally)."""
    expected = os.getenv("APP_PASSWORD")
    if not expected:
        return True
    if st.session_state.get("auth_ok"):
        return True
    st.title("🔒 Protected access")
    st.caption("Private app — enter the password to continue.")
    with st.form("login"):
        pwd = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        if pwd == expected:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    return False


_load_secrets_into_env()
if not _check_password():
    st.stop()


# --------------------------------------------------------------------------- #
# Football-themed styling                                                     #
# --------------------------------------------------------------------------- #

st.markdown(
    """
    <style>
      .hero {
        background:
          radial-gradient(circle at 50% 120%, rgba(255,255,255,.10) 0 28%, transparent 29%),
          repeating-linear-gradient(90deg, #1b7a35 0 38px, #15692e 38px 76px);
        border:1px solid rgba(255,255,255,.18);
        border-radius:18px; padding:26px 28px; color:#fff; margin-bottom:18px;
        box-shadow:0 10px 28px rgba(0,0,0,.20);
      }
      .hero h1 { margin:0; font-size:2.05rem; letter-spacing:.3px; }
      .hero p  { margin:.35rem 0 0; opacity:.92; font-size:.98rem; }
      .matchup { display:flex; align-items:center; justify-content:center;
                 gap:14px; margin:6px 0 2px; }
      .team-chip { background:#0e1117; color:#fff; border:1px solid #2e7d32;
                   border-radius:999px; padding:8px 16px; font-weight:600; }
      .vs-badge { background:#f9a825; color:#1b1b1b; font-weight:800;
                  border-radius:999px; padding:6px 12px; box-shadow:0 2px 8px rgba(0,0,0,.25); }
      .prob-row { display:flex; gap:12px; margin:6px 0 4px; }
      .prob-card { flex:1; border-radius:14px; padding:14px 10px; text-align:center;
                   color:#fff; box-shadow:0 4px 14px rgba(0,0,0,.18); }
      .prob-card.home { background:linear-gradient(160deg,#2e9e4b,#1b7a35); }
      .prob-card.draw { background:linear-gradient(160deg,#b9902b,#8a6d1f); }
      .prob-card.away { background:linear-gradient(160deg,#d4574f,#a8302a); }
      .prob-card .lbl { font-size:.85rem; opacity:.95; }
      .prob-card .val { font-size:1.7rem; font-weight:800; line-height:1.2; }
      div.stButton > button[kind="primary"] {
        background:#2e7d32; border:0; font-weight:700; border-radius:10px; }
      div.stButton > button[kind="primary"]:hover { background:#1b5e20; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Sidebar: data source                                                        #
# --------------------------------------------------------------------------- #

st.sidebar.title("⚙️ Settings")

if os.getenv("APP_PASSWORD") and st.session_state.get("auth_ok"):
    if st.sidebar.button("🔓 Log out"):
        st.session_state["auth_ok"] = False
        st.rerun()

has_fd_key = bool(os.getenv("FOOTBALL_DATA_API_KEY", "").strip())
default_mode = 0 if has_fd_key else 1
mode = st.sidebar.radio(
    "Data source",
    ["🌍 Real API (football-data.org)", "🧪 Mock (demo, no API key)"],
    index=default_mode,
    help="Mock mode works offline with fictional teams.",
)
USE_MOCK = mode.startswith("🧪")
# get_provider() reads DATA_SOURCE on every call: we set it from the choice.
os.environ["DATA_SOURCE"] = "mock" if USE_MOCK else "football-data"

# Project imports read the environment at call time (not at import): OK here.
from agents.predictor_agent import DEFAULT_MODEL, build_agent, build_query  # noqa: E402
from tools import football_data as fd  # noqa: E402
from tools.probability_tool import _lambdas, match_probabilities  # noqa: E402
from tools.providers import get_provider  # noqa: E402
from tools.utils import known_teams  # noqa: E402

has_groq_key = bool(os.getenv("GROQ_API_KEY", "").strip())
if has_groq_key:
    st.sidebar.success(f"LLM: {DEFAULT_MODEL}")
else:
    st.sidebar.error("GROQ_API_KEY missing in secrets — prediction will fail.")
st.sidebar.caption(
    "football-data.org "
    + ("✅ key detected" if has_fd_key else "❌ no key (use mock mode)")
)

TOOL_ICONS = {
    "get_team_stats": "📊",
    "get_head_to_head": "🤝",
    "get_injuries": "🏥",
    "search_team_news": "📰",
    "get_upcoming_matches": "📅",
    "estimate_match_probabilities": "🎲",
}


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner="Loading teams…")
def cached_list_teams(competition: str) -> list[str]:
    return fd.list_teams(competition)


def poisson_chart_data(team_a: str, team_b: str):
    """Probabilities 1/X/2 computed directly (independent of the LLM)."""
    provider = get_provider()
    home = provider.goal_averages(team_a)
    away = provider.goal_averages(team_b)
    if not home or not away:
        return None
    lam_home, lam_away = _lambdas(home, away)
    return match_probabilities(lam_home, lam_away), lam_home, lam_away


def run_prediction(team_a: str, team_b: str):
    """Run the agent and collect the steps + final answer."""
    agent = build_agent()
    query = build_query(team_a, team_b)
    call_args: dict[str, tuple] = {}
    steps: list[dict] = []
    final = ""
    for chunk in agent.stream({"messages": [("user", query)]}, stream_mode="updates"):
        for _node, update in chunk.items():
            for msg in update.get("messages", []):
                cls = msg.__class__.__name__
                tool_calls = getattr(msg, "tool_calls", None)
                if cls == "AIMessage" and tool_calls:
                    for c in tool_calls:
                        call_args[c["id"]] = (c["name"], c["args"])
                elif cls == "ToolMessage":
                    name, args = call_args.get(
                        getattr(msg, "tool_call_id", None), (msg.name, {})
                    )
                    steps.append({"name": name, "args": args, "content": str(msg.content)})
                elif cls == "AIMessage" and msg.content:
                    final = msg.content
    return steps, final


# --- Usage cap (no password needed) ---------------------------------------
# Caps the number of *real* API-backed predictions per day, and caches results
# so the same matchup never re-calls the APIs. 0 = unlimited.
DAILY_LIMIT = int(os.getenv("DAILY_PREDICTION_LIMIT", "50"))


@st.cache_resource
def _usage_counter() -> dict:
    """Shared across sessions for one app instance (resets on restart)."""
    return {"date": None, "count": 0}


def _quota_left() -> int:
    import datetime

    today = datetime.date.today().isoformat()
    c = _usage_counter()
    if c["date"] != today:
        c["date"], c["count"] = today, 0
    return DAILY_LIMIT - c["count"] if DAILY_LIMIT > 0 else 10**9


@st.cache_data(show_spinner=False, ttl=3600)
def cached_prediction(team_a: str, team_b: str, source: str):
    """Cached by matchup+source. Its body runs only on a cache MISS, i.e. a
    real API call — so that is where we increment the daily counter."""
    c = _usage_counter()
    c["count"] = c.get("count", 0) + 1
    return run_prediction(team_a, team_b)


# --------------------------------------------------------------------------- #
# Header                                                                       #
# --------------------------------------------------------------------------- #

st.markdown(
    """
    <div class="hero">
      <h1>⚽ AI Football Match Predictor</h1>
      <p>Explainable predictions: the agent blends stats, head-to-head, schedule
      and a Poisson model — then walks you through its reasoning step by step.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if USE_MOCK:
    st.info("**Demo mode (mock)**: fictional teams, no connection required.")
    teams = known_teams()
else:
    comp = st.selectbox(
        "🏆 Competition",
        options=list(fd.COMPETITION_NAMES),
        format_func=lambda c: fd.COMPETITION_NAMES[c],
    )
    try:
        teams = cached_list_teams(comp)
    except fd.FootballDataError as exc:
        st.error(f"Could not load teams: {exc}")
        st.stop()

if len(teams) < 2:
    st.warning("Not enough teams available.")
    st.stop()

col_a, col_vs, col_b = st.columns([5, 1, 5])
team_a = col_a.selectbox("🏠 Team A (home)", teams, index=0)
col_vs.markdown("<div style='text-align:center;padding-top:32px;'><span class='vs-badge'>VS</span></div>", unsafe_allow_html=True)
team_b = col_b.selectbox("✈️ Team B (away)", teams, index=1)

st.markdown(
    f"<div class='matchup'><span class='team-chip'>🏠 {team_a}</span>"
    f"<span class='vs-badge'>VS</span>"
    f"<span class='team-chip'>✈️ {team_b}</span></div>",
    unsafe_allow_html=True,
)

same_team = team_a == team_b
if same_team:
    st.warning("Pick two different teams.")

predict = st.button(
    "🔮 Predict", type="primary", use_container_width=True,
    disabled=same_team or not has_groq_key,
)
if DAILY_LIMIT > 0:
    st.caption(f"🎟️ Predictions left today: {max(_quota_left(), 0)} / {DAILY_LIMIT} "
               "(repeating the same matchup is free — cached).")

if predict:
    if _quota_left() <= 0:
        st.error(
            f"Daily limit reached ({DAILY_LIMIT} predictions) to protect API "
            "quota. Try again tomorrow, or rerun a matchup you already requested "
            "(those are cached and free)."
        )
        st.stop()
    try:
        with st.spinner("The agent is consulting its tools and reasoning…"):
            steps, final = cached_prediction(team_a, team_b, os.environ["DATA_SOURCE"])
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error while running the agent: {exc}")
        st.stop()

    # --- Final prediction + chart (shown first for impact) -----------------
    st.subheader("🏆 Final prediction")

    data = poisson_chart_data(team_a, team_b)
    if data:
        r, lam_home, lam_away = data
        st.markdown(
            f"<div class='prob-row'>"
            f"<div class='prob-card home'><div class='lbl'>🏠 {team_a} win</div>"
            f"<div class='val'>{r['p_home']:.0%}</div></div>"
            f"<div class='prob-card draw'><div class='lbl'>🤝 Draw</div>"
            f"<div class='val'>{r['p_draw']:.0%}</div></div>"
            f"<div class='prob-card away'><div class='lbl'>✈️ {team_b} win</div>"
            f"<div class='val'>{r['p_away']:.0%}</div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        chart_df = pd.DataFrame(
            {
                "Outcome": [f"{team_a} win", "Draw", f"{team_b} win"],
                "Probability": [r["p_home"], r["p_draw"], r["p_away"]],
                "Color": ["#2e9e4b", "#b9902b", "#d4574f"],
            }
        )
        bar = (
            alt.Chart(chart_df)
            .mark_bar(cornerRadiusEnd=7, height=34)
            .encode(
                x=alt.X("Probability:Q", axis=alt.Axis(format="%"),
                        scale=alt.Scale(domain=[0, 1]), title=None),
                y=alt.Y("Outcome:N", sort=None, title=None),
                color=alt.Color("Color:N", scale=None, legend=None),
                tooltip=[alt.Tooltip("Outcome:N"),
                         alt.Tooltip("Probability:Q", format=".0%")],
            )
            .properties(height=170)
        )
        st.altair_chart(bar, use_container_width=True)
        st.caption(
            f"🎲 Poisson model — most likely score: "
            f"**{r['best_score'][0]}-{r['best_score'][1]}** · "
            f"expected goals: {team_a} {lam_home:.2f} / {team_b} {lam_away:.2f}"
        )
    else:
        st.caption("Poisson probabilities unavailable (missing goal data).")

    # --- Agent's written analysis ------------------------------------------
    if final:
        st.markdown("#### 📝 Agent analysis")
        st.markdown(final)

    # --- Step-by-step reasoning (collapsible) ------------------------------
    st.subheader("🧠 Step-by-step reasoning (tool by tool)")
    for s in steps:
        icon = TOOL_ICONS.get(s["name"], "🔧")
        arg_str = ", ".join(f"{k}={v}" for k, v in s["args"].items())
        label = f"{icon} {s['name']}({arg_str})"
        with st.expander(label, expanded=s["name"] == "estimate_match_probabilities"):
            st.text(s["content"])
