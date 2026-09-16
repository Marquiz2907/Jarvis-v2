# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH)
icon = ROOT / "assets" / "jarvis.ico"

datas = []
for filename in ("config.yaml", ".env.example"):
    source = ROOT / filename
    if source.exists():
        datas.append((str(source), "."))
if icon.exists():
    datas.append((str(icon), "assets"))
png = ROOT / "assets" / "jarvis.png"
if png.exists():
    datas.append((str(png), "assets"))

binaries = []
# Python 3.11 dipende dal runtime Microsoft Visual C++. PyInstaller può non
# raccoglierlo quando si compila su GitHub Actions: includerlo rende il pacchetto
# portabile anche sui PC dove il redistributable non è già installato.
PYTHON_DIR = Path(sys.base_prefix)
for runtime in ("vcruntime140.dll", "vcruntime140_1.dll"):
    source = PYTHON_DIR / runtime
    if source.exists():
        binaries.append((str(source), "."))
hiddenimports = [
    "sounddevice",
    "soundfile",
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "google.genai",
    "google.genai.types",
    "openai",
    "edge_tts",
    "pyttsx3",
    "pynput",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    "pyperclip",
    "PIL",
    "yaml",
    "dotenv",
    "keyboard",
    "numpy",
    "httpx",
    "anyio",
    "core.assistant",
    "core.config",
    "core.paths",
    "audio.listener",
    "audio.tts",
    "llm.gemini",
    "llm.lmstudio",
    "llm.fallback",
    "tools.pc",
    "app",
    "desktop",
    "version",
]

for pkg in (
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "onnxruntime",
    "av",
    "sounddevice",
    "soundfile",
    "cffi",
    "google.genai",
):
    try:
        collected_datas, collected_binaries, collected_hidden = collect_all(pkg)
        datas += collected_datas
        binaries += collected_binaries
        hiddenimports += collected_hidden
    except Exception:
        pass

a = Analysis(
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "torchvision", "torchaudio"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jarvis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon) if icon.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Jarvis",
)
