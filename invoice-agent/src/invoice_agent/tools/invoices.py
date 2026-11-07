"""Les trois outils de l'agent : lister, lire, classer. Rien d'autre."""

from __future__ import annotations

import json

from ..config import Settings
from ..guardrails import safe_inbox_path
from ..llm import ToolSpec
from ..parsing import parse_amount
from ..errors import ToolError
from .base import Registry, Tool


def build_registry(settings: Settings) -> Registry:
    def list_invoices() -> str:
        names = sorted(p.name for p in settings.inbox.glob("*.txt"))
        return json.dumps(names)

    def read_invoice(name: str) -> str:
        return safe_inbox_path(settings, name).read_text(encoding="utf-8")

    def check_classify(name: str, category: str, amount: float) -> None:
        if category not in settings.categories:
            raise ToolError(f"catégorie inconnue : {category} (valides : {list(settings.categories)})")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ToolError("le montant doit être un nombre positif")
        path = safe_inbox_path(settings, name)  # la facture doit exister
        # Le montant annoncé par le modèle n'est pas une preuve : on le compare au document.
        real = parse_amount(path.read_text(encoding="utf-8"))
        if real is None:
            raise ToolError(f"montant introuvable dans {name} : à faire vérifier par un humain")
        if abs(real - amount) > 0.005:
            raise ToolError(f"montant incohérent : {name} indique {real:.2f} EUR, pas {amount:.2f} EUR")

    def classify_invoice(name: str, category: str, amount: float) -> str:
        check_classify(name, category, amount)
        settings.output.mkdir(parents=True, exist_ok=True)
        ledger = settings.output / "ledger.json"
        rows = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
        rows = [r for r in rows if r["name"] != name]
        rows.append({"name": name, "category": category, "amount": amount})
        ledger.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"OK : {name} classée en {category} ({amount:.2f} EUR)"

    return Registry(
        [
            Tool(
                ToolSpec(
                    "list_invoices",
                    "Liste les fichiers de factures de la boîte de réception.",
                    {"type": "object", "properties": {}},
                ),
                list_invoices,
            ),
            Tool(
                ToolSpec(
                    "read_invoice",
                    "Lit le texte d'une facture à partir de son nom de fichier.",
                    {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
                ),
                read_invoice,
            ),
            Tool(
                ToolSpec(
                    "classify_invoice",
                    "Enregistre la catégorie et le montant TTC d'une facture. Au-delà d'un seuil, un humain valide.",
                    {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string", "enum": list(settings.categories)},
                            "amount": {"type": "number"},
                        },
                        "required": ["name", "category", "amount"],
                    },
                ),
                classify_invoice,
                check=check_classify,
            ),
        ]
    )
