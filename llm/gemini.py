from __future__ import annotations

import json

from google import genai
from google.genai import types

from llm.prompt import SYSTEM_PROMPT
from tools.pc import TOOL_DEFINITIONS, execute_tool


def _gemini_tools() -> list[types.Tool]:
    decls = []
    for tool in TOOL_DEFINITIONS:
        decls.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool.get("parameters") or {"type": "object", "properties": {}},
            )
        )
    return [types.Tool(function_declarations=decls)]


class GeminiBrain:
    def __init__(self, api_key: str, model: str, max_history: int = 20):
        if not api_key:
            raise RuntimeError("Manca GEMINI_API_KEY. Mettila nel file .env")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.max_history = max_history
        self.history: list[types.Content] = []

    def think(self, user_text: str) -> str:
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
        self._trim()
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=_gemini_tools(),
            temperature=0.4,
        )
        for _ in range(8):
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.history,
                config=config,
            )
            candidate = response.candidates[0]
            parts = candidate.content.parts or []
            function_calls = [p.function_call for p in parts if getattr(p, "function_call", None) and p.function_call.name]
            if not function_calls:
                text = (response.text or "").strip()
                self.history.append(candidate.content)
                self._trim()
                return text or "Fatto."

            self.history.append(candidate.content)
            result_parts = []
            for call in function_calls:
                args = dict(call.args or {})
                result = execute_tool(call.name, args)
                try:
                    payload = json.loads(result)
                    if not isinstance(payload, dict):
                        payload = {"result": payload}
                except json.JSONDecodeError:
                    payload = {"result": result}
                result_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response=payload,
                    )
                )
            self.history.append(types.Content(role="user", parts=result_parts))
        return "Ho eseguito i comandi ma non sono riuscito a formulare una risposta finale."

    def _trim(self) -> None:
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2 :]
