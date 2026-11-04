#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Prepara el host para la sesion de captura descrita en `dev/models/attackshark-x8pro/docs/captura-kvm.md`.
# Se corre UNA VEZ, como root.
#
# El metodo es el del documento: Windows adentro de la VM con el dongle pasado
# por USB, y la captura hecha desde el host con usbmon. El passthrough le saca
# el driver al dispositivo pero el trafico sigue cruzando el USB core del
# kernel de Linux, que es donde usbmon esta enganchado. Por eso no hay que
# instalar USBPcap adentro del guest.
#
# Lo que NO hace, a proposito: **no instala una regla de udev que le abra
# /dev/usbmon* a un grupo**. Eso le daria a ese grupo el trafico USB entero de
# la maquina, teclado incluido. Las capturas se corren con sudo, explicitas,
# una por sesion.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "esto necesita root: sudo $0" >&2
    exit 1
fi

echo "== tcpdump =="
if command -v tcpdump >/dev/null 2>&1; then
    echo "ya esta: $(command -v tcpdump)"
else
    echo "instalando tcpdump"
    # No todo el mundo esta en Arch. Se prueba el gestor que haya y, si no
    # se reconoce ninguno, se dice que instalar en vez de fallar con
    # "pacman: command not found".
    if command -v pacman >/dev/null; then
        pacman -S --needed --noconfirm tcpdump
    elif command -v apt-get >/dev/null; then
        apt-get install -y tcpdump
    elif command -v dnf >/dev/null; then
        dnf install -y tcpdump
    else
        echo "instalá tcpdump con el gestor de paquetes de tu distro" >&2
        exit 1
    fi
fi

echo
echo "== debugfs =="
if mount | grep -q ' /sys/kernel/debug '; then
    echo "montado"
else
    mount -t debugfs none /sys/kernel/debug
    echo "montado ahora"
fi

echo
echo "== modulo usbmon =="
if lsmod | grep -q '^usbmon'; then
    echo "ya cargado"
else
    modprobe usbmon
    echo "cargado"
fi

if [ ! -f /etc/modules-load.d/usbmon.conf ]; then
    echo "usbmon" > /etc/modules-load.d/usbmon.conf
    echo "queda cargandose al arranque (/etc/modules-load.d/usbmon.conf)"
else
    echo "ya estaba en /etc/modules-load.d/usbmon.conf"
fi

echo
echo "== interfaces de captura =="
ls /sys/kernel/debug/usb/usbmon/ >/dev/null 2>&1 || {
    echo "no existe /sys/kernel/debug/usb/usbmon/; usbmon no cargo bien" >&2
    exit 1
}
ls -l /dev/usbmon* 2>/dev/null || true

echo
echo "== dongle =="
lsusb -d 1d57:fa65 || echo "  no lo veo; enchufalo antes de capturar"

echo
echo "listo. Ahora, la sesion: dev/models/attackshark-x8pro/docs/captura-kvm.md"
echo "  sudo dev/herramientas/capturar-vm.sh web luz-rojo"
