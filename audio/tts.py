from __future__ import annotations

import asyncio
import io
import threading

import edge_tts
import numpy as np
import sounddevice as sd

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None


class Speaker:
    def __init__(self, engine: str = "edge", voice: str = "it-IT-DiegoNeural", rate: int = 175, volume: float = 1.0):
        self.engine = engine
        self.voice = voice
        self.rate = max(80, min(int(rate), 300))
        self.volume = max(0.0, min(float(volume), 1.0))
        self._lock = threading.Lock()
        self._offline = None
        if engine != "edge" and pyttsx3:
            self._offline = pyttsx3.init()
            self._offline.setProperty("rate", self.rate)
            self._offline.setProperty("volume", self.volume)

    def say(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        with self._lock:
            if self.engine == "edge":
                try:
                    self._say_edge(text)
                    return
                except Exception:
                    pass
            self._say_offline(text)

    def _say_edge(self, text: str) -> None:
        audio = asyncio.run(self._synthesize_edge(text))
        import soundfile as sf

        data, rate = sf.read(io.BytesIO(audio))
        sd.play(data, rate)
        sd.wait()

    async def _synthesize_edge(self, text: str) -> bytes:
        rate = f"{self.rate - 175:+d}%"
        communicate = edge_tts.Communicate(text, self.voice, rate=rate, volume=f"{int(self.volume * 100):+d}%")
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    def _say_offline(self, text: str) -> None:
        if not self._offline and pyttsx3:
            self._offline = pyttsx3.init()
        if not self._offline:
            print(text)
            return
        self._offline.setProperty("rate", self.rate)
        self._offline.setProperty("volume", self.volume)
        self._offline.say(text)
        self._offline.runAndWait()

    def beep(self, frequency: int = 880, duration: float = 0.12) -> None:
        rate = 16000
        t = np.linspace(0, duration, int(rate * duration), endpoint=False)
        wave = (0.18 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
        sd.play(wave, rate)
        sd.wait()
