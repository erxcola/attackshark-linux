#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Lee -y SOLO lee- el canal de configuracion del mouse **por cable**.

**Historica**: es la que midio que el mouse no contesta sin el pedido `0xA0`.
El respaldo por cable de verdad, con el pedido, lo hace
`driver/scripts/respaldar.py` (ver `driver/src/linshark/cable.py`).

Por cable el X8 Pro es otro dispositivo USB (`1d57:2126`) y su canal de
configuracion **no es** el del dongle: en vez de un Output Report de 63 bytes,
la interfaz 2 declara veinticinco **Feature Reports** en la Usage Page 0x0B,
con ids que son los mismos numeros que los comandos del dongle (4 dpi, 5 luz,
6 rate, 8 botones, 9 macro...) y tamaños **parecidos pero distintos**.

**Lo que el helper oficial hace por este camino esta LEIDO** de su binario
(`dev/models/attackshark-x8pro/docs/protocolo.md`, "El canal por cable"): el report es el mismo bloque
que viaja adentro de la trama del dongle -`[cmd, sizeTotalData, perfil,
campos..., checksum interno]`-, sin el `04 L 00` de afuera ni su checksum, y
los largos que declara el mouse son justo ese bloque **sin el relleno** del
final. Esta herramienta es la que lo mide: si el checksum interno cierra sobre
lo que devuelve el mouse, el layout es ese.

    dev/herramientas/leer-por-cable.py              # los que el helper lee
    dev/herramientas/leer-por-cable.py --id 6       # solo ese
    dev/herramientas/leer-por-cable.py --guardar dev/models/attackshark-x8pro/respaldos/cable.json

**Por que esto es distinto de escribir, y por que se puede correr:**

  * no manda **ninguna** trama al endpoint vendor: hace `GET_REPORT(Feature)`,
    que es una peticion de lectura estandar de USB HID;
  * pide **solo los reports que el helper oficial pide** (`LEE_EL_HELPER`, con
    la direccion de cada llamada en su binario) **y que el propio mouse
    declara**, con el tamaño que el descriptor dice. Los otros dieciseis ids
    del descriptor -`0x07`, `0x10`, `0xA0`, `0x22`..`0x2E`- el driver oficial
    no los lee nunca, y pedirlos seria mandarle al mouse algo que nadie le mando;
  * **no manda el pedido de lectura `0xA0`** que el helper manda antes de cada
    `GET` (`[a0, cmd, sub, 00, perfil, 00, 00, 00]`): ese viaja como
    `SET_REPORT`, que es el sentido de escritura. Asi que lo que se mide aca es
    si el mouse contesta el bloque **sin** que se lo pidan. **Y no contesta**
    (MEDIDO, `dev/models/attackshark-x8pro/respaldos/cable-primera-lectura.json`): los ocho dieron
    timeout, a 5 s cada uno;
  * el nodo se abre en **solo lectura** (`O_RDONLY`), asi que ni un bug puede
    escribir por aca, y el ioctl de escritura de features no aparece en este
    archivo -ni su nombre-. `dev/tests/evidencia.py` lo verifica leyendo el
    archivo, asi que agregarlo pone el test en rojo a proposito.

Aun asi **es trafico que ninguna captura muestra**, y por eso lo corre el
usuario y no el asistente, como todo lo que toca el mouse (ver
`dev/docs/metodo.md`).

Lo que se saca de aca es el paso 1 de la Etapa 3 para el modo cable: sin poder
leer no hay respaldo, y sin respaldo no se escribe nada. **Escribir por cable
sigue sin tener camino**: lo leido del binario dice que bytes manda el helper,
pero no que pone Windows en el cable -el largo de cada `SET_REPORT`, por
ejemplo- y eso solo lo dice una captura del driver oficial configurando por
cable (`dev/models/attackshark-x8pro/docs/captura-kvm.md`), que es la Etapa 2.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "driver" / "src"))

from linshark import conexiones   # noqa: E402
from linshark import estructuras as est   # noqa: E402
from linshark import protocol as p        # noqa: E402

#: `HIDIOCGFEATURE(len)`, armado a mano: el `_IOC` de Linux con direccion
#: lectura+escritura (el buffer va y vuelve), tipo 'H' y numero 0x07. El
#: hermano que escribe -numero 0x06- **no esta en este archivo a proposito**:
#: por cable no hay nada medido para escribir.
_IOC_WRITE, _IOC_READ = 1, 2


def _hidiocgfeature(largo: int) -> int:
    return (((_IOC_READ | _IOC_WRITE) << 30) | (largo << 16)
            | (ord("H") << 8) | 0x07)


