# ⚽ Agent IA de prédiction sportive explicable

Un agent qui prédit le résultat d'un match de football **et explique son
raisonnement étape par étape** (chain-of-thought visible), en croisant
plusieurs sources de données via des *outils* — plutôt que de cracher un
résultat brut.

Construit avec **LangGraph** pour l'orchestration et l'**API Groq
(LLaMA 3.1)** comme LLM (gratuit et très rapide). Les données peuvent venir de
**données simulées** (hors-ligne) ou de l'**API réelle football-data.org**
(classement, forme, confrontations directes, calendrier).

---

## 🧠 Idée

Un parieur ou un analyste ne se contente pas d'un pronostic : il veut savoir
*pourquoi*. Cet agent imite cette démarche :

1. Il **collecte** des données via 4 outils.
2. Il **analyse chaque facteur séparément** en lui donnant un poids.
3. Il **combine** les facteurs en un raisonnement structuré.
4. Il donne une **prédiction finale + un % de confiance**.
5. Il **justifie** sa conclusion en citant les données utilisées.

---

## 🏗️ Architecture

```
                 ┌──────────────────────────────┐
   Utilisateur → │   main.py (CLI)              │
   (2 équipes)   └──────────────┬───────────────┘
                                │  build_query()
                                ▼
                 ┌──────────────────────────────┐
                 │  Agent ReAct (LangGraph)     │
                 │  agents/predictor_agent.py   │
                 │  LLM = Groq / LLaMA 3.1      │
                 └──────────────┬───────────────┘
              le LLM choisit quels outils appeler
                                ▼
   ┌───────────┬───────────┬───────────┬───────────┬───────────┬──────────┐
   │stats_tool │history    │injury     │news_search│upcoming   │probability│
   │forme,buts,│_tool      │_tool      │_tool      │_tool      │_tool      │
   │classement │H2H        │absences   │moral/news │calendrier │Poisson 1N2│
   └─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴────┬─────┘
         └───────────┴───────────┴─── tools/providers.py ──────────┘
                                ▼
              ┌─────────────────────────────────────────┐
              │  Couche provider (bascule par env)      │
              ├──────────────────┬──────────────────────┤
              │  MockProvider    │  FootballDataProvider │
              │  teams_mock.json │  API football-data.org│
              └──────────────────┴──────────────────────┘
                                ▼
            Raisonnement structuré + prédiction + confiance
                  (le % est ancré sur le modèle de Poisson)
```

La **couche provider** (`tools/providers.py`) découple les outils de la source :
les mêmes 6 outils fonctionnent à l'identique que les données soient simulées
ou réelles. La bascule se fait via la variable d'environnement `DATA_SOURCE`
(`auto` / `mock` / `football-data`).

L'agent est un **agent ReAct** (`create_react_agent` de LangGraph) : le LLM
décide lui-même quels outils appeler et dans quel ordre (boucle
*raisonnement → action → observation*), puis rédige la synthèse finale en
suivant le format imposé par le *system prompt*.

### Structure du projet

```
sports-predictor-agent/
├── app.py                        # Interface web Streamlit
├── main.py                       # Point d'entrée — CLI
├── agents/
│   └── predictor_agent.py        # Construction de l'agent + system prompt
├── tools/
│   ├── stats_tool.py             # Outil 1 — stats récentes
│   ├── history_tool.py           # Outil 2 — confrontations directes
│   ├── injury_tool.py            # Outil 3 — blessures / absences
│   ├── news_search_tool.py       # Outil 4 — actus qualitatives
│   ├── upcoming_tool.py          # Outil 5 — prochains matchs
│   ├── probability_tool.py       # Outil 6 — modèle Poisson (1/N/2)
│   ├── providers.py              # Bascule Mock / football-data.org
│   ├── football_data.py          # Client API football-data.org (+ cache)
│   └── utils.py                  # Chargement mock + résolution des noms
├── data/
│   └── teams_mock.json           # 5 équipes fictives, stats réalistes
├── tests/
│   ├── test_tools.py             # Tests des 4 outils de données
│   ├── test_upcoming.py          # Tests outil calendrier
│   └── test_probability.py       # Tests du modèle Poisson
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Installation & lancement

### 1. Prérequis
- Python 3.10+
- Une clé API **Groq** (gratuite) : https://console.groq.com/keys

### 2. Installation

```bash
cd sports-predictor-agent
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configuration des clés

```bash
cp .env.example .env        # puis éditez .env
```

- `GROQ_API_KEY` (**obligatoire**) — clé Groq pour le LLM.
- `FOOTBALL_DATA_API_KEY` (**optionnel**) — pour les données réelles.
- `DATA_SOURCE` — `auto` (défaut), `mock` ou `football-data`.

