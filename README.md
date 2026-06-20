# ⚽ Explainable AI Football Match Predictor

An agent that predicts a football match result **and explains its reasoning
step by step** (visible chain-of-thought), cross-referencing several data
sources through *tools* — instead of spitting out a raw result.

Built with **LangGraph** for orchestration and the **Groq API (LLaMA 3.1)** as
the LLM (free and very fast). Data can come from **simulated data** (offline)
or the **real football-data.org API** (standings, form, head-to-head,
schedule — including the **FIFA World Cup**).

---

## 🧠 The idea

A bettor or analyst doesn't settle for a tip: they want to know *why*. This
agent mimics that approach:

1. It **collects** data through 6 tools.
2. It **analyzes each factor separately**, assigning a weight.
3. It **combines** the factors into structured reasoning.
4. It gives a **final prediction + a confidence %**.
5. It **justifies** its conclusion by citing the data used.

---

## 🏗️ Architecture

```
                 ┌──────────────────────────────┐
   User       →  │   app.py (Streamlit)         │
   (2 teams)     │   main.py (CLI)              │
                 └──────────────┬───────────────┘
                                │  build_query()
                                ▼
                 ┌──────────────────────────────┐
                 │  ReAct agent (LangGraph)     │
                 │  agents/predictor_agent.py   │
                 │  LLM = Groq / LLaMA 3.1      │
                 └──────────────┬───────────────┘
              the LLM chooses which tools to call
                                ▼
   ┌───────────┬───────────┬───────────┬───────────┬───────────┬──────────┐
   │stats_tool │history    │injury     │news_search│upcoming   │probability│
   │form,goals,│_tool      │_tool      │_tool      │_tool      │_tool      │
   │standing   │H2H        │absences   │morale/news│schedule   │Poisson 1X2│
   └─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴────┬─────┘
         └───────────┴───────────┴─── tools/providers.py ──────────┘
                                ▼
              ┌─────────────────────────────────────────┐
              │  Provider layer (switched by env)       │
              ├──────────────────┬──────────────────────┤
              │  MockProvider    │  FootballDataProvider │
              │  teams_mock.json │  football-data.org API│
              └──────────────────┴──────────────────────┘
                                ▼
            Structured reasoning + prediction + confidence
                 (the % is anchored on the Poisson model)
```

The agent is a **ReAct agent** (`create_react_agent` from LangGraph): the LLM
decides which tools to call and in what order (a *reason → act → observe* loop),
then writes the final synthesis following the format set by the system prompt.

The **provider layer** (`tools/providers.py`) decouples the tools from the data
source: the same 6 tools behave identically whether the data is simulated or
real. The switch is done via the `DATA_SOURCE` environment variable
(`auto` / `mock` / `football-data`).

### Project structure

```
sports-predictor-agent/
├── app.py                        # Streamlit web interface
├── main.py                       # Entry point — CLI
├── agents/
│   └── predictor_agent.py        # Agent build + system prompt
├── tools/
│   ├── stats_tool.py             # Tool 1 — recent stats
│   ├── history_tool.py           # Tool 2 — head-to-head
│   ├── injury_tool.py            # Tool 3 — injuries / absences
│   ├── news_search_tool.py       # Tool 4 — qualitative news
│   ├── upcoming_tool.py          # Tool 5 — upcoming matches
│   ├── probability_tool.py       # Tool 6 — Poisson model (1/X/2)
│   ├── providers.py              # Mock / football-data.org switch
│   ├── football_data.py          # football-data.org API client (+ cache)
│   └── utils.py                  # Mock loading + name resolution
├── data/
│   └── teams_mock.json           # 5 fictional teams, realistic stats
├── tests/
│   ├── test_tools.py             # Tests for the 4 data tools
│   ├── test_upcoming.py          # Schedule tool tests
│   ├── test_probability.py       # Poisson model tests
│   └── test_football_data.py     # API client parsing tests (offline)
├── requirements.txt
├── .env.example
├── DEPLOY.md                     # Free deployment guide (Streamlit Cloud)
└── README.md
```

---

## 🚀 Install & run

### 1. Requirements
- Python 3.10+
- A **Groq** API key (free): https://console.groq.com/keys

### 2. Install

```bash
cd sports-predictor-agent
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure keys

```bash
cp .env.example .env        # then edit .env
```

- `GROQ_API_KEY` (**required**) — Groq key for the LLM.
- `FOOTBALL_DATA_API_KEY` (**optional**) — for real data.
- `DATA_SOURCE` — `auto` (default), `mock` or `football-data`.
- `APP_PASSWORD` (**optional**) — protects the web app behind a password.

Without a football-data key, the agent runs in `mock` mode (offline): no extra
configuration is needed to test.

### 4. Run

**Web interface (Streamlit)** — recommended:

```bash
streamlit run app.py
```

- two `selectbox`es populated dynamically from the chosen competition
  (Premier League, La Liga, Serie A, **FIFA World Cup**…);
- a **Predict** button;
- the agent's reasoning in collapsible sections (`st.expander`), including the
  Poisson computation detail;
- final prediction + **bar chart** of the probabilities (A win / draw / B win);
- **mock / real-API toggle** in the sidebar (demo possible without an API key);
- football-themed design and an optional **password gate**.

**Command line (CLI)**:

```bash
# Interactive mode (the agent asks for both teams)
python main.py

