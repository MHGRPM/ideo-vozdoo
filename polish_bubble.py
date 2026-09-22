"""Burbuja flotante (tkinter) para elegir una acción de IA sobre el
texto dictado, revisar el resultado y pegarlo.

El aspecto sigue la marca Odoo I+D+E Spain sobre fondo oscuro, con el
orbe de Vozdoo (`assets/vozdoo-orb-64.png`) como ancla visual."""

from __future__ import annotations

import logging
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import scrolledtext
from typing import Callable

import requests

import ollama_setup
from llm_engine import LLMEngine, OllamaEngine

log = logging.getLogger("vozdoo")

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Paleta de marca sobre fondo oscuro, la del orbe de Vozdoo.
BG = "#0B0710"            # casi negro con tinte púrpura, funde con el orbe
SURFACE = "#171022"       # tarjetas y campos de texto
TEXT = "#F4F1F7"          # texto principal
MUTED = "#A99FB8"         # texto secundario
PURPLE = "#875A7B"        # --ide-purple-light, botones de acción
PURPLE_ACTIVE = "#714B67" # --ide-purple, estado pulsado
TEAL = "#017E84"          # --ide-teal, acción principal y micrófono
TEAL_ACTIVE = "#016065"
CYAN = "#4DD9E6"          # neón del orbe, estados en curso
DANGER = "#FF6B6B"        # rojo legible sobre oscuro (el "red" de tk no lo es)

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


