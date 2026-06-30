#!/usr/bin/env bash
# Build script para Linux/macOS. Genera dist/AI Grocery Planner.
# Requisitos: pip install pyinstaller
# mercadona-cli debe estar instalado aparte (npm install -g @ivorpad/mercadona)
pyinstaller --noconsole --onefile --name "AI Grocery Planner" main.py
