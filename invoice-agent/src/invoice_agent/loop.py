"""La boucle : regarder, décider, agir, vérifier. C'est tout ce qu'est un agent."""

from __future__ import annotations

from dataclasses import dataclass

from .audit import AuditLog
from .config import Settings
from .guardrails import Approver, needs_approval
from .llm import Final, Message, Model, ToolCall
from .errors import ToolError
from .tools import Registry

SYSTEM_PROMPT = (
    "Tu es un agent qui trie des factures. Utilise uniquement les outils fournis. "
    "Lis chaque facture, classe-la avec sa catégorie et son montant TTC. "
    "Si un montant est introuvable, ne devine pas : signale la facture. "
    "Termine par un court résumé."
)


@dataclass(frozen=True)
class RunResult:
    status: str  # "done" | "step_limit"
    steps: int
    final: str


def run_agent(
    model: Model,
    registry: Registry,
    task: str,
    settings: Settings,
    audit: AuditLog,
    approve: Approver,
) -> RunResult:
    messages = [Message("system", SYSTEM_PROMPT), Message("user", task)]
    audit.record("start", task=task, max_steps=settings.max_steps)

    for step in range(1, settings.max_steps + 1):
        decision = model.decide(messages, registry.specs())  # décider

        if isinstance(decision, Final):
            audit.record("final", step=step, text=decision.text)
            return RunResult("done", step, decision.text)

        call: ToolCall = decision
        messages.append(Message("assistant", tool_call=call))
        audit.record("tool_call", step=step, name=call.name, arguments=call.arguments)

        observation = _act(call, registry, settings, audit, approve)  # agir
        messages.append(Message("tool", observation, tool_call_id=call.id))  # le modèle vérifie au tour suivant
        audit.record("observation", step=step, text=observation)

    audit.record("step_limit", max_steps=settings.max_steps)
    return RunResult("step_limit", settings.max_steps, "Arrêt : limite d'étapes atteinte.")


def _act(call: ToolCall, registry: Registry, settings: Settings, audit: AuditLog, approve: Approver) -> str:
    try:
        registry.validate(call.name, call.arguments)  # d'abord les arguments, avant tout humain
        if needs_approval(settings, call):
            granted = approve(call)
            audit.record("approval", name=call.name, arguments=call.arguments, granted=granted)
            if not granted:
                return "REFUSÉ par l'humain : action non exécutée."
        return registry.call(call.name, call.arguments)
    except ToolError as e:
        return f"ERREUR : {e}"
