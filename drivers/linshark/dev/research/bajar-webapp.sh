#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Baja el bundle de szslxd-tech.com a dev/research/webapp/ y verifica los hashes.
#
# El bundle es codigo propietario de un tercero: no se guarda en el repo, se
# guarda su huella. `webapp.sha256` fija exactamente que bytes se leyeron para
# escribir `docs/protocolo.md`, asi que una auditoria puede bajar lo mismo y
# comprobar que las citas siguen siendo de ese material.
#
# Si el sitio publicó una version nueva, la descarga falla el chequeo: eso no
# es un error del script, es que el bundle citado ya no es el que sirven. En
# ese caso hay que releer las citas contra la version nueva, no actualizar el
# manifiesto sin mirar.
set -euo pipefail

base="https://szslxd-tech.com/assets"
aqui="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$aqui"

# app.js es una copia local del bundle de entrada, que en el sitio se llama
# distinto (confirmado contra la captura del navegador de la Etapa W, que no se
# publica porque trae el bundle: 1530782 bytes).
entrada="index-CHmxtNQf.js"

mkdir -p webapp/chunks

faltan=0
while read -r _hash ruta; do
    [ -f "$ruta" ] && continue
    nombre="$(basename "$ruta")"
    [ "$ruta" = "webapp/app.js" ] && nombre="$entrada"
    echo "bajando $ruta"
    if ! curl -fsSL "$base/$nombre" -o "$ruta"; then
        echo "  FALLO: $base/$nombre" >&2
        rm -f "$ruta"
        faltan=$((faltan + 1))
    fi
done < <(grep -v '^#' webapp.sha256)

if [ "$faltan" -gt 0 ]; then
    echo "no se pudieron bajar $faltan archivos" >&2
fi

echo
echo "verificando contra webapp.sha256"
sha256sum -c webapp.sha256
