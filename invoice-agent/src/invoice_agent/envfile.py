"""Charge un fichier .env dans os.environ, sans jamais écraser ni afficher les valeurs."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path) -> list[str]:
    """Ajoute les variables absentes de l'environnement. Renvoie leurs NOMS (jamais les valeurs)."""
    added: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            added.append(key)
    return added