Sans clé football-data, l'agent tourne en mode `mock` (hors-ligne) : aucune
configuration supplémentaire n'est nécessaire pour tester.

### 4. Lancement

**Interface web (Streamlit)** — recommandé :

```bash
streamlit run app.py
```

- deux `selectbox` alimentées dynamiquement depuis la compétition choisie
  (Premier League, Liga, Serie A…) ;
- bouton **Prédire** ;
- raisonnement de l'agent dans des sections dépliables (`st.expander`), dont le
  détail du calcul Poisson ;
- prédiction finale + **graphique en barres** des probabilités (victoire A /
  nul / victoire B) ;
- bascule **mock / API réelle** dans la sidebar (démo possible sans clé API).

**Ligne de commande (CLI)** :

```bash
# Mode interactif (l'agent demande les deux équipes)
python main.py

# Ou directement en arguments (noms partiels acceptés en mock)
python main.py "lyon" "marseille"
python main.py "Arsenal FC" "Chelsea FC"   # mode API réelle
```

### 5. Tests

```bash
pytest -v
```

Les tests vérifient que **chaque outil renvoie bien les données attendues**
(équipe connue, nom partiel, équipe inconnue, effectif complet, etc.). Ils ne
nécessitent **pas** de clé API.

---

## 🟢 Équipes disponibles (données mockées)

| Équipe              | Classement | Forme (5 derniers) |
|---------------------|:----------:|:------------------:|
| Tigres de Marseille | 1er        | V V V N V          |
| Dragons de Lyon     | 2e         | V V N D V          |
| Loups de Bordeaux   | 3e         | V N V V N          |
| Aigles de Paris     | 4e         | D N V D N          |
| Faucons de Rennes   | 7e         | D D N V D          |

> Les données mockées sont dans `data/teams_mock.json` et servent au mode
> hors-ligne et aux tests.

---

## 🌍 Données réelles — API football-data.org

Pour utiliser de **vraies données** (vrais clubs, vrai classement) :

1. Créez un compte gratuit : https://www.football-data.org/client/register
2. Récupérez votre clé API et mettez-la dans `.env` :
   ```bash
   FOOTBALL_DATA_API_KEY=votre_cle
   DATA_SOURCE=football-data        # ou laissez "auto"
   ```
3. Lancez avec le **nom officiel** des clubs ou des sélections :
   ```bash
   python main.py "Arsenal FC" "Chelsea FC"   # clubs (Premier League)
   python main.py "France" "Spain"            # Coupe du Monde (sélections)
   ```

Ce que l'API fournit (via `tools/football_data.py`) :

| Donnée                              | Endpoint football-data.org              |
|-------------------------------------|-----------------------------------------|
| Classement + forme (5 derniers)     | `/competitions/{code}/standings`        |
| Buts marqués/concédés récents       | `/teams/{id}/matches?status=FINISHED`   |
| Confrontations directes (H2H)       | matchs terminés filtrés par adversaire  |
| Matchs à venir (calendrier)         | `/teams/{id}/matches?status=SCHEDULED`  |

> ⚠️ **Plan gratuit** : ~10 requêtes/minute et un sous-ensemble de
> compétitions — clubs (PL, Liga, Serie A, Bundesliga, Ligue 1, Eredivisie,
> Primeira Liga, Championship) **et la Coupe du Monde `WC`** (sélections
> nationales). Toutes les réponses sont **mises en cache sur disque**
> (`.cache/`) pour respecter ce quota.
>
> 🏆 **Coupe du Monde / sélections** : le classement est réparti en groupes —
> le code agrège automatiquement les 12 groupes (48 équipes). Attention, l'API
> gratuite ne couvre pas toutes les compétitions de sélections (qualifs
> CONMEBOL, etc.) : certaines équipes ont peu de matchs récents. Les outils
> **affichent alors la taille de l'échantillon et un avertissement de
> fiabilité**, que l'agent prend en compte.
>
> ℹ️ football-data.org ne fournit **ni blessures ni actualités** : ces deux
> outils restent en mode mock (le provider réel signale explicitement la donnée
> manquante à l'agent, qui la pondère en conséquence).
>
> 🗓️ **Intersaison** : les matchs terminés sont récupérés sur une fenêtre
> glissante de ~2 ans (`dateFrom`/`dateTo`), si bien que la forme, les
> confrontations directes et le modèle Poisson restent disponibles même quand
> le nouveau championnat n'a pas encore commencé (classement à 0 match joué).

L'architecture est **découplée** : pour ajouter une autre source (API-Football,
etc.), il suffit d'écrire un nouveau provider dans `tools/providers.py` — les
outils et l'agent restent inchangés.

---

## 💻 Exemple d'utilisation

Commande :

```bash
python main.py "lyon" "marseille"
```

