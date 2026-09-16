# Jarvis

Assistente vocale Windows. Si attiva con **ehy Jarvis**, usa **Gemini** oppure **LM Studio**.

## App per PC (GitHub Actions)

1. Crea un repo GitHub e carica questo progetto.
2. GitHub → **Actions** → **Build Windows app** → **Run workflow**.
3. A build finita scarica l’artifact **Jarvis-windows**.
4. Scompatta e avvia `Jarvis\Jarvis.exe`.

Per una release scaricabile, crea un tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

La Action pubblica `Jarvis-windows.zip` nella Release.

## Primo avvio

1. Copia `.env.example` in `.env` nella stessa cartella di `Jarvis.exe`.
2. Gemini: metti `GEMINI_API_KEY` (oppure inseriscila nella finestra e premi Salva).
3. LM Studio: avvia il server locale, scegli *LM Studio* nell’app.
4. Il modello vocale Whisper viene scaricato al primo ascolto in `%LOCALAPPDATA%\Jarvis`.

## Command Center

La finestra desktop ora conserva tutte le funzionalità vocali e aggiunge tre pannelli:

- **Console**: diario della sessione e comando scritto, utile anche senza microfono.
- **Audio**: scelta del microfono Windows, test del segnale, guadagno, soglia del rumore, lingua/modello Whisper, wake word e tempi di ascolto.
- **Intelligenza**: Gemini o LM Studio, voce TTS, velocità, volume, memoria e conferma delle azioni sensibili.

Premi **Salva configurazione** dopo le modifiche. Le impostazioni audio vengono applicate quando riavvii l'ascolto; il dispositivo selezionato viene salvato in `config.yaml`.

## Sviluppo locale

```bat
start.bat
```

```bat
python desktop.py
python app.py --text "che ore sono"
python app.py --backend lmstudio
```

Build locale:

```bat
python scripts/make_icon.py
pip install -r requirements-build.txt
python -m PyInstaller jarvis.spec --noconfirm
```

L’eseguibile finisce in `dist\Jarvis\Jarvis.exe`.
