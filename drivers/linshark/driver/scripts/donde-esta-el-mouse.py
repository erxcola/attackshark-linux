#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Por donde esta conectado el mouse, en que puerto, y si se lo puede configurar.

**No toca el mouse.** Todo sale de `/sys/class/hidraw` y de los atributos que el
kernel ya tiene leidos: no abre ningun nodo, no manda ni un byte y no ensucia
ninguna medicion que este corriendo.

    driver/scripts/donde-esta-el-mouse.py            # todo lo que hay en el bus
    driver/scripts/donde-esta-el-mouse.py --breve    # una linea por dispositivo

Los dos caminos son **dispositivos USB distintos**, con ids distintos:

  * el **dongle** de 2.4 GHz (`1d57:fa65` en el X8 Pro), por donde se
    configura;
  * el **cable** (`1d57:2126`), donde el canal de configuracion es otro
    -Feature Reports de largo variable- y **no esta medido**, asi que este
    programa lo reconoce y lo nombra pero no le escribe.

Y hay algo que conviene saber antes de enchufar el cable a la PC: con el cable
puesto **el mouse deja de hablar por el dongle** (MEDIDO, 32 s
sin un solo latido). Un cargador que no sea la computadora lo carga sin
llevarse el canal de radio.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from linshark import conexiones   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--breve", action="store_true",
                    help="una linea por dispositivo, sin los nodos")
    args = ap.parse_args()

    encontradas = conexiones.buscar()
    if args.breve:
        for c in encontradas:
            print(c.describir())
    else:
        print(conexiones.describir(encontradas))

    if not encontradas:
        return 1

    cable = next((c for c in encontradas
                  if c.via == conexiones.VIA_CABLE), None)
    if cable is not None:
        print()
        print("El mouse esta enchufado por cable. Mientras este asi **no habla "
              "por el dongle**")
        print("(MEDIDO): deja de mandar hasta el latido de "
              "bateria. Para configurarlo,")
        print("sacale el cable, o cargalo de un cargador que no sea la PC -eso "
              "no se lleva el canal-.")
        print()
        print("Experimento PENDIENTE, no medido: desconfigurar el dispositivo "
              "del cable sin cortarle")
        print("la corriente, a ver si el mouse vuelve solo a 2.4 GHz. El "
              "puerto sigue dando VBUS, asi")
        print("que deberia seguir cargando. Que vuelva a la radio **no esta "
              "medido**:")
        print(f"    echo 0 | sudo tee /sys/bus/usb/devices/{cable.puerto}/"
              "authorized     # y 1 para deshacerlo")
        print("    driver/scripts/sondear.py --escuchar 20    # si vuelven los "
              "latidos, volvio a la radio")

    print()
    try:
        elegida = conexiones.elegir(encontradas)
    except conexiones.NoHayCanal as exc:
        print(f"No se puede configurar: {exc}")
        return 1
    print(f"Se configura por: {elegida.describir()}")
    print(f"Canal de comandos: {elegida.nodo_de_configuracion.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
