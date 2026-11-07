"""Un faux modèle déterministe, à base de règles, pour développer sans quota.

Il imite la manière de décider d'un vrai modèle (lister, lire, classer, conclure)
en lisant la conversation. Ce N'EST PAS de l'IA : les vraies sorties de la vidéo
viendront d'un vrai modèle branché sur la même interface `Model`.
"""

from __future__ import annotations

import json

from .llm import Decision, Final, Message, ToolCall, ToolSpec
from .parsing import parse_amount

_KEYWORDS = {
    "energie": ("électricité", "electricite", "énergie", "gaz"),
    "fournitures": ("papeterie", "fournitures", "cartouche"),
    "prestations": ("conseil", "prestation", "mission"),
    "restauration": ("café", "restaurant", "traiteur"),
}


def guess_category(text: str) -> str:
    low = text.lower()
    for category, words in _KEYWORDS.items():
        if any(w in low for w in words):
            return category
    return "autre"


class FakeModel:
    def decide(self, messages: list[Message], tools: list[ToolSpec]) -> Decision:
        calls = [m.tool_call for m in messages if m.tool_call]
        results = {m.tool_call_id: m.content for m in messages if m.role == "tool"}
        n = len(calls) + 1

        listed = next((c for c in calls if c.name == "list_invoices"), None)
        if listed is None:
            return ToolCall(f"c{n}", "list_invoices", {})
        names: list[str] = json.loads(results[listed.id])

        read = {c.arguments["name"]: results[c.id] for c in calls if c.name == "read_invoice"}
        for name in names:
            if name not in read:
                return ToolCall(f"c{n}", "read_invoice", {"name": name})

        done = {c.arguments["name"] for c in calls if c.name == "classify_invoice"}
        for name in names:
            if name in done:
                continue
            amount = parse_amount(read[name])
            if amount is None:
                done.add(name)  # illisible : on ne devine pas, on le signalera
                continue
            return ToolCall(
                f"c{n}",
                "classify_invoice",
                {"name": name, "category": guess_category(read[name]), "amount": amount},
            )

        unreadable = [nm for nm in names if parse_amount(read[nm]) is None]
        refused = [
            c.arguments["name"]
            for c in calls
            if c.name == "classify_invoice" and results[c.id].startswith("REFUSÉ")
        ]
        lines = [f"{len(names)} factures examinées."]
        if refused:
            lines.append("Non classées (validation humaine refusée) : " + ", ".join(refused) + ".")
        if unreadable:
            lines.append("À vérifier à la main (montant introuvable) : " + ", ".join(unreadable) + ".")
        return Final(" ".join(lines))
