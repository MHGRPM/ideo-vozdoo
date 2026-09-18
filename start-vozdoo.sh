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

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "==> Creado .env con valores por defecto. Editalo si quieres cambiar la tecla o el modelo."
fi

echo "==> Arrancando Vozdoo (la primera vez tarda otro poco más descargando el modelo Whisper)..."
python vozdoo_core.py
