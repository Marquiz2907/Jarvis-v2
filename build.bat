@echo off
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-build.txt
python scripts/make_icon.py
python -m PyInstaller jarvis.spec --noconfirm
echo.
echo App pronta: dist\Jarvis\Jarvis.exe
