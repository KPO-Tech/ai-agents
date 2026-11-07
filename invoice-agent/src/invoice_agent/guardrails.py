"""Les règles. Elles vivent dans le code, pas dans le prompt : le modèle ne peut pas les contourner."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .config import Settings
from .llm import ToolCall
from .errors import ToolError

# Une fonction qui montre l'action à un humain et renvoie sa décision.
Approver = Callable[[ToolCall], bool]


def safe_inbox_path(settings: Settings, name: str) -> Path:
    """Résout `name` dans la boîte de réception, jamais en dehors (pas de `../`)."""
    inbox = settings.inbox.resolve()
    path = (inbox / name).resolve()
    if path.parent != inbox:
        raise ToolError(f"accès refusé hors de la boîte de réception : {name}")
    if not path.is_file():
        raise ToolError(f"facture introuvable : {name}")
    return path


def needs_approval(settings: Settings, call: ToolCall) -> bool:
    """Classer une facture au-dessus du seuil exige la validation d'un humain."""
    if call.name != "classify_invoice":
        return False
    amount = call.arguments.get("amount")
    return isinstance(amount, (int, float)) and amount > settings.approval_threshold


def deny_all(call: ToolCall) -> bool:
    return False


def approve_all(call: ToolCall) -> bool:
    return True


def ask_in_terminal(call: ToolCall) -> bool:
    print(f"\n[validation requise] {call.name} {call.arguments}")
    return input("Autoriser ? [o/N] ").strip().lower() in {"o", "oui", "y", "yes"}
