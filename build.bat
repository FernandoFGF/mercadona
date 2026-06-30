@echo off
REM Build script para Windows. Genera dist/AI Grocery Planner.exe.
REM Requisitos: pip install pyinstaller
REM mercadona-cli debe estar instalado aparte (npm install -g @ivorpad/mercadona)
pyinstaller --noconsole --onefile --name "AI Grocery Planner" main.py
