"""Un vrai modèle : l'API Z.ai (GLM), compatible avec le format « chat completions » d'OpenAI.

Aucune dépendance : seulement la bibliothèque standard. La clé vient de la variable
d'environnement ZHIPUAI_API_KEY et n'est jamais écrite ni journalisée.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from .llm import Decision, Final, Message, ToolCall, ToolSpec

BASE_URL = "https://api.z.ai/api/paas/v4"
DEFAULT_MODEL = "glm-5.3-flash"


class ModelError(Exception):
    pass


class ZaiModel:
    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = BASE_URL, timeout: float = 90.0) -> None:
        key = os.environ.get("ZHIPUAI_API_KEY")
        if not key:
            raise ModelError("ZHIPUAI_API_KEY absente (voir --env-file)")
        self._key = key
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._timeout = timeout
        self.calls = 0

    def decide(self, messages: list[Message], tools: list[ToolSpec]) -> Decision:
        body = {
            "model": self.model,
            "temperature": 0,
            "messages": [_to_wire(m) for m in messages],
            "tools": [
                {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                for t in tools
            ],
        }
        reply = self._post(body)
        self.calls += 1
        try:
            message = reply["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            raise ModelError(f"réponse inattendue : {str(reply)[:300]}") from e

        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            first = tool_calls[0]
            fn = first["function"]
            raw = fn.get("arguments") or "{}"
            try:
                arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
            except json.JSONDecodeError:
                arguments = {"_invalid_json": raw}  # l'outil renverra une erreur au modèle
            return ToolCall(first.get("id") or f"call_{self.calls}", fn["name"], arguments)
        return Final((message.get("content") or "").strip())

    def _post(self, body: dict) -> dict:
        data = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            req = urllib.request.Request(
                self._url,
                data=data,
                headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:300]
                if e.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise ModelError(f"HTTP {e.code} : {detail}") from e
            except urllib.error.URLError as e:
                raise ModelError(f"réseau : {e.reason}") from e
        raise ModelError("trop d'échecs")


def _to_wire(m: Message) -> dict:
    if m.role == "assistant" and m.tool_call:
        c = m.tool_call
        return {
            "role": "assistant",
            "content": m.content or "",
            "tool_calls": [
                {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)}}
            ],
        }
    if m.role == "tool":
        return {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
    return {"role": m.role, "content": m.content}
