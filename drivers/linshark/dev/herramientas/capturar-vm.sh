#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
# Una captura, una accion. El procedimiento esta en `dev/models/attackshark-x8pro/docs/captura-kvm.md`.
#
#   sudo dev/herramientas/capturar-vm.sh web  luz-rojo
#   sudo dev/herramientas/capturar-vm.sh soft luz-rojo
#   sudo dev/herramientas/capturar-vm.sh --cable web rate-500
#
# El primer argumento dice de donde sale el cambio -- `web` (la pagina de
# szslxd-tech.com + WebDriver.exe) o `soft` (ATTACK SHARK X8 SOFT.exe) -- y el
# segundo describe que se toco. La etiqueta no es decoracion: `dev/models/attackshark-x8pro/docs/capturas-w/reporteW.md`
# advierte que la igualdad byte a byte solo vale contra un frame del **mismo**
# setting, asi que la captura tiene que decir cual fue.
#
# Al cortar con Ctrl-C: escribe el .txt con lo que se toco (sin esa nota la
# captura no se puede interpretar dentro de un mes) y corre el analisis.
#
# `--cable` captura el otro camino: el mouse enchufado por cable (`1d57:2126`)
# y pasado a la VM en vez del dongle. Es otro protocolo -Feature Reports por el
# endpoint de control- y por eso las capturas salen con el prefijo `cable-` y
# no se mezclan con las del dongle.
#
# Solo lee. usbmon es un tap pasivo del USB core; esto no le manda un byte al
# mouse. Quien escribe es el driver oficial adentro de la VM.
set -euo pipefail

VENDOR=1d57
PRODUCT=fa65
CABLE=2126
# Los ids de arriba son del X8 Pro, y las capturas van a su carpeta. Antes de
# `models/` esto escribia en `dev/docs/capturas-w`, que desde la mudanza por
# modelo ya no era donde estaban las demas, y el `mkdir -p` de abajo lo tapaba.
MODELO=attackshark-x8pro

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
destino="$repo/models/$MODELO/docs/capturas-w"

pedido="$*"
via=dongle
if [ "${1:-}" = "--cable" ]; then
    via=cable
    shift
fi

if [ $# -lt 2 ]; then
    echo "uso: sudo $0 [--cable] <web|soft> <que-se-toco>" >&2
    echo "ej:  sudo $0 web luz-rojo" >&2
    echo "     sudo $0 --cable web rate-500" >&2
    exit 1
fi

case "$1" in
    web|soft) fuente="$1" ;;
    *) echo "el primer argumento tiene que ser 'web' o 'soft', no '$1'" >&2
       exit 1 ;;
esac
etiqueta="$2"

if [ "$(id -u)" -ne 0 ]; then
    echo "usbmon necesita root: sudo $0 $pedido" >&2
    exit 1
fi

command -v tcpdump >/dev/null 2>&1 || {
    echo "falta tcpdump; correr primero: sudo dev/herramientas/preparar-captura-vm.sh" >&2
    exit 1
}

if [ "$via" = dongle ]; then
    # La lista de `dev/models/attackshark-x8pro/docs/captura-kvm.md`: el mouse por cable usa Feature
    # Reports, que son otro protocolo, y ademas con el cable puesto el mouse
    # deja de hablar por el dongle. Una captura mezclada no sirve de referencia.
    if lsusb -d "$VENDOR:$CABLE" >/dev/null 2>&1; then
        echo "AVISO: veo el mouse por cable ($VENDOR:$CABLE) enchufado." >&2
        echo "  Para capturar el dongle, desenchufalo. Para capturar el" >&2
        echo "  cable: sudo $0 --cable $fuente $etiqueta" >&2
        exit 1
    fi
    buscado="$VENDOR:$PRODUCT"
    que="el dongle"
else
    buscado="$VENDOR:$CABLE"
    que="el mouse por cable"
fi

# Sigue enumerado en el host aunque QEMU lo tenga tomado: el passthrough le
# saca el driver, no lo desenchufa.
linea="$(lsusb -d "$buscado" | head -1)" || true
if [ -z "$linea" ]; then
    echo "no veo $que ($buscado). Esta enchufado?" >&2
    exit 1
