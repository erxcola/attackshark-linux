# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Los nombres de los macros, que el mouse no guarda.

**El bloque de un macro no tiene campo de nombre.** Los 111 bytes estan
decodificados enteros -id, modo de disparo, contador, cantidad de pares,
eventos y checksum- y ahi no hay lugar para texto. El soft de Windows guarda
los suyos en un archivo propio (`ms_13/macro.data`, con el nombre en UTF-16 al
principio), asi que los nombres **son cosa del cliente**: si alguien configura
el mouse con el soft y despues con esta aplicacion, los nombres no viajan. El
macro si: ese vive en el mouse.

De ahi salen las tres reglas de este modulo:

  * el nombre es **nuestro** y el macro es **del mouse**, asi que perder este
    archivo no puede romper nada: sin el, un macro se llama "macro 17";
  * un archivo ilegible se lee como vacio y **se dice**, en vez de reventar la
    sesion o -peor- de pisarlo callado;
  * el id se valida con el mismo rango que el mouse (`MACRO_ID_MIN..MAX`), asi
    un nombre no puede quedar colgado de un id que el mouse no acepta.

No sabe leer ni escribir el mouse. Es la mitad de la aplicacion que vive en el
disco de esta maquina.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

# El rango de ids es del modelo y sale del perfil, asi que se lee del modulo
# y no se importa el valor: importarlo lo congelaria en el del X8 Pro.
from . import estructuras as est
from . import lugares

log = logging.getLogger("linshark.nombres")

#: Lo que dice el archivo sobre de que habla. Dos mouses distintos no comparten
#: los nombres de sus macros, y un archivo que no dice de cual es no se puede
#: mezclar despues.
DISPOSITIVO = "attack-shark-x8-pro"

VERSION = 1


def ruta_por_defecto() -> Path:
    """`~/.config/linshark/macros.json`, o lo que diga `XDG_CONFIG_HOME`."""
    return lugares.configuracion() / "macros.json"


class NombresDeMacro:
    """Los nombres de los macros de un mouse, en un archivo JSON.

    Se carga al construirla. `problema` queda con el motivo si el archivo
    existia y no se pudo leer: en ese caso la biblioteca arranca vacia -para
    que la aplicacion siga andando- pero `guardar()` se niega, porque escribir
    encima seria borrar lo que hubiera adentro sin que nadie lo vea.
    """

    def __init__(self, ruta: Path | str | None = None) -> None:
        self.ruta = Path(ruta) if ruta is not None else ruta_por_defecto()
        self.problema = ""
        self._nombres: dict[int, str] = {}
        self._cargar()

    # --- disco ------------------------------------------------------------

    def _cargar(self) -> None:
        if not self.ruta.exists():
            return
        try:
            crudo = json.loads(self.ruta.read_text(encoding="utf-8"))
            macros = crudo["macros"]
            self._nombres = {int(k): str(v) for k, v in macros.items()}
        except Exception as exc:            # noqa: BLE001
            # Cualquier cosa: JSON roto, una clave que no es un numero, el
            # archivo de otro programa. Se avisa una vez y se sigue sin
            # nombres, que es exactamente como estaba el proyecto ayer.
            self.problema = f"{self.ruta}: {exc}"
            self._nombres = {}
            log.warning("no pude leer los nombres de macro (%s)", self.problema)

    def guardar(self) -> None:
        """Escribe el archivo. Se niega si no se pudo leer el que habia."""
        if self.problema:
            raise RuntimeError(
                f"no escribo encima de un archivo que no pude leer "
                f"({self.problema}). Movelo o borralo a mano: si tiene "
                "nombres adentro, esto los perderia")
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        crudo = {"version": VERSION, "dispositivo": DISPOSITIVO,
                 "macros": {str(k): v for k, v in sorted(self._nombres.items())}}
        # Se escribe al lado y se renombra: un corte de luz en el medio deja
        # el archivo viejo entero, no uno a medias.
        tmp = self.ruta.with_suffix(self.ruta.suffix + ".tmp")
        tmp.write_text(json.dumps(crudo, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        tmp.replace(self.ruta)

    # --- nombres ----------------------------------------------------------

    @staticmethod
    def _id(macro_id: int) -> int:
        if not isinstance(macro_id, int) or isinstance(macro_id, bool) or \
                not est.MACRO_ID_MIN <= macro_id <= est.MACRO_ID_MAX:
            raise ValueError(f"macro id {macro_id!r} fuera de "
                             f"{est.MACRO_ID_MIN}..{est.MACRO_ID_MAX}, que es "
                             "el rango del mouse")
        return macro_id

    def nombre(self, macro_id: int) -> str | None:
        """El nombre de ese macro, o None si no le pusimos ninguno."""
        return self._nombres.get(self._id(macro_id))

    def describir(self, macro_id: int) -> str:
        """Como se nombra el macro en pantalla, tenga nombre o no."""
        n = self.nombre(macro_id)
        return f"macro {macro_id} ({n})" if n else f"macro {macro_id}"

    def poner(self, macro_id: int, nombre: str) -> None:
        """Le pone nombre. No guarda: eso lo pide quien llama."""
        texto = str(nombre).strip()
        if not texto:
            raise ValueError("un nombre vacio no es un nombre: si lo que "
                             "queres es sacarlo, es borrar()")
        self._nombres[self._id(macro_id)] = texto

    def borrar(self, macro_id: int) -> None:
        """Le saca el nombre. Que el macro no tenga nombre es lo normal."""
        self._nombres.pop(self._id(macro_id), None)

    def todos(self) -> dict[int, str]:
        """Todos los nombres, por id."""
        return dict(self._nombres)
