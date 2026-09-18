# Dictar + pulir con IA (burbuja) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir un segundo hotkey a Vozdoo que, además de transcribir, pasa el texto por un LLM (Ollama local o una API key personal) a través de una burbuja flotante con acciones predefinidas y una instrucción personalizada por voz, antes de pegarlo.

**Architecture:** Tres módulos nuevos e independientes (`clipboard_paste.py`, `llm_engine.py`, `ollama_setup.py`, `polish_bubble.py`) que no dependen entre sí más que por tipos simples, más cambios mínimos y localizados en `vozdoo_core.py` para registrar el segundo hotkey y ejecutar un bucle de Tkinter en el hilo principal (con `pynput.Listener` corriendo en segundo plano, en vez del `.join()` bloqueante actual).

**Tech Stack:** Python 3.10+, `tkinter` (stdlib, requiere `python3-tk` en Linux), `requests` (nuevo), `pytest` (nuevo, solo dev).

**Spec:** `docs/superpowers/specs/2026-09-18-polish-bubble-design.md`

## Global Constraints

- El hotkey normal (`VOZDOO_HOTKEY`, default `ctrl+win`) no cambia de comportamiento: sigue pegando el texto tal cual, instantáneo.
- El repo es público (`github.com/MHGRPM/ideo-vozdoo`): ningún fichero nuevo puede mencionar JARBOO, ElevenLabs, Anthropic, Boomatik ni nombres de empleados.
- Ningún instalador (Ollama) se ejecuta sin un clic explícito del usuario en la burbuja.
- Motor de IA por defecto: Ollama local, modelo `qwen2.5:3b-instruct`, host `http://localhost:11434`. Si `VOZDOO_LLM_API_KEY` no está vacío, se usa `ApiKeyEngine` en su lugar (formato chat completions estilo OpenAI, sirve para OpenAI y Gemini vía su capa de compatibilidad).
- `VOZDOO_HOTKEY` y `VOZDOO_POLISH_HOTKEY` no pueden solaparse (ningún conjunto de teclas puede contener todas las del otro); default de `VOZDOO_POLISH_HOTKEY` es `alt+win`.
- Fuera de alcance explícitamente: automatizar Gemini vía navegador.

---

## File Structure

```
ideo-vozdoo/
├── vozdoo_core.py          # MODIFICAR: 2º hotkey, Tk mainloop, delega a los módulos nuevos
├── clipboard_paste.py      # NUEVO: paste_text() extraído de vozdoo_core.py
├── llm_engine.py           # NUEVO: OllamaEngine, ApiKeyEngine, get_engine()
├── ollama_setup.py         # NUEVO: detección + instalación + pull de modelo
├── polish_bubble.py        # NUEVO: ventana tkinter, PRESET_INSTRUCTIONS
├── requirements.txt        # MODIFICAR: + requests
├── requirements-dev.txt    # NUEVO: pytest
├── .env.example            # MODIFICAR: + 6 variables nuevas
├── README.md                # MODIFICAR: prerrequisito python3-tk, uso del 2º hotkey, config, troubleshooting
├── tests/
│   ├── __init__.py          # NUEVO
│   ├── test_hotkey.py       # NUEVO: parse_hotkey + hotkeys_overlap (de vozdoo_core.py)
│   ├── test_clipboard_paste.py  # NUEVO
│   ├── test_llm_engine.py   # NUEVO
│   ├── test_ollama_setup.py # NUEVO
│   └── test_polish_bubble.py # NUEVO (solo PRESET_INSTRUCTIONS, sin UI)
```

---

### Task 1: Infraestructura de tests + test de regresión del parser de hotkeys

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/test_hotkey.py`
- Modify: `vozdoo_core.py` (añadir `hotkeys_overlap`, sin cambiar comportamiento existente)

**Interfaces:**
- Produces: `parse_hotkey(spec: str) -> frozenset | None` (ya existe, sin cambios)
- Produces: `hotkeys_overlap(a: frozenset, b: frozenset) -> bool` (nuevo)

- [ ] **Step 1: Crear `requirements-dev.txt`**

```
pytest>=8.0.0
```

- [ ] **Step 2: Crear `tests/__init__.py` vacío**

```python
```

- [ ] **Step 3: Escribir el test de `parse_hotkey` (regresión sobre código ya existente)**

`tests/test_hotkey.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pynput import keyboard as pkb

from vozdoo_core import parse_hotkey, hotkeys_overlap


def test_parse_single_key():
    assert parse_hotkey("f9") == frozenset({pkb.Key.f9})


def test_parse_modifier_only_combo():
    assert parse_hotkey("ctrl+win") == frozenset({"ctrl", "cmd"})


def test_parse_combo_with_letter():
    assert parse_hotkey("ctrl+alt+d") == frozenset(
        {"ctrl", "alt", pkb.KeyCode.from_char("d")}
    )


def test_parse_unknown_key_returns_none():
    assert parse_hotkey("ctrl+notakey") is None


def test_hotkeys_overlap_true_when_subset():
    normal = parse_hotkey("ctrl+win")
    polish = parse_hotkey("ctrl+alt+win")
    assert hotkeys_overlap(normal, polish) is True


def test_hotkeys_overlap_false_when_disjoint_enough():
    normal = parse_hotkey("ctrl+win")
    polish = parse_hotkey("alt+win")
    assert hotkeys_overlap(normal, polish) is False
```

- [ ] **Step 4: Añadir `hotkeys_overlap` a `vozdoo_core.py`**

Justo debajo de la función `parse_hotkey` existente:

```python
def hotkeys_overlap(a: frozenset, b: frozenset) -> bool:
    """True si uno de los dos combos contiene todas las teclas del otro.

    Si eso pasa, pulsar el combo largo dispara el corto a medio camino
    según el orden de pulsación. Ver spec 2026-09-18-polish-bubble-design.
    """
    return a <= b or b <= a