# Or directly via arguments (partial names accepted in mock)
python main.py "lyon" "marseille"
python main.py "Arsenal FC" "Chelsea FC"   # real-API mode
```

### 5. Tests

```bash
pytest -v
```

The tests check that **each tool returns the expected data** (known team,
partial name, unknown team, fully fit squad, World-Cup group aggregation, etc.).
They do **not** require an API key.

---

## 🟢 Available teams (mock data)

| Team             | Position | Form (last 5) |
|------------------|:--------:|:-------------:|
| Marseille Tigers | 1st      | W W W D W     |
| Lyon Dragons     | 2nd      | W W D L W     |
| Bordeaux Wolves  | 3rd      | W D W W D     |
| Paris Eagles     | 4th      | L D W L D     |
| Rennes Falcons   | 7th      | L L D W L     |

> Mock data lives in `data/teams_mock.json` and powers offline mode and tests.

---

## 🌍 Real data — football-data.org API

To use **real data** (real clubs, real standings):

1. Create a free account: https://www.football-data.org/client/register
2. Put your API key in `.env`:
   ```bash
   FOOTBALL_DATA_API_KEY=your_key
   DATA_SOURCE=football-data        # or leave it "auto"
   ```
3. Run with the **official name** of clubs or national teams:
   ```bash
   python main.py "Arsenal FC" "Chelsea FC"   # clubs (Premier League)
   python main.py "France" "Spain"            # World Cup (national teams)
   ```

What the API provides (via `tools/football_data.py`):

| Data                                | football-data.org endpoint              |
|-------------------------------------|-----------------------------------------|
| Standings + form (last 5)           | `/competitions/{code}/standings`        |
| Recent goals scored/conceded        | `/teams/{id}/matches?status=FINISHED`   |
| Head-to-head (H2H)                   | finished matches filtered by opponent   |
| Upcoming matches (schedule)         | `/teams/{id}/matches?status=SCHEDULED`  |

> ⚠️ **Free tier**: ~10 requests/minute and a subset of competitions — clubs
> (PL, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira Liga,
> Championship) **and the World Cup `WC`** (national teams). All responses are
> **cached on disk** (`.cache/`) to respect this quota.
>
> 🏆 **World Cup / national teams**: the standings are split into groups — the
> code automatically aggregates the 12 groups (48 teams). Note that the free
> API does not cover every national-team competition (CONMEBOL qualifiers,
> etc.), so some teams have few recent matches. The tools then **show the
> sample size and a reliability warning**, which the agent takes into account.
>
> 🗓️ **Off-season**: finished matches are fetched over a ~2-year sliding
> window (`dateFrom`/`dateTo`), so form, head-to-head and the Poisson model
> stay available even when the new league season has not started yet.
>
> ℹ️ football-data.org provides **neither injuries nor news**. In real-API mode
> those two tools fall back to a **free web search** (`tools/web_search.py`):
> **DuckDuckGo** by default (no key), or **Tavily** automatically if you set a
> free `TAVILY_API_KEY` (more reliable on the cloud).

The architecture is **decoupled**: to add another source (API-Football, etc.),
just write a new provider in `tools/providers.py` — the tools and the agent stay
unchanged.

---

## 🎲 The Poisson model

`tools/probability_tool.py` is a **pure-Python** statistical model (no heavy
dependency): it estimates each team's expected goals (λ) from their recent goal
averages plus a home advantage, then computes **P(A win) / P(draw) / P(B win)**
over a score grid and the most likely score. The agent calls it to **anchor its
confidence %** on an objective computation, independent of the LLM. The
Streamlit chart is built directly from these numbers (not by parsing the LLM
text), so it is always exact.

---

## ☁️ Deployment

See **[`DEPLOY.md`](DEPLOY.md)** for a step-by-step **free** deployment on
Streamlit Community Cloud, with password protection and secure secret handling.

---

## 🔌 Possible improvements
- ✅ ~~Plug in a real sports data API~~ → football-data.org integrated.
- ✅ ~~Probability model (Poisson) to calibrate the %~~ → `probability_tool`.
- Replace the `news_search_tool` mock with a real web search (Tavily,
  DuckDuckGo, SerpAPI).
- Fetch injuries from a dedicated source (the free API does not provide them).
- Add a knockout-stage flow for the World Cup once the group stage is over.
