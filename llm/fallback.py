from __future__ import annotations

import json
import re

from openai import OpenAI

from llm.prompt import SYSTEM_PROMPT
from tools.pc import TOOL_DEFINITIONS, execute_tool

TOOL_CATALOG = json.dumps(TOOL_DEFINITIONS, ensure_ascii=False, indent=2)

FALLBACK_INSTRUCTIONS = """
Quando ti serve agire sul PC, rispondi SOLO con JSON valido in questo formato:
{"tool":"nome_tool","arguments":{...}}
Dopo aver ricevuto il risultato di un tool, se hai finito rispondi con:
{"final":"testo da dire ad alta voce"}
Non aggiungere markdown.
Catalogo tool:
"""


class PromptToolBrain:
    """Per modelli LM Studio senza native function calling."""

    def __init__(self, base_url: str, model: str = "", max_history: int = 20):
        self.client = OpenAI(base_url=base_url.rstrip("/"), api_key="lm-studio")
        self.model = model or self.client.models.list().data[0].id
        self.max_history = max_history
        self.history: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT + FALLBACK_INSTRUCTIONS + TOOL_CATALOG}
        ]

    def think(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        for _ in range(8):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                temperature=0.2,
            )
            raw = (response.choices[0].message.content or "").strip()
            self.history.append({"role": "assistant", "content": raw})
            parsed = _extract_json(raw)
            if not parsed:
                return raw or "Fatto."
            if "final" in parsed:
                return str(parsed["final"])
            tool = parsed.get("tool")
            if not tool:
                return raw
            result = execute_tool(tool, parsed.get("arguments") or {})
            self.history.append({"role": "user", "content": f"Risultato tool {tool}: {result}"})
        return "Ho eseguito i comandi ma non sono riuscito a formulare una risposta finale."


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
