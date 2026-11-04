#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Guarda todo lo que el mouse sabe contestar, para poder volver atras.

Es la Etapa 0 de `dev/docs/metodo.md`, y es **prerequisito** de cualquier escritura:
antes de mandarle el primer byte de configuracion al mouse hay que poder
responder "que habia antes".

    driver/scripts/respaldar.py                          # a ~/.local/state/linshark/respaldos/
    driver/scripts/respaldar.py -o antes-de-escribir.json
    driver/scripts/respaldar.py --comparar a.json b.json # sin tocar el mouse

**Solo lee.** Manda las mismas tramas de 12 bytes que ya usa el puente en modo
`read`, armadas por `build_read_frame()`.

Conviene mover el mouse mientras corre: el enlace de 2.4 GHz pierde alrededor
de la mitad de los pedidos con el mouse quieto.

**Con el mouse enchufado por cable, respalda por el cable** (`linshark.cable`):
los pedidos de lectura `0xA0` y nada mas -el canal se abre en solo lectura y
rechaza cualquier report de escritura-. El respaldo dice su camino
(`"via": "cable"`).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from linshark import cable  # noqa: E402
from linshark import conexiones  # noqa: E402
from linshark import lugares  # noqa: E402
from linshark import protocol as p  # noqa: E402
from linshark import sesion  # noqa: E402
from linshark.device import Device  # noqa: E402
from linshark.hidraw import (  # noqa: E402
    HidrawChannel, find_config_hidraw, verificar_nodo_dongle,
)

# **La logica vive en `linshark.sesion`, no aca.** Este script es la terminal:
# elige el nodo, imprime mientras el mouse va contestando y guarda el JSON.
# Leer el estado y compararlo es de la biblioteca, porque es lo que usa la
# aplicacion y lo que `primera-escritura.py` necesita sin tener que importar
# otro script (que es lo que hacia antes).
A_LEER = sesion.A_LEER
PASADAS = sesion.PASADAS
RESPIRO_TRAS_FALLO = sesion.RESPIRO_TRAS_FALLO

# Los comparadores se reexportan con los nombres con los que ya se los usa.
comparar = sesion.diferencias
cmds_que_cambiaron = sesion.cmds_que_cambiaron
macros_a_releer = sesion.macros_a_releer


async def tomar_respaldo(canal, device, pasadas: int = PASADAS,
                         macros_extra=()) -> dict:
    """El estado entero, con la salida por terminal de este script."""
    return await sesion.leer_estado(
        device, nodo=str(canal.path), pasadas=pasadas,
        macros_extra=macros_extra,
        al_leer=lambda l: print(sesion.linea_de(l)),
        al_reintentar=lambda f, e: print(sesion.aviso_de_reintento(
            f, e, via=sesion.via_de(device))),
        al_cortar=lambda f, m: print(f"  {m}"))


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hidraw", type=Path, help="por defecto se busca en sysfs")
    ap.add_argument("-o", "--salida", type=Path,
                    help="por defecto ~/.local/state/linshark/respaldos/"
                         "<fecha>.json")
    ap.add_argument("--macro-id", type=int, action="append", metavar="N",
                    default=[],
                    help="respalda tambien este macro, ademas de los que los "
                         "slots de cmd 8 apuntan. Repetible. Hace falta para "
                         "los macros que existen sin boton asignado, que "
                         "ningun slot apunta. Un "
                         "barrido de los 255 slots no es viable: "
                         "cada lectura cuesta segundos y el enlace pierde la "
                         "mitad de los pedidos")
    ap.add_argument("--comparar", nargs=2, type=Path, metavar=("A", "B"),
                    help="compara dos respaldos y sale; no toca el mouse")
    args = ap.parse_args()

    if args.comparar:
        a = json.loads(args.comparar[0].read_text())
        b = json.loads(args.comparar[1].read_text())
        # **Antes del diff, si alguno de los dos se contradice.** Un diff
        # contra un respaldo con una lectura sangrada inventa cambios que
        # nadie hizo: paso el 2026-09-20 con el bloque de rate, y el diff
        # dijo que la tasa habia cambiado cuando no se la habia tocado.
        for ruta, estado in zip(args.comparar, (a, b)):
            for linea in sesion.incoherencias(estado):
                print(f"OJO: {ruta.name} se contradice -> {linea}")
        difs = comparar(a, b)
        print(f"{args.comparar[0].name}  ->  {args.comparar[1].name}")
        if not difs:
            print("  sin diferencias")
            return 0
        for d in difs:
            print(f"  {d}")
        return 1

    if args.hidraw is None:
        try:
            conexion = conexiones.elegir()
        except conexiones.NoHayCanal:
            conexion = None       # que lo explique find_config_hidraw()
        if conexion is not None and conexion.via == conexiones.VIA_CABLE:
            return await _respaldar_por_cable(conexion, args)

    if args.hidraw is not None:
        verificar_nodo_dongle(args.hidraw)
        path = args.hidraw
    else:
        path = find_config_hidraw()

    # **RDWR aunque esto solo lea**, y no es un descuido: un pedido de lectura
    # es una transferencia **OUT** -`build_read_frame()`, opcode 0xA0-, asi que
    # sin poder escribir no hay nada que leer. `O_RDONLY` vale para los flujos
    # que no piden nada: el modo `listen` del puente y `medir-hibernacion.py`,
    # que escuchan el latido espontaneo. Dos auditorias marcaron esto como
    # defecto, dos veces; queda dicho aca para no volver a
    # discutirlo en la tercera.
    canal = HidrawChannel(path)
    canal.open()
    device = Device(canal)
    canal.start_reading(asyncio.get_running_loop(), device.alimentar)

    print(f"leyendo {path} (mové el mouse para que el enlace responda)...")
    try:
        respaldo = await tomar_respaldo(canal, device,
                                        macros_extra=args.macro_id)
    finally:
        canal.close()

    return _guardar(respaldo, args)


