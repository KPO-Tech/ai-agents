"""Réglages de l'agent : tout ce qui borne son comportement est ici."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    inbox: Path = ROOT / "data" / "inbox"
    output: Path = ROOT / "data" / "output"
    logs: Path = ROOT / "logs"
    max_steps: int = 12  # garde-fou contre les boucles infinies
    approval_threshold: float = 500.0  # au-dessus, un humain doit valider (en euros)
    categories: tuple[str, ...] = (
        "energie",
        "fournitures",
        "prestations",
        "restauration",
        "autre",
    )
