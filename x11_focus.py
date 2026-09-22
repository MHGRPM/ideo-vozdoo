"""Recordar que ventana tenia el foco y devolverselo antes de pegar.

Al pulsar el orbe, el gestor de ventanas puede dar el foco del teclado a
la ventana del orbe. Si eso pasa, el Ctrl+V que simulamos al terminar de
dictar se lo come el propio orbe y el texto nunca llega a donde estabas
escribiendo.

Intentar que la ventana no acepte el foco resulto peor: segun el gestor
de ventanas, deja de recibir tambien los clics. Asi que en vez de evitar
perder el foco, lo devolvemos: se vigila cual es la ventana con foco que
NO es nuestra, y se le restituye justo antes de pegar.

Solo hace algo en Linux/X11. En Windows y Mac es un no-op: alli el
problema no se da porque la ventana es de tipo herramienta y no roba el
foco del teclado."""

from __future__ import annotations

import logging
import sys

log = logging.getLogger("vozdoo")


class FocusKeeper:
    def __init__(self) -> None:
        self.enabled = sys.platform.startswith("linux")
        self.display = None
        self.last_window = None
        if not self.enabled:
            return
        try:
            from Xlib import display

            self.display = display.Display()
        except Exception:
            log.debug("Sin X11: no se puede recordar el foco", exc_info=True)
            self.enabled = False

    def remember(self, own_ids: set[int]) -> None:
        """Guarda la ventana con foco si no es una de las nuestras."""
        if not self.enabled or self.display is None:
            return
        try:
            focused = self.display.get_input_focus().focus
            window_id = getattr(focused, "id", None)
            if window_id and window_id not in own_ids:
                self.last_window = focused
        except Exception:
            log.debug("No se pudo leer la ventana con foco", exc_info=True)

    def restore(self) -> bool:
        """Devuelve el foco a la ventana recordada. True si lo intentó."""
        if not self.enabled or self.display is None or self.last_window is None:
            return False
        try:
            from Xlib import X

            self.display.set_input_focus(
                self.last_window, X.RevertToParent, X.CurrentTime
            )
            self.display.flush()
            return True
        except Exception:
            log.debug("No se pudo devolver el foco", exc_info=True)
            return False
