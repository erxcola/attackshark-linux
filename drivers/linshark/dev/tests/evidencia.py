#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Las afirmaciones del proyecto, contra la evidencia que las respalda.

**No prueba codigo: prueba que lo que el codigo afirma se sostiene.** Por eso
vive de este lado: lo que mira son los **respaldos versionados** -mediciones
contra el hardware ya hechas y guardadas- y los descriptores del propio mouse.
El otro lado, `driver/tests/`, prueba que el programa hace lo que dice.

    dev/tests/evidencia.py

Cinco cosas, y cada una tiene su historia:

  * **el perfil completo acompaña a todo cambio**: es la medicion en la que se
    apoya la relectura acotada del driver, verificada sobre los 139 respaldos;
  * **la tabla de fabrica no dice otra cosa que la evidencia**: se compara
    campo por campo contra el mouse leido antes de que el proyecto le
    escribiera nada;
  * **por cable solo se lee**: la herramienta del modo cable no puede escribir,
    y lo que pide lo nombran a la vez el descriptor del mouse y el helper;
  * **el cable mide el bloque del dongle sin su relleno**: lo que el largo
    declarado deja afuera es cero en todos los respaldos, y el checksum
    interno queda adentro;
  * **el lector de capturas entiende el cable**: los Feature Reports viajan
    por el endpoint de control, y una captura sintetica tiene que salir bien.

Si alguien agrega un respaldo que contradiga una de estas, esto se pone rojo y
la afirmacion deja de estar justificada. No son numeros copiados a un
comentario.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ.parent / "driver" / "src"))

# **Los tests no tocan las carpetas de quien los corre**: algunos scripts piden
# la de respaldos al importarse, y una prueba no escribe en el HOME de nadie.
import os  # noqa: E402
import tempfile as _tempfile  # noqa: E402
_CASA_DE_PRUEBA = _tempfile.mkdtemp(prefix="linshark-tests-")
os.environ["XDG_CONFIG_HOME"] = f"{_CASA_DE_PRUEBA}/config"
os.environ["XDG_STATE_HOME"] = f"{_CASA_DE_PRUEBA}/state"

from linshark import protocol as p     # noqa: E402
from linshark import sesion            # noqa: E402

#: El descriptor HID de la interfaz 2 del X8 Pro **por cable**, leido de sysfs
#: con el mouse enchufado. Es lo que el propio mouse declara: 25
#: Feature Reports en la Usage Page 0x0B, con ids que son los mismos numeros
#: que los comandos del dongle y **tamaños que no siempre coinciden** con los
#: de alla. En dpi y luz la diferencia es el relleno del dongle
#: (`test_el_cable_mide_el_bloque_sin_relleno`); que sea el mismo layout lo
#: dice el helper (LEIDO) y lo confirma recien una captura del driver oficial
#: configurando por cable.
DESCRIPTOR_DEL_CABLE = bytes.fromhex(
    "05010980a101850105011981298315002501950375018106950175058101c005"
    "0c0901a1018502150026800319002a8003751095018100c0050a0900a1018503"
    "1900290015002500750895048101c0050b0900a10185049533b1018505950cb1"
    "0185069508b10185079507b1018508953ab1018509953fb101850a9507b10185"
    "0b9507b101850c9505b10185109507b10185a09507b10185229583b101852395"
    "83b10185249507b1018525950cb10185269508b10185279507b10185289583b1"
    "018529956cb101852a9582b101852b9507b101852c9503b101852d9566b10185"
    "239582b101852e9504b101c0")


