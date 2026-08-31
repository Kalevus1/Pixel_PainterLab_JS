@echo off
REM Lanza PixelPainter Lab (Dia 9). Reutiliza el entorno .venv_face o .venv.
cd /d "%~dp0"
set "PY=.venv\Scripts\pythonw.exe"
if not exist "%PY%" set "PY=..\.venv_face\Scripts\pythonw.exe"
if not exist "%PY%" (
  echo No encuentro el entorno. Ejecuta primero instalar.bat
  pause & exit /b 1
)
start "" "%PY%" pixelpainter_lab.py
