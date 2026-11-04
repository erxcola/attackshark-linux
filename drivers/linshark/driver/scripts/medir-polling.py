#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Mide la tasa de reporte real del mouse, leyendo sus eventos de entrada.

No depende del driver ni de lo que diga la web: cronometra los reportes que
llegan de verdad al kernel. Hay que mover el mouse mientras corre, porque un
mouse quieto no reporta.

    driver/scripts/medir-polling.py --segundos 10
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import evdev  # noqa: E402

from linshark.hidraw import DONGLE_PRODUCT_ID, VENDOR_ID, WIRED_PRODUCT_ID  # noqa: E402


def buscar() -> evdev.InputDevice | None:
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        if dev.info.vendor != VENDOR_ID or \
           dev.info.product not in (DONGLE_PRODUCT_ID, WIRED_PRODUCT_ID):
            dev.close()
            continue
        caps = dev.capabilities()
        if evdev.ecodes.EV_REL in caps and \
           evdev.ecodes.REL_X in caps[evdev.ecodes.EV_REL]:
            return dev
        dev.close()
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segundos", type=float, default=10.0)
    args = ap.parse_args()

    dev = buscar()
    if dev is None:
        print("no encontre el mouse. Esta puesto el dongle?")
        return 1
    conexion = "dongle 2.4 GHz" if dev.info.product == DONGLE_PRODUCT_ID else "cable"
    print(f"{dev.name.strip()}  ({conexion})  en {dev.path}")
    print(f"MOVE EL MOUSE sin parar durante {args.segundos:.0f} segundos...\n")

    # El nodo de eventos se cierra pase lo que pase: un Ctrl-C a mitad de una
    # medicion es lo normal, no la excepcion.
    try:
        return _medir(dev, args.segundos)
    finally:
        dev.close()


def _medir(dev, segundos: float) -> int:
    intervalos: list[float] = []
    anterior = None
    fin = time.monotonic() + segundos
    for event in dev.read_loop():
        if time.monotonic() > fin:
            break
        # SYN_REPORT cierra cada paquete: un SYN = un reporte del mouse.
        if event.type != evdev.ecodes.EV_SYN or event.code != evdev.ecodes.SYN_REPORT:
            continue
        ahora = event.timestamp()
        if anterior is not None:
            delta = ahora - anterior
            if 0 < delta < 0.05:      # descarta las pausas entre movimientos
                intervalos.append(delta)
        anterior = ahora

    if len(intervalos) < 50:
        print(f"solo {len(intervalos)} muestras: hay que moverlo mas.")
        return 1

    intervalos.sort()
    mediana = intervalos[len(intervalos) // 2]
    print(f"muestras: {len(intervalos)}")
    print(f"intervalo mediano: {mediana * 1e6:.0f} us")
    print(f"tasa mediana:      {1 / mediana:.0f} Hz")
    print()
    print("distribucion de intervalos:")
    hist = Counter(round(i * 1e6 / 125) * 125 for i in intervalos)
    for us, n in sorted(hist.items())[:8]:
        barra = "#" * min(50, n * 50 // len(intervalos))
        pct = 100 * n / len(intervalos)
        rate = 1e6 / us if us else 0
        print(f"  {us:5} us (~{rate:5.0f} Hz)  {pct:5.1f}%  {barra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
