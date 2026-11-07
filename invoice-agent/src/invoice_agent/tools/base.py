"""Un outil = une fonction Python + sa description pour le modèle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..errors import ToolError
from ..llm import ToolSpec


@dataclass(frozen=True)
class Tool:
    spec: ToolSpec
    run: Callable[..., str]
    # Vérifie les arguments SANS rien exécuter ; lève ToolError s'ils sont invalides.
    check: Callable[..., None] | None = None


class Registry:
    """Seuls les outils enregistrés ici existent pour l'agent."""

    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {t.spec.name: t for t in tools}

    def specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def validate(self, name: str, arguments: dict[str, Any]) -> None:
        """Contrôle préalable : à faire avant de déranger un humain."""
        tool = self.get(name)
        if tool is None:
            raise ToolError(f"outil inconnu : {name}")
        if tool.check is not None:
            try:
                tool.check(**arguments)
            except TypeError as e:
                raise ToolError(f"arguments invalides pour {name} : {e}") from e

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self.get(name)
        if tool is None:
            raise ToolError(f"outil inconnu : {name}")
        try:
            return tool.run(**arguments)
        except TypeError as e:
            raise ToolError(f"arguments invalides pour {name} : {e}") from e
