"""Lecture déterministe d'une facture : la source de vérité, indépendante du modèle."""

from __future__ import annotations

import re

_AMOUNT = re.compile(r"Total TTC\s*:\s*([\d\s  ]+(?:,\d{1,2})?)\s*EUR")


def parse_amount(text: str) -> float | None:
    """Extrait « Total TTC : 1 850,00 EUR » -> 1850.0, ou None si introuvable."""
    m = _AMOUNT.search(text)
    if not m:
        return None
    raw = re.sub(r"[\s  ]", "", m.group(1)).replace(",", ".")
    return float(raw)
