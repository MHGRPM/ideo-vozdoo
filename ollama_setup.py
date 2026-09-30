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


def has_model(host: str, model: str) -> bool:
    """Ollama puede estar encendido pero sin el modelo descargado: en ese
    caso las órdenes fallarían con un error críptico."""
    try:
        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=3)
        names = {m.get("name", "") for m in resp.json().get("models", [])}
    except Exception:
        return False
    wanted = model if ":" in model else f"{model}:latest"
    return wanted in names or model in names


def create_assistant_model(host: str, base_model: str) -> bool:
    """Crea en Ollama el modelo `vozdoo`: el modelo base con todo el
    conocimiento del asistente de prompts y contenidos ya dentro, para
    poder chatear con él también desde la app de Ollama. Si la versión de
    Ollama no lo soporta, no pasa nada: Vozdoo manda ese conocimiento en
    cada orden de todas formas."""
    from polish_actions import ASSISTANT_MODEL_NAME, assistant_system_prompt

    try:
        resp = requests.post(
            f"{host.rstrip('/')}/api/create",
            json={
                "model": ASSISTANT_MODEL_NAME,
                "from": base_model,
                "system": assistant_system_prompt(),
                "parameters": {"temperature": 0.4, "num_ctx": 8192},
                "stream": False,
            },
            timeout=300,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo crear el asistente '%s' en Ollama: %s", ASSISTANT_MODEL_NAME, exc)
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


def pull_model(
    host: str,
    model: str,
    on_progress: Callable[[str], None],
    on_fraction: Callable[[float], None] | None = None,
) -> None:
    """`on_progress` recibe el estado en texto; `on_fraction`, si se pasa,
    recibe el avance real de la descarga (0..1) para pintar una barra."""
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
            if on_fraction is not None:
                total = data.get("total") or 0
                completed = data.get("completed") or 0
                if total:
                    on_fraction(completed / total)


def main(argv: list[str]) -> int:
    """Uso desde los instaladores:
    python ollama_setup.py prepare <modelo>   descarga el modelo y crea el asistente"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    host = "http://localhost:11434"
    if len(argv) >= 2 and argv[0] == "prepare":
        model = argv[1]
        if not is_ollama_running(host):
            print("Ollama no responde todavía.")
            return 1
        if not has_model(host, model):
            last = [""]

            def show(status: str) -> None:
                if status != last[0]:
                    print(f"   {status}")
                    last[0] = status

            def bar(fraction: float) -> None:
                pct = int(fraction * 100)
                print(f"\r   descargando... {pct:3d}%", end="", flush=True)

            pull_model(host, model, on_progress=lambda s: None if s.startswith("pulling") else show(s), on_fraction=bar)
            print()
        ok = create_assistant_model(host, model)
        print("   Asistente 'vozdoo' creado en Ollama." if ok else "   (Asistente de chat no creado; Vozdoo funciona igual.)")
        return 0
    print(main.__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
