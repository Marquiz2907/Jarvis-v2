from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        internal = app_dir() / "_internal"
        if internal.exists():
            return internal
        return app_dir()
    return app_dir()


def user_data_dir() -> Path:
    base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "Jarvis"
    base.mkdir(parents=True, exist_ok=True)
    return base


def prepare_runtime() -> Path:
    data = user_data_dir()
    (data / "screenshots").mkdir(parents=True, exist_ok=True)
    hf = data / "hf"
    hf.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf))
    (data / "logs").mkdir(parents=True, exist_ok=True)
    _seed_user_files()
    return data


def _seed_user_files() -> None:
    dest = app_dir()
    src = bundle_dir()
    for name in ("config.yaml", ".env.example"):
        target = dest / name
        source = src / name
        if not target.exists() and source.exists():
            shutil.copy2(source, target)
    env_path = dest / ".env"
    example = dest / ".env.example"
    if not env_path.exists() and example.exists():
        shutil.copy2(example, env_path)
