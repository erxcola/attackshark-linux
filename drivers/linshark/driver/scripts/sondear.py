#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Sonda del canal de configuracion del mouse, sin navegador de por medio.

Aisla el lado del hardware: abre /dev/hidraw, escucha, y opcionalmente manda
un comando de LECTURA. Sirve para confirmar el formato real de los reports
antes de conectar la web.

    # solo escuchar 15 segundos, no escribe nada
    driver/scripts/sondear.py --escuchar 15

    # pedir la version de firmware (cmd 11) y escuchar la respuesta
    driver/scripts/sondear.py --leer 11

    # la sonda de macros: el byte 5 lleva el id, no el perfil (ver la nota de
    # build_read_frame; es una inferencia leida del bundle, no una captura)
    driver/scripts/sondear.py --pedir 9 --macro-id 17

    # los cuatro pedidos que hace la web al arrancar
    driver/scripts/sondear.py --leer-todo

Solo manda tramas de LECTURA (opcode 0xA0) armadas por build_read_frame(),
o sea con los `sub` de la tabla que salio del helper oficial. No hay forma de
mandar bytes arbitrarios desde aca a proposito: un opcode inventado puede caer
en un comando de bootloader y dejar el mouse ladrillo.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from linshark import estructuras           # noqa: E402
from linshark import protocol as p          # noqa: E402
from linshark.hidraw import (  # noqa: E402
    REPORT_ID_ESTADO, HidrawChannel, find_config_hidraw, verificar_nodo_dongle,
)

# Los cuatro que pide la pagina apenas nos acepta como helper, en orden.
PEDIDOS_DE_ARRANQUE = [
    (p.CMD_VERSION, 0),
    (p.CMD_REPORT_RATE, 0),
    (p.CMD_LIGHTING, 0),
    (p.CMD_DPI, 0),
]