Sortie (raisonnement de l'agent affiché en direct) :

```
⚽ Match analysé : lyon (domicile) vs marseille (extérieur)
🤖 Modèle : llama-3.1-8b-instant
────────────────────────────────────────────────────────────────
L'agent réfléchit et consulte ses outils...

🔧 Appel outil → get_team_stats(team_name='lyon')
🔧 Appel outil → get_team_stats(team_name='marseille')

📊 Données [get_team_stats] :
   Statistiques de Dragons de Lyon :
   - Position au classement : 2e
   - Forme (5 derniers...) : V V N D V (...)
   - Buts marqués (5 derniers) : 11
   - Buts concédés (5 derniers) : 5
   ...

🔧 Appel outil → get_head_to_head(team_a='lyon', team_b='marseille')
🔧 Appel outil → get_injuries(team_name='lyon')
🔧 Appel outil → get_injuries(team_name='marseille')
🔧 Appel outil → search_team_news(team_name='lyon')
🔧 Appel outil → search_team_news(team_name='marseille')
🔧 Appel outil → estimate_match_probabilities(team_a='lyon', team_b='marseille')

📊 Données [get_head_to_head] :
   Confrontations directes Dragons de Lyon vs Tigres de Marseille (4 matchs) :
   - 2025-02-14 : Dragons de Lyon 1-2 Tigres de Marseille (→ Tigres de Marseille)
   ...
   Bilan : Dragons de Lyon 0 victoire(s), Tigres de Marseille 3 victoire(s), 1 nul(s).

────────────────────────────────────────────────────────────────
### 🧠 Raisonnement étape par étape

**1. Forme récente** (poids : 30%)
Marseille est en tête (1er), invaincu, avec 14 buts marqués pour seulement 3
concédés sur les 5 derniers matchs. Lyon est solide (11 buts, 5 encaissés)
mais a connu une défaite récente. Avantage net Marseille.

**2. Confrontations directes** (poids : 15%)
Bilan favorable à Marseille : 3 victoires, 1 nul, 0 défaite sur les 4 derniers
duels. Avantage psychologique Marseille.

**3. Blessures / absences** (poids : 25%)
Lyon perd son attaquant clé K. Diallo (forfait). Marseille n'a qu'un doute
mineur (A. Santos, rotation). Facteur défavorable à Lyon.

**4. Avantage du terrain** (poids : 15%)
Lyon joue à domicile (force 82%), ce qui réduit l'écart. Mais Marseille reste
très fort à l'extérieur (71%).

**5. Contexte qualitatif** (poids : 15%)
Lyon affiche une bonne confiance à domicile, mais l'absence de Diallo inquiète.
Marseille est serein sur une série de 8 matchs sans défaite.

### 📊 Synthèse
Quatre facteurs sur cinq penchent pour Marseille ; seul l'avantage du terrain
aide Lyon à resserrer l'écart.

### 🎲 Modèle de probabilité (Poisson)
Buts attendus : Lyon 1.61 — Marseille 1.80.
P(victoire Lyon) = 35 % · P(nul) = 22 % · P(victoire Marseille) = 43 %.
Score le plus probable : 1-1. *(Le modèle, purement statistique, ignore
l'absence de l'attaquant clé de Lyon — d'où une confiance finale rehaussée
côté Marseille par l'agent.)*

### 🏆 Prédiction finale
- **Résultat probable :** Victoire de Tigres de Marseille
- **Score estimé :** 1-2
- **Confiance :** 68 %

### ✅ Pourquoi cette conclusion
Marseille domine sur la forme (14 buts marqués / 3 encaissés contre 11/5),
sur l'historique (3-0-1) et bénéficie de l'absence de l'attaquant clé de Lyon.
L'avantage du terrain de Lyon et sa solidité défensive empêchent toutefois une
confiance plus élevée, d'où les 68 %.
────────────────────────────────────────────────────────────────
```

> 📸 **Screenshot :** lancez la commande ci-dessus dans votre terminal et
> faites une capture d'écran pour l'ajouter ici, par exemple :
> `![Raisonnement de l'agent](docs/screenshot.png)`.
> *(La sortie exacte varie d'une exécution à l'autre puisqu'elle est générée
> par le LLM.)*

---

## 🔌 Évolutions possibles
- ✅ ~~Brancher une vraie API de données sportives~~ → football-data.org intégré.
- ✅ ~~Modèle de probabilité (Poisson) pour fiabiliser le `%`~~ → `probability_tool`.
- Remplacer le mock de `news_search_tool` par une vraie recherche web
  (Tavily, DuckDuckGo, SerpAPI).
- Récupérer les blessures via une source dédiée (l'API gratuite ne les fournit pas).
- Exposer l'agent via une interface **Streamlit** ou une petite API web.
