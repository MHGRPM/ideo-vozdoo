#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Creado .env con valores por defecto. Editalo si quieres cambiar la tecla o el modelo."
fi

python vozdoo_core.py
