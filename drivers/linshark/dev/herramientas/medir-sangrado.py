#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Cada cuanto el canal por cable devuelve el buffer de otro bloque.

    dev/herramientas/medir-sangrado.py --vueltas 40
    dev/herramientas/medir-sangrado.py --vueltas 40 --pausa 0.5

**Solo lee.** Manda los pedidos `0xA0` de `build_cable_read_request()` y nada
mas: el canal se abre en solo lectura y rechaza cualquier report de escritura.

Va de este lado porque mide **el canal**, no al mouse: es el equivalente por
cable de `medir-enlace.py`, que mide la radio del dongle.

**Que se esta midiendo.** El mouse tiene un solo buffer para todos los reports
(MEDIDO: un `GET(6)` devolvio la version), asi que un `GET` puede traer lo que
quedo del pedido anterior. Hay dos formas en que se nota:

  * el byte 0 trae otro comando -se conocia desde el 2026-09-18-;
  * el checksum interno no cierra: el byte 0 viene bien y el **contenido** es
    de otro bloque. Es lo que el 2026-09-20 hizo que `escribir_reposo_ligero()`
    reescribiera el payload de cmd 6 como si fuera la luz, y dejo el cmd 5 del
    mouse con la hibernacion en 128 min y la respuesta en 0.

`CableDevice` reintenta hasta tres veces y casi siempre sale bien, asi que
**desde afuera el fenomeno es invisible**: un `leer()` que anduvo al segundo
intento no se distingue de uno que anduvo al primero. Por eso el canal lleva la
cuenta (`CableDevice.rechazos`) y esto la lee.

Para que sirve el numero: si el sangrado es raro, configurar por cable es tan
confiable como parecia y las barandas alcanzan. Si es frecuente, hay que mirar
los tiempos -la pausa tras el pedido, el respiro entre pedidos- en vez de
elegirlos a ojo, que es como estan puestos hoy.

**Condicion fisica: ninguna.** Por cable no hay radio, asi que no hace falta
mover el mouse. Si conviene no usarlo mientras corre, para no mezclar el
trafico de los reports de movimiento con el de configuracion.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ.parent / "driver" / "src"))

from linshark import cable            # noqa: E402
from linshark import conexiones       # noqa: E402
from linshark import protocol as p    # noqa: E402

#: Los que se piden en cada vuelta. Van los cuatro que tienen checksum interno
#: -por donde se ve el sangrado silencioso- mas la version, que no lo tiene y
#: es constante, asi que sirve de canario por su cuenta.
A_PEDIR = (p.CMD_LIGHTING, p.CMD_DPI, p.CMD_BUTTONS, p.CMD_REPORT_RATE,
           p.CMD_VERSION, p.CMD_PROFILE)


