"""Utilitaires partagés par tous les outils : chargement des données et
résolution "souple" du nom d'équipe (insensible à la casse, partielle)."""

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "teams_mock.json"


@lru_cache(maxsize=1)
def load_data() -> dict:
    """Charge le JSON de données mockées (mis en cache après le 1er appel)."""
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def find_team(name: str, teams: dict) -> str | None:
    """Retourne la clé exacte d'une équipe à partir d'un nom approximatif.

    Stratégie : correspondance exacte (insensible à la casse) d'abord,
    puis correspondance partielle (sous-chaîne). Pratique car l'utilisateur
    peut taper "lyon" au lieu de "Dragons de Lyon".
    """
    name_l = name.strip().lower()
    if not name_l:
        return None
    for key in teams:
        if key.lower() == name_l:
            return key
    for key in teams:
        if name_l in key.lower() or key.lower() in name_l:
            return key
    return None


def known_teams() -> list[str]:
    """Liste des équipes disponibles dans les données mockées."""
    return list(load_data()["teams"].keys())
