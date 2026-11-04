#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Extrae el software nativo de escritorio, para ver que opciones tiene que el
# WebDriver no expone.
#
# NO EJECUTA NADA DE WINDOWS. innoextract solo descomprime el blob del
# instalador Inno Setup (confirmado: "Inno Setup Setup Data (6.1.0)"), strings
# y objdump solo leen.
#
#   dev/herramientas/extraer-soft.sh ~/Descargas/"ATTACK SHARK X8 SOFT.exe" [destino]
#
# Es el hermano de extraer-helper.sh. Ese saca el helper del navegador; este
# saca el otro producto, que segun dev/models/attackshark-x8pro/docs/capturas-w/soft-todo.txt manda al menos
# un comando (0x0c) que la web nunca manda.
set -euo pipefail

INSTALADOR="${1:?uso: $0 <ATTACK SHARK X8 SOFT.exe> [destino]}"
DESTINO="${2:-./soft}"

SHA_ESPERADO="b54043ca726adf5d4aed061283472845efded61a3aef0fca8e7d983a05f3af66"
sha=$(sha256sum "$INSTALADOR" | cut -d' ' -f1)
if [[ "$sha" != "$SHA_ESPERADO" ]]; then
    echo "AVISO: el instalador no es el mismo del que salieron las capturas." >&2
    echo "  esperado: $SHA_ESPERADO" >&2
    echo "  este:     $sha" >&2
fi

IE="$(command -v innoextract || true)"
if [[ -z "$IE" ]]; then
    IE="$HOME/.local/share/lutris/runtime/innoextract-1.9-linux/innoextract"
fi
[[ -x "$IE" ]] || {
    echo "no encuentro innoextract. En Arch: sudo pacman -S innoextract" >&2
    exit 1
}

mkdir -p "$DESTINO"
"$IE" -e -s -d "$DESTINO" "$INSTALADOR"

echo
echo "== lo que salio =="
find "$DESTINO" -type f -printf "%10s  %p\n" | sort -rn | head -30

echo
echo "== skins de DuiLib (la lista de opciones de la UI vive aca) =="
# DuiLib describe cada ventana en XML. Si estan sueltos o en un .zip/.dat,
# leerlos da la lista completa de controles sin desensamblar una linea.
find "$DESTINO" \( -iname "*.xml" -o -iname "*.skin" -o -iname "*.zip" \
     -o -iname "*.dat" -o -iname "*.rc" \) -printf "  %p\n" | head -40

echo
echo "== dlls de HID =="
find "$DESTINO" -iname "*hid*" -printf "  %p\n" || true

echo
echo "Siguiente paso sugerido: buscar las tablas de comando en el binario"
echo "principal, igual que se hizo con el helper. El comando 0x0c ya esta"
echo "medido en dev/models/attackshark-x8pro/docs/capturas-w/soft-todo.txt; conviene buscar ESE valor."
