#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Los nombres de los macros, que el mouse no guarda y la aplicacion si.

El bloque de un macro son 111 bytes decodificados enteros y **no hay campo de
nombre**: el soft de Windows guarda los suyos en un archivo propio
(`ms_13/macro.data`). O sea que los nombres son cosa del cliente. Esta
herramienta es el lado nuestro de eso, y **no toca el mouse**: solo lee y
escribe `~/.config/linshark/macros.json`.

    driver/scripts/nombres-de-macro.py                          # los que hay
    driver/scripts/nombres-de-macro.py --poner 17 "copiar y pegar"
    driver/scripts/nombres-de-macro.py --borrar 17
    driver/scripts/nombres-de-macro.py --archivo /otro/lado.json --poner 1 "prueba"

Los ids son los del mouse, que los lista `driver/scripts/respaldar.py`. Ponerle
nombre a un id que el mouse no tiene se permite -el nombre puede venir antes
que el macro-, pero el rango si se valida: si el id no le sirve al mouse, el
nombre no le sirve a nadie.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from linshark import nombres as mod_nombres   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archivo", type=Path, metavar="RUTA",
                    help=f"donde viven los nombres (por defecto "
                         f"{mod_nombres.ruta_por_defecto()})")
    ap.add_argument("--poner", nargs=2, metavar=("ID", "NOMBRE"),
                    help="le pone nombre a un macro")
    ap.add_argument("--borrar", type=int, metavar="ID",
                    help="le saca el nombre a un macro")
    args = ap.parse_args()

    if args.poner and args.borrar is not None:
        print("--poner o --borrar, no los dos", file=sys.stderr)
        return 2

    lib = mod_nombres.NombresDeMacro(args.archivo)
    if lib.problema:
        # Se avisa y se sigue: sin nombres la aplicacion anda igual, y lo que
        # no se hace es escribir encima de un archivo que no se pudo leer.
        print(f"  [!] no pude leer {lib.problema}", file=sys.stderr)

    if args.poner:
        crudo, nombre = args.poner
        try:
            macro_id = int(crudo)
        except ValueError:
            print(f"{crudo!r} no es un id de macro", file=sys.stderr)
            return 2
        try:
            lib.poner(macro_id, nombre)
            lib.guardar()
        except (ValueError, RuntimeError) as exc:
            print(exc.args[0], file=sys.stderr)
            return 1
        print(f"  {lib.describir(macro_id)}")
        print(f"  guardado en {lib.ruta}")
        return 0

    if args.borrar is not None:
        try:
            lib.borrar(args.borrar)
            lib.guardar()
        except (ValueError, RuntimeError) as exc:
            print(exc.args[0], file=sys.stderr)
            return 1
        print(f"  el macro {args.borrar} quedo sin nombre")
        return 0

    todos = lib.todos()
    if not todos:
        print(f"  no hay nombres guardados ({lib.ruta})")
        print("  Los ids que tiene el mouse los lista driver/scripts/respaldar.py")
        return 0
    print(f"  {lib.ruta}")
    for macro_id, nombre in sorted(todos.items()):
        print(f"    {macro_id:>3}  {nombre}")
    print("\n  El mouse no guarda estos nombres: son de esta maquina. Si el "
          "mouse\n  se configura con el soft de Windows, los nombres no "
          "viajan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
