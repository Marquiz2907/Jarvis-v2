from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import pyperclip
from PIL import ImageGrab

from core.paths import user_data_dir

SCREENSHOT_DIR = user_data_dir() / "screenshots"


def _run(command: str, cwd: str | None = None, timeout: int = 120) -> dict:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        stdout = (completed.stdout or "")[-12000:]
        stderr = (completed.stderr or "")[-8000:]
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "elapsed_sec": round(time.time() - started, 2),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout dopo {timeout}s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_command(command: str, cwd: str | None = None, timeout: int = 120) -> str:
    return json.dumps(_run(command, cwd=cwd, timeout=timeout), ensure_ascii=False)


def powershell(script: str, timeout: int = 120) -> str:
    encoded = script.replace('"', '`"')
    return run_command(f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{encoded}"', timeout=timeout)


def open_path(path: str) -> str:
    target = Path(os.path.expandvars(os.path.expanduser(path))).resolve()
    if not target.exists():
        return json.dumps({"ok": False, "error": f"Percorso inesistente: {target}"}, ensure_ascii=False)
    os.startfile(str(target))  # type: ignore[attr-defined]
    return json.dumps({"ok": True, "opened": str(target)}, ensure_ascii=False)


def open_url(url: str) -> str:
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    os.startfile(url)  # type: ignore[attr-defined]
    return json.dumps({"ok": True, "opened": url}, ensure_ascii=False)


def launch_app(name: str) -> str:
    candidates = [name]
    if not name.lower().endswith(".exe"):
        candidates.append(name + ".exe")
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            subprocess.Popen([found], shell=False)
            return json.dumps({"ok": True, "launched": found}, ensure_ascii=False)
    os.startfile(name)  # type: ignore[attr-defined]
    return json.dumps({"ok": True, "started": name}, ensure_ascii=False)


def list_directory(path: str, limit: int = 80) -> str:
    target = Path(os.path.expandvars(os.path.expanduser(path))).resolve()
    if not target.exists():
        return json.dumps({"ok": False, "error": f"Percorso inesistente: {target}"}, ensure_ascii=False)
    items = []
    for child in list(target.iterdir())[:limit]:
        items.append(
            {
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            }
        )
    return json.dumps({"ok": True, "path": str(target), "items": items}, ensure_ascii=False)


def read_file(path: str, max_chars: int = 20000) -> str:
    target = Path(os.path.expandvars(os.path.expanduser(path))).resolve()
    if not target.is_file():
        return json.dumps({"ok": False, "error": f"File inesistente: {target}"}, ensure_ascii=False)
    text = target.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > max_chars
    return json.dumps(
        {"ok": True, "path": str(target), "truncated": truncated, "content": text[:max_chars]},
        ensure_ascii=False,
    )


def write_file(path: str, content: str, append: bool = False) -> str:
    target = Path(os.path.expandvars(os.path.expanduser(path))).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with target.open(mode, encoding="utf-8") as handle:
        handle.write(content)
    return json.dumps({"ok": True, "path": str(target), "bytes": target.stat().st_size}, ensure_ascii=False)


def search_files(root: str, pattern: str, limit: int = 40) -> str:
    target = Path(os.path.expandvars(os.path.expanduser(root))).resolve()
    if not target.exists():
        return json.dumps({"ok": False, "error": f"Percorso inesistente: {target}"}, ensure_ascii=False)
    matches = [str(p) for p in target.rglob(pattern)][:limit]
    return json.dumps({"ok": True, "matches": matches}, ensure_ascii=False)


def get_clipboard() -> str:
    try:
        return json.dumps({"ok": True, "text": pyperclip.paste()}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


def set_clipboard(text: str) -> str:
    pyperclip.copy(text)
    return json.dumps({"ok": True}, ensure_ascii=False)


def screenshot() -> str:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    image = ImageGrab.grab()
    path = SCREENSHOT_DIR / f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    image.save(path)
    return json.dumps({"ok": True, "path": str(path), "size": image.size}, ensure_ascii=False)


def type_text(text: str, interval: float = 0.02) -> str:
    from pynput.keyboard import Controller

    keyboard = Controller()
    keyboard.type(text)
    return json.dumps({"ok": True, "typed_chars": len(text)}, ensure_ascii=False)


def press_hotkey(*keys: str) -> str:
    from pynput.keyboard import Controller, Key

    keyboard = Controller()
    mapped = []
    for key in keys:
        name = key.lower().strip()
        mapped.append(getattr(Key, name, name))
    for key in mapped:
        keyboard.press(key)
    for key in reversed(mapped):
        keyboard.release(key)
    return json.dumps({"ok": True, "keys": list(keys)}, ensure_ascii=False)


def system_info() -> str:
    info = {
        "ok": True,
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "user": os.getenv("USERNAME") or os.getenv("USER"),
        "cwd": os.getcwd(),
        "home": str(Path.home()),
        "time": datetime.now().isoformat(timespec="seconds"),
    }
    return json.dumps(info, ensure_ascii=False)


TOOL_DEFINITIONS = [
    {
        "name": "run_command",
        "description": "Esegue un comando shell/PowerShell sul PC dell'utente e restituisce stdout/stderr.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Comando da eseguire"},
                "cwd": {"type": "string", "description": "Directory di lavoro opzionale"},
                "timeout": {"type": "integer", "description": "Timeout in secondi", "default": 120},
            },
            "required": ["command"],
        },
    },
    {
        "name": "powershell",
        "description": "Esegue uno script PowerShell sul PC.",
        "parameters": {
            "type": "object",
            "properties": {"script": {"type": "string"}, "timeout": {"type": "integer", "default": 120}},
            "required": ["script"],
        },
    },
    {
        "name": "open_path",
        "description": "Apre un file o una cartella con l'app predefinita di Windows.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "open_url",
        "description": "Apre un URL nel browser predefinito.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "launch_app",
        "description": "Avvia un'applicazione (es. notepad, chrome, spotify, explorer).",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "list_directory",
        "description": "Elenca file e cartelle in un percorso.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "limit": {"type": "integer", "default": 80}},
            "required": ["path"],
        },
    },
    {
        "name": "read_file",
        "description": "Legge il contenuto di un file di testo.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer", "default": 20000}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Scrive o crea un file di testo.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "append": {"type": "boolean", "default": False},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "search_files",
        "description": "Cerca file per glob (es. *.pdf) a partire da una cartella.",
        "parameters": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "pattern": {"type": "string"},
                "limit": {"type": "integer", "default": 40},
            },
            "required": ["root", "pattern"],
        },
    },
    {
        "name": "get_clipboard",
        "description": "Legge il testo dagli appunti.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "set_clipboard",
        "description": "Copia testo negli appunti.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "screenshot",
        "description": "Cattura uno screenshot dello schermo principale.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "type_text",
        "description": "Digita testo nella finestra attualmente in primo piano.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "press_hotkey",
        "description": "Preme una combinazione di tasti (es. ctrl, c). Nomi: ctrl, alt, shift, enter, tab, win, delete, space.",
        "parameters": {
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}, "description": "Lista tasti in ordine"}
            },
            "required": ["keys"],
        },
    },
    {
        "name": "system_info",
        "description": "Restituisce informazioni sul sistema, utente, ora e cartella corrente.",
        "parameters": {"type": "object", "properties": {}},
    },
]


