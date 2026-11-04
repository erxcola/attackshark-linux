# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El punto de entrada de la ventana.

    $ ./linshark-gui
    $ python3 -m linshark_ui --nodo /dev/hidraw2

**No lee el mouse al arrancar.** Abrir un cliente oficial pisa configuracion
-la web reescribe todo lo que lee y deja el scroll invertido; el soft pisa el
dpi- y lo primero que esta aplicacion no tiene que heredar es eso. Aca la
lectura la pide quien mira, con el boton. Leer no escribe nada, pero arrancar
solo tampoco es gratis: son varios segundos de enlace 2.4 GHz con el mouse
posiblemente quieto.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:                      # correr sin instalar
    sys.path.insert(0, str(RAIZ))

from PySide6.QtWidgets import QApplication          # noqa: E402

from linshark.nombres import NombresDeMacro         # noqa: E402
from linshark import lugares                        # noqa: E402
from linshark_ui import estilo                      # noqa: E402
from linshark_ui import preferencias                # noqa: E402
from linshark_ui.hardware import Hardware           # noqa: E402
from linshark_ui.ventana import Ventana             # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="linshark-gui",
        description="LinShark: configurar el mouse desde Linux.")
    ap.add_argument("--nodo", type=Path, metavar="/dev/hidrawN",
                    help="el nodo del dongle. Sin esto se busca solo, y el "
                         "que se pase se VERIFICA antes de abrirlo")
    ap.add_argument("--sin-tema", action="store_true",
                    help="dibujar con el tema del escritorio en vez del "
                         "propio")
    ap.add_argument("--nombres", type=Path, metavar="ARCHIVO",
                    help="donde estan los nombres de macro "
                         "(por defecto ~/.config/linshark/macros.json)")
    ap.add_argument("--preferencias", type=Path, metavar="ARCHIVO",
                    help="donde se guarda el idioma elegido "
                         "(por defecto ~/.config/linshark/interfaz.json)")
    ap.add_argument("--al-abrir", type=Path, metavar="ARCHIVO",
                    default=None,
                    help="donde queda la primera lectura del mouse de cada "
                         "apertura (por defecto "
                         "~/.local/state/linshark/al-abrir.json)")
    ap.add_argument("--verboso", action="store_true",
                    help="el log del protocolo por la terminal")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verboso else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s")

    app = QApplication(sys.argv[:1])
    app.setApplicationName("linshark")
    app.setApplicationDisplayName("LinShark")
    if not args.sin_tema:
        estilo.aplicar(app)

    # El idioma antes que la ventana: cada widget toma su texto al crearse.
    preferencias.usar(preferencias.Preferencias(args.preferencias))

    hardware = Hardware(nodo=args.nodo)
    ventana = Ventana(hardware, NombresDeMacro(args.nombres),
                      al_abrir=args.al_abrir or lugares.al_abrir())
    ventana.show()
    # Abrir el nodo es lo unico que se hace solo: si falta la regla de udev,
    # conviene que el cartel con el arreglo aparezca ahora y no al primer
    # click. Abrir no lee ni escribe nada.
    hardware.conectar()
    hardware.abrir()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