def pick_font(preferred: tuple[str, ...], fallback: str) -> str:
    """Primera familia instalada de `preferred`, o `fallback`.

    Los equipos del equipo PM no tienen por qué tener Inter ni Caveat,
    así que la burbuja se ve bien igual con la fuente del sistema.
    Requiere que exista ya una ventana raíz de Tk."""
    try:
        available = set(tkfont.families())
    except Exception:
        return fallback
    for family in preferred:
        if family in available:
            return family
    return fallback


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
        self._polish_cancelled = False
        self._orb: tk.PhotoImage | None = None
        self.font_body = "TkDefaultFont"
        self.font_title = "TkDefaultFont"

    # ------------------------------------------------------------------
    # Marca: fuentes, logo y fábricas de widgets ya estilados
    # ------------------------------------------------------------------

    def _load_brand(self) -> None:
        self.font_body = pick_font(("Inter", "Ubuntu", "Noto Sans"), "TkDefaultFont")
        self.font_title = pick_font(("Caveat",), self.font_body)
        try:
            self._orb = tk.PhotoImage(
                master=self.root, file=str(ASSETS_DIR / "vozdoo-orb-64.png")
            )
        except Exception:
            # Sin logo la burbuja sigue siendo perfectamente usable.
            log.debug("No se pudo cargar el orbe de Vozdoo", exc_info=True)
            self._orb = None

    def _label(self, parent, text: str, *, fg: str = TEXT, size: int = 10, **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", BG),
            fg=fg,
            font=(self.font_body, size),
            justify="left",
            **kwargs,
        )

    def _button(self, parent, text: str, command=None, *, kind: str = "purple"):
        colors = {
            "purple": (PURPLE, PURPLE_ACTIVE, TEXT),
            "teal": (TEAL, TEAL_ACTIVE, TEXT),
            "ghost": (SURFACE, PURPLE_ACTIVE, MUTED),
        }[kind]
        bg, active, fg = colors
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            activeforeground=TEXT,
            # En macOS tk ignora bg en los botones y mira highlightbackground.
            highlightbackground=bg,
            font=(self.font_body, 10),
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            cursor="hand2",
        )

    def _header(self) -> None:
        header = tk.Frame(self.window, bg=BG)
        header.pack(fill="x", padx=16, pady=(14, 10))
        if self._orb is not None:
            tk.Label(header, image=self._orb, bg=BG, bd=0).pack(side="left")
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", padx=(12, 0))
        tk.Label(
            titles,
            text="Vozdoo",
            bg=BG,
            fg=TEXT,
            font=(self.font_title, 22 if self.font_title == "Caveat" else 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            titles, text="pulir con IA", bg=BG, fg=MUTED, font=(self.font_body, 9)
        ).pack(anchor="w")

    def _quote(self, text: str) -> None:
        """El texto dictado, en una tarjeta con el púrpura de marca al canto."""
        card = tk.Frame(self.window, bg=PURPLE)
        card.pack(fill="x", padx=16, pady=(0, 12))
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=(3, 0))
        self._label(
            inner, text, bg=SURFACE, fg=TEXT, wraplength=330, padx=12, pady=10
        ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Pantallas
    # ------------------------------------------------------------------

    def show(self) -> None:
        self.window = tk.Toplevel(self.root)
        self.window.title("Vozdoo — pulir")
        self.window.configure(bg=BG)
        self._load_brand()
        x, y = self.root.winfo_pointerxy()
        self.window.geometry(f"+{x + 20}+{y + 20}")
        self.window.attributes("-topmost", True)
        self._render_choose_action()

    def _clear(self) -> None:
        for widget in self.window.winfo_children():
            widget.destroy()

    def _render_choose_action(self) -> None:
        self._clear()
        self._header()
        self._quote(self.original_text)

        if not self.engine.is_available():
            self._render_install_ollama()
            return

        grid = tk.Frame(self.window, bg=BG)
        grid.pack(fill="x", padx=16)
        grid.columnconfigure(0, weight=1, uniform="preset")
        grid.columnconfigure(1, weight=1, uniform="preset")
        for index, (label, instruction) in enumerate(PRESET_INSTRUCTIONS.items()):
            self._button(
                grid, label, lambda i=instruction: self._run_polish(i)
            ).grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)

        custom_btn = self._button(self.window, "Instrucción por voz", kind="teal")
        custom_btn.pack(fill="x", padx=19, pady=(10, 4))
        custom_btn.bind("<ButtonPress-1>", lambda e: self.record_start_fn())
        custom_btn.bind("<ButtonRelease-1>", lambda e: self._on_custom_instruction())
        self._label(
            self.window, "mantén pulsado el botón y habla", fg=MUTED, size=8
        ).pack(pady=(0, 14))

    def _on_custom_instruction(self) -> None:
        instruction = self.record_stop_fn()
        if not instruction:
            return
        self._run_polish(instruction)

    def _render_install_ollama(self) -> None:
        self._label(
            self.window,
            "Ollama no está instalado o no responde, y no hay una "
            "API key configurada.",
            fg=MUTED,
            wraplength=340,
        ).pack(padx=16, pady=(0, 10))
        self._button(
            self.window, "Instalar Ollama automáticamente", self._start_ollama_install
        ).pack(fill="x", padx=19, pady=(0, 16))

    def _run_polish(self, instruction: str) -> None:
        self._clear()
        self._polish_cancelled = False
        self._header()
        self._label(self.window, "Pensando...", fg=CYAN, size=12).pack(
            padx=16, pady=(6, 14)
        )
        self._button(self.window, "Cancelar", self._cancel_polish, kind="ghost").pack(
            fill="x", padx=19, pady=(0, 16)
        )
        threading.Thread(
            target=self._run_polish_thread, args=(instruction,), daemon=True
        ).start()

    def _cancel_polish(self) -> None:
        self._polish_cancelled = True
        self._render_choose_action()

    def _run_polish_thread(self, instruction: str) -> None:
        """Corre en un hilo aparte para no bloquear la UI de Tk durante los
        hasta 60s que puede tardar la llamada HTTP a `engine.polish()`.
        Sigue el mismo patrón que `_run_ollama_install`/`_set_status`:
        el hilo de fondo solo marshalla resultados a la UI vía
        `self.window.after(0, ...)`, nunca toca widgets directamente."""
        try:
            result = self.engine.polish(self.original_text, instruction)
        except Exception as exc:
            log.exception("Error llamando al motor de IA")
            if self._polish_cancelled:
                return
            message = self._polish_error_message(exc)
            self.window.after(0, lambda: self._render_error(message))
            return
        if self._polish_cancelled:
            return
        self.window.after(0, lambda: self._render_result(result))

    def _polish_error_message(self, exc: Exception) -> str:
        """Mensaje amigable cuando Ollama está corriendo pero el modelo
        configurado no se ha descargado (404 en /api/generate). Para
        cualquier otro caso (incluye ApiKeyEngine, donde un 404 significa
        una URL de API inválida, no un modelo sin descargar) se devuelve
        el mensaje genérico de siempre."""
        is_http_404 = (
            isinstance(exc, requests.exceptions.HTTPError)
            and getattr(exc, "response", None) is not None
            and getattr(exc.response, "status_code", None) == 404
        )
        if is_http_404 and isinstance(self.engine, OllamaEngine) and hasattr(self.engine, "model"):
            return (
                f"El modelo '{self.engine.model}' no está descargado. "
                f"Ejecuta en una terminal: ollama pull {self.engine.model}"
            )
        return str(exc)

    def _render_error(self, message: str) -> None:
        self._clear()
        self._header()
        self._label(
            self.window,
            f"Error: {message} Revisa tu configuración en .env.",
            fg=DANGER,
            wraplength=340,
        ).pack(padx=16, pady=(0, 12))
        self._button(self.window, "Cerrar", self.window.destroy, kind="ghost").pack(
            fill="x", padx=19, pady=(0, 16)
        )

    def _render_result(self, result_text: str) -> None:
        self._clear()
        self._header()
        text_widget = scrolledtext.ScrolledText(
            self.window,
            width=42,
            height=8,
            wrap="word",
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground=PURPLE,
            font=(self.font_body, 10),
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
        )
        text_widget.insert("1.0", result_text)
        text_widget.configure(state="disabled")
        # La barra de scroll de ScrolledText es gris de sistema y canta
        # sobre el fondo oscuro; va aparte porque no es un widget hijo normal.
        text_widget.vbar.configure(
            bg=SURFACE,
            troughcolor=BG,
            activebackground=PURPLE,
            relief="flat",
            bd=0,
            width=10,
            highlightthickness=0,
        )
        text_widget.pack(padx=16, pady=(0, 12))

        button_row = tk.Frame(self.window, bg=BG)
        button_row.pack(fill="x", padx=16, pady=(0, 16))
        self._button(
            button_row, "Pegar", lambda: self._paste_and_close(result_text), kind="teal"
        ).pack(side="left", expand=True, fill="x", padx=3)
        self._button(
            button_row, "Reintentar", self._render_choose_action
        ).pack(side="left", expand=True, fill="x", padx=3)
        self._button(
            button_row, "Descartar", self.window.destroy, kind="ghost"
        ).pack(side="left", expand=True, fill="x", padx=3)

    def _start_ollama_install(self) -> None:
        self._clear()
        self._header()
        self.status_label = self._label(
            self.window, "Instalando Ollama...", fg=CYAN, wraplength=340
        )
        self.status_label.pack(padx=16, pady=(0, 16))
        threading.Thread(target=self._run_ollama_install, daemon=True).start()

    def _set_status(self, text: str) -> None:
        self.window.after(0, lambda: self.status_label.configure(text=text))

    def _finish_install_with_retry(self, text: str) -> None:
        def render():
            self.status_label.configure(text=text)
            self._button(
                self.window, "Reintentar", self._render_choose_action
            ).pack(fill="x", padx=19, pady=(0, 16))

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