def formatear(data: bytes, t0: float) -> str:  # noqa: C901
    """El primer byte siempre es el Report ID; el resto es el cuerpo."""
    report_id, body = data[0], data[1:].rstrip(b"\x00")
    if report_id == REPORT_ID_ESTADO:
        # [deviceId, marca, estadoBateria, nivelBateria]
        etiqueta = "estado"
        if len(body) >= 4:
            modelo = p.MOUSE_NUM.get(body[0], f"id {body[0]}")
            etiqueta = (f"estado: {modelo}, marca 0x{body[1]:02x}, "
                        f"bateria {body[3]}% (estado {body[2]})")
    else:
        cmd = body[0] if body else None
        sub = body[1] if len(body) > 1 else None
        etiqueta = f"{p.CMD_NAMES.get(cmd, f'cmd {cmd}')} sub={sub}"
    hexdump = " ".join(f"{b:02x}" for b in body[:32])
    cola = " ..." if len(body) > 32 else ""
    return (f"[{time.monotonic() - t0:6.2f}s] id={report_id} {len(body):3d}B  "
            f"{etiqueta}\n           {hexdump}{cola}")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hidraw", type=Path, help="por defecto se busca en sysfs")
    ap.add_argument("--escuchar", type=float, default=10.0, metavar="SEG",
                    help="cuanto escuchar (por defecto %(default)s s)")
    ap.add_argument("--leer", type=int, metavar="CMD",
                    help="manda una lectura del comando CMD. El `sub` sale "
                         "siempre de la tabla READ_SUB")
    ap.add_argument("--leer-todo", action="store_true",
                    help="manda los cuatro pedidos que hace la web al arrancar")
    ap.add_argument("--pedir", action="append", type=int, metavar="CMD", default=[],
                    help="pide un valor con correlacion y reintentos")
    ap.add_argument("--macro-id", type=int, metavar="N",
                    help="SOLO con el cmd 9: pone el id del macro en el byte 5 "
                         "de la lectura, donde los demas comandos llevan el "
                         "perfil. Es una SONDA con una inferencia adentro "
                         "(ver la nota de build_read_frame): sirve para "
                         "averiguar por que el bloque vuelve vacio, no es la "
                         "plantilla del helper")
    args = ap.parse_args()

    # La opcion es angosta a proposito: un solo comando, un solo byte, un rango
    # validado, y todo sigue pasando por build_read_frame(). No es el `--crudo`
    # que se saco -ese mandaba hexadecimal arbitrario-, y no tiene que
    # convertirse en eso.
    if args.macro_id is not None:
        pedidos = [c for c in (args.pedir + ([args.leer] if args.leer else []))
                   if c is not None]
        if pedidos != [p.CMD_MACRO]:
            print(f"--macro-id va con --pedir {p.CMD_MACRO} (o --leer "
                  f"{p.CMD_MACRO}) y con nada mas", file=sys.stderr)
            return 2
        try:
            p.build_read_frame(p.CMD_MACRO, macro_id=args.macro_id)
        except ValueError as exc:
            print(exc.args[0], file=sys.stderr)
            return 2

    # Antes habia un --crudo que mandaba hexadecimal arbitrario y un --leer que
    # aceptaba cualquier SUB. Los dos salteaban build_read_frame() y con eso la
    # unica garantia que tiene el proyecto de no inventar tramas. Se sacaron:
    # si hace falta probar un comando nuevo, el camino es agregarlo a READ_SUB
    # citando de donde salio, no pasarlo por la linea de comandos.

    if args.hidraw is not None:
        # El nodo de la interfaz 2 del mouse por CABLE tambien existe y se abre
        # sin quejarse, pero habla Feature Reports: mandarle estas tramas seria
        # escribir bytes que nadie leyo nunca en un endpoint vendor.
        verificar_nodo_dongle(args.hidraw)
        path = args.hidraw
    else:
        path = find_config_hidraw()

    # Si solo se va a escuchar, el descriptor se abre O_RDONLY y el kernel se
    # encarga de que no salga un byte.
    va_a_escribir = bool(args.leer_todo or args.leer is not None or args.pedir)
    canal = HidrawChannel(path, solo_lectura=not va_a_escribir)
    canal.open()

    t0 = time.monotonic()
    recibidos = 0

    def al_llegar(data: bytes) -> None:
        nonlocal recibidos
        recibidos += 1
        print(formatear(data, t0), flush=True)

    canal.start_reading(asyncio.get_running_loop(), al_llegar)

    envios: list[tuple[bytes, str]] = []
    try:
        if args.leer_todo:
            for cmd, _ in PEDIDOS_DE_ARRANQUE:
                envios.append((p.build_read_frame(cmd),
                               f"lectura de {p.CMD_NAMES.get(cmd, cmd)}"))
        elif args.leer is not None:
            envios.append((p.build_read_frame(args.leer,
                                              macro_id=args.macro_id),
                           f"lectura de {p.CMD_NAMES.get(args.leer, args.leer)}"))
    except p.ComandoSinSub as exc:
        canal.close()
        print(f"error: {exc.args[0]}", file=sys.stderr)
        print(f"comandos con plantilla: "
              f"{', '.join(str(c) for c in sorted(p.READ_SUB))}", file=sys.stderr)
        return 2

    if not envios and not args.pedir:
        print(f"escuchando {path} por {args.escuchar}s sin escribir nada...")
    for payload, etiqueta in envios:
        print(f"-> {payload.hex()}   ({etiqueta})", flush=True)
        canal.write_frame(payload)
        await asyncio.sleep(1.0)

    if args.pedir:
        from linshark.device import Device
        dev = Device(canal)

        def espiar(data: bytes) -> None:
            if data[:1] != bytes([REPORT_ID_ESTADO]):
                print(f"      <<< {data[:16].hex(' ')}", flush=True)
            dev.alimentar(data)

        canal._on_report = espiar
        dev.on_frame = lambda f: print(f"   (suelta) {f.describe()}")
        for cmd in args.pedir:
            frame = await dev.leer(cmd, macro_id=args.macro_id)
            nombre = p.CMD_NAMES.get(cmd, f"cmd {cmd}")
            if frame is None:
                print(f"{nombre:22} SIN RESPUESTA")
            else:
                print(f"{nombre:22} datos: {frame.data.hex(' ')}"
                      f"   (checksum {'ok' if frame.checksum_ok else 'MAL'})")
                legible = estructuras.describir(frame.cmd, frame.data)
                if legible:
                    print(f"{'':22} {legible}")
        canal.close()
        return 0

    await asyncio.sleep(args.escuchar)
    canal.close()
    print(f"\n{recibidos} report(s) recibidos.")
    return 0 if (recibidos or not envios) else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
