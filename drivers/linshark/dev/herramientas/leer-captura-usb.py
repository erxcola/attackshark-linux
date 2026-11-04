#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Extrae del trafico USB las tramas que el driver oficial le escribe al mouse.

Entiende los dos formatos que nos importan, sin depender de tshark:

  * **USBPcap** (linktype 249), que es lo que sale de capturar en Windows.
  * **usbmon** de Linux (linktypes 189 y 220), que es lo que sale de capturar
    en el host mientras el driver corre adentro de una VM con el dongle
    pasado por USB passthrough.

De cada Interrupt OUT con datos muestra la trama, valida el checksum y, lo
que de verdad interesa, **compara contra lo que armaria `build_write_frame()`**.
Que las dos columnas den identico es el criterio de la Etapa 2 de
`dev/docs/metodo.md`: si nuestro constructor reproduce byte a byte lo que mando el
driver oficial, escribir eso es tan seguro como que lo haga el driver.

**Y el mouse por cable**, que no usa Interrupt: su canal de configuracion son
Feature Reports, que viajan por el endpoint de control como `SET_REPORT` y
`GET_REPORT`. De esos muestra el pedido de lectura `0xA0` contra
`build_cable_read_request()`, cada bloque leido y escrito con su checksum
interno, y **que cambio cada escritura respecto de la ultima lectura** del
mismo comando. Solo en capturas usbmon, que es lo que sale de la VM.

    dev/herramientas/leer-captura-usb.py dev/models/attackshark-x8pro/docs/capturas-w/*.pcap
    dev/herramientas/leer-captura-usb.py --todo captura.pcap     # tambien los IN

Este script solo lee archivos. No abre el mouse ni escribe nada.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "driver" / "src"))

from linshark import estructuras  # noqa: E402
from linshark import protocol as p  # noqa: E402

# linktypes que sabemos leer
LINK_USBPCAP = 249
LINK_USBMON = 189
LINK_USBMON_MMAP = 220

TRANSFER_INTERRUPT = 1   # el mismo valor en USBPcap y en usbmon
TRANSFER_CONTROL = 2

# Los pedidos de clase HID (HID 1.11, seccion 7.2) con los que viaja el canal
# del cable: `bmRequestType` 0x21 / 0xA1, y el tipo de report en el byte alto
# de `wValue` (3 = Feature) con el Report ID en el bajo.
HID_GET_REPORT = 0x01
HID_SET_REPORT = 0x09
REPORT_FEATURE = 3

# La cabecera de usbmon mide 48 bytes en el linktype 189 y 64 en el 220, que
# le agrega cuatro campos al final. El setup va en el mismo lugar en los dos.
CABECERA_USBMON = {LINK_USBMON: 48, LINK_USBMON_MMAP: 64}


class CapturaNoSoportada(Exception):
    pass


def _paquetes(path: Path):
    """(timestamp, bytes) de cada paquete, mas el linktype del archivo."""
    d = path.read_bytes()
    if len(d) < 24:
        raise CapturaNoSoportada(f"{path}: demasiado corto para ser un pcap")
    magic, = struct.unpack_from("<I", d, 0)
    if magic == 0xA1B2C3D4:
        endian, escala = "<", 1e6        # microsegundos
    elif magic == 0xA1B23C4D:
        endian, escala = "<", 1e9        # nanosegundos
    elif magic == 0xD4C3B2A1:
        endian, escala = ">", 1e6
    elif magic == 0x4D3CB2A1:
        endian, escala = ">", 1e9
    elif magic in (0x0A0D0D0A,):
        raise CapturaNoSoportada(
            f"{path}: es un pcapng. Guardalo como pcap clasico "
            "(en Wireshark: Archivo -> Guardar como -> Wireshark/tcpdump pcap)"
        )
    else:
        raise CapturaNoSoportada(f"{path}: no parece un pcap (magic {magic:08x})")

    link, = struct.unpack_from(endian + "I", d, 20)
    off = 24
    paquetes = []
    while off + 16 <= len(d):
        ts, tsub, incl, _orig = struct.unpack_from(endian + "IIII", d, off)
        off += 16
        paquetes.append((ts + tsub / escala, d[off:off + incl]))
        off += incl
    return link, paquetes


def _decodificar_usbpcap(pkt: bytes):
    if len(pkt) < 27:
        return None
    hlen, = struct.unpack_from("<H", pkt, 0)
    dev, = struct.unpack_from("<H", pkt, 19)
    ep = pkt[21]
    transfer = pkt[22]
    dlen, = struct.unpack_from("<I", pkt, 23)
    return dev, ep, transfer, pkt[hlen:hlen + dlen]


def _decodificar_usbmon(pkt: bytes):
    # struct usbmon_packet, 64 bytes de cabecera
    if len(pkt) < 64:
        return None
    tipo = pkt[8]          # 'S'ubmit / 'C'allback / 'E'rror
    transfer = pkt[9]
    ep = pkt[10]
    dev = pkt[11]
    len_cap, = struct.unpack_from("<I", pkt, 36)
    # En un OUT los datos viajan en el Submit; en un IN, en el Callback.
    entrada = bool(ep & 0x80)
    if (entrada and tipo != ord("C")) or (not entrada and tipo != ord("S")):
        return None
    return dev, ep, transfer, pkt[64:64 + len_cap]


def transferencias(path: Path, solo_out: bool = True):
    link, paquetes = _paquetes(path)
    if link == LINK_USBPCAP:
        decodificar, origen = _decodificar_usbpcap, "USBPcap (Windows)"
    elif link in (LINK_USBMON, LINK_USBMON_MMAP):
        decodificar, origen = _decodificar_usbmon, "usbmon (Linux)"
    else:
        raise CapturaNoSoportada(
            f"{path}: linktype {link}. Sabemos leer USBPcap (249) y "
            "usbmon (189/220)"
        )
    salida = []
    for t, pkt in paquetes:
        r = decodificar(pkt)
        if r is None:
            continue
        dev, ep, transfer, datos = r
        if transfer != TRANSFER_INTERRUPT or not datos:
            continue
        if solo_out and (ep & 0x80):
            continue
        salida.append((t, dev, ep, bytes(datos)))
    return origen, len(paquetes), salida


def features(path: Path) -> list[dict]:
    """Los Feature Reports de la captura: el canal de configuracion del cable.

    Cada `SET_REPORT` lleva sus datos en el Submit, detras del setup; cada
    `GET_REPORT` los trae en el Callback, que se empareja con su Submit por el
    id de URB. Del Callback de un `SET_REPORT` sale el `status`: 0 es que el
    mouse lo recibio, y -32 (`EPIPE`) que lo rechazo con un STALL.

    Solo usbmon: en USBPcap las transferencias de control llevan otra cabecera
    por etapa, y las capturas del cable salen de la VM, o sea del host Linux.
    """
    link, paquetes = _paquetes(path)
    cabecera = CABECERA_USBMON.get(link)
    if cabecera is None:
        return []
    salida: list[dict] = []
    en_vuelo: dict[bytes, dict] = {}
    for t, pkt in paquetes:
        if len(pkt) < cabecera or pkt[9] != TRANSFER_CONTROL:
            continue
        urb, tipo, dev = pkt[0:8], pkt[8], pkt[11]
        status, = struct.unpack_from("<i", pkt, 28)
        len_cap, = struct.unpack_from("<I", pkt, 36)
        datos = bytes(pkt[cabecera:cabecera + len_cap])
        if tipo == ord("S") and pkt[14] == 0:           # con setup
            bm, pedido, valor, _indice, largo = struct.unpack_from(
                "<BBHHH", pkt, 40)
            if valor >> 8 != REPORT_FEATURE:
                continue
            if bm == 0x21 and pedido == HID_SET_REPORT:
                x = {"t": t, "dev": dev, "sentido": "SET",
                     "id": valor & 0xFF, "pedido": largo, "datos": datos,
                     "status": None}
            elif bm == 0xA1 and pedido == HID_GET_REPORT:
                x = {"t": t, "dev": dev, "sentido": "GET",
                     "id": valor & 0xFF, "pedido": largo, "datos": b"",
                     "status": None}
            else:
                continue
            salida.append(x)
            en_vuelo[urb] = x
        elif tipo in (ord("C"), ord("E")) and urb in en_vuelo:
            x = en_vuelo.pop(urb)
            x["status"] = status
            if x["sentido"] == "GET":
                x["datos"] = datos
    return salida


def _checksum_interno(cmd: int, bloque: bytes) -> str:
    """Si el checksum interno cierra sobre `[cmd, size, perfil, ...]`."""
    try:
        fin = estructuras.fin_de_campos(cmd)
    except KeyError:
        return "sin estructura conocida"
    cuerpo = bloque[2:]
    if len(cuerpo) < fin + 2:
        return f"corto: {len(cuerpo)} B desde el perfil, hacen falta {fin + 2}"
    esperado = estructuras.checksum_interno(cmd, cuerpo)
    trae = int.from_bytes(cuerpo[fin:fin + 2], "big")
    return "ok" if esperado == trae else f"MAL ({trae:#06x}, da {esperado:#06x})"


def _reintentados(transfs: list[dict]) -> None:
    """Marca los `SET_REPORT` rechazados que se repitieron y pasaron.

    MEDIDO en las capturas del cable: el mouse a veces rechaza un `SET_REPORT`
    con STALL, y el mismo `SET`, repetido unos 205 ms despues, pasa. Eso no es
    un problema de la trama -es la misma- y contarlo como tal seria una falsa
    alarma. Lo que si es un problema es un rechazo que nadie reintento, o un
    reintento que tambien fallo.
    """
    sets = [x for x in transfs if x["sentido"] == "SET"]
    for a, b in zip(sets, sets[1:]):
        if a["status"] not in (None, 0) and b["id"] == a["id"] \
                and b["datos"] == a["datos"] and b["status"] == 0:
            a["reintentado"] = True


def _campos_que_cambian(cmd: int, antes: bytes, despues: bytes) -> str:
    """Los campos que difieren entre dos bloques, por nombre."""
    if cmd == p.CMD_REPORT_RATE and len(antes) > 3 and len(despues) > 3:
        return (f"byte de rate {antes[3]:02x}->{despues[3]:02x}: por radio "
                f"{estructuras.report_rate_de(antes[2:])}->"
                f"{estructuras.report_rate_de(despues[2:])} Hz (nibble alto), "
                f"por cable {estructuras.report_rate_por_cable_de(antes[2:])}->"
                f"{estructuras.report_rate_por_cable_de(despues[2:])} Hz "
                "(nibble bajo)")
    a = estructuras.decodificar(cmd, antes[2:]) or {}
    b = estructuras.decodificar(cmd, despues[2:]) or {}
    nombres = [k for k in b if k != "_cola" and a.get(k) != b.get(k)]
    return ", ".join(nombres)


def _informar_macro(trozos: list[dict], conocido: dict) -> int:
    """Los trozos de un macro por cable, rearmados en el bloque de 111."""
    c0, c1 = trozos[0]["datos"], trozos[1]["datos"]
    bloque = (bytes([p.CMD_MACRO, 0x6F, c0[2]]) + c0[4:] + c1[4:])[:0x6F]
    print(f"    los dos trozos rearmados -> bloque de {len(bloque)} B: "
          f"{bloque.hex()}")
    legible = estructuras.describir(p.CMD_MACRO, bloque[2:])
    if legible:
        print(f"    interpretado: {legible}")
    problemas = 0
    try:
        nuestros = p.build_cable_macro_reports(bloque)
    except ValueError as exc:
        print(f"    build_cable_macro_reports: {exc}")
        return 1
    igual = nuestros == [c0, c1]
    print(f"    build_cable_macro_reports(bloque) -> "
          f"{'IDENTICO' if igual else 'DIFIERE'}")
    if not igual:
        problemas += 1
    clave = ("macro", c0[2])
    antes = conocido.get(clave)
    if antes is not None and antes != bloque:
        cambios = [i for i, (x, y) in enumerate(zip(antes, bloque)) if x != y]
        print("    cambia respecto del ultimo estado conocido en los bytes "
              + ", ".join(f"[{i}] {antes[i]:02x}->{bloque[i]:02x}"
                          for i in cambios))
    conocido[clave] = bloque
    return problemas


def informar_cable(transfs: list[dict], conocido: dict | None = None) -> int:
    """El canal del cable, transferencia por transferencia.

    `conocido` guarda el ultimo bloque visto de cada comando -leido o escrito
    con exito- y se puede compartir entre capturas: asi una escritura de la
    captura siguiente se compara contra el estado en que quedo la anterior.
    """
    if not transfs:
        return 0
    conocido = {} if conocido is None else conocido
    _reintentados(transfs)
    print(f"  --- Feature Reports (el canal del cable): {len(transfs)}")
    problemas = 0
    trozos: list[dict] = []
    for x in transfs:
        rid, datos = x["id"], x["datos"]
        nombre = p.CMD_NAMES.get(rid, f"report 0x{rid:02x}")
        estado = {None: "sin callback", 0: "ok"}.get(
            x["status"], f"status {x['status']}")
        print(f"\n  [{x['t']:.3f}] dev={x['dev']} {x['sentido']}_REPORT(Feature)"
              f" id=0x{rid:02x} pedido={x['pedido']} B -> {len(datos)} B "
              f"[{estado}]")
        if datos:
            print(f"    datos : {datos.hex()}")
        if x["status"] not in (None, 0):
            if x.get("reintentado"):
                print("    rechazado con STALL; el mismo SET se repitio y paso")
                continue
            print("    OJO: el mouse no recibio este SET_REPORT, y no se "
                  "repitio")
            problemas += 1
            continue
        if rid == p.CABLE_READ_REPORT_ID:
            if x["sentido"] == "GET":
                listo = len(datos) > 1 and datos[1] == p.CABLE_READ_READY
                print(f"    estado del pedido: {'listo' if listo else 'NO listo'}")
                continue
            cmd = datos[1] if len(datos) > 1 else None
            print(f"    PEDIDO DE LECTURA de {p.CMD_NAMES.get(cmd, cmd)}")
            try:
                nuestro = p.build_cable_read_request(cmd)
            except (KeyError, TypeError) as exc:
                print(f"    build_cable_read_request: {exc}")
                continue
            igual = nuestro == datos
            print(f"    build_cable_read_request({cmd}) -> "
                  f"{'IDENTICO' if igual else 'DIFIERE'}")
            if not igual:
                print(f"       nuestro: {nuestro.hex()}")
                problemas += 1
            continue
        if not datos:
            continue
        if rid == p.CMD_MACRO and x["sentido"] == "SET" and len(datos) > 3 \
                and datos[1] == p.CABLE_MACRO_REPORT_LEN:
            # Un trozo de macro: se junta con el siguiente y se informa el
            # bloque entero. Leer cada trozo como si fuera el bloque da un
            # "checksum mal" que no existe.
            print(f"    TROZO {datos[3]} del macro {datos[2]}")
            if datos[3] == 0:
                trozos = [x]
            elif trozos and datos[3] == len(trozos) \
                    and trozos[0]["datos"][2] == datos[2]:
                trozos.append(x)
            if len(trozos) == 2:
                problemas += _informar_macro(trozos, conocido)
                trozos = []
            continue
        tamaño = datos[1] if len(datos) > 1 else None
        print(f"    {'LECTURA' if x['sentido'] == 'GET' else 'ESCRITURA'} "
              f"{nombre}   sizeTotalData={tamaño}   "
              f"checksum interno: {_checksum_interno(rid, datos)}")
        legible = estructuras.describir(rid, datos[2:])
        if legible:
            print(f"    interpretado: {legible}")
        antes = conocido.get(rid)
        conocido[rid] = datos
        if x["sentido"] == "GET":
            continue
        # Una escritura: que cambio respecto del ultimo estado conocido. Es la
        # materia prima de la Etapa 2 -dos bloques que difieren en el campo
        # que se toco- y la forma de ver si el cliente oficial pisa algo mas.
        # Lo leido trae el relleno y lo escrito no: se compara lo que hay.
        if antes is None:
            print("    (no hay un estado anterior de este comando)")
            continue
        n = min(len(antes), len(datos))
        cambios = [i for i in range(n) if antes[i] != datos[i]]
        if cambios:
            print("    cambia respecto del ultimo estado conocido en los bytes "
                  + ", ".join(f"[{i}] {antes[i]:02x}->{datos[i]:02x}"
                              for i in cambios))
            campos = _campos_que_cambian(rid, antes, datos)
            if campos:
                print(f"    campos: {campos}")
        else:
            print("    identica al ultimo estado conocido: idempotente")
    print()
    return problemas


def informar(path: Path, solo_out: bool = True,
             conocido: dict | None = None) -> int:
    try:
        origen, total, transfs = transferencias(path, solo_out)
    except CapturaNoSoportada as exc:
        print(f"### {path.name}\n    {exc}\n")
        return 1

    print(f"### {path.name}   [{origen}, {total} paquetes]")
    cable = features(path)
    if not transfs and not cable:
        print("    ningun Interrupt ni Feature Report con datos. Se toco algun "
              "control durante la captura?\n")
        return 1

    problemas = 0
    pendientes = set()   # indices ya consumidos como continuacion de un bloque
    for i, (t, dev, ep, datos) in enumerate(transfs):
        if i in pendientes:
            continue
        sentido = "IN " if ep & 0x80 else "OUT"
        print(f"\n  [{t:.3f}] dev={dev} ep=0x{ep:02x} {sentido} "
              f"report de {len(datos)} B")
        if datos[0] != p.DEVICE_REPORT_ID:
            print(f"    Report ID {datos[0]}, no es el canal de configuracion "
                  f"({p.DEVICE_REPORT_ID}). Lo salteo.")
            continue

        largo = datos[1]
        if largo < 6 or largo > len(datos):
            print(f"    largo declarado {largo}, incoherente con el report")
            problemas += 1
            continue
        trama = datos[:largo]
        opcode = trama[2]
        cmd, sub = trama[3], trama[4]
        nombre = p.CMD_NAMES.get(cmd, f"cmd 0x{cmd:02x}")
        clase = {p.READ_OPCODE: "LEER", p.WRITE_OPCODE: "ESCRIBIR/respuesta"}.get(
            opcode, f"opcode 0x{opcode:02x}")

        # Un comando que no entra en un report se manda por bloques, y ahi
        # `largo` es el del trozo y no el del comando: la igualdad de siempre
        # no aplica y decir que "no cierra" seria una falsa alarma.
        por_bloques = (opcode == p.WRITE_OPCODE
                       and sub + p.WRITE_FRAME_OVERHEAD > p.WRITE_REPORT_LEN)
        cierra = ("por bloques, no entra en un report" if por_bloques
                  else f"largo == sizeTotalData + 5: {largo == sub + 5}")
        print(f"    trama : {trama.hex()}")
        print(f"    {clase} {nombre}   largo={largo}  sizeTotalData={sub}"
              f"   ({cierra})")
        print(f"    checksum: {'ok' if p.verify_frame(trama) else 'MAL'}")
        if any(datos[largo:]):
            print(f"    OJO: hay bytes no nulos despues de la trama: "
                  f"{datos[largo:].hex()}")

        if por_bloques:
            # El camino por bloques: el comando no entra en un report y el
            # driver oficial lo parte en trozos de 59 bytes, poniendo el
            # **numero de bloque** donde va el opcode (0, 1, ...). Sale del
            # trio de 0x40d612 del helper y quedo MEDIDO contra
            # `soft-macro-asignado.pcap`, que es la unica captura con cmd 9.
            trozos = [trama]
            j = i + 1
            while sum(len(x) - p.WRITE_FRAME_OVERHEAD for x in trozos) < sub \
                    and j < len(transfs):
                sig = transfs[j][3]
                if not sig or sig[0] != p.DEVICE_REPORT_ID or \
                        sig[2] != len(trozos):
                    break
                trozos.append(sig[:sig[1]])
                pendientes.add(j)
                j += 1
            bloque = b"".join(x[3:-2] for x in trozos)
            print(f"    {len(trozos)} trama(s) por bloques -> {len(bloque)} B")
            for extra in trozos[1:]:
                print(f"    sigue : {extra.hex()}")
                print("    checksum: "
                      f"{'ok' if p.verify_frame(extra) else 'MAL'}")
            nuestras = p.build_write_blocks(bloque)
            igual = nuestras == trozos
            print(f"    build_write_blocks(bloque) -> "
                  f"{'IDENTICO' if igual else 'DIFIERE'}")
            if not igual:
                for x in nuestras:
                    print(f"       nuestro: {x.hex()}")
                problemas += 1
            legible = estructuras.describir(cmd, bloque[2:])
            if legible:
                print(f"    interpretado: {legible}")
        elif opcode == p.WRITE_OPCODE:
            bloque = trama[3:-2]
            try:
                nuestra = p.build_write_frame(bloque)
            except ValueError as exc:
                print(f"    build_write_frame: {exc}")
                problemas += 1
            else:
                igual = nuestra == trama
                print(f"    build_write_frame(bloque) -> "
                      f"{'IDENTICO' if igual else 'DIFIERE'}")
                if not igual:
                    print(f"       nuestro: {nuestra.hex()}")
                    problemas += 1
            legible = estructuras.describir(cmd, trama[5:-2])
            if legible:
                print(f"    interpretado: {legible}")
    print()
    return problemas + informar_cable(cable, conocido)


def _primer_instante(path: Path) -> float:
    """El instante del primer paquete, para ordenar capturas."""
    try:
        _, paquetes = _paquetes(path)
    except (CapturaNoSoportada, OSError):
        return 0.0
    return paquetes[0][0] if paquetes else 0.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capturas", nargs="+", type=Path)
    ap.add_argument("--todo", action="store_true",
                    help="mostrar tambien las transferencias IN")
    args = ap.parse_args(argv)

    # En el orden en que se capturaron, no en el que las da el shell: el
    # estado conocido pasa de una captura a la siguiente, y con un glob
    # `rate-1000` viene antes que `rate-500`.
    problemas = 0
    conocido: dict = {}
    for path in sorted(args.capturas, key=_primer_instante):
        problemas += informar(path, solo_out=not args.todo, conocido=conocido)
    if problemas:
        print(f"{problemas} trama(s) que no reproducimos o que no cierran. "
              "Ver dev/docs/metodo.md antes de escribir nada.")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
