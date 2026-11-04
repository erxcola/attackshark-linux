#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Devuelve un bloque del mouse al valor exacto que tiene un respaldo.

Es la vuelta de `respaldar.py`, que antes no existia: se podia guardar "que
habia antes" y no se podia volver a eso.

    driver/scripts/restaurar-bloque.py --respaldo antes.json --comando luz
    driver/scripts/restaurar-bloque.py --respaldo antes.json --comando luz --solo-probar

**Para que hace falta escribir un bloque entero, si estan los campos sueltos.**
Los codificadores de un campo -`escribir_reposo_ligero()`,
`escribir_parametros_luz()`- tocan su byte y **copian el resto del bloque que
leyeron**. Si el bloque que tiene el mouse quedo mal, cada escritura de un
campo arrastra los otros y `estructuras.fuera_de_rango()` la corta, con razon:
el mouse queda trabado en el estado malo, porque no hay campo suelto que lo
saque. La salida es escribir el bloque entero de una vez, que es lo que hace
esto.

Paso de verdad el 2026-09-20, por cable: una relectura de cmd 5 vino podrida,
`escribir_reposo_ligero()` la copio de vuelta y el mouse quedo con hibernacion
128 min y respuesta 0. Ver `dev/models/attackshark-x8pro/docs/bitacora.md`.

**No manda bytes crudos.** Los bytes salen de un respaldo de este mouse y de
ningun otro lado: no hay opcion para tipearlos, ni la va a haber. Y antes de
mandarlos se los juzga con la misma baranda que juzga a cualquier escritura.

**Solo los comandos cuyo formato de lectura es el de escritura.** cmd 8 y cmd 9
no lo son -los slots 4, 5 y 6 se permutan, y el checksum interno del macro
vuelve invertido (las dos cosas MEDIDAS, ver `CMDS_QUE_NO_VUELVEN_IGUAL`)- asi
que copiarles el bloque leido escribiria otra cosa. Para esos estan los
codificadores de `primera-escritura.py`. Y la tasa va por `cambiar-rate.py`,
que toca un solo comando: escribirla por la Etapa 3 se deshace sola (`AGENTS.md`).

Corre la Etapa 3 entera, igual que `primera-escritura.py`: respaldo completo,
escritura, relectura y veredicto. Anda por el dongle y por cable.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from linshark import cable  # noqa: E402
from linshark import conexiones  # noqa: E402
from linshark import estructuras  # noqa: E402
from linshark import protocol as p  # noqa: E402
from linshark import sesion  # noqa: E402
from linshark.device import Device  # noqa: E402
from linshark.hidraw import (  # noqa: E402
    HidrawChannel, find_config_hidraw, verificar_nodo_dongle,
)

# **Los que se pueden restaurar copiando, y por que no estan los otros.** Un
# bloque leido solo sirve de escritura cuando los dos formatos coinciden; para
# cmd 8 y cmd 9 no coinciden, y la tasa no va por este camino.
COMANDOS = {"dpi": p.CMD_DPI, "luz": p.CMD_LIGHTING}

# Los que alguien va a pedir igual, con la razon a mano en vez de un
# "comando invalido" que no dice donde ir.
NO_SE_RESTAURAN = {
    "botones": "los slots 4, 5 y 6 se permutan entre lectura y escritura "
               "(MEDIDO), asi que copiar el bloque leido escribiria otra cosa. "
               "Va por primera-escritura.py --comando botones",
    "macro": "el checksum interno vuelve invertido del mouse (MEDIDO), asi que "
             "el bloque leido no es el que se escribe. Va por "
             "primera-escritura.py --comando macro",
    "rate": "escribir la tasa por la Etapa 3 se deshace sola: la Etapa 3 "
            "verifica releyendo y arriba de 1000 Hz la relectura no llega. Va "
            "por cambiar-rate.py --valor N",
}