DISPATCH = {
    "run_command": lambda **kw: run_command(kw["command"], kw.get("cwd"), int(kw.get("timeout") or 120)),
    "powershell": lambda **kw: powershell(kw["script"], int(kw.get("timeout") or 120)),
    "open_path": lambda **kw: open_path(kw["path"]),
    "open_url": lambda **kw: open_url(kw["url"]),
    "launch_app": lambda **kw: launch_app(kw["name"]),
    "list_directory": lambda **kw: list_directory(kw["path"], int(kw.get("limit") or 80)),
    "read_file": lambda **kw: read_file(kw["path"], int(kw.get("max_chars") or 20000)),
    "write_file": lambda **kw: write_file(kw["path"], kw["content"], bool(kw.get("append"))),
    "search_files": lambda **kw: search_files(kw["root"], kw["pattern"], int(kw.get("limit") or 40)),
    "get_clipboard": lambda **kw: get_clipboard(),
    "set_clipboard": lambda **kw: set_clipboard(kw["text"]),
    "screenshot": lambda **kw: screenshot(),
    "type_text": lambda **kw: type_text(kw["text"]),
    "press_hotkey": lambda **kw: press_hotkey(*list(kw.get("keys") or [])),
    "system_info": lambda **kw: system_info(),
}


def execute_tool(name: str, arguments: dict) -> str:
    fn = DISPATCH.get(name)
    if not fn:
        return json.dumps({"ok": False, "error": f"Tool sconosciuto: {name}"}, ensure_ascii=False)
    try:
        return fn(**(arguments or {}))
    except TypeError as exc:
        return json.dumps({"ok": False, "error": f"Argomenti non validi: {exc}"}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
