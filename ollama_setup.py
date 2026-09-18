"""Detectar, instalar (con confirmación explícita del usuario) y
preparar Ollama para usuarios sin conocimientos técnicos."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from collections.abc import Callable

import requests

log = logging.getLogger("vozdoo")


def is_ollama_running(host: str) -> bool:
    try:
        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def linux_mac_install_command() -> str:
    return "curl -fsSL https://ollama.com/install.sh | sh"


def run_install_linux_mac() -> subprocess.Popen:
    """Abre una terminal visible ejecutando el instalador oficial, porque
    el script puede pedir la contraseña de sudo y necesita un TTY.
    Prueba varios emuladores de terminal comunes en Linux; en Mac usa
    Terminal.app vía `open`."""
    cmd = linux_mac_install_command()
    full = f'{cmd}; echo; read -p "Pulsa Enter para cerrar esta ventana"'

    if sys.platform == "darwin":
        script = full.replace('"', '\\"')
        return subprocess.Popen(
            ["osascript", "-e", f'tell app "Terminal" to do script "{script}"']
        )

    for terminal in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
        try:
            if terminal == "gnome-terminal":
                return subprocess.Popen([terminal, "--", "bash", "-c", full])
            return subprocess.Popen([terminal, "-e", "bash", "-c", full])
        except FileNotFoundError:
            continue

    raise RuntimeError(
        "No se encontró un emulador de terminal. Copia y pega esto en una "
        f"terminal manualmente:\n{cmd}"
    )


def download_windows_installer(dest_path: str) -> str:
    url = "https://ollama.com/download/OllamaSetup.exe"
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    return dest_path


def launch_windows_installer(path: str) -> None:
    subprocess.Popen([path])


def pull_model(host: str, model: str, on_progress: Callable[[str], None]) -> None:
    with requests.post(
        f"{host.rstrip('/')}/api/pull",
        json={"model": model, "stream": True},
        stream=True,
        timeout=None,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            status = data.get("status", "")
            on_progress(status)
