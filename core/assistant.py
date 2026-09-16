from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol

from rich.console import Console

from audio.listener import Listener
from audio.tts import Speaker
from core.config import Settings
from llm.gemini import GeminiBrain
from llm.lmstudio import LMStudioBrain

console = Console()
LogFn = Callable[[str, str], None]


class Brain(Protocol):
    def think(self, user_text: str) -> str: ...


def build_brain(settings: Settings) -> Brain:
    if settings.backend in {"lmstudio", "local", "lm-studio"}:
        console.print(f"[cyan]Backend:[/cyan] LM Studio  {settings.lmstudio_base_url}")
        return LMStudioBrain(settings.lmstudio_base_url, settings.lmstudio_model, settings.max_history)
    console.print(f"[cyan]Backend:[/cyan] Gemini  {settings.gemini_model}")
    return GeminiBrain(settings.gemini_api_key, settings.gemini_model, settings.max_history)


class Jarvis:
    def __init__(self, settings: Settings, on_log: LogFn | None = None):
        self.settings = settings
        self.on_log = on_log
        self.speaker = Speaker(engine=settings.tts_engine, voice=settings.tts_voice, rate=settings.tts_rate, volume=settings.tts_volume)
        self._log("system", "Avvio cervello e microfono...")
        self.brain = build_brain(settings)
        self._busy = threading.Lock()
        self._stop = threading.Event()
        self.listener = None
        if not getattr(settings, "text_only", False):
            self.listener = Listener(
                sample_rate=settings.sample_rate,
                language=settings.language,
                whisper_model=settings.whisper_model,
                energy_threshold=settings.energy_threshold,
                wake_words=settings.wake_words,
                input_device=settings.input_device,
                input_gain=settings.input_gain,
            )
        self._log("system", "Pronto. Dì «ehy Jarvis» oppure usa Ctrl+Alt+J.")

    def _log(self, kind: str, message: str) -> None:
        if self.on_log:
            self.on_log(kind, message)
            return
        colors = {"user": "green", "assistant": "cyan", "system": "magenta", "error": "red"}
        color = colors.get(kind, "white")
        console.print(f"[{color}]{message}[/{color}]")

    def stop(self) -> None:
        self._stop.set()

    def handle_command(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            if not self.listener:
                self.speaker.say("Nessun comando.")
                return
            self.speaker.beep(660, 0.08)
            self._log("system", "Ti ascolto...")
            text = self.listener.listen_utterance(max_seconds=self.settings.command_timeout_sec, silence_seconds=self.settings.silence_seconds)
        if not text:
            self.speaker.say("Non ho sentito il comando.")
            self._log("error", "Comando vuoto")
            return
        self._log("user", text)
        try:
            reply = self.brain.think(text)
        except Exception as exc:
            reply = f"Errore nel cervello: {exc}"
            self._log("error", reply)
        self._log("assistant", reply)
        self.speaker.say(reply)

    def run(self) -> None:
        self._stop.clear()
        self._log("system", "Ascolto continuo attivo")
        self._install_hotkey()
        if not self.listener:
            return
        while not self._stop.is_set():
            leftover = self.listener.wait_for_wake(poll_seconds=self.settings.wake_poll_seconds, stop_event=self._stop)
            if leftover is None:
                break
            with self._busy:
                if self._stop.is_set():
                    break
                self.speaker.beep()
                self._log("system", "Wake word rilevata")
                self.handle_command(leftover)
        self._log("system", "Ascolto fermato")

    def _install_hotkey(self) -> None:
        try:
            import keyboard

            def trigger() -> None:
                if self._busy.locked() or self._stop.is_set():
                    return
                threading.Thread(target=self._hotkey_listen, daemon=True).start()

            keyboard.add_hotkey("ctrl+alt+j", trigger)
        except Exception:
            self._log("system", "Hotkey non disponibile")

    def _hotkey_listen(self) -> None:
        with self._busy:
            self.speaker.beep(990, 0.1)
            self.handle_command("")
