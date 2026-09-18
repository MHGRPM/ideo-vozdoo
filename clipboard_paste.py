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