```

- [ ] **Step 5: Instalar pytest y correr los tests**

```bash
cd /home/odoo/ideo-vozdoo
source .venv/bin/activate  # crear con python3 -m venv .venv si no existe
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/test_hotkey.py -v
```

Expected: 6 tests PASS (los 4 de `parse_hotkey` confirman comportamiento ya existente; los 2 de `hotkeys_overlap` son del código nuevo del Step 4).

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt tests/__init__.py tests/test_hotkey.py vozdoo_core.py
git commit -m "test: infraestructura pytest + hotkeys_overlap"
```

---

### Task 2: Extraer `paste_text` a `clipboard_paste.py`

**Files:**
- Create: `clipboard_paste.py`
- Create: `tests/test_clipboard_paste.py`
- Modify: `vozdoo_core.py:paste_text` (eliminar la función, importarla)

**Interfaces:**
- Produces: `paste_text(text: str, auto_paste: bool) -> None` (mismo comportamiento que hoy, movido de sitio)
- Consumes (en `vozdoo_core.py`): `from clipboard_paste import paste_text`

- [ ] **Step 1: Escribir el test (falla porque el módulo no existe todavía)**

`tests/test_clipboard_paste.py`:
```python
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clipboard_paste import paste_text


@patch("clipboard_paste.pkb.Controller")
@patch("clipboard_paste.pyperclip")
def test_paste_text_copies_and_pastes(mock_pyperclip, mock_controller_cls):
    mock_pyperclip.paste.return_value = "portapapeles anterior"
    controller = MagicMock()
    mock_controller_cls.return_value = controller

    paste_text("hola mundo", auto_paste=True)

    mock_pyperclip.copy.assert_called_once_with("hola mundo")
    controller.press.assert_called_once_with("v")
    controller.release.assert_called_once_with("v")


@patch("clipboard_paste.pkb.Controller")
@patch("clipboard_paste.pyperclip")
def test_paste_text_no_auto_paste_only_copies(mock_pyperclip, mock_controller_cls):
    mock_pyperclip.paste.return_value = ""

    paste_text("solo copiar", auto_paste=False)

    mock_pyperclip.copy.assert_called_once_with("solo copiar")
    mock_controller_cls.assert_not_called()


@patch("clipboard_paste.pkb.Controller")
@patch("clipboard_paste.pyperclip")
def test_paste_text_restores_previous_clipboard(mock_pyperclip, mock_controller_cls):
    mock_pyperclip.paste.return_value = "lo que hubiera antes"
    mock_controller_cls.return_value = MagicMock()

    paste_text("nuevo texto", auto_paste=True)
    time.sleep(0.7)  # el restore corre en un hilo con time.sleep(0.5)

    assert mock_pyperclip.copy.call_args_list[-1].args == ("lo que hubiera antes",)
```

- [ ] **Step 2: Correr el test, comprobar que falla**

```bash
pytest tests/test_clipboard_paste.py -v
```

Expected: FAIL con `ModuleNotFoundError: No module named 'clipboard_paste'`

- [ ] **Step 3: Crear `clipboard_paste.py` moviendo el código de `vozdoo_core.py`**

```python
"""Copiar al portapapeles y simular Ctrl+V (Cmd+V en Mac) sin perder lo
que el usuario tuviera copiado antes."""

from __future__ import annotations

import logging
import sys
import threading
import time

import pyperclip
from pynput import keyboard as pkb

log = logging.getLogger("vozdoo")


def paste_text(text: str, auto_paste: bool) -> None:
    previous = None
    try:
        previous = pyperclip.paste()
    except Exception:
        pass

    try:
        pyperclip.copy(text)
    except Exception as exc:
        log.warning("No se pudo copiar al portapapeles (%s). Texto: %s", exc, text)
        return

    if not auto_paste:
        return

    controller = pkb.Controller()
    modifier = pkb.Key.cmd if sys.platform == "darwin" else pkb.Key.ctrl
    try:
        with controller.pressed(modifier):
            controller.press("v")
            controller.release("v")
    except Exception as exc:
        log.warning("No se pudo simular Ctrl+V (%s). El texto sigue en el portapapeles.", exc)
        return

    if previous is not None:
        def restore():
            time.sleep(0.5)
            try:
                pyperclip.copy(previous)
            except Exception:
                pass

        threading.Thread(target=restore, daemon=True).start()
```

- [ ] **Step 4: Quitar `paste_text` de `vozdoo_core.py` e importarla**

En `vozdoo_core.py`: eliminar la función `paste_text` completa (y los imports `pyperclip`, `threading`, `time` si ya no se usan en otro sitio — `time` sigue haciendo falta para `time.time()` en el resto del fichero, no lo quites; `pyperclip` y `threading` sí se pueden quitar de los imports si `paste_text` era su único uso — comprueba con `grep -n "pyperclip\|threading" vozdoo_core.py` antes de quitarlos).

Añadir cerca del resto de imports:
```python
from clipboard_paste import paste_text
```

- [ ] **Step 5: Correr los tests, comprobar que pasan**

```bash
pytest tests/test_clipboard_paste.py -v
python3 -m py_compile vozdoo_core.py
```

Expected: 3 tests PASS, compilación sin errores.

- [ ] **Step 6: Verificación manual de regresión (no automatizable sin micrófono/hotkeys reales)**

Arrancar `./start-vozdoo.sh`, mantener `Ctrl+Win`, hablar, soltar. Confirmar que el texto se sigue pegando igual que antes de este cambio.

- [ ] **Step 7: Commit**

```bash
git add clipboard_paste.py tests/test_clipboard_paste.py vozdoo_core.py
git commit -m "refactor: extraer paste_text a clipboard_paste.py"
```