fi
bus="$(echo "$linea" | sed -E 's/^Bus 0*([0-9]+).*/\1/')"
iface="usbmon$bus"

[ -e "/dev/$iface" ] || {
    echo "no existe /dev/$iface; correr: sudo dev/herramientas/preparar-captura-vm.sh" >&2
    exit 1
}

if pgrep -f "linshark" >/dev/null 2>&1; then
    echo "AVISO: hay un linshark corriendo. Cerralo: dos procesos hablandole" >&2
    echo "  al mismo /dev/hidraw se pisan (dev/models/attackshark-x8pro/docs/captura-kvm.md)." >&2
    exit 1
fi

mkdir -p "$destino"
if [ "$via" = cable ]; then
    base="$destino/cable-$fuente-$etiqueta"
else
    base="$destino/$fuente-$etiqueta"
fi
if [ -e "$base.pcap" ]; then
    base="$base-$(date +%H%M%S)"
fi

echo "$via : $linea"
echo "captura: $iface  (el bus $bus entero, no solo $que)"
echo "archivo: ${base#"$repo"/}.pcap"
echo
if [ "$fuente" = web ]; then
    cliente="la pagina (web)"
else
    cliente="el soft nativo (ATTACK SHARK X8 SOFT.exe)"
fi
echo "Adentro de la VM: abri $cliente, toca UN solo control y guarda."
echo "Espera dos segundos y corta con Ctrl-C."
echo "Mover el mouse lo menos posible: a 8 kHz el movimiento engorda el archivo."
echo

tcpdump -i "$iface" -w "$base.pcap" || true

echo
if [ ! -s "$base.pcap" ]; then
    echo "no se grabo nada" >&2
    exit 1
fi

# La nota que pide dev/models/attackshark-x8pro/docs/captura-kvm.md.
echo "== la nota =="
# **El cliente se pregunta, no se supone.** El `web` o `soft` de la linea de
# comandos lo escribe quien arma el comando, y el 2026-09-17 seis capturas
# salieron `cable-web-*` con el usuario usando el soft: todo lo que se leyo de
# ellas se le atribuyo a la web hasta que el lo aclaro. Si la respuesta es la
# otra, los archivos se renombran antes de escribir la nota.
read -r -p "que abriste en la VM, web o soft? [$fuente]  " abierto </dev/tty \
    || abierto=""
case "${abierto:-$fuente}" in
    web|soft) ;;
    *) echo "'$abierto' no es web ni soft; queda '$fuente', revisar la nota" >&2
       abierto="$fuente" ;;
esac
if [ "${abierto:-$fuente}" != "$fuente" ]; then
    fuente="$abierto"
    nombre="$(basename "$base" | sed -E "s/^(cable-)?(web|soft)-/\1$fuente-/")"
    nuevo="$(dirname "$base")/$nombre"
    if [ -e "$nuevo.pcap" ]; then
        nuevo="$nuevo-$(date +%H%M%S)"
    fi
    mv "$base.pcap" "$nuevo.pcap"
    base="$nuevo"
    echo "renombrada: ${base#"$repo"/}.pcap"
fi
read -r -p "que valor exacto pusiste?  " valor </dev/tty || valor=""
read -r -p "version de firmware que muestra el driver?  " firmware </dev/tty || firmware=""

{
    echo "fuente:   $fuente"
    echo "que:      $etiqueta"
    echo "valor:    ${valor:-<COMPLETAR>}"
    echo "firmware: ${firmware:-<COMPLETAR>}"
    echo "fecha:    $(date -Is)"
    echo "via:      $via ($buscado)"
    echo "captura:  host Linux, usbmon $iface, VM de Windows con $que"
    echo "          pasado por USB passthrough (dev/models/attackshark-x8pro/docs/captura-kvm.md)"
} > "$base.txt"

# Los archivos quedan de root; que los pueda leer quien corrio el sudo.
if [ -n "${SUDO_UID:-}" ]; then
    chown "$SUDO_UID:${SUDO_GID:-$SUDO_UID}" "$base.pcap" "$base.txt"
fi

echo
echo "== analisis =="
"$repo/herramientas/leer-captura-usb.py" "$base.pcap"
