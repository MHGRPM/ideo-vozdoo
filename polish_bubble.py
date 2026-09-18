"""Burbuja flotante (tkinter) para elegir una acción de IA sobre el
texto dictado, revisar el resultado y pegarlo."""

from __future__ import annotations

import logging
import sys
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

import ollama_setup
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

    def _paste_and_close(self, text: str) -> None:
        self.paste_fn(text, self.auto_paste)
        self.window.destroy()
