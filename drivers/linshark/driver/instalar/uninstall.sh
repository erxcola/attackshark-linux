#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Deshace lo que hizo install.sh, y nada mas.
#
#     sudo ./driver/instalar/uninstall.sh
#     sudo ./driver/instalar/uninstall.sh --prefijo /opt/linshark
#
# **No toca la configuracion del mouse.** Lo que el mouse tenga escrito se
# queda como esta: desinstalar el programa no es restaurar el hardware, y
# hacerlo por sorpresa seria justo lo que este proyecto le reprocha a los
# clientes oficiales. Si querias volver a los valores de fabrica, hacelo desde
# la aplicacion **antes** de desinstalarla.
#
# Tampoco borra lo que guardaste vos: los nombres de macro y la preferencia de
# idioma viven en ~/.config/linshark/, y la lectura de cada apertura y los
# respaldos en ~/.local/state/linshark/. Quedan ahi; se borran a mano.
set -euo pipefail

PREFIJO="${PREFIJO:-/opt/linshark}"
BIN="${BIN:-/usr/local/bin}"
APLICACIONES="${APLICACIONES:-/usr/share/applications}"
ICONOS="${ICONOS:-/usr/share/icons/hicolor/scalable/apps}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefijo) PREFIJO="$2"; shift 2 ;;
        -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "no entiendo la opcion $1" >&2; exit 2 ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    echo "hay que correrlo como root:  sudo $0" >&2
    exit 1
fi

decir() { printf '  %s\n' "$*"; }

echo "Sacando el programa"
rm -rf "$PREFIJO"
decir "$PREFIJO"
rm -f "$BIN/linshark-gui" "$BIN/linshark"
decir "$BIN/linshark-gui, $BIN/linshark"
rm -f "$APLICACIONES/linshark.desktop" "$ICONOS/linshark.svg"
decir "la entrada del menu y el icono"

echo "Sacando la regla de udev"
rm -f /etc/udev/rules.d/70-attackshark-x8pro.rules
rm -f /etc/udev/rules.d/99-attackshark-x8pro.rules
udevadm control --reload-rules
udevadm trigger --action=add --subsystem-match=hidraw
decir "quitada; el nodo vuelve a ser solo de root"

echo ""
echo "Listo. Lo que guardaste vos sigue en ~/.config/linshark/ (nombres de"
echo "macro, idioma), y los respaldos en ~/.local/state/linshark/. La"
echo "configuracion del mouse quedo como estaba."
