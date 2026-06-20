# 🚀 Free deployment (Streamlit Community Cloud)

Goal: put the app online **without spending a cent**, with a **password** that
prevents strangers from burning your free-tier API quota.

Total cost: **$0** as long as you stay within the free tiers
(Streamlit Community Cloud + Groq + football-data.org).

---

## 🔐 How the keys are protected

- No key lives in the code or on GitHub: `.env` and
  `.streamlit/secrets.toml` are **git-ignored** (see `.gitignore`).
- Online, the keys live in **Streamlit Cloud's secret manager** (encrypted),
  injected via `st.secrets`.
- The app is protected by a **password** (`APP_PASSWORD`). Without it, no
  prediction can run → your Groq/football-data quota is safe from abuse.

---

## Step 1 — Put the code on GitHub

The local git repo is already initialized and committed. You just need to push
it to **your** GitHub account.

### Option A — with the GitHub CLI (`gh`)
```bash
cd sports-predictor-agent
gh repo create sports-predictor-agent --private --source=. --push
```

### Option B — manually
1. Create an empty repo at https://github.com/new (private recommended).
2. Then:
   ```bash
   cd sports-predictor-agent
   git branch -M main
   git remote add origin https://github.com/<your-username>/sports-predictor-agent.git
   git push -u origin main
   ```

> ✅ Check on GitHub that **`.env` does NOT appear** in the files. (It must not.)

---

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io** and sign in with GitHub (free).
2. Click **“Create app”** → **“Deploy a public/private app from GitHub”**.
3. Fill in:
   - **Repository**: `<your-username>/sports-predictor-agent`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Open **“Advanced settings” → “Secrets”** and paste (adapting the values) the
   contents of `.streamlit/secrets.toml.example`:
   ```toml
   APP_PASSWORD = "your-password"
   GROQ_API_KEY = "gsk_..."
   GROQ_MODEL = "llama-3.1-8b-instant"
   FOOTBALL_DATA_API_KEY = "..."
   FOOTBALL_DATA_COMPETITIONS = "WC,PL,PD,SA,BL1,FL1,DED,PPL,ELC"
   ```
5. Click **“Deploy”**. After a few minutes, the app is live at a
   `https://<your-app>.streamlit.app` URL.

On open, the app asks for the **password** before any prediction. 🎉

---

## Notes & free-tier limits

- **Groq**: free tier with per-minute request limits — plenty for a personal,
  password-protected demo.
- **football-data.org**: ~10 req/min, a subset of competitions. Responses are
  cached (`.cache/`) to limit calls. *(On the cloud this cache is ephemeral and
  rebuilds after each restart — at no extra cost.)*
- **Demo mode**: if you do **not** set `FOOTBALL_DATA_API_KEY`, the app starts
  in **mock** mode (fictional teams) — useful to show the app without exposing
  a key. `GROQ_API_KEY` is still required for the LLM reasoning.
- **Update the app**: a simple `git push` to `main` redeploys automatically.

---

## Security reminder

Your Groq and football-data keys were shared in plain text during development.
Before going public, **regenerate them**:
- Groq: https://console.groq.com/keys
- football-data.org: client area → regenerate the token

Then put the new values **only** in Streamlit Cloud secrets (and your local
`.env`), never in the code.
