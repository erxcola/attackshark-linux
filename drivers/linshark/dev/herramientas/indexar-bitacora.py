#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Regenera el indice de `dev/models/attackshark-x8pro/docs/bitacora.md` a partir de sus encabezados.

La bitacora tiene 90 y pico de entradas y crece con cada sesion, asi que el
indice se desactualiza solo. Esto lo rearma: lee los `## ` del archivo y
reescribe **solo** el bloque del indice, entre el marcador de apertura y la
linea de guiones que lo cierra. El orden es el del archivo, que es el orden
en que pasaron las cosas.

No toca ninguna entrada. Y no toca el mouse: lee y escribe un archivo de texto.

    dev/herramientas/indexar-bitacora.py            # reescribe el indice
    dev/herramientas/indexar-bitacora.py --revisar  # dice si esta al dia, sin escribir
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BITACORA = (Path(__file__).resolve().parent.parent / "models" / "attackshark-x8pro"
            / "docs" / "bitacora.md")
INICIO = "## Indice\n"
FIN = "\n---\n"

# Lo que GitHub le saca a un encabezado para armar el ancla. Se mantiene en un
# solo lugar porque un enlace roto en un indice largo no se nota hasta que
# alguien lo usa.
ACENTOS = str.maketrans("áéíóúüñ", "aeiouun")
SOBRAN = "—–:,.()[]`\"'¿?¡!/\\"


def ancla(titulo: str) -> str:
    a = titulo.lower().translate(ACENTOS)
    for ch in SOBRAN:
        a = a.replace(ch, "")
    return "-".join(a.split())


def indice_de(texto: str) -> str:
    titulos = [t for t in re.findall(r"^## (.+)$", texto, re.M)
               if t.strip() != "Indice"]
    return "\n" + "\n".join(f"- [{t}](#{ancla(t)})" for t in titulos) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--revisar", action="store_true",
                    help="no escribe; devuelve 1 si el indice esta viejo")
    args = ap.parse_args(argv)

    texto = BITACORA.read_text()
    if INICIO not in texto or FIN not in texto:
        print("no encuentro el bloque del indice en dev/models/attackshark-x8pro/docs/bitacora.md",
              file=sys.stderr)
        return 2
    i = texto.index(INICIO) + len(INICIO)
    j = texto.index(FIN, i)

    nuevo = indice_de(texto)
    if texto[i:j] == nuevo:
        print("el indice esta al dia")
        return 0
    if args.revisar:
        print("el indice esta viejo: corré dev/herramientas/indexar-bitacora.py",
              file=sys.stderr)
        return 1
    BITACORA.write_text(texto[:i] + nuevo + texto[j:])
    print(f"indice regenerado: {nuevo.count('- [')} entradas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
