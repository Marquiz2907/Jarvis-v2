from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

from core.paths import app_dir, prepare_runtime

ROOT = app_dir()


@dataclass
class Settings:
    wake_words: list[str]
    backend: str
    gemini_model: str
    gemini_api_key: str
    lmstudio_base_url: str
    lmstudio_model: str
    sample_rate: int
    language: str
    whisper_model: str
    tts_engine: str
    tts_voice: str
    command_timeout_sec: float
    energy_threshold: float
    input_device: str | int | None
    silence_seconds: float
    wake_poll_seconds: float
    input_gain: float
    name: str
    confirm_destructive: bool
    max_history: int
    tts_rate: int
    tts_volume: float
    extra: dict = field(default_factory=dict)
    text_only: bool = False


def _config_path() -> Path:
    return app_dir() / "config.yaml"


def load_settings() -> Settings:
    prepare_runtime()
    load_dotenv(app_dir() / ".env", override=True)
    cfg_path = _config_path()
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

    gemini = raw.get("gemini") or {}
    lm = raw.get("lmstudio") or {}
    audio = raw.get("audio") or {}
    assistant = raw.get("assistant") or {}

    backend = (os.getenv("JARVIS_BACKEND") or raw.get("backend") or "gemini").strip().lower()
    return Settings(
        wake_words=[str(w).lower() for w in (raw.get("wake_words") or ["hey jarvis", "ehi jarvis"])],
        backend=backend,
        gemini_model=os.getenv("GEMINI_MODEL") or gemini.get("model") or "gemini-2.5-flash",
        gemini_api_key=os.getenv("GEMINI_API_KEY") or "",
        lmstudio_base_url=os.getenv("LMSTUDIO_BASE_URL") or lm.get("base_url") or "http://127.0.0.1:1234/v1",
        lmstudio_model=os.getenv("LMSTUDIO_MODEL") or lm.get("model") or "",
        sample_rate=int(audio.get("sample_rate") or 16000),
        language=os.getenv("JARVIS_LANGUAGE") or audio.get("language") or "it",
        whisper_model=audio.get("whisper_model") or "base",
        tts_engine=audio.get("tts_engine") or "edge",
        tts_voice=audio.get("tts_voice") or "it-IT-DiegoNeural",
        command_timeout_sec=float(audio.get("command_timeout_sec") or 12),
        energy_threshold=float(audio.get("energy_threshold") or 0.012),
        input_device=audio.get("input_device") if audio.get("input_device") not in ("", None, "default") else None,
        silence_seconds=float(audio.get("silence_seconds") or 1.1),
        wake_poll_seconds=float(audio.get("wake_poll_seconds") or 1.6),
        input_gain=float(audio.get("input_gain") or 1.0),
        name=assistant.get("name") or "Jarvis",
        confirm_destructive=bool(assistant.get("confirm_destructive")),
        max_history=int(assistant.get("max_history") or 20),
        tts_rate=int(audio.get("tts_rate") or 175),
        tts_volume=float(audio.get("tts_volume") or 1.0),
    )


def save_runtime_settings(settings: Settings) -> None:
    env_path = app_dir() / ".env"
    lines = [
        f"GEMINI_API_KEY={settings.gemini_api_key}",
        f"GEMINI_MODEL={settings.gemini_model}",
        f"JARVIS_BACKEND={settings.backend}",
        f"LMSTUDIO_BASE_URL={settings.lmstudio_base_url}",
        f"LMSTUDIO_MODEL={settings.lmstudio_model}",
        f"JARVIS_LANGUAGE={settings.language}",
        "",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")

    cfg_path = _config_path()
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    raw = raw or {}
    raw["backend"] = settings.backend
    raw.setdefault("gemini", {})["model"] = settings.gemini_model
    raw.setdefault("lmstudio", {})["base_url"] = settings.lmstudio_base_url
    raw.setdefault("lmstudio", {})["model"] = settings.lmstudio_model
    audio = raw.setdefault("audio", {})
    audio.update({
        "sample_rate": settings.sample_rate,
        "language": settings.language,
        "whisper_model": settings.whisper_model,
        "tts_engine": settings.tts_engine,
        "tts_voice": settings.tts_voice,
        "tts_rate": settings.tts_rate,
        "tts_volume": settings.tts_volume,
        "command_timeout_sec": settings.command_timeout_sec,
        "energy_threshold": settings.energy_threshold,
        "input_device": settings.input_device if settings.input_device is not None else "default",
        "silence_seconds": settings.silence_seconds,
        "wake_poll_seconds": settings.wake_poll_seconds,
        "input_gain": settings.input_gain,
    })
    raw["wake_words"] = settings.wake_words
    assistant = raw.setdefault("assistant", {})
    assistant.update({
        "name": settings.name,
        "confirm_destructive": settings.confirm_destructive,
        "max_history": settings.max_history,
    })
    cfg_path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
