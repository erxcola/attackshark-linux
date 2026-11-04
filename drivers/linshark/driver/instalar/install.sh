#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Instala LinShark, el configurador de ratones LXDDZ / Beken, en cualquier Linux.
#
#     sudo ./driver/instalar/install.sh
#     sudo ./driver/instalar/install.sh --prefijo /opt/linshark
#     ./driver/instalar/install.sh --solo-probar     # no toca nada, dice que haria
#
# Que hace, en orden, y por que:
#
#   1. comprueba que haya python3 >= 3.10 y el modulo venv;
#   2. copia el programa a PREFIJO (por defecto /opt/linshark);
#   3. arma un entorno virtual ahi adentro. **Si el sistema ya trae PySide6, lo
#      usa** (--system-site-packages) en vez de bajar 100+ MB otra vez;
#   4. instala la **regla de udev**, que es lo que le da acceso al canal de
#      configuracion sin ser root, y la aplica a los nodos que ya estan;
#   5. deja `linshark-gui` y `linshark` en /usr/local/bin y una entrada en el
#      menu de aplicaciones.
#
# No usa el gestor de paquetes de ninguna distro a proposito: lo unico que pide
# es python3 y, para la ventana, PySide6 -del sistema o de pip-.
#
# Para deshacerlo: `sudo ./uninstall.sh`, que borra exactamente esto.
set -euo pipefail

PREFIJO="${PREFIJO:-/opt/linshark}"
BIN="${BIN:-/usr/local/bin}"
APLICACIONES="${APLICACIONES:-/usr/share/applications}"
ICONOS="${ICONOS:-/usr/share/icons/hicolor/scalable/apps}"
SOLO_PROBAR=0

AQUI="$(dirname "$(readlink -f "$0")")"
DRIVER="$(dirname "$AQUI")"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefijo) PREFIJO="$2"; shift 2 ;;
        --solo-probar) SOLO_PROBAR=1; shift ;;
        -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "no entiendo la opcion $1" >&2; exit 2 ;;
    esac
done

decir() { printf '  %s\n' "$*"; }
paso()  { printf '\n%s\n' "$*"; }

correr() {
    if [[ $SOLO_PROBAR -eq 1 ]]; then
        decir "(solo probar) $*"
    else
        "$@"
    fi
}

# --- 1. lo que hace falta ---------------------------------------------------
paso "Comprobando lo que hace falta"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "no encuentro python3. Instalalo con el gestor de tu distro." >&2
    exit 1
fi
VERSION="$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "python $VERSION es muy viejo: hace falta 3.10 o mas nuevo." >&2
    exit 1
fi
decir "python $VERSION en $(command -v "$PYTHON")"

if ! "$PYTHON" -c 'import venv' 2>/dev/null; then
    echo "falta el modulo venv de python (paquete python3-venv en Debian/Ubuntu)." >&2
    exit 1
fi

# **Si el sistema ya tiene PySide6, se usa el del sistema.** Bajarlo de pip son
# mas de 100 MB y casi todas las distros lo empaquetan.
CON_SISTEMA=""
if "$PYTHON" -c 'import PySide6' 2>/dev/null; then
    decir "PySide6 del sistema: se usa ese"
    CON_SISTEMA="--system-site-packages"
else
    decir "sin PySide6 en el sistema: se instala en el entorno virtual"
fi

# **Que este todo lo que se va a copiar, ANTES de copiar nada, y tambien en
# `--solo-probar`.** Un ensayo que no puede fallar por un archivo que no esta
# da confianza falsa: paso el 2026-09-20, cuando la regla de udev se movio a
# `attackshark-x8pro/udev/` -lo del X8 Pro va en su carpeta- y aca quedo un
# camino viejo. El ensayo salio limpio porque la linea que lo usaba estaba
# adentro del `if` de instalar de verdad, y la instalacion real murio a la
# mitad, con el programa ya copiado y sin regla ni lanzadores.
REGLA="70-attackshark-x8pro.rules"
ORIGEN_REGLA="$DRIVER/models/attackshark-x8pro/udev/$REGLA"
FALTANTES=()
for origen in "$DRIVER/src" "$DRIVER/scripts" "$DRIVER/requirements.txt" \
              "$DRIVER/models" "$ORIGEN_REGLA" \
              "$AQUI/linshark.desktop" "$AQUI/LinShark.svg"; do
    [[ -e "$origen" ]] || FALTANTES+=("$origen")
