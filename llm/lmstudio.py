from __future__ import annotations

import json

from openai import OpenAI

from llm.fallback import PromptToolBrain
from llm.prompt import SYSTEM_PROMPT
from tools.pc import TOOL_DEFINITIONS, execute_tool


def _openai_tools() -> list[dict]:
    tools = []
    for tool in TOOL_DEFINITIONS:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
                },
            }
        )
    return tools


class LMStudioBrain:
    def __init__(self, base_url: str, model: str = "", max_history: int = 20):
        self.client = OpenAI(base_url=base_url.rstrip("/"), api_key="lm-studio")
        self.model = model or self._discover_model()
        self.max_history = max_history
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._native_tools = True
        self._fallback: PromptToolBrain | None = None

    def _discover_model(self) -> str:
        models = self.client.models.list()
        ids = [m.id for m in models.data]
        if not ids:
            raise RuntimeError(
                "LM Studio non espone nessun modello. Avvia il server locale e carica un modello."
            )
        return ids[0]

    def think(self, user_text: str) -> str:
        if not self._native_tools:
            return self._fallback_think(user_text)
        self.history.append({"role": "user", "content": user_text})
        self._trim()
        try:
            return self._tool_loop()
        except Exception:
            self._native_tools = False
            last_user = user_text
            if self.history and self.history[-1].get("role") == "user":
                self.history.pop()
            return self._fallback_think(last_user)

    def _tool_loop(self) -> str:
        for _ in range(8):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                tools=_openai_tools(),
                tool_choice="auto",
                temperature=0.4,
            )
            message = response.choices[0].message
            tool_calls = message.tool_calls or []
            if not tool_calls:
                text = (message.content or "").strip()
                self.history.append({"role": "assistant", "content": text})
                self._trim()
                return text or "Fatto."

            self.history.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )
            for call in tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(call.function.name, args)
                self.history.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )
        return "Ho eseguito i comandi ma non sono riuscito a formulare una risposta finale."

    def _fallback_think(self, user_text: str) -> str:
        if self._fallback is None:
            self._fallback = PromptToolBrain(str(self.client.base_url), self.model, self.max_history)
        return self._fallback.think(user_text)

    def _trim(self) -> None:
        system = self.history[:1]
        rest = self.history[1:]
        if len(rest) > self.max_history * 2:
            rest = rest[-self.max_history * 2 :]
        self.history = system + rest
