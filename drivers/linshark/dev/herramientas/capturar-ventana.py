#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Las capturas de pantalla del README, hechas por un programa y no a mano.

Levanta la ventana contra el `_MouseFalso` de la tanda de pruebas -que sirve
los bloques REALES de este mouse: `LUZ_REAL`, `DPI_REAL`, `BOTONES_LEIDO`- y
guarda la imagen sin servidor grafico (`QT_QPA_PLATFORM=offscreen`).

Que la imagen se regenere con un comando es lo que la hace evidencia y no
adorno: cuando la ventana cambie, la captura del README se rehace, en vez de
quedarse mostrando una version que ya no existe.

    $ dev/herramientas/capturar-ventana.py
    $ dev/herramientas/capturar-ventana.py --panel macros --ancho 1100

**No toca el mouse**: no abre ningun nodo ni manda nada al bus.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ / "driver" / "src"))
sys.path.insert(0, str(RAIZ / "driver" / "tests"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from linshark import conexiones as con  # noqa: E402
from linshark import dispositivos as disp  # noqa: E402
from linshark_ui.hardware import Hardware  # noqa: E402
from linshark_ui.ventana import Ventana  # noqa: E402
from salvaguardas import _MouseFalso  # noqa: E402

# Al lado del README del driver y no en `dev/`: `driver/` se distribuye solo,
# y su manual tiene que verse sin el otro arbol.
DESTINO = RAIZ / "driver" / "docs" / "img"


class _ConexionFalsa:
    """Lo justo para que la barra diga por donde esta, sin mirar el bus."""

    via = con.VIA_DONGLE
    puerto = "1-2"
    producto = 0xFA65
    nodo = "/dev/hidraw2"
    legible = True
    escribible = True
    vendor = 0x1D57
    velocidad = 480
    bus = 1
    dispositivo = 8

    def __getattr__(self, _nombre):        # lo que la barra pida y no este
        return None


def _esperar(app, condicion, segundos=20) -> bool:
    fin = [False]
    QTimer.singleShot(int(segundos * 1000), lambda: fin.__setitem__(0, True))
    while not condicion() and not fin[0]:
        app.processEvents()
    return bool(condicion())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel", default="parametros",
                    choices=("parametros", "macros", "registro"))
    ap.add_argument("--ancho", type=int, default=1280)
    ap.add_argument("--alto", type=int, default=860)
    ap.add_argument("--salida", type=Path, default=None)
    args = ap.parse_args()

    # El bus se fija: si esta maquina tiene un mouse por cable, la ventana
    # mostraria el cartel del cable y la captura hablaria de otra cosa.
    con.buscar = lambda *a, **k: [_ConexionFalsa()]

    app = QApplication.instance() or QApplication([])
    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, {17: "copiar y pegar"})
    ventana.resize(args.ancho, args.alto)
    hw.conectar()
    ventana.leer()
    # El cartel de "todavia no lei el mouse" se esconde cuando hay campos:
    # esperar a eso es esperar a que la ventana tenga algo que mostrar.
    if not _esperar(app, lambda: ventana.parametros._vacio.isHidden()):
        print("la ventana no llego a mostrar campos", file=sys.stderr)
        return 1
    # **La barra se completa a mano, y conviene saber por que.** Los campos
    # que se ven son bloques REALES de este mouse, servidos por `_MouseFalso`;
    # la barra, en cambio, describe la conexion, y sin bus de verdad diria
    # "Sin conectar" y "(device inyectado)". Estos tres valores son los de una
    # sesion tipica -dongle en el puerto 1-2, nodo 2- y estan aca, a la vista,
    # y no escondidos en la imagen.
    perfil = disp.activo()
    ventana.conexion.poner_modelo(perfil.device_id, perfil.nombre)
    ventana.conexion.poner_via(con.VIA_DONGLE, "1-2")
    ventana.conexion.poner_nodo("/dev/hidraw2")
    ventana.conexion.poner_bateria(82, False)
    for _ in range(40):                    # que termine de pintarse
        app.processEvents()

    pestañas = {"parametros": 0, "macros": 1, "registro": 2}
    ventana.pestañas.setCurrentIndex(pestañas[args.panel])
    for _ in range(40):
        app.processEvents()

    salida = args.salida or (DESTINO / f"ventana-{args.panel}.png")
    salida.parent.mkdir(parents=True, exist_ok=True)
    if not ventana.grab().save(str(salida)):
        print(f"no se pudo escribir {salida}", file=sys.stderr)
        return 1
    print(f"{salida.relative_to(RAIZ)}  ({salida.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