def test_el_perfil_acompana_a_todo_cambio(fallos: list[str]) -> None:
    """La medicion en la que se apoya la relectura acotada, sobre los respaldos.

    `evidencia.md` decia que el perfil completo embebe a los demas bloques, y
    lo tenia MEDIDO para **dos** comandos: rate y botones
. La relectura acotada lo usa como testigo para cuatro, asi que
 se lo verifico sobre los respaldos versionados, que son
    mediciones contra el hardware ya hechas y guardadas.

    Esta prueba **es** esa verificacion, y corre en cada tanda: si alguien
    agrega un respaldo que la contradiga, se pone roja y la relectura acotada
    deja de estar justificada. No es un numero copiado a un comentario.
    """
    import json

    carpeta = RAIZ / "models" / "attackshark-x8pro" / "respaldos"
    estados = []
    descartados = []
    for archivo in sorted(carpeta.glob("*.json")):
        try:
            d = json.loads(archivo.read_text())
        except Exception:                          # noqa: BLE001
            continue
        cmds = d.get("comandos") or {}
        if not cmds.get(str(p.CMD_PROFILE)):
            continue
        # **Un respaldo que se contradice no es evidencia de nada.** El perfil
        # y el bloque suelto traen dos copias de los mismos bytes; si difieren,
        # una de las dos lecturas vino mal, y contarlo como par mediria el
        # canal, no al mouse. Paso de verdad: `cable-restaurado.json` es una
        # lectura de cmd 5 sangrada con el buffer de cmd 6 (2026-09-20), y
        # comparada con su vecina dice "cambio la luz y el perfil no
        # acompaño", que es exactamente el agujero que esta prueba busca y
        # aca seria falso.
        if sesion.incoherencias(d):
            descartados.append(archivo.name)
            continue
        estados.append((archivo.name,
                        {k: v["datos"] for k, v in cmds.items() if v}))
    if descartados:
        print(f"       ({len(descartados)} respaldo(s) con lecturas que se "
              f"contradicen, fuera de la cuenta: {', '.join(descartados)})")

    if len(estados) < 20:
        fallos.append(f"solo {len(estados)} respaldos con perfil: la medicion "
                      "en la que se apoya la relectura acotada no se puede "
                      "rehacer")
        return

    perfil = str(p.CMD_PROFILE)
    pares = 0
    for (na, a), (nb, b) in zip(estados, estados[1:]):
        comunes = set(a) & set(b)
        dif = {k for k in comunes if a[k] != b[k]}
        if not dif:
            continue
        pares += 1
        otros = dif - {perfil}
        if dif == {perfil}:
            fallos.append(f"el perfil se movio solo entre {na} y {nb}: como "
                          "testigo da falsos positivos")
        if otros and perfil not in dif:
            nombres = ", ".join(sorted(otros))
            fallos.append(f"cambio {nombres} entre {na} y {nb} y el perfil no "
                          "acompaño: el testigo tiene un agujero")
    if pares < 20:
        fallos.append(f"solo {pares} pares con diferencias: poca base")


