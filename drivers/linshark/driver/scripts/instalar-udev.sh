#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Instala la regla de udev que da acceso de usuario al canal de configuracion
# del Attack Shark X8 Pro. Correr como root (sudo o pkexec).
set -euo pipefail

REGLA="70-attackshark-x8pro.rules"
ORIGEN="$(dirname "$(readlink -f "$0")")/../models/attackshark-x8pro/udev/$REGLA"
DESTINO="/etc/udev/rules.d/$REGLA"

if [[ $EUID -ne 0 ]]; then
    echo "hay que correrlo como root:  sudo $0" >&2
    exit 1
fi
if [[ ! -f "$ORIGEN" ]]; then
    echo "no encuentro $ORIGEN" >&2
    exit 1
fi

rm -f /etc/udev/rules.d/99-attackshark-x8pro.rules   # nombre viejo
install -m 0644 "$ORIGEN" "$DESTINO"
echo "instalada en $DESTINO"

udevadm control --reload-rules
# --action=add es obligatorio. La accion por defecto de udevadm trigger es
# "change", y con esa los permisos de un nodo /dev/hidraw* que ya existe NO se
# reaplican: el script termina bien y el usuario se queda sin acceso hasta que
# desenchufa y vuelve a enchufar el dongle.
udevadm trigger --action=add --subsystem-match=hidraw
echo "reglas recargadas"
