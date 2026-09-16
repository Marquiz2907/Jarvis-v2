from __future__ import annotations

import argparse
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.assistant import Jarvis
from core.config import load_settings, save_runtime_settings
from core.paths import prepare_runtime
from version import APP_NAME, __version__

BG, SURFACE, PANEL, FIELD = "#050b14", "#0a1525", "#0e1d31", "#07111f"
FG, MUTED, CYAN, RED = "#e7f5ff", "#84a0ba", "#39e6dd", "#ff7782"


class JarvisDesktop:
    def __init__(self) -> None:
        prepare_runtime()
        self.settings = load_settings()
        self.jarvis: Jarvis | None = None
        self.worker: threading.Thread | None = None
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.testing = False
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} · Command Center")
        self.root.geometry("970x760")
        self.root.minsize(820, 640)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._style()
        self._vars()
        self._build()
        self.root.after(120, self._drain)

    def _style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=SURFACE, foreground=MUTED, padding=(18, 10), borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", CYAN)])
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=FG, arrowcolor=CYAN, padding=6)
        style.configure("TRadiobutton", background=PANEL, foreground=FG, font=("Segoe UI", 10))

    def _vars(self) -> None:
        s = self.settings
        self.backend, self.api_key, self.gemini_model = tk.StringVar(value=s.backend), tk.StringVar(value=s.gemini_api_key), tk.StringVar(value=s.gemini_model)
        self.lm_url, self.lm_model = tk.StringVar(value=s.lmstudio_base_url), tk.StringVar(value=s.lmstudio_model)
        self.sample_rate, self.language, self.whisper_model = tk.StringVar(value=str(s.sample_rate)), tk.StringVar(value=s.language), tk.StringVar(value=s.whisper_model)
        self.threshold, self.gain = tk.DoubleVar(value=s.energy_threshold), tk.DoubleVar(value=s.input_gain)
        self.command_timeout, self.silence, self.wake_poll = tk.DoubleVar(value=s.command_timeout_sec), tk.DoubleVar(value=s.silence_seconds), tk.DoubleVar(value=s.wake_poll_seconds)
        self.wake_words = tk.StringVar(value=", ".join(s.wake_words))
        self.tts_engine, self.tts_voice = tk.StringVar(value=s.tts_engine), tk.StringVar(value=s.tts_voice)
        self.tts_rate, self.tts_volume = tk.IntVar(value=s.tts_rate), tk.DoubleVar(value=s.tts_volume)
        self.name, self.history, self.confirm = tk.StringVar(value=s.name), tk.IntVar(value=s.max_history), tk.BooleanVar(value=s.confirm_destructive)
        self.status, self.mic_reading, self.text_command = tk.StringVar(value="STANDBY"), tk.StringVar(value="Pronto per il test"), tk.StringVar()
        self.mic = tk.StringVar(value="Microfono predefinito")
        self._load_devices()

    def _load_devices(self) -> None:
        self.device_map: dict[str, int | None] = {"Microfono predefinito": None}
        try:
            for index, item in enumerate(sd.query_devices()):
                if int(item["max_input_channels"]) > 0:
                    self.device_map[f"{index} · {item['name']}"] = index
            if self.settings.input_device is not None:
                for label, index in self.device_map.items():
                    if str(index) == str(self.settings.input_device):
                        self.mic.set(label)
                        break
        except Exception as exc:
            self.events.put(("error", f"Elenco microfoni non disponibile: {exc}"))

    def _card(self, parent: tk.Widget, title: str, subtitle: str = "") -> tk.Frame:
        card = tk.Frame(parent, bg=PANEL, highlightbackground="#17324c", highlightthickness=1)
        tk.Label(card, text=title, bg=PANEL, fg=CYAN, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
        if subtitle:
            tk.Label(card, text=subtitle, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(1, 8))
        return card

    def _label(self, parent: tk.Widget, text: str, row: int) -> None:
        tk.Label(parent, text=text.upper(), bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).grid(row=row, column=0, sticky="w", padx=14, pady=(10, 3))

    def _entry(self, parent: tk.Widget, variable: tk.Variable, row: int, show: str | None = None) -> None:
        tk.Entry(parent, textvariable=variable, show=show, bg=FIELD, fg=FG, insertbackground=CYAN, relief="flat", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 8))

    def _button(self, parent: tk.Widget, text: str, command, primary: bool = False, **pack) -> tk.Button:
        button = tk.Button(parent, text=text, command=command, bg=CYAN if primary else "#172b43", fg="#032525" if primary else FG, activebackground="#71fff8" if primary else "#244461", relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"), padx=14, pady=8)
        button.pack(**pack)
        return button

    def _build(self) -> None:
        top = tk.Frame(self.root, bg=BG); top.pack(fill="x", padx=24, pady=(18, 12))
        tk.Label(top, text="J.A.R.V.I.S", bg=BG, fg=CYAN, font=("Segoe UI", 28, "bold")).pack(side="left")
        tk.Label(top, text="PERSONAL INTELLIGENCE INTERFACE", bg=BG, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=14, pady=(11, 0))
        tk.Label(top, textvariable=self.status, bg="#123047", fg=CYAN, font=("Segoe UI", 9, "bold"), padx=12, pady=6).pack(side="right", pady=3)
        control = tk.Frame(self.root, bg=SURFACE, highlightbackground="#183753", highlightthickness=1); control.pack(fill="x", padx=24)
        self.start_btn = self._button(control, "◉  AVVIA ASCOLTO", self.start, True, side="left", padx=12, pady=12)
        self.stop_btn = self._button(control, "■  STOP", self.stop, side="left", padx=(0, 8), pady=12); self.stop_btn.configure(state="disabled")
        self._button(control, "SALVA CONFIGURAZIONE", self.save, side="left", pady=12)
        tk.Label(control, text="Wake word · Ctrl + Alt + J", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", padx=14)
        tabs = ttk.Notebook(self.root); tabs.pack(fill="both", expand=True, padx=24, pady=(14, 10))
        console, audio, brain = tk.Frame(tabs, bg=BG), tk.Frame(tabs, bg=BG), tk.Frame(tabs, bg=BG)
        tabs.add(console, text="  CONSOLE  "); tabs.add(audio, text="  AUDIO  "); tabs.add(brain, text="  INTELLIGENZA  ")
        self._build_console(console); self._build_audio(audio); self._build_brain(brain)

    def _build_console(self, parent: tk.Frame) -> None:
        command = self._card(parent, "COMANDO DIRETTO", "Scrivi a Jarvis: utile anche senza microfono."); command.pack(fill="x", pady=(12, 10))
        row = tk.Frame(command, bg=PANEL); row.pack(fill="x", padx=14, pady=(0, 13))
        box = tk.Entry(row, textvariable=self.text_command, bg=FIELD, fg=FG, insertbackground=CYAN, relief="flat", font=("Segoe UI", 11)); box.pack(side="left", fill="x", expand=True, ipady=8); box.bind("<Return>", lambda _: self.send_text())
        self._button(row, "INVIA", self.send_text, True, side="left", padx=(8, 0))
        log = self._card(parent, "DIARIO DI BORDO", "Eventi, trascrizioni e risposte della sessione."); log.pack(fill="both", expand=True)
        self.log = tk.Text(log, bg=FIELD, fg=FG, insertbackground=FG, relief="flat", wrap="word", font=("Cascadia Mono", 10), padx=12, pady=10); self.log.pack(fill="both", expand=True, padx=14, pady=(0, 14)); self.log.configure(state="disabled")
        for tag, color in (("user", "#8ef0ae"), ("assistant", CYAN), ("system", MUTED), ("error", RED)): self.log.tag_config(tag, foreground=color)

    def _build_audio(self, parent: tk.Frame) -> None:
        parent.columnconfigure((0, 1), weight=1)
        mic = self._card(parent, "MICROFONO", "Selezione ingresso, sensibilità e verifica rapida."); mic.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=12); mic.columnconfigure(0, weight=1)
        self._label(mic, "Dispositivo di input", 0)
        self.device_combo = ttk.Combobox(mic, textvariable=self.mic, values=list(self.device_map), state="readonly"); self.device_combo.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 4))
        tools = tk.Frame(mic, bg=PANEL); tools.grid(row=2, column=0, sticky="ew", padx=14, pady=(3, 4)); self._button(tools, "AGGIORNA", self.refresh_devices, side="left"); self._button(tools, "TEST 2 SEC", self.test_microphone, True, side="left", padx=(8, 0))
        tk.Label(mic, textvariable=self.mic_reading, bg=PANEL, fg=CYAN, font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", padx=14, pady=(3, 6))
        self._label(mic, "Campionamento (Hz)", 4); ttk.Combobox(mic, textvariable=self.sample_rate, values=("8000", "16000", "24000", "44100", "48000"), state="readonly").grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 8))
        for row, label, var, low, high, step in ((6, "Guadagno input", self.gain, .5, 3, .1), (8, "Soglia rumore / voce", self.threshold, .002, .08, .001)):
            self._label(mic, label, row); tk.Scale(mic, variable=var, from_=low, to=high, resolution=step, orient="horizontal", bg=PANEL, fg=FG, troughcolor=FIELD, highlightthickness=0, activebackground=CYAN).grid(row=row+1, column=0, sticky="ew", padx=10, pady=(0, 8))
        rec = self._card(parent, "RICONOSCIMENTO VOCALE", "Wake word, modello Whisper e tempi d'ascolto."); rec.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=12); rec.columnconfigure(0, weight=1)
        self._label(rec, "Lingua", 0); ttk.Combobox(rec, textvariable=self.language, values=("it", "en", "es", "fr", "de", "auto"), state="readonly").grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        self._label(rec, "Modello Whisper", 2); ttk.Combobox(rec, textvariable=self.whisper_model, values=("tiny", "base", "small", "medium", "large-v3"), state="readonly").grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 8))
        self._label(rec, "Wake words (separate da virgola)", 4); self._entry(rec, self.wake_words, 5)
        for row, label, var, low, high, step in ((6, "Timeout comando (secondi)", self.command_timeout, 3, 30, 1), (8, "Silenzio per chiudere (secondi)", self.silence, .4, 3, .1), (10, "Finestra rilevamento wake word", self.wake_poll, .8, 4, .1)):
            self._label(rec, label, row); tk.Scale(rec, variable=var, from_=low, to=high, resolution=step, orient="horizontal", bg=PANEL, fg=FG, troughcolor=FIELD, highlightthickness=0, activebackground=CYAN).grid(row=row+1, column=0, sticky="ew", padx=10, pady=(0, 4))

    def _build_brain(self, parent: tk.Frame) -> None:
        parent.columnconfigure((0, 1), weight=1)
        brain = self._card(parent, "MOTORE AI", "Scegli cloud Gemini o il tuo server locale LM Studio."); brain.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=12); brain.columnconfigure(0, weight=1)
        radios = tk.Frame(brain, bg=PANEL); radios.grid(row=0, column=0, sticky="w", padx=14, pady=(8, 2)); ttk.Radiobutton(radios, text="Gemini · cloud", variable=self.backend, value="gemini").pack(side="left", padx=(0, 16)); ttk.Radiobutton(radios, text="LM Studio · locale", variable=self.backend, value="lmstudio").pack(side="left")
        for row, label, var, secret in ((1, "Gemini API key", self.api_key, True), (3, "Modello Gemini", self.gemini_model, False), (5, "URL LM Studio", self.lm_url, False), (7, "Modello LM Studio (vuoto = automatico)", self.lm_model, False)):
            self._label(brain, label, row); self._entry(brain, var, row + 1, "•" if secret else None)
        voice = self._card(parent, "VOCE E COMPORTAMENTO", "Personalizza la risposta e conserva il contesto."); voice.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=12); voice.columnconfigure(0, weight=1)
        self._label(voice, "Nome assistente", 0); self._entry(voice, self.name, 1)
        self._label(voice, "Motore TTS", 2); ttk.Combobox(voice, textvariable=self.tts_engine, values=("edge", "offline"), state="readonly").grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 8))
        self._label(voice, "Voce Edge", 4); self._entry(voice, self.tts_voice, 5)
        for row, label, var, low, high, step in ((6, "Velocità voce", self.tts_rate, 100, 250, 5), (8, "Volume voce", self.tts_volume, 0, 1, .05)):
            self._label(voice, label, row); tk.Scale(voice, variable=var, from_=low, to=high, resolution=step, orient="horizontal", bg=PANEL, fg=FG, troughcolor=FIELD, highlightthickness=0, activebackground=CYAN).grid(row=row+1, column=0, sticky="ew", padx=10)
        self._label(voice, "Memoria conversazione", 10); tk.Spinbox(voice, textvariable=self.history, from_=1, to=100, bg=FIELD, fg=FG, buttonbackground="#1c3854", insertbackground=FG, relief="flat").grid(row=11, column=0, sticky="ew", padx=14, pady=(0, 8))
        tk.Checkbutton(voice, text="Chiedi conferma per azioni distruttive", variable=self.confirm, bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=CYAN, selectcolor=FIELD, font=("Segoe UI", 9)).grid(row=12, column=0, sticky="w", padx=10, pady=(2, 14))

    def _append(self, kind: str, message: str) -> None:
        self.log.configure(state="normal"); prefix = {"user":"TU", "assistant":"JARVIS", "system":"SISTEMA", "error":"ERRORE"}.get(kind, kind.upper()); self.log.insert("end", f"[{prefix}]  {message}\n", kind); self.log.see("end"); self.log.configure(state="disabled")

    def _drain(self) -> None:
        while True:
            try: kind, message = self.events.get_nowait()
            except queue.Empty: break
            self._append(kind, message)
            if kind == "system" and "Pronto" in message: self.status.set("IN ASCOLTO")
            if kind == "system" and "fermato" in message:
                self.status.set("STANDBY"); self.start_btn.configure(state="normal"); self.stop_btn.configure(state="disabled")
        self.root.after(120, self._drain)

    def _apply_form(self) -> None:
        s = self.settings
        s.backend, s.gemini_api_key, s.gemini_model = self.backend.get(), self.api_key.get().strip(), self.gemini_model.get().strip()
        s.lmstudio_base_url, s.lmstudio_model, s.input_device = self.lm_url.get().strip(), self.lm_model.get().strip(), self.device_map.get(self.mic.get())
        s.sample_rate, s.language, s.whisper_model = int(self.sample_rate.get()), self.language.get(), self.whisper_model.get()
        s.energy_threshold, s.input_gain = float(self.threshold.get()), float(self.gain.get())
        s.command_timeout_sec, s.silence_seconds, s.wake_poll_seconds = float(self.command_timeout.get()), float(self.silence.get()), float(self.wake_poll.get())
        s.wake_words = [w.strip().lower() for w in self.wake_words.get().split(",") if w.strip()] or ["ehi jarvis"]
        s.tts_engine, s.tts_voice, s.tts_rate, s.tts_volume = self.tts_engine.get(), self.tts_voice.get().strip(), int(self.tts_rate.get()), float(self.tts_volume.get())
        s.name, s.max_history, s.confirm_destructive = self.name.get().strip() or "Jarvis", int(self.history.get()), bool(self.confirm.get())

    def save(self) -> None:
        try:
            self._apply_form(); save_runtime_settings(self.settings); self._append("system", "Configurazione salvata. Le modifiche audio si applicano al prossimo avvio dell'ascolto.")
        except (ValueError, tk.TclError) as exc: messagebox.showerror(APP_NAME, f"Impostazione non valida: {exc}")

    def refresh_devices(self) -> None:
        self._load_devices(); self.device_combo.configure(values=list(self.device_map)); self.mic_reading.set(f"{len(self.device_map)-1} microfoni rilevati")

    def test_microphone(self) -> None:
        if self.testing or (self.worker and self.worker.is_alive()): self.mic_reading.set("Ferma l'ascolto continuo prima del test"); return
        self.testing = True; self.mic_reading.set("Registrazione in corso… parla ora")
        def test() -> None:
            try:
                rate = int(self.sample_rate.get()); audio = sd.rec(rate * 2, samplerate=rate, channels=1, dtype="float32", device=self.device_map.get(self.mic.get())); sd.wait(); level = float(np.sqrt(np.mean(np.square(audio)))) * float(self.gain.get())
                self.events.put(("system", f"Test microfono completato · livello RMS {level:.4f}")); self.root.after(0, lambda: self.mic_reading.set(f"Segnale: {level:.4f}  ·  soglia: {self.threshold.get():.3f}"))
            except Exception as exc: self.events.put(("error", f"Test microfono fallito: {exc}")); self.root.after(0, lambda: self.mic_reading.set("Test non riuscito"))
            finally: self.testing = False
        threading.Thread(target=test, daemon=True).start()

    def start(self) -> None:
        if self.worker and self.worker.is_alive(): return
        try: self._apply_form()
        except (ValueError, tk.TclError) as exc: messagebox.showerror(APP_NAME, f"Impostazione non valida: {exc}"); return
        if self.settings.backend == "gemini" and not self.settings.gemini_api_key: messagebox.showerror(APP_NAME, "Inserisci la Gemini API key oppure passa a LM Studio."); return
        self.save(); self.status.set("AVVIO…"); self.start_btn.configure(state="disabled"); self.stop_btn.configure(state="normal")
        def boot() -> None:
            try: self.jarvis = Jarvis(self.settings, on_log=lambda k, m: self.events.put((k, m))); self.jarvis.run()
            except Exception as exc: self.events.put(("error", str(exc))); self.events.put(("system", "Ascolto fermato"))
        self.worker = threading.Thread(target=boot, daemon=True); self.worker.start()

    def send_text(self) -> None:
        text = self.text_command.get().strip()
        if not text: return
        self.text_command.set("")
        if self.worker and self.worker.is_alive(): self.events.put(("system", "Ferma l'ascolto continuo prima di inviare un comando testuale.")); return
        try: self._apply_form()
        except (ValueError, tk.TclError) as exc: messagebox.showerror(APP_NAME, f"Impostazione non valida: {exc}"); return
        self.status.set("ELABORAZIONE…")
        def run_text() -> None:
            try: Jarvis(self.settings, on_log=lambda k, m: self.events.put((k, m))).handle_command(text)
            except Exception as exc: self.events.put(("error", str(exc)))
            finally: self.root.after(0, lambda: self.status.set("STANDBY"))
        threading.Thread(target=run_text, daemon=True).start()

    def stop(self) -> None:
        if self.jarvis: self.jarvis.stop()
        self.status.set("ARRESTO…")

    def _on_close(self) -> None:
        self.stop(); self.root.destroy()

    def run(self) -> None: self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis desktop"); parser.add_argument("--cli", action="store_true", help="Avvia la versione terminale"); args, rest = parser.parse_known_args()
    if args.cli:
        from app import main as cli_main
        sys.argv = [sys.argv[0], *rest]; cli_main(); return
    JarvisDesktop().run()


if __name__ == "__main__": main()
