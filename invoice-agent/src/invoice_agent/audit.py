"""Le journal : une ligne JSON par événement, pour savoir ce que l'agent a fait."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, directory: Path, run_id: str | None = None, echo: bool = False) -> None:
        self.echo = echo  # afficher aussi les étapes dans le terminal
        directory.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or datetime.now().strftime("run-%Y%m%d-%H%M%S")
        self.path = directory / f"{self.run_id}.jsonl"

    def record(self, event: str, **data: Any) -> None:
        row = {"t": datetime.now().isoformat(timespec="seconds"), "event": event, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if self.echo:
            line = _format(event, data)
            if line:
                print(line, flush=True)


def _format(event: str, data: dict[str, Any]) -> str:
    if event == "tool_call":
        args = ", ".join(f"{k}={v!r}" for k, v in data["arguments"].items())
        return f"[{data['step']:>2}] {data['name']}({args})"
    if event == "observation":
        text = " ".join(str(data["text"]).split())
        return f"     -> {text[:90]}{'...' if len(text) > 90 else ''}"
    if event == "approval":
        return f"     ?? validation humaine : {'accordée' if data['granted'] else 'refusée'}"
    return ""