def test_el_perfil_embebe_donde_dice(fallos: list[str]) -> None:
    """`Perfil.perfil_embebe` se rehace contra los respaldos, cada tanda.

    El perfil completo **no tiene checksum interno** y es el testigo de toda
    escritura por el camino de la relectura acotada, asi que una lectura suya
    corrompida no la notaba nadie. Lo unico que lo cubre es que embebe a los
    otros bloques: un estado trae dos copias de esos bytes y tienen que
    coincidir (`sesion.incoherencias`).

    Los offsets salieron de estos respaldos, asi que aca se verifican contra
    ellos **en los dos sentidos**:

      1. cada tramo coincide en todos los respaldos sanos;
      2. cada tramo **toma varios valores distintos** entre respaldos. Sin
         esto, un tramo de bytes fijos coincidiria siempre sin verificar nada.
         La primera version de la tabla tenia justo eso en cmd 6: cuatro ceros
         que casaban por casualidad y no probaban nada;
      3. y detecta el que se sabe corrompido. Una baranda que nunca dice que
         no, no es una baranda.
    """
    import json

    from linshark import dispositivos, estructuras

    embebe = dispositivos.perfil_de(p.DEVICE_X8_PRO).perfil_embebe
    if not embebe:
        fallos.append("el perfil del X8 Pro no dice donde embebe a los bloques")
        return

    carpeta = RAIZ / "models" / "attackshark-x8pro" / "respaldos"
    estados = []
    for archivo in sorted(carpeta.glob("*.json")):
        try:
            d = json.loads(archivo.read_text())
        except Exception:                          # noqa: BLE001
            continue
        cmds = d.get("comandos") or {}
        bloques = {int(k): bytes.fromhex(v["datos"]) for k, v in cmds.items()
                   if isinstance(v, dict) and v.get("datos")}
        if p.CMD_PROFILE in bloques:
            estados.append((archivo.name, bloques))
    if len(estados) < 20:
        fallos.append(f"solo {len(estados)} respaldos con perfil: la tabla se "
                      "verifica contra ellos y asi no prueba gran cosa")
        return

    #: Los respaldos que se sabe que tienen una lectura sangrada, y por eso
    #: **tienen** que discrepar. Se guardan a proposito: son la evidencia de
    #: que esto detecta algo, no solo de que no molesta. Si alguno deja de
    #: discrepar, la tabla dejo de verificar.
    #:
    #:   * `cable-restaurado.json` — cmd 5 trajo el payload de cmd 6;
    #:   * `cable-antes-de-P2b.json` — cmd 6 trajo el de la version, y como
    #:     `respaldar.py` todavia no avisaba, el diff contra el siguiente dijo
    #:     que la tasa habia cambiado. No se habia tocado.
    CORROMPIDOS = {"cable-restaurado.json", "cable-antes-de-P2b.json"}
    detecto = set()
    for nombre, bloques in estados:
        for cmd in embebe:
            if cmd not in bloques:
                continue
            dice = estructuras.perfil_discrepa(cmd, bloques[p.CMD_PROFILE],
                                               bloques[cmd])
            if dice is None:
                continue
            if nombre in CORROMPIDOS:
                detecto.add(nombre)
            else:
                fallos.append(f"{nombre}: el perfil y cmd {cmd} discrepan y no "
                              f"deberian ({dice})")
    for nombre in sorted(CORROMPIDOS - detecto):
        fallos.append(f"{nombre} tiene una lectura sangrada y la tabla ya no "
                      "la detecta: dejo de verificar nada")

    for cmd, (_po, bo, largo) in embebe.items():
        valores = {b[cmd][bo:bo + largo] for _n, b in estados
                   if cmd in b and len(b[cmd]) >= bo + largo}
        if len(valores) < 2:
            fallos.append(f"el tramo de cmd {cmd} vale siempre lo mismo en los "
                          "respaldos: que coincida no prueba nada")