#: Los reports que el helper oficial lee por cable (`connectionMethod` 0x80),
#: con la direccion del `hid_get_feature_report` de cada uno en
#: `WebDriver.exe` (sha256 `0eea3fef…`). LEIDO, no medido: son los ocho
#: comandos de la tabla de `sub` del dongle y ninguno mas. Del resto de los ids
#: que el mouse declara, el driver oficial no pide ninguno.
LEE_EL_HELPER = {
    0x04: 0x4137DA,   # dpi
    0x05: 0x4132BC,   # iluminacion
    0x06: 0x412CDA,   # report rate
    0x08: 0x413CFA,   # botones
    0x09: 0x40FC0E,   # macro
    0x0A: 0x40F654,   # perfil completo
    0x0B: 0x40EF67,   # version de firmware
    0x0C: 0x40E919,   # (sin nombre)
}


def reports_del_descriptor(ruta: Path) -> list[tuple[int, int]]:
    """`[(report_id, bytes)]` de los Feature Reports que el mouse declara.

    Se parsea el descriptor del propio dispositivo, que el kernel publica en
    sysfs. **Es una de las dos listas** que tienen que nombrar un id para que
    se lo pida; la otra es `LEE_EL_HELPER` (ver `a_pedir`).
    """
    crudo = ruta.read_bytes()
    i = 0
    rid = cuenta = tamaño = None
    salida: list[tuple[int, int]] = []
    while i < len(crudo):
        cabeza = crudo[i]
        largo = cabeza & 3
        tipo = (cabeza >> 2) & 3
        etiqueta = cabeza >> 4
        valor = int.from_bytes(crudo[i + 1:i + 1 + largo], "little")
        i += 1 + largo
        if tipo == 1 and etiqueta == 8:            # Report ID
            rid = valor
        elif tipo == 1 and etiqueta == 9:          # Report Count
            cuenta = valor
        elif tipo == 1 and etiqueta == 7:          # Report Size
            tamaño = valor
        elif tipo == 0 and etiqueta == 11:         # Main: Feature
            if rid is not None and cuenta and tamaño:
                bytes_ = cuenta * tamaño // 8
                if (rid, bytes_) not in salida:
                    salida.append((rid, bytes_))
    return salida


def a_pedir(declarados: list[tuple[int, int]], ids: list[int] | None = None
            ) -> tuple[list[tuple[int, int]], list[tuple[int, str]]]:
    """Que reports se piden, y por que no los demas.

    Un id se pide si **las dos** fuentes lo nombran: el descriptor del mouse
    -que dice que existe y cuanto mide- y el helper oficial -que dice que el
    driver de verdad lo lee-. `ids` achica la lista, nunca la agranda.
    """
    candidatos = [(i, l) for i, l in declarados if i in LEE_EL_HELPER]
    rechazados: list[tuple[int, str]] = []
    if ids:
        declarados_ids = {i for i, _ in declarados}
        for i in sorted(set(ids)):
            if i not in LEE_EL_HELPER:
                rechazados.append((i, "el helper oficial no lo lee nunca"))
            elif i not in declarados_ids:
                rechazados.append((i, "el mouse no lo declara"))
        candidatos = [(i, l) for i, l in candidatos if i in ids]
    return candidatos, rechazados


def leer_feature(fd: int, report_id: int, largo: int) -> bytes:
    """`GET_REPORT(Feature)` de ese id. No escribe nada."""
    buf = bytearray(largo + 1)
    buf[0] = report_id
    leidos = fcntl.ioctl(fd, _hidiocgfeature(len(buf)), buf, True)
    return bytes(buf[:leidos]) if leidos > 0 else b""


