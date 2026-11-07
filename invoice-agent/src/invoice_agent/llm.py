"""Le modèle, vu de la boucle : il reçoit la conversation et renvoie UNE décision.

Une décision est soit un appel d'outil, soit une réponse finale. Tout modèle
(vrai ou simulé) qui respecte l'interface `Model` peut piloter l'agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Final:
    text: str


Decision = ToolCall | Final


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_call: ToolCall | None = None  # pour role == "assistant"
    tool_call_id: str | None = None  # pour role == "tool"


@dataclass(frozen=True)
class ToolSpec:
    """Ce que le modèle voit d'un outil : un nom, un rôle, des paramètres."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


class Model(Protocol):
    def decide(self, messages: list[Message], tools: list[ToolSpec]) -> Decision: ...


class ScriptedModel:
    """Rejoue une liste de décisions écrites à l'avance (pour les tests)."""

    def __init__(self, decisions: list[Decision]) -> None:
        self._decisions = list(decisions)
        self._i = 0

    def decide(self, messages: list[Message], tools: list[ToolSpec]) -> Decision:
        if self._i >= len(self._decisions):
            raise RuntimeError("ScriptedModel : plus de décisions prévues")
        decision = self._decisions[self._i]
        self._i += 1
        return decision