done
if (( ${#FALTANTES[@]} )); then
    echo "" >&2
    echo "no esta lo que hay que instalar:" >&2
    printf '    %s\n' "${FALTANTES[@]}" >&2
    exit 1
fi
decir "estan los archivos y carpetas que se copian"

if [[ $SOLO_PROBAR -eq 0 && $EUID -ne 0 ]]; then
    echo "" >&2
    echo "hay que correrlo como root para instalar en $PREFIJO y $BIN:" >&2
    echo "    sudo $0" >&2
    echo "(o mira que haria, sin tocar nada:  $0 --solo-probar)" >&2
    exit 1
fi

# --- 2. el programa ---------------------------------------------------------

paso "Instalando el programa en $PREFIJO"
correr install -d "$PREFIJO"
# `udev/` es donde quedaba la regla antes de `models/`: se borra para que una
# instalacion vieja no deje dos copias.
correr rm -rf "$PREFIJO/src" "$PREFIJO/scripts" "$PREFIJO/models" "$PREFIJO/udev"
correr cp -r "$DRIVER/src" "$PREFIJO/src"
correr cp -r "$DRIVER/scripts" "$PREFIJO/scripts"
# **Con la misma forma que en el repo**, porque `scripts/instalar-udev.sh` -el
# que corre el boton de la ventana- busca la regla en `../models/<modelo>/udev/`
# y tiene que encontrarla tanto aca como en el repo.
correr cp -r "$DRIVER/models" "$PREFIJO/models"
correr cp "$DRIVER/requirements.txt" "$PREFIJO/requirements.txt"
# El manual y sus traducciones: el castellano es el original, y las otras
# dicen que version tradujeron (`test_las_traducciones_no_quedaron_atrasadas`).
correr rm -f "$PREFIJO"/README*.md
for leeme in "$DRIVER"/README*.md; do
    [[ -f "$leeme" ]] && correr cp "$leeme" "$PREFIJO/$(basename "$leeme")"
done
# Las capturas y el icono que muestra ese README, para que se vea igual
# instalado: el README los pide en `docs/img/` y en `instalar/`.
correr rm -rf "$PREFIJO/docs" "$PREFIJO/instalar"
if [[ -d "$DRIVER/docs" ]]; then
    correr cp -r "$DRIVER/docs" "$PREFIJO/docs"
fi
correr install -D -m 0644 "$AQUI/LinShark.svg" "$PREFIJO/instalar/LinShark.svg"
# El codigo compilado de otra corrida no tiene por que viajar.
if [[ $SOLO_PROBAR -eq 0 ]]; then
    find "$PREFIJO" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
fi
decir "copiado"

# --- 3. el entorno virtual --------------------------------------------------
paso "Armando el entorno virtual"
if [[ $SOLO_PROBAR -eq 0 ]]; then
    "$PYTHON" -m venv $CON_SISTEMA "$PREFIJO/venv"
    "$PREFIJO/venv/bin/python" -m pip install --quiet --upgrade pip
    # websockets es del puente; PySide6 solo si no estaba en el sistema.
    "$PREFIJO/venv/bin/python" -m pip install --quiet "websockets>=13.0"
    if [[ -z "$CON_SISTEMA" ]]; then
        decir "bajando PySide6 (son varios cientos de MB la primera vez)…"
        "$PREFIJO/venv/bin/python" -m pip install --quiet "PySide6>=6.6"
    fi
    if ! "$PREFIJO/venv/bin/python" -c 'import PySide6' 2>/dev/null; then
        echo "el entorno quedo sin PySide6: la ventana no va a abrir." >&2
        echo "Instalalo con tu distro (python-pyside6 / python3-pyside6) y volve a correr esto." >&2
        exit 1
    fi
else
    decir "(solo probar) venv en $PREFIJO/venv con websockets${CON_SISTEMA:+ y PySide6 del sistema}"
fi
decir "listo"

# --- 4. la regla de udev ----------------------------------------------------
# **Es lo que hace que el programa ande sin ser root.** Sin esto el nodo
# /dev/hidraw del canal de configuracion queda root:root 0600.
paso "Instalando la regla de udev"
if [[ $SOLO_PROBAR -eq 0 ]]; then
    rm -f "/etc/udev/rules.d/99-attackshark-x8pro.rules"    # nombre viejo
    install -m 0644 "$ORIGEN_REGLA" "/etc/udev/rules.d/$REGLA"
    udevadm control --reload-rules
    # --action=add es obligatorio: con "change" -la accion por defecto- los
    # permisos de un nodo que ya existe NO se reaplican, y el usuario se queda
    # sin acceso hasta desenchufar el dongle.
    udevadm trigger --action=add --subsystem-match=hidraw
else
    decir "(solo probar) /etc/udev/rules.d/$REGLA + udevadm trigger"
fi
decir "instalada y aplicada"

# --- 5. los lanzadores y el menu --------------------------------------------
paso "Dejando los lanzadores"
if [[ $SOLO_PROBAR -eq 0 ]]; then
    install -d "$BIN"
    cat > "$BIN/linshark-gui" <<EOF
#!/bin/sh
# La ventana de LinShark.
exec "$PREFIJO/venv/bin/python" "$PREFIJO/src/linshark_ui/__main__.py" "\$@"
EOF
    chmod 0755 "$BIN/linshark-gui"
    cat > "$BIN/linshark" <<EOF
#!/bin/sh
# El puente para la pagina oficial. La aplicacion propia es linshark-gui.
cd "$PREFIJO/src" || exit 1
exec "$PREFIJO/venv/bin/python" -m linshark "\$@"
EOF
    chmod 0755 "$BIN/linshark"
    install -d "$APLICACIONES" "$ICONOS"
    install -m 0644 "$AQUI/linshark.desktop" "$APLICACIONES/linshark.desktop"
    # En el tema de iconos va en minuscula, que es la convencion y lo que pide
    # el `Icon=linshark` del .desktop.
    install -m 0644 "$AQUI/LinShark.svg" "$ICONOS/linshark.svg"
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database "$APLICACIONES" 2>/dev/null || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -q "$(dirname "$(dirname "$(dirname "$ICONOS")")")" 2>/dev/null || true
else
    decir "(solo probar) $BIN/linshark-gui, $BIN/linshark, $APLICACIONES/linshark.desktop"
fi
decir "linshark-gui y linshark en $BIN"

paso "Listo."
decir "Abrí la aplicación con:  linshark-gui"
decir "O desde el menú: «LinShark»"
decir ""
decir "Si el programa dice que no puede abrir el nodo, desenchufá y volvé a"
decir "enchufar el dongle: la regla de udev se aplica al conectarlo."
decir "Para desinstalar:  sudo $AQUI/uninstall.sh"
