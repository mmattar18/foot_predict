"""Streamlit web app for the explainable football match predictor.

Run with:
    streamlit run app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(
    page_title="AI Football Predictor",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------- #
# Secrets + optional password gate                                            #
# --------------------------------------------------------------------------- #

def _load_secrets_into_env() -> None:
    """Load secrets: `.env` locally, then `st.secrets` on Streamlit Cloud."""
    load_dotenv()
    for key in (
        "GROQ_API_KEY", "GROQ_MODEL", "FOOTBALL_DATA_API_KEY",
        "FOOTBALL_DATA_COMPETITIONS", "APP_PASSWORD", "DAILY_PREDICTION_LIMIT",
        "TAVILY_API_KEY",
    ):
        if not os.getenv(key):
            try:
                value = st.secrets[key]
            except Exception:  # noqa: BLE001 — no secrets file locally
                value = None
            if value:
                os.environ[key] = str(value)


def _check_password() -> bool:
    expected = os.getenv("APP_PASSWORD")
    if not expected or st.session_state.get("auth_ok"):
        return True
    st.title("🔒 Protected access")
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
# Styling                                                                     #
# --------------------------------------------------------------------------- #

st.markdown(
    """
    <style>
      #MainMenu, footer {visibility: hidden;}
      .block-container {padding-top: 2.2rem; max-width: 820px;}

      .hero {
        background:
          radial-gradient(circle at 50% 135%, rgba(255,255,255,.10) 0 30%, transparent 31%),
          linear-gradient(135deg, #0e5c2f 0%, #14803f 55%, #0b4a26 100%);
        border-radius:20px; padding:30px 30px 26px; color:#fff;
        box-shadow:0 14px 34px rgba(6,60,28,.30); margin-bottom:22px;
      }
      .hero h1 {margin:0; font-size:2.15rem; font-weight:800; letter-spacing:.2px;}
      .hero p {margin:.45rem 0 0; opacity:.9; font-size:1rem; font-weight:400;}

      .scorecard {
        background:#ffffff; border:1px solid #e7eae7; border-radius:18px;
        padding:22px 24px; text-align:center; box-shadow:0 8px 22px rgba(0,0,0,.07);
        margin:6px 0 14px;
      }
      .scorecard .teams {display:flex; align-items:center; justify-content:center;
        gap:18px; font-size:1.15rem; font-weight:700; color:#16181d;}
      .scorecard .score {font-size:2.3rem; font-weight:800; color:#0e5c2f;
        background:#eef6ef; border-radius:12px; padding:4px 16px; min-width:96px;}
      .scorecard .verdict {margin-top:12px; font-size:1.02rem; color:#3a3f44;}
      .scorecard .verdict b {color:#0e5c2f;}

      .prob-row {display:flex; gap:12px; margin:2px 0 6px;}
      .prob-card {flex:1; border-radius:14px; padding:13px 8px; text-align:center;
        color:#fff; box-shadow:0 4px 12px rgba(0,0,0,.12);}
      .prob-card.home {background:linear-gradient(160deg,#27a14e,#157a37);}
      .prob-card.draw {background:linear-gradient(160deg,#c79a2c,#937019);}
      .prob-card.away {background:linear-gradient(160deg,#d6554d,#a82e28);}
      .prob-card .lbl {font-size:.8rem; opacity:.95; font-weight:500;}
      .prob-card .val {font-size:1.65rem; font-weight:800; line-height:1.25;}

      div.stButton > button[kind="primary"] {
        background:#0e5c2f; border:0; font-weight:700; border-radius:11px;
        padding:.6rem 0; font-size:1.02rem;}
      div.stButton > button[kind="primary"]:hover {background:#0a4322;}
      .analysis {background:#fbfcfb; border:1px solid #eceeec; border-radius:14px;
        padding:6px 20px 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Sidebar (minimal settings)                                                  #
# --------------------------------------------------------------------------- #

has_fd_key = bool(os.getenv("FOOTBALL_DATA_API_KEY", "").strip())

st.sidebar.header("Settings")
mode = st.sidebar.radio(
    "Data",
    ["Live data", "Demo (offline)"],
    index=0 if has_fd_key else 1,
    help="Live data uses real clubs and national teams via football-data.org.",
)
USE_MOCK = mode.startswith("Demo")
os.environ["DATA_SOURCE"] = "mock" if USE_MOCK else "football-data"

# Project imports read the environment at call time (not at import): OK here.
from agents.predictor_agent import DEFAULT_MODEL, build_agent, build_query  # noqa: E402
from tools import football_data as fd  # noqa: E402
from tools.probability_tool import _lambdas, match_probabilities  # noqa: E402
from tools.providers import get_provider  # noqa: E402
from tools.utils import known_teams  # noqa: E402

has_groq_key = bool(os.getenv("GROQ_API_KEY", "").strip())
DAILY_LIMIT = int(os.getenv("DAILY_PREDICTION_LIMIT", "50"))


@st.cache_resource
def _usage_counter() -> dict:
    return {"date": None, "count": 0}


def _quota_left() -> int:
    import datetime

    today = datetime.date.today().isoformat()
    c = _usage_counter()
    if c["date"] != today:
        c["date"], c["count"] = today, 0
    return DAILY_LIMIT - c["count"] if DAILY_LIMIT > 0 else 10**9


st.sidebar.caption(f"Model: {DEFAULT_MODEL}")
if DAILY_LIMIT > 0:
    st.sidebar.caption(f"Predictions left today: {max(_quota_left(), 0)} / {DAILY_LIMIT}")
st.sidebar.markdown("---")
st.sidebar.caption(
    "Explainable predictions: recent form, head-to-head, injuries & news, "
    "schedule, and a Poisson model — with transparent reasoning."
)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner="Loading teams…")
def cached_list_teams(competition: str) -> list[str]:
    return fd.list_teams(competition)


def poisson_chart_data(team_a: str, team_b: str):
    provider = get_provider()
    home = provider.goal_averages(team_a)
    away = provider.goal_averages(team_b)
    if not home or not away:
        return None
    lam_home, lam_away = _lambdas(home, away)
    return match_probabilities(lam_home, lam_away), lam_home, lam_away


def run_prediction(team_a: str, team_b: str):
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


@st.cache_data(show_spinner=False, ttl=3600)
def cached_prediction(team_a: str, team_b: str, source: str):
    c = _usage_counter()
    c["count"] = c.get("count", 0) + 1
    return run_prediction(team_a, team_b)


# --------------------------------------------------------------------------- #
# Header + inputs                                                             #
# --------------------------------------------------------------------------- #

st.markdown(
    """
    <div class="hero">
      <h1>⚽ AI Football Predictor</h1>
      <p>Pick a match and get a data-driven prediction — with the reasoning behind it.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if USE_MOCK:
    teams = known_teams()
else:
    comp = st.selectbox(
        "Competition",
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

col_a, col_b = st.columns(2)
team_a = col_a.selectbox("Home team", teams, index=0)
team_b = col_b.selectbox("Away team", teams, index=1)

same_team = team_a == team_b
if same_team:
    st.warning("Pick two different teams.")
if not has_groq_key:
    st.error("The prediction engine is not configured (missing GROQ_API_KEY).")

predict = st.button(
    "Predict result", type="primary", use_container_width=True,
    disabled=same_team or not has_groq_key,
)


# --------------------------------------------------------------------------- #
# Result                                                                       #
# --------------------------------------------------------------------------- #

if predict:
    if _quota_left() <= 0:
        st.error(f"Daily limit reached ({DAILY_LIMIT}). Try again tomorrow.")
        st.stop()
    try:
        with st.spinner("Analyzing the match…"):
            steps, final = cached_prediction(team_a, team_b, os.environ["DATA_SOURCE"])
    except Exception as exc:  # noqa: BLE001
        st.error(f"Something went wrong: {exc}")
        st.stop()

    data = poisson_chart_data(team_a, team_b)
    if data:
        r, lam_home, lam_away = data
        outcomes = [
            (r["p_home"], f"{team_a} win"),
            (r["p_draw"], "a draw"),
            (r["p_away"], f"{team_b} win"),
        ]
        conf, verdict = max(outcomes, key=lambda x: x[0])
        h, a = r["best_score"]

        st.markdown(
            f"""
            <div class="scorecard">
              <div class="teams"><span>{team_a}</span>
                <span class="score">{h} – {a}</span><span>{team_b}</span></div>
              <div class="verdict">Most likely: <b>{verdict}</b>
                &nbsp;·&nbsp; {conf:.0%} confidence</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="prob-row">
              <div class="prob-card home"><div class="lbl">{team_a}</div>
                <div class="val">{r['p_home']:.0%}</div></div>
              <div class="prob-card draw"><div class="lbl">Draw</div>
                <div class="val">{r['p_draw']:.0%}</div></div>
              <div class="prob-card away"><div class="lbl">{team_b}</div>
                <div class="val">{r['p_away']:.0%}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            f"Expected goals: {team_a} {lam_home:.2f} · {team_b} {lam_away:.2f} "
            "— Poisson model."
        )

    if final:
        st.subheader("Match analysis")
        st.markdown(final)

    if steps:
        with st.expander("How the prediction was made (data & sources)"):
            for s in steps:
                st.markdown(f"**{s['name']}**")
                st.text(s["content"])