---

### Task 3: `llm_engine.py` — motores Ollama y API key

**Files:**
- Create: `llm_engine.py`
- Create: `tests/test_llm_engine.py`
- Modify: `requirements.txt` (+ `requests`)

**Interfaces:**
- Produces: `build_prompt(text: str, instruction: str) -> str`
- Produces: `class LLMEngine` con métodos `polish(text: str, instruction: str) -> str` y `is_available() -> bool`
- Produces: `class OllamaEngine(LLMEngine)`, `class ApiKeyEngine(LLMEngine)`
- Produces: `get_engine(env: dict[str, str]) -> LLMEngine`
- Consumes: nada de otros módulos nuevos (solo `requests`, `ollama_setup.is_ollama_running` para `OllamaEngine.is_available()` — ver Task 4, se importa ahí)

- [ ] **Step 1: Añadir `requests` a `requirements.txt`**

```
sounddevice>=0.5.0
numpy>=2.0
faster-whisper>=1.1.0
pynput>=1.8.0
pyperclip>=1.9.0
requests>=2.32.0
```

- [ ] **Step 2: Escribir los tests (fallan porque el módulo no existe)**

`tests/test_llm_engine.py`:
```python
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_engine import ApiKeyEngine, OllamaEngine, build_prompt, get_engine


def test_build_prompt_contains_instruction_and_text():
    prompt = build_prompt("hola mundo", "hazlo formal")
    assert "hola mundo" in prompt
    assert "hazlo formal" in prompt


def test_get_engine_returns_api_key_engine_when_key_set():
    env = {
        "VOZDOO_LLM_API_KEY": "sk-test",
        "VOZDOO_LLM_API_URL": "https://api.openai.com/v1/chat/completions",
        "VOZDOO_LLM_API_MODEL": "gpt-4o-mini",
    }
    engine = get_engine(env)
    assert isinstance(engine, ApiKeyEngine)


def test_get_engine_returns_ollama_engine_when_no_key():
    env = {
        "VOZDOO_LLM_API_KEY": "",
        "VOZDOO_LLM_HOST": "http://localhost:11434",
        "VOZDOO_LLM_MODEL": "qwen2.5:3b-instruct",
    }
    engine = get_engine(env)
    assert isinstance(engine, OllamaEngine)


@patch("llm_engine.requests.post")
def test_ollama_engine_polish_calls_generate_endpoint(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200, json=lambda: {"response": "  texto pulido  "}
    )
    mock_post.return_value.raise_for_status = MagicMock()

    engine = OllamaEngine(host="http://localhost:11434", model="qwen2.5:3b-instruct")
    result = engine.polish("hola", "hazlo formal")

    assert result == "texto pulido"
    called_url = mock_post.call_args.args[0]
    assert called_url == "http://localhost:11434/api/generate"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "qwen2.5:3b-instruct"
    assert payload["stream"] is False


@patch("llm_engine.requests.post")
def test_api_key_engine_polish_calls_chat_completions(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": "  texto pulido  "}}]},
    )
    mock_post.return_value.raise_for_status = MagicMock()

    engine = ApiKeyEngine(
        api_url="https://api.openai.com/v1/chat/completions",
        api_key="sk-test",
        model="gpt-4o-mini",
    )
    result = engine.polish("hola", "hazlo formal")

    assert result == "texto pulido"
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer sk-test"
    payload = mock_post.call_args.kwargs["json"]
    assert payload["model"] == "gpt-4o-mini"
    assert payload["messages"][0]["role"] == "user"


def test_api_key_engine_is_available_is_always_true():
    engine = ApiKeyEngine(api_url="x", api_key="sk-test", model="m")
    assert engine.is_available() is True
```

- [ ] **Step 3: Correr los tests, comprobar que fallan**

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/test_llm_engine.py -v
```

Expected: FAIL con `ModuleNotFoundError: No module named 'llm_engine'`

- [ ] **Step 4: Crear `llm_engine.py`**

```python
"""Motores de IA para pulir texto: Ollama local o una API key personal
(formato chat completions compatible con OpenAI, sirve también para
Gemini vía su capa de compatibilidad)."""

from __future__ import annotations

import requests


def build_prompt(text: str, instruction: str) -> str:
    return (
        "Eres un asistente de escritura. Se te da un texto dictado por voz "
        "y una instrucción sobre cómo reescribirlo.\n\n"
        f"Instrucción: {instruction}\n\n"
        f"Texto original:\n{text}\n\n"
        "Devuelve SOLO el texto reescrito, sin explicaciones ni comillas."
    )


class LLMEngine:
    def polish(self, text: str, instruction: str) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError


class OllamaEngine(LLMEngine):
    def __init__(self, host: str, model: str):
        self.host = host.rstrip("/")
        self.model = model

    def polish(self, text: str, instruction: str) -> str:
        prompt = build_prompt(text, instruction)
        resp = requests.post(
            f"{self.host}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    def is_available(self) -> bool:
        from ollama_setup import is_ollama_running

        return is_ollama_running(self.host)


class ApiKeyEngine(LLMEngine):
    def __init__(self, api_url: str, api_key: str, model: str):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    def polish(self, text: str, instruction: str) -> str:
        prompt = build_prompt(text, instruction)
        resp = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def is_available(self) -> bool:
        return True


def get_engine(env: dict[str, str]) -> LLMEngine:
    api_key = env.get("VOZDOO_LLM_API_KEY", "").strip()
    if api_key:
        return ApiKeyEngine(
            api_url=env.get(
                "VOZDOO_LLM_API_URL", "https://api.openai.com/v1/chat/completions"
            ),
            api_key=api_key,
            model=env.get("VOZDOO_LLM_API_MODEL", "gpt-4o-mini"),
        )
    return OllamaEngine(
        host=env.get("VOZDOO_LLM_HOST", "http://localhost:11434"),
        model=env.get("VOZDOO_LLM_MODEL", "qwen2.5:3b-instruct"),
    )
```

Nota: `OllamaEngine.is_available()` importa `ollama_setup` dentro del método (no arriba del fichero) para evitar un import circular, porque `ollama_setup.py` no necesita importar nada de `llm_engine.py` — es una dependencia en un solo sentido y así no hace falta reordenar los ficheros.

- [ ] **Step 5: Correr los tests, comprobar que pasan (menos el que depende de `ollama_setup`, que llega en la siguiente tarea)**

```bash
pytest tests/test_llm_engine.py -v
```

Expected: PASS todos excepto ninguno debería fallar por `ollama_setup` porque `is_available()` de `OllamaEngine` no está cubierto por ningún test todavía (se cubre en Task 4). El resto: 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add llm_engine.py tests/test_llm_engine.py requirements.txt
git commit -m "feat: motores de IA (Ollama + API key personal)"
```

---

### Task 4: `ollama_setup.py` — detección, instalación con un clic, descarga de modelo

**Files:**
- Create: `ollama_setup.py`
- Create: `tests/test_ollama_setup.py`

**Interfaces:**
- Produces: `is_ollama_running(host: str) -> bool`
- Produces: `linux_mac_install_command() -> str`
- Produces: `run_install_linux_mac() -> subprocess.Popen`
- Produces: `download_windows_installer(dest_path: str) -> str`
- Produces: `launch_windows_installer(path: str) -> None`
- Produces: `pull_model(host: str, model: str, on_progress: Callable[[str], None]) -> None`
- Consumes: `requests` (ya en requirements.txt desde Task 3)

- [ ] **Step 1: Escribir los tests**

`tests/test_ollama_setup.py`:
```python
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ollama_setup import is_ollama_running, linux_mac_install_command, pull_model


@patch("ollama_setup.requests.get")
def test_is_ollama_running_true_on_200(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    assert is_ollama_running("http://localhost:11434") is True


@patch("ollama_setup.requests.get")
def test_is_ollama_running_false_on_connection_error(mock_get):
    mock_get.side_effect = Exception("connection refused")
    assert is_ollama_running("http://localhost:11434") is False


def test_linux_mac_install_command_uses_official_script():
    cmd = linux_mac_install_command()
    assert "curl" in cmd
    assert "ollama.com/install.sh" in cmd
    assert "sh" in cmd


@patch("ollama_setup.requests.post")
def test_pull_model_reports_progress(mock_post):
    fake_lines = [
        b'{"status": "downloading", "completed": 10, "total": 100}',
        b'{"status": "success"}',
    ]
    mock_response = MagicMock()
    mock_response.iter_lines.return_value = fake_lines
    mock_response.__enter__ = lambda self: mock_response
    mock_response.__exit__ = lambda self, *a: None
    mock_post.return_value = mock_response

    seen = []
    pull_model("http://localhost:11434", "qwen2.5:3b-instruct", on_progress=seen.append)

    assert len(seen) == 2
    assert "downloading" in seen[0] or "success" in seen[-1]
```

- [ ] **Step 2: Correr los tests, comprobar que fallan**

```bash
pytest tests/test_ollama_setup.py -v
```

Expected: FAIL con `ModuleNotFoundError: No module named 'ollama_setup'`

- [ ] **Step 3: Crear `ollama_setup.py`**

```python
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
```

- [ ] **Step 4: Correr los tests, comprobar que pasan**

```bash
pytest tests/test_ollama_setup.py tests/test_llm_engine.py -v
```

Expected: todos PASS (ahora `OllamaEngine.is_available()` de Task 3 también queda cubierto indirectamente al existir el módulo, aunque no tiene test propio explícito — añadir uno):

Añadir a `tests/test_llm_engine.py`:
```python
@patch("llm_engine.is_ollama_running", create=True)
def test_ollama_engine_is_available_delegates_to_ollama_setup(_):
    with patch("ollama_setup.is_ollama_running", return_value=True) as mock_check:
        engine = OllamaEngine(host="http://localhost:11434", model="m")
        assert engine.is_available() is True
        mock_check.assert_called_once_with("http://localhost:11434")
```

Correr de nuevo:
```bash
pytest tests/test_llm_engine.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ollama_setup.py tests/test_ollama_setup.py tests/test_llm_engine.py
git commit -m "feat: instalación de Ollama con un clic + descarga de modelo"
```

---

### Task 5: `polish_bubble.py` — ventana flotante

**Files:**
- Create: `polish_bubble.py`
- Create: `tests/test_polish_bubble.py`

**Interfaces:**
- Produces: `PRESET_INSTRUCTIONS: dict[str, str]`
- Produces: `class PolishBubble` con constructor
  `(root, original_text, engine, record_start_fn, record_stop_fn, paste_fn, auto_paste)`
  y método `show() -> None`
- Consumes: `llm_engine.LLMEngine` (de Task 3), `ollama_setup` (de Task 4, indirecto vía `engine.is_available()`; la instalación completa con progreso se conecta en la Task 6)

- [ ] **Step 1: Escribir el test de los presets (única parte testable sin pantalla)**

`tests/test_polish_bubble.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from polish_bubble import PRESET_INSTRUCTIONS

EXPECTED_PRESETS = {"Más formal", "Mejorar prompt", "Corregir", "Resumir"}


def test_preset_instructions_has_expected_keys():
    assert set(PRESET_INSTRUCTIONS.keys()) == EXPECTED_PRESETS


def test_preset_instructions_are_non_empty_strings():
    for instruction in PRESET_INSTRUCTIONS.values():
        assert isinstance(instruction, str)
        assert len(instruction) > 10
```

- [ ] **Step 2: Correr el test, comprobar que falla**

```bash
pytest tests/test_polish_bubble.py -v
```

Expected: FAIL con `ModuleNotFoundError: No module named 'polish_bubble'`

- [ ] **Step 3: Crear `polish_bubble.py`**

```python
"""Burbuja flotante (tkinter) para elegir una acción de IA sobre el
texto dictado, revisar el resultado y pegarlo."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

from llm_engine import LLMEngine

log = logging.getLogger("vozdoo")

PRESET_INSTRUCTIONS: dict[str, str] = {
    "Más formal": (
        "Reescribe el texto en un tono más formal y profesional, "
        "en español de España."
    ),
    "Mejorar prompt": (
        "Reescribe el texto como un prompt claro y bien estructurado "
        "para un asistente de IA."
    ),
    "Corregir": (
        "Corrige la gramática y ortografía del texto sin cambiar "
        "el significado ni el tono."
    ),
    "Resumir": "Resume el texto en 1-2 frases manteniendo la idea principal.",
}


class PolishBubble:
    def __init__(
        self,
        root: tk.Tk,
        original_text: str,
        engine: LLMEngine,
        record_start_fn: Callable[[], None],
        record_stop_fn: Callable[[], str],
        paste_fn: Callable[[str, bool], None],
        auto_paste: bool,
    ):
        self.root = root
        self.original_text = original_text
        self.engine = engine
        self.record_start_fn = record_start_fn
        self.record_stop_fn = record_stop_fn
        self.paste_fn = paste_fn
        self.auto_paste = auto_paste
        self.window: tk.Toplevel | None = None

    def show(self) -> None:
        self.window = tk.Toplevel(self.root)
        self.window.title("Vozdoo — pulir")
        self.window.attributes("-topmost", True)
        self._render_choose_action()

    def _clear(self) -> None:
        for widget in self.window.winfo_children():
            widget.destroy()

    def _render_choose_action(self) -> None:
        self._clear()
        tk.Label(self.window, text=self.original_text, wraplength=360, justify="left").pack(
            padx=10, pady=(10, 6)
        )

        if not self.engine.is_available():
            self._render_install_ollama()
            return

        for label, instruction in PRESET_INSTRUCTIONS.items():
            tk.Button(
                self.window,
                text=label,
                command=lambda i=instruction: self._run_polish(i),
            ).pack(fill="x", padx=10, pady=2)

        custom_btn = tk.Button(self.window, text="🎤 Instrucción personalizada")
        custom_btn.pack(fill="x", padx=10, pady=(6, 10))
        custom_btn.bind("<ButtonPress-1>", lambda e: self.record_start_fn())
        custom_btn.bind("<ButtonRelease-1>", lambda e: self._on_custom_instruction())

    def _on_custom_instruction(self) -> None:
        instruction = self.record_stop_fn()
        if not instruction:
            return
        self._run_polish(instruction)

    def _render_install_ollama(self) -> None:
        tk.Label(
            self.window,
            text=(
                "Ollama no está instalado o no responde, y no hay una "
                "API key configurada."
            ),
            wraplength=360,
            justify="left",
        ).pack(padx=10, pady=6)
        tk.Button(
            self.window,
            text="Instalar Ollama automáticamente",
            command=self._start_ollama_install,
        ).pack(fill="x", padx=10, pady=(0, 10))

    def _run_polish(self, instruction: str) -> None:
        self._clear()
        tk.Label(self.window, text="Pensando...").pack(padx=10, pady=20)
        self.window.update()
        try:
            result = self.engine.polish(self.original_text, instruction)
        except Exception as exc:
            log.exception("Error llamando al motor de IA")
            self._render_error(str(exc))
            return
        self._render_result(result)

    def _render_error(self, message: str) -> None:
        self._clear()
        tk.Label(
            self.window,
            text=f"Error: {message}",
            wraplength=360,
            justify="left",
            fg="red",
        ).pack(padx=10, pady=10)
        tk.Button(self.window, text="Cerrar", command=self.window.destroy).pack(
            fill="x", padx=10, pady=(0, 10)
        )

    def _render_result(self, result_text: str) -> None:
        self._clear()
        text_widget = scrolledtext.ScrolledText(self.window, width=44, height=8, wrap="word")
        text_widget.insert("1.0", result_text)
        text_widget.configure(state="disabled")
        text_widget.pack(padx=10, pady=10)

        button_row = tk.Frame(self.window)
        button_row.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(
            button_row,
            text="Pegar",
            command=lambda: self._paste_and_close(result_text),
        ).pack(side="left", expand=True, fill="x")
        tk.Button(
            button_row, text="Reintentar", command=self._render_choose_action
        ).pack(side="left", expand=True, fill="x")
        tk.Button(button_row, text="Descartar", command=self.window.destroy).pack(
            side="left", expand=True, fill="x"
        )

    def _paste_and_close(self, text: str) -> None:
        self.paste_fn(text, self.auto_paste)
        self.window.destroy()
```

Nota: el botón "Instalar Ollama automáticamente" llama a
`self._start_ollama_install`, que todavía no existe — se añade completo
en la Task 6. Hasta entonces el archivo importa y los tests de esta
tarea pasan igual (nadie lo invoca en los tests), pero si alguien pulsa
ese botón antes de la Task 6 dará `AttributeError`. Es intencional: el
resto de la burbuja (presets, instrucción personalizada, resultado) ya
queda completo y probado en esta tarea.

- [ ] **Step 4: Correr los tests, comprobar que pasan**

```bash
pytest tests/test_polish_bubble.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Verificación manual (requiere sesión gráfica, no automatizable aquí)**

No hay forma de probar `tkinter` end-to-end sin una pantalla real y sin estar aún conectado al hotkey (eso llega en la Task 7). Queda pendiente de verificación manual conjunta en la Task 7, Step 7.

- [ ] **Step 6: Commit**

```bash
git add polish_bubble.py tests/test_polish_bubble.py
git commit -m "feat: burbuja de pulido con tkinter"
```

---

### Task 6: Instalación de Ollama con progreso, integrada en la burbuja

**Files:**
- Modify: `polish_bubble.py` (añadir `_start_ollama_install` y helpers de estado)

**Interfaces:**
- Consumes: `ollama_setup.run_install_linux_mac`, `ollama_setup.is_ollama_running`,
  `ollama_setup.pull_model`, `ollama_setup.download_windows_installer`,
  `ollama_setup.launch_windows_installer` (todas de Task 4)
- Produces: `PolishBubble._start_ollama_install()` (llamado desde el botón
  añadido en Task 5)

No lleva tests automáticos nuevos: es un flujo en segundo plano que
lanza un subproceso e instala software real, no tiene sentido mockear
cada paso por separado sin perder valor — se verifica a mano en el
Step 3. Los tests ya existentes de `ollama_setup.py` (Task 4) cubren la
lógica que este código invoca.

- [ ] **Step 1: Añadir imports a `polish_bubble.py`**

Al principio del archivo, junto a los imports existentes:
```python
import sys
import threading
import time

import ollama_setup
```

- [ ] **Step 2: Añadir los métodos de instalación a la clase `PolishBubble`**

Añadir estos métodos (por ejemplo, justo antes de `_paste_and_close`):

```python
    def _start_ollama_install(self) -> None:
        self._clear()
        self.status_label = tk.Label(
            self.window, text="Instalando Ollama...", wraplength=360, justify="left"
        )
        self.status_label.pack(padx=10, pady=20)
        threading.Thread(target=self._run_ollama_install, daemon=True).start()

    def _set_status(self, text: str) -> None:
        self.window.after(0, lambda: self.status_label.configure(text=text))

    def _finish_install_with_retry(self, text: str) -> None:
        def render():
            self.status_label.configure(text=text)
            tk.Button(
                self.window, text="Reintentar", command=self._render_choose_action
            ).pack(fill="x", padx=10, pady=(6, 10))

        self.window.after(0, render)

    def _run_ollama_install(self) -> None:
        host = self.engine.host
        model = self.engine.model
        try:
            if sys.platform == "win32":
                import os
                import tempfile

                dest = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
                self._set_status("Descargando instalador de Ollama...")
                ollama_setup.download_windows_installer(dest)
                self._set_status(
                    "Abriendo el instalador de Ollama — sigue el asistente y "
                    "cuando termine, vuelve aquí y pulsa Reintentar."
                )
                ollama_setup.launch_windows_installer(dest)
                self._finish_install_with_retry(
                    "Instalador abierto. Cuando termines, pulsa Reintentar."
                )
                return

            self._set_status(
                "Abriendo una terminal para instalar Ollama "
                "(puede pedirte tu contraseña)..."
            )
            proc = ollama_setup.run_install_linux_mac()
            proc.wait()

            self._set_status("Comprobando que Ollama arrancó...")
            for _ in range(30):
                if ollama_setup.is_ollama_running(host):
                    break
                time.sleep(1)
            else:
                self._finish_install_with_retry(
                    "Ollama no respondió tras instalar. Pulsa Reintentar."
                )
                return

            self._set_status(f"Descargando modelo {model} (puede tardar unos minutos)...")
            ollama_setup.pull_model(host, model, on_progress=self._set_status)
            self._finish_install_with_retry("Listo. Pulsa Reintentar para usarlo.")
        except Exception as exc:
            log.exception("Error instalando Ollama")
            self._finish_install_with_retry(f"Error instalando Ollama: {exc}")
```

- [ ] **Step 3: Verificación manual (requiere máquina real sin Ollama instalado)**

No se puede automatizar sin una máquina limpia de verdad. En un
ordenador de prueba sin Ollama instalado y sin `VOZDOO_LLM_API_KEY`:

1. Disparar el hotkey de pulir → confirmar que aparece el aviso y el
   botón "Instalar Ollama automáticamente".
2. Pulsar el botón → en Linux/Mac, confirmar que se abre una terminal
   nueva ejecutando el instalador oficial. En Windows, confirmar que se
   descarga y lanza `OllamaSetup.exe`.
3. Tras completar la instalación (a mano si hace falta, `ollama pull
   qwen2.5:3b-instruct` desde una terminal si el flujo automático no
   llega a esa parte), confirmar que la burbuja acaba mostrando "Listo.
   Pulsa Reintentar para usarlo." y que Reintentar lleva a los botones
   de acción normales.

- [ ] **Step 4: Comprobar que compila y que el resto de tests siguen en verde**

```bash
python3 -m py_compile polish_bubble.py
pytest tests/ -v
```

Expected: sin errores de sintaxis, todos los tests existentes en PASS
(este cambio no toca nada que tuviera tests).

- [ ] **Step 5: Commit**

```bash
git add polish_bubble.py
git commit -m "feat: instalar Ollama con progreso desde la burbuja"
```

---

### Task 7: Conectar el segundo hotkey en `vozdoo_core.py`

**Files:**
- Modify: `vozdoo_core.py` (constructor, `run()`, sustituir el `on_press`/`on_release` de un solo hotkey por soporte multi-hotkey)

**Interfaces:**
- Consumes: `paste_text` (Task 2), `get_engine` (Task 3), `PolishBubble` (Task 5), `hotkeys_overlap` (Task 1)
- Produces: nada nuevo exportable — es el punto de entrada

- [ ] **Step 1: Añadir imports y nuevas variables de entorno en `load_env()`**

En la cabecera de `vozdoo_core.py`, junto a los imports existentes:
```python
import signal
import tkinter as tk

from llm_engine import get_engine
from polish_bubble import PolishBubble
```

En el diccionario de defaults de `load_env()`, añadir estas claves (junto a las que ya existen `VOZDOO_HOTKEY`, `VOZDOO_WHISPER_MODEL`, etc.):
```python
        "VOZDOO_POLISH_HOTKEY": "alt+win",
        "VOZDOO_LLM_API_KEY": "",
        "VOZDOO_LLM_API_URL": "https://api.openai.com/v1/chat/completions",
        "VOZDOO_LLM_API_MODEL": "gpt-4o-mini",
        "VOZDOO_LLM_MODEL": "qwen2.5:3b-instruct",
        "VOZDOO_LLM_HOST": "http://localhost:11434",
```

- [ ] **Step 2: Sustituir el hotkey único por dos hotkeys con validación de solape, en `Vozdoo.__init__`**

Reemplaza el bloque:
```python
        parsed = parse_hotkey(env["VOZDOO_HOTKEY"])
        if parsed is None:
            raise SystemExit(1)
        self.hotkey_tokens = parsed
        self._pressed_tokens: set = set()
```

por:
```python
        normal_hotkey = parse_hotkey(env["VOZDOO_HOTKEY"])
        polish_hotkey = parse_hotkey(env["VOZDOO_POLISH_HOTKEY"])
        if normal_hotkey is None or polish_hotkey is None:
            raise SystemExit(1)
        if hotkeys_overlap(normal_hotkey, polish_hotkey):
            log.error(
                "VOZDOO_HOTKEY (%s) y VOZDOO_POLISH_HOTKEY (%s) se solapan: "
                "uno no puede contener todas las teclas del otro.",
                env["VOZDOO_HOTKEY"],
                env["VOZDOO_POLISH_HOTKEY"],
            )
            raise SystemExit(1)
        self.hotkeys = {"normal": normal_hotkey, "polish": polish_hotkey}
        self._pressed_tokens: set = set()
        self._active_mode: str | None = None
        self.engine_env = env
        self.tk_root: tk.Tk | None = None
```

- [ ] **Step 3: Sustituir `on_press`/`on_release` (métodos de instancia) por `_start_recording`/`_finish_recording` con modo**

Reemplaza los métodos `on_press` y `on_release` existentes de la clase por:
```python
    def _start_recording(self, mode: str) -> None:
        with self.lock:
            if self.buffer.recording or self.processing:
                return
            self._active_mode = mode
            log.info("Grabando (%s)... (suelta para transcribir)", mode)
            beep(800, 80)
            self.buffer.start()

    def _finish_recording(self) -> None:
        with self.lock:
            if not self.buffer.recording:
                return
            audio = self.buffer.stop()
            self.processing = True
            mode = self._active_mode
            self._active_mode = None

        beep(600, 80)
        log.info("Audio capturado (%.2fs)", len(audio) / self.sample_rate)

        try:
            t0 = time.time()
            text = transcribe(self.whisper, audio, self.language)
            log.info("STT (%.2fs): %s", time.time() - t0, text)

            if not text:
                log.info("Audio vacío o sin voz, nada que hacer")
                return

            if mode == "normal":
                paste_text(text, self.auto_paste)
                log.info("Pegado en la ventana activa" if self.auto_paste else "Copiado al portapapeles")
            else:
                self.tk_root.after(0, lambda: self._open_polish_bubble(text))
        except Exception:
            log.exception("Error transcribiendo/procesando")
        finally:
            self.processing = False

    def start_custom_recording(self) -> None:
        """Llamado desde la burbuja al mantener pulsado el botón del micro."""
        with self.lock:
            if self.buffer.recording or self.processing:
                return
            beep(800, 80)
            self.buffer.start()

    def stop_custom_recording(self) -> str:
        """Llamado desde la burbuja al soltar el botón del micro."""
        with self.lock:
            if not self.buffer.recording:
                return ""
            audio = self.buffer.stop()
        beep(600, 80)
        return transcribe(self.whisper, audio, self.language)

    def _open_polish_bubble(self, text: str) -> None:
        """Nota de alcance: si `transcribe()` lanza una excepción (no si
        solo devuelve vacío, ese caso ya está cubierto arriba), el error
        se registra en el log pero la burbuja no llega a abrirse — el
        spec pedía que fuera visible en la burbuja, pero eso exigiría
        abrirla ANTES de transcribir; se deja así por ahora porque es un
        caso raro (fallo real de Whisper, no "no se dijo nada")."""
        engine = get_engine(self.engine_env)
        bubble = PolishBubble(
            root=self.tk_root,
            original_text=text,
            engine=engine,
            record_start_fn=self.start_custom_recording,
            record_stop_fn=self.stop_custom_recording,
            paste_fn=paste_text,
            auto_paste=self.auto_paste,
        )
        bubble.show()
```

Nota: la instalación de Ollama (botón dentro de la burbuja cuando
`engine.is_available()` es `False`) vive entera en `polish_bubble.py`
desde la Task 6 — `vozdoo_core.py` no necesita saber nada de Ollama.

- [ ] **Step 4: Reescribir `run()` para usar Tkinter en el hilo principal y el listener en segundo plano**

Reemplaza el método `run()` completo por:
```python
    def run(self) -> None:
        self.tk_root = tk.Tk()
        self.tk_root.withdraw()
        signal.signal(signal.SIGINT, lambda *_: self.tk_root.quit())

        def normalize(key):
            for name, variants in _MODIFIER_KEYS.items():
                if key in variants:
                    return name
            return key

        def on_press(key):
            token = normalize(key)
            self._pressed_tokens.add(token)
            if self._active_mode is not None:
                return
            if self.hotkeys["polish"] <= self._pressed_tokens:
                self._start_recording("polish")
            elif self.hotkeys["normal"] <= self._pressed_tokens:
                self._start_recording("normal")

        def on_release(key):
            token = normalize(key)
            active = self._active_mode
            was_active = active is not None and token in self.hotkeys[active]
            self._pressed_tokens.discard(token)
            if was_active:
                self._finish_recording()

        listener = pkb.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        log.info(
            "Vozdoo listo. '%s' dicta y pega. '%s' dicta y pulir con IA. Ctrl+C para salir.",
            self.env["VOZDOO_HOTKEY"],
            self.env["VOZDOO_POLISH_HOTKEY"],
        )

        try:
            self.tk_root.mainloop()
        finally:
            listener.stop()
            log.info("Saliendo...")
```

- [ ] **Step 5: Comprobar que compila**

```bash
python3 -m py_compile vozdoo_core.py
```

Expected: sin errores.

- [ ] **Step 6: Correr toda la suite de tests**

```bash
pytest tests/ -v
```

Expected: todos los tests de Tasks 1-5 siguen en PASS (este refactor no debería romper ninguno, porque `parse_hotkey`, `hotkeys_overlap`, `paste_text`, `llm_engine` y `polish_bubble` no cambian en esta tarea).

- [ ] **Step 7: Verificación manual completa (requiere máquina con micrófono, pantalla y, opcionalmente, Ollama instalado)**

En un ordenador real (no en este entorno, que no tiene audio ni pantalla):

1. `./start-vozdoo.sh` — confirmar que arranca sin errores y muestra el mensaje con los dos hotkeys.
2. Mantener `Ctrl+Win`, hablar, soltar → confirmar que **sigue pegando el texto tal cual, igual que antes** (regresión del hotkey normal).
3. Mantener `Alt+Win`, hablar, soltar → confirmar que se abre la burbuja con el texto transcrito y los 4 botones.
4. Sin Ollama instalado y sin API key en `.env` → confirmar que la burbuja muestra el aviso de instalar Ollama en vez de los botones de acción.
5. Con Ollama instalado y el modelo descargado (`ollama pull qwen2.5:3b-instruct`) → pulsar "Más formal" → confirmar que aparece "Pensando..." y luego el resultado con Pegar/Reintentar/Descartar.
6. Pulsar "Pegar" → confirmar que el texto pulido se pega en la ventana activa.
7. Pulsar `Ctrl+C` en la terminal → confirmar que el proceso termina (verifica el fix del `signal.signal` para que Tkinter no bloquee la interrupción).

- [ ] **Step 8: Commit**

```bash
git add vozdoo_core.py
git commit -m "feat: segundo hotkey dictar+pulir con burbuja de IA"
```

---

### Task 8: Documentación — `.env.example` y `README.md`

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Añadir las variables nuevas a `.env.example`**

Añadir al final del archivo:
```bash

# --- Dictar + pulir con IA (opcional) ---

# Tecla o combo para "dictar y pulir" (abre una burbuja con opciones de IA
# antes de pegar). No puede compartir todas las teclas de DICTADO_HOTKEY.
VOZDOO_POLISH_HOTKEY=alt+win

# Si rellenas esto, se usa tu propia API en vez de Ollama local.
# Gemini: crea una clave gratis en https://aistudio.google.com/apikey y
# pon VOZDOO_LLM_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
VOZDOO_LLM_API_KEY=
VOZDOO_LLM_API_URL=https://api.openai.com/v1/chat/completions
VOZDOO_LLM_API_MODEL=gpt-4o-mini

# Si no hay API key, se usa Ollama local con este modelo:
VOZDOO_LLM_MODEL=qwen2.5:3b-instruct
VOZDOO_LLM_HOST=http://localhost:11434
```

- [ ] **Step 2: Añadir `python3-tk` a los requisitos de Linux en `README.md`**

Buscar la línea:
```bash
sudo apt install python3 python3-venv python3-pip git libportaudio2
```
y sustituirla por:
```bash
sudo apt install python3 python3-venv python3-pip python3-tk git libportaudio2
```
(hay dos apariciones: en la Guía rápida y en la sección 1 de requisitos — cambiar ambas).

- [ ] **Step 3: Añadir una sección "Dictar + pulir con IA" al README, después de la sección de uso normal**

```markdown
## Dictar + pulir con IA (opcional)

Además del dictado normal (`Ctrl + Win`), hay un segundo hotkey,
**Alt + Win** por defecto, que abre una burbuja para reescribir el texto
con IA antes de pegarlo: más formal, mejorar un prompt, corregir, resumir,
o una instrucción tuya dicha por voz.

Por defecto usa un modelo de IA local (Ollama) — si no lo tienes
instalado, la burbuja te ofrece instalarlo con un clic. Si prefieres usar
tu propia clave de API (OpenAI o Gemini), configúrala en `.env`
(`VOZDOO_LLM_API_KEY`) y se usará esa en su lugar, sin necesidad de
Ollama.

Este hotkey es totalmente opcional: si no lo usas nunca, no afecta en
nada al dictado normal.
```

- [ ] **Step 4: Verificar que no hay referencias internas**

```bash
grep -rni -E "jarboo|elevenlabs|anthropic|marc herrero|boomatik" . --include="*.py" --include="*.md" --include="*.example" --include="*.ps1" --include="*.sh"
```

Expected: sin resultados.

- [ ] **Step 5: Commit**

```bash
git add .env.example README.md
git commit -m "docs: documentar dictar+pulir con IA"
git push
```

---

## Siguientes pasos no incluidos en v1 (documentar en el README como "mejoras futuras", no implementar ahora)

- Instalador de Windows: investigar flags silenciosos del instalador oficial de Ollama (hoy abre el asistente gráfico normal).
- Icono de bandeja del sistema / autoarranque (ya estaba en el README como mejora futura de v1).