def test_leer_por_cable_solo_lee(fallos: list[str]) -> None:
    """La herramienta del modo cable **no puede escribir**, y lo que pide lo
    nombran a la vez el descriptor del mouse y el helper oficial.

    Por cable el canal de configuracion no esta medido: lo que hace el helper
    esta LEIDO de su binario, pero ninguna captura lo muestra en el cable.
    Pedir lo que el mouse declara y el helper pide es una peticion estandar
    que el driver oficial ya hace; **escribir** seria inventar
    bytes en un canal vendor, que es lo que este proyecto no hace. Por eso la
    herramienta existe solo del lado de la lectura, y esto lo fija.
    """
    # **La otra herramienta que le habla al cable tambien mide y no escribe.**
    # No le sirve el chequeo de literales de abajo -no usa ioctls a mano, pasa
    # por `linshark.cable`, que abre O_RDWR porque un pedido de lectura es una
    # transferencia OUT-, asi que lo que se le exige es lo que de verdad la
    # hace inofensiva: pedir el canal en solo lectura, donde el propio canal
    # rechaza cualquier report de escritura.
    medidor = (RAIZ / "herramientas" / "medir-sangrado.py").read_text("utf-8")
    if "solo_lectura=True" not in medidor:
        fallos.append("dev/herramientas/medir-sangrado.py abre el cable sin "
                      "solo_lectura=True")
    for prohibido in (".escribir(", "escribir_por_bloques",
                      "build_cable_write_report"):
        if prohibido in medidor:
            fallos.append(f"dev/herramientas/medir-sangrado.py menciona "
                          f"{prohibido}: es una herramienta de medir")

    ruta = RAIZ / "herramientas" / "leer-por-cable.py"
    fuente = ruta.read_text(encoding="utf-8")

    # 1. Ni el ioctl de escritura, ni un descriptor abierto para escribir.
    for prohibido in ("HIDIOCSFEATURE", "O_RDWR", "O_WRONLY", "os.write"):
        if prohibido in fuente:
            fallos.append(f"dev/herramientas/leer-por-cable.py menciona {prohibido}: "
                          "por cable no hay nada medido para escribir")
    if "O_RDONLY" not in fuente:
        fallos.append("el nodo del cable ya no se abre en solo lectura")

    # 2. Y lo que pide sale del descriptor del propio mouse, no de una lista
    #    escrita a mano: con el descriptor de verdad tienen que salir los 25
    #    Feature Reports que declara, con sus tamaños.
    mod = _herramienta("leer-por-cable.py")
    declarados = _declarados_por_el_cable(mod)

    if len(declarados) != 25:
        fallos.append(f"del descriptor del cable saco {len(declarados)} "
                      "Feature Reports, y declara 25")
    por_id = dict(declarados)
    # Tres de referencia: el dpi, que mide cuatro menos que por el dongle -el
    # relleno, ver `test_el_cable_mide_el_bloque_sin_relleno`-, y rate y
    # botones, que miden lo mismo.
    for report_id, largo in ((0x04, 51), (0x06, 8), (0x08, 58)):
        if por_id.get(report_id) != largo:
            fallos.append(f"el report {report_id:#04x} del cable mide "
                          f"{por_id.get(report_id)} y el descriptor dice "
                          f"{largo}")
    mismos = [cmd for cmd, largo in por_id.items()
              if cmd in p.READ_SUB and largo + 1 == p.READ_SUB[cmd]]
    if len(mismos) == len(por_id):
        fallos.append("todos los tamaños del cable coincidieron con los del "
                      "dongle: si eso paso de verdad, el layout se puede "
                      "empezar a contrastar y hay que revisar esta nota")

    # 3. Y de lo declarado pide solo lo que el helper oficial lee: los otros
    #    dieciseis ids no los pide el driver de verdad, y pedirlos seria
    #    mandarle al mouse algo que nadie le mando.
    pedidos, _ = mod.a_pedir(declarados)
    ids = {i for i, _ in pedidos}
    if not ids <= set(mod.LEE_EL_HELPER):
        fallos.append(f"leer-por-cable pide {sorted(ids - set(mod.LEE_EL_HELPER))}, "
                      "que el helper no lee nunca")
    if ids != set(mod.LEE_EL_HELPER) & set(por_id):
        fallos.append(f"leer-por-cable pide {sorted(ids)}: tendria que pedir "
                      "todo lo que el helper lee y el mouse declara")
    _, rechazados = mod.a_pedir(declarados, [0x22, 0x10])
    if len(rechazados) != 2:
        fallos.append("--id deja pedir un report que el helper no lee: tiene "
                      "que achicar la lista, no agrandarla")