def bloque_del_respaldo(respaldo: dict, cmd: int) -> bytes:
    """Los datos de `cmd` en el respaldo, o levanta diciendo que falto.

    Devuelve la parte de datos, **sin `[cmd, sizeTotalData]`**: los dos bytes
    de adelante los pone `sesion.aplicar()` con el `sub` de la lectura viva,
    que es la que manda sobre el largo.
    """
    entrada = (respaldo.get("comandos") or {}).get(str(cmd))
    if entrada is None:
        nombre = p.CMD_NAMES.get(cmd, cmd)
        raise SystemExit(
            f"el respaldo no tiene el bloque de {nombre} (cmd {cmd}). Un "
            "respaldo al que le falta el comando que se quiere restaurar no "
            "sirve: hay que tomar uno donde ese bloque haya contestado.")
    return bytes.fromhex(entrada["datos"])


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--respaldo", type=Path, required=True,
                    help="el JSON de respaldar.py del que sale el bloque")
    ap.add_argument("--comando", required=True,
                    help=f"cual bloque: {', '.join(sorted(COMANDOS))}")
    ap.add_argument("--hidraw", type=Path,
                    help="por defecto se busca en sysfs")
    ap.add_argument("--solo-probar", action="store_true",
                    help="dice que escribiria y no toca el mouse")
    args = ap.parse_args()

    if args.comando in NO_SE_RESTAURAN:
        print(f"'{args.comando}' no se restaura copiando el bloque leido: "
              f"{NO_SE_RESTAURAN[args.comando]}")
        return 2
    if args.comando not in COMANDOS:
        print(f"comando desconocido '{args.comando}'. Los que se pueden "
              f"restaurar: {', '.join(sorted(COMANDOS))}")
        return 2
    cmd = COMANDOS[args.comando]
    nombre = p.CMD_NAMES.get(cmd, cmd)

    respaldo = json.loads(args.respaldo.read_text())
    datos = bloque_del_respaldo(respaldo, cmd)

    # **El bloque del respaldo pasa por la misma baranda que cualquier
    # escritura.** Un respaldo tomado despues de que algo se rompiera tiene
    # guardado lo roto, y restaurarlo seria escribir la basura a proposito.
    imposible = estructuras.fuera_de_rango(cmd, datos)
    if imposible is not None:
        print(f"el bloque de {nombre} que tiene ese respaldo YA esta mal "
              f"({imposible}).")
        print("No lo escribo: restaurarlo seria dejar el mouse como esta. "
              "Hace falta un respaldo anterior al problema.")
        return 1

    print(f"respaldo: {args.respaldo}  ({respaldo.get('fecha', 'sin fecha')}, "
          f"via {respaldo.get('via', 'dongle')})")
    print(f"bloque a restaurar: {nombre} (cmd {cmd}), {len(datos)} B")
    legible = estructuras.describir(cmd, datos)
    if legible:
        print(f"  {legible}")
    print(f"  {datos.hex(' ')}")

    if args.solo_probar:
        print("\n--solo-probar: no se toca el mouse.")
        return 0

    if args.hidraw is None:
        try:
            conexion = conexiones.elegir()
        except conexiones.NoHayCanal:
            conexion = None       # que lo explique find_config_hidraw()
        if conexion is not None and conexion.via == conexiones.VIA_CABLE:
            return await _restaurar(cable.abrir(conexion), cmd, datos,
                                    cerrar=True, por_cable=True,
                                    conexion=conexion)

    if args.hidraw is not None:
        verificar_nodo_dongle(args.hidraw)
        path = args.hidraw
    else:
        path = find_config_hidraw()
    canal = HidrawChannel(path)
    canal.open()
    device = Device(canal)
    canal.start_reading(asyncio.get_running_loop(), device.alimentar)
    print(f"\npor el dongle, {path} (mové el mouse: el enlace pierde la mitad "
          "de los pedidos con el mouse quieto)")
    try:
        return await _escribir(device, cmd, datos)
    finally:
        canal.close()


async def _restaurar(device, cmd, datos, *, cerrar, por_cable, conexion) -> int:
    print(f"\n{conexion.describir()}")
    print(f"por cable, {device.path} (no hace falta mover el mouse)")
    try:
        return await _escribir(device, cmd, datos)
    finally:
        if cerrar:
            device.close()


async def _escribir(device, cmd: int, datos: bytes) -> int:
    """La Etapa 3, con el bloque del respaldo de codificador."""
    pasos = []

    def avisar(texto: str) -> None:
        clave, _, detalle = texto.partition("|")
        pasos.append(clave)
        if detalle:
            print(f"      {detalle}")
        elif clave == sesion.AVISO_RESPALDO:
            print("[1/6] respaldo fresco antes de escribir")
        elif clave == sesion.AVISO_RELECTURA:
            print("[6/6] releyendo para ver si el mouse lo aplico")

    async def confirmar(bloque, _trama):
        # **Sin prompt**, igual que `primera-escritura.py`: el consentimiento es
        # el comando. Lo que no se saca es el registro de la trama exacta.
        trama = p.build_write_frame(bloque)
        print(f"\n[3/6] escribo el bloque del respaldo, entero")
        print(f"      {trama[:trama[1]].hex(' ')}")
        print("\n[5/6] escribiendo...")
        return True

    resultado = await sesion.aplicar(
        device, cmd=cmd, codificar=lambda _leido: datos,
        confirmar=confirmar, al_avisar=avisar, bajar_la_tasa=True)

    print(f"\nresultado: {resultado.motivo}")
    print(f"  {resultado.explicacion}")
    # **Un veredicto tiene que decir QUE cambio.** `cambio-de-mas` sin la lista
    # es el mismo reproche que este proyecto le hace al cliente oficial: avisar
    # que se movio algo y no decir que. Y aca importa el doble, porque el
    # bloque de version -que no se puede escribir- sirve de testigo: si aparece
    # en esta lista, lo que fallo es una LECTURA, no la escritura.
    if resultado.antes and resultado.despues:
        difs = sesion.diferencias(resultado.antes, resultado.despues)
        if difs:
            print("\nlo que cambio en el mouse:")
            for d in difs:
                print(f"  {d}")
        else:
            print("\nno se movio un byte")
    if resultado.veredicto is not None and resultado.veredicto.no_releidos:
        nombres = ", ".join(sorted(str(c) for c in
                                   resultado.veredicto.no_releidos))
        print(f"  OJO: no se releyeron {nombres}, asi que sobre esos no se "
              "afirma nada")
    return 0 if resultado.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
