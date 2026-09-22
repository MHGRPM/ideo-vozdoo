#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "==> Creando entorno virtual (.venv)..."
    python3 -m venv .venv
fi

echo "==> Activando entorno virtual..."
source .venv/bin/activate

echo "==> Instalando dependencias (la primera vez puede tardar 1-3 minutos, descarga el motor de Whisper)..."
pip install --upgrade pip
pip install -r requirements.txt

if [ "$(uname)" = "Linux" ]; then
    python -c "from PyQt6.QtWidgets import QApplication" 2>/dev/null || \
        echo "==> Aviso: PyQt6 no arranca. En Linux suele faltar una librería del sistema: sudo apt install libxcb-cursor0"
fi

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "==> Creado .env con valores por defecto. Editalo si quieres cambiar la tecla o el modelo."
fi

echo "==> Arrancando Vozdoo (la primera vez tarda otro poco más descargando el modelo Whisper)..."
python vozdoo_core.py
