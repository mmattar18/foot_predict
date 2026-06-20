# 🚀 Déploiement gratuit (Streamlit Community Cloud)

Objectif : mettre l'app en ligne **sans dépenser un centime**, avec un **mot de
passe** qui empêche des inconnus de consommer ton quota d'API gratuites.

Coût total : **0 €** tant que tu restes dans les tiers gratuits
(Streamlit Community Cloud + Groq + football-data.org).

---

## 🔐 Comment les clés sont protégées

- Aucune clé n'est dans le code ni sur GitHub : `.env` et
  `.streamlit/secrets.toml` sont **ignorés par git** (voir `.gitignore`).
- En ligne, les clés vivent dans le **gestionnaire de secrets de Streamlit
  Cloud** (chiffré), injectées via `st.secrets`.
- L'app est protégée par un **mot de passe** (`APP_PASSWORD`). Sans lui,
  impossible de lancer une prédiction → ton quota Groq/football-data est à
  l'abri des abus.

---

## Étape 1 — Mettre le code sur GitHub

Le dépôt git local est déjà initialisé et committé. Il te reste à le pousser
sur **ton** compte GitHub.

### Option A — avec le CLI GitHub (`gh`)
```bash
cd sports-predictor-agent
gh repo create sports-predictor-agent --private --source=. --push
```

### Option B — à la main
1. Crée un dépôt vide sur https://github.com/new (privé de préférence).
2. Puis :
   ```bash
   cd sports-predictor-agent
   git remote add origin https://github.com/<ton-pseudo>/sports-predictor-agent.git
   git branch -M main
   git push -u origin main
   ```

> ✅ Vérifie sur GitHub que **`.env` n'apparaît PAS** dans les fichiers. (Il ne
> doit pas y être.)

---

## Étape 2 — Déployer sur Streamlit Community Cloud

1. Va sur **https://share.streamlit.io** et connecte-toi avec GitHub (gratuit).
2. Clique **« Create app »** → **« Deploy a public/ private app from GitHub »**.
3. Renseigne :
   - **Repository** : `<ton-pseudo>/sports-predictor-agent`
   - **Branch** : `main`
   - **Main file path** : `app.py`
4. Ouvre **« Advanced settings » → « Secrets »** et colle (en adaptant les
   valeurs) le contenu de `.streamlit/secrets.toml.example` :
   ```toml
   APP_PASSWORD = "ton-mot-de-passe"
   GROQ_API_KEY = "gsk_..."
   GROQ_MODEL = "llama-3.1-8b-instant"
   FOOTBALL_DATA_API_KEY = "..."
   FOOTBALL_DATA_COMPETITIONS = "WC,PL,PD,SA,BL1,FL1,DED,PPL,ELC"
   ```
5. Clique **« Deploy »**. Au bout de quelques minutes, l'app est en ligne sur
   une URL `https://<ton-app>.streamlit.app`.

À l'ouverture, l'app demande le **mot de passe** avant toute prédiction. 🎉

---

## Notes & limites du gratuit

- **Groq** : tier gratuit avec limites de requêtes/minute — largement suffisant
  pour une démo perso protégée par mot de passe.
- **football-data.org** : ~10 req/min, sous-ensemble de compétitions. Les
  réponses sont mises en cache (`.cache/`) pour limiter les appels. *(Sur le
  cloud, ce cache est éphémère et se reconstruit après chaque redémarrage —
  sans surcoût.)*
- **Mode démo** : si tu ne renseignes **pas** `FOOTBALL_DATA_API_KEY`, l'app
  démarre en mode **mock** (équipes fictives) — utile pour montrer l'app sans
  exposer de clé. `GROQ_API_KEY` reste nécessaire pour le raisonnement du LLM.
- **Mettre à jour l'app** : un simple `git push` sur `main` redéploie
  automatiquement.

---

## Rappel sécurité

Tes clés Groq et football-data ont transité en clair pendant le développement.
Avant une mise en ligne publique, pense à les **régénérer** :
- Groq : https://console.groq.com/keys
- football-data.org : espace client → regénérer le token

Puis mets les nouvelles valeurs **uniquement** dans les secrets Streamlit Cloud
(et ton `.env` local), jamais dans le code.
