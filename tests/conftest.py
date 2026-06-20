"""Force la source de données "mock" pendant les tests.

Ainsi la suite reste hors-ligne et déterministe même si une clé
FOOTBALL_DATA_API_KEY est présente dans l'environnement du développeur.
"""

import os

os.environ["DATA_SOURCE"] = "mock"
