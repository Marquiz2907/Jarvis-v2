from __future__ import annotations

import re
import time
from collections import deque

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("è", "e").replace("é", "e")
    text = re.sub(r"[^a-z0-9àèéìòù\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class Listener:
    def __init__(
        self,
        sample_rate: int = 16000,
        language: str = "it",
        whisper_model: str = "small",
        energy_threshold: float = 0.012,
        wake_words: list[str] | None = None,
        input_device: str | int | None = None,
        input_gain: float = 1.0,
    ):
        self.sample_rate = sample_rate
        self.language = language
        self.energy_threshold = energy_threshold
        self.wake_words = [_normalize(w) for w in (wake_words or ["ehi jarvis", "hey jarvis"])]
        self.input_device = input_device
        self.input_gain = max(0.1, min(float(input_gain), 4.0))
        self.model = WhisperModel(whisper_model, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        audio = np.clip(audio.astype(np.float32), -1.0, 1.0)
        segments, _info = self.model.transcribe(
            audio,
            language=self.language,
            vad_filter=True,
            beam_size=1,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()

    def contains_wake_word(self, text: str) -> bool:
        norm = _normalize(text)
        if not norm:
            return False
        compact = norm.replace(" ", "")
        for phrase in self.wake_words:
            if phrase in norm or phrase.replace(" ", "") in compact:
                return True
            if "jarvis" in compact and any(token in compact for token in ("ehy", "ehi", "hey", "ei", "ahi", "ok")):
                return True
        return "jarvis" in compact and len(norm.split()) <= 4

    def strip_wake_word(self, text: str) -> str:
        norm_original = text.strip()
        lowered = _normalize(norm_original)
        for phrase in sorted(self.wake_words, key=len, reverse=True):
            if lowered.startswith(phrase):
                idx = len(phrase)
                # map back roughly by cutting first words
                words = norm_original.split()
                wake_len = len(phrase.split())
                return " ".join(words[wake_len:]).strip()
        return re.sub(r"(?i)^(ehy|ehi|hey|ei|ahi|ok)\s+jarvis[,:\s]*", "", norm_original).strip()

    def record_seconds(self, seconds: float) -> np.ndarray:
        frames = int(self.sample_rate * seconds)
        audio = sd.rec(frames, samplerate=self.sample_rate, channels=1, dtype="float32", device=self.input_device)
        sd.wait()
        return np.clip(audio.reshape(-1) * self.input_gain, -1.0, 1.0)

    def listen_utterance(self, max_seconds: float = 12.0, silence_seconds: float = 1.1) -> str:
        chunk = 0.2
        chunk_frames = int(self.sample_rate * chunk)
        voiced = []
        started = False
        silent_for = 0.0
        elapsed = 0.0
        while elapsed < max_seconds:
            block = sd.rec(chunk_frames, samplerate=self.sample_rate, channels=1, dtype="float32", device=self.input_device)
            sd.wait()
            samples = np.clip(block.reshape(-1) * self.input_gain, -1.0, 1.0)
            energy = float(np.sqrt(np.mean(np.square(samples) + 1e-12)))
            elapsed += chunk
            if energy >= self.energy_threshold:
                started = True
                silent_for = 0.0
                voiced.append(samples)
            elif started:
                silent_for += chunk
                voiced.append(samples)
                if silent_for >= silence_seconds:
                    break
        if not voiced:
            return ""
        audio = np.concatenate(voiced)
        return self.transcribe(audio)

    def wait_for_wake(self, poll_seconds: float = 1.6, stop_event=None) -> str | None:
        """Ascolto continuo. Restituisce il testo dopo la wake word, se presente nello stesso enunciato."""
        overlap = deque(maxlen=int(self.sample_rate * 0.6))
        slice_sec = 0.5
        buffered: list[np.ndarray] = []
        collected = 0.0
        while True:
            if stop_event is not None and stop_event.is_set():
                return None
            chunk = self.record_seconds(slice_sec)
            buffered.append(chunk)
            collected += slice_sec
            if collected < poll_seconds:
                continue
            audio_chunk = np.concatenate(buffered)
            buffered = []
            collected = 0.0
            energy = float(np.sqrt(np.mean(np.square(audio_chunk) + 1e-12)))
            if energy < self.energy_threshold * 0.7:
                overlap.clear()
                continue
            if overlap:
                audio = np.concatenate([np.array(overlap, dtype=np.float32), audio_chunk])
            else:
                audio = audio_chunk
            overlap.extend(audio_chunk.tolist())
            text = self.transcribe(audio)
            if self.contains_wake_word(text):
                return self.strip_wake_word(text)
            time.sleep(0.01)
