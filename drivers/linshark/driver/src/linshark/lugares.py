# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Donde guarda el programa lo que anota de un mouse, en la maquina de quien lo usa.

Nada de eso va al lado del codigo. Instalado, al lado del codigo es
`/opt/linshark`, que es de root; en el repositorio, terminaba versionado junto
con el protocolo. Como estaba un mouse al abrir la ventana, o antes de una
escritura, es de quien lo usa y no del proyecto.

  * `~/.config/linshark/`: lo que **elige** quien usa el programa -el idioma,
    los nombres de macro-. Lo manejan `linshark.nombres` y
    `linshark_ui.preferencias`.
  * `~/.local/state/linshark/`: lo que el programa **anota** del mouse. No es
    cache: un respaldo no se puede volver a sacar despues de escribir.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def configuracion() -> Path:
    """`~/.config/linshark/`, o lo que diga `XDG_CONFIG_HOME`."""
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "linshark"


def carpeta() -> Path:
    """`~/.local/state/linshark/`, o lo que diga `XDG_STATE_HOME`."""
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "linshark"


def respaldos() -> Path:
    """Donde las herramientas de la terminal dejan cada respaldo."""
    return carpeta() / "respaldos"


def al_abrir() -> Path:
    """Donde la ventana deja la primera lectura de cada apertura.

    Se reemplaza cada vez que se abre la ventana y se lee el mouse. Tiene el
    formato de un respaldo, asi que sirve para `respaldar.py --comparar` y
    para `restaurar-bloque.py --respaldo`. Si la ventana bajo la tasa para
    poder leer, el bloque de rate dice 1000 y `tasa_bajada_desde` dice a
    cuanto estaba el mouse.
    """
    return carpeta() / "al-abrir.json"


def guardar_estado(estado: dict, ruta: Path) -> None:
    """Escribe un estado leido del mouse, con el formato de un respaldo."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Al lado y despues se renombra: un corte en el medio deja el anterior.
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(estado, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(ruta)
