#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Mide la fiabilidad del enlace 2.4 GHz contra la actividad del mouse.

El dongle acepta todos los pedidos, pero el mouse contesta solo a veces. La
sospecha es que depende de si el mouse esta activo (su radio despierta mas
seguido) o quieto. Esto lo mide en vez de suponerlo: lee el nodo de eventos
del propio mouse y clasifica cada pedido segun hubo o no movimiento reciente.

    dev/herramientas/medir-enlace.py --segundos 30

Mientras corre, movelo un rato y dejalo quieto otro rato.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "driver" / "src"))

import evdev  # noqa: E402

from linshark import protocol as p            # noqa: E402
from linshark.device import Device            # noqa: E402
from linshark.hidraw import (                 # noqa: E402
    DONGLE_PRODUCT_ID, VENDOR_ID, HidrawChannel, find_config_hidraw,
)

VENTANA_ACTIVO = 1.0   # segundos desde el ultimo movimiento para contar "activo"


def buscar_evdev() -> evdev.InputDevice | None:
    """El nodo de eventos del mouse detras del dongle (el que tiene REL_X)."""
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        info = dev.info
        if info.vendor != VENDOR_ID or info.product != DONGLE_PRODUCT_ID:
            dev.close()
            continue
        caps = dev.capabilities()
        if evdev.ecodes.EV_REL in caps and evdev.ecodes.REL_X in caps[evdev.ecodes.EV_REL]:
            return dev
        dev.close()
    return None


async def vigilar_movimiento(dev: evdev.InputDevice, estado: dict) -> None:
    async for event in dev.async_read_loop():
        if event.type == evdev.ecodes.EV_REL:
            estado["ultimo"] = time.monotonic()


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segundos", type=float, default=30.0)
    ap.add_argument("--cmd", type=int, default=p.CMD_VERSION,
                    help="que comando pedir (por defecto 11, version)")
    args = ap.parse_args()

    canal = HidrawChannel(find_config_hidraw())
    canal.open()
    dev = Device(canal)
    canal.start_reading(asyncio.get_running_loop(), dev.alimentar)

    evd = buscar_evdev()
    estado = {"ultimo": 0.0}
    tarea = None
    if evd is None:
        print("aviso: no encontre el nodo de eventos, no puedo medir actividad")
    else:
        print(f"midiendo actividad en {evd.path} ({evd.name.strip()})")
        tarea = asyncio.create_task(vigilar_movimiento(evd, estado))

    print(f"pidiendo '{p.CMD_NAMES.get(args.cmd, args.cmd)}' durante {args.segundos:.0f}s.")
    print("MOVE EL MOUSE un rato y dejalo quieto otro rato.\n")

    stats = {True: [0, 0], False: [0, 0]}   # activo -> [exitos, total]
    fin = time.monotonic() + args.segundos
    while time.monotonic() < fin:
        activo = (time.monotonic() - estado["ultimo"]) < VENTANA_ACTIVO
        frame = await dev.leer(args.cmd, reintentos=1, timeout=2.6)
        stats[activo][1] += 1
        if frame is not None:
            stats[activo][0] += 1
        etiqueta = "moviendose" if activo else "quieto     "
        marca = "ok " if frame else "NAK"
        print(f"  {etiqueta}  {marca}", flush=True)
        await asyncio.sleep(0.2)

    if tarea:
        tarea.cancel()
    canal.close()
    # El nodo de eventos tambien: lo abre `buscar_evdev()` y antes quedaba
    # abierto al terminar.
    if evd is not None:
        evd.close()

    print("\n--- resultado ---")
    for activo in (True, False):
        exitos, total = stats[activo]
        if not total:
            continue
        etiqueta = "moviendose" if activo else "quieto"
        pct = 100 * exitos / total
        print(f"  {etiqueta:11} {exitos}/{total} respondieron  ({pct:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
