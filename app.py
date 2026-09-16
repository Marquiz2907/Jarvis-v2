from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.panel import Panel

from core.assistant import Jarvis
from core.config import load_settings
from core.paths import prepare_runtime
from version import APP_NAME, __version__

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jarvis — assistente vocale")
    parser.add_argument(
        "--backend",
        choices=["gemini", "lmstudio"],
        help="Forza Gemini o LM Studio",
    )
    parser.add_argument("--text", help="Esegue un comando testuale senza microfono e termina")
    parser.add_argument("--gui", action="store_true", help="Apre l'app grafica")
    return parser.parse_args()


def main() -> None:
    prepare_runtime()
    args = parse_args()
    if args.gui:
        from desktop import JarvisDesktop

        JarvisDesktop().run()
        return

    settings = load_settings()
    if args.backend:
        settings.backend = args.backend
    if args.text:
        settings.text_only = True

    console.print(
        Panel.fit(
            f"[bold cyan]{APP_NAME}[/bold cyan]  v{__version__}\n"
            "Wake word: [white]ehy Jarvis[/white]  ·  Hotkey: [white]Ctrl+Alt+J[/white]\n"
            f"Backend: [yellow]{settings.backend}[/yellow]",
            border_style="cyan",
        )
    )

    jarvis = Jarvis(settings)
    if args.text:
        jarvis.handle_command(args.text)
        return
    try:
        jarvis.run()
    except KeyboardInterrupt:
        jarvis.stop()
        console.print("\n[dim]Jarvis in standby.[/dim]")


if __name__ == "__main__":
    main()
