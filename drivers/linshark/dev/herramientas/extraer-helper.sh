#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Extrae el helper oficial de Windows y lo desensambla, para poder reproducir
# el analisis del que salio el formato de trama.
#
# NO EJECUTA NADA DE WINDOWS. innoextract solo descomprime el blob LZMA del
# instalador Inno Setup, y objdump solo lee.
#
#   dev/herramientas/extraer-helper.sh ~/Descargas/WebDriverSetup.exe [destino]
set -euo pipefail

INSTALADOR="${1:?uso: $0 <WebDriverSetup.exe> [destino]}"
DESTINO="${2:-./helper}"

SHA_ESPERADO="ec2e171e593f6219af1fca7bc8101bf6967347c0d34855d7bee69acaf6d3c4da"
sha=$(sha256sum "$INSTALADOR" | cut -d' ' -f1)
if [[ "$sha" != "$SHA_ESPERADO" ]]; then
    echo "AVISO: el instalador no es el mismo que se analizo." >&2
    echo "  esperado: $SHA_ESPERADO" >&2
    echo "  este:     $sha" >&2
    echo "  Los offsets de este documento pueden no coincidir." >&2
fi

# innoextract: paquete 'innoextract' en Arch, o el que trae Lutris.
IE="$(command -v innoextract || true)"
if [[ -z "$IE" ]]; then
    IE="$HOME/.local/share/lutris/runtime/innoextract-1.9-linux/innoextract"
fi
[[ -x "$IE" ]] || { echo "no encuentro innoextract" >&2; exit 1; }

mkdir -p "$DESTINO"
"$IE" -e -s -d "$DESTINO" "$INSTALADOR"

echo
echo "payload extraido en $DESTINO/app:"
sha256sum "$DESTINO"/app/* || true

echo
echo "desensamblando WebDriver.exe (unos 640k lineas)..."
objdump -d -M intel \
    --start-address=0x401000 --stop-address=0x5cf000 \
    "$DESTINO/app/WebDriver.exe" > "$DESTINO/WebDriver.asm"
echo "-> $DESTINO/WebDriver.asm"

echo
echo "sitios de llamada a hid_write (IAT en 0x5cfa00):"
grep -c "ds:0x5cfa00" "$DESTINO/WebDriver.asm" || true
echo "  de 12 bytes (lecturas)  -> ver 'push 0xc' antes de la llamada"
echo "  de 65 bytes (escrituras)-> ver 'push 0x41'"