def _herramienta(nombre: str):
    """Carga una herramienta de `dev/herramientas/` como modulo."""
    import importlib.util

    ruta = RAIZ / "herramientas" / nombre
    spec = importlib.util.spec_from_file_location(
        nombre.removesuffix(".py").replace("-", "_"), ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _declarados_por_el_cable(mod=None) -> list[tuple[int, int]]:
    """Los Feature Reports del descriptor del cable, parseados por la
    herramienta que los pide."""
    import tempfile

    mod = mod or _herramienta("leer-por-cable.py")
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / "report_descriptor"
        archivo.write_bytes(DESCRIPTOR_DEL_CABLE)
        return mod.reports_del_descriptor(archivo)


def test_el_cable_mide_el_bloque_sin_relleno(fallos: list[str]) -> None:
    """Por cable, cada report es el bloque del dongle **sin el relleno final**.

    Es la hipotesis de `protocol.build_cable_write_report()`, y la parte que se
    puede medir sin tocar el cable: sobre los respaldos -bloques que el mouse
    devolvio por el dongle-, lo que el largo que declara el cable deja afuera
    tiene que ser **siempre cero**, y el checksum interno tiene que quedar
    adentro. Si un respaldo trae algo distinto de cero ahi, cortar el bloque a
    ese largo seria perder datos, y la hipotesis se cae.

    No prueba que el mouse por cable use ese layout: eso lo dice
    `leer-por-cable.py` con el mouse enchufado, o una captura.
    """
    import json

    from linshark import estructuras as est

    largos = {rid: largo + 1 for rid, largo in _declarados_por_el_cable()}
    vistos: dict[int, int] = {}
    for archivo in sorted((RAIZ / "models" / "attackshark-x8pro" / "respaldos").glob("*.json")):
        try:
            cmds = json.loads(archivo.read_text()).get("comandos") or {}
        except Exception:                          # noqa: BLE001
            continue
        for cmd in (p.CMD_DPI, p.CMD_LIGHTING, p.CMD_REPORT_RATE,
                    p.CMD_BUTTONS, p.CMD_VERSION):
            e = cmds.get(str(cmd))
            if not e or not e.get("datos"):
                continue
            bloque = bytes([cmd, e["sizeTotalData"]]) + bytes.fromhex(e["datos"])
            largo = largos[cmd]
            if any(bloque[largo:]):
                fallos.append(f"{archivo.name}: el bloque de cmd {cmd} trae "
                              f"{bloque[largo:].hex()} despues de los {largo} B "
                              "que declara el cable")
            vistos[cmd] = vistos.get(cmd, 0) + 1

    # El checksum interno, adentro: los campos, mas sus dos bytes, mas
    # [cmd, size], caben justo en el largo del cable.
    for cmd in (p.CMD_DPI, p.CMD_LIGHTING, p.CMD_BUTTONS):
        ocupa = 2 + est.fin_de_campos(cmd) + 2
        if ocupa != largos[cmd]:
            fallos.append(f"cmd {cmd}: campos y checksum ocupan {ocupa} B y el "
                          f"cable declara {largos[cmd]}")
    for cmd in (p.CMD_DPI, p.CMD_LIGHTING):
        if vistos.get(cmd, 0) < 20:
            fallos.append(f"solo {vistos.get(cmd, 0)} bloques de cmd {cmd} en "
                          "los respaldos: poca base")


def test_el_lector_de_capturas_entiende_el_cable(fallos: list[str]) -> None:
    """Una captura usbmon del cable, armada a mano, tiene que salir bien.

    Por cable no hay Interrupt: todo va por el endpoint de control. Esto arma
    una captura con el pedido de lectura `0xA0`, su estado, la lectura del
    dpi y una escritura que cambia el nivel en uso, y verifica que el lector
    la entienda -y que marque un `SET_REPORT` rechazado con STALL-.
    """
    import struct
    import tempfile

    from linshark import estructuras as est

    def urb(n, tipo, bm, pedido, valor, largo, datos=b"", status=0,
            setup=True):
        h = bytearray(64)
        struct.pack_into("<Q", h, 0, n)
        h[8], h[9] = ord(tipo), 2
        h[10], h[11] = (0x80 if bm & 0x80 else 0), 5
        h[14] = 0 if setup else ord("-")
        struct.pack_into("<iII", h, 28, status, len(datos), len(datos))
        if setup:
            struct.pack_into("<BBHHH", h, 40, bm, pedido, valor, 2, largo)
        return bytes(h) + datos

    def pcap(paquetes) -> bytes:
        salida = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 220)
        for i, x in enumerate(paquetes):
            salida += struct.pack("<IIII", i, 0, len(x), len(x)) + x
        return salida

    leido = bytes([p.CMD_DPI, 0x38]) + bytes.fromhex(
        "0101013f2000172f3f6f9f8f0000000000000001000001ff000000ff000000ffffff"
        "0000ffffff00ffff4000ffffff020fba")
    datos = bytearray(leido[2:])
    datos[est.offsets(p.CMD_DPI)["Current_Dpi_level_flag"][0]] = 2
    escrito = leido[:2] + est.poner_checksum_interno(p.CMD_DPI, bytes(datos))
    paquetes = [
        urb(1, "S", 0x21, 9, 0x03A0, 8, p.build_cable_read_request(4)),
        urb(1, "C", 0x21, 9, 0x03A0, 8, setup=False),
        urb(2, "S", 0xA1, 1, 0x03A0, 8),
        urb(2, "C", 0xA1, 1, 0x03A0, 8, bytes([0xA0, 1]) + bytes(6),
            setup=False),
        urb(3, "S", 0xA1, 1, 0x0304, 52),
        urb(3, "C", 0xA1, 1, 0x0304, 52, leido, setup=False),
        urb(4, "S", 0x21, 9, 0x0304, 52, escrito),
        urb(4, "C", 0x21, 9, 0x0304, 52, setup=False),
    ]
    mod = _herramienta("leer-captura-usb.py")
    import contextlib
    import io

    with tempfile.TemporaryDirectory() as tmp:
        bien = Path(tmp) / "cable.pcap"
        bien.write_bytes(pcap(paquetes))
        transfs = mod.features(bien)
        vistos = [(x["sentido"], x["id"], len(x["datos"])) for x in transfs]
        if vistos != [("SET", 0xA0, 8), ("GET", 0xA0, 8), ("GET", 4, 52),
                      ("SET", 4, 52)]:
            fallos.append(f"el lector vio {vistos}")
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            problemas = mod.informar_cable(transfs)
        texto = salida.getvalue()
        if problemas:
            fallos.append(f"una captura sana dio {problemas} problema(s)")
        for esperado in ("IDENTICO", "listo", "checksum interno: ok",
                         "[24] 01->02"):
            if esperado not in texto:
                fallos.append(f"el informe no dice {esperado!r}")

        # El mismo SET rechazado por el mouse y **no repetido** tiene que
        # contar como problema.
        paquetes[-1] = urb(4, "C", 0x21, 9, 0x0304, 52, status=-32,
                           setup=False)
        mal = Path(tmp) / "stall.pcap"
        mal.write_bytes(pcap(paquetes))
        with contextlib.redirect_stdout(io.StringIO()):
            if not mod.informar_cable(mod.features(mal)):
                fallos.append("un SET_REPORT con STALL no conto como problema")

        # Y repetido identico y aceptado, no: es lo que pasa en el bus con el
        # cliente oficial (MEDIDO en las capturas del cable).
        paquetes += [urb(5, "S", 0x21, 9, 0x0304, 52, escrito),
                     urb(5, "C", 0x21, 9, 0x0304, 52, setup=False)]
        reintento = Path(tmp) / "reintento.pcap"
        reintento.write_bytes(pcap(paquetes))
        with contextlib.redirect_stdout(io.StringIO()) as salida:
            problemas = mod.informar_cable(mod.features(reintento))
        if problemas:
            fallos.append("un STALL reintentado y aceptado conto como problema")
        if "se repitio y paso" not in salida.getvalue():
            fallos.append("el informe no dice que el STALL se reintento")