def _mirar_si_es_el_anterior(rechazos) -> None:
    """La hipotesis que este medidor puede confirmar o romper.

    Si lo que vuelve es **siempre el bloque del pedido anterior**, el fenomeno
    esta explicado -el mouse sirve lo ultimo que tenia cuando todavia no armo
    lo nuevo- y cualquier arreglo pasa a ser dirigido. Como los pedidos van en
    el orden fijo de `A_PEDIR`, cual es el anterior de cada uno se sabe.

    **Requiere saber que se estaba pidiendo**, que es justo lo que la primera
    version de esta herramienta no guardaba: contaba que volvio y no de que
    pedido, y con eso la hipotesis no se puede ni plantear -cualquier bloque
    que vuelva es "el anterior" de algun pedido-.
    """
    import re

    anterior = {cmd: A_PEDIR[i - 1] for i, cmd in enumerate(A_PEDIR)}
    nombres = {p.CMD_NAMES.get(c, str(c)): c for c in A_PEDIR}
    encaja = rompe = sin_datos = 0
    for clave, n in rechazos.items():
        m = re.match(r"pidiendo (.+?): volvio el bloque de (0x[0-9a-f]+)",
                     clave)
        if not m:
            sin_datos += n          # el del checksum: no dice que volvio
            continue
        pedido, volvio = nombres.get(m.group(1)), int(m.group(2), 16)
        if pedido is None:
            sin_datos += n
        elif anterior[pedido] == volvio:
            encaja += n
        else:
            rompe += n

    if not (encaja or rompe):
        return
    print(f"\n  de los que dicen que volvio: {encaja} son el bloque del pedido "
          f"ANTERIOR y {rompe} no.")
    if rompe == 0:
        print("      Todos. El mouse sirve lo ultimo que tenia cuando todavia "
              "no armo lo nuevo.")
    else:
        print("      No es solo el anterior, asi que el buffer guarda mas de "
              "un bloque o el orden no manda.")
    if sin_datos:
        print(f"      ({sin_datos} rechazado(s) por checksum no dicen que "
              "volvio: ahi el byte 0 venia bien)")


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vueltas", type=int, default=20, metavar="N",
                    help="cuantas veces leer la tanda entera (por defecto 20)")
    ap.add_argument("--pausa", type=float, default=0.0, metavar="S",
                    help="segundos entre tandas, ademas del respiro propio "
                         "del canal. Sirve para ver si el sangrado depende de "
                         "que tan seguido se pide")
    args = ap.parse_args()

    try:
        conexion = conexiones.elegir()
    except conexiones.NoHayCanal as exc:
        print(f"no hay por donde: {exc}")
        return 2
    if conexion.via != conexiones.VIA_CABLE:
        print(f"{conexion.describir()}: esto mide el canal por CABLE. "
              "Enchufa el mouse por USB; con el cable puesto manda el cable.")
        return 2

    device = cable.abrir(conexion, solo_lectura=True)
    print(f"{conexion.describir()}")
    print(f"{args.vueltas} vueltas de {len(A_PEDIR)} bloques por "
          f"{device.path}, solo lectura\n")

    #: Un bloque que no volvio **despues** de los reintentos: el canal se
    #: rindio. Es lo que la Etapa 3 ve como "no contesto".
    perdidos: collections.Counter[int] = collections.Counter()
    version = collections.Counter()
    pedidos = 0
    arranque = time.monotonic()
    try:
        for vuelta in range(1, args.vueltas + 1):
            for cmd in A_PEDIR:
                frame = await device.leer(cmd)
                pedidos += 1
                if frame is None:
                    perdidos[cmd] += 1
                elif cmd == p.CMD_VERSION:
                    version[bytes(frame.data).hex()] += 1
            hasta_ahora = sum(device.rechazos.values())
            print(f"  vuelta {vuelta:>3}/{args.vueltas}: "
                  f"{hasta_ahora} rechazo(s) acumulado(s)", end="\r",
                  flush=True)
            if args.pausa:
                await asyncio.sleep(args.pausa)
    except KeyboardInterrupt:
        print("\n(cortado a mano)")
    finally:
        device.close()

    tardo = time.monotonic() - arranque
    print(f"\n\n{pedidos} pedidos en {tardo:.0f} s\n")

    total = sum(device.rechazos.values())
    if not total:
        print("  ningun bloque rechazado: no se vio sangrado en esta corrida.")
    else:
        print(f"  {total} bloque(s) rechazado(s) y vueltos a pedir "
              f"({total / pedidos:.1%} de los pedidos):")
        for motivo, n in device.rechazos.most_common():
            print(f"      {n:>5}  {motivo}")
        _mirar_si_es_el_anterior(device.rechazos)
    if perdidos:
        print("\n  y estos no volvieron ni con los reintentos, que es lo que "
              "la Etapa 3 ve como 'no contesto':")
        for cmd, n in perdidos.most_common():
            print(f"      {n:>5}  {p.CMD_NAMES.get(cmd, cmd)}")

    # La version no se puede escribir, asi que dos valores distintos son dos
    # lecturas y una vino mal. No tiene checksum interno: es el unico modo de
    # verlo (ver `sesion.CMDS_INMUTABLES`).
    if len(version) > 1:
        print("\n  OJO: el bloque de version, que NO se puede escribir, "
              "volvio con valores distintos:")
        for val, n in version.most_common():
            print(f"      {n:>5}  {val}")
        print("      Son lecturas corrompidas que el checksum no puede "
              "agarrar, porque cmd 11 no tiene.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