async def _respaldar_por_cable(conexion, args) -> int:
    """El mismo respaldo, por el cable. Solo pedidos de lectura."""
    device = cable.abrir(conexion, solo_lectura=True)
    print(f"{conexion.describir()}")
    print(f"leyendo {device.path} por cable (no hace falta mover el mouse)...")
    try:
        respaldo = await tomar_respaldo(device, device,
                                        macros_extra=args.macro_id)
    finally:
        device.close()
    return _guardar(respaldo, args)


def _guardar(respaldo: dict, args) -> int:
    faltan = [k for k, v in respaldo["comandos"].items() if v is None]
    salida = args.salida
    if salida is None:
        carpeta = lugares.respaldos()
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        salida = carpeta / f"{marca}.json"
    # Leer el mouse cuesta minutos y depende de que el enlace acompañe: no se
    # puede perder el resultado porque falte una carpeta.
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(respaldo, indent=2, ensure_ascii=False))
    print(f"\nguardado en {salida}")

    # **Un respaldo que se contradice se guarda igual, pero se dice.** El
    # perfil completo embebe a rate, dpi, luz y botones, asi que un estado trae
    # dos copias de esos bytes; si difieren, una de las dos lecturas vino mal.
    # Se guarda porque tirarlo perdería minutos de lectura y porque la copia
    # buena puede servir para mirarlo; lo que no se puede es usarlo de linea de
    # base sin saberlo. **Paso de verdad** (2026-09-20): un respaldo salio con
    # el bloque de rate sangrado, el diff contra el siguiente dijo "la tasa
    # cambio", y la tasa no se habia tocado.
    malas = sesion.incoherencias(respaldo)
    if malas:
        print("\nOJO: este respaldo SE CONTRADICE a si mismo, asi que una de "
              "las lecturas vino mal:")
        for linea in malas:
            print(f"  {linea}")
        print("  No sirve de linea de base ni de referencia para un diff: "
              "repetilo. Queda guardado para poder mirarlo.")

    mudos = [k for k, v in (respaldo.get("macros") or {}).items() if v is None]
    if mudos and respaldo.get("via") == conexiones.VIA_CABLE:
        # El pedido del macro por cable esta LEIDO del helper, no visto en el
        # bus: si no contesta, es la primera cosa que mirar.
        print(f"\nOJO: por cable no contesto el macro {', '.join(mudos)}. Su "
              "pedido esta LEIDO del helper y nunca se vio en el bus: por cable "
              "ese macro no se puede escribir hasta mirarlo.")
    if faltan and respaldo.get("via") == conexiones.VIA_CABLE:
        # Por cable no hay radio que pierda pedidos: un comando que no vuelve
        # es uno cuyo pedido el mouse no atiende. Rate, dpi y luz tienen el
        # suyo visto en el bus; los otros estan LEIDOS del helper.
        nombres = ", ".join(p.CMD_NAMES.get(int(k), k) for k in faltan)
        print(f"\nOJO: por cable no contesto {nombres}. No es el enlace: por "
              "cable no hay radio. Si es uno de los pedidos LEIDOS del helper "
              "(version, botones, perfil completo), es que el mouse no lo "
              "atiende asi, y hay que mirarlo antes de escribir por cable.")
        return 2
    if faltan:
        print(f"\nOJO: {len(faltan)} comando(s) sin respuesta. Un respaldo "
              "incompleto NO sirve como linea de base: repetilo moviendo el "
              "mouse.")
        return 2
    return 0


if __name__ == "__main__":
    # Cortar a mano una lectura que esta esperando al enlace es normal, no un
    # accidente: hasta salia por un traceback de asyncio de
    # treinta lineas que tapaba lo que el respaldo si habia leido.
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n  cortado a mano. No se escribio nada: esto solo lee.",
              file=sys.stderr)
        raise SystemExit(130)