def _parecido_conocido(report_id: int, datos: bytes) -> str:
    """Si el bloque se parece a uno de los del dongle, lo dice. Sin afirmar.

    Compara **solo el byte de tamaño y el checksum interno**, que es lo unico
    que se puede chequear sin haber medido nada. El layout que se prueba es el
    que dice el helper: `[cmd, sizeTotalData, perfil, campos..., checksum]`, o
    sea que los datos -lo que `estructuras` decodifica- arrancan en el byte 2.
    Antes se miraba desde el byte 1, que suponia un report sin el byte de
    tamaño, y con ese corrimiento el checksum no podia cerrar nunca.

    Si cierra, el layout es ese y el decodificador sirve tal cual; si no
    cierra, no se sabe cual es -no que este mal-.
    """
    nombre = p.CMD_NAMES.get(report_id)
    if nombre is None:
        return ""
    if datos and not any(datos[1:]):
        return ("vino en cero: puede que el mouse solo lo llene despues del "
                "pedido de lectura 0xA0 que manda el helper, y que esto no manda")
    tamaño = datos[1] if len(datos) > 1 else None
    cuerpo = datos[2:]                     # desde el perfil, como el dongle
    esperado_tamaño = p.READ_SUB.get(report_id)
    nota_tamaño = ""
    if tamaño is not None and esperado_tamaño is not None:
        nota_tamaño = (f"; el byte de tamaño dice {tamaño}, "
                       f"por el dongle es {esperado_tamaño}")
    try:
        fin = est.fin_de_campos(report_id)
    except KeyError:
        return (f"es el numero del comando «{nombre}», cuya estructura no "
                f"conocemos ni por el dongle{nota_tamaño}")
    if len(cuerpo) < fin + 2:
        return (f"es el numero del comando «{nombre}», y trae {len(cuerpo)} B "
                f"desde el perfil: por el dongle los campos y el checksum "
                f"ocupan {fin + 2}{nota_tamaño}")
    esperado = est.checksum_interno(report_id, cuerpo)
    trae = int.from_bytes(cuerpo[fin:fin + 2], "big")
    if esperado == trae:
        return (f"es «{nombre}» y **el checksum interno cierra** "
                f"({esperado:#06x}): el layout es el del dongle{nota_tamaño}")
    return (f"es el numero de «{nombre}», pero el checksum interno no "
            f"cierra ({esperado:#06x} contra {trae:#06x}): el layout es "
            f"otro{nota_tamaño}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", type=lambda x: int(x, 0), action="append",
                    metavar="N", help="solo ese report (se puede repetir)")
    ap.add_argument("--guardar", type=Path, metavar="RUTA",
                    help="guarda lo leido en un json, como los respaldos")
    args = ap.parse_args()

    por_cable = [c for c in conexiones.buscar()
                 if c.via == conexiones.VIA_CABLE]
    if not por_cable:
        print("No hay ningun mouse de esta familia enchufado por cable.",
              file=sys.stderr)
        print("Esto lee el canal del CABLE; para el dongle esta "
              "driver/scripts/respaldar.py", file=sys.stderr)
        return 1
    cable = por_cable[0]
    # La interfaz de configuracion es la misma numero 2 que en el dongle, pero
    # el canal de adentro es otro. La baranda es que este nodo sea el del
    # producto del cable: mandarle esto al dongle no tendria sentido.
    nodo = cable.nodo(2)
    if nodo is None:
        print(f"el mouse por cable esta en {cable.puerto} pero no encuentro "
              "su interfaz 2", file=sys.stderr)
        return 1
    print(f"{cable.describir()}")
    print(f"canal: {nodo.path} (solo lectura)")

    sysfs = conexiones.SYS_HIDRAW / nodo.path.name / "device" / \
        "report_descriptor"
    declarados = reports_del_descriptor(sysfs)
    pedidos, rechazados = a_pedir(declarados, args.id)
    for report_id, motivo in rechazados:
        print(f"id {report_id:#04x}: no se pide, {motivo}", file=sys.stderr)
    print(f"el descriptor declara {len(declarados)} Feature Report(s); "
          f"el helper lee {len(LEE_EL_HELPER)}; pido {len(pedidos)}\n")

    try:
        fd = os.open(nodo.path, os.O_RDONLY)
    except PermissionError:
        print(f"sin permiso sobre {nodo.path}. La regla de udev cubre el "
              "dongle y el cable; si falta, sudo driver/scripts/"
              "instalar-udev.sh", file=sys.stderr)
        return 1

    leidos: dict[str, dict] = {}
    try:
        for report_id, largo in pedidos:
            try:
                datos = leer_feature(fd, report_id, largo)
            except OSError as exc:
                # Se guarda tambien lo que fallo: un json sin el bloque y sin
                # el motivo no distingue "no contesto" de "no se pidio".
                print(f"id {report_id:#04x} ({largo:3d} B): no contesto "
                      f"({exc.strerror})")
                leidos[str(report_id)] = {"largo": largo,
                                          "error": exc.strerror}
                continue
            print(f"id {report_id:#04x} ({largo:3d} B): {datos.hex()}")
            nota = _parecido_conocido(report_id, datos)
            if nota:
                print(f"    {nota}")
            leidos[str(report_id)] = {"largo": largo, "datos": datos.hex()}
    finally:
        os.close(fd)

    if args.guardar:
        args.guardar.write_text(json.dumps({
            "cuando": datetime.now().isoformat(timespec="seconds"),
            "maquina": socket.gethostname(),
            "via": "cable",
            "puerto": cable.puerto,
            "usb": f"{cable.vendor:04x}:{cable.producto:04x}",
            "features": leidos,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nguardado en {args.guardar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