def test_la_tabla_de_fabrica_sale_del_respaldo(fallos):
    """La tabla no puede decir otra cosa que la evidencia.

    `dev/models/attackshark-x8pro/respaldos/linea-base-antes-de-escribir.json` es este mouse leido **antes
    de que el proyecto le escribiera nada** —`dev/models/attackshark-x8pro/docs/bitacora.md` lo llama "de
    fabrica"— y el dpi ademas coincide byte por byte con `M()` del chunk
    `dpiX8Pro-CVtR2JhM.js`, que es el boton "restaurar" del cliente oficial.
    Dos fuentes independientes: el hardware y el bundle del fabricante.

    Si alguien agrega un campo a `DE_FABRICA` con un valor inventado, esto se
    pone rojo.
    """
    import json

    from linshark import modelo

    ruta = RAIZ / "models" / "attackshark-x8pro" / "respaldos" / "linea-base-antes-de-escribir.json"
    if not ruta.exists():
        fallos.append(f"falta el respaldo de fabrica ({ruta.name}): la tabla "
                      "se queda sin la fuente que la verifica")
        return
    virgen = modelo.por_clave(json.loads(ruta.read_text(encoding="utf-8")))

    for clave, valor in modelo.DE_FABRICA.items():
        campo = virgen.get(clave)
        if campo is None:
            fallos.append(f"DE_FABRICA trae {clave!r}, que no esta en el "
                          "respaldo de fabrica")
        elif campo.valor != valor:
            fallos.append(f"DE_FABRICA dice {clave}={valor!r} y el mouse "
                          f"virgen tenia {campo.valor!r}")

    # Y al reves: un campo escribible que el respaldo trae y la tabla no,
    # queda sin restaurar y nadie se entera.
    sin_tabla = [c for c, campo in virgen.items()
                 if campo.escribible and c not in modelo.DE_FABRICA]
    if sin_tabla:
        fallos.append(f"estos campos escribibles no tienen valor de fabrica: "
                      f"{sorted(sin_tabla)}")

    # La unica diferencia entre lo de fabrica y lo "seguro" es la tasa, y esta
    # explicada: 8000 Hz deja el mouse sin poder leerse entero.
    distintos = {c for c in modelo.SEGUROS
                 if modelo.SEGUROS[c] != modelo.DE_FABRICA.get(c)}
    if distintos != {"tasa"}:
        fallos.append(f"valores seguros difiere de fabrica en {distintos}, no "
                      "solo en la tasa")
    if modelo.TASA_SEGURA > sesion.RATE_MAXIMO_PARA_LEER:
        fallos.append(f"la tasa 'segura' es {modelo.TASA_SEGURA} Hz, arriba "
                      f"del techo desde el que el mouse se puede leer entero")


# --- el corredor ------------------------------------------------------------

PRUEBAS = [
    ("el perfil acompaña a todo cambio", test_el_perfil_acompana_a_todo_cambio),
    ("el perfil embebe donde dice", test_el_perfil_embebe_donde_dice),
    ("la tabla de fabrica sale del respaldo",
     test_la_tabla_de_fabrica_sale_del_respaldo),
    ("por cable solo se lee", test_leer_por_cable_solo_lee),
    ("el cable mide el bloque sin relleno",
     test_el_cable_mide_el_bloque_sin_relleno),
    ("el lector de capturas entiende el cable",
     test_el_lector_de_capturas_entiende_el_cable),
]


def main() -> int:
    problemas = 0
    for nombre, prueba in PRUEBAS:
        fallos: list[str] = []
        try:
            prueba(fallos)
        except Exception as exc:                   # noqa: BLE001
            fallos.append(f"{type(exc).__name__}: {exc}")
        if fallos:
            problemas += 1
            print(f"FALLA  {nombre}")
            for f in fallos:
                print(f"         - {f}")
        else:
            print(f"ok     {nombre}")
    print()
    print(f"{problemas} prueba(s) con problemas" if problemas
          else "todo en orden")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
