# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Lo que la ventana recuerda entre corridas: hoy, el idioma.

Vive al lado de los nombres de macro (`linshark.nombres`) y sigue sus mismas
reglas, por los mismos motivos:

  * **es nuestro y no del mouse**, asi que perder el archivo no rompe nada: sin
    el, la aplicacion arranca en castellano;
  * un archivo ilegible se lee como vacio y **se dice** en el log, y
    `guardar()` se niega a escribirle encima -podria ser de otra version, o
    tener algo que alguien edito a mano-;
  * un idioma que la aplicacion no conoce se ignora, no revienta el arranque.

No sabe nada de Qt ni del mouse: lee y escribe un JSON.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from linshark import lugares

from . import i18n

log = logging.getLogger("linshark_ui.preferencias")

VERSION = 1


def ruta_por_defecto() -> Path:
    """`~/.config/linshark/interfaz.json`, o lo que diga `XDG_CONFIG_HOME`."""
    return lugares.configuracion() / "interfaz.json"


class Preferencias:
    """Las preferencias de la ventana, en un archivo JSON.

    Se carga al construirla. `problema` queda con el motivo si el archivo
    existia y no se pudo leer; en ese caso `guardar()` no escribe.
    """

    def __init__(self, ruta: Path | str | None = None) -> None:
        self.ruta = Path(ruta) if ruta is not None else ruta_por_defecto()
        self.problema = ""
        self.idioma = i18n.IDIOMA_POR_DEFECTO
        self._cargar()

    def _cargar(self) -> None:
        if not self.ruta.exists():
            return
        try:
            crudo = json.loads(self.ruta.read_text(encoding="utf-8"))
            idioma = crudo.get("idioma", i18n.IDIOMA_POR_DEFECTO)
        except Exception as exc:            # noqa: BLE001
            self.problema = f"{self.ruta}: {exc}"
            log.warning("no pude leer las preferencias (%s)", self.problema)
            return
        if idioma in i18n.IDIOMAS:
            self.idioma = idioma
        else:
            log.warning("idioma %r en %s no es ninguno de %s; sigo en %r",
                        idioma, self.ruta, list(i18n.IDIOMAS), self.idioma)

    def guardar(self) -> None:
        """Escribe el archivo. Se niega si no se pudo leer el que habia."""
        if self.problema:
            raise RuntimeError(
                f"no escribo encima de un archivo que no pude leer "
                f"({self.problema}). Movelo o borralo a mano")
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        crudo = {"version": VERSION, "idioma": self.idioma}
        # Al lado y despues se renombra: un corte en el medio deja el viejo.
        tmp = self.ruta.with_suffix(self.ruta.suffix + ".tmp")
        tmp.write_text(json.dumps(crudo, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        tmp.replace(self.ruta)

    def recordar_idioma(self, idioma: str) -> None:
        """Lo que se engancha a `i18n.al_cambiar_idioma`. Nunca revienta."""
        self.idioma = idioma
        try:
            self.guardar()
        except Exception as exc:            # noqa: BLE001
            # Que no se guarde el idioma no es motivo para dejar la pantalla
            # a medio traducir: el cambio ya se hizo, y se dice en el log.
            log.warning("no pude guardar el idioma: %s", exc)


def usar(preferencias: Preferencias) -> None:
    """Pone el idioma guardado y guarda cada cambio que se haga despues.

    Va **antes** de construir la ventana: los widgets toman su texto al
    crearse, y arrancar en castellano para cambiar enseguida seria armar la
    pantalla dos veces.
    """
    i18n.fijar_idioma(preferencias.idioma)
    i18n.al_cambiar_idioma(preferencias.recordar_idioma)
